"""Step 3, `PANTHER_PSEP1.01.pl`: how long each substitution's position has been preserved.

A port of `PANTHER_PSEP1.01.pl` at `cebb5ab` (design.md, decision 5), citing its lines (`PSEP:n`)
and the quirk IDs of the legacy behaviour spec §6. Per snpParse record, in the Perl's order
(`SCORE-1`):

1. The family must have a `.paml`, else "No PANTHER family".
2. The mapped position must contain a digit, else "Invalid substitution".
3. The gene's AN, with the Perl's open-ended pattern (`legacy.GeneLookup`).
4. The gene's sequence in the `.rst`, and the column of the mapped position in it
   (`getCorrectnum`). Unless the residue there is the wild type: "Invalid substitution". The
   families with broken files have no sequence list, so they stop here.
5. Only now the strict readers: the `.paml` header and the needed sites, in one pass; the `.rst`
   branch list and tree; the `.orig.tree`; the species tree. Then the walk from the start column
   (`SCORE-2`) towards the root, while each node keeps the wild type with a probability above 0.99
   (`SCORE-3`), and the age of the node where it stops (`getYear`, `SCORE-4`).
6. The message at 180 and 380 Mya (`SCORE-5`), and pDel from the table, `age < bound` (`SCORE-6`).

One call is one Perl process: the Perl's state that outlives a record, `$nth` and the start column
(`SCORE-8`), outlives it here too, until the call ends. Each family's tree is its own (`SCORE-7`
doesn't arise with one family per call). Each library file is read once per call, and of a `.paml`
only the header and the needed sites are kept.
"""

import itertools
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from panther_engine.csnp import legacy
from panther_engine.csnp.library import LibraryFormatError, open_lines
from panther_engine.csnp.orig_tree import read_orig_tree
from panther_engine.csnp.paml import PamlHeader, Site, read_sites
from panther_engine.csnp.rst import read_rst
from panther_engine.csnp.species import read_species

LIBRARY = "PAML_RST"
SPECIES = "species_pthr8_time.nhx"
FAMILY_NAME = re.compile(r"PTHR[0-9]+(?:_[0-9]+)*")
DIGIT = re.compile(r"[0-9]")
RESIDUE_OR_GAP = re.compile(r"-|[A-Z]")
NO_FAMILY = "Not scored: No PANTHER family for input sequence"
INVALID = "Not scored: Invalid substitution"
# PSEP:245
THRESHOLD = 0.99
# PSEP:197
CAP = 4200
SPECIATION = "0>1"
DUPLICATION = "1>0"
LEAF = "NA"
# PSEP:409-410 (SCORE-5)
POSSIBLY_DAMAGING = 180
PROBABLY_DAMAGING = 380
# PSEP:211-231 (SCORE-6): pDel for the first bound the age is below
PDEL = (
    (25, "0.02"),
    (85, "0.13"),
    (91, "0.17"),
    (99, "0.19"),
    (199, "0.27"),
    (399, "0.50"),
    (699, "0.57"),
    (799, "0.74"),
    (899, "0.78"),
    (1299, "0.85"),
    (1599, "0.86"),
    (3999, "0.89"),
)
PDEL_TOP = "0.95"


def message(age: int | None) -> str:
    """`ageMessage` (PSEP:407-424). An empty age counts as 0."""
    years = age or 0
    if years < POSSIBLY_DAMAGING:
        return "probably benign"
    if years < PROBABLY_DAMAGING:
        return "possibly damaging"
    return "probably damaging"


def pdel(age: int | None) -> str:
    """`getPdel` (PSEP:208-232): the value of the first bound the age is below. An empty age counts
    as 0."""
    years = age or 0
    return next((value for bound, value in PDEL if years < bound), PDEL_TOP)


def step3(lines: Iterable[str], data: Path) -> list[str]:
    """Step 3: one result record per snpParse record, in order, each ending in a line feed.

    `data` is the cSNP data folder, `csnp/9/`, with the library in `PAML_RST/` and the species
    tree. A scored record is `snpId,subst,family,age,message,pDel`, with an empty age where the
    Perl's is; one that isn't scored is `snpId,subst,Not scored: ...`.
    """
    return _Call(data).run([_Record.read(line) for line in lines])


