"""The `refmap` job's input and result: protein IDs mapped to PANTHER IDs, for one organism.

The input rules are openspec's `scoring-input`. The legacy website posted its input to
`genericMapping.cgi` unnormalised, so they follow the CGI, and are new where it had none;
design.md of `add-refmap-job` gives the legacy line for each, and
`docs/parity/refmap-legacy-behaviour.md` the quirks. No message quotes the submitted value.

The result mirrors the dataclasses proposed for the engine's `panther_engine.refmap`, field for
field. Until the engine maps IDs, the API answers a valid request with a 501, and nothing builds
a result. A worker process imports this module, so keep its imports light and set up no state at
import time.
"""

import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

MOST_IDS = 100_000
"""The website's limit on a mapping's lines (`ListAnalysisConstants.maxNumLinesAllowed`)."""

LONGEST_ID = 64

# A UniProt species mnemonic: the last `_` part of the legacy organism's long name.
_ORGANISM = re.compile(r"[A-Z0-9]{1,5}")
# Printable ASCII, without space.
_PRINTABLE = re.compile(r"[!-~]+")


def _check_organism(value: str) -> str:
    if not _ORGANISM.fullmatch(value):
        raise ValueError(
            "The organism must be a UniProt species code of 1 to 5 upper-case letters or "
            "digits, such as HUMAN."
        )
    return value


def _check_id(value: str) -> str:
    """Kept as submitted: the legacy lookup is exact and case-sensitive (`REFMAP-1`)."""
    if not _PRINTABLE.fullmatch(value):
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
    Field(json_schema_extra={"pattern": "^[!-~]+$"}),
]
Organism = Annotated[
    str,
    AfterValidator(_check_organism),
    Field(json_schema_extra={"pattern": "^[A-Z0-9]{1,5}$", "maxLength": 5}),
]


class RefmapInput(BaseModel):
    """One organism, and the IDs to map to PANTHER IDs in it.

    `organism` is a UniProt species code such as `HUMAN`. `ids` are the protein IDs, such as
    UniProt accessions, each looked up exactly as given: not trimmed, not upper-cased, and
    repeated IDs each get their own mapping, in order.
    """

    model_config = ConfigDict(extra="forbid")

    organism: Organism
    ids: Annotated[list[ProteinId], Field(min_length=1, max_length=MOST_IDS)]


class IdMapping(BaseModel):
    """One ID and the PANTHER ID it maps to, such as `PTHR10078:SF1`.

    `panther_id` is null for an ID with no PANTHER ID, where the legacy service said `NOHIT`.
    """

    id: str
    panther_id: str | None


class RefmapResult(BaseModel):
    """One mapping per submitted ID, in the order submitted, repeated IDs included."""

    mappings: list[IdMapping]
