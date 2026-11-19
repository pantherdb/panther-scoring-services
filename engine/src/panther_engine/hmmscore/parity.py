"""Parity with the legacy `scoreAlignXml.cgi` and `pantherScore.pl`: the golden cases, the Perl
reference, and the comparison (port-hmmscore, design.md, decisions 6 to 8).

The reference is `pantherScoring` at `89ea0ae`, with HMMER 3.1b2, in the `hmmscore-reference`
image (docs/parity/golden-setup.md). A golden folder, `tests/golden/hmmscore/parity/`, holds:

- `cases.json`: each case's name, why it's there, and the CGI's posted text where it differs from
  the engine's sequence;
- `inputs/<case>.txt`: the engine's sequence, as the API sends it;
- `<goldens>/<case>/`, for `sample` (the data sample, on amd64) and `full` (the full library, from
  the staging run): the reference's outputs. `cgi.xml` is the CGI's answer, without its
  `Content-type` header; `best.tsv` is `pantherScore.pl -D B -n`'s, which lists every tied best
  ID, where the CGI shows only the first; `hmmsearch/<ID>.out` is the CGI's `hmmsearch` for each;
- `sample-arm64/<case>.json`: the port's result on arm64, for a case whose arm64 result differs.

A case's expected result comes from `best.tsv`, divergence 13's pick among its IDs, and that ID's
report, by the CGI's rule (`expected`). Files are read as bytes, as Latin-1.

`__all__` is what the API's tests import, to score the golden cases through the API
(wire-hmmscore, decision 7). The engine's CLI and tests use the rest.
"""

import dataclasses
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from panther_engine.core.data import DataFolderError, MissingDataError, service_folder
from panther_engine.core.errors import InputError
from panther_engine.core.process import run_tool
from panther_engine.hmmscore.data import SERVICE, VERSION
from panther_engine.hmmscore.library import ENCODING, LibraryFormatError, lines_of, path_of
from panther_engine.hmmscore.scoring import (
    NO_NAME,
    QUERY_NAME,
    HmmHit,
    HmmscoreError,
    HmmscoreInput,
    HmmscoreResult,
    alignment,
    pick,
    score,
)

__all__ = ["Case", "expected_result", "read_cases"]

GOLDEN = Path("tests/golden/hmmscore/parity")
CASES = "cases.json"
INPUTS = "inputs"
GOLDEN_SETS = ("sample", "full")
ARM64 = "sample-arm64"
CGI_XML = "cgi.xml"
BEST = "best.tsv"
HMMSEARCH = "hmmsearch"
REFERENCE = Path("/opt/hmmscore-reference")
HMMER = Path("/opt/hmmer-3.1b2/bin")
CGI = "scoreAlignXml.cgi"
SCRIPT = "pantherScore.pl"
SCRIPTS = (CGI, SCRIPT, "lib")
# What the CGI prints first (66), before the XML.
CGI_HEADER = b"Content-type:text/html\n\n"
NO_HIT_XML = "<scores>\n</scores>\n"
CGI_HIT = re.compile(
    r"<scores>\n  <id>(.*)</id>\n  <eval>(.*)</eval>\n  <align>\n(.*)  </align>\n</scores>\n",
    re.DOTALL,
)
# `printRes`'s line: sequence ID, HMM ID, name, E-value, score and range (275).
BEST_FIELDS = 6
# A Perl run on the full library, titin's 10,000 residues included, takes minutes.
TIMEOUT = 3600.0
# The self-check: the example on the sample and the full library (the survey, and
# tests/golden/hmmscore/sample-hmmscan/amd64/apoe.domtblout).
SELF_CHECK_CASE = "apoe"
SELF_CHECK_HIT = ("PTHR18976:SF2", "439.0")


class ParityError(Exception):
    """The reference can't run, or a golden folder can't be read."""


