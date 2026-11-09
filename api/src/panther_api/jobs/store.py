"""Jobs, kept in memory in the API process, until they expire or the API restarts.

Only the event loop touches a job (runner.py), so nothing here takes a lock.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from pydantic_core import to_json

from panther_api.jobs.models import JobStatus
from panther_api.jobs.work import JobRequest, JobResult, SerializedResult
from panther_api.problems import Problem
from panther_api.versions import Versions


def utcnow() -> datetime:
    """Every job timestamp comes from here, so tests can move time by patching it."""
    return datetime.now(UTC)


@dataclass
class JobRecord:
    """A job's state. `result` is set only when it succeeds, `error` only when it fails.

    A job is finished only through its store, `JobStore.succeed` or `JobStore.fail`, so its result
    is always counted against the results budget: the record has no method of its own for it.

    It doesn't keep the request: the runner holds that until the job finishes. The job keeps its
    service, and its input's size for the log (`summary`), never the input itself, so a finished
    job of 100,000 IDs doesn't hold them for its 24 hours.
    """

    service: str
    summary: str
    versions: Versions
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    # A lambda, not `utcnow` itself, so a patched clock is looked up when the job is made.
    created_at: datetime = field(default_factory=lambda: utcnow())
    status: JobStatus = JobStatus.QUEUED
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: JobResult | None = None
    error: Problem | None = None

    def start(self) -> None:
        self.status = JobStatus.RUNNING
        self.started_at = utcnow()

    def expired(self, expiry: timedelta) -> bool:
        """A finished job expires `expiry` after it finished. An unfinished job never does."""
        return self.finished_at is not None and utcnow() >= self.finished_at + expiry


class JobStore:
    """Jobs by id. An expired job is gone: `get` drops it, and `add` sweeps out the rest.

    The finished jobs' results share a budget, `results_budget` bytes, each counted by the size of
    its JSON when its job finishes. When a finishing job takes them over it, the largest results
    expire first, the oldest first among equal sizes, before their time, until they fit: a burst
    of large jobs from one client then expires large results, not everyone's small ones. The
    finishing job itself is always kept, even when its result alone is over the budget, so its
    user can read it.

    Each job carries the versions with only its own service's data (`Versions.for_service`).
    """

    def __init__(self, expiry: timedelta, *, results_budget: int) -> None:
        self._expiry = expiry
        self._results_budget = results_budget
        self._jobs: dict[uuid.UUID, JobRecord] = {}
        # The finished jobs, in the order they finished, with their results' sizes.
        self._finished: dict[uuid.UUID, int] = {}
        self._results_bytes = 0

    def __len__(self) -> int:
        return len(self._jobs)

    @property
    def results_bytes(self) -> int:
        """The kept results' size, in bytes of JSON."""
        return self._results_bytes

    def add(self, request: JobRequest, versions: Versions) -> JobRecord:
        """Store a new job for `request`, keeping its service and its input's log summary, and
        `versions` with only its service's data."""
        # The number of jobs only grows here, so sweeping here bounds it without a background task.
        for job_id in [job.id for job in self._jobs.values() if job.expired(self._expiry)]:
            self._drop(job_id)
        job = JobRecord(
            service=request.service,
            summary=request.input.log_summary(),
            versions=versions.for_service(request.service),
        )
        self._jobs[job.id] = job
        return job

    def succeed(self, job: JobRecord, result: JobResult) -> None:
        """The job succeeded with `result`: keep it within the results budget."""
        job.status = JobStatus.SUCCEEDED
        job.result = result
        job.finished_at = utcnow()
        self._finished_with(job, _json_size(result))

    def fail(self, job: JobRecord, error: Problem) -> None:
        """The job failed. It has no result, so it counts nothing against the budget."""
        job.status = JobStatus.FAILED
        job.error = error
        job.finished_at = utcnow()
        self._finished_with(job, 0)

    def get(self, job_id: str) -> JobRecord | None:
        """The job, or None if the id is unknown, isn't a UUID, or its job expired."""
        try:
            key = uuid.UUID(job_id)
        except ValueError:
            return None
        job = self._jobs.get(key)
        if job is None or not job.expired(self._expiry):
            return job
        self._drop(key)
        return None

    def _finished_with(self, job: JobRecord, size: int) -> None:
        """Count the job's result, then, while over budget, expire the other finished jobs that
        hold a result, the largest first, and the oldest first among equal sizes. A job without
        one, such as a failed job, frees nothing, so it's kept until its time.

        The results only grow here, so the budget is kept here, without a background task.
        """
        if job.id not in self._jobs:
            return
        self._finished[job.id] = size
        self._results_bytes += size
        if self._results_bytes <= self._results_budget:
            return
        # `_finished` is in the order the jobs finished, and the sort is stable.
        largest_first = sorted(
            (key for key, kept in self._finished.items() if kept and key != job.id),
            key=lambda key: self._finished[key],
            reverse=True,
        )
        for job_id in largest_first:
            if self._results_bytes <= self._results_budget:
                break
            self._drop(job_id)

    def _drop(self, job_id: uuid.UUID) -> None:
        del self._jobs[job_id]
        self._results_bytes -= self._finished.pop(job_id, 0)


def _json_size(result: JobResult) -> int:
    """The result's size as JSON: a serialised result's bytes, or a model's, serialised once."""
    if isinstance(result, SerializedResult):
        return len(result.json)
    return len(to_json(result))
