"""The API's limits for hosting: the request body's size, the jobs that may wait, and the startup
checks of each service's data (openspec changes harden-api-for-hosting and wire-refmap)."""

import asyncio
import json
import logging
import time
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from job_helpers import GATE_VARIABLE, fail, wait_for_gate
from starlette.types import Message, Receive, Scope, Send

from panther_api.jobs.runner import JobRunner
from panther_api.limits import BodyLimit, body_too_large_detail
from panther_api.main import create_app
from panther_api.routers.jobs import QUEUE_FULL_DETAIL, RETRY_AFTER_SECONDS
from panther_api.settings import MAX_BODY_BYTES

PROBLEM = "application/problem+json"
TOOLS_JOB: dict[str, object] = {"service": "tools", "input": {}}
POLL_TIMEOUT = 60.0
SMALL_LIMIT = 1000


def runner(client: TestClient) -> JobRunner:
    return cast(FastAPI, client.app).state.jobs


def poll(client: TestClient, job_id: str, until: tuple[str, ...]) -> str:
    deadline = time.monotonic() + POLL_TIMEOUT
    while True:
        status = client.get(f"/api/v1/jobs/{job_id}").json()["status"]
        if status in until:
            return status
        assert time.monotonic() < deadline, f"job still {status}"
        time.sleep(0.05)


def padded_tools_job(size: int) -> bytes:
    """A valid tools job, padded with JSON whitespace to exactly `size` bytes."""
    body = json.dumps(TOOLS_JOB).encode()
    return body + b" " * (size - len(body))


def assert_too_large(response: Any, limit: int) -> None:
    assert response.status_code == 413
    assert response.headers["content-type"] == PROBLEM
    assert response.json() == {
        "type": "about:blank",
        "title": "Content Too Large",
        "status": 413,
        "detail": body_too_large_detail(limit),
    }
    assert "xyzzy" not in response.text.lower()


# The request body's size.


