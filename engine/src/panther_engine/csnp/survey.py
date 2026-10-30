"""The survey of the PAML_RST library: one streaming pass over the archive, checking every family.

The archive is read as a stream, `r|gz`, and never unpacked to disk. Its sha256 comes from the same
pass. Members are matched by file name, `PTHRnnnnn[_N].{paml,rst,orig.tree}`, in any folder, so the
sample tarball can be surveyed too. The archive stores members in hash order, so a family's three
files arrive far apart. Each file is reduced to a small summary of numbers as it arrives; when a
family's third file arrives, the checks that need all three run and the summaries are dropped.

Each check counts the families it finds, and the items where that means more (leaves, nodes, …),
with up to five examples, smallest family first. A legacy check compares the Perl's reading
(`legacy.py`) with the strict reader's, on files the strict reader accepts.

Given the PANTHER9 BLAST archive too, the survey reads the headers of `blast/blast.fasta` first,
and checks each entry's gene against its family's `.orig.tree` when that arrives.
"""

import hashlib
import itertools
import re
import tarfile
import zlib
from collections import Counter
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import IO, cast

from panther_engine.csnp import legacy
from panther_engine.csnp.library import CARRIAGE_RETURN, ENCODING, LibraryFormatError
from panther_engine.csnp.orig_tree import OrigTree, read_orig_tree
from panther_engine.csnp.paml import read_paml
from panther_engine.csnp.rst import read_rst
from panther_engine.csnp.species import read_species

FAMILY_FILE = re.compile(r"(PTHR[0-9]+(?:_[0-9]+)*)\.(paml|rst|orig\.tree)")
# A split part, `PTHRnnnnn_N` or `PTHRnnnnn_N_M`, and its base family.
SPLIT_PART = re.compile(r"(PTHR[0-9]+)(?:_[0-9]+)+")
FAMILY_NAME = re.compile(r"PTHR[0-9]+(?:_[0-9]+)*")
KINDS = ("paml", "rst", "orig.tree")
EXAMPLES = 5
READ_SIZE = 1 << 20
SPECIATION = "0>1"
EVENTS = ("0>1", "1>0", "0>0")


class SurveyError(Exception):
    """An archive that can't be read to the end."""


@dataclass(frozen=True)
class Check:
    key: str
    description: str
    unit: str | None = None
    """What `items` counts, where that isn't the families."""


