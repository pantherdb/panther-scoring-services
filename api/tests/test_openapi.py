import json
from typing import Any

import pytest
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


# The jobs contract.

SCHEMAS = "#/components/schemas/"


def test_job_request_is_a_union_tagged_by_service(client: TestClient) -> None:
    operation = served_schema(client)["paths"]["/api/v1/jobs"]["post"]
    body = operation["requestBody"]["content"]["application/json"]["schema"]

    assert body["oneOf"] == [
        {"$ref": f"{SCHEMAS}ToolsJobRequest"},
        {"$ref": f"{SCHEMAS}CsnpJobRequest"},
        {"$ref": f"{SCHEMAS}RefmapJobRequest"},
    ]
    assert body["discriminator"] == {
        "propertyName": "service",
        "mapping": {
            "tools": f"{SCHEMAS}ToolsJobRequest",
            "csnp": f"{SCHEMAS}CsnpJobRequest",
            "refmap": f"{SCHEMAS}RefmapJobRequest",
        },
    }


def test_submitting_documents_202_with_location(client: TestClient) -> None:
    responses = served_schema(client)["paths"]["/api/v1/jobs"]["post"]["responses"]

    assert "200" not in responses
    assert "Location" in responses["202"]["headers"]
    job = responses["202"]["content"]["application/json"]["schema"]
    assert job["discriminator"]["mapping"] == {
        "tools": f"{SCHEMAS}ToolsJob",
        "csnp": f"{SCHEMAS}CsnpJob",
        "refmap": f"{SCHEMAS}RefmapJob",
    }
    assert list(responses["422"]["content"]) == [PROBLEM]


def test_polling_documents_the_job_and_problems(client: TestClient) -> None:
    responses = served_schema(client)["paths"]["/api/v1/jobs/{job_id}"]["get"]["responses"]

    job = responses["200"]["content"]["application/json"]["schema"]
    assert job["oneOf"] == [
        {"$ref": f"{SCHEMAS}ToolsJob"},
        {"$ref": f"{SCHEMAS}CsnpJob"},
        {"$ref": f"{SCHEMAS}RefmapJob"},
    ]
    assert responses["default"]["content"][PROBLEM]["schema"] == {"$ref": f"{SCHEMAS}Problem"}


def test_job_status_is_a_named_enum(client: TestClient) -> None:
    status = served_schema(client)["components"]["schemas"]["JobStatus"]

    assert status["enum"] == ["queued", "running", "succeeded", "failed"]


@pytest.mark.parametrize(
    ("job_model", "result_model"),
    [("ToolsJob", "ToolsResult"), ("CsnpJob", "CsnpResult"), ("RefmapJob", "RefmapResult")],
)
def test_job_result_and_error_are_required_and_nullable(
    client: TestClient, job_model: str, result_model: str
) -> None:
    job = served_schema(client)["components"]["schemas"][job_model]

    for field, model in (("result", result_model), ("error", "Problem")):
        assert field in job["required"]
        assert job["properties"][field]["anyOf"] == [
            {"$ref": f"{SCHEMAS}{model}"},
            {"type": "null"},
        ]


# The csnp job.

NULLABLE_STRING = {"anyOf": [{"type": "string"}, {"type": "null"}]}


def properties(schema: dict[str, Any], model: str) -> dict[str, Any]:
    """The model's properties, without their titles."""
    component = schema["components"]["schemas"][model]
    return {
        name: {key: value for key, value in prop.items() if key != "title"}
        for name, prop in component["properties"].items()
    }


def test_the_csnp_request_and_input(client: TestClient) -> None:
    schema = served_schema(client)
    components = schema["components"]["schemas"]

    assert properties(schema, "CsnpJobRequest") == {
        "service": {"type": "string", "const": "csnp"},
        "input": {"$ref": f"{SCHEMAS}CsnpInput"},
    }
    csnp_input = components["CsnpInput"]
    assert sorted(csnp_input["required"]) == ["sequence", "species", "substitutions"]
    assert csnp_input["additionalProperties"] is False
    assert csnp_input["properties"]["substitutions"]["type"] == "array"
    assert csnp_input["properties"]["substitutions"]["items"]["type"] == "string"


