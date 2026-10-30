import pickle
import time
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from clock import Clock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from job_helpers import (
    FAKE_RESULT,
    GATE_VARIABLE,
    INTERNAL_PATH,
    exit_worker,
    fail,
    report_fake_tools,
    wait_for_gate,
)
from panther_engine.core.tools import ToolReport
from pydantic import ValidationError

from panther_api.jobs.csnp import CsnpInput
from panther_api.jobs.runner import WORKER_STOPPED_DETAIL, JobRunner
from panther_api.jobs.tools import ToolsInput, run_tools
from panther_api.jobs.work import CsnpJobRequest, ToolsJobRequest, run_job
from panther_api.main import create_app

# The directory in conftest's fake report paths. No job may contain it.
FAKE_TOOLS_DIR = "fake-tools"
PROBLEM = "application/problem+json"
TOOLS_JOB: dict[str, object] = {"service": "tools", "input": {}}
STATUS_ORDER = ["queued", "running", "succeeded"]
FINISHED = ("succeeded", "failed")
# A worker's first start under spawn imports pydantic and the engine: about a second.
POLL_TIMEOUT = 60.0

Job = dict[str, Any]


def submit(client: TestClient, body: object = TOOLS_JOB) -> Job:
    response = client.post("/api/v1/jobs", json=body)
    assert response.status_code == 202, response.text
    return response.json()


def poll(client: TestClient, job_id: str, until: tuple[str, ...] = FINISHED) -> list[Job]:
    """Poll the job, as the frontend does, until its status is one of `until`. Every answer."""
    deadline = time.monotonic() + POLL_TIMEOUT
    answers: list[Job] = []
    while True:
        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200, response.text
        answers.append(response.json())
        if answers[-1]["status"] in until:
            return answers
        assert time.monotonic() < deadline, f"job still {answers[-1]['status']}"
        time.sleep(0.05)


def runner(client: TestClient) -> JobRunner:
    return cast(FastAPI, client.app).state.jobs


# The tools job's work, in the test process. conftest patches the report it calls.


def test_run_tools_lists_the_tools_in_the_engine_order() -> None:
    result = run_tools(ToolsInput())

    assert [(tool.name, tool.version) for tool in result.tools] == [
        ("blastp", "2.17.0"),
        ("hmmscan", "3.4"),
        ("hmmsearch", "3.4"),
        ("epa-ng", "0.3.8"),
    ]


def test_run_tools_gives_null_for_a_missing_tool(
    monkeypatch: pytest.MonkeyPatch, fake_tools: tuple[ToolReport, ...]
) -> None:
    reports = [*fake_tools[:3], ToolReport("epa-ng", None, None)]
    monkeypatch.setattr("panther_api.jobs.tools.report_tools", lambda: reports)

    result = run_tools(ToolsInput())

    assert result.tools[-1].name == "epa-ng"
    assert result.tools[-1].version is None


def test_run_tools_leaves_out_the_paths() -> None:
    assert FAKE_TOOLS_DIR not in run_tools(ToolsInput()).model_dump_json()


def test_run_job_runs_the_tools_job() -> None:
    result = run_job(ToolsJobRequest(service="tools", input=ToolsInput()))

    assert result == run_tools(ToolsInput())
    assert result == FAKE_RESULT


def test_work_pickles_by_reference() -> None:
    # Under spawn, a worker imports each function by name: it must be module-level.
    assert pickle.loads(pickle.dumps(run_job)) is run_job  # noqa: S301 (our own bytes)
    assert pickle.loads(pickle.dumps(run_tools)) is run_tools  # noqa: S301 (our own bytes)


# Submitting and polling, through a real worker pool.


def test_submit_answers_202_with_location_and_the_job(client: TestClient) -> None:
    response = client.post("/api/v1/jobs", json=TOOLS_JOB)

    assert response.status_code == 202
    assert response.headers["content-type"] == "application/json"
    job = response.json()
    assert job["service"] == "tools"
    assert job["status"] in ("queued", "running")
    assert response.headers["location"] == f"/api/v1/jobs/{job['id']}"
    assert client.get(response.headers["location"]).status_code == 200