CHECKS = (
    # Files and parsing
    Check("missing-paml", "families without a .paml"),
    Check("missing-rst", "families without a .rst"),
    Check("missing-orig-tree", "families without a .orig.tree"),
    Check("split-without-base", "split parts whose base family has no files (DATA-1)", "bases"),
    Check("duplicate-member", "files that appear twice in the archive", "files"),
    Check("rejected-paml", ".paml files the strict reader rejects"),
    Check("rejected-rst", ".rst files the strict reader rejects"),
    Check("rejected-orig-tree", ".orig.tree files the strict reader rejects"),
    Check("carriage-return", "files with a carriage return, which the Perl keeps", "files"),
    Check("unreconstructed", ".paml files with unreconstructed cells: NUL and -nan", "cells"),
    Check("internal-without-an", ".paml files with internal columns that have no AN", "columns"),
    Check("extra-parenthesis", ".orig.tree files whose tree ends with one unmatched ')'"),
    # Agreement between a family's files
    Check("parents", ".paml parents that disagree with the .rst branch list", "nodes"),
    Check("leaf-labels", ".paml leaf labels that aren't the .orig.tree's leaves", "ANs"),
    Check("node-count", "node counts that differ between the .paml, .rst tree and .orig.tree"),
    Check("tree-shape", ".rst and .orig.tree trees that differ in shape or leaf ANs", "nodes"),
    Check("sequence-length", ".rst sequences whose length isn't the .paml site count", "ANs"),
    # The legacy readings
    Check(
        "legacy-start-column",
        "leaves whose legacy start isn't their own column (SCORE-2)",
        "leaves",
    ),
    Check("legacy-root", "legacy root differs from the strict root"),
    Check("legacy-branches", "legacy branch list differs from the strict one (SCORE-9)"),
    Check("legacy-tree-nodes", "legacy .rst tree nodes differ from the strict ones"),
    Check("legacy-an-order", "legacy .orig.tree AN order differs from the strict one"),
    Check("legacy-pairing", "legacy pairing of nodes with ANs differs", "nodes"),
    Check("legacy-events", "events and taxa the legacy pattern misses or misreads", "nodes"),
    Check("legacy-sequence", "legacy sequence reading differs", "ANs"),
    Check("legacy-species-ages", "taxa whose legacy age differs from the strict one", "taxa"),
    # Events and taxa (DATA-3)
    Check("event-0>0", "internal nodes with Ev=0>0", "nodes"),
    Check("event-other", "internal nodes with another Ev", "nodes"),
    Check("event-none", "internal nodes without an Ev", "nodes"),
    Check("missing-taxon", "speciation nodes whose taxon isn't in the species tree", "nodes"),
    # The BLAST database (DATA-2, SCORE-8)
    Check("blast-not-a-family", "BLAST entries whose family field isn't a family name", "entries"),
    Check("blast-no-paml", "BLAST entries whose family has no .paml", "entries"),
    Check("blast-gene-not-found", "BLAST entries not on a gene line of the .orig.tree", "entries"),
    Check("blast-legacy-lookup", "BLAST entries the legacy lookup maps to another AN", "entries"),
)
SPECIES_CHECKS = frozenset({"missing-taxon", "legacy-species-ages"})
BLAST_CHECKS = frozenset(
    {"blast-not-a-family", "blast-no-paml", "blast-gene-not-found", "blast-legacy-lookup"}
)


@dataclass(frozen=True)
class Example:
    family: str
    size: int
    """The bytes of the family's files in the archive."""
    detail: str


@dataclass
class CheckResult:
    check: Check
    families: int = 0
    items: int = 0
    examples: list[Example] = field(default_factory=list[Example])
    checked: bool = True

    @property
    def found(self) -> bool:
        return self.families > 0 or self.items > 0

    def add(self, example: Example, items: int = 1, *, family: bool = True) -> None:
        self.families += family
        self.items += items
        self.examples.append(example)
        self.examples.sort(key=lambda each: (each.size, each.family))
        del self.examples[EXAMPLES:]


@dataclass(frozen=True)
class Source:
    path: str
    sha256: str
    size: int


@dataclass
class Report:
    archive: Source
    families: int = 0
    members: int = 0
    other_members: int = 0
    rooted: int = 0
    """Families whose .paml read, so have a root."""
    leaves: int = 0
    """Leaf columns in those families."""
    largest_paml: tuple[str, int] = ("", 0)
    """The family with the largest .paml, and its size."""
    rejected: list[tuple[str, str]] = field(default_factory=list[tuple[str, str]])
    """Every file the strict readers reject, with the error, in file name order."""
    checks: dict[str, CheckResult] = field(
        default_factory=lambda: {check.key: CheckResult(check) for check in CHECKS}
    )
    events: Counter[str] = field(default_factory=Counter[str])
    missing_taxa: Counter[str] = field(default_factory=Counter[str])
    species: Source | None = None
    blast: Source | None = None
    blast_entries: int = 0

    def found(self) -> list[str]:
        """The keys of the checks that found something."""
        return [key for key, result in self.checks.items() if result.found]


@dataclass(frozen=True)
class PamlFacts:
    root: int
    columns: int
    leaf_ans: tuple[int, ...]
    parents: tuple[int, ...]
    sites: int


@dataclass(frozen=True)
class RstFacts:
    branches: dict[int, int]
    """Child to parent."""
    nodes: tuple[int, ...]
    leaves: dict[int, int]
    lengths: dict[int, int]
    legacy_nodes: tuple[int, ...]


@dataclass(frozen=True)
class TreeFacts:
    ans: tuple[int | None, ...]
    leaf: tuple[bool, ...]
    legacy_ans: tuple[int, ...]


