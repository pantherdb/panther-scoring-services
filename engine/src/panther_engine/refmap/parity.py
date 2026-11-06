"""Parity with the legacy `map_panther.pl`: the golden cases, the Perl reference, and the
comparison.

The reference is `map_panther.pl` at RefProteomeMapper's `4fc6a09`, in the `refmap-reference` image
(docs/parity/golden-setup.md). A golden folder, such as `tests/golden/refmap/`, holds:

- `cases.json`: each case's name, what it shows, its ID list, and either an organism, whose
  classification file is in the data folder, or a made-up classification file in the folder. A
  case the port refuses names the error and its divergence row;
- `release/`: the data server's test lists, unchanged;
- `cases/`: the hand-made ID lists and made-up classification files;
- `out/`: `map_panther.pl`'s standard output for each case, byte for byte.

Files are read as bytes, and decoded as Latin-1 where they are compared, so every byte, carriage
returns included, survives.
"""

import json
import os
import random
import shutil
import subprocess
import tempfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from panther_engine.core.data import DataFolderError, MissingDataError
from panther_engine.core.manifest import ManifestError, relative_path
from panther_engine.core.process import run_tool
from panther_engine.refmap.mapping import (
    ENCODING,
    RefmapInput,
    map_ids,
    read_id_list,
    render,
)
from panther_engine.refmap.organisms import (
    CLASSIFICATION,
    CODE,
    FOLDER,
    ORGANISM_CODES,
    ORGANISM_NAMES,
)

GOLDEN = Path("tests/golden/refmap")
CASES = "cases.json"
OUT = "out"
SCRIPT = Path("/opt/refmap-reference/map_panther.pl")
# The largest file, ARAVE, maps in under a second; generous, so a slow machine doesn't fail.
TIMEOUT = 600.0
REFUSALS = ("ValueError", "MissingDataError")
# The code a made-up file is mapped as, in a temporary data folder.
MADE_UP = "ENDPU"
# The full run's extras: from a generator seeded with "<seed>:<code>", this many of each kind.
SEED = "port-refmap"
EXTRAS = 20


class ParityError(Exception):
    """The reference can't run, or a golden folder can't be read."""


@dataclass(frozen=True)
class Case:
    name: str
    what: str
    list: str
    organism: str | None = None
    file: str | None = None
    refused: str | None = None
    divergence: int | None = None

    def classification(self, golden: Path, data: Path) -> Path:
        """The classification file the Perl reads: the organism's in the data folder `data`, or
        the made-up file in the golden folder."""
        if self.file is not None:
            return golden / self.file
        return data / FOLDER / CLASSIFICATION / cast(str, self.organism)


