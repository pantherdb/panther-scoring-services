"""refmap's reference data: the organisms a `refmap` job maps for, with their names and gene
counts, and each organism's whole classification file."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response, status
from fastapi.concurrency import run_in_threadpool
from panther_engine.core.data import MissingDataError
from panther_engine.refmap import ORGANISM_CODES, ORGANISM_GENES, ORGANISM_NAMES
from panther_engine.refmap.mapping import ENCODING, classification_file, panther_id_of
from pydantic import BaseModel, ConfigDict
from pydantic_core import to_json

from panther_api.jobs.fields import LONGEST_SPECIES_CODE, SPECIES_CODE, schema_pattern
from panther_api.jobs.refmap import RefmapResult
from panther_api.routers.reference import list_json, list_response, list_responses

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


ORGANISM_NOT_FOUND = "There is no organism with that code that refmap maps for, such as ENDPU."


def classification_json(code: str) -> bytes:
    """The organism's classification file as a `RefmapResult`'s JSON: one mapping per line, in the
    file's order, repeated IDs included. Runs off the event loop.

    Each line is read as `map_panther.pl` reads it (engine `read_classification`): lines end at
    `\\n`, the ID is the text before the first tab, and the PANTHER ID the text after it, up to
    the next tab. `NOHIT`, or no tab, is null, as in a `refmap` job's result.

    Raises MissingDataError, naming the file, if it is missing or can't be read.
    """
    path = classification_file(code)
    try:
        lines = path.read_bytes().decode(ENCODING).split("\n")
    except OSError as error:
        raise MissingDataError(f"can't read the classification file {path}: {error}") from error
    if lines[-1] == "":
        lines.pop()
    mappings: list[dict[str, str | None]] = []
    for line in lines:
        key, tab, rest = line.partition("\t")
        mappings.append(
            {"id": key, "panther_id": panther_id_of(rest.partition("\t")[0] if tab else None)}
        )
    return to_json({"organism": code, "mappings": mappings})


@router.get(
    "/organisms/{code}/classification",
    summary="Every gene of an organism, with its PANTHER ID",
    response_model=RefmapResult,
    responses={
        status.HTTP_200_OK: {
            "description": "Every gene in the organism's classification file, in the file's "
            "order, with its PANTHER ID, or null where the file says `NOHIT`.",
        },
        status.HTTP_404_NOT_FOUND: {"description": "No organism refmap maps for has that code."},
    },
)
async def refmap_classification(
    # The schema carries the rule; the route checks it, so any other code is a 404, not a 422.
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
) -> Response:
    """Every gene of the organism and its PANTHER ID, in the shape of a `refmap` job's result, from
    the same classification file a job reads. For clients that need the whole organism rather
    than some IDs: the PANTHER website uses it as the reference list of a gene list analysis,
    where it read data.pantherdb.org's `generic_mapping/panther_classification/<long name>`.

    The code is checked against the engine's organisms before any path is built from it. A
    missing file fails with the generic 500, as a `refmap` job does. Nothing is kept: each
    request reads the file and builds its response, and no cache header is sent.
    """
    if not SPECIES_CODE.fullmatch(code) or code not in ORGANISM_CODES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=ORGANISM_NOT_FOUND)
    body = await run_in_threadpool(classification_json, code)
    return Response(body, media_type="application/json")