@dataclass(frozen=True)
class _Record:
    """A snpParse record, read as PSEP:35-46 reads it: chomped and split on commas."""

    snp_id: str
    family: str
    an_info: str
    position: str
    mapped: str
    wt: str
    mut: str

    @classmethod
    def read(cls, line: str) -> "_Record":
        fields = [*legacy.split_fields(legacy.chomp(line), ","), *[""] * 8]
        return cls(fields[0], fields[2], fields[3], fields[4], fields[5], fields[6], fields[7])

    @property
    def subst(self) -> str:
        """PSEP:65: the substitution as submitted (`SCORE-10`)."""
        return self.wt + self.position + self.mut


@dataclass
class _Family:
    """One family's files, each read once per call: the `.orig.tree` and `.rst` when a record
    first needs them, the `.paml` only for the sites the walks need."""

    name: str
    folder: Path
    tree_lines: list[str] = field(default_factory=list[str])
    rst_lines: list[str] = field(default_factory=list[str])
    lookup: legacy.GeneLookup | None = None
    sequences: dict[str, str] | None = None

    def path(self, kind: str) -> Path:
        return self.folder / f"{self.name}.{kind}"

    def find_an(self, gene: str) -> int | None:
        """findAN (PSEP:284-305): the gene's AN in the `.orig.tree` (`SCORE-8`)."""
        if self.lookup is None:
            self.tree_lines = list(open_lines(self.path("orig.tree")))
            self.lookup = legacy.GeneLookup(self.tree_lines)
        return self.lookup.find_an(gene)

    def sequence(self, an: int | None) -> str | None:
        """The AN's sequence in the `.rst` sequence list (PSEP:322-334)."""
        if self.sequences is None:
            self.rst_lines = list(open_lines(self.path("rst")))
            self.sequences = legacy.sequences(self.rst_lines)
        if an is None:
            # The Perl's pattern is `AN` and three spaces.
            return legacy.sequence(self.rst_lines, "")
        return self.sequences.get(str(an))


@dataclass(frozen=True)
class FamilyTree:
    """What the walk and `getYear` read of a family, apart from the `.paml` sites: the `.paml`
    header, the `.rst` branch list and tree line, the `.orig.tree` events, and the species tree.
    Built by `family_tree`."""

    name: str
    header: PamlHeader
    rows: tuple[list[str], list[str]]
    """The `.paml`'s first two rows, as the Perl splits them."""
    starts: dict[str, int]
    nodes: int
    """`$i`: the number of nodes on the `.rst` tree line."""
    children: dict[int, list[int]]
    events: dict[int, tuple[str, int | None]]
    """Each internal node's event and its taxon's age, as PSEP:170-179 sets them."""
    kinds: dict[int, str]
    """Each node's kind, for reports: `leaf`; the event the Perl reads, such as `0>1`, or `missing
    taxon` where the species tree lacks its taxon; or, where the Perl reads no event, the `Ev`
    attribute and `not read`, such as `Ev=1>0, not read` for a duplication without `S`, or
    `no Ev`."""
    memo: dict[int, int | None] = field(default_factory=dict[int, int | None])

    def start(self, an: int | None) -> int | None:
        """The last header column labelled with the AN (PSEP:388, `SCORE-2`)."""
        if an is None:
            return legacy.start_node(self.rows, "")
        return self.starts.get(str(an))

    def kept(self, node: int, cells: Site | None, wt: str) -> bool:
        """PSEP:251, 259: the node's residue is the wild type with a probability above 0.99, which
        NaN isn't. A site past the file's last, or column 0 for no start, is never kept."""
        if cells is None or not 1 <= node <= self.header.columns:
            return False
        return cells.residues[node - 1] == wt and cells.probabilities[node - 1] > THRESHOLD

    def path(self, start: int | None, cells: Site | None, wt: str) -> list[int]:
        """The nodes the walk from `start` visits, up to where it stops: the first one not kept,
        or the root (PSEP:249-277, `SCORE-3`). Empty where there's no start."""
        if start is None:
            return []
        visited = [start]
        while visited[-1] != self.header.root and self.kept(visited[-1], cells, wt):
            visited.append(self.header.parents[visited[-1] - 1])
        return visited

    def age(self, node: int | None) -> int | None:
        """`getYear` (PSEP:181-206), without recursion, each node's age computed once. None is the
        Perl's empty age: a node whose event falls through the `if` chain, such as `0>0` with a
        known taxon or a node that isn't in the tree, or a duplication with no child."""
        if node is None:
            return None
        stack = [(node, False)]
        while stack:
            current, expanded = stack.pop()
            if current in self.memo:
                continue
            event, age = self.event(current)
            if event != DUPLICATION:
                self.memo[current] = age if event in (SPECIATION, LEAF) else None
                continue
            children = self.children.get(current, [])
            if not expanded:
                if len(stack) > 2 * self.nodes:
                    raise LibraryFormatError(self.name, None, "the .rst branch list has a cycle")
                stack.append((current, True))
                stack.extend((child, False) for child in children if child not in self.memo)
                continue
            # PSEP:191-200: the oldest child plus one, an empty age counting as 0, capped.
            oldest = max(((self.memo.get(child) or 0) + 1 for child in children), default=None)
            self.memo[current] = None if oldest is None else min(oldest, CAP)
        return self.memo[node]

    def event(self, node: int) -> tuple[str | None, int | None]:
        """PSEP:165-179: a leaf is NA, aged 0. An internal node has its event and its taxon's
        age; a taxon without an age makes it a duplication (`DATA-3`)."""
        if 1 <= node < self.header.root:
            return LEAF, 0
        return self.events.get(node, (None, None))


