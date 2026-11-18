from fastapi.testclient import TestClient

from klod.api.main import app, runtime


def test_missing_model_is_reported_honestly() -> None:
    previous = runtime.model, runtime.tokenizer
    runtime.model = None
    runtime.tokenizer = None
    try:
        with TestClient(app) as client:
            health = client.get("/health")
            status = client.get("/v1/model")
            response = client.post("/v1/chat", json={"message": "Olá"})
        assert health.status_code == 200
        assert health.json()["model_available"] is False
        assert status.json()["available"] is False
        assert response.status_code == 503
    finally:
        runtime.model, runtime.tokenizer = previous
