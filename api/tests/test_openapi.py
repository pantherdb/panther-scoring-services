import json
from typing import Any

from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel

from panther_api.main import create_app
from panther_api.openapi import REGENERATE_COMMAND, SCHEMA_PATH, render

PROBLEM = "application/problem+json"

router = APIRouter()


class Payload(BaseModel):
    count: int


@router.post("/test/validate")
def validate(payload: Payload) -> Payload:
    return payload


def served_schema(client: TestClient) -> dict[str, Any]:
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    return response.json()


def test_schema_lists_health_and_defines_problem(client: TestClient) -> None:
    schema = served_schema(client)

    assert "get" in schema["paths"]["/api/v1/health"]
    assert "Problem" in schema["components"]["schemas"]


def test_error_responses_are_problem_details(client: TestClient) -> None:
    responses = served_schema(client)["paths"]["/api/v1/health"]["get"]["responses"]

    for status in ("default", "500"):
        assert list(responses[status]["content"]) == [PROBLEM]
        assert responses[status]["content"][PROBLEM]["schema"] == {
            "$ref": "#/components/schemas/Problem"
        }


def test_route_without_input_has_no_422(client: TestClient) -> None:
    responses = served_schema(client)["paths"]["/api/v1/health"]["get"]["responses"]

    assert "422" not in responses


def test_route_with_a_body_documents_422_as_validation_problem() -> None:
    with TestClient(create_app(router)) as client:
        schema = served_schema(client)

    response = schema["paths"]["/api/v1/test/validate"]["post"]["responses"]["422"]
    assert response["content"][PROBLEM]["schema"] == {
        "$ref": "#/components/schemas/ValidationProblem"
    }
    assert "ValidationProblem" in schema["components"]["schemas"]


def test_fastapi_validation_error_schema_is_gone() -> None:
    with TestClient(create_app(router)) as client:
        schema = served_schema(client)

    assert "HTTPValidationError" not in json.dumps(schema)
    assert "#/components/schemas/ValidationError" not in json.dumps(schema)


def test_committed_schema_is_current() -> None:
    committed = SCHEMA_PATH.read_text(encoding="utf-8") if SCHEMA_PATH.exists() else ""

    assert committed == render(), (
        f"api/openapi.json is out of date. Regenerate it with `{REGENERATE_COMMAND}` "
        "from api/, and commit it with the change."
    )


def test_docs_page_loads_the_schema(client: TestClient) -> None:
    response = client.get("/api/v1/docs")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "/api/v1/openapi.json" in response.text
