"""What the worker processes run: the job request union, the result union, the job's options
and `run_job()`.

Workers are started with `spawn`, so each one imports this module afresh and gets everything it
needs from `run_job`'s arguments: the request, and the options the API read from its settings
(`JobOptions`). Keep it that way: no state set up at import time in the API process reaches a
worker. Keep the imports light too: a worker imports this module, and doesn't need FastAPI.

A scoring service joins by adding its request model to `JobRequest`, its result to `JobResult`,
and a case to `run_job`.
"""

from dataclasses import dataclass
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, Field

from panther_api.jobs.csnp import CsnpInput, CsnpResult, run_csnp
from panther_api.jobs.hmmscore import (
    HMMSCORE_MAX_RESIDUES,
    HmmscoreInput,
    HmmscoreResult,
    run_hmmscore,
)
from panther_api.jobs.refmap import RefmapInput, run_refmap
from panther_api.jobs.tools import ToolsInput, ToolsResult, run_tools


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
    """Start an `hmmscore` job: score one protein against PANTHER's HMM library."""

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
class JobOptions:
    """What a job's work needs from the API's settings, which only the API process reads.

    The lifespan builds them once from the settings (main.py), and the runner submits them with
    every job, beside its request (openspec wire-hmmscore, design.md, decision 2). Each case of
    `run_job` takes what it needs and ignores the rest.
    """

    hmmscore_cpu: int
    """`--cpu` for both `hmmscan` and `hmmsearch` (`PANTHER_API_HMMSCORE_CPU`)."""
    hmmscore_time_limit_seconds: int
    """The time limit at 10,000 residues, the most a job gets
    (`PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS`)."""
    hmmscore_min_time_limit_seconds: int
    """The time limit of the shortest sequence (`PANTHER_API_HMMSCORE_MIN_TIME_LIMIT_SECONDS`)."""


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


def hmmscore_time_limit(residues: int, options: JobOptions) -> int:
    """An hmmscore job's time limit, in seconds: the minimum, plus the difference between the time
    limit and the minimum, times the residues over 10,000, rounded to the nearest second, a half
    up.

    It divides by 10,000, the most residues the API ever takes, not by the configured residue
    limit, so a server that lowers that doesn't lengthen anyone's limit (openspec wire-hmmscore,
    design.md, decision 3; divergence row 14). With the defaults, APOE's 317 residues get 139 s.
    """
    floor = options.hmmscore_min_time_limit_seconds
    spread = options.hmmscore_time_limit_seconds - floor
    # In whole numbers, so the rounding is exact.
    return floor + (2 * spread * residues + HMMSCORE_MAX_RESIDUES) // (2 * HMMSCORE_MAX_RESIDUES)


def run_job(request: JobRequest, options: JobOptions) -> JobResult:
    """Do a job's work, with the API's options. The runner submits this function to the worker
    pool."""
    match request:
        case ToolsJobRequest():
            return run_tools(request.input)
        case CsnpJobRequest():
            return run_csnp(request.input)
        case RefmapJobRequest():
            return SerializedResult(run_refmap(request.input))
        case HmmscoreJobRequest():
            return run_hmmscore(
                request.input,
                cpu=options.hmmscore_cpu,
                timeout=hmmscore_time_limit(request.input.residues, options),
            )
