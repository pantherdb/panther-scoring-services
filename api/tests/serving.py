"""The app served by a real Uvicorn server, for the tests that need what only Uvicorn does, such as
its access log. `TestClient` calls the app directly, so Uvicorn never sees its requests.
"""

import json
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import uvicorn

from panther_api.main import create_app

START_TIMEOUT = 30.0
JOB_TIMEOUT = 60.0


class Server:
    """A base URL, and requests to it that return the status and the JSON body, if any."""

    def __init__(self, base: str) -> None:
        self.base = base

    def request(self, method: str, path: str, body: object = None) -> tuple[int, Any]:
        data = None if body is None else json.dumps(body).encode()
        headers = {} if body is None else {"Content-Type": "application/json"}
        # Always the local server's http:// URL.
        request = urllib.request.Request(self.base + path, data, headers, method=method)  # noqa: S310
        try:
            with urllib.request.urlopen(request, timeout=JOB_TIMEOUT) as response:  # noqa: S310
                return response.status, json.loads(response.read() or b"null")
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"null")

    def run_job(self, body: object) -> dict[str, Any]:
        """Submit a job and poll it until it finishes. The finished job."""
        status, job = self.request("POST", "/api/v1/jobs", body)
        assert status == 202, job
        deadline = time.monotonic() + JOB_TIMEOUT
        while job["status"] not in ("succeeded", "failed"):
            assert time.monotonic() < deadline, f"job still {job['status']}"
            time.sleep(0.05)
            status, job = self.request("GET", f"/api/v1/jobs/{job['id']}")
            assert status == 200, job
        return job


@contextmanager
def serve(*, access_log: bool = True) -> Generator[Server]:
    """A new app on a free local port, with Uvicorn's own logging config, as `fastapi run` starts
    it; `access_log=False` as `--no-access-log` does. Stopped, and its jobs' workers with it, at
    the end."""
    config = uvicorn.Config(
        create_app(), host="127.0.0.1", port=0, lifespan="on", access_log=access_log
    )
    server = uvicorn.Server(config)
    # Not the main thread, so Uvicorn installs no signal handlers.
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + START_TIMEOUT
    while not server.started:
        assert thread.is_alive(), "the server stopped while starting"
        assert time.monotonic() < deadline, "the server didn't start"
        time.sleep(0.02)
    port = server.servers[0].sockets[0].getsockname()[1]
    try:
        yield Server(f"http://127.0.0.1:{port}")
    finally:
        server.should_exit = True
        thread.join(START_TIMEOUT)
