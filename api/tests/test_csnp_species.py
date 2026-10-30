"""GET /api/v1/csnp/species: cSNP's species, from the engine (openspec api-service)."""

from collections.abc import Iterator, Mapping
from typing import Any

import pytest
from fastapi.testclient import TestClient
from panther_engine.csnp import SPECIES_CODES, SPECIES_NAMES
from pydantic import ValidationError

from panther_api.jobs.csnp import CsnpInput
from panther_api.main import create_app

PATH = "/api/v1/csnp/species"


def listed(client: TestClient) -> list[dict[str, Any]]:
    response = client.get(PATH)
    assert response.status_code == 200
    return response.json()


def test_the_list_is_the_engines_names_in_its_order(client: TestClient) -> None:
    assert listed(client) == [{"code": code, "name": name} for code, name in SPECIES_NAMES.items()]


def test_every_species_is_listed_once(client: TestClient) -> None:
    codes = [item["code"] for item in listed(client)]

    assert len(codes) == 85
    assert len(set(codes)) == len(codes)
    assert set(codes) == SPECIES_CODES


@pytest.mark.parametrize(
    ("code", "name"), [("HUMAN", "Homo sapiens"), ("PLAF7", "Plasmodium falciparum")]
)
def test_a_species_has_its_name(client: TestClient, code: str, name: str) -> None:
    assert {"code": code, "name": name} in listed(client)


def test_the_list_is_json_and_may_be_cached_for_an_hour(client: TestClient) -> None:
    response = client.get(PATH)

    assert response.headers["content-type"] == "application/json"
    assert response.headers["cache-control"] == "public, max-age=3600"


class Unreadable(Mapping[str, str]):
    """Fails if anything reads it."""

    def __getitem__(self, key: str) -> str:
        raise AssertionError("SPECIES_NAMES was read after startup")

    def __iter__(self) -> Iterator[str]:
        raise AssertionError("SPECIES_NAMES was read after startup")

    def __len__(self) -> int:
        raise AssertionError("SPECIES_NAMES was read after startup")


def test_the_list_is_built_once_not_per_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("panther_api.routers.csnp.SPECIES_NAMES", Unreadable())

    with TestClient(create_app()) as client:
        bodies = [listed(client) for _ in range(2)]

    assert bodies[0] == bodies[1]
    assert len(bodies[0]) == 85


def test_the_list_needs_no_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PANTHER_DATA_DIR", "/nowhere")

    with TestClient(create_app()) as client:
        assert len(listed(client)) == 85


def test_the_csnp_request_accepts_every_listed_code(client: TestClient) -> None:
    for item in listed(client):
        data = {"sequence": "MKVL", "substitutions": ["K2R"], "species": item["code"]}

        assert CsnpInput.model_validate(data).species == item["code"]


def test_the_csnp_request_refuses_a_species_not_listed(client: TestClient) -> None:
    assert "XENLA" not in {item["code"] for item in listed(client)}

    with pytest.raises(ValidationError) as caught:
        CsnpInput.model_validate({"sequence": "MKVL", "substitutions": ["K2R"], "species": "XENLA"})

    assert [error["loc"] for error in caught.value.errors()] == [("species",)]
