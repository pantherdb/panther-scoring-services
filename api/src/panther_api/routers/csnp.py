"""cSNP's reference lists. Today, the species a `csnp` job scores against, with their names."""

from fastapi import APIRouter, Response
from panther_engine.csnp import SPECIES_NAMES
from pydantic import BaseModel, ConfigDict

from panther_api.routers.reference import list_json, list_response, list_responses

router = APIRouter(prefix="/csnp", tags=["csnp"])


class CsnpSpecies(BaseModel):
    """A species cSNP scores against: its PANTHER species code, such as `HUMAN`, and its
    scientific name, such as `Homo sapiens`. The code is what a `csnp` request's `species` names.
    """

    model_config = ConfigDict(frozen=True)

    code: str
    name: str


# Built once, from the engine, in its order. The request model checks `species` against the
# same codes (jobs/csnp.py), so every listed code is accepted, and no other.
SPECIES: tuple[CsnpSpecies, ...] = tuple(
    CsnpSpecies(code=code, name=name) for code, name in SPECIES_NAMES.items()
)
_SPECIES_JSON = list_json(SPECIES)


# The response is the bytes made at import, so FastAPI documents the list but doesn't build it.
@router.get(
    "/species",
    summary="The species cSNP scores against",
    response_model=list[CsnpSpecies],
    responses=list_responses("species"),
)
async def csnp_species() -> Response:
    """Every species a `csnp` job's `species` may name, with its name, in the engine's order.

    Needs no data folder. The response may be cached for an hour.
    """
    return list_response(_SPECIES_JSON)
