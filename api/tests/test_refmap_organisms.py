"""GET /api/v1/refmap/organisms: refmap's organisms, from the engine (openspec api-service)."""

from typing import Any

from fastapi.testclient import TestClient
from panther_engine.refmap import ORGANISM_CODES, ORGANISM_GENES, ORGANISM_NAMES

from panther_api.jobs.refmap import RefmapInput
from panther_api.main import create_app

PATH = "/api/v1/refmap/organisms"


def listed(client: TestClient) -> list[dict[str, Any]]:
    response = client.get(PATH)
    assert response.status_code == 200
    return response.json()


def test_the_list_is_the_engines_organisms_in_its_order(client: TestClient) -> None:
    assert listed(client) == [
        {
            "code": code,
            "name": name,
            "genes": ORGANISM_GENES[code].genes,
            "genes_with_panther_id": ORGANISM_GENES[code].genes_with_panther_id,
        }
        for code, name in ORGANISM_NAMES.items()
    ]


def test_every_organism_is_listed_once(client: TestClient) -> None:
    codes = [item["code"] for item in listed(client)]

    assert len(codes) == 1533
    assert len(set(codes)) == len(codes)
    assert set(codes) == ORGANISM_CODES


def test_an_organism_has_its_name_and_gene_counts(client: TestClient) -> None:
    assert {
        "code": "ENDPU",
        "name": "Endocarpon pusillum",
        "genes": 9228,
        "genes_with_panther_id": 7665,
    } in listed(client)


def test_the_list_is_json_and_may_be_cached_for_an_hour(client: TestClient) -> None:
    response = client.get(PATH)

    assert response.headers["content-type"] == "application/json"
    assert response.headers["cache-control"] == "public, max-age=3600"


def test_the_list_needs_no_data(monkeypatch: Any) -> None:
    monkeypatch.setenv("PANTHER_DATA_DIR", "/nowhere")

    with TestClient(create_app()) as client:
        assert len(listed(client)) == 1533


def test_the_refmap_request_accepts_every_listed_code(client: TestClient) -> None:
    for item in listed(client):
        RefmapInput.model_validate({"organism": item["code"], "ids": ["U1G4Q5"]})


def test_the_list_is_in_the_schema(client: TestClient) -> None:
    schema = client.get("/api/v1/openapi.json").json()
    entry = schema["components"]["schemas"]["RefmapOrganism"]

    assert sorted(entry["required"]) == ["code", "genes", "genes_with_panther_id", "name"]
    assert {name: value["type"] for name, value in entry["properties"].items()} == {
        "code": "string",
        "name": "string",
        "genes": "integer",
        "genes_with_panther_id": "integer",
    }
    assert PATH in schema["paths"]
