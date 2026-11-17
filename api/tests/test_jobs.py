import asyncio
import json
import logging
import pickle
import time
from collections.abc import Awaitable, Callable, Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any, cast, get_args
from uuid import UUID, uuid4

import panther_engine.csnp as engine_csnp
import pytest
from clock import Clock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from job_helpers import (
    FAILING_SEQUENCE,
    FAKE_AGE,
    FAKE_FAMILY,
    FAKE_MESSAGE,
    FAKE_PDEL,
    FAKE_RESULT,
    GATE_VARIABLE,
    INPUT_ERROR_MESSAGE,
    INTERNAL_PATH,
    exit_worker,
    fail,
    fake_score,
    hold_hmmscore_jobs,
    input_error_for_csnp,
    raise_input_error,
    report_fake_tools,
    score_with_a_fake_engine,
    wait_for_gate,
)
from panther_engine.core.errors import InputError
from panther_engine.core.tools import ToolReport
from polling import poll
from pydantic import ValidationError

from panther_api.jobs.csnp import CsnpInput, CsnpResult, SubstitutionScore, run_csnp
from panther_api.jobs.hmmscore import HmmscoreInput
from panther_api.jobs.models import JobStatus
from panther_api.jobs.refmap import MOST_IDS
from panther_api.jobs.runner import (
    INPUT_ERROR_OUTCOME,
    UNEXPECTED_JOB_DETAIL,
    WORKER_STOPPED_DETAIL,
    JobRunner,
    QueueFullError,
)
from panther_api.jobs.store import JobRecord
from panther_api.jobs.tools import ToolsInput, run_tools
from panther_api.jobs.work import (
    SERVICES,
    CsnpJobRequest,
    HmmscoreJobRequest,
    JobRequest,
    Service,
    ToolsJobRequest,
    run_job,
)
from panther_api.main import create_app
from panther_api.problems import MOST_FIELD_ERRORS
from panther_api.versions import read_versions

# The directory in conftest's fake report paths. No job may contain it.
FAKE_TOOLS_DIR = "fake-tools"
PROBLEM = "application/problem+json"
TOOLS_JOB: dict[str, object] = {"service": "tools", "input": {}}
STATUS_ORDER = ["queued", "running", "succeeded"]

Job = dict[str, Any]


def submit(client: TestClient, body: object = TOOLS_JOB) -> Job:
    response = client.post("/api/v1/jobs", json=body)
    assert response.status_code == 202, response.text
    return response.json()


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
    # The versions report's, with no data: a tools job reads none.
    assert job["versions"] == {**client.get("/api/v1/versions").json(), "data": []}


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


# Input errors: the engine's InputError, raised in a real worker.


