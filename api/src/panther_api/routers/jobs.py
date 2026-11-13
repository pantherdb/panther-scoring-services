"""Start a job, and poll it.

Both handlers are `async def`, so they run on the event loop, the only place that touches a job
(jobs/runner.py). Neither runs any work itself.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError

from panther_api.jobs.models import JOB_ADAPTER, Job
from panther_api.jobs.runner import JobRunner, QueueFullError
from panther_api.jobs.store import JobRecord
from panther_api.jobs.work import UNAVAILABLE, HmmscoreJobRequest, JobRequest, SerializedResult
from panther_api.problems import Problem
from panther_api.settings import Settings

router = APIRouter(prefix="/jobs", tags=["jobs"])

JOB_NOT_FOUND = "There is no job with this id. A finished job expires after a time."
QUEUE_FULL_DETAIL = "Too many jobs are waiting to run. Try again later."
RETRY_AFTER_SECONDS = 30
"""What a 503's `Retry-After` asks for: about how long a typical `csnp` job takes."""

_CREATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_202_ACCEPTED: {
        "description": "The job was accepted. Poll it at `Location`.",
        "headers": {
            "Location": {
                "description": "The job's path, `/api/v1/jobs/{job_id}`",
                "schema": {"type": "string"},
            }
        },
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "model": Problem,
        "description": "As many jobs are waiting for a worker as the API allows "
        "(`PANTHER_API_MAX_QUEUED_JOBS`). The request was valid, and no job was created.",
        "headers": {
            "Retry-After": {
                "description": "Seconds to wait before submitting again",
                "schema": {"type": "integer"},
            }
        },
    },
}
# Documented while any service is unavailable (jobs/work.py's UNAVAILABLE, which says when each
# row goes, and what lands with it).
if UNAVAILABLE:
    _CREATE_RESPONSES[status.HTTP_501_NOT_IMPLEMENTED] = {
        "model": Problem,
        "description": "The service can't run jobs yet: "
        + "; ".join(f"`{service}`, {why.until}" for service, why in UNAVAILABLE.items())
        + ". The request was valid, and no job was created.",
    }


def _runner(request: Request) -> JobRunner:
    return request.app.state.jobs


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _check_hmmscore_residues(job_request: HmmscoreJobRequest, most: int) -> None:
    """Refuse a sequence over the configured residue limit with a 422 on `sequence`, as any
    invalid field is.

    The limit is a setting, read at startup, and the committed schema must equal the served one,
    so the model can't hold it (openspec add-hmmscore-job, design.md, decision 7). The message
    names the limit, which is configuration, never the sequence.
    """
    if job_request.input.residues > most:
        raise RequestValidationError(
            [
                {
                    "type": "value_error",
                    "loc": ("body", "hmmscore", "input", "sequence"),
                    "msg": f"The sequence has more than {most:,} residues.",
                }
            ]
        )


def _job(record: JobRecord) -> Job:
    """The job as a model. A serialised result is left out, as `null`: `_job_json` adds it."""
    result = None if isinstance(record.result, SerializedResult) else record.result
    return JOB_ADAPTER.validate_python(
        {
            "id": record.id,
            "service": record.service,
            "status": record.status,
            "created_at": record.created_at,
            "started_at": record.started_at,
            "finished_at": record.finished_at,
            "result": result,
            "error": record.error,
            "versions": record.versions,
        }
    )


_NULL_RESULT = b'"result":null'


def _job_json(record: JobRecord) -> bytes:
    """The job's JSON. A serialised result's bytes are put in as they are, not validated and
    serialised again: they're a `RefmapResult`'s, made in the worker (jobs/work.py)."""
    job = JOB_ADAPTER.dump_json(_job(record))
    if not isinstance(record.result, SerializedResult):
        return job
    # The fields before `result` are the job's id, service, status and times, none of which can
    # hold this text. Exactly one match is required, so a reordered or new field that could hold
    # it fails loudly here, and in the tests, rather than splicing into the wrong place.
    if job.count(_NULL_RESULT) != 1:
        raise ValueError("the job's JSON doesn't have exactly one null result to replace")
    before, _, after = job.partition(_NULL_RESULT)
    return b"".join((before, b'"result":', record.result.json, after))


@router.post(
    "", status_code=status.HTTP_202_ACCEPTED, summary="Start a job", responses=_CREATE_RESPONSES
)
async def create_job(
    job_request: Annotated[JobRequest, Body()], request: Request, response: Response
) -> Job:
    """Start a job for `service` with its `input`. The job runs after this request returns.

    An input the job can't run with is a 422, and no job is created. A problem only the work can
    find, such as a `csnp` sequence BLAST+ can't read, fails the job with a 422 `error`. A valid
    request is a 503 when too many jobs are already waiting for a worker. A valid `hmmscore`
    request gets a 501 until its scoring is available; its input, and its residue limit, are still
    validated first.
    """
    if isinstance(job_request, HmmscoreJobRequest):
        _check_hmmscore_residues(job_request, _settings(request).hmmscore_max_residues)
    unavailable = UNAVAILABLE.get(job_request.service)
    if unavailable is not None:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail=unavailable.detail)
    try:
        record = _runner(request).submit(job_request)
    except QueueFullError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=QUEUE_FULL_DETAIL,
            headers={"Retry-After": str(RETRY_AFTER_SECONDS)},
        ) from None
    response.headers["Location"] = request.app.url_path_for("get_job", job_id=str(record.id))
    return _job(record)


# The response is built by _job_json, so FastAPI documents `Job` but doesn't serialise it again.
@router.get("/{job_id}", summary="A job's status and result", response_model=Job)
async def get_job(job_id: str, request: Request) -> Response:
    """The job's current state. An unknown, invalid or expired id is a 404."""
    record = _runner(request).store.get(job_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=JOB_NOT_FOUND)
    return Response(_job_json(record), media_type="application/json")