def family_tree(
    name: str,
    header: PamlHeader,
    rows: tuple[list[str], list[str]],
    rst_lines: list[str],
    tree_lines: list[str],
    species: dict[str, int],
) -> FamilyTree:
    """A family's tree, from its `.paml` header and first two rows, and its `.rst` and
    `.orig.tree` lines, read with the strict readers. The species tree gives each taxon's age."""
    rst = read_rst(rst_lines, f"{name}.rst")
    tree = read_orig_tree(tree_lines, f"{name}.orig.tree")
    ans = tree.ans
    # The .rst tree's nodes and the .orig.tree's ANs, each in order of appearance (PSEP:132-148).
    pairing = {
        node: ans[index] if index < len(ans) else None for index, node in enumerate(rst.tree.nodes)
    }
    attributes = {node.an: node.event for node in tree.nodes if node.an is not None}
    read = legacy.events(tree_lines[0]) if tree_lines else {}
    events: dict[int, tuple[str, int | None]] = {}
    kinds = {node: "leaf" for node in range(1, header.root)}
    for node in range(header.root, len(rst.tree.nodes) + 1):
        an = pairing.get(node)
        event, taxon = read.get(an, (None, None)) if an is not None else (None, None)
        age = species.get(taxon) if taxon is not None else None
        events[node] = (DUPLICATION, None) if age is None else (event or "", age)
        if event is not None:
            kinds[node] = event if age is not None else "missing taxon"
        else:
            attribute = attributes.get(an) if an is not None else None
            kinds[node] = "no Ev" if attribute is None else f"Ev={attribute}, not read"
    mothers = {child: parent for parent, child in rst.branches}
    mothers[header.root] = header.root
    children: dict[int, list[int]] = {}
    for child in range(1, len(rst.tree.nodes) + 1):
        parent = mothers.get(child)
        if parent is not None and parent != child:
            children.setdefault(parent, []).append(child)
    return FamilyTree(
        name,
        header,
        rows,
        legacy.start_nodes(rows),
        len(rst.tree.nodes),
        children,
        events,
        kinds,
    )


@dataclass(frozen=True)
class Walk:
    """A scored record's walk, for parity reports: the nodes it visited and their kinds."""

    snp_id: str
    family: str
    nodes: tuple[int, ...]
    kinds: tuple[str, ...]


