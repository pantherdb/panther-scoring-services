"""Runs each job's work in a pool of worker processes, and keeps its state on the event loop.

Every change to a job happens in that job's asyncio task, on the event loop, so no lock is
needed: the pool's future completes on another thread, and `asyncio.wrap_future` hands the
outcome back to the loop.

Each job gets one line in the log when it finishes, and one at DEBUG when it's submitted. The lines
give the size of the input (`log_summary()`), never what was submitted.
"""

import asyncio
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass
from datetime import datetime, timedelta
from http import HTTPStatus

from fastapi.concurrency import run_in_threadpool
from panther_engine.core.errors import InputError

from panther_api.jobs.store import JobRecord, JobStore
from panther_api.jobs.work import JobRequest, run_job
from panther_api.problems import Problem
from panther_api.versions import Versions

logger = logging.getLogger(__name__)

UNEXPECTED_JOB_DETAIL = "The job hit an unexpected error and could not complete."
WORKER_STOPPED_DETAIL = "The worker running the job stopped unexpectedly."

TRACEBACK_INTERVAL = timedelta(minutes=10)
"""An unexpected error's traceback is logged once in this time; repeats name that job instead."""


def _job_problem(detail: str, status: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR) -> Problem:
    return Problem(title=status.phrase, status=status, detail=detail)


class QueueFullError(Exception):
    """As many jobs are waiting for a worker as the cap allows. No job was stored."""


def _seconds(start: datetime | None, end: datetime | None) -> float:
    return (end - start).total_seconds() if start and end else 0.0


def _describe(job: JobRecord) -> str:
    """`Job <id> csnp, HUMAN, 347 residues, 3 substitutions`, or `Job <id> tools`."""
    summary = job.request.input.log_summary()
    return f"Job {job.id} {job.service}" + (f", {summary}" if summary else "")


@dataclass
class _ErrorSeen:
    job_id: str
    first: datetime
    count: int = 1


class _RecentErrors:
    """The unexpected errors seen in the last TRACEBACK_INTERVAL, by type and message, so that a
    traceback is logged once while every job fails the same way (openspec add-api-logging,
    design.md, decision 7).

    The times are the jobs' own `finished_at`, so a test moves them with store.utcnow.
    """

    def __init__(self) -> None:
        self._seen: dict[tuple[str, str], _ErrorSeen] = {}

    def repeat_of(self, error: BaseException, job_id: str, now: datetime) -> _ErrorSeen | None:
        """The earlier sighting this error repeats, counting this one, or None if it's new."""
        self._seen = {
            key: seen for key, seen in self._seen.items() if now - seen.first < TRACEBACK_INTERVAL
        }
        key = (type(error).__qualname__, str(error))
        seen = self._seen.get(key)
        if seen is None:
            self._seen[key] = _ErrorSeen(job_id, now)
            return None
        seen.count += 1
        return seen


