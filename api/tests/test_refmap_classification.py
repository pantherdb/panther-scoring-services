"""GET /api/v1/refmap/organisms/{code}/classification: every gene of an organism, with its
PANTHER ID, sent from the JSON the engine builds ahead of time (openspec api-service, refmap
organism classification).

The engine's tests check how the JSON is built from a classification file; these check that the
route sends it as it is, gzipped or not, and what it does without it."""

import gzip
import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from panther_engine.refmap import classification_json_file

from panther_api.main import create_app
from panther_api.routers import refmap
from panther_api.routers.refmap import ORGANISM_NOT_FOUND, accepts_gzip

PATH = "/api/v1/refmap/organisms/{}/classification"
RESULT = {
    "organism": "ENDPU",
    "mappings": [
        {"id": "U1G4Q5", "panther_id": "PTHR10351"},
        {"id": "U1HV42", "panther_id": None},
        {"id": "U1G4Q5", "panther_id": "PTHR10351:SF2"},
    ],
}


@pytest.fixture
def data_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[TestClient]:
    """An app whose data folder holds ENDPU's classification JSON only."""
    monkeypatch.setenv("PANTHER_DATA_DIR", str(tmp_path))
    path = classification_json_file("ENDPU", tmp_path)
    path.parent.mkdir(parents=True)
    path.write_bytes(gzip.compress(json.dumps(RESULT).encode(), mtime=0))
    monkeypatch.setattr(refmap, "_missing", refmap._MissingLog())  # pyright: ignore[reportPrivateUsage]
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        yield client


def test_a_client_that_accepts_gzip_gets_the_file_as_it_is(
    data_client: TestClient, tmp_path: Path
) -> None:
    response = data_client.get(PATH.format("ENDPU"), headers={"Accept-Encoding": "gzip"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.headers["content-encoding"] == "gzip"
    stored = classification_json_file("ENDPU", tmp_path).stat().st_size
    assert response.headers["content-length"] == str(stored)
    assert response.json() == RESULT


def test_a_client_that_doesnt_accept_gzip_gets_plain_json(data_client: TestClient) -> None:
    response = data_client.get(PATH.format("ENDPU"), headers={"Accept-Encoding": "identity"})

    assert response.status_code == 200
    assert "content-encoding" not in response.headers
    assert response.json() == RESULT


def test_nothing_says_the_response_may_be_cached(data_client: TestClient) -> None:
    response = data_client.get(PATH.format("ENDPU"))

    assert "cache-control" not in response.headers
    assert "etag" not in response.headers
    assert "last-modified" not in response.headers
    assert response.headers["vary"] == "Accept-Encoding"


@pytest.mark.parametrize(
    ("header", "accepted"),
    [
        ("gzip", True),
        ("gzip, deflate, br", True),
        ("deflate, GZIP;q=0.5", True),
        ("gzip;q=0", False),
        ("gzip; q=0.000", False),
        ("identity", False),
        ("", False),
        (None, False),
    ],
)
def test_accept_encoding(header: str | None, accepted: bool) -> None:
    assert accepts_gzip(header) is accepted


# Each reaches the route, as its 404's detail shows: `..` and an encoded `/` would be routed
# elsewhere, to the router's own 404, so they wouldn't test the route's check.
@pytest.mark.parametrize("code", ["NOPE1", "endpu", "ENDPUX", "%2E%2E", "ENDP%20", "HUMAN"])
def test_a_code_refmap_doesnt_map_for_is_a_404_and_reads_nothing(
    data_client: TestClient, monkeypatch: pytest.MonkeyPatch, code: str
) -> None:
    def no_path(*_args: object) -> Path:
        raise AssertionError("a path was built for an unlisted code")

    monkeypatch.setattr(refmap, "classification_json_file", no_path)
    response = data_client.get(PATH.format(code))

    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == ORGANISM_NOT_FOUND


def test_a_listed_organism_without_its_json_fails_with_the_generic_500_logged_once(
    data_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR, logger="panther_api.routers.refmap"):
        first = data_client.get(PATH.format("ABSGL"))
        second = data_client.get(PATH.format("ABSGL"))

    for response in (first, second):
        assert response.status_code == 500
        assert response.headers["content-type"] == "application/problem+json"
        assert "ABSGL" not in response.text
        assert "classification_json" not in response.text
    logged = [record for record in caplog.records if record.name == "panther_api.routers.refmap"]
    assert len(logged) == 1
    assert "ABSGL" in logged[0].getMessage()


def test_without_a_data_folder_it_fails_with_the_generic_500(
    data_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PANTHER_DATA_DIR")

    response = data_client.get(PATH.format("ENDPU"))

    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"


def test_the_route_is_in_the_schema_with_its_404_problem_and_no_422(
    data_client: TestClient,
) -> None:
    schema = data_client.get("/api/v1/openapi.json").json()
    entry = schema["paths"]["/api/v1/refmap/organisms/{code}/classification"]["get"]

    content = entry["responses"]["200"]["content"]["application/json"]["schema"]
    assert content == {"$ref": "#/components/schemas/RefmapResult"}
    not_found = entry["responses"]["404"]["content"]["application/problem+json"]["schema"]
    assert not_found == {"$ref": "#/components/schemas/Problem"}
    assert "422" not in entry["responses"]
    assert "x-no-validation-problem" not in entry
