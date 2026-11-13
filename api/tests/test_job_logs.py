"""Each job's lines in the log (openspec change add-api-logging; scoring-jobs: One line for each
finished job, The size of a job's input, A job's submission is logged at DEBUG, An unexpected
error's traceback is logged once in ten minutes, A refused submission is logged)."""

import logging
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from clock import Clock
from fastapi.testclient import TestClient
from job_helpers import (
    GATE_VARIABLE,
    INPUT_ERROR_MESSAGE,
    exit_worker,
    fail,
    fail_differently,
    fail_elsewhere,
    fail_with_a_new_message,
    no_hmm_hit,
    raise_input_error,
    score_with_a_fake_engine,
    wait_for_gate,
)
from polling import Job, submit_and_wait

from panther_api.jobs.runner import INPUT_ERROR_OUTCOME, REFUSAL_INTERVAL, TRACEBACK_INTERVAL
from panther_api.jobs.work import UNAVAILABLE
from panther_api.main import create_app

RUNNER = "panther_api.jobs.runner"
TOOLS_JOB: dict[str, object] = {"service": "tools", "input": {}}
# 347 residues and 3 substitutions; none of them may reach the log.
SEQUENCE = ("ACDEFGHIKLMNPQRSTVWY" * 18)[:347]
SUBSTITUTIONS = ["A1C", "C2D", "D3E"]
CSNP_JOB: dict[str, object] = {
    "service": "csnp",
    "input": {"sequence": SEQUENCE, "substitutions": SUBSTITUTIONS, "species": "HUMAN"},
}


@pytest.fixture
def debug_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("PANTHER_API_LOG_LEVEL", "DEBUG")
    with TestClient(create_app()) as client:
        yield client


def run(client: TestClient, body: object = TOOLS_JOB) -> Job:
    return submit_and_wait(client, body)


def job_records(caplog: pytest.LogCaptureFixture, job: Job) -> list[logging.LogRecord]:
    return [
        record
        for record in caplog.records
        if record.name == RUNNER and record.getMessage().startswith(f"Job {job['id']} ")
    ]


def runner_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == RUNNER]


# One line for each finished job.


