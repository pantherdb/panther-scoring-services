"""The legacy scorer's readings of the library, for comparison with the strict readers.

`PANTHER_PSEP1.01.pl` at `cebb5ab` finds what it needs with unanchored patterns and fixed line
numbers. Each function here reads a file the way the Perl does, citing the Perl's lines (`PSEP:n`)
and the quirk ID from the legacy behaviour spec §6. The survey runs them beside the strict readers
on every family. Where they differ, the port has two options: use the reading here to match the
goldens, or log a divergence.

They take raw lines, with their line endings, as the strict readers do. Unlike the strict readers,
they never raise on a malformed file: like the Perl, they read what they can.
"""

import re
from collections.abc import Iterable, Sequence

SEQUENCES_START = "List of extant and reconstructed sequences"
SEQUENCES_END = "Overall"
# PSEP:388, `readCSV_getNode`. The AN is interpolated where `(\d+)` is here.
START_LABEL = re.compile(r"Node([0-9]+) AN([0-9]+)$")
# PSEP:391
NODE = re.compile(r"Node([0-9]+)")
# PSEP:118. The dots are unescaped, so each matches any character.
BRANCH = re.compile(r"([0-9]+)..([0-9]+)")
# PSEP:124 and 133
TREE_LEAF_LABEL = re.compile(r"_AN[0-9]+")
TREE_NODE = re.compile(r"([0-9]+)(,|\)|;)")
# PSEP:140
TREE_AN = re.compile(r"AN([0-9]+)(:|\])")
# PSEP:150
EVENT = re.compile(r"Ev=([0-9]>[0-9]):S=([a-zA-Z\-]+):ID=AN([0-9]+)")
# PSEP:159
SPECIES_AGE = re.compile(r":S=(([a-zA-Z]|-)+):A=([0-9]+)\]")
# PSEP:325, `getCorrectnum`, for every AN at once
SEQUENCE_LABEL = re.compile(r"AN([0-9]+)   ")
# Gene identifiers whose parts the Perl interpolates as plain text: no character with a meaning in
# a pattern, and a first part that can't match a branch length on the tree line.
PLAIN_GENE = re.compile(r"[A-Za-z][A-Za-z0-9_=\-]*\|[A-Za-z0-9_=\-]*\|[A-Za-z0-9_=\-]*")
# Characters whose meaning in a Perl pattern differs from Python's, or that Perl interpolates.
NOT_EMULATED = re.compile(r"[$@\\]")


def chomp(line: str) -> str:
    """`chomp` removes only the line feed, so a carriage return stays (PSEP:36, 327, 378)."""
    return line.removesuffix("\n")


def split_fields(line: str, separator: str) -> list[str]:
    """Perl's `split`, which drops trailing empty fields (PSEP:294, 379)."""
    fields = line.split(separator)
    while fields and not fields[-1]:
        fields.pop()
    return fields


# .paml: `readCSV_getNode` (PSEP:362-405)


def paml_rows(lines: Iterable[str]) -> tuple[list[str], list[str]]:
    """The first two rows of a `.paml` file, chomped and split as the Perl does (PSEP:377-379)."""
    rows: list[list[str]] = []
    for line in lines:
        rows.append(split_fields(chomp(line), ","))
        if len(rows) == 2:
            break
    while len(rows) < 2:
        rows.append([])
    return rows[0], rows[1]


def start_node(rows: tuple[list[str], list[str]], an: str) -> int | None:
    """The trace-back's start: the LAST column labelled `Node<k> AN<an>`, giving `k` (`SCORE-2`).

    PSEP:388 tests each column of the second row against the first row's label, unanchored at the
    start. Internal columns carry spurious AN labels that collide with leaf labels, so the last
    match is often an internal node. None where nothing matches; the Perl keeps the previous
    SNP's value instead (`SCORE-8`).
    """
    labels, parents = rows
    pattern = re.compile(rf"Node([0-9]+) AN{re.escape(an)}$")
    node = None
    for column in range(len(parents)):
        label = labels[column] if column < len(labels) else ""
        if match := pattern.search(label):
            node = int(match[1])
    return node


