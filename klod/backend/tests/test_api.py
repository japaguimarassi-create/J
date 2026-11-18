from fastapi.testclient import TestClient

from klod.api.main import app, runtime
from klod.auth.store import AuthStore


def test_health_endpoint_reports_missing_model_honestly(monkeypatch) -> None:
    from klod.api import main

    csrf = "csrf-test-token"
    monkeypatch.setattr(
        main,
        "current_session",
        lambda _request: (None, {"role": "user", "csrf_hash": AuthStore.digest(csrf)}),
    )
    previous_model, previous_tokenizer = runtime.model, runtime.tokenizer
    runtime.model = None
    runtime.tokenizer = None
    try:
        with TestClient(app) as client:
            health = client.get("/health")
            status = client.get("/v1/model")
            client.cookies.set("klod_csrf", csrf)
            response = client.post(
                "/v1/chat",
                json={"message": "Olá"},
                headers={"X-Klod-CSRF": csrf},
            )
        assert health.status_code == 200
        assert health.json()["model_available"] is False
        assert status.json()["available"] is False
        assert response.status_code == 503
    finally:
        runtime.model, runtime.tokenizer = previous_model, previous_tokenizer


def test_chat_requires_csrf_even_with_a_valid_session(monkeypatch) -> None:
    from klod.api import main

    monkeypatch.setattr(
        main,
        "current_session",
        lambda _request: (None, {"role": "user", "csrf_hash": AuthStore.digest("expected")}),
    )
    with TestClient(app) as client:
        response = client.post("/v1/chat", json={"message": "Olá"})
    assert response.status_code == 403


def test_google_login_requires_real_server_configuration(monkeypatch) -> None:
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        response = client.post("/v1/auth/google", json={"credential": "a" * 24})
    assert response.status_code == 503
    assert "GOOGLE_CLIENT_ID" in response.json()["detail"]


def test_auth_me_requires_an_existing_session(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://unavailable")
    with TestClient(app) as client:
        response = client.get("/v1/auth/me")
    assert response.status_code == 401


def test_chat_rejects_requests_without_a_google_session(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with TestClient(app) as client:
        response = client.post("/v1/chat", json={"message": "Olá"})
    assert response.status_code == 401


def test_admin_users_rejects_non_admin_role(monkeypatch) -> None:
    from klod.api import main

    monkeypatch.setattr(main, "current_session", lambda _request: (None, {"role": "user"}))
    with TestClient(app) as client:
        response = client.get("/v1/admin/users")
    assert response.status_code == 403
