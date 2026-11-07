"""The `refmap` job's input and result: protein IDs mapped to PANTHER IDs, for one organism.

The input rules are openspec's `scoring-input`. The legacy website posted its input to
`genericMapping.cgi` unnormalised, so they follow the CGI, and are new where it had none;
design.md of `add-refmap-job` gives the legacy line for each, and
`docs/parity/refmap-legacy-behaviour.md` the quirks. No message quotes the submitted value.

The result mirrors the engine's `panther_engine.refmap.RefmapResult`, field for field, and
`run_refmap` calls the engine's `map_ids` in a worker. A worker process imports this module, so
keep its imports light and set up no state at import time beyond the engine's organism list.
"""

import re
from typing import Annotated, Any, cast

from panther_engine import refmap as engine
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    ValidatorFunctionWrapHandler,
    WrapValidator,
)
from pydantic_core import InitErrorDetails

from panther_api.jobs.fields import (
    LONGEST_SPECIES_CODE,
    MOST_FIELD_ERRORS,
    PRINTABLE,
    SPECIES_CODE,
    Unlisted,
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
_PROTEIN_ID: TypeAdapter[str] = TypeAdapter(ProteinId)

VALID_ID = re.compile(rf"[!-~]{{1,{LONGEST_ID}}}")
"""What `ProteinId` accepts, in one pattern: PRINTABLE's characters, 1 to LONGEST_ID of them.
Use with `fullmatch`. tests/test_refmap_input.py checks the two agree."""

# The JSON types Pydantic never accepts as a string. A list holding anything else, such as bytes,
# which it does accept, is left to Pydantic, so the fast path can't reject what it would take.
_NOT_STRINGS = frozenset({int, float, bool, type(None), list, dict})


def _check_ids(value: Any, handler: ValidatorFunctionWrapHandler) -> list[str]:
    """Check every ID in one pass, and raise at most MOST_FIELD_ERRORS errors (#41).

    Pydantic's own check builds an error for every bad ID before the 422 can list only the first
    100: about 0.9 s on the event loop for 100,000. Here a list of the right length is checked
    against VALID_ID in one pass. A valid list is returned as it is. A list with more bad IDs
    than a 422 lists gets the errors Pydantic would give for the first ones only, each from
    `ProteinId` itself at its index, and the last one's `input` says how many more there were
    (`Unlisted`), so the 422's `detail` still gives the total. Anything else, such as a list of
    the wrong length, or few bad IDs, is Pydantic's, as before.
    """
    if not isinstance(value, list):
        return handler(value)
    items = cast(list[object], value)
    if not 1 <= len(items) <= MOST_IDS:
        return handler(value)
    bad = [
        index
        for index, item in enumerate(items)
        if type(item) is not str or not VALID_ID.fullmatch(item)
    ]
    if not bad:
        return cast(list[str], items)
    if len(bad) <= MOST_FIELD_ERRORS or any(
        type(items[index]) is not str and type(items[index]) not in _NOT_STRINGS for index in bad
    ):
        return handler(value)
    errors: list[InitErrorDetails] = []
    for index in bad[:MOST_FIELD_ERRORS]:
        try:
            _PROTEIN_ID.validate_python(items[index])
        except ValidationError as error:
            for item in error.errors(include_url=False):
                details = InitErrorDetails(
                    type=item["type"], loc=(index, *item["loc"]), input=item["input"]
                )
                if "ctx" in item:
                    details["ctx"] = item["ctx"]
                errors.append(details)
    if len(errors) != MOST_FIELD_ERRORS:
        # VALID_ID and ProteinId disagree on an item: let Pydantic check every item, as before,
        # rather than list too few errors or miscount the rest.
        return handler(value)
    errors[-1]["input"] = Unlisted(len(bad) - MOST_FIELD_ERRORS)
    raise ValidationError.from_exception_data("ids", errors)


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
    # The schema comes from `list[ProteinId]`; _check_ids checks it faster, with the same errors.
    ids: Annotated[
        list[ProteinId], Field(min_length=1, max_length=MOST_IDS), WrapValidator(_check_ids)
    ]

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