def start_nodes(rows: tuple[list[str], list[str]]) -> dict[str, int]:
    """`start_node` for every AN at once, keyed by the AN as written.

    A label matches `Node(\\d+) AN<an>$` only for the digits after its last ` AN`, so one search
    per label finds the one AN it can match.
    """
    labels, parents = rows
    nodes: dict[str, int] = {}
    for column in range(min(len(parents), len(labels))):
        if match := START_LABEL.search(labels[column]):
            nodes[match[2]] = int(match[1])
    return nodes


def root_node(rows: tuple[list[str], list[str]]) -> int | None:
    """The LAST column whose parent cell contains `Node<k>`, `k` from its label (PSEP:391-395).

    Unanchored, so a parent `Node123` makes column 12 a root.
    """
    labels, parents = rows
    root = None
    for column in range(len(parents)):
        label = labels[column] if column < len(labels) else ""
        if (match := NODE.search(label)) and re.search(f"Node{match[1]}", parents[column]):
            root = int(match[1])
    return root


# .rst (PSEP:100-136)


def rst_lines(lines: Iterable[str]) -> tuple[str | None, str | None]:
    """The raw lines at 0-based positions 11 and 14, the 12th and 15th (PSEP:104-116, `SCORE-9`)."""
    branch_line = None
    for count, line in enumerate(lines):
        if count == 11:
            branch_line = line
        if count == 14:
            return branch_line, line
    return branch_line, None


def branches(line: str | None) -> dict[int, int]:
    """Each child's parent from the branch list: `([0-9]+)..([0-9]+)`, unescaped dots, the last
    pair for a child winning (PSEP:118-120, `SCORE-9`)."""
    if line is None:
        return {}
    return {int(child): int(parent) for parent, child in BRANCH.findall(line)}


def tree_nodes(line: str | None) -> list[int]:
    """Node numbers in order of appearance: the line without `_AN<n>` and spaces, then each number
    followed by `,`, `)` or `;` (PSEP:124-136)."""
    if line is None:
        return []
    bare = TREE_LEAF_LABEL.sub("", line).replace(" ", "")
    return [int(match[1]) for match in TREE_NODE.finditer(bare)]


# .orig.tree (PSEP:127-153)


def tree_ans(line: str) -> list[int]:
    """AN numbers in order of appearance on the first line: `AN([0-9]+)(:|\\])` (PSEP:140-143)."""
    return [int(match[1]) for match in TREE_AN.finditer(line)]


def pairing(nodes: Sequence[int], ans: Sequence[int]) -> dict[int, int | None]:
    """The `.rst` tree's nodes zipped with the `.orig.tree` ANs, by order of appearance. A node past
    the last AN gets none (PSEP:145-148)."""
    return {node: ans[index] if index < len(ans) else None for index, node in enumerate(nodes)}


def events(line: str) -> dict[int, tuple[str, str]]:
    """Each AN's event and taxon, from `Ev=…:S=…:ID=AN…` in that order only (PSEP:150-153). A node
    with no `S`, attributes in another order or a taxon with other characters is missed."""
    return {int(an): (event, taxon) for event, taxon, an in EVENT.findall(line)}


# species_pthr8_time.nhx (PSEP:155-161)


def species_ages(line: str) -> dict[str, int]:
    """Each taxon's age from the first line: `:S=…:A=…]`, `A` last (PSEP:159-161)."""
    return {match[1]: int(match[3]) for match in SPECIES_AGE.finditer(line)}


# .rst sequences: `getCorrectnum` (PSEP:310-334)


def sequence(lines: Iterable[str], an: str) -> str | None:
    """The first line in the sequence list containing `AN<an>` and three spaces, chomped, without
    its first `AN<an>` and without spaces (PSEP:323-333).

    The list is Perl's flip-flop `/List of extant…/ .. /Overall/`: from the start line through the
    line containing `Overall`, or to the end of the file. A carriage return stays in the sequence.
    """
    for line in _sequence_list(lines):
        if f"AN{an}   " in line:
            return _sequence_of(line, an)
    return None


