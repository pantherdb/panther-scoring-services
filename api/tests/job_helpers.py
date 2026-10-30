"""Job functions the tests run in worker processes, in place of `run_job`.

Workers are started with `spawn`: each imports these by name, so they must be module-level in a
module that isn't a test module. pytest puts tests/ on `sys.path`, and `multiprocessing` hands the
parent's `sys.path` to each worker. A monkeypatch in the test process never reaches a worker, so
a helper that needs a parameter reads an environment variable, which a worker inherits when it
starts.
"""

import os
import time
from pathlib import Path

from panther_api.jobs.tools import ToolsResult
from panther_api.jobs.work import JobRequest
from panther_api.versions import ToolVersion

# The fake tool versions, as conftest's FAKE_REPORTS gives them.
FAKE_RESULT = ToolsResult(
    tools=[
        ToolVersion(name="blastp", version="2.17.0"),
        ToolVersion(name="hmmscan", version="3.4"),
        ToolVersion(name="hmmsearch", version="3.4"),
        ToolVersion(name="epa-ng", version="0.3.8"),
    ]
)

INTERNAL_PATH = "/data/panther/19/books/PTHR10000/hmmer.hmm"

# wait_for_gate() holds its job until a file at this path exists.
GATE_VARIABLE = "PANTHER_TEST_JOB_GATE"
GATE_TIMEOUT = 60.0


def report_fake_tools(_request: JobRequest) -> ToolsResult:
    """What every test's workers run unless a test says otherwise: no real tools."""
    return FAKE_RESULT


def fail(_request: JobRequest) -> ToolsResult:
    raise RuntimeError(f"failed reading {INTERNAL_PATH}")


def exit_worker(_request: JobRequest) -> ToolsResult:
    """End the worker process at once, as a crash would, past the pool's exception handling."""
    os._exit(1)


def wait_for_gate(_request: JobRequest) -> ToolsResult:
    """Stay running until the test creates the gate file, then succeed."""
    gate = Path(os.environ[GATE_VARIABLE])
    deadline = time.monotonic() + GATE_TIMEOUT
    while not gate.exists():
        if time.monotonic() > deadline:
            raise TimeoutError("the test never opened the gate")
        time.sleep(0.02)
    return FAKE_RESULT