@dataclass
class BlastFacts:
    entries: int
    not_found: int = 0
    not_found_example: str = ""
    legacy: int = 0
    legacy_example: str = ""


@dataclass
class Family:
    name: str
    size: int = 0
    seen: set[str] = field(default_factory=set[str])
    paml: PamlFacts | None = None
    rst: RstFacts | None = None
    tree: TreeFacts | None = None
    blast: BlastFacts | None = None
    findings: list[tuple[str, str, int]] = field(default_factory=list[tuple[str, str, int]])
    done: bool = False

    def note(self, key: str, detail: str, items: int = 1) -> None:
        self.findings.append((key, detail, items))


class HashingReader:
    """A binary file that hashes and counts what is read from it."""

    def __init__(self, raw: IO[bytes]) -> None:
        self.raw = raw
        self.digest = hashlib.sha256()
        self.size = 0

    def read(self, size: int = -1) -> bytes:
        data = self.raw.read(size)
        self.digest.update(data)
        self.size += len(data)
        return data

    def drain(self) -> None:
        while self.read(READ_SIZE):
            pass


def open_stream(reader: HashingReader) -> tarfile.TarFile:
    """A gzipped tar read as a stream, front to back, through `reader`.

    tarfile's default buffer is kept: with a large one, each small read of a member copies the
    rest of a large decompressed buffer, and the pass runs many times slower.
    """
    return tarfile.open(fileobj=cast(IO[bytes], reader), mode="r|gz")


def member_lines(tar: tarfile.TarFile, member: tarfile.TarInfo) -> Iterator[bytes]:
    """A member's lines, with their line feeds, read in large chunks."""
    stream = tar.extractfile(member)
    if stream is None:
        raise SurveyError(f"can't read {member.name}")
    rest = b""
    while chunk := stream.read(READ_SIZE):
        lines = (rest + chunk).split(b"\n")
        rest = lines.pop()
        for line in lines:
            yield line + b"\n"
    if rest:
        yield rest


Progress = Callable[[int, int], None]
"""Called now and then with the members and the compressed bytes read so far."""


def survey(
    archive: Path,
    *,
    species: Path | None = None,
    blast: Path | None = None,
    progress: Progress | None = None,
) -> Report:
    """Survey `archive`, a gzipped tar of the library. Raises SurveyError if it can't be read."""
    survey = Survey(species, blast)
    with archive.open("rb") as raw:
        reader = HashingReader(raw)
        try:
            with open_stream(reader) as tar:
                for member in tar:
                    survey.member(tar, member)
                    if progress is not None and survey.report.members % 500 == 0:
                        progress(survey.report.members, reader.size)
            reader.drain()
        except (tarfile.TarError, EOFError, zlib.error, OSError) as error:
            raise SurveyError(f"can't read {archive} to the end: {error}") from error
    survey.report.archive = Source(str(archive), reader.digest.hexdigest(), reader.size)
    survey.finish()
    return survey.report