@pytest.mark.parametrize(
    ("body", "loc"),
    [
        ({"service": "no-such-service", "input": {}}, ["body"]),
        ({"input": {}}, ["body"]),
        (
            {"service": "tools", "input": {"unexpected": 1}},
            ["body", "tools", "input", "unexpected"],
        ),
        ({"service": "tools"}, ["body", "tools", "input"]),
        ({"service": "tools", "input": "xyzzy-not-an-object"}, ["body", "tools", "input"]),
    ],
    ids=["unknown service", "no service", "invalid input", "missing input", "input not an object"],
)
def test_an_invalid_request_is_a_422_and_creates_no_job(
    client: TestClient, body: object, loc: list[str]
) -> None:
    response = client.post("/api/v1/jobs", json=body)

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM
    assert [error["loc"] for error in response.json()["errors"]] == [loc]
    assert "xyzzy" not in response.text
    assert len(runner(client).store) == 0


def test_an_unknown_service_is_not_echoed(client: TestClient) -> None:
    response = client.post("/api/v1/jobs", json={"service": "xyzzy-service", "input": {}})

    assert response.status_code == 422
    assert "xyzzy" not in response.text
    # The message still says which services there are.
    assert "'tools'" in response.json()["errors"][0]["msg"]


def test_job_ids_are_different_random_uuid4s(client: TestClient) -> None:
    ids = [submit(client)["id"] for _ in range(2)]

    assert ids[0] != ids[1]
    assert all(UUID(job_id).version == 4 for job_id in ids)


def test_status_only_moves_forward_until_succeeded(client: TestClient) -> None:
    job = submit(client)

    answers = poll(client, job["id"])

    statuses = [job["status"]] + [answer["status"] for answer in answers]
    assert statuses[-1] == "succeeded"
    positions = [STATUS_ORDER.index(status) for status in statuses]
    assert positions == sorted(positions)


def test_a_finished_job(client: TestClient) -> None:
    job = poll(client, submit(client)["id"])[-1]

    assert job["status"] == "succeeded"
    assert job["created_at"] <= job["started_at"] <= job["finished_at"]
    assert job["created_at"].endswith("Z")
    assert job["result"] == FAKE_RESULT.model_dump()
    assert job["error"] is None
    assert job["versions"] == client.get("/api/v1/versions").json()


def test_a_finished_job_has_no_paths(client: TestClient) -> None:
    job = poll(client, submit(client)["id"])[-1]

    assert FAKE_TOOLS_DIR not in str(job)


@pytest.mark.parametrize("job_id", [str(uuid4()), "not-a-uuid"])
def test_an_unknown_id_is_a_404_problem(client: TestClient, job_id: str) -> None:
    response = client.get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 404
    assert response.headers["content-type"] == PROBLEM
    body = response.json()
    assert body["status"] == 404
    assert job_id not in body["detail"]


# Workers: more jobs than workers, and the API while a job runs.


