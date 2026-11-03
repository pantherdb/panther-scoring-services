"""CORS for a frontend on another origin (openspec change deploy-frontend-to-pages)."""

from collections.abc import Iterator

import httpx2
import pytest
from fastapi.testclient import TestClient

from panther_api.main import create_app

PAGES = "https://pantherdb.github.io"
OTHER = "https://example.com"
TOOLS_JOB: dict[str, object] = {"service": "tools", "input": {}}
SMALL_LIMIT = 1000


def preflight(client: TestClient, origin: str) -> httpx2.Response:
    return client.options(
        "/api/v1/jobs",
        headers={
            "origin": origin,
            "access-control-request-method": "POST",
            "access-control-request-headers": "content-type",
        },
    )


def cors_headers(response: httpx2.Response) -> dict[str, str]:
    return {
        name: value
        for name, value in response.headers.items()
        if name.startswith("access-control-")
    }


@pytest.fixture
def no_cors(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.delenv("PANTHER_API_CORS_ORIGINS", raising=False)
    with TestClient(create_app()) as client:
        yield client


@pytest.fixture
def pages(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("PANTHER_API_CORS_ORIGINS", f"{PAGES}, http://localhost:4173")
    monkeypatch.setenv("PANTHER_API_MAX_BODY_BYTES", str(SMALL_LIMIT))
    with TestClient(create_app()) as client:
        yield client


# Empty: no CORS at all.


def test_without_origins_a_request_from_another_origin_gets_no_cors_headers(
    no_cors: TestClient,
) -> None:
    response = no_cors.get("/api/v1/health", headers={"origin": PAGES})

    assert response.status_code == 200
    assert cors_headers(response) == {}


def test_without_origins_a_preflight_isnt_answered(no_cors: TestClient) -> None:
    response = preflight(no_cors, PAGES)

    # The route has no OPTIONS: FastAPI's 405, and nothing that allows the call.
    assert response.status_code == 405
    assert cors_headers(response) == {}


# Set: exactly those origins.


def test_a_preflight_from_an_allowed_origin_is_allowed(pages: TestClient) -> None:
    response = preflight(pages, PAGES)

    assert response.status_code == 200
    headers = cors_headers(response)
    assert headers["access-control-allow-origin"] == PAGES
    assert set(headers["access-control-allow-methods"].split(", ")) == {"GET", "POST"}
    # Starlette always adds the CORS-safelisted request headers to the one the API names.
    allowed = {name.strip().lower() for name in headers["access-control-allow-headers"].split(",")}
    assert allowed == {"content-type", "accept", "accept-language", "content-language"}
    assert "access-control-allow-credentials" not in headers


def test_a_request_from_an_allowed_origin_gets_the_cors_headers(pages: TestClient) -> None:
    response = pages.post("/api/v1/jobs", json=TOOLS_JOB, headers={"origin": PAGES})

    assert response.status_code == 202
    headers = cors_headers(response)
    assert headers["access-control-allow-origin"] == PAGES
    assert {
        name.strip().lower() for name in headers["access-control-expose-headers"].split(",")
    } == {
        "location",
        "retry-after",
    }
    assert "access-control-allow-credentials" not in headers
    assert response.headers["location"]


def test_each_listed_origin_is_allowed(pages: TestClient) -> None:
    response = pages.get("/api/v1/health", headers={"origin": "http://localhost:4173"})

    assert response.headers["access-control-allow-origin"] == "http://localhost:4173"


def test_a_preflight_from_another_origin_is_refused(pages: TestClient) -> None:
    response = preflight(pages, OTHER)

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_a_request_from_another_origin_gets_no_allow_origin(pages: TestClient) -> None:
    response = pages.get("/api/v1/health", headers={"origin": OTHER})

    # The API still answers; it's the browser that withholds the answer from the page.
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_a_request_without_an_origin_is_unaffected(pages: TestClient) -> None:
    response = pages.get("/api/v1/health")

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


# With the body limit.


def test_a_preflight_passes_the_body_limit(pages: TestClient) -> None:
    # A preflight declaring a length over the limit is still answered, not refused with a 413.
    response = pages.options(
        "/api/v1/jobs",
        headers={
            "origin": PAGES,
            "access-control-request-method": "POST",
            "content-length": str(SMALL_LIMIT + 1),
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == PAGES


def test_a_413_carries_the_cors_headers_for_an_allowed_origin(pages: TestClient) -> None:
    response = pages.post(
        "/api/v1/jobs",
        content=b"x" * (SMALL_LIMIT + 1),
        headers={"origin": PAGES, "content-type": "application/json"},
    )

    assert response.status_code == 413
    assert response.headers["access-control-allow-origin"] == PAGES


def test_a_413_for_another_origin_carries_no_allow_origin(pages: TestClient) -> None:
    response = pages.post(
        "/api/v1/jobs",
        content=b"x" * (SMALL_LIMIT + 1),
        headers={"origin": OTHER, "content-type": "application/json"},
    )

    assert response.status_code == 413
    assert "access-control-allow-origin" not in response.headers