def test_the_csnp_result_in_the_schema(client: TestClient) -> None:
    schema = served_schema(client)
    components = schema["components"]["schemas"]

    assert sorted(components["CsnpResult"]["required"]) == ["family", "scores"]
    assert properties(schema, "CsnpResult") == {
        "family": NULLABLE_STRING,
        "scores": {"type": "array", "items": {"$ref": f"{SCHEMAS}SubstitutionScore"}},
    }
    score = components["SubstitutionScore"]
    assert sorted(score["required"]) == ["age", "message", "pdel", "substitution"]
    assert properties(schema, "SubstitutionScore") == {
        "substitution": {"type": "string"},
        "age": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "message": {"type": "string"},
        "pdel": NULLABLE_STRING,
    }


# The refmap job: its contract, and the 501 until the engine maps IDs.


def test_the_refmap_501_is_documented_as_a_problem(client: TestClient) -> None:
    responses = served_schema(client)["paths"]["/api/v1/jobs"]["post"]["responses"]

    assert list(responses["501"]["content"]) == [PROBLEM]
    assert responses["501"]["content"][PROBLEM]["schema"] == {"$ref": f"{SCHEMAS}Problem"}
    # Only refmap: csnp runs.
    assert "`refmap`" in responses["501"]["description"]
    assert "csnp" not in responses["501"]["description"]


def test_the_refmap_request_and_input(client: TestClient) -> None:
    schema = served_schema(client)
    components = schema["components"]["schemas"]

    assert properties(schema, "RefmapJobRequest") == {
        "service": {"type": "string", "const": "refmap"},
        "input": {"$ref": f"{SCHEMAS}RefmapInput"},
    }
    refmap_input = components["RefmapInput"]
    assert sorted(refmap_input["required"]) == ["ids", "organism"]
    assert refmap_input["additionalProperties"] is False
    assert refmap_input["properties"]["organism"]["type"] == "string"
    ids = refmap_input["properties"]["ids"]
    assert ids["type"] == "array"
    assert (ids["minItems"], ids["maxItems"]) == (1, 100_000)
    assert ids["items"] == {"type": "string", "minLength": 1, "maxLength": 64}


def test_the_refmap_result_in_the_schema(client: TestClient) -> None:
    schema = served_schema(client)
    components = schema["components"]["schemas"]

    assert components["RefmapResult"]["required"] == ["mappings"]
    assert properties(schema, "RefmapResult") == {
        "mappings": {"type": "array", "items": {"$ref": f"{SCHEMAS}IdMapping"}},
    }
    assert sorted(components["IdMapping"]["required"]) == ["id", "panther_id"]
    assert properties(schema, "IdMapping") == {
        "id": {"type": "string"},
        "panther_id": NULLABLE_STRING,
    }


def test_the_versions_name_each_services_data(client: TestClient) -> None:
    schema = served_schema(client)
    components = schema["components"]["schemas"]

    assert "data" in components["Versions"]["required"]
    assert components["Versions"]["properties"]["data"]["items"] == {
        "$ref": f"{SCHEMAS}DataVersion"
    }
    assert sorted(components["DataVersion"]["required"]) == ["panther", "service"]
    assert properties(schema, "DataVersion") == {
        "service": {"type": "string"},
        "panther": {"type": "string"},
    }


# The cSNP species list.


def test_the_csnp_species_list_in_the_schema(client: TestClient) -> None:
    schema = served_schema(client)
    responses = schema["paths"]["/api/v1/csnp/species"]["get"]["responses"]

    body = responses["200"]["content"]["application/json"]["schema"]
    assert body["type"] == "array"
    assert body["items"] == {"$ref": f"{SCHEMAS}CsnpSpecies"}
    assert "Cache-Control" in responses["200"]["headers"]
    assert "422" not in responses
    species = schema["components"]["schemas"]["CsnpSpecies"]
    assert sorted(species["required"]) == ["code", "name"]
    assert properties(schema, "CsnpSpecies") == {
        "code": {"type": "string"},
        "name": {"type": "string"},
    }


def test_the_csnp_requests_species_is_not_an_enum(client: TestClient) -> None:
    # The species list is the endpoint above; the request keeps its validator.
    species = served_schema(client)["components"]["schemas"]["CsnpInput"]["properties"]["species"]

    assert species["type"] == "string"
    assert "enum" not in species
