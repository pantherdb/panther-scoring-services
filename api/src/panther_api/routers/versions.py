"""The API, engine and tool versions, as read when the app started."""

from fastapi import APIRouter, Request

from panther_api.versions import Versions

router = APIRouter(tags=["versions"])


@router.get("/versions", summary="API, engine and tool versions")
def versions(request: Request) -> Versions:
    """The versions read when the app started. A missing tool has a null version. Runs no tool."""
    return request.app.state.versions
