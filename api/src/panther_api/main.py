"""The FastAPI app. Every route, the schema and the docs are under /api/v1."""

from importlib.metadata import version
from typing import Any, override

from fastapi import APIRouter, FastAPI

from panther_api.problems import PROBLEM_RESPONSES, add_problem_handlers, document_problems
from panther_api.routers import health

API_PREFIX = "/api/v1"


class PantherAPI(FastAPI):
    """FastAPI, with error responses documented as problem details in the schema."""

    @override
    def openapi(self) -> dict[str, Any]:
        if not self.openapi_schema:
            self.openapi_schema = document_problems(super().openapi())
        return self.openapi_schema


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
    )
    add_problem_handlers(app)

    api = APIRouter(prefix=API_PREFIX, responses=PROBLEM_RESPONSES)
    api.include_router(health.router)
    for router in routers:
        api.include_router(router)
    app.include_router(api)

    return app


app = create_app()
