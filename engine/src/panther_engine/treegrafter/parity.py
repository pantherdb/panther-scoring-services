"""Parity with EBI's command line at the pinned commit: the golden cases, the reference run, and the
comparison (adopt-treegrafter, design.md, decision 10).

The reference is EBI's `treegrafter` in the engine image: `hmmsearch` with `treegrafter.sh`'s
flags, then EBI's console script, `treegrafter run -e 0.00000001 --print-go`, from the upstream
`pyproject.toml`. No reference image is needed, since EBI's code and the tools are already in the
engine's. A golden folder, `tests/golden/treegrafter/`, holds:

- `cases.json`: each case's name, and why it's there;
- `inputs/<case>.txt`: the engine's sequence, as the API sends it;
- `parity/<goldens>/<case>/result.tsv`: EBI's `--print-go` output for the case, made on `fixture`,
  the committed fixture, or `full`, the full library, on amd64;
- `parity/<goldens>-arm64/<case>/result.tsv`: the same on arm64, for a case whose result differs
  there.

`hmmsearch`'s report isn't kept: it ends with CPU times (port-hmmscore's lesson). A result's row
maps to a hit as the engine's does: `-` is no value, and the GO terms are split on `,`. EBI's row
has no graft point, so the comparison leaves the engine's out.
"""

import dataclasses
import json
import os
import platform
import shutil
import sys
import tempfile
import time
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from panther_engine.core.data import DataFolderError, MissingDataError, data_root, service_folder
from panther_engine.core.hmmer import program
from panther_engine.core.process import run_tool
from panther_engine.treegrafter import data
from panther_engine.treegrafter.scoring import (
    CUTOFF,
    QUERY,
    SEARCH_OPTIONS,
    TimeLimitError,
    TreegrafterError,
    TreegrafterHit,
    TreegrafterInput,
    active,
    hit_from_row,
    score,
)

GOLDEN = Path("tests/golden/treegrafter")
FIXTURE = Path("tests/fixtures/treegrafter")
CASES = "cases.json"
INPUTS = "inputs"
PARITY = "parity"
GOLDEN_SETS = ("fixture", "full")
ARM64 = "-arm64"
RESULT = "result.tsv"
# EBI's `--print-go` header (treegrafter.py 582 to 586).
HEADER = (
    "query_id\tpanther_id\tscore\tevalue\tdom_score\tdom_evalue\thmm_start\thmm_end\tali_start\t"
    "ali_end\tenv_start\tenv_end\tnode_id\tgo_terms\tprotein_class"
)
# A graft on the full library can take minutes on a slow machine.
TIMEOUT = 3600.0


class ParityError(Exception):
    """The golden folder, a case or the reference run has a problem."""


@dataclass(frozen=True)
class Case:
    name: str
    why: str


def read_cases(golden: Path = GOLDEN) -> list[Case]:
    """`cases.json`'s cases, each with its input."""
    try:
        listed = cast(object, json.loads((golden / CASES).read_text(encoding="utf-8")))
    except (OSError, ValueError) as error:
        raise ParityError(f"can't read {golden / CASES}: {error}") from error
    if not isinstance(listed, dict) or not isinstance(
        cases := cast(dict[str, object], listed).get("cases"), list
    ):
        raise ParityError(f"{golden / CASES} needs a cases list")
    found: list[Case] = []
    for item in cast(list[object], cases):
        fields = cast(dict[str, object], item) if isinstance(item, dict) else {}
        name, why = fields.get("name"), fields.get("why")
        if not isinstance(name, str) or not isinstance(why, str) or set(fields) != {"name", "why"}:
            raise ParityError(f"{golden / CASES}: a case needs a name and a why, only: {item!r}")
        found.append(Case(name, why))
    names = [case.name for case in found]
    if len(set(names)) != len(names):
        raise ParityError(f"{golden / CASES} names a case twice")
    return found


def sequence_of(golden: Path, name: str) -> str:
    try:
        return (golden / INPUTS / f"{name}.txt").read_text(encoding="ascii")
    except (OSError, UnicodeDecodeError) as error:
        raise ParityError(f"can't read case {name}'s input: {error}") from error


def chosen(cases: list[Case], names: Iterable[str] | None) -> list[Case]:
    if not names:
        return cases
    wanted = list(names)
    known = {case.name for case in cases}
    unknown = [name for name in wanted if name not in known]
    if unknown:
        raise ParityError(f"no such case: {', '.join(unknown)}")
    return [case for case in cases if case.name in wanted]


@contextmanager
def data_folder(goldens: str, data_dir: Path | None, fixture: Path) -> Generator[Path]:
    """The data folder a set's runs read: for `fixture`, the fixture installed in a temporary
    folder; for `full`, `data_dir` or `PANTHER_DATA_DIR`."""
    if goldens == "fixture":
        with tempfile.TemporaryDirectory(prefix="treegrafter-fixture-") as work:
            data.install_fixture(fixture, Path(work))
            yield Path(work)
    else:
        yield data_root(data_dir)


def architecture() -> str:
    machine = platform.machine().lower()
    return "arm64" if machine in ("arm64", "aarch64") else "amd64"


def result_path(golden: Path, goldens: str, name: str) -> Path:
    """The reference's output for a case: the arm64 copy on arm64, if there is one."""
    if architecture() == "arm64":
        copy = golden / PARITY / f"{goldens}{ARM64}" / name / RESULT
        if copy.is_file():
            return copy
    return golden / PARITY / goldens / name / RESULT


# The reference run


