"""`refmap` jobs end to end against a made-up data folder: the API, a real worker and the engine,
mapping with ENDPU's golden lines (openspec scoring-jobs, refmap job maps with the engine).

No release data is needed, so these run everywhere. `test_refmap_data.py` runs the same jobs
against the real release.
"""

import logging
from collections.abc import Iterator
from itertools import cycle
from pathlib import Path
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from job_helpers import FAKE_FAMILY, score_with_a_fake_engine
from polling import poll, submit_and_wait
from refmap_golden import (
    EXAMPLE_IDS,
    EXAMPLE_PANTHER_IDS,
    ORGANISM,
    golden_mappings,
    write_endpu_folder,
)

from panther_api.jobs.models import JOB_ADAPTER, RefmapJob
from panther_api.jobs.refmap import MOST_IDS, RefmapInput, RefmapResult, run_refmap
from panther_api.jobs.runner import JobRunner
from panther_api.jobs.work import RefmapJobRequest, SerializedResult, run_job
from panther_api.main import create_app


def refmap_job(ids: list[str] | tuple[str, ...]) -> dict[str, object]:
    return {"service": "refmap", "input": {"organism": ORGANISM, "ids": list(ids)}}


@pytest.fixture
def endpu_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[TestClient]:
    """A client whose jobs run the real work, with a data folder holding only ENDPU's file. The
    folder is set before the app starts: the workers start with the first job, and inherit it."""
    write_endpu_folder(tmp_path)
    monkeypatch.setenv("PANTHER_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("panther_api.jobs.runner.run_job", run_job)
    with TestClient(create_app()) as client:
        yield client


def test_the_example_maps_to_the_goldens_values(endpu_client: TestClient) -> None:
    job = submit_and_wait(endpu_client, refmap_job(EXAMPLE_IDS))

    assert job["status"] == "succeeded", job
    assert job["error"] is None
    assert job["result"] == {
        "organism": ORGANISM,
        "mappings": [
            {"id": an_id, "panther_id": panther_id}
            for an_id, panther_id in zip(EXAMPLE_IDS, EXAMPLE_PANTHER_IDS, strict=True)
        ],
    }


def test_repeated_and_unknown_ids_each_get_a_mapping_in_order(endpu_client: TestClient) -> None:
    job = submit_and_wait(endpu_client, refmap_job(["U1G4Q5", "P04217", "U1G4Q5"]))

    assert job["status"] == "succeeded", job
    assert job["result"]["mappings"] == [
        {"id": "U1G4Q5", "panther_id": "PTHR11360:SF130"},
        {"id": "P04217", "panther_id": None},
        {"id": "U1G4Q5", "panther_id": "PTHR11360:SF130"},
    ]


def test_every_golden_id_maps_as_map_panther_pl_gave_it(endpu_client: TestClient) -> None:
    golden = golden_mappings()

    job = submit_and_wait(endpu_client, refmap_job(list(golden)))

    assert job["status"] == "succeeded", job
    assert job["result"]["mappings"] == [
        {"id": an_id, "panther_id": panther_id} for an_id, panther_id in golden.items()
    ]


def test_an_organism_without_its_file_fails_with_the_generic_500(
    endpu_client: TestClient, tmp_path: Path
) -> None:
    job = submit_and_wait(
        endpu_client, {"service": "refmap", "input": {"organism": "ARAVE", "ids": ["P04217"]}}
    )

    assert job["status"] == "failed"
    assert job["result"] is None
    assert job["error"]["status"] == 500
    assert str(tmp_path) not in str(job)


def test_a_refmap_and_a_csnp_job_dont_mix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # The real refmap work, and csnp's with the engine's score() faked in the worker.
    write_endpu_folder(tmp_path)
    monkeypatch.setenv("PANTHER_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("panther_api.jobs.runner.run_job", score_with_a_fake_engine)
    csnp = {
        "service": "csnp",
        "input": {"sequence": "MKVLAAGIV", "substitutions": ["K2E"], "species": "HUMAN"},
    }
    with TestClient(create_app()) as client:
        refmap_id = client.post("/api/v1/jobs", json=refmap_job(EXAMPLE_IDS)).json()["id"]
        csnp_job = submit_and_wait(client, csnp)
        refmap_job_ = submit_and_wait(client, refmap_job(["U1G4Q5"]))
        first = poll(client, refmap_id)[-1]

    assert (first["status"], csnp_job["status"], refmap_job_["status"]) == ("succeeded",) * 3
    assert first["result"]["organism"] == ORGANISM
    assert [item["id"] for item in first["result"]["mappings"]] == list(EXAMPLE_IDS)
    assert csnp_job["result"]["family"] == FAKE_FAMILY
    assert [score["substitution"] for score in csnp_job["result"]["scores"]] == ["K2E"]
    assert refmap_job_["result"]["mappings"] == [{"id": "U1G4Q5", "panther_id": "PTHR11360:SF130"}]


# A finished result is kept as the JSON the worker made (wire-refmap, design.md, decision 4).


def test_run_job_returns_the_refmap_result_serialised(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    write_endpu_folder(tmp_path)
    monkeypatch.setenv("PANTHER_DATA_DIR", str(tmp_path))
    request = RefmapInput(organism=ORGANISM, ids=list(EXAMPLE_IDS))

    result = run_job(RefmapJobRequest(service="refmap", input=request))

    assert isinstance(result, SerializedResult)
    assert RefmapResult.model_validate_json(result.json) == run_refmap(request)


def test_a_large_job_polls_as_a_job_with_every_mapping_in_order(
    endpu_client: TestClient,
) -> None:
    golden = golden_mappings()
    ids = [an_id for _, an_id in zip(range(MOST_IDS), cycle(golden), strict=False)]

    response = submit_and_wait(endpu_client, refmap_job(ids), timeout=120.0)
    polled = endpu_client.get(f"/api/v1/jobs/{response['id']}")

    assert polled.status_code == 200
    assert polled.headers["content-type"] == "application/json"
    job = JOB_ADAPTER.validate_json(polled.content)
    assert isinstance(job, RefmapJob)
    assert job.result is not None
    assert job.result.organism == ORGANISM
    assert [(item.id, item.panther_id) for item in job.result.mappings] == [
        (an_id, golden[an_id]) for an_id in ids
    ]
    # Every other field as for a small job.
    assert polled.json() | {"result": None} == response | {"result": None}


def test_a_finished_job_keeps_its_result_as_json_and_its_log_line(
    endpu_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    job = submit_and_wait(endpu_client, refmap_job(EXAMPLE_IDS))

    record = cast(JobRunner, cast(FastAPI, endpu_client.app).state.jobs).store.get(job["id"])
    assert record is not None
    assert isinstance(record.result, SerializedResult)
    assert RefmapResult.model_validate_json(record.result.json).model_dump() == job["result"]
    [line] = [
        r.getMessage()
        for r in caplog.records
        if r.name == "panther_api.jobs.runner" and r.levelno == logging.INFO
    ]
    assert f"refmap, {ORGANISM}, 6 IDs: succeeded" in line
    for an_id in EXAMPLE_IDS:
        assert an_id not in line