def sequences(lines: Iterable[str]) -> dict[str, str]:
    """`sequence` for every AN at once, keyed by the AN as written. Sequences hold no digits, so
    each line contains `AN<n>   ` only for the label `SEQUENCE_LABEL` finds."""
    found: dict[str, str] = {}
    for line in _sequence_list(lines):
        for match in SEQUENCE_LABEL.finditer(line):
            if match[1] not in found:
                found[match[1]] = _sequence_of(line, match[1])
    return found


def _sequence_list(lines: Iterable[str]) -> Iterable[str]:
    inside = False
    for line in lines:
        if not inside and SEQUENCES_START not in line:
            continue
        # `..` tests the end on the line where it starts, too.
        inside = SEQUENCES_END not in line
        yield line


def _sequence_of(line: str, an: str) -> str:
    return chomp(line).replace(f"AN{an}", "", 1).replace(" ", "")


# .orig.tree gene lookup: `findAN` (PSEP:284-305)


def find_an(lines: Iterable[str], gene: str) -> int | None:
    """The AN of the first line, the tree line included, matching `AN([0-9]+):<a>\\|<b>\\|<c>`,
    where `a|b|c` is the gene identifier split on `|`, interpolated unescaped (PSEP:294-299,
    `SCORE-8`).

    So `.` matches any character, and the last part is open-ended: a gene that is a prefix of an
    earlier gene line finds that line. Raises ValueError for a part Perl would interpolate as a
    variable, or that isn't a pattern in Python.
    """
    if NOT_EMULATED.search(gene):
        raise ValueError(f"gene {gene!r} isn't emulated: Perl would interpolate it")
    a, b, c = [*split_fields(gene, "|"), "", "", ""][:3]
    try:
        pattern = re.compile(rf"AN([0-9]+):{a}\|{b}\|{c}")
    except re.error as error:
        raise ValueError(f"gene {gene!r} isn't a pattern: {error}") from error
    for line in lines:
        if match := pattern.search(line):
            return int(match[1])
    return None


class GeneLookup:
    """`find_an` for many genes of one `.orig.tree` file that the strict reader accepted.

    When the tree line has no `|` and the gene lines no `:` after their label, a plain gene's
    pattern can only match a gene line from its start. Then the Perl's match is the first gene line
    with the same first two parts whose third part starts with the gene's. Otherwise each gene is
    looked up with `find_an`.
    """

    def __init__(self, lines: Sequence[str]) -> None:
        self.lines = lines
        self.groups: dict[tuple[str, str], list[tuple[str, int]]] = {}
        self.plain = bool(lines) and "|" not in lines[0]
        for line in lines[1:]:
            label, _, gene = chomp(line).removesuffix(";").partition(":")
            self.plain = self.plain and ":" not in gene
            a, b, c = gene.split("|", 2)
            self.groups.setdefault((a, b), []).append((c, int(label.removeprefix("AN"))))

    def find_an(self, gene: str) -> int | None:
        if not self.plain or not PLAIN_GENE.fullmatch(gene):
            return find_an(self.lines, gene)
        a, b, c = gene.split("|")
        return next((an for third, an in self.groups.get((a, b), []) if third.startswith(c)), None)


# Perl's own conversions, for both scripts


NUMBER = re.compile(r"\s*([+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)")


def lines_of(text: str) -> list[str]:
    """`text` split as Perl's `<FILE>` reads it: after each line feed only, so a carriage return
    stays in its line. The last line may have no line feed."""
    parts = text.split("\n")
    return [part + "\n" for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def numify(text: str | None) -> float:
    """A string as a Perl number: its leading decimal number, after any white space, or 0. An
    undefined value is 0 too."""
    match = NUMBER.match(text or "")
    return float(match[1]) if match else 0.0


def number_text(value: float) -> str:
    """A number as Perl prints it: whole numbers without a decimal point."""
    return str(int(value)) if value.is_integer() else f"{value:.15g}"
