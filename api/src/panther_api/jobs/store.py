"""Jobs, kept in memory in the API process, until they expire or the API restarts.

Only the event loop touches a job (runner.py), so nothing here takes a lock.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from panther_api.jobs.models import JobStatus
from panther_api.jobs.work import JobRequest, JobResult
from panther_api.problems import Problem
from panther_api.versions import Versions


def utcnow() -> datetime:
    """Every job timestamp comes from here, so tests can move time by patching it."""
    return datetime.now(UTC)


@dataclass
class JobRecord:
    """A job's state. `result` is set only when it succeeds, `error` only when it fails.

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

    def succeed(self, result: JobResult) -> None:
        self.status = JobStatus.SUCCEEDED
        self.result = result
        self.finished_at = utcnow()

    def fail(self, error: Problem) -> None:
        self.status = JobStatus.FAILED
        self.error = error
        self.finished_at = utcnow()

    def expired(self, expiry: timedelta) -> bool:
        """A finished job expires `expiry` after it finished. An unfinished job never does."""
        return self.finished_at is not None and utcnow() >= self.finished_at + expiry


class JobStore:
    """Jobs by id. An expired job is gone: `get` drops it, and `add` sweeps out the rest."""

    def __init__(self, expiry: timedelta) -> None:
        self._expiry = expiry
        self._jobs: dict[uuid.UUID, JobRecord] = {}

    def __len__(self) -> int:
        return len(self._jobs)

    def add(self, request: JobRequest, versions: Versions) -> JobRecord:
        """Store a new job for `request`, keeping its service and its input's log summary."""
        # Memory only grows here, so sweeping here bounds it without a background task.
        for job_id in [job.id for job in self._jobs.values() if job.expired(self._expiry)]:
            del self._jobs[job_id]
        job = JobRecord(
            service=request.service, summary=request.input.log_summary(), versions=versions
        )
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> JobRecord | None:
        """The job, or None if the id is unknown, isn't a UUID, or its job expired."""
        try:
            key = uuid.UUID(job_id)
        except ValueError:
            return None
        job = self._jobs.get(key)
        if job is None or not job.expired(self._expiry):
            return job
        del self._jobs[key]
        return None
