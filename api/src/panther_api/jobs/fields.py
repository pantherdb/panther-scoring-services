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
