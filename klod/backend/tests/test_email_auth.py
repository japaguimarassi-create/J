from __future__ import annotations

from fastapi.testclient import TestClient

from klod.api import main


class MemoryAuthStore:
    def __init__(self, user=None):
        self.user = user
        self.issued = []
        self.consumed = []
        self.failures = 0
        self.session = {
            "session_token": "opaque-session-token",
            "csrf_token": "csrf-session-token",
            "expires_at": __import__("datetime").datetime(2026, 12, 1),
            "user": {
                "id": "user-1",
                "email": "person@example.com",
                "display_name": "Person",
                "picture": "",
                "role": "admin",
            },
        }

    def create_email_account(self, email, display_name, password_hash):
        self.user = {
            "id": "user-1",
            "email": email,
            "display_name": display_name,
            "password_hash": password_hash,
            "email_verified": False,
        }
        return self.user

    def get_auth_user(self, email):
        return self.user if self.user and self.user["email"] == email else None

    def issue_email_token(self, user_id, purpose):
        self.issued.append((user_id, purpose))
        return "single-use-email-token-0123456789"

    def consume_email_token(self, token, purpose, **kwargs):
        self.consumed.append((token, purpose, kwargs))
        if token != "single-use-email-token-0123456789":
            return None
        return {
            "id": "user-1",
            "email": "person@example.com",
            "display_name": "Person",
            "picture": "",
            "role": "admin",
        }

    def is_login_rate_limited(self, attempt_key):
        return False

    def record_login_failure(self, attempt_key):
        self.failures += 1

    def clear_login_failures(self, attempt_key):
        return None

    def create_session_for_user(self, user_id):
        return self.session


def test_registration_hashes_password_and_requests_email_delivery(monkeypatch):
    store = MemoryAuthStore()
    sent = []
    monkeypatch.setattr(main, "auth_store", lambda: store)
    monkeypatch.setattr(main, "ensure_email_delivery_configured", lambda: None)
    monkeypatch.setattr(main, "send_account_email", lambda email, token, purpose: sent.append((email, token, purpose)))
    with TestClient(main.app) as client:
        response = client.post(
            "/v1/auth/register",
            json={
                "display_name": "Person",
                "email": " PERSON@Example.com ",
                "password": "correct-horse-battery",
            },
        )
    assert response.status_code == 200
    assert store.user["email"] == "person@example.com"
    assert main.password_hasher.verify(store.user["password_hash"], "correct-horse-battery")
    assert sent == [("person@example.com", "single-use-email-token-0123456789", "verify_email")]


def test_login_creates_httponly_session_after_email_is_verified(monkeypatch):
    password_hash = main.password_hasher.hash("correct-horse-battery")
    store = MemoryAuthStore({
        "id": "user-1",
        "email": "person@example.com",
        "display_name": "Person",
        "picture_url": "",
        "role": "user",
        "password_hash": password_hash,
        "email_verified": True,
    })
    monkeypatch.setattr(main, "auth_store", lambda: store)
    monkeypatch.setenv("KLOD_SESSION_COOKIE_SECURE", "false")
    with TestClient(main.app) as client:
        response = client.post(
            "/v1/auth/login",
            json={"email": "person@example.com", "password": "correct-horse-battery"},
        )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "person@example.com"
    assert any(
        header.startswith("klod_session=") and "httponly" in header.lower()
        for header in response.headers.get_list("set-cookie")
    )


def test_unverified_user_cannot_create_a_login_session(monkeypatch):
    password_hash = main.password_hasher.hash("correct-horse-battery")
    store = MemoryAuthStore({
        "id": "user-1",
        "email": "person@example.com",
        "display_name": "Person",
        "picture_url": "",
        "role": "user",
        "password_hash": password_hash,
        "email_verified": False,
    })
    monkeypatch.setattr(main, "auth_store", lambda: store)
    with TestClient(main.app) as client:
        response = client.post(
            "/v1/auth/login",
            json={"email": "person@example.com", "password": "correct-horse-battery"},
        )
    assert response.status_code == 403
    assert "Confirme seu e-mail" in response.json()["detail"]


def test_verification_token_is_consumed_and_starts_a_session(monkeypatch):
    store = MemoryAuthStore()
    monkeypatch.setattr(main, "auth_store", lambda: store)
    monkeypatch.setenv("KLOD_SESSION_COOKIE_SECURE", "false")
    monkeypatch.setenv("KLOD_OWNER_EMAIL", "person@example.com")
    with TestClient(main.app) as client:
        response = client.post(
            "/v1/auth/verify-email",
            json={"token": "single-use-email-token-0123456789"},
        )
    assert response.status_code == 200
    assert store.consumed[0][1] == "verify_email"
    assert store.consumed[0][2]["owner_email"] == "person@example.com"
    assert response.json()["user"]["role"] == "admin"
    assert client.cookies.get("klod_session") == "opaque-session-token"


def test_password_reset_hashes_the_new_password(monkeypatch):
    store = MemoryAuthStore()
    monkeypatch.setattr(main, "auth_store", lambda: store)
    with TestClient(main.app) as client:
        response = client.post(
            "/v1/auth/reset-password",
            json={
                "token": "single-use-email-token-0123456789",
                "password": "new-correct-horse-battery",
            },
        )
    assert response.status_code == 200
    kwargs = store.consumed[0][2]
    assert main.password_hasher.verify(kwargs["new_password_hash"], "new-correct-horse-battery")


def test_bad_password_increments_rate_limit_counter(monkeypatch):
    password_hash = main.password_hasher.hash("correct-horse-battery")
    store = MemoryAuthStore({
        "id": "user-1",
        "email": "person@example.com",
        "display_name": "Person",
        "picture_url": "",
        "role": "user",
        "password_hash": password_hash,
        "email_verified": True,
    })
    monkeypatch.setattr(main, "auth_store", lambda: store)
    with TestClient(main.app) as client:
        response = client.post(
            "/v1/auth/login",
            json={"email": "person@example.com", "password": "incorrect-password"},
        )
    assert response.status_code == 401
    assert store.failures == 2