class _Call:
    """One step-3 call: the Perl's process."""

    def __init__(self, data: Path) -> None:
        self.data = data
        self.library = data / LIBRARY
        self.families: dict[str, _Family] = {}
        self.trees: dict[str, FamilyTree] = {}
        self.sites: dict[str, dict[int, Site]] = {}
        self.walks: list[Walk] = []
        self.species: dict[str, int] | None = None
        # PSEP:341 `$nth` and PSEP:54 `$node_num` live as long as the process (SCORE-8).
        self.nth: str | None = None
        self.node_num: int | None = None
        self.last_family = "PTHR"
        self.last_an = -1

    def run(self, records: list[_Record]) -> list[str]:
        # First the checks that need no .paml, in order; then each .paml once, for the sites the
        # walks need; then the walks, in order.
        results: list[str | None] = []
        walks: list[tuple[int, _Record, int | None, int]] = []
        for index, record in enumerate(records):
            result = self.check(record)
            if isinstance(result, str):
                results.append(f"{record.snp_id},{record.subst},{result}\n")
            else:
                results.append(None)
                walks.append((index, record, *result))
        needed: dict[str, set[int]] = {}
        for _, record, _, site in walks:
            needed.setdefault(record.family, set()).add(site)
        for family, sites in needed.items():
            self.read_tree(family, sites)
        for index, record, an, site in walks:
            tree = self.trees[record.family]
            if record.family != self.last_family or (an or 0) != self.last_an:
                # PSEP:88-96: the .paml is read again, and `$node_num` changes only on a match.
                start = tree.start(an)
                if start is not None:
                    self.node_num = start
                self.last_family, self.last_an = record.family, an or 0
            path = tree.path(self.node_num, self.sites[record.family].get(site), record.wt)
            stop = path[-1] if path else self.node_num
            age = tree.age(stop)
            kinds = tuple(tree.kinds.get(node, "not a node") for node in path)
            self.walks.append(Walk(record.snp_id, record.family, tuple(path), kinds))
            results[index] = (
                f"{record.snp_id},{record.subst},{record.family},{'' if age is None else age},"
                f"{message(age)},{pdel(age)}\n"
            )
        return [result for result in results if result is not None]

    def check(self, record: _Record) -> str | tuple[int | None, int]:
        """PSEP:66-86: the reason the record isn't scored, or its AN and site."""
        family = self.family(record.family)
        if family is None:
            return NO_FAMILY
        if not DIGIT.search(record.mapped):
            return INVALID
        an = family.find_an(record.an_info)
        site = self.correct_site(family.sequence(an), legacy.numify(record.mapped))
        if self.nth != record.wt:
            return INVALID
        return an, site

    def family(self, name: str) -> _Family | None:
        """The family, if it has a `.paml` (PSEP:66-72). A name that isn't a family's, such as
        `AN12345` or one with a `/`, has none."""
        if name not in self.families:
            if not FAMILY_NAME.fullmatch(name) or not (self.library / f"{name}.paml").exists():
                return None
            self.families[name] = _Family(name, self.library)
        return self.families[name]

    def correct_site(self, sequence: str | None, position: float) -> int:
        """`getCorrectnum` (PSEP:310-357), line for line: the column of the `position`-th residue.

        One step per `-` or `A`-`Z` in the sequence, but the string is indexed by the step, so
        other characters shift it. Past the last residue, the last step's column stands. `$nth`,
        the character found, keeps its value from the previous record when there's no sequence.
        """
        column = 0
        residues = 0
        if sequence is None:
            return column
        for _ in range(len(RESIDUE_OR_GAP.findall(sequence))):
            if residues < position:
                self.nth = sequence[column] if column < len(sequence) else ""
                column += 1
                if "A" <= self.nth <= "Z":
                    residues += 1
        return column

    def read_tree(self, name: str, sites: set[int]) -> None:
        """Read the family's `.paml` once, for its header and the sites the walks need, and the
        rest of its tree."""
        family = self.families[name]
        paml = family.path("paml")
        lines: Iterator[str] = open_lines(paml)
        first = list(itertools.islice(lines, 2))
        wanted = [site for site in sites if site >= 1]
        header, self.sites[name] = read_sites(itertools.chain(first, lines), paml.name, wanted)
        if self.species is None:
            self.species = read_species(open_lines(self.data / SPECIES), SPECIES)
        self.trees[name] = family_tree(
            name,
            header,
            legacy.paml_rows(first),
            family.rst_lines,
            family.tree_lines,
            self.species,
        )


def trace(lines: Iterable[str], data: Path) -> list[Walk]:
    """Step 3, for parity reports: the walk of each record that's walked, in order."""
    call = _Call(data)
    call.run([_Record.read(line) for line in lines])
    return call.walks
