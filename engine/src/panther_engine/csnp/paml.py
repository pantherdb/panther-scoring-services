"""The `.paml` file of a family: each node's reconstructed residue and its posterior, per site.

The format is in the legacy behaviour spec §3.5. It's CSV:

- line 1: `Node number`, then `Node<k> AN<n>` for column `k`;
- line 2: `root number`, then each column's parent, `Node<p>`. The root is its own parent;
- line 3: `Branch`, then branch lengths;
- lines `2s+2` and `2s+3`: `Site s` with a residue per column (`-` for a gap), and
  `Probability of site s` with a posterior per column.

Where PAML couldn't reconstruct a node's residue, the file has a NUL byte as the residue and
` -nan` as the probability. `PTHR10366` has such cells. They are read only as that pair.

Reading a site reads the file up to it, never more, and never holds the file.
"""

import math
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from panther_engine.csnp.library import LibraryFormatError, numbered

UNRECONSTRUCTED_RESIDUE = "\x00"
UNRECONSTRUCTED_PROBABILITY = " -nan"

# Internal-node columns can have no AN: `Node1454 `. Leaf columns always have one.
LABEL = re.compile(r"Node([0-9]+) (?:AN([0-9]+))?")
PARENT = re.compile(r"Node([0-9]+)")
BRANCHES = re.compile(r"Branch((?:,[0-9]+(?:\.[0-9]+)?)*)")
# The cells of a site row, after the label, with the commas taken out: one residue each.
RESIDUES = re.compile(r"[A-Z\-\x00]*")
# The cells of a probability row, after the label: each between 0 and 1, or the unreconstructed
# ` -nan`. The survey checks every row of the library with these patterns.
PROBABILITIES = re.compile(r"(?:,(?:0(?:\.[0-9]+)?|1(?:\.0+)?| -nan))*")


@dataclass(frozen=True)
class PamlHeader:
    """Column `k` is node `k`: its AN label is `ans[k - 1]` and its parent `parents[k - 1]`.

    The AN labels of internal columns aren't real AN ids (`SCORE-2`), and some are None.
    """

    ans: tuple[int | None, ...]
    parents: tuple[int, ...]
    root: int

    @property
    def columns(self) -> int:
        return len(self.ans)

    @property
    def leaves(self) -> range:
        """The leaf columns: those below the root."""
        return range(1, self.root)


@dataclass(frozen=True)
class Site:
    """Each column's residue (None where unreconstructed) and probability (NaN there)."""

    number: int
    residues: tuple[str | None, ...]
    probabilities: tuple[float, ...]


@dataclass(frozen=True)
class PamlSummary:
    """A whole `.paml` file checked: its header, its site count and its unreconstructed cells."""

    header: PamlHeader
    sites: int
    unreconstructed: int


def read_header(lines: Iterable[str], name: str) -> PamlHeader:
    return _header(numbered(lines, name), name)


def read_site(lines: Iterable[str], name: str, site: int) -> Site:
    """Site `site`'s residues and probabilities. Rows before it are checked only by their label."""
    if site < 1:
        raise ValueError(f"sites are numbered from 1, not {site}")
    rows = numbered(lines, name)
    header = _header(rows, name)
    for number, line in rows:
        current, is_probability = divmod(number - 2, 2)
        if current < site:
            _check_label(number, line, current, name, probability=is_probability == 1)
            continue
        return _site(rows, number, line, current, header.columns, name)
    raise LibraryFormatError(name, None, f"no site {site}")


def _site(
    rows: Iterator[tuple[int, str]], number: int, line: str, site: int, columns: int, name: str
) -> Site:
    """Site `site` from its residue row, `line`, and the probability row after it."""
    residues = _residues(number, line, site, columns, name)
    probability_number, probability_line = _next_row(rows, number, site, name)
    probabilities = _probabilities(probability_number, probability_line, site, columns, name)
    _pair_unreconstructed(probability_number, residues, probabilities, name)
    return Site(
        site,
        tuple(None if cell == UNRECONSTRUCTED_RESIDUE else cell for cell in residues),
        tuple(
            math.nan if cell == UNRECONSTRUCTED_PROBABILITY else float(cell)
            for cell in probabilities
        ),
    )


def read_sites(
    lines: Iterable[str], name: str, sites: Iterable[int]
) -> tuple[PamlHeader, dict[int, Site]]:
    """The header, and each of `sites` the file has, in one pass that stops after the last one
    needed. A site past the file's last is absent from the result, not an error. Rows of other
    sites are checked only by their label, as `read_site` checks them."""
    wanted = set(sites)
    if any(site < 1 for site in wanted):
        raise ValueError(f"sites are numbered from 1, not {min(wanted)}")
    rows = numbered(lines, name)
    header = _header(rows, name)
    found: dict[int, Site] = {}
    last = max(wanted, default=0)
    for number, line in rows:
        current, is_probability = divmod(number - 2, 2)
        if current > last:
            break
        if current not in wanted:
            _check_label(number, line, current, name, probability=is_probability == 1)
            continue
        found[current] = _site(rows, number, line, current, header.columns, name)
        if current == last:
            break
    return header, {site: found[site] for site in sorted(found)}


def iter_sites(lines: Iterable[str], name: str) -> tuple[PamlHeader, Iterator[Site]]:
    """The header, and each site in turn, read as it's needed: the file is never held."""
    rows = numbered(lines, name)
    header = _header(rows, name)

    def sites() -> Iterator[Site]:
        for site, (number, line) in enumerate(rows, 1):
            yield _site(rows, number, line, site, header.columns, name)

    return header, sites()


