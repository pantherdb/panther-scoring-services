from fastapi.testclient import TestClient


def test_health_is_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}


def test_health_outside_the_prefix_is_not_found(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 404
