"""The `hmmscore` job's input and result: one protein scored against PANTHER's HMM library.

The input rules are openspec's `scoring-input`. The sequence is normalised as cSNP's is, after the
legacy website's form (`SequenceSearchForm.java`), then holds only what HMMER 3.1b2 and 3.4 score
alike: letters, `.`, `_`, `~` and `*`, with at least one letter. design.md of `add-hmmscore-job`
gives the legacy line for each rule (decision 3), and `docs/parity/hmmscore-legacy-behaviour.md`
the quirks. No message quotes the submitted value. The residue limit is a setting, so the router
checks it, not the model (decision 7).

The result mirrors the dataclasses proposed for the engine's `panther_engine.hmmscore`, field for
field (decision 4). Until the engine scores, the API answers a valid request with a 501, and
nothing builds a result. A worker process imports this module, so keep its imports light and set
up no state at import time.
"""

import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from panther_api.jobs.fields import (
    LONGEST_RAW_SEQUENCE,
    SequenceRules,
    count,
    normalise_sequence,
)

STOP = "*"
"""A stop. A final one, which translated sequences often end with, isn't counted as a residue."""

_SEQUENCE_RULES = SequenceRules(
    # Letters in either case, and `.`, `_`, `~` and `*` anywhere: what 3.1b2 and 3.4 score alike on
    # amd64, measured by the engine developer on 2026-11-13 (design.md, decision 3). `-`, which
    # 3.4 refuses, and everything else are divergence row 12. With no letter, such as a lone `*`,
    # the reference answered no hit, so it gets `no_residues` (needs_a_letter).
    characters=re.compile(r"[A-Za-z._~*]+"),
    needs_a_letter=True,
    more_than_one=(
        "The sequence has more than one '>', so it holds more than one sequence. "
        "Submit one protein."
    ),
    no_residues="The sequence has no residues.",
    not_residues=(
        "The sequence must be one-letter residue codes, the letters A to Z, and may also hold "
        ". _ ~ and *. Remove any -, digit, other punctuation or other character."
    ),
)


def _normalise_sequence(value: str) -> str:
    """Normalise as cSNP's sequence is, then keep only letters, `.`, `_`, `~` and `*`, with at
    least one letter."""
    return normalise_sequence(value, _SEQUENCE_RULES)


Sequence = Annotated[
    str,
    Field(max_length=LONGEST_RAW_SEQUENCE),
    AfterValidator(_normalise_sequence),
]


class HmmscoreInput(BaseModel):
    """One protein to score against PANTHER's HMM library.

    `sequence` is the protein, as plain residues or FASTA with one header line. Whitespace and the
    header are removed and letters upper-cased before scoring. It may hold only the letters A to
    Z, `.`, `_`, `~` and `*`, and at least one letter. It may have at most as many residues as the
    API is configured to take, 10,000 by default and never more: every character counts but a
    final `*`. A longer sequence is a 422 naming the limit.
    """

    model_config = ConfigDict(extra="forbid")

    sequence: Sequence

    @property
    def residues(self) -> int:
        """The sequence's residues: every position `hmmscan` reads, so every character but a
        final `*`. `.`, `_`, `~` and an inner `*` count."""
        return len(self.sequence.removesuffix(STOP))

    def log_summary(self) -> str:
        """The input's size for the log: the residues, never the sequence."""
        return count(self.residues, "residue")


class HmmHit(BaseModel):
    """The best-scoring PANTHER HMM, as the legacy service reported it, with its name and score.

    `panther_id` is the family or subfamily, such as `PTHR10000:SF1`. `name` is its name in the
    library's `names.tab`. `evalue` and `score` are the full-sequence E-value and bit score as
    `hmmscan` printed them. `alignment` is `hmmsearch`'s domain annotation of the sequence against
    the model, as the legacy page showed it.
    """

    panther_id: str
    name: str
    evalue: str
    score: str
    alignment: str


class HmmscoreResult(BaseModel):
    """The best hit, or null when there's none, or the best hit's full-sequence E-value is over
    1e-3, as the legacy service applied its cutoff."""

    hit: HmmHit | None
