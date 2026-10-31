from collections.abc import Iterator
from typing import Annotated

import httpx2
import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import AfterValidator, BaseModel

from panther_api.main import create_app
from panther_api.problems import MOST_FIELD_ERRORS, VALIDATION_DETAIL

INTERNAL_PATH = "/data/panther/19/books/PTHR10000/hmmer.hmm"
SUBMITTED_VALUE = "xyzzy-not-a-number"

router = APIRouter()


class Payload(BaseModel):
    count: int


@router.post("/test/validate")
def validate(payload: Payload) -> Payload:
    return payload


def _needs_letters(value: str) -> str:
    if not value.isalpha():
        raise ValueError("Use letters only.")
    return value


class Letters(BaseModel):
    word: Annotated[str, AfterValidator(_needs_letters)]


@router.post("/test/letters")
def letters(payload: Letters) -> Letters:
    return payload


class Counts(BaseModel):
    counts: list[int]


@router.post("/test/counts")
def counts(payload: Counts) -> Counts:
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


def test_a_validators_message_has_no_value_error_prefix(client: TestClient) -> None:
    # Pydantic writes a ValueError raised in a validator as "Value error, <message>". Users
    # read the message, so the API returns it without the prefix.
    response = client.post("/api/v1/test/letters", json={"word": "abc123"})

    assert_problem(response, 422)
    assert response.json()["errors"] == [
        {"loc": ["body", "word"], "msg": "Use letters only.", "type": "value_error"}
    ]


def _bad_counts(client: TestClient, bad: int) -> httpx2.Response:
    """A list of `bad` values that aren't integers, each with its own field error."""
    return client.post("/api/v1/test/counts", json={"counts": [SUBMITTED_VALUE] * bad})


@pytest.mark.parametrize("bad", [1, MOST_FIELD_ERRORS])
def test_up_to_the_cap_every_error_is_listed(client: TestClient, bad: int) -> None:
    response = _bad_counts(client, bad)

    assert_problem(response, 422)
    body = response.json()
    assert body["detail"] == VALIDATION_DETAIL
    assert [error["loc"] for error in body["errors"]] == [
        ["body", "counts", index] for index in range(bad)
    ]


def test_past_the_cap_the_first_errors_are_listed_with_the_total(client: TestClient) -> None:
    response = _bad_counts(client, 12_345)

    assert_problem(response, 422)
    body = response.json()
    assert [error["loc"] for error in body["errors"]] == [
        ["body", "counts", index] for index in range(MOST_FIELD_ERRORS)
    ]
    assert all(error["msg"] and error["type"] for error in body["errors"])
    assert body["detail"] == (
        f"Request validation failed: 12,345 fields are invalid, and the first "
        f"{MOST_FIELD_ERRORS} are listed."
    )
    assert SUBMITTED_VALUE not in response.text


def test_one_past_the_cap_is_counted(client: TestClient) -> None:
    body = _bad_counts(client, MOST_FIELD_ERRORS + 1).json()

    assert len(body["errors"]) == MOST_FIELD_ERRORS
    assert body["detail"].startswith(f"Request validation failed: {MOST_FIELD_ERRORS + 1:,} fields")