def read_paml(lines: Iterable[str], name: str) -> PamlSummary:
    """Check every row of a `.paml` file, without holding it."""
    rows = numbered(lines, name)
    header = _header(rows, name)
    sites = 0
    unreconstructed = 0
    for number, line in rows:
        site = sites + 1
        residues = _residues(number, line, site, header.columns, name)
        probability_number, probability_line = _next_row(rows, number, site, name)
        probabilities = _probabilities(
            probability_number, probability_line, site, header.columns, name
        )
        unreconstructed += _pair_unreconstructed(probability_number, residues, probabilities, name)
        sites = site
    return PamlSummary(header, sites, unreconstructed)


def _header(rows: Iterator[tuple[int, str]], name: str) -> PamlHeader:
    labels = _cells(rows, 1, "Node number", name)
    ans: list[int | None] = []
    for column, cell in enumerate(labels, 1):
        match = LABEL.fullmatch(cell)
        if match is None or int(match[1]) != column:
            raise LibraryFormatError(
                name, 1, f"column {column} is {cell!r}, not 'Node{column} AN<n>'"
            )
        ans.append(None if match[2] is None else int(match[2]))

    parent_cells = _cells(rows, 2, "root number", name)
    if len(parent_cells) != len(labels):
        raise LibraryFormatError(name, 2, f"{len(parent_cells)} parents for {len(labels)} columns")
    parents: list[int] = []
    for column, cell in enumerate(parent_cells, 1):
        match = PARENT.fullmatch(cell)
        if match is None:
            raise LibraryFormatError(
                name, 2, f"column {column}'s parent is {cell!r}, not 'Node<p>'"
            )
        parents.append(int(match[1]))
    roots = [column for column, parent in enumerate(parents, 1) if parent == column]
    if not roots:
        raise LibraryFormatError(name, 2, "no root: no column is its own parent")
    if len(roots) > 1:
        raise LibraryFormatError(name, 2, f"more than one root: columns {roots}")
    for column, parent in enumerate(parents, 1):
        if parent > len(labels):
            raise LibraryFormatError(
                name, 2, f"column {column}'s parent, Node{parent}, isn't a column"
            )
    unlabelled = [column for column in range(1, roots[0]) if ans[column - 1] is None]
    if unlabelled:
        raise LibraryFormatError(name, 1, f"leaf column {unlabelled[0]} has no AN")

    number, line = _next_row(rows, 2, 0, name, expected="the Branch row")
    match = BRANCHES.fullmatch(line)
    if match is None or match[1].count(",") != len(labels):
        raise LibraryFormatError(name, number, f"not a Branch row of {len(labels)} lengths")
    return PamlHeader(tuple(ans), tuple(parents), roots[0])


def _cells(rows: Iterator[tuple[int, str]], number: int, label: str, name: str) -> list[str]:
    row = next(rows, None)
    if row is None:
        raise LibraryFormatError(
            name, None, "empty file" if number == 1 else f"ends at line {number - 1}"
        )
    cells = row[1].split(",")
    if cells[0] != label:
        raise LibraryFormatError(name, number, f"starts {cells[0]!r}, not {label!r}")
    return cells[1:]


def _next_row(
    rows: Iterator[tuple[int, str]], number: int, site: int, name: str, expected: str = ""
) -> tuple[int, str]:
    row = next(rows, None)
    if row is None:
        raise LibraryFormatError(
            name, number, f"ends before {expected or f'the probability row of site {site}'}"
        )
    return row


def _check_label(number: int, line: str, site: int, name: str, *, probability: bool) -> None:
    label = f"Probability of site {site}," if probability else f"Site {site},"
    if not line.startswith(label):
        raise LibraryFormatError(name, number, f"doesn't start {label!r}")


def _residues(number: int, line: str, site: int, columns: int, name: str) -> str:
    """The row's residues, one character per column, from a `Site` row checked whole."""
    label = f"Site {site}"
    cells = line[len(label) :]
    if (
        not line.startswith(label)
        or len(cells) != 2 * columns
        or cells[::2] != "," * columns
        or RESIDUES.fullmatch(cells[1::2]) is None
    ):
        raise LibraryFormatError(
            name, number, f"not a row 'Site {site}' of {columns} residues: {_preview(line)}"
        )
    return cells[1::2]


def _probabilities(number: int, line: str, site: int, columns: int, name: str) -> list[str]:
    label = f"Probability of site {site}"
    if (
        not line.startswith(label)
        or PROBABILITIES.fullmatch(line, len(label)) is None
        or line.count(",") != columns
    ):
        bad = _first_bad_probability(line, label)
        raise LibraryFormatError(
            name,
            number,
            f"not a row '{label}' of {columns} probabilities"
            + (f": {bad!r} isn't a probability" if bad is not None else f": {_preview(line)}"),
        )
    return line[len(label) + 1 :].split(",")


def _pair_unreconstructed(number: int, residues: str, probabilities: list[str], name: str) -> int:
    """The number of unreconstructed cells. Each NUL residue must pair with ` -nan`."""
    if UNRECONSTRUCTED_RESIDUE not in residues and UNRECONSTRUCTED_PROBABILITY not in probabilities:
        return 0
    count = 0
    for column, (residue, probability) in enumerate(zip(residues, probabilities, strict=True), 1):
        nul = residue == UNRECONSTRUCTED_RESIDUE
        nan = probability == UNRECONSTRUCTED_PROBABILITY
        if nul != nan:
            raise LibraryFormatError(
                name,
                number,
                f"column {column}: residue {residue!r} with probability {probability!r}",
            )
        count += nul
    return count


def _first_bad_probability(line: str, label: str) -> str | None:
    if not line.startswith(label + ","):
        return None
    for cell in line[len(label) + 1 :].split(","):
        if PROBABILITIES.fullmatch("," + cell) is None:
            return cell
    return None


def _preview(line: str) -> str:
    return repr(line if len(line) <= 60 else line[:57] + "...")