@dataclass(frozen=True)
class Case:
    name: str
    why: str
    posted: str | None = None
    """The text the CGI is posted, when it isn't the engine's sequence."""

    def sequence(self, golden: Path) -> str:
        """The engine's sequence, as the API sends it."""
        return (golden / INPUTS / f"{self.name}.txt").read_text(encoding="ascii")

    def posted_text(self, golden: Path) -> str:
        return self.sequence(golden) if self.posted is None else self.posted


NAME = re.compile(r"[a-z0-9][a-z0-9-]*")


def read_cases(golden: Path) -> tuple[Case, ...]:
    """The golden folder's cases, in order."""
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
        try:
            if not all(isinstance(value, str) for value in fields.values()):
                raise TypeError("a field isn't a string")
            case = Case(**fields)  # pyright: ignore[reportArgumentType]
        except TypeError as error:
            raise ParityError(f"not a case in {golden / CASES}: {item!r}") from error
        if not NAME.fullmatch(case.name):
            raise ParityError(f"not a case name in {golden / CASES}: {case.name!r}")
        cases.append(case)
    names = [case.name for case in cases]
    if len(set(names)) != len(names):
        raise ParityError(f"{golden / CASES} repeats a case name")
    return tuple(cases)


def selected(cases: Sequence[Case], names: Iterable[str] | None) -> list[Case]:
    """The cases named, in the golden set's order, or every case for None."""
    if names is None:
        return list(cases)
    wanted = list(names)
    unknown = [name for name in wanted if name not in {case.name for case in cases}]
    if unknown:
        raise ParityError(f"no such case: {', '.join(unknown)}")
    return [case for case in cases if case.name in wanted]


# The expected result and the cross-checks


def report_name(panther_id: str) -> str:
    """The file of a PANTHER ID's `hmmsearch` report: `PTHR18976.SF2.out`, since Windows can't
    hold `:` in a file name."""
    return f"{panther_id.replace(':', '.')}.out"


@dataclass(frozen=True)
class BestLine:
    panther_id: str
    name: str
    evalue: str
    score: str


def read_best(folder: Path) -> list[BestLine]:
    """`best.tsv`'s lines. Each is split on tabs and chomped, as the CGI read it (122 to 123)."""
    path = folder / BEST
    if not path.is_file():
        raise ParityError(f"no reference outputs: no {path}")
    lines: list[BestLine] = []
    for number, line in enumerate(lines_of(path.read_bytes()), 1):
        fields = line.removesuffix("\n").split("\t")
        if len(fields) != BEST_FIELDS:
            raise ParityError(f"{path}, line {number}: not {BEST_FIELDS} fields: {line!r}")
        lines.append(BestLine(fields[1], fields[2], fields[3], fields[4]))
    return lines


def read_report(folder: Path, panther_id: str) -> str:
    path = folder / HMMSEARCH / report_name(panther_id)
    if not path.is_file():
        raise ParityError(f"no hmmsearch report for {panther_id}: no {path}")
    try:
        return alignment(path.read_bytes())
    except HmmscoreError as error:
        raise ParityError(f"{path}: {error}") from error


def expected(folder: Path) -> HmmscoreResult:
    """A case's expected result from the reference's files in `folder`: no hit for an empty
    `best.tsv`; otherwise divergence 13's pick among its IDs, with that line's name, E-value and
    score, and the alignment from that ID's report. `pantherScore.pl` printed an empty name for
    an ID `names.tab` lacks, which the port calls "No name"."""
    lines = read_best(folder)
    if not lines:
        return HmmscoreResult(None)
    if len({(line.evalue, line.score) for line in lines}) != 1:
        raise ParityError(f"{folder / BEST}: the tied lines' E-value and score differ")
    chosen = pick(line.panther_id for line in lines)
    line = next(line for line in lines if line.panther_id == chosen)
    aligned = read_report(folder, chosen)
    return HmmscoreResult(HmmHit(chosen, line.name or NO_NAME, line.evalue, line.score, aligned))


