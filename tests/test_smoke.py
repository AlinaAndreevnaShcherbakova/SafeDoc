from fastapi.testclient import TestClient

from app.main import app


def test_openapi_available() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "paths" in response.json()