def console_script() -> Path:
    """EBI's `treegrafter` command, beside the running Python's, or on PATH."""
    beside = Path(sys.executable).parent / "treegrafter"
    if beside.is_file():
        return beside
    return program("treegrafter")


def reference_arguments(
    library: Path, release: Path, query: Path, report: Path, out: Path, work: Path
) -> tuple[list[str], list[str]]:
    """`hmmsearch`'s arguments, as `treegrafter.sh search` gives them, and EBI's `run`'s, with
    `--print-go` and its temporary files in `work`."""
    search = [*SEARCH_OPTIONS, str(library / data.BINHMM), str(query)]
    run = [
        "run",
        "-e",
        f"{CUTOFF:.8f}",
        "--print-go",
        "-o",
        str(out),
        "-d",
        str(library),
        "-a",
        str(release),
        "-T",
        str(work),
        str(query),
        str(report),
    ]
    return search, run


def run_reference(
    golden: Path,
    goldens: str,
    data_dir: Path | None,
    names: Iterable[str] | None,
    *,
    fixture: Path = FIXTURE,
) -> list[str]:
    """Run each case through EBI's command line, one at a time, each in a temporary folder, and
    move its output into `parity/<goldens>/<case>/` once it has run. Returns the cases' names."""
    cases = chosen(read_cases(golden), names)
    target = golden / PARITY / (goldens if architecture() == "amd64" else f"{goldens}{ARM64}")
    with data_folder(goldens, data_dir, fixture) as root:
        library = service_folder(data.SERVICE, data.VERSION, root)
        date = active(root)
        if date is None:
            raise MissingDataError(f"no annotation release is active in {library}")
        release = library / data.ANNOTATIONS / date
        for case in cases:
            sequence = sequence_of(golden, case.name)
            with tempfile.TemporaryDirectory(prefix="treegrafter-reference-") as work:
                folder = Path(work)
                query, report, out = (
                    folder / "query.fasta",
                    folder / "hmmsearch.out",
                    folder / RESULT,
                )
                query.write_text(f">{QUERY}\n{sequence}\n", encoding="ascii")
                temporary = folder / "tmp"
                temporary.mkdir()
                search, run = reference_arguments(library, release, query, report, out, temporary)
                ran = run_tool(program("hmmsearch"), search, timeout=TIMEOUT, stdout=report)
                if ran.returncode != 0:
                    raise ParityError(
                        f"{case.name}: hmmsearch exited with {ran.returncode}: {ran.stderr}"
                    )
                ran = run_tool(console_script(), run, timeout=TIMEOUT)
                if ran.returncode != 0 or not out.is_file():
                    raise ParityError(
                        f"{case.name}: EBI's treegrafter exited with {ran.returncode}: {ran.stderr}"
                    )
                place = target / case.name
                place.mkdir(parents=True, exist_ok=True)
                # Copied beside its place first, since the temporary folder may be on another
                # device, then moved into place.
                partial = place / f".{RESULT}.partial"
                shutil.copyfile(out, partial)
                os.replace(partial, place / RESULT)
    return [case.name for case in cases]


# The comparison


def expected_hit(result: Path) -> TreegrafterHit | None:
    """The hit EBI's output gives: None for the header alone, the row's hit for one row. Raises
    ParityError for any other output."""
    lines = result.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != HEADER:
        raise ParityError(f"{result} doesn't start with EBI's --print-go header")
    rows = [line.split("\t") for line in lines[1:]]
    if not rows:
        return None
    if len(rows) != 1 or rows[0][0] != QUERY:
        raise ParityError(f"{result} has {len(rows)} rows, not one for {QUERY}")
    try:
        return hit_from_row(rows[0], None)
    except TreegrafterError as error:
        raise ParityError(f"{result}: {error}") from error


def differences(actual: TreegrafterHit | None, expected: TreegrafterHit | None) -> list[str]:
    """Each field that differs, the graft point left out, which EBI's row doesn't have."""
    if actual is None or expected is None:
        if actual == expected:
            return []
        return [f"hit: the engine's {actual!r}, the reference's {expected!r}"]
    engine = dataclasses.asdict(dataclasses.replace(actual, graft_point=None))
    reference = dataclasses.asdict(expected)
    return [
        f"{field}: the engine's {engine[field]!r}, the reference's {reference[field]!r}"
        for field in engine
        if engine[field] != reference[field]
    ]


@dataclass(frozen=True)
class Checked:
    name: str
    seconds: float
    differences: tuple[str, ...]


def run_check(
    golden: Path,
    goldens: str,
    data_dir: Path | None,
    names: Iterable[str] | None,
    *,
    fixture: Path = FIXTURE,
) -> list[Checked]:
    """Graft each case with the engine, and compare its hit with the reference's output. A case
    with no output is a difference, and isn't grafted."""
    cases = chosen(read_cases(golden), names)
    checks: list[Checked] = []
    with data_folder(goldens, data_dir, fixture) as root:
        for case in cases:
            result = result_path(golden, goldens, case.name)
            if not result.is_file():
                checks.append(Checked(case.name, 0.0, (f"no reference output: {result}",)))
                continue
            expected = expected_hit(result)
            started = time.monotonic()
            try:
                actual = score(TreegrafterInput(sequence_of(golden, case.name)), data_dir=root).hit
            except (
                TreegrafterError,
                TimeLimitError,
                MissingDataError,
                DataFolderError,
                ValueError,
            ) as error:
                checks.append(
                    Checked(case.name, time.monotonic() - started, (f"grafting failed: {error}",))
                )
                continue
            checks.append(
                Checked(case.name, time.monotonic() - started, tuple(differences(actual, expected)))
            )
    return checks
