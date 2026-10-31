"""Shapes that more than one service's input checks, written once so they can't drift.

Each service keeps its own messages, since each names its own field. A worker process imports
this module, so keep it to the standard library.
"""

import re

PRINTABLE = re.compile(r"[!-~]+")
"""Printable ASCII, without space. Use with `fullmatch`."""

SPECIES_CODE = re.compile(r"[A-Z0-9]{1,5}")
"""A species code, as PANTHER and UniProt write one, such as `HUMAN`: 1 to 5 upper-case letters
or digits. Use with `fullmatch`."""

LONGEST_SPECIES_CODE = 5


def schema_pattern(shape: re.Pattern[str]) -> str:
    """The shape as a JSON Schema `pattern`, which matches anywhere unless it's anchored."""
    return f"^{shape.pattern}$"