class JobRunner:
    """The job store, the worker pool, and a task per job that waits for its work."""

    def __init__(
        self, *, workers: int, max_queued: int, expiry: timedelta, versions: Versions
    ) -> None:
        self.store = JobStore(expiry)
        self._versions = versions
        self._workers = workers
        self._max_queued = max_queued
        self._pool = self._new_pool()
        self._slots = asyncio.Semaphore(workers)
        self._tasks: set[asyncio.Task[None]] = set()
        # Jobs submitted and not yet finished, running or waiting.
        self._unfinished = 0
        self._errors = _RecentErrors()

    def submit(self, request: JobRequest) -> JobRecord:
        """Store a new job and start its task. Call it on the event loop.

        Raises QueueFullError, and stores nothing, when the job would have to wait for a worker
        and `max_queued` jobs already are.
        """
        # The jobs waiting are those unfinished past one per worker. They're counted this way,
        # not by status, because a job becomes `running` only when its task next gets the loop:
        # jobs submitted back to back while a worker is free would otherwise count as waiting.
        if self._unfinished >= self._workers + self._max_queued:
            logger.warning(
                "Refused a %s job: the queue is full, with %d jobs running or waiting and a cap "
                "of %d waiting",
                request.service,
                self._unfinished,
                self._max_queued,
            )
            raise QueueFullError
        job = self.store.add(request, self._versions)
        logger.debug("%s: submitted", _describe(job))
        self._unfinished += 1
        task = asyncio.create_task(self._run(job))
        # The loop keeps only a weak reference to a task: keep it alive until it's done.
        self._tasks.add(task)
        task.add_done_callback(self._finished)
        return job

    def _finished(self, task: asyncio.Task[None]) -> None:
        self._tasks.discard(task)
        self._unfinished -= 1

    def _new_pool(self) -> ProcessPoolExecutor:
        # spawn on every platform (docs/design/tech-stack.md, API recommendation 1). Processes
        # start only when a job arrives.
        return ProcessPoolExecutor(
            max_workers=self._workers, mp_context=multiprocessing.get_context("spawn")
        )

    async def _run(self, job: JobRecord) -> None:
        # The pool gets at most one job per worker, so a job it has been given is running, not
        # waiting in the pool's own queue. The rest wait here, `queued`.
        async with self._slots:
            job.start()
            pool = self._pool
            try:
                # Looked up when called, so a test can patch `run_job` with a function of its own.
                result = await asyncio.wrap_future(pool.submit(run_job, job.request))
            except BrokenProcessPool as error:
                # A worker died. The pool fails every job it holds and takes no more, so replace
                # it; jobs still queued here then run on the new one.
                job.fail(_job_problem(WORKER_STOPPED_DETAIL))
                self._log_unexpected(job, error, "failed 500, the worker stopped")
                self._replace_pool(pool)
            except InputError as error:
                # The user's input, not a fault: the engine writes the message for the user, with
                # no paths or tool output (engine-core, "Input errors"). Shown as given, and
                # logged without a traceback.
                job.fail(_job_problem(str(error), HTTPStatus.UNPROCESSABLE_CONTENT))
                logger.info("%s", self._finish_line(job, f"failed 422 ({error})"))
            except Exception as error:
                # As for a 500 (problems.py), nothing about the exception goes in the job. The
                # log gets it, with the worker's traceback: concurrent.futures chains it as the
                # exception's cause.
                job.fail(_job_problem(UNEXPECTED_JOB_DETAIL))
                self._log_unexpected(job, error, "failed 500")
            else:
                job.succeed(result)
                logger.info("%s", self._finish_line(job, "succeeded"))

    @staticmethod
    def _finish_line(job: JobRecord, outcome: str) -> str:
        waited = _seconds(job.created_at, job.started_at)
        ran = _seconds(job.started_at, job.finished_at)
        return f"{_describe(job)}: {outcome}, waited {waited:.1f} s, ran {ran:.1f} s"

    def _log_unexpected(self, job: JobRecord, error: BaseException, outcome: str) -> None:
        """The finish line at ERROR, with the traceback unless the same error has had one in the
        last TRACEBACK_INTERVAL."""
        line = self._finish_line(job, outcome)
        # A failed job always has finished_at; created_at only satisfies the type.
        seen = self._errors.repeat_of(error, str(job.id), job.finished_at or job.created_at)
        if seen is None:
            logger.error("%s", line, exc_info=error)
            return
        since = seen.first.strftime("%Y-%m-%dT%H:%M:%SZ")
        logger.error(
            "%s (same error as job %s, seen %d times since %s)",
            line,
            seen.job_id,
            seen.count,
            since,
        )

    def _replace_pool(self, broken: ProcessPoolExecutor) -> None:
        # Every job that was in the broken pool gets here. Only the first replaces it: every task
        # runs on the event loop, so nothing can change `self._pool` between the check and the set.
        if self._pool is broken:
            self._pool = self._new_pool()
            broken.shutdown(wait=False, cancel_futures=True)

    async def close(self) -> None:
        """Cancel the jobs not yet running, and wait for the running ones to finish."""
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await run_in_threadpool(self._pool.shutdown, wait=True, cancel_futures=True)
