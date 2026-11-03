"""The FastAPI app. Every route, the schema and the docs are under /api/v1."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta
from importlib.metadata import version
from typing import Any, override

import panther_engine.csnp
from fastapi import APIRouter, FastAPI
from fastapi.concurrency import run_in_threadpool

from panther_api.jobs.runner import JobRunner
from panther_api.limits import BodyLimit
from panther_api.problems import PROBLEM_RESPONSES, add_problem_handlers, document_problems
from panther_api.routers import csnp, health, jobs, versions
from panther_api.settings import Settings
from panther_api.versions import read_versions

API_PREFIX = "/api/v1"

logger = logging.getLogger(__name__)


class PantherAPI(FastAPI):
    """FastAPI, with error responses documented as problem details in the schema."""

    @override
    def openapi(self) -> dict[str, Any]:
        if not self.openapi_schema:
            self.openapi_schema = document_problems(super().openapi())
        return self.openapi_schema


def check_csnp_data() -> None:
    """Log an error when the cSNP data is missing or incomplete, and carry on.

    The API still starts: a developer runs it natively without the data, and only `csnp` jobs
    need it. Each `csnp` job checks again, and fails with the generic 500 while it's missing.
    """
    try:
        panther_engine.csnp.check_data()
    except Exception as error:
        # The engine's message names the folder and what's missing; it goes only to the log.
        logger.error("csnp jobs will fail until the cSNP data is in place: %s", error)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Before the app takes requests: read the settings and the versions, and start the jobs.

    An invalid setting stops the app here. The tools and the data check run off the event loop.
    On shutdown, the jobs still queued are dropped, and the running ones finish first.
    """
    settings = Settings()
    app.state.settings = settings
    app.state.versions = await run_in_threadpool(read_versions)
    await run_in_threadpool(check_csnp_data)
    runner = JobRunner(
        workers=settings.job_workers,
        max_queued=settings.max_queued_jobs,
        expiry=timedelta(seconds=settings.job_expiry_seconds),
        versions=app.state.versions,
    )
    app.state.jobs = runner
    try:
        yield
    finally:
        await runner.close()


def create_app(*routers: APIRouter) -> FastAPI:
    """Build a new app.

    `routers` are included under /api/v1 after the app's own; tests use them for throwaway routes.
    """
    app = PantherAPI(
        title="PANTHER Scoring Services API",
        version=version("panther-api"),
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    add_problem_handlers(app)
    # Before anything reads a body, so the limit holds however the route reads it.
    app.add_middleware(BodyLimit)

    api = APIRouter(prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    api.include_router(health.router)
    api.include_router(versions.router)
    api.include_router(jobs.router)
    api.include_router(csnp.router)
    for router in routers:
        api.include_router(router)
    app.include_router(api)

    return app


app = create_app()
