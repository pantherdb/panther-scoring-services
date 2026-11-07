"""The `refmap` job's input and result: protein IDs mapped to PANTHER IDs, for one organism.

The input rules are openspec's `scoring-input`. The legacy website posted its input to
`genericMapping.cgi` unnormalised, so they follow the CGI, and are new where it had none;
design.md of `add-refmap-job` gives the legacy line for each, and
`docs/parity/refmap-legacy-behaviour.md` the quirks. No message quotes the submitted value.

The result mirrors the engine's `panther_engine.refmap.RefmapResult`, field for field, and
`run_refmap` calls the engine's `map_ids` in a worker. A worker process imports this module, so
keep its imports light and set up no state at import time beyond the engine's organism list.
"""

from typing import Annotated

from panther_engine import refmap as engine
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from panther_api.jobs.fields import (
    LONGEST_SPECIES_CODE,
    PRINTABLE,
    SPECIES_CODE,
    count,
    schema_pattern,
)

MOST_IDS = 100_000
"""The website's limit on a mapping's lines (`ListAnalysisConstants.maxNumLinesAllowed`)."""

LONGEST_ID = 64


def _check_organism(value: str) -> str:
    """One of the engine's organisms: the UniProt species mnemonic ending its long name. The shape
    is checked first, so no other value is looked up."""
    if not SPECIES_CODE.fullmatch(value) or value not in engine.ORGANISM_CODES:
        raise ValueError(
            "The organism must be the code of an organism refmap maps for, such as ENDPU. "
            "GET /api/v1/refmap/organisms lists them."
        )
    return value


def _check_id(value: str) -> str:
    """Kept as submitted: the legacy lookup is exact and case-sensitive (`REFMAP-1`)."""
    if not PRINTABLE.fullmatch(value):
        raise ValueError(
            f"Each ID must be 1 to {LONGEST_ID} printable ASCII characters, with no spaces, "
            "such as P04217."
        )
    return value


# The schema carries each rule as a `pattern`, so clients learn it from the contract. Only the
# schema: the validators enforce it, with messages a pattern mismatch wouldn't give.
ProteinId = Annotated[
    str,
    StringConstraints(min_length=1, max_length=LONGEST_ID),
    AfterValidator(_check_id),
    Field(json_schema_extra={"pattern": schema_pattern(PRINTABLE)}),
]
Organism = Annotated[
    str,
    AfterValidator(_check_organism),
    Field(
        json_schema_extra={
            "pattern": schema_pattern(SPECIES_CODE),
            "maxLength": LONGEST_SPECIES_CODE,
        }
    ),
]


class RefmapInput(BaseModel):
    """One organism, and the IDs to map to PANTHER IDs in it.

    `organism` is the code of an organism refmap maps for, such as `ENDPU`. `ids` are the protein
    IDs, such as UniProt accessions, each looked up exactly as given: not trimmed, not
    upper-cased, and repeated IDs each get their own mapping, in order.
    """

    model_config = ConfigDict(extra="forbid")

    organism: Organism
    ids: Annotated[list[ProteinId], Field(min_length=1, max_length=MOST_IDS)]

    def log_summary(self) -> str:
        """The input's size for the log: the organism and a count, never the IDs."""
        return f"{self.organism}, {count(len(self.ids), 'ID')}"


class IdMapping(BaseModel):
    """One ID and the PANTHER ID it maps to, such as `PTHR10078:SF1`.

    `panther_id` is null for an ID with no PANTHER ID, where the legacy service said `NOHIT`.
    """

    id: str
    panther_id: str | None


class RefmapResult(BaseModel):
    """The organism mapped against, and one mapping per submitted ID, in the order submitted,
    repeated IDs included."""

    organism: str
    mappings: list[IdMapping]


def run_refmap(request: RefmapInput) -> RefmapResult:
    """Map the IDs with the engine. Runs in a worker process, never on the event loop.

    The engine reads its data folder from `PANTHER_DATA_DIR`, which a worker inherits. Its
    exceptions pass through: the input was checked here first, so the engine's `ValueError` is a
    bug, and it and a missing data file (`MissingDataError`) fail the job with the generic 500.
    """
    result = engine.map_ids(engine.RefmapInput(organism=request.organism, ids=tuple(request.ids)))
    return RefmapResult(
        organism=result.organism,
        mappings=[IdMapping(id=item.id, panther_id=item.panther_id) for item in result.mappings],
    )