@pytest.fixture
def gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Jobs stay running until the test creates this file. Created at the end, whatever happens,
    so the app's shutdown doesn't wait for a held job."""
    path = tmp_path / "gate"
    monkeypatch.setenv(GATE_VARIABLE, str(path))
    monkeypatch.setattr("panther_api.jobs.runner.run_job", wait_for_gate)
    yield path
    path.touch()


def test_a_job_waits_queued_while_the_only_worker_is_busy(
    monkeypatch: pytest.MonkeyPatch, gate: Path
) -> None:
    monkeypatch.setenv("PANTHER_API_JOB_WORKERS", "1")
    with TestClient(create_app()) as client:
        first = submit(client)
        poll(client, first["id"], until=("running",))
        second = submit(client)

        # However long the first runs, the second waits for the one worker.
        for _ in range(10):
            assert poll(client, second["id"], until=("queued",))[-1]["status"] == "queued"
            time.sleep(0.05)

        gate.touch()
        first_done = poll(client, first["id"])[-1]
        second_done = poll(client, second["id"])[-1]

    assert (first_done["status"], second_done["status"]) == ("succeeded", "succeeded")
    assert second_done["started_at"] >= first_done["finished_at"]


def test_the_api_answers_while_a_job_runs(gate: Path) -> None:
    with TestClient(create_app()) as client:
        job = submit(client)
        poll(client, job["id"], until=("running",))

        assert client.get("/api/v1/health").status_code == 200
        assert client.get(f"/api/v1/jobs/{job['id']}").json()["status"] == "running"

        gate.touch()
        assert poll(client, job["id"])[-1]["status"] == "succeeded"


# Failures.


def assert_failed_with_a_problem(job: Job) -> None:
    assert job["status"] == "failed"
    assert job["result"] is None
    assert job["finished_at"] is not None
    error = job["error"]
    assert error["status"] == 500
    assert isinstance(error["type"], str)
    assert isinstance(error["title"], str)
    assert isinstance(error["detail"], str)


def test_work_that_raises_fails_the_job_and_reveals_nothing(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", fail)

    job = poll(client, submit(client)["id"])[-1]

    assert_failed_with_a_problem(job)
    text = str(job)
    assert "failed reading" not in text
    assert INTERNAL_PATH not in text
    assert "Traceback" not in text
    assert "RuntimeError" not in text


def test_a_failed_job_leaves_the_next_one_alone(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", fail)
    failed = poll(client, submit(client)["id"])[-1]
    monkeypatch.setattr("panther_api.jobs.runner.run_job", report_fake_tools)

    succeeded = poll(client, submit(client)["id"])[-1]

    assert failed["status"] == "failed"
    assert succeeded["status"] == "succeeded"


def test_a_dead_worker_fails_its_job_and_later_jobs_run(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", exit_worker)
    dead = poll(client, submit(client)["id"])[-1]
    monkeypatch.setattr("panther_api.jobs.runner.run_job", report_fake_tools)

    later = poll(client, submit(client)["id"])[-1]

    assert_failed_with_a_problem(dead)
    assert dead["error"]["detail"] == WORKER_STOPPED_DETAIL
    assert later["status"] == "succeeded"


def test_a_dead_worker_leaves_the_queued_jobs_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PANTHER_API_JOB_WORKERS", "1")
    with TestClient(create_app()) as client:
        monkeypatch.setattr("panther_api.jobs.runner.run_job", exit_worker)
        dead = submit(client)
        # Queued behind it, for the one worker. The pool is given it only after the death.
        queued = submit(client)
        monkeypatch.setattr("panther_api.jobs.runner.run_job", report_fake_tools)

        assert poll(client, dead["id"])[-1]["status"] == "failed"
        assert poll(client, queued["id"])[-1]["status"] == "succeeded"


# Expiry and settings.


def test_a_finished_job_expires_24_hours_after_it_finished(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    clock = Clock()
    monkeypatch.setattr("panther_api.jobs.store.utcnow", clock)
    job = poll(client, submit(client)["id"])[-1]

    clock.advance(timedelta(hours=24) - timedelta(seconds=1))
    before = client.get(f"/api/v1/jobs/{job['id']}")
    clock.advance(timedelta(seconds=1))
    after = client.get(f"/api/v1/jobs/{job['id']}")

    assert before.status_code == 200
    assert before.json() == job
    assert after.status_code == 404
    assert after.headers["content-type"] == PROBLEM


def test_two_workers_by_default(gate: Path, client: TestClient) -> None:
    jobs = [submit(client) for _ in range(2)]

    for job in jobs:
        poll(client, job["id"], until=("running",))

    statuses = [client.get(f"/api/v1/jobs/{job['id']}").json()["status"] for job in jobs]
    assert statuses == ["running", "running"]
    gate.touch()


def test_an_invalid_setting_stops_the_app(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PANTHER_API_JOB_WORKERS", "0")

    with pytest.raises(ValidationError), TestClient(create_app()):
        pass


# The csnp job: validated at submit, then 501 until the engine's scoring is wired in.

CSNP_INPUT: dict[str, object] = {
    "sequence": "MKVLWAALLV",
    "substitutions": ["L4P"],
    "species": "HUMAN",
}
CSNP_LOC = ["body", "csnp", "input"]


def csnp_job(**changes: object) -> dict[str, object]:
    return {"service": "csnp", "input": {**CSNP_INPUT, **changes}}


def assert_rejected(client: TestClient, body: object, locs: list[list[str | int]]) -> None:
    """A 422 validation problem at exactly `locs`, without `xyzzy`, and no job stored."""
    response = client.post("/api/v1/jobs", json=body)

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM
    assert sorted(str(error["loc"]) for error in response.json()["errors"]) == sorted(
        str(loc) for loc in locs
    )
    assert "xyzzy" not in response.text.lower()
    assert len(runner(client).store) == 0


def test_an_invalid_species_is_a_422_without_the_value(client: TestClient) -> None:
    assert_rejected(client, csnp_job(species="xyzzy;id"), [[*CSNP_LOC, "species"]])


@pytest.mark.parametrize(
    ("changes", "loc"),
    [
        ({"sequence": ">xyzzy\nMKV\n>xyzzy\nMKV"}, ["sequence"]),
        ({"sequence": "MKV xyzzyÄ"}, ["sequence"]),
        ({"substitutions": ["L4P", "xyzzy xyzzy"]}, ["substitutions", 1]),
        ({"substitutions": "xyzzy"}, ["substitutions"]),
        ({"species": "XYZZY1"}, ["species"]),
    ],
    ids=[
        "two sequences",
        "not ascii",
        "token with a space",
        "substitutions not a list",
        "species too long",
    ],
)
def test_each_invalid_csnp_field_is_a_422_without_the_value(
    client: TestClient, changes: dict[str, object], loc: list[str | int]
) -> None:
    assert_rejected(client, csnp_job(**changes), [[*CSNP_LOC, *loc]])


def test_every_invalid_csnp_field_is_listed(client: TestClient) -> None:
    body: dict[str, object] = {"service": "csnp", "input": {"sequence": "", "substitutions": []}}

    assert_rejected(
        client,
        body,
        [[*CSNP_LOC, "sequence"], [*CSNP_LOC, "substitutions"], [*CSNP_LOC, "species"]],
    )


def test_a_field_the_csnp_input_doesnt_take_is_a_422(client: TestClient) -> None:
    assert_rejected(client, csnp_job(organism="XYZZY"), [[*CSNP_LOC, "organism"]])


def test_a_valid_csnp_request_is_a_501_and_creates_no_job(client: TestClient) -> None:
    response = client.post("/api/v1/jobs", json=csnp_job())

    assert response.status_code == 501
    assert response.headers["content-type"] == PROBLEM
    assert "location" not in response.headers
    assert response.json() == {
        "type": "about:blank",
        "title": "Not Implemented",
        "status": 501,
        "detail": "cSNP scoring isn't available yet.",
    }
    assert len(runner(client).store) == 0


def test_tools_jobs_still_run_after_a_501(client: TestClient) -> None:
    assert client.post("/api/v1/jobs", json=csnp_job()).status_code == 501

    job = poll(client, submit(client)["id"])[-1]

    assert job["status"] == "succeeded"
    assert len(runner(client).store) == 1


def test_run_job_refuses_a_csnp_request() -> None:
    request = CsnpJobRequest(service="csnp", input=CsnpInput.model_validate(CSNP_INPUT))

    with pytest.raises(NotImplementedError):
        run_job(request)
