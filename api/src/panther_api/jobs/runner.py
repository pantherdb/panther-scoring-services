"""Runs each job's work in a pool of worker processes, and keeps its state on the event loop.

Every change to a job happens in that job's asyncio task, on the event loop, so no lock is
needed: the pool's future completes on another thread, and `asyncio.wrap_future` hands the
outcome back to the loop.
"""

import asyncio
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from datetime import timedelta
from http import HTTPStatus

from fastapi.concurrency import run_in_threadpool

from panther_api.jobs.store import JobRecord, JobStore
from panther_api.jobs.work import JobRequest, run_job
from panther_api.problems import Problem
from panther_api.versions import Versions

logger = logging.getLogger(__name__)

UNEXPECTED_JOB_DETAIL = "The job hit an unexpected error and could not complete."
WORKER_STOPPED_DETAIL = "The worker running the job stopped unexpectedly."


def _job_problem(detail: str) -> Problem:
    status = HTTPStatus.INTERNAL_SERVER_ERROR
    return Problem(title=status.phrase, status=status, detail=detail)


class JobRunner:
    """The job store, the worker pool, and a task per job that waits for its work."""

    def __init__(self, *, workers: int, expiry: timedelta, versions: Versions) -> None:
        self.store = JobStore(expiry)
        self._versions = versions
        self._workers = workers
        self._pool = self._new_pool()
        self._slots = asyncio.Semaphore(workers)
        self._tasks: set[asyncio.Task[None]] = set()

    def _new_pool(self) -> ProcessPoolExecutor:
        # spawn on every platform (docs/design/tech-stack.md, API recommendation 1). Processes
        # start only when a job arrives.
        return ProcessPoolExecutor(
            max_workers=self._workers, mp_context=multiprocessing.get_context("spawn")
        )

    def submit(self, request: JobRequest) -> JobRecord:
        """Store a new job and start its task. Call it on the event loop."""
        job = self.store.add(request, self._versions)
        task = asyncio.create_task(self._run(job))
        # The loop keeps only a weak reference to a task: keep it alive until it's done.
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job

    async def _run(self, job: JobRecord) -> None:
        # The pool gets at most one job per worker, so a job it has been given is running, not
        # waiting in the pool's own queue. The rest wait here, `queued`.
        async with self._slots:
            job.start()
            pool = self._pool
            try:
                # Looked up when called, so a test can patch `run_job` with a function of its own.
                result = await asyncio.wrap_future(pool.submit(run_job, job.request))
            except BrokenProcessPool:
                # A worker died. The pool fails every job it holds and takes no more, so replace
                # it; jobs still queued here then run on the new one.
                logger.exception("A worker died running job %s", job.id)
                job.fail(_job_problem(WORKER_STOPPED_DETAIL))
                self._replace_pool(pool)
            except Exception:
                # As for a 500 (problems.py), nothing about the exception goes in the job. The
                # log gets it, with the worker's traceback: concurrent.futures chains it as the
                # exception's cause.
                logger.exception("Job %s failed", job.id)
                job.fail(_job_problem(UNEXPECTED_JOB_DETAIL))
            else:
                job.succeed(result)

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