def escape(text: str) -> str:
    """The CGI's escaping of the alignment (152 to 153)."""
    return text.replace(">", "&gt;").replace("<", "&lt;")


def cross_check(name: str, folder: Path) -> list[str]:
    """Each way `cgi.xml` disagrees with `best.tsv` and the reports. With no line, it must be an
    empty `<scores>`. Otherwise its `<id>` and `<eval>` must be one of `best.tsv`'s tied lines,
    in hash order the CGI's first, and its `<align>`, unescaped, that ID's alignment."""
    try:
        lines = read_best(folder)
        cgi = (folder / CGI_XML).read_bytes().decode(ENCODING)
    except (ParityError, OSError) as error:
        return [f"{name}: {error}"]
    if not lines:
        if cgi != NO_HIT_XML:
            return [f"{name}: best.tsv is empty, but cgi.xml isn't an empty <scores>"]
        return []
    match = CGI_HIT.fullmatch(cgi)
    tied = {(line.panther_id, line.evalue) for line in lines}
    if match is None or (match[1], match[2]) not in tied:
        shown = "no hit" if match is None else f"{match[1]} at {match[2]}"
        return [f"{name}: cgi.xml's {shown} isn't among best.tsv's tied lines"]
    try:
        aligned = read_report(folder, match[1])
    except ParityError as error:
        return [f"{name}: {error}"]
    if match[3] != escape(aligned):
        return [f"{name}: cgi.xml's <align> doesn't match {report_name(match[1])}"]
    return []


def architecture() -> str:
    """`amd64` or `arm64`, as Docker names them, or the machine's own name."""
    machine = platform.machine().lower()
    return {"x86_64": "amd64", "aarch64": "arm64"}.get(machine, machine)


def result_json(result: HmmscoreResult) -> str:
    return json.dumps(dataclasses.asdict(result), indent=2) + "\n"


def write_result(path: Path, result: HmmscoreResult) -> None:
    path.write_text(result_json(result), encoding="utf-8")


def read_result(path: Path) -> HmmscoreResult:
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
        hit = cast(dict[str, object], raw)["hit"]
        if hit is None:
            return HmmscoreResult(None)
        return HmmscoreResult(HmmHit(**cast(dict[str, str], hit)))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ParityError(f"can't read {path}: {error}") from error


def expected_result(case: Case, golden: Path, goldens: str) -> HmmscoreResult:
    """The case's expected result: on arm64, the sample's arm64 copy if it has one, otherwise
    what the reference's files give."""
    arm64 = golden / ARM64 / f"{case.name}.json"
    if goldens == "sample" and architecture() == "arm64" and arm64.is_file():
        return read_result(arm64)
    return expected(golden / goldens / case.name)


# The check


@dataclass(frozen=True)
class CaseCheck:
    name: str
    seconds: float
    differences: tuple[str, ...]


def check_case(case: Case, golden: Path, goldens: str, data_dir: Path | str | None) -> CaseCheck:
    """Score the case's sequence and compare with its expected result, and cross-check its
    `cgi.xml`. `data_dir` is the data folder, holding `hmmscore/19/`."""
    try:
        want = expected_result(case, golden, goldens)
    except ParityError as error:
        return CaseCheck(case.name, 0.0, (f"{case.name}: {error}",))
    started = time.monotonic()
    try:
        got = score(HmmscoreInput(case.sequence(golden)), data_dir=data_dir)
    except (
        ValueError,
        InputError,
        HmmscoreError,
        MissingDataError,
        LibraryFormatError,
        DataFolderError,
        OSError,
    ) as error:
        seconds = time.monotonic() - started
        return CaseCheck(
            case.name, seconds, (f"{case.name}: the port raised {type(error).__name__}: {error}",)
        )
    seconds = time.monotonic() - started
    differences = compare(case.name, want, got)
    differences += cross_check(case.name, golden / goldens / case.name)
    return CaseCheck(case.name, seconds, tuple(differences))


