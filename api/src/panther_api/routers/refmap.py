"""refmap's reference lists. Today, the organisms a `refmap` job maps for, with their names and
gene counts."""

from fastapi import APIRouter, Response
from panther_engine.refmap import ORGANISM_GENES, ORGANISM_NAMES
from pydantic import BaseModel, ConfigDict

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
