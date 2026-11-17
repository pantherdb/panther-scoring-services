"""The FastAPI app. Every route, the schema and the docs are under /api/v1."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta
from importlib.metadata import version
from typing import Any, override

import panther_engine.csnp
import panther_engine.refmap
from fastapi import APIRouter, FastAPI
from fastapi.concurrency import run_in_threadpool

from panther_api.cors import Cors
from panther_api.jobs.runner import JobRunner
from panther_api.limits import BodyLimit
from panther_api.logs import configure_logging
from panther_api.prefix import API_PREFIX
from panther_api.problems import PROBLEM_RESPONSES, add_problem_handlers, document_problems
from panther_api.routers import csnp, health, jobs, refmap, versions
from panther_api.settings import MIB, Settings
from panther_api.versions import read_versions

logger = logging.getLogger(__name__)


class PantherAPI(FastAPI):
    """FastAPI, with error responses documented as problem details in the schema."""

    @override
    def openapi(self) -> dict[str, Any]:
        if not self.openapi_schema:
            self.openapi_schema = document_problems(super().openapi())
        return self.openapi_schema


DATA_CHECKS = (("csnp", "cSNP", panther_engine.csnp), ("refmap", "refmap", panther_engine.refmap))
"""Each service whose jobs need data: its name, its data's name, and the engine module whose
`check_data()` checks it. Looked up when called, so a test can patch a module's check."""


def check_data() -> None:
    """Check each service's data, and log an error for each one that's missing or incomplete, then
    carry on.

    The API still starts: a developer runs it natively without the data, and only that service's
    jobs need it. Each check is independent, so one service's missing data neither hides nor stops
    another's. Each job checks again, and fails with the generic 500 while its data is missing.

    Once the refmap data is in place, the classification JSON built from it is checked too, for
    `GET /refmap/organisms/{code}/classification`; without the refmap data, its line would only
    repeat refmap's.
    """
    refmap_data = False
    for service, data, module in DATA_CHECKS:
        try:
            module.check_data()
        except Exception as error:
            # The engine's message names the folder and what's missing; it goes only to the log.
            logger.error(
                "%s jobs will fail until the %s data is in place: %s", service, data, error
            )
        else:
            refmap_data = refmap_data or service == "refmap"
    if not refmap_data:
        return
    try:
        panther_engine.refmap.check_classification_json()
    except Exception as error:
        logger.error(
            "refmap classifications will fail until the classification JSON is built "
            "(panther-engine refmap data build-json): %s",
            error,
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Before the app takes requests: read the settings, set up the log, read the versions, and
    start the jobs.

    An invalid setting stops the app here. The tools and the data checks run off the event loop.
    On shutdown, the jobs still queued are dropped, and the running ones finish first.
    """
    settings = Settings()
    configure_logging(settings.log_level)
    app.state.settings = settings
    app.state.versions = await run_in_threadpool(read_versions)
    await run_in_threadpool(check_data)
    runner = JobRunner(
        workers=settings.job_workers,
        max_queued=settings.max_queued_jobs,
        expiry=timedelta(seconds=settings.job_expiry_seconds),
        results_budget=settings.results_budget_mib * MIB,
        versions=app.state.versions,
        max_running={"hmmscore": settings.hmmscore_max_running},
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
    # Each middleware added wraps the ones before it. BodyLimit runs before anything reads a body,
    # so the limit holds however the route reads it. Cors wraps it, so a preflight is answered
    # before the limit, and a 413 still gets the CORS headers a browser needs to read it.
    app.add_middleware(BodyLimit)
    app.add_middleware(Cors)

    api = APIRouter(prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    api.include_router(health.router)
    api.include_router(versions.router)
    api.include_router(jobs.router)
    api.include_router(csnp.router)
    api.include_router(refmap.router)
    for router in routers:
        api.include_router(router)
    app.include_router(api)

    return app


app = create_app()