def compare(name: str, want: HmmscoreResult, got: HmmscoreResult) -> list[str]:
    if want.hit is None or got.hit is None:
        if want.hit == got.hit:
            return []
        reference = "no hit" if want.hit is None else want.hit.panther_id
        port = "no hit" if got.hit is None else got.hit.panther_id
        return [f"{name}: the reference has {reference}, the port {port}"]
    differences: list[str] = []
    for field in ("panther_id", "name", "evalue", "score"):
        wanted, found = getattr(want.hit, field), getattr(got.hit, field)
        if wanted != found:
            differences.append(
                f"{name}: the reference's {field} is {wanted!r}, the port's {found!r}"
            )
    if want.hit.alignment != got.hit.alignment:
        differences.append(f"{name}: {first_difference(want.hit.alignment, got.hit.alignment)}")
    return differences


def first_difference(want: str, got: str) -> str:
    wanted, found = want.splitlines(), got.splitlines()
    for number, (line, other) in enumerate(zip(wanted, found, strict=False), 1):
        if line != other:
            return (
                f"the alignments differ at line {number}: the reference has {line!r}, "
                f"the port {other!r}"
            )
    return f"the reference's alignment has {len(wanted)} lines, the port's {len(found)}"


def run_check(
    golden: Path, goldens: str, data_dir: Path | str | None, names: Iterable[str] | None = None
) -> list[CaseCheck]:
    """Check every case, or those named, one at a time."""
    if goldens not in GOLDEN_SETS:
        raise ParityError(f"not a golden set: {goldens!r}")
    return [
        check_case(case, golden, goldens, data_dir) for case in selected(read_cases(golden), names)
    ]


# The reference


def config_yaml(*, data: Path, library: Path, tmp: Path, hmmer: Path) -> str:
    """The CGI's `config.yaml` (18 to 28): the data folder for the model files, the library
    `pantherScore.pl` reads `globals/binHmm` from, its temporary folder and HMMER's. Each value is
    a double-quoted string, as JSON writes one, which YAML reads as written."""
    values = {
        "library_directory": data,
        "binHmm_library_directory": library,
        "tmp_directory": tmp,
        "hmmer_bin_directory": hmmer,
    }
    return "".join(f"{key}: {json.dumps(str(value))}\n" for key, value in values.items())


def cgi_body(posted: str) -> str:
    """The form the CGI is posted: the sequence alone, as `sequence=<text>`. The cases hold no
    character the form's decoding changes (`HMMSCORE-10`)."""
    return f"sequence={posted}"


def cgi_environment(body: str) -> dict[str, str]:
    """A POST of `body`, which the CGI reads `CONTENT_LENGTH` bytes of (76 to 77)."""
    return {"REQUEST_METHOD": "POST", "CONTENT_LENGTH": str(len(body.encode("ascii")))}


def score_arguments(*, library: Path, query: Path, out: Path, hmmer: Path) -> list[str]:
    """`pantherScore.pl` as the CGI runs it (111), with `-n` for the names."""
    return [
        SCRIPT,
        "-l",
        str(library),
        "-D",
        "B",
        "-n",
        "-i",
        str(query),
        "-o",
        str(out),
        "-H",
        str(hmmer),
    ]


def self_check_problem(best: str) -> str | None:
    """What's wrong with the example's `best.tsv`, or None: it must be one line,
    `PTHR18976:SF2` at 439.0 bits."""
    lines = best.splitlines()
    if len(lines) != 1:
        return f"the example gave {len(lines)} best lines, not 1"
    fields = lines[0].split("\t")
    if len(fields) != BEST_FIELDS or (fields[1], fields[4]) != SELF_CHECK_HIT:
        return f"the example gave {lines[0]!r}, not {SELF_CHECK_HIT[0]} at {SELF_CHECK_HIT[1]} bits"
    return None


