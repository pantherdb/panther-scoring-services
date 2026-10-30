"""The job as the API returns it. Workers never import this module.

A scoring service joins by adding its own job model, with its `service` and `result`, to `Job`.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, TypeAdapter

from panther_api.jobs.csnp import CsnpResult
from panther_api.jobs.refmap import RefmapResult
from panther_api.jobs.tools import ToolsResult
from panther_api.problems import Problem
from panther_api.versions import Versions


class JobStatus(StrEnum):
    """Where a job is. It only moves forward: queued, running, then succeeded or failed."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ToolsJob(BaseModel):
    """A `tools` job. Times are UTC, and null until reached.

    `result` is null unless the job succeeded, and `error` is null unless it failed. `versions`
    are the API, engine and tool versions the job ran with.
    """

    id: UUID
    service: Literal["tools"]
    status: JobStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result: ToolsResult | None
    error: Problem | None
    versions: Versions


class CsnpJob(BaseModel):
    """A `csnp` job, with the same fields as every job. `result` is its PANTHER-PSEP scores.

    It fails with a 422 `error` when the engine can't read the sequence, and with the generic 500
    otherwise.
    """

    id: UUID
    service: Literal["csnp"]
    status: JobStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result: CsnpResult | None
    error: Problem | None
    versions: Versions


class RefmapJob(BaseModel):
    """A `refmap` job, with the same fields as every job. `result` is its ID mappings.

    None is created until the engine's mapping is wired in: a valid request gets a 501.
    """

    id: UUID
    service: Literal["refmap"]
    status: JobStatus
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result: RefmapResult | None
    error: Problem | None
    versions: Versions


# Tagged by `service`, like the request, so the frontend narrows the result the same way.
Job = Annotated[ToolsJob | CsnpJob | RefmapJob, Field(discriminator="service")]

JOB_ADAPTER: TypeAdapter[Job] = TypeAdapter(Job)