def test_an_input_error_fails_the_job_with_a_422_and_its_message(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", raise_input_error)
    caplog.set_level(logging.INFO, logger="panther_api.jobs.runner")

    job = poll(client, submit(client)["id"])[-1]

    assert job["status"] == "failed"
    assert job["result"] is None
    assert job["error"] == {
        "type": "about:blank",
        "title": "Unprocessable Content",
        "status": 422,
        "detail": INPUT_ERROR_MESSAGE,
    }
    assert "Traceback" not in str(job)
    assert "InputError" not in str(job)
    [record] = [
        record
        for record in caplog.records
        if record.name == "panther_api.jobs.runner" and job["id"] in record.getMessage()
    ]
    assert record.levelno == logging.INFO
    # The message is for the user: the job has it, the log has a fixed outcome instead.
    assert INPUT_ERROR_OUTCOME in record.getMessage()
    assert INPUT_ERROR_MESSAGE not in caplog.text
    assert record.exc_info is None


def test_other_jobs_keep_running_after_an_input_error(
    monkeypatch: pytest.MonkeyPatch, gate: Path, client: TestClient
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", input_error_for_csnp)
    running = submit(client)
    poll(client, running["id"], until=("running",))

    failed = poll(client, submit(client, csnp_job())["id"])[-1]
    gate.touch()
    succeeded = poll(client, running["id"])[-1]

    assert (failed["status"], failed["error"]["status"]) == ("failed", 422)
    assert succeeded["status"] == "succeeded"


def test_any_other_error_is_still_the_generic_500(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", fail)

    job = poll(client, submit(client)["id"])[-1]

    assert job["error"]["status"] == 500
    assert job["error"]["detail"] == UNEXPECTED_JOB_DETAIL


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


# The csnp job: validated at submit, then scored in a worker by the engine.

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


def test_a_species_the_engine_doesnt_score_is_a_422_without_the_value(
    client: TestClient,
) -> None:
    # The shape of a species code, but not a species in cSNP's data.
    assert_rejected(client, csnp_job(species="XYZZY"), [[*CSNP_LOC, "species"]])


def test_run_csnp_converts_to_and_from_the_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[engine_csnp.CsnpInput] = []

    def score(
        request: engine_csnp.CsnpInput, *, data_dir: Path | str | None = None
    ) -> engine_csnp.CsnpResult:
        seen.append(request)
        return engine_csnp.CsnpResult(
            "PTHR10366",
            (
                engine_csnp.SubstitutionScore("A10E", 220, "possibly damaging", "0.50"),
                engine_csnp.SubstitutionScore(
                    "M1V", None, "Not scored: Invalid substitution", None
                ),
            ),
        )

    monkeypatch.setattr("panther_engine.csnp.score", score)
    request = CsnpInput.model_validate(
        {"sequence": ">sp|P26439\nmgws\nclvt", "substitutions": ["a10e", "M1V"], "species": "HUMAN"}
    )

    result = run_csnp(request)

    assert seen == [engine_csnp.CsnpInput("MGWSCLVT", ("A10E", "M1V"), "HUMAN")]
    assert result == CsnpResult(
        family="PTHR10366",
        scores=[
            SubstitutionScore(
                substitution="A10E", age=220, message="possibly damaging", pdel="0.50"
            ),
            SubstitutionScore(
                substitution="M1V", age=None, message="Not scored: Invalid substitution", pdel=None
            ),
        ],
    )


def test_run_csnp_keeps_a_null_family(monkeypatch: pytest.MonkeyPatch) -> None:
    no_hit = engine_csnp.SubstitutionScore(
        "A10E", None, "Not scored: No PANTHER family for input sequence", None
    )

    def score(_request: engine_csnp.CsnpInput, **_options: object) -> engine_csnp.CsnpResult:
        return engine_csnp.CsnpResult(None, (no_hit,))

    monkeypatch.setattr("panther_engine.csnp.score", score)

    result = run_csnp(CsnpInput.model_validate(CSNP_INPUT))

    assert result.family is None
    assert result.scores[0].message == no_hit.message


def test_run_csnp_passes_the_engines_errors_on(monkeypatch: pytest.MonkeyPatch) -> None:
    def score(_request: engine_csnp.CsnpInput, **_options: object) -> engine_csnp.CsnpResult:
        raise InputError("The sequence can't be read.")

    monkeypatch.setattr("panther_engine.csnp.score", score)

    with pytest.raises(InputError):
        run_csnp(CsnpInput.model_validate(CSNP_INPUT))


def test_run_job_runs_the_csnp_job(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("panther_engine.csnp.score", fake_score)
    request = CsnpJobRequest(service="csnp", input=CsnpInput.model_validate(CSNP_INPUT))

    assert run_job(request) == run_csnp(request.input)


def test_a_csnp_job_succeeds_with_the_engines_scores(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", score_with_a_fake_engine)
    body = csnp_job(substitutions=["l4p", "W5R"])

    response = client.post("/api/v1/jobs", json=body)
    assert response.status_code == 202
    assert response.json()["service"] == "csnp"
    job = poll(client, response.json()["id"])[-1]

    assert job["status"] == "succeeded"
    assert job["error"] is None
    assert job["result"] == {
        "family": FAKE_FAMILY,
        "scores": [
            {"substitution": token, "age": FAKE_AGE, "message": FAKE_MESSAGE, "pdel": FAKE_PDEL}
            for token in ["L4P", "W5R"]
        ],
    }
    # The versions report's, with only cSNP's data.
    assert job["versions"] == {
        **client.get("/api/v1/versions").json(),
        "data": [{"service": "csnp", "panther": "9"}],
    }


# The refmap job: validated, then mapped by the engine in a worker.

REFMAP_INPUT: dict[str, object] = {"organism": "ENDPU", "ids": ["U1G4Q5", "P04217"]}
REFMAP_LOC = ["body", "refmap", "input"]


def refmap_job(**changes: object) -> dict[str, object]:
    return {"service": "refmap", "input": {**REFMAP_INPUT, **changes}}


def test_an_invalid_organism_is_a_422_without_the_value(client: TestClient) -> None:
    assert_rejected(client, refmap_job(organism="xyzzy|"), [[*REFMAP_LOC, "organism"]])


def test_an_organism_refmap_doesnt_map_for_is_a_422(client: TestClient) -> None:
    # PANTHER's own genomes aren't in the generic mapping data (#52).
    assert_rejected(client, refmap_job(organism="HUMAN"), [[*REFMAP_LOC, "organism"]])


@pytest.mark.parametrize(
    ("changes", "loc"),
    [
        ({"organism": "../xyzzy"}, ["organism"]),
        ({"organism": "Homo_sapiens_XYZZY"}, ["organism"]),
        ({"ids": ["P04217", "xyzzy xyzzy"]}, ["ids", 1]),
        ({"ids": ["xyzzy\tvalue"]}, ["ids", 0]),
        ({"ids": ["P04217", "xyzzy" * 13]}, ["ids", 1]),
        ({"ids": "xyzzy"}, ["ids"]),
    ],
    ids=["a path", "a long name", "two ids in one", "a tab", "too long", "ids not a list"],
)
def test_each_invalid_refmap_field_is_a_422_without_the_value(
    client: TestClient, changes: dict[str, object], loc: list[str | int]
) -> None:
    assert_rejected(client, refmap_job(**changes), [[*REFMAP_LOC, *loc]])


def test_every_invalid_refmap_field_is_listed(client: TestClient) -> None:
    body: dict[str, object] = {"service": "refmap", "input": {"ids": []}}

    assert_rejected(client, body, [[*REFMAP_LOC, "organism"], [*REFMAP_LOC, "ids"]])


def test_a_422_for_every_id_lists_the_first_100(client: TestClient) -> None:
    response = client.post("/api/v1/jobs", json=refmap_job(ids=[""] * MOST_IDS))

    assert response.status_code == 422
    body = response.json()
    assert [error["loc"] for error in body["errors"]] == [
        [*REFMAP_LOC, "ids", index] for index in range(MOST_FIELD_ERRORS)
    ]
    assert body["detail"] == (
        "Request validation failed: 100,000 fields are invalid, and the first 100 are listed."
    )
    assert len(response.content) < 20_000
    assert len(runner(client).store) == 0


def test_a_bad_organism_and_every_bad_id_are_counted(client: TestClient) -> None:
    body = {"service": "refmap", "input": {"organism": "HUMAN", "ids": [""] * MOST_IDS}}

    response = client.post("/api/v1/jobs", json=body)

    assert response.status_code == 422
    errors = response.json()["errors"]
    assert [error["loc"] for error in errors] == [
        [*REFMAP_LOC, "organism"],
        *([*REFMAP_LOC, "ids", index] for index in range(MOST_FIELD_ERRORS - 1)),
    ]
    assert response.json()["detail"] == (
        "Request validation failed: 100,001 fields are invalid, and the first 100 are listed."
    )


def test_many_bad_ids_are_rejected_about_as_fast_as_valid_ones(client: TestClient) -> None:
    # The valid IDs are for an organism refmap doesn't map for, so both are 422s. Each is timed
    # at its best of four, after one to warm up, in the same process (#41). Pydantic's own check
    # took about seven times the valid list's time; the bound is loose, a ratio of 3 plus 0.1 s,
    # so a loaded runner doesn't fail it, and still catches that.
    bad = json.dumps(refmap_job(ids=[""] * MOST_IDS)).encode()
    valid = json.dumps(
        refmap_job(organism="ZZZZZ", ids=[f"P{index:05d}" for index in range(MOST_IDS)])
    ).encode()

    def best(body: bytes) -> float:
        times: list[float] = []
        for _ in range(5):
            start = time.perf_counter()
            response = client.post(
                "/api/v1/jobs", content=body, headers={"content-type": "application/json"}
            )
            times.append(time.perf_counter() - start)
            assert response.status_code == 422
        return min(times[1:])

    assert best(bad) <= 3 * best(valid) + 0.1


def test_a_field_the_refmap_input_doesnt_take_is_a_422(client: TestClient) -> None:
    assert_rejected(client, refmap_job(fileContents="XYZZY"), [[*REFMAP_LOC, "fileContents"]])


def test_a_valid_refmap_request_starts_a_job(client: TestClient) -> None:
    response = client.post("/api/v1/jobs", json=refmap_job())

    assert response.status_code == 202, response.text
    job = response.json()
    assert job["service"] == "refmap"
    assert response.headers["location"] == f"/api/v1/jobs/{job['id']}"
    assert len(runner(client).store) == 1


def test_a_refmap_job_without_the_data_fails_with_the_generic_500(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # The real work, not the autouse fake; the data folder set before the app starts, as the
    # workers start with the first job and inherit it.
    monkeypatch.setattr("panther_api.jobs.runner.run_job", run_job)
    monkeypatch.setenv("PANTHER_DATA_DIR", str(tmp_path))
    with TestClient(create_app()) as client:
        job = poll(client, client.post("/api/v1/jobs", json=refmap_job()).json()["id"])[-1]

    assert job["status"] == "failed"
    assert job["result"] is None
    assert job["error"]["status"] == 500
    assert str(tmp_path) not in str(job)


# The hmmscore job: validated, the configured residue limit checked, then a 501 until the engine
# scores. No hit is made up.

HMMSCORE_SEQUENCE = "MKVLWAALLVTFLAGCQAKV"
HMMSCORE_LOC: list[str | int] = ["body", "hmmscore", "input", "sequence"]
HMMSCORE_UNAVAILABLE = {
    "type": "about:blank",
    "title": "Not Implemented",
    "status": 501,
    "detail": "HMM scoring isn't available yet.",
}


def hmmscore_job(sequence: object = HMMSCORE_SEQUENCE, **changes: object) -> dict[str, object]:
    return {"service": "hmmscore", "input": {"sequence": sequence, **changes}}


def assert_unavailable(client: TestClient, body: object) -> None:
    """Valid: the 501 problem, with no `Location`, and no job stored."""
    response = client.post("/api/v1/jobs", json=body)

    assert response.status_code == 501, response.text
    assert response.headers["content-type"] == PROBLEM
    assert "location" not in response.headers
    assert response.json() == HMMSCORE_UNAVAILABLE
    assert len(runner(client).store) == 0


def assert_over_the_residue_limit(client: TestClient, residues: int, limit: str) -> None:
    """A 422 on `sequence` naming the limit, without the sequence, and no job stored."""
    response = client.post("/api/v1/jobs", json=hmmscore_job("W" * residues))

    assert response.status_code == 422
    assert response.headers["content-type"] == PROBLEM
    [error] = response.json()["errors"]
    assert error["loc"] == HMMSCORE_LOC
    assert error["msg"] == f"The sequence has more than {limit} residues."
    assert "WWWWWWWWWW" not in response.text
    assert len(runner(client).store) == 0


def test_a_valid_hmmscore_request_is_a_501_and_creates_no_job(client: TestClient) -> None:
    assert_unavailable(client, hmmscore_job())


def test_a_fasta_hmmscore_request_with_a_final_stop_is_a_501(client: TestClient) -> None:
    assert_unavailable(client, hmmscore_job(">sp|P02649|APOE_HUMAN\nmkvlwaallv\ntflagcqakv*\n"))


def test_dots_underscores_tildes_and_inner_stops_are_a_501(client: TestClient) -> None:
    assert_unavailable(client, hmmscore_job("MKV.LW_AA~LL*VT"))


def test_tools_jobs_still_run_after_an_hmmscore_501(client: TestClient) -> None:
    assert client.post("/api/v1/jobs", json=hmmscore_job()).status_code == 501

    job = poll(client, submit(client)["id"])[-1]

    assert job["status"] == "succeeded"
    assert len(runner(client).store) == 1


def test_two_hmmscore_sequences_are_a_422_without_the_residues(client: TestClient) -> None:
    response = client.post("/api/v1/jobs", json=hmmscore_job(">one\nMKVQWERTY\n>two\nMKV"))

    assert response.status_code == 422
    assert [error["loc"] for error in response.json()["errors"]] == [HMMSCORE_LOC]
    assert "MKVQWERTY" not in response.text
    assert len(runner(client).store) == 0


@pytest.mark.parametrize(
    "sequence",
    [">xyzzy\nMKV1XYZZY", "MKV-XYZZY", "MKV+XYZZY", ">only a header xyzzy\n*", "", 12345],
    ids=["digit", "dash", "plus", "a stop with no residues", "empty", "not a string"],
)
def test_each_invalid_hmmscore_sequence_is_a_422_without_the_value(
    client: TestClient, sequence: object
) -> None:
    assert_rejected(client, hmmscore_job(sequence), [HMMSCORE_LOC])


def test_no_hmmscore_sequence_is_a_422(client: TestClient) -> None:
    assert_rejected(client, {"service": "hmmscore", "input": {}}, [HMMSCORE_LOC])


@pytest.mark.parametrize("sequence", ["*", ".~_", ">only a header xyzzy\n*"])
def test_an_hmmscore_sequence_with_no_letters_has_no_residues(
    client: TestClient, sequence: str
) -> None:
    response = client.post("/api/v1/jobs", json=hmmscore_job(sequence))

    assert response.status_code == 422
    [error] = response.json()["errors"]
    assert (error["loc"], error["msg"]) == (HMMSCORE_LOC, "The sequence has no residues.")
    assert "xyzzy" not in response.text
    assert len(runner(client).store) == 0


def test_a_field_the_hmmscore_input_doesnt_take_is_a_422(client: TestClient) -> None:
    # The website's form sent `opType` beside the sequence.
    assert_rejected(client, hmmscore_job(opType="hmm"), [["body", "hmmscore", "input", "opType"]])


def test_the_default_residue_limit_takes_10000(client: TestClient) -> None:
    assert_unavailable(client, hmmscore_job("W" * 10_000))


def test_a_final_stop_isnt_counted_toward_the_limit(client: TestClient) -> None:
    assert_unavailable(client, hmmscore_job("W" * 10_000 + "*"))


def test_dots_and_inner_stops_count_toward_the_limit(client: TestClient) -> None:
    # Every position hmmscan reads counts, but a final `*` (engine developer, 2026-11-13).
    assert_unavailable(client, hmmscore_job("W" * 9_997 + ".*~" + "*"))

    response = client.post("/api/v1/jobs", json=hmmscore_job("W" * 9_998 + ".*~"))

    assert response.status_code == 422
    [error] = response.json()["errors"]
    assert error["msg"] == "The sequence has more than 10,000 residues."


def test_past_the_default_residue_limit_is_a_422_naming_it(client: TestClient) -> None:
    assert_over_the_residue_limit(client, 10_001, "10,000")


def test_a_lower_residue_limit_the_server_sets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PANTHER_API_HMMSCORE_MAX_RESIDUES", "5000")
    with TestClient(create_app()) as client:
        assert_unavailable(client, hmmscore_job("W" * 5_000))
        assert_over_the_residue_limit(client, 5_001, "5,000")


def test_the_residue_limit_counts_after_normalising(client: TestClient) -> None:
    # 10,000 residues in lines of 50, after a header.
    sequence = ">header\n" + "\n".join(["W" * 50] * 200)

    assert_unavailable(client, hmmscore_job(sequence))


def test_run_job_refuses_an_hmmscore_job() -> None:
    request = HmmscoreJobRequest(
        service="hmmscore", input=HmmscoreInput.model_validate({"sequence": HMMSCORE_SEQUENCE})
    )

    with pytest.raises(NotImplementedError):
        run_job(request)


# The cap on hmmscore jobs running at once, on a JobRunner, since the router answers 501
# (openspec add-hmmscore-job, design.md, decision 6). hold_hmmscore_jobs() stands in for the work.

HOLD_TIMEOUT = 60.0


def hmmscore_request(sequence: str = HMMSCORE_SEQUENCE) -> HmmscoreJobRequest:
    return HmmscoreJobRequest(
        service="hmmscore", input=HmmscoreInput.model_validate({"sequence": sequence})
    )


async def until(job: JobRecord, *statuses: JobStatus) -> None:
    """Wait on the loop until the job's status is one of `statuses`."""
    deadline = time.monotonic() + HOLD_TIMEOUT
    while job.status not in statuses:
        assert time.monotonic() < deadline, f"job still {job.status}"
        await asyncio.sleep(0.02)


async def stays_queued(job: JobRecord) -> None:
    """The job is still queued however long the loop turns."""
    for _ in range(10):
        assert job.status == JobStatus.QUEUED
        await asyncio.sleep(0.05)


def run_with_a_capped_runner(
    gate: Path, test: Callable[[JobRunner], Awaitable[None]], *, max_queued: int = 50
) -> None:
    """Run `test` against a JobRunner of 2 workers and a cap of 1 running hmmscore job, as the
    API's defaults give, and `max_queued` waiting, on a loop of its own. The gate opens at the
    end, whatever happens."""

    async def main() -> None:
        jobs = JobRunner(
            workers=2,
            max_queued=max_queued,
            expiry=timedelta(hours=1),
            results_budget=1024 * 1024,
            versions=read_versions(),
            max_running={"hmmscore": 1},
        )
        try:
            await test(jobs)
        finally:
            gate.touch()
            await jobs.close()

    asyncio.run(main())


@pytest.fixture
def hmmscore_gate(gate: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """hmmscore jobs stay running until the gate opens; others succeed at once."""
    monkeypatch.setattr("panther_api.jobs.runner.run_job", hold_hmmscore_jobs)
    return gate


def test_a_second_hmmscore_job_waits_for_the_first(hmmscore_gate: Path) -> None:
    async def test(jobs: JobRunner) -> None:
        first = jobs.submit(hmmscore_request())
        await until(first, JobStatus.RUNNING)
        second = jobs.submit(hmmscore_request())

        # A worker is free, but the cap holds the second.
        await stays_queued(second)

        hmmscore_gate.touch()
        await until(second, JobStatus.SUCCEEDED, JobStatus.FAILED)

        assert (first.status, second.status) == (JobStatus.SUCCEEDED, JobStatus.SUCCEEDED)
        assert first.finished_at is not None
        assert second.started_at is not None
        assert second.started_at >= first.finished_at

    run_with_a_capped_runner(hmmscore_gate, test)


def test_another_service_runs_beside_a_waiting_hmmscore_job(hmmscore_gate: Path) -> None:
    async def test(jobs: JobRunner) -> None:
        running = jobs.submit(hmmscore_request())
        await until(running, JobStatus.RUNNING)
        waiting = jobs.submit(hmmscore_request())
        await stays_queued(waiting)

        tools = jobs.submit(ToolsJobRequest(service="tools", input=ToolsInput()))
        await until(tools, JobStatus.SUCCEEDED, JobStatus.FAILED)

        # The waiting hmmscore job held no worker, so the tools job had the free one.
        assert tools.status == JobStatus.SUCCEEDED
        assert waiting.status == JobStatus.QUEUED
        assert running.status == JobStatus.RUNNING

    run_with_a_capped_runner(hmmscore_gate, test)


def test_a_failed_hmmscore_job_frees_its_place(hmmscore_gate: Path) -> None:
    async def test(jobs: JobRunner) -> None:
        failing = jobs.submit(hmmscore_request(FAILING_SEQUENCE))
        await until(failing, JobStatus.RUNNING)
        waiting = jobs.submit(hmmscore_request())
        await stays_queued(waiting)

        hmmscore_gate.touch()
        await until(waiting, JobStatus.SUCCEEDED, JobStatus.FAILED)

        assert failing.status == JobStatus.FAILED
        assert waiting.status == JobStatus.SUCCEEDED

    run_with_a_capped_runner(hmmscore_gate, test)


# The waiting count, with the cap: a job waiting for the cap waits, though a worker is free.


def tools_request() -> ToolsJobRequest:
    return ToolsJobRequest(service="tools", input=ToolsInput())


def test_hmmscore_jobs_waiting_for_the_cap_count_as_waiting(hmmscore_gate: Path) -> None:
    async def test(jobs: JobRunner) -> None:
        # One runs, and three wait for the cap while the second worker is free.
        accepted = [jobs.submit(hmmscore_request()) for _ in range(4)]

        with pytest.raises(QueueFullError):
            jobs.submit(hmmscore_request())

        assert len(jobs.store) == 4
        await until(accepted[0], JobStatus.RUNNING)
        for job in accepted[1:]:
            assert job.status == JobStatus.QUEUED

    run_with_a_capped_runner(hmmscore_gate, test, max_queued=3)


def test_another_service_runs_beside_a_full_queue_of_hmmscore_jobs(hmmscore_gate: Path) -> None:
    async def test(jobs: JobRunner) -> None:
        held = [jobs.submit(hmmscore_request()) for _ in range(4)]
        with pytest.raises(QueueFullError):
            jobs.submit(hmmscore_request())

        # The free worker runs it, so it adds nothing to the waiting count.
        tools = jobs.submit(tools_request())
        # A second has to wait for a worker, and three already wait.
        with pytest.raises(QueueFullError):
            jobs.submit(tools_request())

        await until(tools, JobStatus.SUCCEEDED, JobStatus.FAILED)
        assert tools.status == JobStatus.SUCCEEDED
        assert [job.status for job in held] == [JobStatus.RUNNING] + [JobStatus.QUEUED] * 3

    run_with_a_capped_runner(hmmscore_gate, test, max_queued=3)


def test_no_waiting_refuses_a_second_hmmscore_job(hmmscore_gate: Path) -> None:
    async def test(jobs: JobRunner) -> None:
        running = jobs.submit(hmmscore_request())

        with pytest.raises(QueueFullError):
            jobs.submit(hmmscore_request())

        # Another service's job still runs on the free worker.
        tools = jobs.submit(tools_request())
        await until(tools, JobStatus.SUCCEEDED, JobStatus.FAILED)
        assert tools.status == JobStatus.SUCCEEDED
        assert running.status == JobStatus.RUNNING
        assert len(jobs.store) == 2

    run_with_a_capped_runner(hmmscore_gate, test, max_queued=0)


def test_a_finished_hmmscore_job_makes_room_in_the_queue(hmmscore_gate: Path) -> None:
    async def test(jobs: JobRunner) -> None:
        first = jobs.submit(hmmscore_request())
        with pytest.raises(QueueFullError):
            jobs.submit(hmmscore_request())

        hmmscore_gate.touch()
        await until(first, JobStatus.SUCCEEDED, JobStatus.FAILED)
        await asyncio.sleep(0.05)
        second = jobs.submit(hmmscore_request())
        await until(second, JobStatus.SUCCEEDED, JobStatus.FAILED)

        assert (first.status, second.status) == (JobStatus.SUCCEEDED, JobStatus.SUCCEEDED)

    run_with_a_capped_runner(hmmscore_gate, test, max_queued=0)


# The cap's keys: only services JobRequest has.


def test_the_services_are_the_job_requests() -> None:
    members = get_args(get_args(JobRequest)[0])

    assert {get_args(member.model_fields["service"].annotation)[0] for member in members} == (
        SERVICES
    )


def test_a_cap_on_a_service_that_doesnt_exist_is_refused() -> None:
    with pytest.raises(ValueError, match="hmmscor"):
        JobRunner(
            workers=2,
            max_queued=50,
            expiry=timedelta(hours=1),
            results_budget=1024 * 1024,
            versions=read_versions(),
            max_running=cast(dict[Service, int], {"hmmscor": 1}),
        )


def test_a_cap_below_one_is_refused() -> None:
    with pytest.raises(ValueError, match="hmmscore"):
        JobRunner(
            workers=2,
            max_queued=50,
            expiry=timedelta(hours=1),
            results_budget=1024 * 1024,
            versions=read_versions(),
            max_running={"hmmscore": 0},
        )
