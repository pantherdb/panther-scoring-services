"""`pantherScore.pl`'s own readings of the library, beside the strict readers in library.py.

Each cites its lines in `pantherScoring/pantherScore.pl` at `89ea0ae`; the code is unchanged since
`d7b28ee`. The survey counts where these differ from the strict readers, and the port matches them
where M1's parity needs it.
"""

import re

# /^SF\d+/: anchored at its start only, so `SF5x` matches too.
SUBFAMILY_PART = re.compile(r"SF[0-9]")


def names_key(line: str) -> str:
    """`getHmmNames`'s key for a `names.tab` line (299 to 310).

    `chomp` drops a final line feed only (305). The whole line is split on `.` (307), so its tab
    doesn't stop the split. The key is the first part, then `:` and the second part, unless that
    is false in Perl, `""` or `"0"`, or is `mag` (308 and 309). A later line with the same key
    replaces an earlier one (310).
    """
    parts = line.removesuffix("\n").split(".")
    book = parts[0]
    subfamily = parts[1] if len(parts) > 1 else ""
    if subfamily in ("", "0", "mag"):
        return book
    return f"{book}:{subfamily}"


def model_id(name: str) -> str:
    """`runHmmscan`'s HMM ID for a model name (387 to 389).

    The name is split on `.`. The ID is the first part, then `:` and the second part if that
    matches `/^SF\\d+/`.
    """
    parts = name.split(".")
    family = parts[0]
    subfamily = parts[1] if len(parts) > 1 else ""
    if SUBFAMILY_PART.match(subfamily):
        return f"{family}:{subfamily}"
    return family