def read_cases(golden: Path) -> tuple[Case, ...]:
    """The golden folder's cases, in order. Every path must stay inside the folder."""
    try:
        listing: object = json.loads((golden / CASES).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ParityError(f"can't read {golden / CASES}: {error}") from error
    raw = cast(dict[str, object], listing).get("cases") if isinstance(listing, dict) else None
    if not isinstance(raw, list):
        raise ParityError(f"{golden / CASES} has no list of cases")
    cases: list[Case] = []
    for item in cast(list[object], raw):
        fields = cast(dict[str, object], item) if isinstance(item, dict) else {}
        typed = all(
            isinstance(value, int if key == "divergence" else str) for key, value in fields.items()
        )
        try:
            if not typed:
                raise TypeError("a field has the wrong type")
            case = Case(**fields)  # pyright: ignore[reportArgumentType]
        except TypeError as error:
            raise ParityError(f"not a case in {golden / CASES}: {item!r}") from error
        validate_case(case, golden)
        cases.append(case)
    names = [case.name for case in cases]
    if len(set(names)) != len(names):
        raise ParityError(f"{golden / CASES} repeats a case name")
    return tuple(cases)


def validate_case(case: Case, golden: Path) -> None:
    where = f"case {case.name!r} in {golden / CASES}"
    if (case.organism is None) == (case.file is None):
        raise ParityError(f"{where} needs an organism or a file, not both")
    if case.organism is not None and not CODE.fullmatch(case.organism):
        raise ParityError(f"{where}: not an organism code: {case.organism!r}")
    if case.refused not in (None, *REFUSALS) or (case.refused is None) != (case.divergence is None):
        raise ParityError(f"{where}: a refused case names its error and its divergence row")
    for path in (case.list, case.file):
        if path is None:
            continue
        try:
            relative_path(path)
        except ManifestError as error:
            raise ParityError(f"{where}: {error}") from error


# The reference


@dataclass(frozen=True)
class Reference:
    """`map_panther.pl`, run with `perl`."""

    perl: Path
    script: Path = SCRIPT

    @classmethod
    def find(cls, script: Path = SCRIPT) -> "Reference":
        perl = shutil.which("perl")
        if perl is None:
            raise ParityError("no perl on PATH: run this in the refmap-reference image")
        if not script.is_file():
            raise ParityError(f"no {script}: run this in the refmap-reference image")
        return cls(Path(perl).absolute(), script)

    def run(self, classification: Path, gene_list: Path, out: Path) -> None:
        """`perl map_panther.pl -i classification -g gene_list > out`, byte for byte."""
        args = [str(self.script), "-i", str(classification), "-g", str(gene_list)]
        try:
            result = run_tool(self.perl, args, timeout=TIMEOUT, stdout=out)
        except subprocess.TimeoutExpired as error:
            raise ParityError(f"map_panther.pl ran past {TIMEOUT:.0f} s") from error
        if result.returncode != 0:
            raise ParityError(
                f"map_panther.pl exited with status {result.returncode}: {result.stderr.strip()}"
            )


def run_reference(reference: Reference, golden: Path, data: Path) -> dict[str, int]:
    """Run every case through the reference, and write its output to `out/<name>.out`. Returns
    each case's lines of output.

    `data` is the data folder. The Perl reads a missing file as an empty one, so every published
    organism's file must be there before anything runs. The outputs are written to a temporary
    folder, and moved into `out/` only once every case has run: if one fails, `out/` is left as
    it was.
    """
    cases = read_cases(golden)
    for case in cases:
        if not (golden / case.list).is_file():
            raise ParityError(f"case {case.name!r}: no list {golden / case.list}")
        classification = case.classification(golden, data)
        needed = case.file is not None and case.refused is None
        if (case.organism in ORGANISM_CODES or needed) and not classification.is_file():
            raise ParityError(
                f"case {case.name!r}: no classification file {classification}. Fetch the refmap "
                "data: docs/testing/engine.md"
            )
    counts: dict[str, int] = {}
    with tempfile.TemporaryDirectory(dir=golden, prefix=".refmap-reference-") as work:
        written = Path(work)
        for case in cases:
            target = written / f"{case.name}.out"
            try:
                reference.run(case.classification(golden, data), golden / case.list, target)
            except ParityError as error:
                raise ParityError(f"case {case.name!r}: {error}") from error
            counts[case.name] = target.read_bytes().count(b"\n")
        out = golden / OUT
        out.mkdir(exist_ok=True)
        for case in cases:
            os.replace(written / f"{case.name}.out", out / f"{case.name}.out")
    return counts


# The comparison


def golden_lines(path: Path) -> list[str]:
    """The first two fields of each line of the Perl's output. The ID and the PANTHER ID hold no
    tab, and the Perl always prints a third field after a second tab (`REFMAP-5`)."""
    lines = path.read_bytes().decode(ENCODING).split("\n")
    if lines[-1] == "":
        lines.pop()
    return ["\t".join(line.split("\t", 2)[:2]) for line in lines]


def needs_data(case: Case) -> bool:
    """True for a case mapped against an organism's file in the data folder. A made-up file needs
    no data, nor does a refused case: the port refuses it before reading anything."""
    return case.file is None and case.refused is None


def check_case(case: Case, golden: Path, data: Path | None) -> list[str]:
    """Each difference between the port and the reference's output for one case, naming the case
    and the line. A refused case must raise its error instead. `data` is the data folder, read
    only by the cases that `needs_data`: a made-up file is mapped in a temporary one."""
    ids = read_id_list((golden / case.list).read_bytes())
    if case.file is None:
        return compare(case, golden, ids, cast(str, case.organism), data)
    with tempfile.TemporaryDirectory(prefix="refmap-parity-") as work:
        root = Path(work)
        target = root / FOLDER / CLASSIFICATION / MADE_UP
        target.parent.mkdir(parents=True)
        if (golden / case.file).is_file():
            shutil.copyfile(golden / case.file, target)
        return compare(case, golden, ids, MADE_UP, root)


def compare(
    case: Case, golden: Path, ids: tuple[str, ...], organism: str, data: Path | None
) -> list[str]:
    try:
        result = map_ids(RefmapInput(organism, ids), data_dir=data)
    except (ValueError, MissingDataError, DataFolderError) as error:
        raised = type(error).__name__
        if raised == case.refused:
            return []
        wanted = case.refused or "mappings"
        return [f"{case.name}: the port raised {raised} ({error}), not {wanted}"]
    if case.refused is not None:
        return [
            f"{case.name}: the port mapped the IDs, but divergence {case.divergence} has it "
            f"raise {case.refused}"
        ]
    expected = golden_lines(golden / OUT / f"{case.name}.out")
    return compare_lines(case.name, expected, [render(mapping) for mapping in result.mappings])


def compare_lines(name: str, expected: Sequence[str], actual: Sequence[str]) -> list[str]:
    """Each line that differs, by number, and a difference in the number of lines."""
    differences = [
        f"{name} line {number}: the reference has {want!r}, the port {got!r}"
        for number, (want, got) in enumerate(zip(expected, actual, strict=False), 1)
        if want != got
    ]
    if len(expected) != len(actual):
        differences.append(
            f"{name}: the reference has {len(expected):,} lines, the port {len(actual):,}"
        )
    return differences


# The full run


def file_ids(path: Path) -> list[str]:
    """The IDs of a classification file, in file order: the text before each line's first tab."""
    lines = path.read_bytes().decode(ENCODING).split("\n")
    if lines[-1] == "":
        lines.pop()
    return [line.partition("\t")[0] for line in lines]


def extras(ids: Sequence[str], other: Sequence[str], seed: str, code: str) -> list[str]:
    """The full run's extra IDs for one organism, from a generator seeded with `seed:code`: up to
    20 of its IDs repeated, 20 lower-cased, 20 with `-2`, 20 with `.1`, and 20 IDs from `other`,
    the next organism's file. The same IDs, seed and code give the same list."""
    rng = random.Random(f"{seed}:{code}")  # noqa: S311 (test IDs, not secrets)

    def sample(population: Sequence[str]) -> list[str]:
        return rng.sample(population, min(EXTRAS, len(population)))

    return [
        *sample(ids),
        *(id.lower() for id in sample(ids)),
        *(f"{id}-2" for id in sample(ids)),
        *(f"{id}.1" for id in sample(ids)),
        *sample(other),
    ]


@dataclass(frozen=True)
class OrganismRun:
    """One organism of the full run: the IDs compared, and every line that differs."""

    code: str
    ids: int
    differences: tuple[str, ...]


def next_organism(code: str, order: Sequence[str]) -> str:
    """The organism after `code` in `order`; the last one's is the first."""
    return order[(order.index(code) + 1) % len(order)]


def organism_list(
    folder: Path, code: str, seed: str, order: Sequence[str] | None = None
) -> list[str]:
    """The full run's IDs for one organism: every ID of its file in `folder`, in file order, then
    its extras. The IDs from another organism come from the next one in `order`, the published
    list by default, whichever organisms a run covers: a rerun of one organism checks the IDs
    the full run did."""
    order = list(ORGANISM_NAMES) if order is None else order
    ids = file_ids(folder / code)
    following = file_ids(folder / next_organism(code, order))
    return [*ids, *extras(ids, following, seed, code)]


def run_full(
    reference: Reference,
    data: Path,
    codes: Sequence[str],
    seed: str = SEED,
    order: Sequence[str] | None = None,
) -> Iterator[OrganismRun]:
    """Map each organism's list (`organism_list`) through the Perl and the port, and compare,
    one organism at a time. `data` is the data folder. Every organism must be in `order`, and its
    file and the next organism's must be there before anything runs."""
    order = list(ORGANISM_NAMES) if order is None else list(order)
    unknown = [code for code in codes if code not in order]
    if unknown:
        raise ParityError(f"not an organism refmap maps for: {', '.join(map(repr, unknown))}")
    folder = data / FOLDER / CLASSIFICATION
    needed = dict.fromkeys(name for code in codes for name in (code, next_organism(code, order)))
    missing = [name for name in needed if not (folder / name).is_file()]
    if missing:
        raise ParityError(
            f"no classification file in {folder} for {', '.join(missing[:EXTRAS])}"
            + (f" and {len(missing) - EXTRAS:,} more" if len(missing) > EXTRAS else "")
        )
    for code in codes:
        listed = organism_list(folder, code, seed, order)
        yield OrganismRun(code, len(listed), tuple(compare_organism(reference, data, code, listed)))


def compare_organism(reference: Reference, data: Path, code: str, listed: list[str]) -> list[str]:
    with tempfile.TemporaryDirectory(prefix="refmap-full-") as work:
        gene_list, out = Path(work) / "ids", Path(work) / "out"
        gene_list.write_bytes("".join(f"{id}\n" for id in listed).encode(ENCODING))
        reference.run(data / FOLDER / CLASSIFICATION / code, gene_list, out)
        expected = golden_lines(out)
    try:
        result = map_ids(RefmapInput(code, tuple(listed)), data_dir=data)
    except (ValueError, MissingDataError) as error:
        return [f"{code}: the port raised {type(error).__name__} ({error})"]
    return compare_lines(code, expected, [render(mapping) for mapping in result.mappings])
