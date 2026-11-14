"""What the worker processes run: the job request union, the result union and `run_job()`.

Workers are started with `spawn`, so each one imports this module afresh and gets everything it
needs from `run_job`'s argument. Keep it that way: no state set up at import time in the API
process reaches a worker. Keep the imports light too: a worker imports this module, and doesn't
need FastAPI.

A scoring service joins by adding its request model to `JobRequest`, its result to `JobResult`,
and a case to `run_job`. One whose contract comes before its port also gets a row in
`UNAVAILABLE`, which the router answers with a 501, and a `run_job` case that refuses to run.
"""

from dataclasses import dataclass
from typing import Annotated, Literal, NamedTuple, get_args

from pydantic import BaseModel, Field

from panther_api.jobs.csnp import CsnpInput, CsnpResult, run_csnp
from panther_api.jobs.hmmscore import HmmscoreInput, HmmscoreResult
from panther_api.jobs.refmap import RefmapInput, run_refmap
from panther_api.jobs.tools import ToolsInput, ToolsResult, run_tools


class Unavailable(NamedTuple):
    """Why a service's valid request gets a 501 and no job."""

    detail: str
    """The 501's `detail`."""
    until: str
    """Ends the 501's description after the service's name, such as "until it's ported"."""


UNAVAILABLE: dict[str, Unavailable] = {
    # Removed, with run_job's hmmscore case, when the engine's hmmscore scoring is wired in. The
    # same change calls `score()` with the time limit and `--cpu` settings, adds hmmscore's data
    # check at startup and its data version (openspec add-hmmscore-job, design.md, Migration Plan).
    "hmmscore": Unavailable("HMM scoring isn't available yet.", "until its scoring is ported"),
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
    """Start a `refmap` job: map protein IDs to PANTHER IDs for one organism."""

    service: Literal["refmap"]
    input: RefmapInput


class HmmscoreJobRequest(BaseModel):
    """Start an `hmmscore` job: score one protein against PANTHER's HMM library.

    Until the engine's hmmscore scoring is wired in, a valid request gets a 501, and no job.
    """

    service: Literal["hmmscore"]
    input: HmmscoreInput


# Tagged by `service`, so the schema is a `oneOf` with a discriminator, and each service adds a
# member.
JobRequest = Annotated[
    ToolsJobRequest | CsnpJobRequest | RefmapJobRequest | HmmscoreJobRequest,
    Field(discriminator="service"),
]

Service = Literal["tools", "csnp", "refmap", "hmmscore"]
"""Every `service` a `JobRequest` names. A service added to `JobRequest` is added here too;
test_jobs.py compares the two."""

SERVICES: frozenset[str] = frozenset(get_args(Service))


@dataclass(frozen=True)
class SerializedResult:
    """A result already serialised as JSON, in the worker: a `RefmapResult`'s bytes.

    A large result is kept this way, about a tenth of its size as models, and each poll returns
    the bytes as they are, without validating or serialising it again (openspec wire-refmap,
    design.md, decision 4). Bytes also cross the process boundary cheaper than 100,000 pickled
    models.
    """

    json: bytes


JobResult = ToolsResult | CsnpResult | HmmscoreResult | SerializedResult
"""What a job's work returns. A small result is a model; a large one, refmap's, is serialised."""


def run_job(request: JobRequest) -> JobResult:
    """Do a job's work. The runner submits this function to the worker pool."""
    match request:
        case ToolsJobRequest():
            return run_tools(request.input)
        case CsnpJobRequest():
            return run_csnp(request.input)
        case RefmapJobRequest():
            return SerializedResult(run_refmap(request.input))
        case HmmscoreJobRequest():
            # The router answers 501 and never submits one. If one gets here anyway, the job
            # fails with the generic error, never a made-up hit. The wiring calls the engine here.
            raise NotImplementedError(UNAVAILABLE["hmmscore"].detail)
