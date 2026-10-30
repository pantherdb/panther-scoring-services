"""Parity with the legacy cSNP scripts: generated cases, the Perl reference, and the comparison.

The reference is `parse_blastp.pl` (step 2) and `PANTHER_PSEP1.01.pl` (step 3) at `cebb5ab`, in the
`csnp-reference` image (docs/parity/golden-setup.md). Its outputs are the goldens the port must
match, byte for byte, at each step's boundary (design.md, decision 1).

A cases folder, such as `tests/golden/csnp/generated/`, holds:

- `cases.json`: the seed and sizes that generated the cases, the step-2 runs and their species,
  and the families with step-3 cases;
- `sample.snpparse` and `edge-cases.snpparse`: the reference's step-2 output for spec §7.3's and
  §7.5's inputs, saved by the self-check;
- `step2/<run>.blast` and `<run>.input`: BLAST lines and SNP lines, and the reference's
  `<run>.snpparse`;
- `step3/<family>.snpparse`: snpParse rows for one family, and the reference's `<family>.out`.

Files are read and written as Latin-1, so every byte, carriage returns included, survives.
"""

import json
import random
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from panther_engine.core.process import run_tool
from panther_engine.csnp import hits, legacy, psep
from panther_engine.csnp.library import LibraryFormatError, open_lines
from panther_engine.csnp.orig_tree import read_orig_tree
from panther_engine.csnp.paml import iter_sites, read_header
from panther_engine.csnp.species import read_species

ENCODING = "latin-1"
SPECIES_TREE = "species_pthr8_time.nhx"
LIBRARY = "PAML_RST"
CASES = "cases.json"
STEP2 = "step2"
STEP3 = "step3"
SCRIPTS = Path("/opt/csnp-reference")
GOLDEN = Path("tests/golden/csnp")
# The self-check's runs (legacy behaviour spec §7.3 and §7.5): the SNP input, the species, the
# expected step-3 output, all relative to the golden folder, and the BLAST lines, `release/HUMAN`.
SELF_CHECK = (
    ("sample", "release/sample.input", "HUMAN", "spec/sample.out"),
    ("edge-cases", "spec/edge-cases.input", "NA", "spec/edge-cases.out"),
)
SELF_CHECK_BLAST = "release/HUMAN"
# A species code reaches `grep` and a file name in parse_blastp.pl, through a shell (CGI-5).
SPECIES_CODE = re.compile(r"[A-Za-z0-9]+")
# Step 3 reads a 136 MB .paml once per gene: generous, so a slow machine doesn't fail the run.
TIMEOUT = 3600.0
SEED = "port-csnp"
GENES = 5
POSITIONS = 8
AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"
# A family no library has, for each family's "no family" row
NO_SUCH_FAMILY = "PTHR00000"


class ParityError(Exception):
    """The reference can't run, or a cases folder can't be read."""


def read(path: Path) -> str:
    return path.read_bytes().decode(ENCODING)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode(ENCODING))


# The reference


