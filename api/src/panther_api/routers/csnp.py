"""cSNP's reference lists. Today, the species a `csnp` job scores against, with their names."""

from typing import Any

from fastapi import APIRouter, Response, status
from panther_engine.csnp import SPECIES_NAMES
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/csnp", tags=["csnp"])

SPECIES_CACHE_CONTROL = "public, max-age=3600"
"""The list changes only with a new image, so a browser may reuse it for an hour."""


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

_SPECIES_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "description": "Every species, in the engine's order.",
        "headers": {
            "Cache-Control": {
                "description": f"`{SPECIES_CACHE_CONTROL}`",
                "schema": {"type": "string"},
            }
        },
    },
}


@router.get("/species", summary="The species cSNP scores against", responses=_SPECIES_RESPONSES)
def csnp_species(response: Response) -> list[CsnpSpecies]:
    """Every species a `csnp` job's `species` may name, with its name, in the engine's order.

    Needs no data folder. The response may be cached for an hour.
    """
    response.headers["Cache-Control"] = SPECIES_CACHE_CONTROL
    return list(SPECIES)
