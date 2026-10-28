"""Liveness check."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: Literal["ok"]


@router.get("/health", summary="Liveness check")
def health() -> Health:
    """Answer 200 while the process can serve requests. Checks no data, tools or engine."""
    return Health(status="ok")
