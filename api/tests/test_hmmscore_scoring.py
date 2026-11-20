"""`hmmscore` jobs end to end: the API, a real worker, the engine, HMMER 3.4 and the hmmscore data
sample (scoring-jobs: hmmscore job scores with the engine).

Skipped without `hmmscan` and `hmmsearch` at the image's version, or without the sample, as
natively on Windows and in CI's `api` job. Run them in the API image (docs/testing/api.md, "Tests
With the Tools and Data"). Each case's sequence and expected result come from the engine's
goldens through `panther_engine.hmmscore.parity`, which applies divergence 13's pick, the "No
name" rule and the sample's arm64 copies (openspec wire-hmmscore, design.md, decision 7).
"""

import dataclasses
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from markers import REPO_ROOT, data_folder
from panther_engine.hmmscore import TimeLimitError
from panther_engine.hmmscore.parity import Case, expected_result, read_cases
from polling import poll

from panther_api.jobs.hmmscore import HmmscoreInput, run_hmmscore
from panther_api.jobs.work import run_job
from panther_api.main import create_app

pytestmark = [pytest.mark.tools("hmmscan", "hmmsearch"), pytest.mark.data("hmmscore")]

GOLDEN = REPO_ROOT / "engine" / "tests" / "golden" / "hmmscore" / "parity"
# The goldens made on the data sample.
GOLDENS = "sample"
# A search of the sample takes about a second; the first job also starts a worker.
POLL_TIMEOUT = 300.0
CASES = {case.name: case for case in read_cases(GOLDEN)}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """An app whose workers run the real work, with the data folder the markers checked. The
    workers start with the first job, so they inherit `PANTHER_DATA_DIR` from here."""
    monkeypatch.setattr("panther_api.jobs.runner.run_job", run_job)
    monkeypatch.setenv("PANTHER_DATA_DIR", str(data_folder()))
    with TestClient(create_app()) as client:
        yield client


def expected(case: Case) -> dict[str, Any]:
    """The case's expected result, as the job's JSON gives it."""
    return dataclasses.asdict(expected_result(case, GOLDEN, GOLDENS))


def run(client: TestClient, case: Case) -> dict[str, Any]:
    response = client.post(
        "/api/v1/jobs",
        json={"service": "hmmscore", "input": {"sequence": case.sequence(GOLDEN)}},
    )
    assert response.status_code == 202, response.text
    return poll(client, response.json()["id"], timeout=POLL_TIMEOUT, interval=0.2)[-1]


def test_the_forms_example_gets_its_golden_hit(client: TestClient) -> None:
    case = CASES["apoe"]

    job = run(client, case)

    assert job["status"] == "succeeded", job["error"]
    assert job["result"] == expected(case)
    assert job["result"]["hit"]["panther_id"] == "PTHR18976:SF2"
    assert job["result"]["hit"]["name"] == "APOLIPOPROTEIN E"
    assert job["versions"]["data"] == [{"service": "hmmscore", "panther": "19"}]


def test_a_sequence_that_matches_no_family_has_no_hit(client: TestClient) -> None:
    job = run(client, CASES["no-hit"])

    assert job["status"] == "succeeded", job["error"]
    assert job["result"] == {"hit": None}
    assert expected(CASES["no-hit"]) == {"hit": None}


def test_tied_best_hits_give_the_subfamily(client: TestClient) -> None:
    # Divergence 13: the subfamily before its own family, where the CGI picked in hash order.
    case = CASES["tie-pthr35774"]

    job = run(client, case)

    assert job["status"] == "succeeded", job["error"]
    assert job["result"] == expected(case)
    assert job["result"]["hit"]["panther_id"] == "PTHR35774:SF1"


def test_a_search_past_its_time_limit_raises_the_engines_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # In this process, with a millisecond: the setting is whole seconds, at least 1, and a search
    # of the sample finishes within one, so a job can't be made to reach its limit.
    monkeypatch.setenv("PANTHER_DATA_DIR", str(data_folder()))
    request = HmmscoreInput.model_validate({"sequence": CASES["apoe"].sequence(GOLDEN)})

    with pytest.raises(TimeLimitError):
        run_hmmscore(request, cpu=0, timeout=0.001)

    # Beside it, with time enough, the same search succeeds.
    assert run_hmmscore(request, cpu=0, timeout=300).hit is not None
