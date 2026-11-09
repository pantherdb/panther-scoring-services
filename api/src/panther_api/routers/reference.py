"""What the services' reference lists share, such as cSNP's species and refmap's organisms.

Each list comes from the engine and changes only with a new image, so it's serialised once, at
import, and every request gets the same bytes, which a browser may reuse for an hour.
"""

from collections.abc import Sequence
from typing import Any

from fastapi import Response, status
from pydantic import BaseModel
from pydantic_core import to_json

LIST_CACHE_CONTROL = "public, max-age=3600"
"""A list changes only with a new image, so a browser may reuse it for an hour."""


def list_responses(what: str) -> dict[int | str, dict[str, Any]]:
    """A list route's documented 200, such as "Every species, in the engine's order."."""
    return {
        status.HTTP_200_OK: {
            "description": f"Every {what}, in the engine's order.",
            "headers": {
                "Cache-Control": {
                    "description": f"`{LIST_CACHE_CONTROL}`",
                    "schema": {"type": "string"},
                }
            },
        },
    }


def list_json(items: Sequence[BaseModel]) -> bytes:
    """The list as the JSON body FastAPI would give for it, made once."""
    return to_json(list(items))


def list_response(body: bytes) -> Response:
    """A list's response: its bytes as they are, with the cache header."""
    return Response(
        body, media_type="application/json", headers={"Cache-Control": LIST_CACHE_CONTROL}
    )