@pytest.fixture
def small_limit(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("PANTHER_API_MAX_BODY_BYTES", str(SMALL_LIMIT))
    with TestClient(create_app()) as client:
        yield client


def test_a_body_at_the_limit_is_accepted(small_limit: TestClient) -> None:
    response = small_limit.post(
        "/api/v1/jobs",
        content=padded_tools_job(SMALL_LIMIT),
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 202, response.text


def test_a_body_over_the_limit_by_its_length_is_a_413_and_creates_no_job(
    small_limit: TestClient,
) -> None:
    body = padded_tools_job(SMALL_LIMIT)[:-1] + b"xyzzy"

    response = small_limit.post(
        "/api/v1/jobs", content=body, headers={"content-type": "application/json"}
    )

    assert_too_large(response, SMALL_LIMIT)
    assert len(runner(small_limit).store) == 0


def test_a_body_over_the_limit_without_a_length_is_a_413(small_limit: TestClient) -> None:
    def chunks() -> Iterator[bytes]:
        yield padded_tools_job(SMALL_LIMIT)
        yield b"xyzzy"

    response = small_limit.post(
        "/api/v1/jobs", content=chunks(), headers={"content-type": "application/json"}
    )

    assert "content-length" not in response.request.headers
    assert_too_large(response, SMALL_LIMIT)
    assert len(runner(small_limit).store) == 0


def test_a_body_without_a_length_within_the_limit_is_accepted(small_limit: TestClient) -> None:
    def chunks() -> Iterator[bytes]:
        yield json.dumps(TOOLS_JOB).encode()

    response = small_limit.post(
        "/api/v1/jobs", content=chunks(), headers={"content-type": "application/json"}
    )

    assert response.status_code == 202, response.text


def test_the_largest_valid_refmap_request_is_within_the_default(client: TestClient) -> None:
    # 100,000 IDs of 64 characters, each `"` or `\`, so every one is escaped in the JSON.
    body = json.dumps(
        {"service": "refmap", "input": {"organism": "ENDPU", "ids": ['"\\' * 32] * 100_000}}
    ).encode()
    assert len(body) > 13_000_000

    response = client.post(
        "/api/v1/jobs", content=body, headers={"content-type": "application/json"}
    )

    # Read, validated and accepted, not a 413.
    assert response.status_code == 202, response.text


def test_a_body_over_the_default_is_a_413(client: TestClient) -> None:
    response = client.post(
        "/api/v1/jobs",
        content=padded_tools_job(MAX_BODY_BYTES + 1),
        headers={"content-type": "application/json"},
    )

    assert_too_large(response, MAX_BODY_BYTES)
    assert len(runner(client).store) == 0


def test_a_request_without_a_body_is_unaffected(small_limit: TestClient) -> None:
    assert small_limit.get("/api/v1/health").status_code == 200


def run_body_limit(limit: int, chunks: int, chunk: bytes) -> tuple[list[Message], int, bool]:
    """Send `chunks` copies of `chunk` through the middleware alone. What it sent, how many
    chunks it read, and whether the app behind it was called."""
    received = 0
    sent: list[Message] = []
    called = False

    async def receive() -> Message:
        nonlocal received
        received += 1
        return {"type": "http.request", "body": chunk, "more_body": received < chunks}

    async def send(message: Message) -> None:
        sent.append(message)

    async def app(_scope: Scope, _receive: Receive, _send: Send) -> None:
        nonlocal called
        called = True

    state = SimpleNamespace(settings=SimpleNamespace(max_body_bytes=limit))
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/jobs",
        "headers": [],
        "app": SimpleNamespace(state=state),
    }
    asyncio.run(BodyLimit(app)(scope, receive, send))
    return sent, received, called


def test_a_streamed_body_is_refused_once_it_passes_the_limit() -> None:
    # 1,000 chunks of 1,000 bytes against a limit of 2,500: refused on the third.
    sent, received, called = run_body_limit(2_500, 1_000, b"x" * 1_000)

    assert received == 3
    assert not called
    assert sent[0]["type"] == "http.response.start"
    assert sent[0]["status"] == 413


def test_a_streamed_body_within_the_limit_reaches_the_app() -> None:
    sent, received, called = run_body_limit(2_500, 2, b"x" * 1_000)

    assert received == 2
    assert called
    assert sent == []


# The jobs that may wait.


@pytest.fixture
def gate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Jobs stay running until the test creates this file (job_helpers.wait_for_gate)."""
    path = tmp_path / "gate"
    monkeypatch.setenv(GATE_VARIABLE, str(path))
    monkeypatch.setattr("panther_api.jobs.runner.run_job", wait_for_gate)
    yield path
    path.touch()


def test_a_job_past_the_cap_is_a_503_and_creates_no_job(
    monkeypatch: pytest.MonkeyPatch, gate: Path
) -> None:
    monkeypatch.setenv("PANTHER_API_JOB_WORKERS", "1")
    monkeypatch.setenv("PANTHER_API_MAX_QUEUED_JOBS", "2")
    with TestClient(create_app()) as client:
        running = client.post("/api/v1/jobs", json=TOOLS_JOB).json()
        poll(client, running["id"], until=("running",))
        queued = [client.post("/api/v1/jobs", json=TOOLS_JOB) for _ in range(2)]

        refused = client.post("/api/v1/jobs", json=TOOLS_JOB)

        assert [response.status_code for response in queued] == [202, 202]
        assert refused.status_code == 503
        assert refused.headers["content-type"] == PROBLEM
        assert refused.headers["retry-after"] == str(RETRY_AFTER_SECONDS)
        assert "location" not in refused.headers
        assert refused.json() == {
            "type": "about:blank",
            "title": "Service Unavailable",
            "status": 503,
            "detail": QUEUE_FULL_DETAIL,
        }
        assert len(runner(client).store) == 3
        # An invalid request is still validated first.
        invalid = client.post("/api/v1/jobs", json={"service": "tools", "input": {"xyzzy": 1}})
        assert invalid.status_code == 422

        # Once the queue drains, jobs are accepted again.
        gate.touch()
        for response in queued:
            poll(client, response.json()["id"], until=("succeeded",))
        later = client.post("/api/v1/jobs", json=TOOLS_JOB)
        assert later.status_code == 202
        assert poll(client, later.json()["id"], until=("succeeded", "failed")) == "succeeded"


def test_jobs_for_free_workers_dont_count_as_waiting(
    monkeypatch: pytest.MonkeyPatch, gate: Path
) -> None:
    # Two workers and no waiting allowed: two jobs back to back each get a worker; a third waits.
    monkeypatch.setenv("PANTHER_API_MAX_QUEUED_JOBS", "0")
    with TestClient(create_app()) as client:
        first = client.post("/api/v1/jobs", json=TOOLS_JOB)
        second = client.post("/api/v1/jobs", json=TOOLS_JOB)
        third = client.post("/api/v1/jobs", json=TOOLS_JOB)

        assert (first.status_code, second.status_code, third.status_code) == (202, 202, 503)
        gate.touch()


def test_a_failed_job_frees_its_place(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PANTHER_API_JOB_WORKERS", "1")
    monkeypatch.setenv("PANTHER_API_MAX_QUEUED_JOBS", "0")
    monkeypatch.setattr("panther_api.jobs.runner.run_job", fail)
    with TestClient(create_app()) as client:
        for _ in range(3):
            response = client.post("/api/v1/jobs", json=TOOLS_JOB)
            assert response.status_code == 202
            assert poll(client, response.json()["id"], until=("succeeded", "failed")) == "failed"


# The startup checks of each service's data (scoring-jobs: Startup check of the refmap data).


def main_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.name == "panther_api.main"]


def complete(_data_dir: object = None) -> None:
    """A data check that passes."""


def test_missing_data_is_logged_for_each_service_and_the_api_starts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("PANTHER_DATA_DIR", str(tmp_path))

    with TestClient(create_app()) as client:
        health = client.get("/api/v1/health")

    assert health.status_code == 200
    csnp, refmap = main_records(caplog)
    assert (csnp.levelno, refmap.levelno) == (logging.ERROR, logging.ERROR)
    assert "csnp jobs will fail until the cSNP data is in place" in csnp.getMessage()
    assert "refmap jobs will fail until the refmap data is in place" in refmap.getMessage()
    assert str(tmp_path) in csnp.getMessage()
    assert str(tmp_path) in refmap.getMessage()


def test_csnp_data_without_refmap_data_logs_only_refmaps_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("PANTHER_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("panther_engine.csnp.check_data", complete)

    with TestClient(create_app()) as client:
        assert client.get("/api/v1/health").status_code == 200

    [record] = main_records(caplog)
    assert record.levelno == logging.ERROR
    assert record.getMessage().startswith(
        "refmap jobs will fail until the refmap data is in place: "
    )
    # The engine's message: the folder, and how many files are missing.
    assert str(tmp_path) in record.getMessage()
    assert "lacks 1,534 of 1,534 files" in record.getMessage()


def test_refmap_data_without_csnp_data_logs_only_csnps_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("PANTHER_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("panther_engine.refmap.check_data", complete)
    monkeypatch.setattr("panther_engine.refmap.check_classification_json", complete)

    with TestClient(create_app()) as client:
        assert client.get("/api/v1/health").status_code == 200

    [record] = main_records(caplog)
    assert "csnp jobs will fail until the cSNP data is in place" in record.getMessage()


def test_refmap_data_without_its_classification_json_logs_only_that(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("PANTHER_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("panther_engine.csnp.check_data", complete)
    monkeypatch.setattr("panther_engine.refmap.check_data", complete)

    with TestClient(create_app()) as client:
        assert client.get("/api/v1/health").status_code == 200

    [record] = main_records(caplog)
    assert record.levelno == logging.ERROR
    assert record.getMessage().startswith(
        "refmap classifications will fail until the classification JSON is built "
        "(panther-engine refmap data build-json): "
    )
    assert "lacks 1,533 of 1,533 files" in record.getMessage()


def test_an_unset_data_folder_is_logged_and_the_api_starts(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.delenv("PANTHER_DATA_DIR", raising=False)

    with TestClient(create_app()) as client:
        assert client.get("/api/v1/health").status_code == 200

    records = main_records(caplog)
    assert [record.getMessage().split()[0] for record in records] == ["csnp", "refmap"]
    assert all("PANTHER_DATA_DIR" in record.getMessage() for record in records)


def test_complete_data_logs_nothing(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    calls: list[str] = []
    monkeypatch.setattr("panther_engine.csnp.check_data", lambda: calls.append("csnp"))
    monkeypatch.setattr("panther_engine.refmap.check_data", lambda: calls.append("refmap"))
    monkeypatch.setattr(
        "panther_engine.refmap.check_classification_json", lambda: calls.append("json")
    )

    with TestClient(create_app()) as client:
        assert client.get("/api/v1/health").status_code == 200

    assert calls == ["csnp", "refmap", "json"]
    assert main_records(caplog) == []


# The schema.


def test_the_schema_documents_the_413_and_the_503() -> None:
    schema = create_app().openapi()
    responses = schema["paths"]["/api/v1/jobs"]["post"]["responses"]

    for status in ("413", "503"):
        content = responses[status]["content"]
        assert content == {PROBLEM: {"schema": {"$ref": "#/components/schemas/Problem"}}}
    assert "Retry-After" in responses["503"]["headers"]
    # Only an operation with a body can be too large.
    assert "413" not in schema["paths"]["/api/v1/jobs/{job_id}"]["get"]["responses"]
