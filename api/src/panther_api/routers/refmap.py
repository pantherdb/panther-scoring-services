"""refmap's reference data: the organisms a `refmap` job maps for, with their names and gene
counts, and each organism's whole classification file."""

import gzip
import logging
import time
from collections.abc import Iterator
from http import HTTPStatus
from pathlib import Path as FilePath
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Path, Response, status
from fastapi.responses import StreamingResponse
from panther_engine.core.data import DataFolderError
from panther_engine.refmap import (
    ORGANISM_CODES,
    ORGANISM_GENES,
    ORGANISM_NAMES,
    classification_json_file,
)
from pydantic import BaseModel, ConfigDict

from panther_api.jobs.fields import LONGEST_SPECIES_CODE, SPECIES_CODE, schema_pattern
from panther_api.jobs.refmap import RefmapResult
from panther_api.problems import (
    NO_VALIDATION_PROBLEM,
    UNEXPECTED_DETAIL,
    Problem,
    problem_response,
)
from panther_api.routers.reference import list_json, list_response, list_responses

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/refmap", tags=["refmap"])


class RefmapOrganism(BaseModel):
    """An organism refmap maps for: its UniProt species code, such as `ENDPU`, which a `refmap`
    request's `organism` names; its name, such as `Endocarpon pusillum`; how many genes its
    classification file holds; and how many of them have a PANTHER ID.
    """

    model_config = ConfigDict(frozen=True)

    code: str
    name: str
    genes: int
    genes_with_panther_id: int


# Built once, from the engine, in its order. The request model checks `organism` against the same
# codes (jobs/refmap.py), so every listed code is accepted, and no other.
ORGANISMS: tuple[RefmapOrganism, ...] = tuple(
    RefmapOrganism(
        code=code,
        name=name,
        genes=ORGANISM_GENES[code].genes,
        genes_with_panther_id=ORGANISM_GENES[code].genes_with_panther_id,
    )
    for code, name in ORGANISM_NAMES.items()
)
# 1,533 entries, about 110 KB: serialised once, not on every request (review of #64).
_ORGANISMS_JSON = list_json(ORGANISMS)


# The response is the bytes made at import, so FastAPI documents the list but doesn't build it.
@router.get(
    "/organisms",
    summary="The organisms refmap maps for",
    response_model=list[RefmapOrganism],
    responses=list_responses("organism"),
)
async def refmap_organisms() -> Response:
    """Every organism a `refmap` job's `organism` may name, with its name and gene counts, in the
    engine's order.

    Needs no data folder. The response may be cached for an hour.
    """
    return list_response(_ORGANISMS_JSON)


# No form shows it, so it can name the list (unlike a job's organism message, review of #64).
ORGANISM_NOT_FOUND = (
    "refmap doesn't map for an organism with that code. "
    "GET /api/v1/refmap/organisms lists every code it does."
)
# What the file is sent in, read a piece at a time.
CHUNK = 64 * 1024
# A missing file is logged at most once in this long, as a job's unexpected error is
# (api/CLAUDE.md, "The log"), so repeated requests don't flood the log.
MISSING_LOG_SECONDS = 600.0


class _MissingLog:
    """Logs a missing classification JSON at most once in `MISSING_LOG_SECONDS`."""

    def __init__(self) -> None:
        self._last: float | None = None

    def error(self, message: str, *args: object) -> None:
        now = time.monotonic()
        if self._last is not None and now - self._last < MISSING_LOG_SECONDS:
            return
        self._last = now
        logger.error(message, *args)


_missing = _MissingLog()


def accepts_gzip(accept_encoding: str | None) -> bool:
    """Whether an `Accept-Encoding` header accepts gzip: `gzip` listed, without `q=0`."""
    for part in (accept_encoding or "").split(","):
        name, *params = (piece.strip() for piece in part.split(";"))
        if name.lower() == "gzip":
            return not any(
                param.replace(" ", "") in ("q=0", "q=0.0", "q=0.00", "q=0.000") for param in params
            )
    return False


def _chunks(path: FilePath) -> Iterator[bytes]:
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK):
            yield chunk


def _gunzipped_chunks(path: FilePath) -> Iterator[bytes]:
    with gzip.open(path, "rb") as stream:
        while chunk := stream.read(CHUNK):
            yield chunk


@router.get(
    "/organisms/{code}/classification",
    summary="Every gene of an organism, with its PANTHER ID",
    response_model=RefmapResult,
    responses={
        status.HTTP_200_OK: {
            "description": "Every gene in the organism's classification file, one mapping per "
            "line, in the file's order, with its PANTHER ID, or null where the file says "
            "`NOHIT`. Sent gzipped (`Content-Encoding: gzip`) when the request accepts gzip.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": Problem,
            "description": "No organism refmap maps for has that code.",
        },
    },
    # `code` is a plain string and every bad value is a 404, so no 422 is possible.
    openapi_extra={NO_VALIDATION_PROBLEM: True},
)
async def refmap_classification(
    # The schema documents the shape; the route checks the code against the engine's list.
    code: Annotated[
        str,
        Path(
            description="The organism's UniProt species code, such as `ENDPU`.",
            json_schema_extra={
                "pattern": schema_pattern(SPECIES_CODE),
                "maxLength": LONGEST_SPECIES_CODE,
            },
        ),
    ],
    accept_encoding: Annotated[str | None, Header(include_in_schema=False)] = None,
) -> Response:
    """Every gene of the organism and its PANTHER ID, one mapping per line of its classification
    file, in the file's order, in the shape of a `refmap` job's result. For clients that need the
    whole organism rather than some IDs: the PANTHER website uses it as the reference list of a
    gene list analysis, where it read data.pantherdb.org's
    `generic_mapping/panther_classification/<long name>`.

    The response is built ahead of time (`panther-engine refmap data build-json`) and sent from
    disk as it is, a piece at a time: nothing is built or kept in memory, and no cache header or
    ETag is sent. The code is checked against the engine's organisms before any path is built
    from it. Without the built file, the request fails with the generic 500.
    """
    if code not in ORGANISM_CODES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ORGANISM_NOT_FOUND)
    try:
        path = classification_json_file(code)
        size = path.stat().st_size
    except (DataFolderError, OSError) as error:
        _missing.error("can't send the classification of %s: %s", code, error)
        failed = HTTPStatus.INTERNAL_SERVER_ERROR
        problem = Problem(title=failed.phrase, status=failed, detail=UNEXPECTED_DETAIL)
        return problem_response(problem)
    headers = {"Vary": "Accept-Encoding"}
    if accepts_gzip(accept_encoding):
        headers |= {"Content-Encoding": "gzip", "Content-Length": str(size)}
        chunks = _chunks(path)
    else:
        chunks = _gunzipped_chunks(path)
    return StreamingResponse(chunks, media_type="application/json", headers=headers)
