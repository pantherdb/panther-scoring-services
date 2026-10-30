"""Start a job, and poll it.

Both handlers are `async def`, so they run on the event loop, the only place that touches a job
(jobs/runner.py). Neither runs any work itself.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Request, Response, status

from panther_api.jobs.models import JOB_ADAPTER, Job
from panther_api.jobs.runner import JobRunner
from panther_api.jobs.store import JobRecord
from panther_api.jobs.work import JobRequest

router = APIRouter(prefix="/jobs", tags=["jobs"])

JOB_NOT_FOUND = "There is no job with this id. A finished job expires after a time."

_LOCATION: dict[int | str, dict[str, Any]] = {
    status.HTTP_202_ACCEPTED: {
        "description": "The job was accepted. Poll it at `Location`.",
        "headers": {
            "Location": {
                "description": "The job's path, `/api/v1/jobs/{job_id}`",
                "schema": {"type": "string"},
            }
        },
    }
}


def _runner(request: Request) -> JobRunner:
    return request.app.state.jobs


def _job(record: JobRecord) -> Job:
    return JOB_ADAPTER.validate_python(
        {
            "id": record.id,
            "service": record.service,
            "status": record.status,
            "created_at": record.created_at,
            "started_at": record.started_at,
            "finished_at": record.finished_at,
            "result": record.result,
            "error": record.error,
            "versions": record.versions,
        }
    )


@router.post("", status_code=status.HTTP_202_ACCEPTED, summary="Start a job", responses=_LOCATION)
async def create_job(
    job_request: Annotated[JobRequest, Body()], request: Request, response: Response
) -> Job:
    """Start a job for `service` with its `input`. The job runs after this request returns."""
    record = _runner(request).submit(job_request)
    response.headers["Location"] = request.app.url_path_for("get_job", job_id=str(record.id))
    return _job(record)


@router.get("/{job_id}", summary="A job's status and result")
async def get_job(job_id: str, request: Request) -> Job:
    """The job's current state. An unknown, invalid or expired id is a 404."""
    record = _runner(request).store.get(job_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=JOB_NOT_FOUND)
    return _job(record)