@dataclass(frozen=True)
class Reference:
    """The CGI and `pantherScore.pl`, run with `perl`, and HMMER 3.1b2."""

    perl: Path
    scripts: Path = REFERENCE
    hmmer: Path = HMMER

    @classmethod
    def find(cls, scripts: Path = REFERENCE, hmmer: Path = HMMER) -> "Reference":
        perl = shutil.which("perl")
        if perl is None:
            raise ParityError("no perl on PATH: run this in the hmmscore-reference image")
        for path in (*(scripts / name for name in SCRIPTS), hmmer / "hmmscan"):
            if not path.exists():
                raise ParityError(f"no {path}: run this in the hmmscore-reference image")
        return cls(Path(perl).absolute(), scripts, hmmer)

    def run(
        self,
        program: Path,
        args: list[str],
        *,
        what: str,
        input: str | None = None,
        cwd: Path | None = None,
        stdout: Path | None = None,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        """Run one program of the reference, and raise ParityError if it fails."""
        try:
            result = run_tool(
                program,
                args,
                timeout=TIMEOUT,
                input=input,
                cwd=cwd,
                stdout=stdout,
                environment=environment,
            )
        except subprocess.TimeoutExpired as error:
            raise ParityError(f"{what} ran past {TIMEOUT:.0f} s") from error
        except OSError as error:
            raise ParityError(f"can't run {what}: {error}") from error
        if result.returncode != 0:
            detail = " / ".join(result.stderr.strip().splitlines()[-5:])
            raise ParityError(f"{what} exited with status {result.returncode}: {detail}")

    def press(self, data: Path, folder: Path) -> Path:
        """3.1b2's presses of the data folder's models, as the survey's task 10.1 made them:
        `hmmconvert` turns `globals/binHmm.h3m` back to text, and `hmmpress` presses it into
        `folder/globals/`. `names.tab` and `books/` are linked beside them, since
        `FamLibBuilder::exists` needs both folders. Returns `folder`, the library to read."""
        globals_folder = folder / "globals"
        globals_folder.mkdir(parents=True)
        flat = globals_folder / "binHmm"
        self.run(
            self.hmmer / "hmmconvert",
            [str(data / "globals" / "binHmm.h3m")],
            what="hmmconvert",
            stdout=flat,
        )
        self.run(self.hmmer / "hmmpress", [str(flat)], what="hmmpress", stdout=Path(os.devnull))
        flat.unlink()
        (globals_folder / "names.tab").symlink_to(data / "globals" / "names.tab")
        (folder / "books").symlink_to(data / "books")
        return folder

    def prepare(self, work: Path, *, data: Path, library: Path) -> None:
        """A case's working folder: the CGI's `config.yaml`, its temporary folder, and links to
        the scripts, which the CGI finds by relative path (`./pantherScore.pl`, `lib`)."""
        (work / "tmp").mkdir(parents=True)
        for name in SCRIPTS:
            (work / name).symlink_to(self.scripts / name)
        text = config_yaml(data=data, library=library, tmp=work / "tmp", hmmer=self.hmmer)
        (work / "config.yaml").write_text(text, encoding="utf-8")

    def best(self, work: Path, posted: str, *, library: Path, out: Path) -> None:
        """`pantherScore.pl -D B -n` on the posted text, as the CGI wrote it to its FASTA file."""
        query = work / "query.fasta"
        query.write_bytes(f">{QUERY_NAME}\n{posted}".encode("ascii"))
        args = score_arguments(library=library, query=query, out=out, hmmer=self.hmmer)
        self.run(self.perl, args, what=SCRIPT, cwd=work)

    def case(
        self, case: Case, golden: Path, *, data: Path, library: Path, work: Path, out: Path
    ) -> None:
        """Run one case, writing `cgi.xml`, `best.tsv` and `hmmsearch/` into `out`."""
        posted = case.posted_text(golden)
        self.prepare(work, data=data, library=library)
        body = cgi_body(posted)
        raw = work / "cgi.out"
        self.run(
            self.perl,
            [CGI],
            what=CGI,
            input=body,
            cwd=work,
            stdout=raw,
            environment=cgi_environment(body),
        )
        printed = raw.read_bytes()
        if not printed.startswith(CGI_HEADER):
            raise ParityError(f"{CGI} printed no Content-type header: {printed[:80]!r}")
        out.mkdir(parents=True)
        (out / CGI_XML).write_bytes(printed.removeprefix(CGI_HEADER))
        self.best(work, posted, library=library, out=out / BEST)
        (out / HMMSEARCH).mkdir()
        for panther_id in dict.fromkeys(line.panther_id for line in read_best(out)):
            model = data / path_of(panther_id)
            if not model.is_file():
                raise ParityError(f"no model file for {panther_id}: {model}")
            # As the CGI runs it (140): no --cpu, and the report on standard output.
            self.run(
                self.hmmer / "hmmsearch",
                [str(model), "query.fasta"],
                what=f"hmmsearch of {panther_id}",
                cwd=work,
                stdout=out / HMMSEARCH / report_name(panther_id),
            )


def run_reference(
    reference: Reference,
    golden: Path,
    goldens: str,
    data_dir: Path | str | None,
    names: Iterable[str] | None = None,
) -> list[str]:
    """Run the self-check, then each case, or those named, one at a time, and return their names.

    For `sample`, 3.1b2 reads its own presses of the data sample; for `full`, the library's shipped
    pressed files, as production's did. Each case runs in a fresh folder, and its outputs replace
    `<goldens>/<case>/` only once it has run: one that fails leaves the case's goldens as they
    were.
    """
    if goldens not in GOLDEN_SETS:
        raise ParityError(f"not a golden set: {goldens!r}")
    every = read_cases(golden)
    cases = selected(every, names)
    example = next((case for case in every if case.name == SELF_CHECK_CASE), None)
    if example is None:
        raise ParityError(f"the self-check needs the case {SELF_CHECK_CASE!r} in {golden / CASES}")
    data = service_folder(SERVICE, VERSION, data_dir)
    if not (data / "globals" / "binHmm.h3m").is_file():
        raise ParityError(f"no hmmscore library in {data}: fetch the data sample or the library")
    for case in cases:
        if not (golden / INPUTS / f"{case.name}.txt").is_file():
            raise ParityError(f"case {case.name!r}: no {golden / INPUTS / f'{case.name}.txt'}")
    target = golden / goldens
    target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hmmscore-reference-") as scratch:
        root = Path(scratch)
        library_folder = reference.press(data, root / "presses") if goldens == "sample" else data
        check = root / "self-check"
        reference.prepare(check, data=data, library=library_folder)
        reference.best(
            check,
            example.sequence(golden),
            library=library_folder,
            out=check / BEST,
        )
        problem = self_check_problem((check / BEST).read_text(encoding=ENCODING))
        if problem is not None:
            raise ParityError(f"the self-check failed: {problem}")
        for case in cases:
            with tempfile.TemporaryDirectory(dir=target, prefix=f".{case.name}-") as staged:
                out = Path(staged) / case.name
                try:
                    reference.case(
                        case,
                        golden,
                        data=data,
                        library=library_folder,
                        work=root / case.name,
                        out=out,
                    )
                except ParityError as error:
                    raise ParityError(f"case {case.name!r}: {error}") from error
                replace(out, target / case.name)
    return [case.name for case in cases]


def replace(new: Path, old: Path) -> None:
    """Move the folder `new` to `old`, replacing it if it's there."""
    if old.exists():
        retired = old.with_name(f".{old.name}-replaced-{uuid.uuid4().hex}")
        os.replace(old, retired)
        os.replace(new, old)
        shutil.rmtree(retired)
    else:
        os.replace(new, old)