class Survey:
    def __init__(self, species: Path | None, blast: Path | None) -> None:
        self.report = Report(Source("", "", 0))
        self.families: dict[str, Family] = {}
        self.ages: dict[str, int] | None = None
        self.blast_genes: dict[str, list[str]] = {}
        if species is not None:
            self.read_species(species)
        else:
            for key in SPECIES_CHECKS:
                self.report.checks[key].checked = False
        if blast is not None:
            self.read_blast(blast)
        else:
            for key in BLAST_CHECKS:
                self.report.checks[key].checked = False

    # Inputs other than the library

    def read_species(self, path: Path) -> None:
        with path.open("rb") as stream:
            content = stream.read()
        self.report.species = Source(str(path), hashlib.sha256(content).hexdigest(), len(content))
        lines = content.decode(ENCODING).splitlines(keepends=True)
        self.ages = read_species(lines, path.name)
        old = legacy.species_ages(lines[0])
        result = self.report.checks["legacy-species-ages"]
        for taxon in sorted(set(self.ages) | set(old)):
            if old.get(taxon) != self.ages.get(taxon):
                detail = f"{taxon}: {self.ages.get(taxon)}, legacy {old.get(taxon)}"
                result.add(Example(path.name, 0, detail), family=False)

    def read_blast(self, path: Path) -> None:
        found = False
        with path.open("rb") as raw:
            reader = HashingReader(raw)
            try:
                with open_stream(reader) as tar:
                    for member in tar:
                        if member.isfile() and PurePosixPath(member.name).name == "blast.fasta":
                            self.blast_headers(member_lines(tar, member))
                            found = True
                reader.drain()
            except (tarfile.TarError, EOFError, zlib.error, OSError) as error:
                raise SurveyError(f"can't read {path} to the end: {error}") from error
        if not found:
            raise SurveyError(f"{path} has no blast/blast.fasta")
        self.report.blast = Source(str(path), reader.digest.hexdigest(), reader.size)

    def blast_headers(self, stream: Iterable[bytes]) -> None:
        """Each entry's gene and family, from the first word of its header, `GENE:FAMILY:SF`.

        Step 2 takes the family from the second field (`parse_blastp.pl:63, 69`). Some headers are
        `GENE:AN<n>:FAMILY`, so the Perl looks for a family `AN<n>`, finds no `.paml`, and never
        scores them. The survey reads them the same way, and counts them.
        """
        not_family: Counter[str] = Counter()
        for line in stream:
            if line.startswith(b">"):
                words = line[1:].split(None, 1)
                header = words[0].decode(ENCODING) if words else ""
                gene, _, rest = header.partition(":")
                family = rest.partition(":")[0]
                if not FAMILY_NAME.fullmatch(family):
                    not_family[re.sub(r"[0-9]+", "<n>", family)] += 1
                self.blast_genes.setdefault(family, []).append(gene)
                self.report.blast_entries += 1
        result = self.report.checks["blast-not-a-family"]
        for shape, count in not_family.most_common():
            result.add(Example(f"{shape!r}", 0, f"{count:,} entries"), count, family=False)

    # The library

    def member(self, tar: tarfile.TarFile, member: tarfile.TarInfo) -> None:
        if not member.isfile():
            return
        self.report.members += 1
        found = FAMILY_FILE.fullmatch(PurePosixPath(member.name).name)
        if found is None:
            self.report.other_members += 1
            return
        name, kind = found[1], found[2]
        family = self.families.setdefault(name, Family(name))
        file_name = f"{name}.{kind}"
        if kind in family.seen:
            example = Example(name, family.size, f"{member.name}")
            self.report.checks["duplicate-member"].add(example, family=not family.done)
            return
        family.seen.add(kind)
        family.size += member.size
        if kind == "paml" and member.size > self.report.largest_paml[1]:
            self.report.largest_paml = (name, member.size)
        # Decoded line by line: a TextIOWrapper needs a seekable stream, which `r|gz` isn't.
        lines = (line.decode(ENCODING) for line in member_lines(tar, member))
        try:
            match kind:
                case "paml":
                    self.read_paml(family, lines, file_name)
                case "rst":
                    self.read_rst(family, list(lines), file_name)
                case _:
                    self.read_tree(family, list(lines), file_name)
        except LibraryFormatError as error:
            family.note(f"rejected-{kind.replace('.', '-')}", str(error))
            self.report.rejected.append((file_name, str(error)))
            if error.message == CARRIAGE_RETURN:
                family.note("carriage-return", file_name)
            if kind == "orig.tree":
                self.blast_entries(family, None, [])
        if family.seen == set(KINDS):
            self.join(family)

    def read_paml(self, family: Family, lines: Iterator[str], name: str) -> None:
        first = list(itertools.islice(lines, 2))
        summary = read_paml(itertools.chain(first, lines), name)
        header = summary.header
        leaf_ans = tuple(an for an in header.ans[: header.root - 1] if an is not None)
        family.paml = PamlFacts(
            header.root, header.columns, leaf_ans, header.parents, summary.sites
        )
        self.report.rooted += 1
        self.report.leaves += len(leaf_ans)
        if summary.unreconstructed:
            family.note(
                "unreconstructed", f"{summary.unreconstructed} cells", summary.unreconstructed
            )
        without = sum(an is None for an in header.ans)
        if without:
            family.note("internal-without-an", f"{without} columns", without)

        rows = legacy.paml_rows(first)
        old_root = legacy.root_node(rows)
        if old_root != header.root:
            family.note("legacy-root", f"root {header.root}, legacy {old_root}")
        starts = legacy.start_nodes(rows)
        moved = [
            (column, an, starts.get(str(an)))
            for column, an in enumerate(leaf_ans, 1)
            if starts.get(str(an)) != column
        ]
        if moved:
            column, an, start = moved[0]
            detail = f"{len(moved)} of {len(leaf_ans)}; AN{an}: column {column}, legacy {start}"
            family.note("legacy-start-column", detail, len(moved))

    def read_rst(self, family: Family, lines: list[str], name: str) -> None:
        rst = read_rst(lines, name)
        branches = {child: parent for parent, child in rst.branches}
        branch_line, tree_line = legacy.rst_lines(lines)
        old_nodes = tuple(legacy.tree_nodes(tree_line))
        family.rst = RstFacts(
            branches,
            rst.tree.nodes,
            rst.tree.leaves,
            {an: len(sequence) for an, sequence in rst.sequences.items()},
            old_nodes,
        )
        if legacy.branches(branch_line) != branches:
            family.note("legacy-branches", "the 12th line")
        if old_nodes != rst.tree.nodes:
            family.note(
                "legacy-tree-nodes", f"{len(rst.tree.nodes)} nodes, legacy {len(old_nodes)}"
            )
        old_sequences = legacy.sequences(lines)
        differ = [an for an, seq in rst.sequences.items() if old_sequences.get(str(an)) != seq]
        if differ:
            family.note("legacy-sequence", f"{len(differ)} ANs, such as AN{differ[0]}", len(differ))

    def read_tree(self, family: Family, lines: list[str], name: str) -> None:
        tree = read_orig_tree(lines, name)
        old_ans = tuple(legacy.tree_ans(lines[0]))
        family.tree = TreeFacts(tree.ans, tuple(node.leaf for node in tree.nodes), old_ans)
        if tree.extra_parenthesis:
            family.note("extra-parenthesis", "one ')' too many before the ';'")
        if old_ans != tree.ans:
            family.note("legacy-an-order", f"{len(tree.ans)} nodes, legacy {len(old_ans)} ANs")

        old_events = legacy.events(lines[0])
        missed = 0
        example = ""
        counts: Counter[str] = Counter()
        missing: Counter[str] = Counter()
        for node in tree.nodes:
            if node.leaf:
                continue
            event = node.event
            counts[event if event in EVENTS else ("none" if event is None else "other")] += 1
            expected = (event, node.taxon) if event is not None and node.taxon is not None else None
            if node.an is not None and old_events.get(node.an) != expected:
                missed += 1
                example = example or f"AN{node.an}: {expected}, legacy {old_events.get(node.an)}"
            if event == SPECIATION and self.ages is not None and node.taxon not in self.ages:
                missing[node.taxon or "(no taxon)"] += 1
        if missed:
            family.note("legacy-events", example, missed)
        self.report.events.update(counts)
        for key, label in (("event-0>0", "0>0"), ("event-other", "other"), ("event-none", "none")):
            if counts[label]:
                family.note(key, f"{counts[label]} nodes", counts[label])
        if missing:
            self.report.missing_taxa.update(missing)
            taxa = ", ".join(sorted(missing))
            family.note("missing-taxon", f"{missing.total()} nodes: {taxa}", missing.total())
        self.blast_entries(family, tree, lines)

    def blast_entries(self, family: Family, tree: OrigTree | None, lines: list[str]) -> None:
        genes = self.blast_genes.pop(family.name, None)
        if genes is None:
            return
        facts = BlastFacts(len(genes))
        exact = {gene: an for an, gene in tree.genes.items()} if tree is not None else {}
        lookup = legacy.GeneLookup(lines) if tree is not None else None
        for gene in genes:
            an = exact.get(gene)
            if an is None:
                facts.not_found += 1
                facts.not_found_example = facts.not_found_example or (
                    gene if tree is not None else "the .orig.tree didn't read"
                )
            if lookup is None:
                continue
            try:
                old: int | str | None = lookup.find_an(gene)
            except ValueError as error:
                old = str(error)
            if old != an:
                facts.legacy += 1
                facts.legacy_example = facts.legacy_example or f"{gene}: AN{an}, legacy {old}"
        family.blast = facts

    # Families

    def join(self, family: Family) -> None:
        paml, rst, tree = family.paml, family.rst, family.tree
        if paml is not None and rst is not None and tree is not None:
            self.agreement(family, paml, rst, tree)
        self.finalize(family)

    def agreement(self, family: Family, paml: PamlFacts, rst: RstFacts, tree: TreeFacts) -> None:
        parents = {
            column: parent for column, parent in enumerate(paml.parents, 1) if column != paml.root
        }
        differ = sorted(set(parents.items()) ^ set(rst.branches.items()))
        if differ:
            child = differ[0][0]
            detail = f"node {child}: .paml {parents.get(child)}, .rst {rst.branches.get(child)}"
            family.note("parents", detail, len({child for child, _ in differ}))

        tree_leaves = {an for an, leaf in zip(tree.ans, tree.leaf, strict=True) if leaf}
        labels = sorted(an for an in set(paml.leaf_ans) ^ tree_leaves if an is not None)
        if labels:
            family.note("leaf-labels", f"AN{labels[0]}", len(labels))
        elif len(paml.leaf_ans) != len(set(paml.leaf_ans)):
            family.note("leaf-labels", "a leaf label appears twice in the .paml")

        counts = (paml.columns, len(rst.nodes), len(tree.ans))
        if len(set(counts)) > 1:
            family.note("node-count", ".paml {}, .rst {}, .orig.tree {}".format(*counts))
        else:
            shape = [
                index
                for index, (node, an, leaf) in enumerate(
                    zip(rst.nodes, tree.ans, tree.leaf, strict=True)
                )
                if (node in rst.leaves) != leaf or (leaf and rst.leaves[node] != an)
            ]
            if shape:
                family.note("tree-shape", f"node {rst.nodes[shape[0]]}", len(shape))
            else:
                strict = dict(zip(rst.nodes, tree.ans, strict=True))
                old = legacy.pairing(rst.legacy_nodes, tree.legacy_ans)
                moved = [
                    node for node in strict.keys() | old.keys() if strict.get(node) != old.get(node)
                ]
                if moved:
                    node = min(moved)
                    detail = f"node {node}: AN{strict.get(node)}, legacy AN{old.get(node)}"
                    family.note("legacy-pairing", detail, len(moved))

        lengths = [an for an, length in rst.lengths.items() if length != paml.sites]
        if lengths:
            an = lengths[0]
            detail = f"AN{an}: {rst.lengths[an]} residues, {paml.sites} sites"
            family.note("sequence-length", detail, len(lengths))

    def finalize(self, family: Family) -> None:
        if family.blast is not None:
            facts = family.blast
            if "paml" not in family.seen:
                family.note("blast-no-paml", f"{facts.entries} entries", facts.entries)
            else:
                if facts.not_found:
                    family.note("blast-gene-not-found", facts.not_found_example, facts.not_found)
                if facts.legacy:
                    family.note("blast-legacy-lookup", facts.legacy_example, facts.legacy)
        by_key: dict[str, tuple[list[str], int]] = {}
        for key, detail, items in family.findings:
            details, count = by_key.get(key, ([], 0))
            by_key[key] = ([*details, detail], count + items)
        for key, (details, items) in by_key.items():
            example = Example(family.name, family.size, "; ".join(details))
            self.report.checks[key].add(example, items)
        family.findings.clear()
        family.paml = family.rst = family.tree = None
        family.done = True

    def finish(self) -> None:
        bases = {SPLIT_PART.fullmatch(name) for name in self.families}
        for name, genes in self.blast_genes.items():
            family = self.families.setdefault(name, Family(name))
            family.blast = BlastFacts(len(genes), len(genes), "the family has no .orig.tree")
        self.blast_genes.clear()
        unreached: dict[str, list[str]] = {}
        for match in bases:
            if match is not None and match[1] not in self.families:
                unreached.setdefault(match[1], []).append(match[0])
        result = self.report.checks["split-without-base"]
        for base, parts in unreached.items():
            for part in parts:
                family = self.families[part]
                if family.done:
                    result.add(Example(part, family.size, base), 0)
                else:
                    family.note("split-without-base", base, 0)
        result.items += len(unreached)
        for family in self.families.values():
            if family.done:
                continue
            if family.seen:
                for kind in KINDS:
                    if kind not in family.seen:
                        family.note(f"missing-{kind.replace('.', '-')}", f"{family.name}.{kind}")
            self.finalize(family)
        self.report.families = sum(bool(family.seen) for family in self.families.values())
        self.report.rejected.sort()