@dataclass(frozen=True)
class Reference:
    """The legacy scripts in `scripts`, run with `perl`. Each run gets a fresh working folder."""

    perl: Path
    scripts: Path = SCRIPTS

    @classmethod
    def find(cls, scripts: Path = SCRIPTS) -> "Reference":
        perl = shutil.which("perl")
        if perl is None:
            raise ParityError("no perl on PATH: run this in the csnp-reference image")
        for name in ("parse_blastp.pl", "PANTHER_PSEP1.01.pl"):
            if not (scripts / name).is_file():
                raise ParityError(f"no {name} in {scripts}: run this in the csnp-reference image")
        return cls(Path(perl).absolute(), scripts)

    def step2(self, blast: str, snps: str, species: str) -> str:
        """`parse_blastp.pl`'s snpParse output for BLAST lines, SNP lines and a species code."""
        if not SPECIES_CODE.fullmatch(species):
            raise ParityError(f"not a species code: {species!r}")
        with tempfile.TemporaryDirectory(prefix="csnp-reference-") as work:
            folder = Path(work)
            write(folder / "blast.csv", blast)
            write(folder / "snp.input", snps)
            args = ["-i", "snp.input", "-o", "blast.csv", "-O", "snpParse", "-s", species]
            self._run("parse_blastp.pl", args, folder)
            return read(folder / "snpParse")

    def step3(self, snpparse: str, data: Path) -> str:
        """`PANTHER_PSEP1.01.pl`'s output for snpParse rows, against the cSNP data folder `data`.

        The script opens the species tree by relative path (`RUN-1`), so the working folder gets a
        link to the data folder's.
        """
        with tempfile.TemporaryDirectory(prefix="csnp-reference-") as work:
            folder = Path(work)
            (folder / SPECIES_TREE).symlink_to((data / SPECIES_TREE).absolute())
            write(folder / "snpParse", snpparse)
            library = str((data / LIBRARY).absolute())
            self._run("PANTHER_PSEP1.01.pl", ["-i", "snpParse", "-l", library, "-o", "out"], folder)
            return read(folder / "out")

    def _run(self, script: str, args: Sequence[str], folder: Path) -> None:
        command = [str(self.scripts / script), *args, "-e", "log"]
        try:
            result = run_tool(self.perl, command, timeout=TIMEOUT, cwd=folder)
        except subprocess.TimeoutExpired as error:
            raise ParityError(f"{script} ran past {TIMEOUT:.0f} s") from error
        if result.returncode != 0:
            log = folder / "log"
            tail = read(log).splitlines()[-5:] if log.exists() else []
            raise ParityError(
                f"{script} exited with status {result.returncode}: "
                + " / ".join([*tail, result.stdout.strip(), result.stderr.strip()])
            )


# BLAST lines


def blast_line(
    qseqid: str,
    sseqid: str,
    qseq: str,
    sseq: str,
    *,
    qstart: int = 1,
    sstart: int = 1,
    pident: str | None = None,
    decimals: int = 2,
) -> str:
    """A line of the legacy `-outfmt` for the alignment of `qseq` against `sseq`, with the counts
    BLAST+ would give it. `pident` overrides the identity, which is otherwise written with
    `decimals` decimals: 2 as the legacy BLAST+ wrote it, 3 as 2.17.0 does."""
    columns = list(zip(qseq, sseq, strict=True))
    gaps = sum(1 for query, subject in columns if "-" in (query, subject))
    mismatch = sum(
        1 for query, subject in columns if query != subject and "-" not in (query, subject)
    )
    gapopen = len(re.findall("-+", qseq)) + len(re.findall("-+", sseq))
    qend = qstart + len(qseq) - qseq.count("-") - 1
    send = sstart + len(sseq) - sseq.count("-") - 1
    identity = pident or f"{100 * (len(qseq) - mismatch - gaps) / len(qseq):.{decimals}f}"
    fields = (
        qseqid,
        sseqid,
        identity,
        len(qseq),
        mismatch,
        gapopen,
        gaps,
        qstart,
        qend,
        sstart,
        send,
        qseq,
        sseq,
        "1e-50",
        "100",
    )
    return ",".join(str(field) for field in fields) + "\n"


# Comparison


def diff_records(expected: str, actual: str, where: str) -> list[str]:
    """Each line of `actual` that differs from `expected`, named by `where` and its first field,
    the case's SNP id. Lines are compared as text, line endings and carriage returns included."""
    old = legacy.lines_of(expected)
    new = legacy.lines_of(actual)
    differences: list[str] = []
    for index in range(max(len(old), len(new))):
        want = old[index] if index < len(old) else None
        got = new[index] if index < len(new) else None
        if want == got:
            continue
        case = (want or got or "").split(",", 1)[0]
        differences.append(
            f"{where}, case {case} (line {index + 1}): expected {want!r}, got {got!r}"
        )
    return differences


