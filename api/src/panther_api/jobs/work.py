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

from panther_api.jobs.csnp import CsnpInput, CsnpResult
from panther_api.jobs.tools import ToolsInput, ToolsResult, run_tools

CSNP_UNAVAILABLE = "cSNP scoring isn't available yet."


class ToolsJobRequest(BaseModel):
    """Start a `tools` job: report the external tools' versions from a worker process."""

    service: Literal["tools"]
    input: ToolsInput


class CsnpJobRequest(BaseModel):
    """Start a `csnp` job: score substitutions in one protein with PANTHER-PSEP.

    Until the engine's cSNP scoring is wired in, a valid request gets a 501, and no job.
    """

    service: Literal["csnp"]
    input: CsnpInput


# Tagged by `service`, so the schema is a `oneOf` with a discriminator, and each service adds a
# member.
JobRequest = Annotated[ToolsJobRequest | CsnpJobRequest, Field(discriminator="service")]

JobResult = ToolsResult | CsnpResult


def run_job(request: JobRequest) -> JobResult:
    """Do a job's work. The runner submits this function to the worker pool."""
    match request:
        case ToolsJobRequest():
            return run_tools(request.input)
        case CsnpJobRequest():
            # The router answers 501 and never submits one. If one gets here anyway, the job
            # fails with the generic error, never a made-up score. The port calls the engine here.
            raise NotImplementedError(CSNP_UNAVAILABLE)