def test_a_job_that_succeeds_has_one_info_line(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    job = run(client)

    [record] = job_records(caplog, job)
    assert record.levelno == logging.INFO
    message = record.getMessage()
    assert message.startswith(f"Job {job['id']} tools: succeeded, waited ")
    assert message.endswith(" s")
    assert ", ran " in message
    assert record.exc_info is None


def test_a_csnp_job_line_has_its_size_and_none_of_its_input(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", score_with_a_fake_engine)

    job = run(client, CSNP_JOB)

    assert job["status"] == "succeeded"
    [record] = job_records(caplog, job)
    assert record.getMessage().startswith(
        f"Job {job['id']} csnp, HUMAN, 347 residues, 3 substitutions: succeeded, waited "
    )
    assert SEQUENCE[:20] not in caplog.text
    for substitution in SUBSTITUTIONS:
        assert substitution not in caplog.text


def test_an_hmmscore_job_line_has_its_residues_and_not_its_sequence(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    # The router answers 501 until hmmscore's scoring is wired in: lift it for this job, and stand
    # in for the work. 317 residues and a final stop, which isn't one.
    monkeypatch.delitem(UNAVAILABLE, "hmmscore")
    monkeypatch.setattr("panther_api.jobs.runner.run_job", no_hmm_hit)
    body = {"service": "hmmscore", "input": {"sequence": SEQUENCE[:317] + "*"}}

    job = run(client, body)

    assert job["status"] == "succeeded"
    assert job["result"] == {"hit": None}
    [record] = job_records(caplog, job)
    assert record.getMessage().startswith(f"Job {job['id']} hmmscore, 317 residues: succeeded, ")
    assert SEQUENCE[:20] not in caplog.text


def test_a_job_that_fails_on_its_input_has_one_info_line_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", raise_input_error)

    job = run(client)

    [record] = job_records(caplog, job)
    assert record.levelno == logging.INFO
    assert f"tools: {INPUT_ERROR_OUTCOME}, waited " in record.getMessage()
    assert record.exc_info is None
    # The message is the user's; the job has it, the log doesn't.
    assert job["error"]["detail"] == INPUT_ERROR_MESSAGE
    assert INPUT_ERROR_MESSAGE not in caplog.text


def test_a_job_that_fails_unexpectedly_has_one_error_line_with_the_traceback(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", fail)

    job = run(client)

    [record] = job_records(caplog, job)
    assert record.levelno == logging.ERROR
    assert "tools: failed 500, waited " in record.getMessage()
    assert record.exc_info is not None
    assert "failed reading" in caplog.text


def test_a_dead_worker_has_one_error_line(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", exit_worker)

    job = run(client)

    [record] = job_records(caplog, job)
    assert record.levelno == logging.ERROR
    assert "tools: failed 500, the worker stopped, waited " in record.getMessage()


# The submission, at DEBUG.


def test_at_info_a_job_has_only_its_finish_line(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    job = run(client)

    assert [record.levelno for record in job_records(caplog, job)] == [logging.INFO]


def test_at_debug_the_submission_comes_first(
    debug_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    job = run(debug_client)

    submitted, finished = job_records(caplog, job)
    assert submitted.levelno == logging.DEBUG
    assert submitted.getMessage() == f"Job {job['id']} tools: submitted"
    assert finished.levelno == logging.INFO
    assert "succeeded" in finished.getMessage()


def test_a_request_that_creates_no_job_logs_no_submission(
    debug_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    invalid = debug_client.post("/api/v1/jobs", json={"service": "tools", "input": {"x": 1}})
    # HUMAN isn't an organism refmap maps for.
    unknown = debug_client.post(
        "/api/v1/jobs", json={"service": "refmap", "input": {"organism": "HUMAN", "ids": ["P1"]}}
    )

    assert (invalid.status_code, unknown.status_code) == (422, 422)
    assert runner_records(caplog) == []


@pytest.fixture
def gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    path = tmp_path / "gate"
    monkeypatch.setenv(GATE_VARIABLE, str(path))
    monkeypatch.setattr("panther_api.jobs.runner.run_job", wait_for_gate)
    yield path
    path.touch()


def test_a_full_queue_logs_a_warning_and_no_submission(
    monkeypatch: pytest.MonkeyPatch, gate: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("PANTHER_API_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("PANTHER_API_JOB_WORKERS", "1")
    monkeypatch.setenv("PANTHER_API_MAX_QUEUED_JOBS", "0")
    with TestClient(create_app()) as client:
        accepted = client.post("/api/v1/jobs", json=TOOLS_JOB)
        refused = client.post("/api/v1/jobs", json=TOOLS_JOB)
        gate.touch()

    assert (accepted.status_code, refused.status_code) == (202, 503)
    submitted = [r for r in runner_records(caplog) if r.getMessage().endswith(": submitted")]
    assert len(submitted) == 1
    [warning] = [r for r in runner_records(caplog) if r.levelno == logging.WARNING]
    assert warning.getMessage() == (
        "Refused a tools job: the queue is full, with 1 jobs running or waiting and a cap of 0 "
        "waiting"
    )


def test_refusals_are_logged_at_most_once_a_minute(
    monkeypatch: pytest.MonkeyPatch, gate: Path, caplog: pytest.LogCaptureFixture
) -> None:
    clock = Clock()
    monkeypatch.setattr("panther_api.jobs.store.utcnow", clock)
    monkeypatch.setenv("PANTHER_API_JOB_WORKERS", "1")
    monkeypatch.setenv("PANTHER_API_MAX_QUEUED_JOBS", "0")
    with TestClient(create_app()) as client:
        accepted = client.post("/api/v1/jobs", json=TOOLS_JOB)
        refused = [client.post("/api/v1/jobs", json=TOOLS_JOB).status_code for _ in range(3)]
        clock.advance(REFUSAL_INTERVAL)
        refused.append(client.post("/api/v1/jobs", json=TOOLS_JOB).status_code)
        gate.touch()

    assert accepted.status_code == 202
    assert refused == [503] * 4
    queue = "the queue is full, with 1 jobs running or waiting and a cap of 0 waiting"
    warnings = [r.getMessage() for r in runner_records(caplog) if r.levelno == logging.WARNING]
    assert warnings == [
        f"Refused a tools job: {queue}",
        f"Refused 3 jobs since 2026-10-29T12:00:00Z, the last a tools job: {queue}",
    ]


# A traceback once in ten minutes.


def test_a_repeated_error_names_the_job_with_the_traceback(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", fail)

    first = run(client)
    second = run(client)
    third = run(client)

    [first_line] = job_records(caplog, first)
    [second_line] = job_records(caplog, second)
    [third_line] = job_records(caplog, third)
    assert first_line.exc_info is not None
    assert second_line.exc_info is None
    assert third_line.exc_info is None
    assert second_line.levelno == logging.ERROR
    assert f"(same error as job {first['id']}, seen 2 times since " in second_line.getMessage()
    assert f"(same error as job {first['id']}, seen 3 times since " in third_line.getMessage()


def test_a_different_error_gets_its_own_traceback(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", fail)
    first = run(client)
    monkeypatch.setattr("panther_api.jobs.runner.run_job", fail_differently)

    second = run(client)

    [first_line] = job_records(caplog, first)
    [second_line] = job_records(caplog, second)
    assert first_line.exc_info is not None
    assert second_line.exc_info is not None
    assert "same error" not in second_line.getMessage()


def test_an_error_whose_message_varies_is_the_same_error(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", fail_with_a_new_message)

    first = run(client)
    second = run(client)

    [first_line] = job_records(caplog, first)
    [second_line] = job_records(caplog, second)
    assert first_line.exc_info is not None
    assert second_line.exc_info is None
    assert f"(same error as job {first['id']}, seen 2 times since " in second_line.getMessage()


def test_the_same_message_raised_elsewhere_is_another_error(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr("panther_api.jobs.runner.run_job", fail)
    first = run(client)
    monkeypatch.setattr("panther_api.jobs.runner.run_job", fail_elsewhere)

    second = run(client)

    [first_line] = job_records(caplog, first)
    [second_line] = job_records(caplog, second)
    assert first_line.exc_info is not None
    assert second_line.exc_info is not None
    assert "same error" not in second_line.getMessage()


def test_after_ten_minutes_the_traceback_is_logged_again(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    clock = Clock()
    monkeypatch.setattr("panther_api.jobs.store.utcnow", clock)
    monkeypatch.setattr("panther_api.jobs.runner.run_job", fail)

    first = run(client)
    clock.advance(TRACEBACK_INTERVAL - timedelta(seconds=1))
    repeat = run(client)
    clock.advance(timedelta(seconds=1))
    again = run(client)
    later = run(client)

    [repeat_line] = job_records(caplog, repeat)
    [again_line] = job_records(caplog, again)
    [later_line] = job_records(caplog, later)
    assert f"same error as job {first['id']}" in repeat_line.getMessage()
    assert repeat_line.exc_info is None
    assert again_line.exc_info is not None
    assert "same error" not in again_line.getMessage()
    assert f"(same error as job {again['id']}, seen 2 times since " in later_line.getMessage()
