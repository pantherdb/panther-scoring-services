"""Reading one protein from FASTA text, as the API normalises a submitted sequence.

For the commands that score by hand (`csnp score`, `hmmscore score`), so they score what an API job
would. The API's own normalising is `scoring-input`'s, after the legacy website's forms; it also
checks the characters, which each service's `score()` checks here.
"""

import re

# The API's normalisation (`scoring-input`), as the legacy website's form did it: trim every
# character up to U+0020, drop one header line at the very start, and all whitespace.
TRIMMED = "".join(chr(code) for code in range(0x21))
HEADER = re.compile(r"\A>[^\n]*")
WHITESPACE = re.compile(r"[ \t\n\x0b\x0c\r]+")


def read_protein(text: str) -> str:
    """One protein from a FASTA file, normalised as the API normalises it. Raises ValueError for
    more than one sequence, or none."""
    text = text.strip(TRIMMED)
    if text.count(">") > 1:
        raise ValueError("the file holds more than one sequence: give one protein")
    residues = WHITESPACE.sub("", HEADER.sub("", text))
    if not residues:
        raise ValueError("the file has no sequence")
    return residues.upper()
