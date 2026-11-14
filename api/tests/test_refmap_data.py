"""`refmap` jobs against the real PANTHER 19 release: the API, a real worker, the engine and the
refmap data (openspec scoring-jobs, refmap job maps with the engine; refmap job shape; api-service,
refmap organism classification).

Skipped without the data, as in CI's `api` job; fetch it with `panther-engine refmap data fetch`
(docs/testing/api.md, "The refmap Data"). CI's `api-image` job runs them with the data required.
"""

import time
from collections.abc import Iterator
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from markers import data_folder
from panther_engine import refmap as engine
from polling import submit_and_wait
from pydantic_core import to_json
from refmap_golden import EXAMPLE_IDS, EXAMPLE_PANTHER_IDS, ORGANISM

from panther_api.jobs.models import JOB_ADAPTER, RefmapJob
from panther_api.jobs.refmap import MOST_IDS
from panther_api.jobs.runner import JobRunner
from panther_api.jobs.work import run_job
from panther_api.main import create_app

pytestmark = pytest.mark.data("refmap")

LARGEST = "ARAVE"
"""The organism with the most genes, 246,021, so 100,000 of its own IDs are a real large job."""

MOST_RESULT_BYTES = 8_000_000
"""A bound on 100,000 mappings' JSON, about 4 MB: models of them would take about 59 MB."""

MOST_POLL_SECONDS = 2.0
"""A generous bound on a poll of the large job: it returns stored bytes, about 10 ms locally."""


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A client whose jobs run the real work, against the data folder the markers checked."""
    monkeypatch.setenv("PANTHER_DATA_DIR", str(data_folder()))
    monkeypatch.setattr("panther_api.jobs.runner.run_job", run_job)
    with TestClient(create_app()) as client:
        yield client


def first_ids(organism: str, number: int) -> list[str]:
    """The first `number` IDs of the organism's classification file, in its order."""
    folder = data_folder() / "refmap" / engine.DATA_VERSION / "panther_classification"
    with (folder / organism).open(encoding="latin-1", newline="\n") as lines:
        return [line.partition("\t")[0] for _, line in zip(range(number), lines, strict=False)]


def test_the_example_maps_as_map_panther_pl_gave_it(client: TestClient) -> None:
    body = {"service": "refmap", "input": {"organism": ORGANISM, "ids": list(EXAMPLE_IDS)}}

    job = submit_and_wait(client, body)

    assert job["status"] == "succeeded", job
    assert job["result"] == {
        "organism": ORGANISM,
        "mappings": [
            {"id": an_id, "panther_id": panther_id}
            for an_id, panther_id in zip(EXAMPLE_IDS, EXAMPLE_PANTHER_IDS, strict=True)
        ],
    }


def test_a_job_of_100000_ids_is_kept_small_and_polls_fast(client: TestClient) -> None:
    ids = first_ids(LARGEST, MOST_IDS)
    assert len(ids) == MOST_IDS
    expected = engine.map_ids(
        engine.RefmapInput(organism=LARGEST, ids=tuple(ids)), data_dir=data_folder()
    )

    job = submit_and_wait(
        client, {"service": "refmap", "input": {"organism": LARGEST, "ids": ids}}, timeout=300.0
    )
    start = time.perf_counter()
    polled = client.get(f"/api/v1/jobs/{job['id']}")
    poll_seconds = time.perf_counter() - start

    assert job["status"] == "succeeded", job["error"]
    parsed = JOB_ADAPTER.validate_json(polled.content)
    assert isinstance(parsed, RefmapJob)
    assert parsed.result is not None
    assert parsed.result.organism == LARGEST
    assert [(item.id, item.panther_id) for item in parsed.result.mappings] == [
        (item.id, item.panther_id) for item in expected.mappings
    ]
    # What the store keeps for the job: its result's JSON, and nothing else counted.
    kept = cast(JobRunner, cast(FastAPI, client.app).state.jobs).store.results_bytes
    assert kept == len(to_json(parsed.result))
    assert kept < MOST_RESULT_BYTES
    assert poll_seconds < MOST_POLL_SECONDS


@pytest.mark.skipif(
    not engine.classification_json_file(ORGANISM, data_folder()).is_file(),
    reason="needs the classification JSON: panther-engine refmap data build-json",
)
def test_every_organisms_classification_is_its_file_as_the_engine_reads_it(
    client: TestClient,
) -> None:
    """`GET /refmap/organisms/{code}/classification` for each of the 1,533 organisms, gzipped and
    not: its mappings are the engine's `classification_mappings` of the organism's file, which
    the engine's release tests check rebuild the published file byte for byte (openspec
    api-service, refmap organism classification)."""
    for code in sorted(engine.ORGANISM_CODES):
        response = client.get(f"/api/v1/refmap/organisms/{code}/classification")
        assert response.status_code == 200, code
        assert response.headers["content-encoding"] == "gzip", code
        assert response.json() == {
            "organism": code,
            "mappings": [
                {"id": item.id, "panther_id": item.panther_id}
                for item in engine.classification_mappings(code, data_folder())
            ],
        }, code
    plain = client.get(
        f"/api/v1/refmap/organisms/{ORGANISM}/classification",
        headers={"Accept-Encoding": "identity"},
    )
    assert "content-encoding" not in plain.headers
    assert len(plain.json()["mappings"]) == engine.ORGANISM_GENES[ORGANISM].genes