def report_json(report: Report) -> dict[str, object]:
    def source(value: Source | None) -> dict[str, object] | None:
        if value is None:
            return None
        return {"path": value.path, "sha256": value.sha256, "bytes": value.size}

    return {
        "archive": source(report.archive),
        "species": source(report.species),
        "blast": source(report.blast),
        "families": report.families,
        "members": report.members,
        "other_members": report.other_members,
        "rooted_families": report.rooted,
        "leaves": report.leaves,
        "largest_paml": {"family": report.largest_paml[0], "bytes": report.largest_paml[1]},
        "events": dict(sorted(report.events.items())),
        "missing_taxa": dict(sorted(report.missing_taxa.items())),
        "blast_entries": report.blast_entries,
        "rejected": [{"file": name, "error": error} for name, error in report.rejected],
        "checks": [
            {
                "key": result.check.key,
                "description": result.check.description,
                "checked": result.checked,
                "families": result.families,
                "items": result.items,
                "unit": result.check.unit,
                "examples": [
                    {"family": each.family, "bytes": each.size, "detail": each.detail}
                    for each in result.examples
                ],
            }
            for result in report.checks.values()
        ],
    }


def report_text(report: Report) -> str:
    lines = [
        f"Archive:  {report.archive.path}",
        f"sha256:   {report.archive.sha256}",
        f"Bytes:    {report.archive.size:,}",
        f"Families: {report.families:,} ({report.rooted:,} with a root; {report.leaves:,} leaves)",
        f"Members:  {report.members:,} files, {report.other_members:,} not a family file",
        f"Largest .paml: {report.largest_paml[0]} ({report.largest_paml[1]:,} bytes)",
        "Internal nodes by event: "
        + ", ".join(f"{event} {count:,}" for event, count in sorted(report.events.items())),
    ]
    if report.species is not None:
        lines.append(f"Species:  {report.species.path} ({report.species.sha256})")
        if report.missing_taxa:
            lines.append(
                "Taxa missing from the species tree: "
                + ", ".join(f"{taxon} {count:,}" for taxon, count in report.missing_taxa.items())
            )
    if report.blast is not None:
        lines.append(f"BLAST:    {report.blast.path} ({report.blast.sha256})")
        lines.append(f"BLAST entries: {report.blast_entries:,}")
    lines.append("")
    for result in report.checks.values():
        if not result.checked:
            lines.append(f"{result.check.key}: not checked")
            continue
        count = f"{result.families:,} families"
        if result.check.unit is not None:
            count += f", {result.items:,} {result.check.unit}"
        lines.append(f"{result.check.key}: {count}  ({result.check.description})")
        lines.extend(
            f"    {each.family} ({each.size:,} bytes): {each.detail}" for each in result.examples
        )
    lines.append("")
    lines.append(f"Files the strict readers reject: {len(report.rejected):,}")
    lines.extend(f"    {error}" for _, error in report.rejected)
    return "\n".join(lines) + "\n"
