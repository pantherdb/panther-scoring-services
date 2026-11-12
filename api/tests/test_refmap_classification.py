"""GET /api/v1/refmap/organisms/{code}/classification: every gene of an organism, with its
PANTHER ID, from its classification file (openspec api-service, refmap organism classification)."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from panther_engine.refmap.mapping import classification_file

from panther_api.main import create_app

PATH = "/api/v1/refmap/organisms/{}/classification"
# Lines as the published files have them, plus the cases map_panther.pl's reading defines: NOHIT,
# a repeated ID, a line with no tab, and a third field.
CONTENT = (
    b"U1G4Q5\tPTHR10351\n"
    b"U1GLA3\tPTHR47338:SF27\n"
    b"U1HV42\tNOHIT\n"
    b"U1G4Q5\tPTHR10351:SF2\n"
    b"U1NOTAB\n"
    b"U1EXTRA\tPTHR11111\textra\n"
)
MAPPINGS = [
    {"id": "U1G4Q5", "panther_id": "PTHR10351"},
    {"id": "U1GLA3", "panther_id": "PTHR47338:SF27"},
    {"id": "U1HV42", "panther_id": None},
    {"id": "U1G4Q5", "panther_id": "PTHR10351:SF2"},
    {"id": "U1NOTAB", "panther_id": None},
    {"id": "U1EXTRA", "panther_id": "PTHR11111"},
]


@pytest.fixture
def data_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[TestClient]:
    """An app whose data folder holds ENDPU's classification file only."""
    monkeypatch.setenv("PANTHER_DATA_DIR", str(tmp_path))
    path = classification_file("ENDPU", tmp_path)
    path.parent.mkdir(parents=True)
    path.write_bytes(CONTENT)
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        yield client


def test_every_line_is_a_mapping_in_the_files_order(data_client: TestClient) -> None:
    response = data_client.get(PATH.format("ENDPU"))

    assert response.status_code == 200
    assert response.json() == {"organism": "ENDPU", "mappings": MAPPINGS}


def test_the_result_is_json_with_no_cache_header(data_client: TestClient) -> None:
    response = data_client.get(PATH.format("ENDPU"))

    assert response.headers["content-type"] == "application/json"
    assert "cache-control" not in response.headers


@pytest.mark.parametrize("code", ["NOPE1", "endpu", "ENDPUX", "..", "%2E%2E", "ENDP%2F"])
def test_a_code_refmap_doesnt_map_for_is_a_404_problem(data_client: TestClient, code: str) -> None:
    response = data_client.get(PATH.format(code))

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"


def test_a_listed_organism_without_its_file_fails_with_the_generic_500(
    data_client: TestClient,
) -> None:
    response = data_client.get(PATH.format("ABSGL"))

    assert response.status_code == 500
    assert "ABSGL" not in response.text
    assert "panther_classification" not in response.text


def test_the_route_is_in_the_schema_as_a_refmap_result(data_client: TestClient) -> None:
    schema = data_client.get("/api/v1/openapi.json").json()
    entry = schema["paths"]["/api/v1/refmap/organisms/{code}/classification"]["get"]

    content = entry["responses"]["200"]["content"]["application/json"]["schema"]
    assert content == {"$ref": "#/components/schemas/RefmapResult"}
    assert "404" in entry["responses"]
