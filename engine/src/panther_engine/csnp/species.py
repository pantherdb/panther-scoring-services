"""The species tree, `species_pthr8_time.nhx`: each taxon's age in millions of years.

It's one line of Newick with `[&&NHX:S=<taxon>:A=<age>]` on internal nodes; LUCA is 4200. One node
is written `[&&NXH:…]`, a typo, and is read all the same. The format is in the legacy behaviour
spec §3.6. Only the attribute sets are read, not the tree's shape.
"""

import re
from collections.abc import Iterable

from panther_engine.csnp.library import LibraryFormatError, numbered

ATTRIBUTE_SET = re.compile(r"\[([^\[\]]*)\]")
NHX = re.compile(r"&&(?:NHX|NXH)((?::[A-Za-z]+=[^:]*)*)")
AGE = re.compile(r"[0-9]+")


def read_species(lines: Iterable[str], name: str) -> dict[str, int]:
    ages: dict[str, int] = {}
    rows = list(numbered(lines, name))
    if not rows:
        raise LibraryFormatError(name, None, "empty file")
    if len(rows) > 1:
        raise LibraryFormatError(name, 2, "more than one line")
    line = rows[0][1]
    for brackets in ATTRIBUTE_SET.finditer(line):
        match = NHX.fullmatch(brackets[1])
        if match is None:
            raise LibraryFormatError(name, 1, f"not NHX attributes: {brackets[0]!r}")
        pairs = dict(item.split("=", 1) for item in match[1].split(":")[1:])
        taxon, age = pairs.get("S"), pairs.get("A")
        if taxon is None or age is None:
            continue
        if not AGE.fullmatch(age):
            raise LibraryFormatError(name, 1, f"{taxon}'s age isn't a whole number: {age!r}")
        if taxon in ages:
            raise LibraryFormatError(name, 1, f"{taxon} appears twice")
        ages[taxon] = int(age)
    if not ages:
        raise LibraryFormatError(name, 1, "no taxon with an age")
    return ages