# The cases folder


@dataclass(frozen=True)
class Step2Run:
    name: str
    species: str


@dataclass(frozen=True)
class Cases:
    """`cases.json`: how the cases were generated, and what they are."""

    seed: str
    genes: int
    positions: int
    step2: tuple[Step2Run, ...]
    step3: tuple[str, ...]

    def to_json(self) -> str:
        content = {
            "seed": self.seed,
            "genes": self.genes,
            "positions": self.positions,
            "step2": [{"name": run.name, "species": run.species} for run in self.step2],
            "step3": list(self.step3),
        }
        return json.dumps(content, indent=2) + "\n"


def read_cases(folder: Path) -> Cases:
    path = folder / CASES
    try:
        content = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
        runs = cast(list[dict[str, str]], content["step2"])
        return Cases(
            str(content["seed"]),
            int(cast(int, content["genes"])),
            int(cast(int, content["positions"])),
            tuple(Step2Run(run["name"], run["species"]) for run in runs),
            tuple(str(family) for family in cast(list[object], content["step3"])),
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ParityError(f"can't read {path}: {error}") from error


# Generating cases (design.md, decision 10)


def write_cases(
    out: Path,
    data: Path,
    *,
    seed: str = SEED,
    genes: int = GENES,
    positions: int = POSITIONS,
    families: Iterable[str] | None = None,
) -> Cases:
    """Write step-2 and step-3 cases to `out`, the same files for the same data and seed.

    Step 3 gets cases for each family in the data folder's library, or each of `families`.
    """
    library = data / psep.LIBRARY
    names = (
        sorted(families)
        if families is not None
        else sorted(path.name.removesuffix(".paml") for path in library.glob("*.paml"))
    )
    if (library / f"{NO_SUCH_FAMILY}.paml").exists():
        raise ParityError(f"the library has {NO_SUCH_FAMILY}, the cases' family that isn't")
    species = read_species(open_lines(data / psep.SPECIES), psep.SPECIES)
    for name in names:
        rng = random.Random(f"{seed}:{name}")  # noqa: S311 (test cases, not secrets)
        write(
            out / STEP3 / f"{name}.snpparse",
            family_cases(library, name, species, rng, genes, positions),
        )
    runs = step2_cases(random.Random(f"{seed}:step2"))  # noqa: S311 (test cases, not secrets)
    for run, (_, blast, snps) in runs.items():
        write(out / STEP2 / f"{run}.blast", blast)
        write(out / STEP2 / f"{run}.input", snps)
    cases = Cases(
        seed,
        genes,
        positions,
        tuple(Step2Run(run, species_code) for run, (species_code, _, _) in runs.items()),
        tuple(names),
    )
    write(out / CASES, cases.to_json())
    return cases


@dataclass(frozen=True)
class _Gene:
    """A gene line of the `.orig.tree`: its identifier, the AN the Perl finds for it, and that
    AN's sequence in the `.rst`."""

    gene: str
    an: int | None
    sequence: str | None

    @property
    def residues(self) -> list[int]:
        """The column of each residue, 1-based: `getCorrectnum`'s column for each position."""
        if self.sequence is None:
            return []
        return [column for column, residue in enumerate(self.sequence, 1) if "A" <= residue <= "Z"]


def family_cases(
    library: Path,
    family: str,
    species: dict[str, int],
    rng: random.Random,
    genes: int,
    positions: int,
) -> str:
    """One family's step-3 cases, as snpParse records, grouped by gene (`SCORE-11`).

    A "no family" row and an unmapped row, then for each chosen gene: its first and last
    residue, one past the end, a wrong wild type, and positions whose walks stop at nodes of each
    kind the family's walks can reach, then random ones, `positions` in all.
    """
    tree_lines = list(open_lines(library / f"{family}.orig.tree"))
    rst_lines = list(open_lines(library / f"{family}.rst"))
    lookup = legacy.GeneLookup(tree_lines)
    sequences = legacy.sequences(rst_lines)
    candidates: list[_Gene] = []
    for gene in read_orig_tree(tree_lines, f"{family}.orig.tree").genes.values():
        try:
            an = lookup.find_an(gene)
        except ValueError:
            continue
        candidates.append(_Gene(gene, an, sequences.get(str(an)) if an is not None else None))
    tree = _tree(library, family, rst_lines, tree_lines, species)
    chosen = _choose_genes(candidates, tree, rng, genes)
    stops = _stops(library, family, tree, chosen) if tree is not None else {}

    first = chosen[0].gene if chosen else ""
    rows = [
        _row("no-family", NO_SUCH_FAMILY, first, 1, "M", rng),
        _row("unmapped", family, first, None, "M", rng),
    ]
    covered: set[str] = set()
    for number, gene in enumerate(chosen, 1):
        for label, position, wt in _positions(
            gene, stops.get(gene.gene, {}), covered, rng, positions
        ):
            rows.append(_row(f"g{number}-{label}", family, gene.gene, position, wt, rng))
    return "".join(rows)


def _tree(
    library: Path, family: str, rst_lines: list[str], tree_lines: list[str], species: dict[str, int]
) -> psep.FamilyTree | None:
    """The family's tree, or None where a strict reader rejects one of its files."""
    paml = library / f"{family}.paml"
    try:
        header = read_header(open_lines(paml), paml.name)
        rows = legacy.paml_rows(open_lines(paml))
        return psep.family_tree(family, header, rows, rst_lines, tree_lines, species)
    except LibraryFormatError:
        return None


def _path_kinds(tree: psep.FamilyTree, gene: _Gene) -> set[str]:
    """The kinds of the nodes from the gene's start column to the root, whatever the residues."""
    node = tree.start(gene.an)
    kinds: set[str] = set()
    while node is not None and 1 <= node <= tree.header.columns:
        kinds.add(tree.kinds.get(node, "not a node"))
        if node == tree.header.root:
            break
        node = tree.header.parents[node - 1]
    return kinds


def _choose_genes(
    candidates: list[_Gene], tree: psep.FamilyTree | None, rng: random.Random, count: int
) -> list[_Gene]:
    """`count` genes: first, for each kind of node on the genes' paths to the root, rarest kind
    first, one gene whose path has it; then genes at random."""
    chosen: list[_Gene] = []
    if tree is not None:
        paths = {gene.gene: _path_kinds(tree, gene) for gene in candidates}
        kinds = {kind for path in paths.values() for kind in path}
        by_kind = {
            kind: [gene for gene in candidates if kind in paths[gene.gene]] for kind in kinds
        }
        for kind in sorted(kinds, key=lambda kind: (len(by_kind[kind]), kind)):
            if len(chosen) == count or any(kind in paths[gene.gene] for gene in chosen):
                continue
            chosen.append(rng.choice(by_kind[kind]))
    rest = [gene for gene in candidates if gene not in chosen]
    chosen += rng.sample(rest, min(count - len(chosen), len(rest)))
    return chosen


def _stops(
    library: Path, family: str, tree: psep.FamilyTree, genes: list[_Gene]
) -> dict[str, dict[str, list[int]]]:
    """For each gene, the positions whose walk stops at a node of each kind, from one pass over
    the `.paml`."""
    columns = {
        gene.gene: {column: number for number, column in enumerate(gene.residues, 1)}
        for gene in genes
    }
    starts = {gene.gene: tree.start(gene.an) for gene in genes}
    stops: dict[str, dict[str, list[int]]] = {gene.gene: {} for gene in genes}
    paml = library / f"{family}.paml"
    _, sites = iter_sites(open_lines(paml), paml.name)
    for cells in sites:
        for gene in genes:
            position = columns[gene.gene].get(cells.number)
            if position is None or gene.sequence is None:
                continue
            path = tree.path(starts[gene.gene], cells, gene.sequence[cells.number - 1])
            if path:
                kind = tree.kinds.get(path[-1], "not a node")
                stops[gene.gene].setdefault(kind, []).append(position)
    return stops


def _positions(
    gene: _Gene,
    stops: dict[str, list[int]],
    covered: set[str],
    rng: random.Random,
    count: int,
) -> list[tuple[str, int, str]]:
    """The gene's cases: a label, a position and a wild type each."""
    residues = gene.residues
    sequence = gene.sequence or ""
    if not residues:
        # No sequence: the Perl can't score any position. A few, all with their own label.
        return [
            (f"p{position}", position, rng.choice(AMINO_ACIDS)) for position in range(1, count + 1)
        ]
    length = len(residues)

    def wt(position: int) -> str:
        return sequence[residues[position - 1] - 1]

    # One past the end, getCorrectnum takes the last character it steps on.
    steps = len(psep.RESIDUE_OR_GAP.findall(sequence))
    last = sequence[steps - 1] if steps and "A" <= sequence[steps - 1] <= "Z" else wt(length)
    wrong = rng.randint(1, length)
    cases = [
        ("start", 1, wt(1)),
        ("end", length, wt(length)),
        ("past-end", length + 1, last),
        ("wrong-wt", wrong, rng.choice([acid for acid in AMINO_ACIDS if acid != wt(wrong)])),
    ]
    used = {1, length}
    for kind in sorted(stops):
        if len(cases) == count or kind in covered:
            continue
        options = [position for position in stops[kind] if position not in used]
        if options:
            position = rng.choice(options)
            cases.append((f"p{position}", position, wt(position)))
            used.add(position)
            covered.add(kind)
    rest = [position for position in range(1, length + 1) if position not in used]
    for position in sorted(rng.sample(rest, min(count - len(cases), len(rest)))):
        cases.append((f"p{position}", position, wt(position)))
    return cases[:count]


def _row(
    snp_id: str, family: str, gene: str, mapped: int | None, wt: str, rng: random.Random
) -> str:
    """A snpParse record. The submitted position differs from the mapped one, as it does when the
    query's numbering differs from the family sequence's, so that the result shows which it uses."""
    position = (mapped or 1) + rng.randint(0, 20)
    mut = rng.choice([acid for acid in AMINO_ACIDS if acid != wt])
    mapped_text = "" if mapped is None else str(mapped)
    return f"{snp_id},P0001,{family},{gene},{position},{mapped_text},{wt},{mut}\n"


# Step-2 cases: alignments written as BLAST lines, and SNPs on them

HUMAN_GENE = "HUMAN|HGNC=1|UniProtKB=P00001:PTHR00001:SF1"
MOUSE_GENE = "MOUSE|MGI=MGI=1|UniProtKB=Q00001:PTHR00002:SF2"
RAT_GENE = "RAT|RGD=1|UniProtKB=R00001:PTHR00003:SF3"
# Each listed case: its query id, its alignments (subject id, query, subject, query start, subject
# start), and its SNPs (position as written, wild type). The cases of design.md, decision 10.
LISTED: tuple[
    tuple[str, tuple[tuple[str, str, str, int, int], ...], tuple[tuple[str, str], ...]], ...
] = (
    (
        "gap-in-query",
        ((HUMAN_GENE, "MK-VL", "MKWVL", 1, 1),),
        (("1", "M"), ("2", "K"), ("3", "V"), ("3", "W"), ("4", "L"), ("5", "L")),
    ),
    (
        "gap-in-subject",
        ((HUMAN_GENE, "MKVLE", "MK-LE", 1, 1),),
        (("2", "K"), ("3", "V"), ("4", "L"), ("5", "E"), ("6", "E")),
    ),
    (
        "gaps-both-sides",
        ((HUMAN_GENE, "MA--KVLE-GH", "MAPQK-LEDGH", 3, 7),),
        (
            ("3", "M"),
            ("4", "A"),
            ("5", "K"),
            ("6", "V"),
            ("7", "L"),
            ("8", "E"),
            ("9", "G"),
            ("10", "H"),
            ("11", "H"),
        ),
    ),
    (
        "offset",
        ((HUMAN_GENE, "KVLEA", "KVLEA", 5, 20),),
        (("4", "K"), ("5", "K"), ("6", "V"), ("9", "A"), ("10", "A")),
    ),
    (
        "x-and-stop",
        ((HUMAN_GENE, "MKXV*LE", "MKAVWLE", 1, 1),),
        (("3", "A"), ("3", "X"), ("4", "V"), ("5", "W"), ("5", "L"), ("6", "L"), ("7", "E")),
    ),
    (
        "leading-zero",
        ((HUMAN_GENE, "MKVLEAGHIKL", "MKVLEAGHIKL", 1, 1),),
        (("010", "I"), ("03", "V"), ("0", "M"), ("+5", "E"), ("10.0", "I")),
    ),
    (
        "wrong-wt",
        ((HUMAN_GENE, "MKVLE", "MKVLE", 1, 1),),
        (("2", "A"), ("3", "v"), ("4", "LL"), ("4", "")),
    ),
    (
        "tie",
        (
            ("HUMAN|HGNC=2|UniProtKB=a00001:PTHR00004:SF1", "MKVLE", "MKVLE", 1, 1),
            ("HUMAN|HGNC=2|UniProtKB=A00001:PTHR00005:SF1", "MKVLE", "MKVLE", 1, 1),
        ),
        (("2", "K"),),
    ),
    (
        "ranking",
        (
            (HUMAN_GENE, "A" + "KVLEGHIKLM", "A" + "WWWWWWWWWW", 1, 1),
            ("HUMAN|HGNC=3|UniProtKB=P00003:PTHR00006:SF1", "AKVLEGHIKL", "AWWWWWWWWW", 1, 1),
        ),
        (("2", "W"),),
    ),
    (
        "filtered",
        (
            (MOUSE_GENE, "MKVLEGHIKL", "MKVLEGHIKL", 1, 1),
            (HUMAN_GENE, "MKVLEGHIKL", "MKVLEGHIKW", 1, 1),
        ),
        (("2", "K"), ("10", "W")),
    ),
    ("no-hit", (), (("2", "K"),)),
    ("NA", ((HUMAN_GENE, "MKVLE", "MKVLE", 1, 1),), (("2", "K"),)),
)
# Species substrings (MAP-2): run with RAT, which the MOUSE line spells in its aligned sequences.
SPECIES_CASES: tuple[
    tuple[str, tuple[tuple[str, str, str, int, int], ...], tuple[tuple[str, str], ...]], ...
] = (
    (
        "substring",
        (
            (MOUSE_GENE, "MGRATKVLEG", "MGRATKVLEG", 1, 1),
            (RAT_GENE, "MGRATKVLEG", "MGRATKVLEW", 1, 1),
        ),
        (("3", "R"), ("10", "G")),
    ),
    (
        "lower-case",
        (("MOUSE|MGI=MGI=2|UniProtKB=rat001:PTHR00002:SF2", "MKVLE", "MKVLE", 1, 1),),
        (("2", "K"),),
    ),
)


def step2_cases(rng: random.Random) -> dict[str, tuple[str, str, str]]:
    """Each step-2 run: its species, its BLAST lines and its SNP lines."""
    runs = {
        "listed": ("HUMAN", *_case_text(LISTED)),
        "species": ("RAT", *_case_text(SPECIES_CASES)),
        "unfiltered": ("NA", *_case_text(LISTED)),
        "random": ("HUMAN", *_case_text(_random_cases(rng, 30))),
    }
    return runs


def _case_text(
    cases: Iterable[
        tuple[str, Sequence[tuple[str, str, str, int, int]], Sequence[tuple[str, str]]]
    ],
) -> tuple[str, str]:
    blast: list[str] = []
    snps: list[str] = []
    for query, alignments, positions in cases:
        for sseqid, qseq, sseq, qstart, sstart in alignments:
            blast.append(blast_line(query, sseqid, qseq, sseq, qstart=qstart, sstart=sstart))
        for number, (position, wt) in enumerate(positions, 1):
            snps.append(f"{query}-{number}|{query}|{position}|{wt};V\n")
    return "".join(blast), "".join(snps)


def _random_cases(
    rng: random.Random, count: int
) -> list[tuple[str, list[tuple[str, str, str, int, int]], list[tuple[str, str]]]]:
    """Random alignments with gaps on either side, one to three hits each, and SNPs at the
    alignment's start, after a gap, at its end, past it, and at random."""
    cases: list[tuple[str, list[tuple[str, str, str, int, int]], list[tuple[str, str]]]] = []
    for number in range(1, count + 1):
        query = f"R{number:03d}"
        length = rng.randint(8, 40)
        qseq = [rng.choice(AMINO_ACIDS) for _ in range(length)]
        sseq = [residue if rng.random() < 0.8 else rng.choice(AMINO_ACIDS) for residue in qseq]
        for _ in range(rng.randint(0, 3)):
            # Never at either end, and never on both sides of one column, as BLAST+ writes them.
            side, other, at = *rng.choice(((qseq, sseq), (sseq, qseq))), rng.randint(1, length - 2)
            if other[at] != "-":
                side[at] = "-"
        qstart, sstart = rng.randint(1, 30), rng.randint(1, 30)
        alignments = [
            (
                HUMAN_GENE if rng.random() < 0.8 else MOUSE_GENE,
                "".join(qseq),
                "".join(sseq),
                qstart,
                sstart,
            )
        ]
        for _ in range(rng.randint(0, 2)):
            other = [
                residue if residue != "-" and rng.random() < 0.7 else rng.choice(AMINO_ACIDS)
                for residue in qseq
            ]
            accession, family = rng.randint(1, 99), rng.randint(1, 9)
            gene = f"HUMAN|HGNC={accession}|UniProtKB=P{accession:05d}:PTHR{family:05d}:SF1"
            alignments.append((gene, "".join(qseq), "".join(other), qstart, rng.randint(1, 30)))
        residues = [residue for residue in qseq if residue != "-"]
        qend = qstart + len(residues) - 1
        after_gap = [
            qstart + sum(1 for residue in qseq[:index] if residue != "-")
            for index in range(1, length)
            if qseq[index - 1] == "-" and qseq[index] != "-"
        ]
        wanted = [
            qstart,
            qstart + 1,
            qend,
            qend + 1,
            *after_gap,
            *rng.sample(range(qstart, qend + 1), 2),
        ]
        snps: list[tuple[str, str]] = []
        for position in wanted:
            index = position - qstart
            wt = residues[index] if 0 <= index < len(residues) else rng.choice(AMINO_ACIDS)
            if rng.random() < 0.15:
                wt = rng.choice(AMINO_ACIDS)
            snps.append((str(position), wt))
        cases.append((query, alignments, snps))
    return cases


def trace_cases(cases: Path, data: Path) -> list[psep.Walk]:
    """The walk of each step-3 case that's walked, through the port, for coverage reports."""
    walks: list[psep.Walk] = []
    for family in read_cases(cases).step3:
        lines = legacy.lines_of(read(cases / STEP3 / f"{family}.snpparse"))
        walks += psep.trace(lines, data)
    return walks


# Commands


def self_check(reference: Reference, golden: Path, data: Path, cases: Path | None) -> list[str]:
    """Run spec §7.3's and §7.5's inputs through the reference, and compare with their goldens.

    Returns the differences. Where there are none and `cases` is given, saves each run's step-2
    output there, as `<run>.snpparse`.
    """
    blast = read(golden / SELF_CHECK_BLAST)
    differences: list[str] = []
    parsed: dict[str, str] = {}
    for name, snps, species, expected in SELF_CHECK:
        parsed[name] = reference.step2(blast, read(golden / snps), species)
        result = reference.step3(parsed[name], data)
        differences += diff_records(read(golden / expected), result, f"self-check {name}")
    if not differences and cases is not None:
        for name, text in parsed.items():
            write(cases / f"{name}.snpparse", text)
    return differences


def run_reference(
    reference: Reference, cases: Path, data: Path, families: Iterable[str] | None = None
) -> dict[str, int]:
    """Run every case in the folder through the reference, and write each output beside its input.

    `families` limits step 3 to those families. Returns the number of cases run, per run name.
    """
    listed = read_cases(cases)
    counts: dict[str, int] = {}
    for run in listed.step2:
        base = cases / STEP2 / run.name
        output = reference.step2(
            read(base.with_suffix(".blast")), read(base.with_suffix(".input")), run.species
        )
        write(base.with_suffix(".snpparse"), output)
        counts[f"step 2 {run.name}"] = len(output.splitlines())
    wanted = set(families) if families is not None else None
    for family in listed.step3:
        if wanted is not None and family not in wanted:
            continue
        base = cases / STEP3 / family
        output = reference.step3(read(base.with_suffix(".snpparse")), data)
        write(base.with_suffix(".out"), output)
        counts[family] = len(output.splitlines())
    return counts


# Checking the port


def check_self(golden: Path, cases: Path, data: Path) -> list[str]:
    """The port on the self-check's inputs: step 2 against the reference's snpParse saved in
    `cases`, and steps 2 and 3 against the spec's goldens."""
    blast = legacy.lines_of(read(golden / SELF_CHECK_BLAST))
    differences: list[str] = []
    for name, snps, species, expected in SELF_CHECK:
        parsed = "".join(hits.parse(blast, hits.read_snps(read(golden / snps)), species))
        differences += diff_records(read(cases / f"{name}.snpparse"), parsed, f"step 2 {name}")
        result = "".join(psep.step3(legacy.lines_of(parsed), data))
        differences += diff_records(read(golden / expected), result, f"spec {name}")
    return differences


def check_step2(cases: Path, run: Step2Run) -> list[str]:
    """The port's step 2 on one run's BLAST and SNP lines, against the reference's snpParse."""
    base = cases / STEP2 / run.name
    blast = legacy.lines_of(read(base.with_suffix(".blast")))
    snps = hits.read_snps(read(base.with_suffix(".input")))
    parsed = "".join(hits.parse(blast, snps, run.species))
    return diff_records(read(base.with_suffix(".snpparse")), parsed, f"step 2 {run.name}")


def check_step3(cases: Path, family: str, data: Path) -> list[str]:
    """The port's step 3 on one family's cases, against the reference's output."""
    base = cases / STEP3 / family
    result = "".join(psep.step3(legacy.lines_of(read(base.with_suffix(".snpparse"))), data))
    return diff_records(read(base.with_suffix(".out")), result, family)


def coverage(walks: Iterable[psep.Walk]) -> dict[str, tuple[int, int]]:
    """For each kind of node, the number of walks that stopped at one and that visited one."""
    stopped: dict[str, int] = {}
    visited: dict[str, int] = {}
    for walk in walks:
        if walk.kinds:
            stopped[walk.kinds[-1]] = stopped.get(walk.kinds[-1], 0) + 1
        for kind in set(walk.kinds):
            visited[kind] = visited.get(kind, 0) + 1
    return {kind: (stopped.get(kind, 0), visited[kind]) for kind in sorted(visited)}
