"""The `csnp` job's input and result: PANTHER-PSEP coding-SNP scoring, one protein per job.

The input rules are openspec's `scoring-input`. They follow the legacy website's form
(`CsnpScoreForm.java`), which normalised the input before `snpScore.cgi` saw it; design.md of
`add-csnp-job` gives the legacy line for each. No message quotes the submitted value.

The result mirrors the engine's `panther_engine.csnp` dataclasses, field for field, and
`run_csnp()` converts between the two: it's what a worker runs for a `csnp` job. A worker process
imports this module, so keep its imports light and set up no state at import time.
"""

import re
from typing import Annotated

from panther_engine import csnp as engine
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

LONGEST_SEQUENCE = 50_000
"""Residues, after normalising: the website's limit (`errors.sequence.too.long`)."""

LONGEST_RAW_SEQUENCE = 1_000_000
"""Characters as submitted, before normalising. Bounds the work one request can cause."""

MOST_SUBSTITUTIONS = 1_000
LONGEST_SUBSTITUTION = 32

# Java's String.trim() removes every character up to U+0020 from both ends.
_TRIMMED = "".join(chr(code) for code in range(0x21))
# One header line, only at the very start, as the form's `^>[^\n]*` without MULTILINE.
_HEADER = re.compile(r"\A>[^\n]*")
# Java's `\s`: space, tab, LF, VT, FF and CR.
_WHITESPACE = re.compile(r"[ \t\n\x0b\x0c\r]+")
# Printable ASCII, without space.
_PRINTABLE = re.compile(r"[!-~]+")
_SPECIES = re.compile(r"[A-Z0-9]{1,5}")
# The legacy CGI's substitution form, after upper-casing: wild-type residue, position, residue.
_SUBSTITUTION = re.compile(r"[A-Z][0-9]+[A-Z]")


def _normalise_sequence(value: str) -> str:
    """Normalise as the website's form did: trim, drop one header line and all whitespace."""
    value = value.strip(_TRIMMED)
    if value.count(">") > 1:
        raise ValueError(
            "The sequence has more than one '>', so it holds more than one sequence. "
            "Submit one protein."
        )
    residues = _WHITESPACE.sub("", _HEADER.sub("", value))
    if not residues:
        raise ValueError("The sequence has no residues.")
    if not _PRINTABLE.fullmatch(residues):
        raise ValueError(
            "The sequence has a character that isn't printable ASCII. Use one-letter residue codes."
        )
    if len(residues) > LONGEST_SEQUENCE:
        raise ValueError(f"The sequence has more than {LONGEST_SEQUENCE:,} residues.")
    # After the ASCII check: str.upper() turns some other letters into ASCII ones (ß into SS).
    return residues.upper()


def _normalise_substitution(value: str) -> str:
    """Upper-case the token, as the website did, and keep it only in the legacy CGI's form.

    The CGI dropped any other token without a row (`snpScore.cgi` 212 to 214), so rejecting it
    loses no score. Decided with the engine developer on PR #19 (2026-10-30). The ASCII check
    comes first: str.upper() turns some other letters into ASCII ones (dotless i into I).
    """
    if not _PRINTABLE.fullmatch(value) or not _SUBSTITUTION.fullmatch(value.upper()):
        raise ValueError(
            "Each substitution must be a residue letter, a position and a residue letter, "
            "such as L46P."
        )
    return value.upper()


def _check_species(value: str) -> str:
    if not _SPECIES.fullmatch(value):
        raise ValueError(
            "The species must be a PANTHER species code of 1 to 5 upper-case letters or digits, "
            "such as HUMAN."
        )
    return value


def _check_species_scored(value: str) -> str:
    """After the shape check: a species the engine scores against, so `score()` never refuses it."""
    if value not in engine.SPECIES_CODES:
        raise ValueError(
            "cSNP scoring has no sequences for this species. Use a PANTHER species code from "
            "the cSNP data, such as HUMAN or MOUSE."
        )
    return value


Sequence = Annotated[
    str,
    Field(max_length=LONGEST_RAW_SEQUENCE),
    AfterValidator(_normalise_sequence),
]
Substitution = Annotated[
    str,
    StringConstraints(min_length=1, max_length=LONGEST_SUBSTITUTION),
    AfterValidator(_normalise_substitution),
]


class CsnpInput(BaseModel):
    """One protein, the substitutions to score in it, and its species.

    `sequence` is the protein, as plain residues or FASTA with one header line. Whitespace and
    the header are removed and letters upper-cased before scoring. `substitutions` are tokens such
    as `L46P`, positions counted from 1 in this sequence; each is upper-cased and must be a
    residue letter, a position and a residue letter. One that can't be mapped onto the sequence,
    such as a wrong wild-type residue, is reported in the result, not rejected. `species` is a
    PANTHER species code such as `HUMAN`, one of the species in cSNP's data.
    """

    model_config = ConfigDict(extra="forbid")

    sequence: Sequence
    substitutions: Annotated[list[Substitution], Field(min_length=1, max_length=MOST_SUBSTITUTIONS)]
    # Validators run in order, and the second only if the first passed: one error per species.
    species: Annotated[str, AfterValidator(_check_species), AfterValidator(_check_species_scored)]


class SubstitutionScore(BaseModel):
    """One substitution's score, as the legacy service reported it.

    `age` is how long the position has been preserved, in millions of years, and `pdel` the
    probability of a deleterious effect as the legacy two-decimal string, such as "0.50". Either
    may be null, as when the substitution wasn't scored. `message` is the legacy text: the
    prediction, or why it wasn't scored.
    """

    substitution: str
    age: int | None
    message: str
    pdel: str | None


class CsnpResult(BaseModel):
    """The PANTHER family the protein was placed in, null with no family hit, and the scores."""

    family: str | None
    scores: list[SubstitutionScore]


def run_csnp(request: CsnpInput) -> CsnpResult:
    """Score the input with the engine. Runs in a worker process, never on the event loop.

    The engine reads its data folder from `PANTHER_DATA_DIR`, which a worker inherits. Its
    exceptions pass through unchanged: the runner turns an `InputError` into a 422 problem, and
    anything else into the generic 500.
    """
    result = engine.score(
        engine.CsnpInput(
            sequence=request.sequence,
            substitutions=tuple(request.substitutions),
            species=request.species,
        )
    )
    return CsnpResult(
        family=result.family,
        scores=[
            SubstitutionScore(
                substitution=item.substitution, age=item.age, message=item.message, pdel=item.pdel
            )
            for item in result.scores
        ],
    )
