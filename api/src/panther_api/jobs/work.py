"""What the worker processes run: the job request union, the result union and `run_job()`.

Workers are started with `spawn`, so each one imports this module afresh and gets everything it
needs from `run_job`'s argument. Keep it that way: no state set up at import time in the API
process reaches a worker. Keep the imports light too: a worker imports this module, and doesn't
need FastAPI.

A scoring service joins by adding its request model to `JobRequest`, its result to `JobResult`,
and a case to `run_job`.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from panther_api.jobs.tools import ToolsInput, ToolsResult, run_tools


class ToolsJobRequest(BaseModel):
    """Start a `tools` job: report the external tools' versions from a worker process."""

    service: Literal["tools"]
    input: ToolsInput


# Tagged by `service`, so the schema is a `oneOf` with a discriminator, and each service adds a
# member. Pydantic accepts a union of one.
JobRequest = Annotated[ToolsJobRequest, Field(discriminator="service")]

JobResult = ToolsResult


def run_job(request: JobRequest) -> JobResult:
    """Do a job's work. The runner submits this function to the worker pool."""
    match request:
        case ToolsJobRequest():
            return run_tools(request.input)
