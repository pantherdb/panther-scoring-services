"""What the worker processes run: the job request union, the result union and `run_job()`.

Workers are started with `spawn`, so each one imports this module afresh and gets everything it
needs from `run_job`'s argument. Keep it that way: no state set up at import time in the API
process reaches a worker. Keep the imports light too: a worker imports this module, and doesn't
need FastAPI.

A scoring service joins by adding its request model to `JobRequest`, its result to `JobResult`,
and a case to `run_job`. One whose contract comes before its port also gets a row in
`UNAVAILABLE`, which the router answers with a 501, and a `run_job` case that refuses to run.
"""

from typing import Annotated, Literal, NamedTuple

from pydantic import BaseModel, Field

from panther_api.jobs.csnp import CsnpInput, CsnpResult, run_csnp
from panther_api.jobs.refmap import RefmapInput, RefmapResult
from panther_api.jobs.tools import ToolsInput, ToolsResult, run_tools


class Unavailable(NamedTuple):
    """Why a service's valid request gets a 501 and no job."""

    detail: str
    """The 501's `detail`."""
    until: str
    """Ends the 501's description after the service's name, such as "until it's ported"."""


UNAVAILABLE: dict[str, Unavailable] = {
    # Removed, with run_job's refmap case, when the engine's refmap mapping is wired in. The
    # check of `organism` against the engine's organism list (ORGANISM_CODES) lands in the same
    # change: until then only its shape is checked, and the 501 keeps any other code from
    # reaching the engine.
    "refmap": Unavailable("refmap ID mapping isn't available yet.", "until its mapping is ported"),
}
"""The services whose requests are validated, then refused with a 501 (routers/jobs.py)."""


class ToolsJobRequest(BaseModel):
    """Start a `tools` job: report the external tools' versions from a worker process."""

    service: Literal["tools"]
    input: ToolsInput


class CsnpJobRequest(BaseModel):
    """Start a `csnp` job: score substitutions in one protein with PANTHER-PSEP."""

    service: Literal["csnp"]
    input: CsnpInput


class RefmapJobRequest(BaseModel):
    """Start a `refmap` job: map protein IDs to PANTHER IDs for one organism.

    Until the engine's refmap mapping is wired in, a valid request gets a 501, and no job.
    """

    service: Literal["refmap"]
    input: RefmapInput


# Tagged by `service`, so the schema is a `oneOf` with a discriminator, and each service adds a
# member.
JobRequest = Annotated[
    ToolsJobRequest | CsnpJobRequest | RefmapJobRequest, Field(discriminator="service")
]

JobResult = ToolsResult | CsnpResult | RefmapResult


def run_job(request: JobRequest) -> JobResult:
    """Do a job's work. The runner submits this function to the worker pool."""
    match request:
        case ToolsJobRequest():
            return run_tools(request.input)
        case CsnpJobRequest():
            return run_csnp(request.input)
        case RefmapJobRequest():
            # The router answers 501 and never submits one. If one gets here anyway, the job
            # fails with the generic error, never a made-up mapping. The port calls the engine here.
            raise NotImplementedError(UNAVAILABLE["refmap"].detail)
