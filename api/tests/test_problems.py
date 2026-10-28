from collections.abc import Iterator

import httpx2
import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from panther_api.main import create_app

INTERNAL_PATH = "/data/panther/19/books/PTHR10000/hmmer.hmm"
SUBMITTED_VALUE = "xyzzy-not-a-number"

router = APIRouter()


class Payload(BaseModel):
    count: int


@router.post("/test/validate")
def validate(payload: Payload) -> Payload:
    return payload


@router.get("/test/boom")
def boom() -> None:
    raise RuntimeError(f"failed reading {INTERNAL_PATH}")


@pytest.fixture
def client() -> Iterator[TestClient]:
    # Starlette re-raises the exception after the 500 handler; without this flag the test
    # would see the exception instead of the response.
    with TestClient(create_app(router), raise_server_exceptions=False) as client:
        yield client


# Starlette 1.x's TestClient is built on httpx2, not httpx.
def assert_problem(response: httpx2.Response, status: int) -> None:
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["status"] == status
    assert isinstance(body["type"], str)
    assert isinstance(body["title"], str)
    assert isinstance(body["detail"], str)


def test_unknown_path_is_a_problem(client: TestClient) -> None:
    assert_problem(client.get("/api/v1/does-not-exist"), 404)


def test_path_outside_the_prefix_is_a_problem(client: TestClient) -> None:
    assert_problem(client.get("/health"), 404)


def test_wrong_method_is_a_problem_with_allow(client: TestClient) -> None:
    response = client.post("/api/v1/health")

    assert_problem(response, 405)
    assert "GET" in response.headers["allow"]


def test_validation_error_lists_the_field(client: TestClient) -> None:
    response = client.post("/api/v1/test/validate", json={"count": SUBMITTED_VALUE})

    assert_problem(response, 422)
    errors = response.json()["errors"]
    assert len(errors) == 1
    assert errors[0]["loc"] == ["body", "count"]
    assert isinstance(errors[0]["msg"], str)
    assert isinstance(errors[0]["type"], str)


def test_validation_error_does_not_echo_the_value(client: TestClient) -> None:
    response = client.post("/api/v1/test/validate", json={"count": SUBMITTED_VALUE})

    assert SUBMITTED_VALUE not in response.text


def test_unexpected_error_reveals_nothing(client: TestClient) -> None:
    response = client.get("/api/v1/test/boom")

    assert_problem(response, 500)
    assert "failed reading" not in response.text
    assert INTERNAL_PATH not in response.text
