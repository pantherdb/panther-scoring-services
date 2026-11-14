"""Shapes that more than one service's input checks, written once so they can't drift.

Each service keeps its own messages, since each names its own field. A worker process imports
this module, so keep it to the standard library.
"""

import re
from dataclasses import dataclass

PRINTABLE = re.compile(r"[!-~]+")
"""Printable ASCII, without space. Use with `fullmatch`."""

SPECIES_CODE = re.compile(r"[A-Z0-9]{1,5}")
"""A species code, as PANTHER and UniProt write one, such as `HUMAN`: 1 to 5 upper-case letters
or digits. Use with `fullmatch`."""

LONGEST_SPECIES_CODE = 5

LONGEST_RAW_SEQUENCE = 1_000_000
"""Characters as submitted, before normalising: every service's limit on a protein sequence.
Bounds the work one request can cause."""

# Java's String.trim() removes every character up to U+0020 from both ends.
_TRIMMED = "".join(chr(code) for code in range(0x21))
# One header line, only at the very start, as the form's `^>[^\n]*` without MULTILINE.
_HEADER = re.compile(r"\A>[^\n]*")
# Java's `\s`: space, tab, LF, VT, FF and CR.
_WHITESPACE = re.compile(r"[ \t\n\x0b\x0c\r]+")
_LETTER = re.compile(r"[A-Za-z]")


@dataclass(frozen=True)
class SequenceRules:
    """The characters a service's sequence may hold once normalised, and its messages, none of
    which may quote the submitted value."""

    characters: re.Pattern[str]
    """The whole sequence once normalised, before upper-casing. Used with `fullmatch`."""
    more_than_one: str
    """The message for more than one `>`."""
    no_residues: str
    """The message for nothing left once the header and whitespace are removed, and, when
    `needs_a_letter`, for no letter among what's left."""
    not_residues: str
    """The message for a character `characters` doesn't allow."""
    needs_a_letter: bool = False
    """Refuse a sequence of allowed characters with no letter among them, such as hmmscore's
    lone `*`, with `no_residues`. cSNP's rules leave it unset, so its behaviour is unchanged."""


def normalise_sequence(value: str, rules: SequenceRules) -> str:
    """Normalise a protein sequence as cSNP's website form did, and check its characters: trim,
    refuse a second `>`, drop one header line and all whitespace, check the characters, and, if
    the rules ask, that a letter is among them, then upper-case.

    cSNP's form is `CsnpScoreForm.java` (openspec add-csnp-job, design.md); hmmscore applies the
    same normalising (openspec add-hmmscore-job, design.md, decision 3). Each service checks its
    own length after this.
    """
    value = value.strip(_TRIMMED)
    if value.count(">") > 1:
        raise ValueError(rules.more_than_one)
    residues = _WHITESPACE.sub("", _HEADER.sub("", value))
    if not residues:
        raise ValueError(rules.no_residues)
    if not rules.characters.fullmatch(residues):
        raise ValueError(rules.not_residues)
    # After the character check, so a refused character gets its own message wherever it is.
    if rules.needs_a_letter and not _LETTER.search(residues):
        raise ValueError(rules.no_residues)
    # After the character check: str.upper() turns some other letters into ASCII ones (ß into SS).
    return residues.upper()


def schema_pattern(shape: re.Pattern[str]) -> str:
    """The shape as a JSON Schema `pattern`, which matches anywhere unless it's anchored."""
    return f"^{shape.pattern}$"


def count(number: int, noun: str) -> str:
    """`1 substitution`, `3 substitutions`: a count for the log, with its noun."""
    return f"{number} {noun}" + ("" if number == 1 else "s")


MOST_FIELD_ERRORS = 100
"""The most field errors a 422 lists. A list such as refmap's 100,000 IDs could otherwise give
a problem body of megabytes, built and serialised on the event loop."""


@dataclass(frozen=True)
class Unlisted:
    """How many more of a list's items failed than its validator raised errors for.

    A list validator that stops at MOST_FIELD_ERRORS puts this in place of its last error's
    `input`, which no response or log shows, so the 422's `detail` can still give the total
    (problems.py). Never built from a request: JSON can't hold one.
    """

    count: int
