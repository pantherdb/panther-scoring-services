"""Submitting a job and polling it until it finishes, as the frontend does, through a TestClient.

`serving.Server.run_job` does the same against a real Uvicorn server, over HTTP.
"""

import time
from typing import Any

from fastapi.testclient import TestClient

Job = dict[str, Any]
FINISHED = ("succeeded", "failed")
# A worker's first start under spawn imports pydantic and the engine: about a second.
POLL_TIMEOUT = 60.0


def poll(
    client: TestClient,
    job_id: str,
    until: tuple[str, ...] = FINISHED,
    *,
    timeout: float = POLL_TIMEOUT,
    interval: float = 0.05,
) -> list[Job]:
    """Poll the job until its status is one of `until`. Every answer."""
    deadline = time.monotonic() + timeout
    answers: list[Job] = []
    while True:
        response = client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200, response.text
        answers.append(response.json())
        if answers[-1]["status"] in until:
            return answers
        assert time.monotonic() < deadline, f"job still {answers[-1]['status']}"
        time.sleep(interval)


def submit_and_wait(
    client: TestClient, body: object, *, timeout: float = POLL_TIMEOUT, interval: float = 0.05
) -> Job:
    """Submit a job, expecting a 202, and poll it until it finishes. The finished job."""
    response = client.post("/api/v1/jobs", json=body)
    assert response.status_code == 202, response.text
    return poll(client, response.json()["id"], timeout=timeout, interval=interval)[-1]
