from __future__ import annotations

import os
from pathlib import Path

import pytest

DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL is required for PostgreSQL integration tests")


def identity(subject: str, email: str) -> dict[str, str]:
    return {
        "google_sub": subject,
        "email": email,
        "display_name": subject,
        "picture": "",
    }


@pytest.fixture(scope="module", autouse=True)
def migrated_database():
    import psycopg

    migration_dir = Path(__file__).resolve().parents[1] / "migrations"
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        for migration in sorted(migration_dir.glob("*.sql")):
            connection.execute(migration.read_text(encoding="utf-8"))
        connection.execute(
            "TRUNCATE klod_sessions, klod_messages, klod_conversations, klod_projects, klod_users CASCADE"
        )
        connection.execute(
            "UPDATE klod_platform_state SET owner_google_sub = NULL, initialized_at = NULL WHERE id = 1"
        )
    yield
    with psycopg.connect(DATABASE_URL, autocommit=True) as connection:
        connection.execute(
            "TRUNCATE klod_sessions, klod_messages, klod_conversations, klod_projects, klod_users CASCADE"
        )
        connection.execute(
            "UPDATE klod_platform_state SET owner_google_sub = NULL, initialized_at = NULL WHERE id = 1"
        )


def test_postgres_first_admin_sessions_conversations_projects_and_workspace(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from klod.agent import KlodAgent, KlodResponse
    from klod.api import main
    from klod.api.runtime import ModelRuntime
    from klod.auth.store import AuthStore
    from klod.tools.workspace import CoderWorkspace

    assert DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "integration-client")
    monkeypatch.setenv("KLOD_SESSION_COOKIE_SECURE", "false")
    store = AuthStore(DATABASE_URL)

    first = store.create_session(identity("first-owner", "owner@example.com"))
    second = store.create_session(identity("second-user", "user@example.com"))
    assert first["user"]["role"] == "admin"
    assert second["user"]["role"] == "user"
    assert store.get_session(first["session_token"])["id"] == first["user"]["id"]

    conversation = store.create_conversation(first["user"]["id"], "Persistência")
    conversation_id = store.save_chat_turn(
        first["user"]["id"],
        conversation["id"],
        "Teste de persistência",
        "Resposta persistida",
    )
    detail = store.get_conversation(first["user"]["id"], conversation_id)
    assert [message["role"] for message in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][0]["content"] == "Teste de persistência"

    project = store.create_project(first["user"]["id"], "Projeto de teste", "Workspace isolado")
    assert store.get_project(first["user"]["id"], project["id"])["name"] == "Projeto de teste"
    assert store.get_project(second["user"]["id"], project["id"]) is None
    assert store.admin_overview() == {"users": 2, "conversations": 1, "projects": 1}

    original_agent = main.klod_agent
    main.klod_agent = KlodAgent(ModelRuntime(), CoderWorkspace(tmp_path / "workspace"))

    def test_response(message, max_new_tokens=128, temperature=0.8):
        return KlodResponse(
            text="Resposta integrada: " + message,
            model_status="experimental",
            training_steps=2,
            parameter_count=1234,
        )

    monkeypatch.setattr(main.klod_agent, "respond", test_response)
    identities = {
        "owner-test-token-123456": identity("first-owner", "owner@example.com"),
        "user-test-token-123456": identity("second-user", "user@example.com"),
    }
    monkeypatch.setattr(main, "verify_google_identity", lambda credential, _client_id: identities[credential])
    try:
        with TestClient(main.app) as client:
            login = client.post("/v1/auth/google", json={"credential": "owner-test-token-123456"})
            assert login.status_code == 200
            assert login.json()["user"]["role"] == "admin"
            session_cookie = client.cookies.get("klod_session")
            csrf = client.cookies.get("klod_csrf")
            assert session_cookie
            assert csrf
            assert any(
                header.startswith("klod_session=") and "httponly" in header.lower()
                for header in login.headers.get_list("set-cookie")
            )
            current_user = client.get("/v1/auth/me")
            assert current_user.status_code == 200
            assert current_user.json()["user"]["role"] == "admin"

            created_conversation = client.post(
                "/v1/conversations",
                json={"title": "Conversa pela API"},
                headers={"X-Klod-CSRF": csrf},
            )
            assert created_conversation.status_code == 200
            conversation_id = created_conversation.json()["conversation"]["id"]
            loaded_conversation = client.get("/v1/conversations/" + conversation_id)
            assert loaded_conversation.status_code == 200
            assert loaded_conversation.json()["conversation"]["messages"] == []

            chat = client.post(
                "/v1/chat",
                json={"message": "Teste de chat persistente", "conversation_id": conversation_id},
                headers={"X-Klod-CSRF": csrf},
            )
            assert chat.status_code == 200
            assert chat.json()["response"] == "Resposta integrada: Teste de chat persistente"
            reloaded_conversation = client.get("/v1/conversations/" + conversation_id)
            saved_messages = reloaded_conversation.json()["conversation"]["messages"]
            assert [item["role"] for item in saved_messages] == ["user", "assistant"]
            assert saved_messages[0]["content"] == "Teste de chat persistente"
            assert saved_messages[1]["content"] == "Resposta integrada: Teste de chat persistente"

            created_project = client.post(
                "/v1/projects",
                json={"name": "Workspace API", "description": "Integração"},
                headers={"X-Klod-CSRF": csrf},
            )
            assert created_project.status_code == 200
            project_id = created_project.json()["project"]["id"]

            write = client.put(
                f"/v1/projects/{project_id}/files",
                json={"path": "src/main.py", "content": "print('Klod')\n"},
                headers={"X-Klod-CSRF": csrf},
            )
            assert write.status_code == 200
            read = client.get(f"/v1/projects/{project_id}/files?path=src%2Fmain.py")
            assert read.status_code == 200
            assert read.json()["content"] == "print('Klod')\n"
            file_list = client.get(f"/v1/projects/{project_id}/files")
            assert file_list.json()["files"][0]["path"] == "src/main.py"
            assert client.get("/v1/admin/overview").json()["users"] == 2

            logout = client.post("/v1/auth/logout", headers={"X-Klod-CSRF": csrf})
            assert logout.status_code == 200
            assert client.get("/v1/auth/me").status_code == 401

            user_login = client.post(
                "/v1/auth/google",
                json={"credential": "user-test-token-123456"},
            )
            assert user_login.status_code == 200
            assert user_login.json()["user"]["role"] == "user"
            assert client.get("/v1/admin/overview").status_code == 403
            user_csrf = client.cookies.get("klod_csrf")
            assert user_csrf
            assert client.post(
                "/v1/auth/logout",
                headers={"X-Klod-CSRF": user_csrf},
            ).status_code == 200
    finally:
        main.klod_agent = original_agent

    assert store.get_session(first["session_token"]) is not None
    store.revoke_session(second["session_token"])
    assert store.get_session(second["session_token"]) is None
