"""`score()`: one protein against PANTHER's HMM library, as `scoreAlignXml.cgi` and the
`pantherScore.pl -D B` it ran did.

The interface is `add-hmmscore-job`'s decision 4, which the engine developer approved on #70:
frozen dataclasses, one protein per call, the sequence already normalised by the API. The steps
(port-hmmscore, design.md, decision 2), each in a folder of the call's own, never the shared
`/tmp/temp.domtblout` (`HMMSCORE-7`):

1. the query file, `>sequence` and the sequence, as the CGI wrote it (93 to 105);
2. `hmmscan --domtblout` against `globals/binHmm` (`pantherScore.pl` 372 to 403);
3. `getBestHit`'s best hit and its 1e-3 cutoff (316 to 340), with ties resolved by divergence 13;
4. `hmmsearch` of the model file at the hit's ID, and the report's lines the CGI printed, without
   its `&gt;` and `&lt;` (`scoreAlignXml.cgi` 133 to 158);
5. the hit's name from `globals/names.tab`, which the CGI never gave (`HMMSCORE-2`).

Line numbers are `pantherScoring`'s at `89ea0ae`. Files HMMER writes are read as bytes, as Latin-1,
and split at line feeds only, as Perl reads them.
"""

import re
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from panther_engine.core import hmmer
from panther_engine.core.data import MissingDataError, service_folder
from panther_engine.core.errors import InputError
from panther_engine.hmmscore import legacy, library
from panther_engine.hmmscore.data import SERVICE, VERSION

DATA_VERSION = VERSION
# pantherScore.pl's $distantHmmCutoff (51), which -D B applies to the best hit (147 to 148, 338).
CUTOFF = 1e-3
# The name scoreAlignXml.cgi gave a sequence posted without a header (93 to 95). hmmsearch's
# report names it (`>> sequence`), so the alignment depends on it.
QUERY_NAME = "sequence"
BINHMM = "globals/binHmm"
NAMES = "globals/names.tab"
PRESSED = tuple(f"{BINHMM}.{suffix}" for suffix in ("h3f", "h3i", "h3m", "h3p"))
BOOKS = "books"
NO_NAME = "No name"
TIME_LIMIT_MESSAGE = "The search took longer than this service allows. Try a shorter sequence."
# What the API sends: upper-case letters, and the `.`, `_`, `~` and `*` that HMMER 3.4 reads as
# 3.1b2 did (divergence 12), with at least one letter.
SEQUENCE = re.compile(r"[A-Z._~*]+")
LETTER = re.compile(r"[A-Z]")
# A `--domtblout` line has 23 columns, the last the target's description, which may hold spaces.
# pantherScore.pl splits it on /\s+/, and reads the target's name, the full-sequence E-value and
# the full-sequence score (385). Perl's \s on bytes: Python's would also match \x85 and \xa0 in
# Latin-1 text.
WHITESPACE = re.compile(r"[ \t\n\r\f\v]+")
DOMAIN_COLUMNS = 23
TARGET, EVALUE, SCORE = 0, 6, 7
# The CGI printed the report from the line after the first, to the line before the second
# (scoreAlignXml.cgi 145 to 151).
ALIGNMENT_START = "Domain annotation for each sequence"
ALIGNMENT_END = "Internal pipeline statistics summary:"
# Divergence 13: a PANTHER ID's family number, and subfamily number, if it has one.
PANTHER_ID = re.compile(r"PTHR([0-9]+)(?::SF([0-9]+))?")
# How much of a failing tool's standard error goes into the error, for the log.
STDERR_LINES = 3


class HmmscoreError(Exception):
    """Scoring failed in a way that isn't the input's fault: a tool that exits with an error,
    can't be run or writes nothing the port can read, or a missing model file.

    Never an `InputError`: the job fails with the generic `500`.
    """


@dataclass(frozen=True)
class HmmscoreInput:
    """One protein, as the API normalised it: no header or whitespace, upper-cased, and holding
    only letters, `.`, `_`, `~` and `*`."""

    sequence: str


@dataclass(frozen=True)
class HmmHit:
    """The best hit. `evalue` and `score` are the full-sequence E-value and bit score, as
    `hmmscan` printed them. `name` is `names.tab`'s, or "No name" if it has none for the ID.
    `alignment` is the report's text the CGI printed, unescaped."""

    panther_id: str
    name: str
    evalue: str
    score: str
    alignment: str


@dataclass(frozen=True)
class HmmscoreResult:
    """The best hit, or None: no model reported, or the best one's E-value over 1e-3."""

    hit: HmmHit | None


def score(
    request: HmmscoreInput,
    *,
    data_dir: Path | str | None = None,
    cpu: int = 0,
    timeout: float | None = None,
) -> HmmscoreResult:
    """Score one protein against the HMM library.

    The data folder is `PANTHER_DATA_DIR`, or `data_dir` in tests. `cpu` goes to both tools as
    `--cpu`. `timeout`, in seconds, covers the whole search, from this call: `hmmscan` gets what's
    left of it, then `hmmsearch` what's left after that. None sets no limit.

    Raises ValueError, before anything runs, for a sequence the API never sends. Then raises
    MissingDataError if the data folder lacks the library (`check_data`). Raises InputError, with
    TIME_LIMIT_MESSAGE, past the time limit, once the running tool is killed. Raises HmmscoreError
    when a tool fails or the hit's model file is missing, and LibraryFormatError for a broken
    `names.tab`. The search's folder is removed however scoring ends.
    """
    started = time.monotonic()
    check_sequence(request.sequence)
    check_data(data_dir)
    data = service_folder(SERVICE, VERSION, data_dir)
    deadline = None if timeout is None else started + timeout
    with tempfile.TemporaryDirectory(prefix="hmmscore-") as work:
        folder = Path(work)
        query = folder / "query.fasta"
        # As the CGI wrote it: the header, then the sequence, with no final line feed.
        query.write_bytes(f">{QUERY_NAME}\n{request.sequence}".encode("ascii"))
        table = folder / "hits.domtblout"
        finish(
            "hmmscan",
            lambda left: hmmer.hmmscan(
                data / BINHMM, query, table=table, cpu=cpu, timeout=left, cwd=folder
            ),
            deadline,
        )
        if not table.is_file():
            raise HmmscoreError("hmmscan exited with status 0, but wrote no table")
        best = best_hit(read_table(table.read_bytes()))
        if best is None:
            return HmmscoreResult(None)
        panther_id = pick(best.ids)
        model = data / library.path_of(panther_id)
        if not model.is_file():
            raise HmmscoreError(f"no model file for the best hit, {panther_id}: {model}")
        report = folder / "hmmsearch.out"
        finish(
            "hmmsearch",
            lambda left: hmmer.hmmsearch(
                model, query, report=report, cpu=cpu, timeout=left, cwd=folder
            ),
            deadline,
        )
        aligned = alignment(report.read_bytes())
    name = name_of(data / NAMES, panther_id)
    return HmmscoreResult(HmmHit(panther_id, name, best.evalue, best.score, aligned))


def check_sequence(sequence: str) -> None:
    """Raise ValueError for a sequence the API never sends."""
    if not SEQUENCE.fullmatch(sequence):
        raise ValueError(
            "the sequence must be upper-case letters, '.', '_', '~' and '*', and not empty"
        )
    if not LETTER.search(sequence):
        raise ValueError("the sequence must hold a letter")


def check_data(data_dir: Path | str | None = None) -> None:
    """Check that the hmmscore data folder holds what every search needs: `globals/names.tab`,
    the four pressed files of `globals/binHmm` and the `books/` folder. Raises MissingDataError,
    naming the folder and each missing part, if it doesn't.

    It's cheap: a few `stat`s, and no file is read. `hmmscore data verify` checks the contents.
    """
    data = service_folder(SERVICE, VERSION, data_dir)
    missing = [name for name in (NAMES, *PRESSED) if not (data / name).is_file()]
    if not (data / BOOKS).is_dir():
        missing.append(f"{BOOKS}/")
    if missing:
        raise MissingDataError(f"the hmmscore data folder {data} lacks: {', '.join(missing)}")


def finish(
    name: str,
    run: Callable[[float | None], subprocess.CompletedProcess[str]],
    deadline: float | None,
) -> None:
    """Run one tool with what's left of the time limit, and check how it ended."""
    try:
        result = run(remaining(deadline))
    except subprocess.TimeoutExpired as error:
        raise InputError(TIME_LIMIT_MESSAGE) from error
    except OSError as error:
        raise HmmscoreError(f"can't run {name}: {error}") from error
    if result.returncode != 0:
        detail = " / ".join(result.stderr.strip().splitlines()[-STDERR_LINES:])
        raise HmmscoreError(f"{name} exited with status {result.returncode}: {detail}")


def remaining(deadline: float | None) -> float | None:
    """The seconds left before `deadline`, or None for no limit. Raises the input error when none
    are left."""
    if deadline is None:
        return None
    left = deadline - time.monotonic()
    if left <= 0:
        raise InputError(TIME_LIMIT_MESSAGE)
    return left


# The table and the best hit


@dataclass(frozen=True)
class Row:
    """A domain line of `hmmscan`'s table: the model's name and PANTHER ID, and its full-sequence
    E-value and score, as printed."""

    model: str
    panther_id: str
    evalue: str
    score: str


def read_table(content: bytes) -> list[Row]:
    """The domain lines of a `--domtblout` table. `#` lines are skipped (384). Each line is split
    on whitespace, as `split(/\\s+/)` splits it (385), and its model's ID read by `legacy.model_id`
    (387 to 389). Raises HmmscoreError for a line that isn't a domain line, which `hmmscan` never
    writes."""
    rows: list[Row] = []
    for number, line in enumerate(library.lines_of(content), 1):
        if line.startswith("#"):
            continue
        fields = WHITESPACE.split(line)
        while fields and not fields[-1]:
            fields.pop()
        try:
            if len(fields) < DOMAIN_COLUMNS or not fields[TARGET]:
                raise ValueError("too few columns")
            for column in (EVALUE, SCORE):
                float(fields[column])
        except ValueError as error:
            raise HmmscoreError(
                f"hmmscan's table, line {number}: not a domain line ({error}): {line!r}"
            ) from error
        target = fields[TARGET]
        rows.append(Row(target, legacy.model_id(target), fields[EVALUE], fields[SCORE]))
    return rows


@dataclass(frozen=True)
class Best:
    """`getBestHit`'s answer: every PANTHER ID with the best score and E-value, as printed."""

    ids: frozenset[str]
    evalue: str
    score: str


def best_hit(rows: Sequence[Row]) -> Best | None:
    """`getBestHit` (316 to 340): the highest score, then, for that score, the smallest E-value,
    both compared as numbers, then every ID with both, as printed. None for no rows, or when that
    E-value is over the cutoff (`HMMSCORE-5`): exactly 1e-3 is kept, since the Perl tests `>`."""
    if not rows:
        return None
    best_score = max((row.score for row in rows), key=float)
    best_evalue = min((row.evalue for row in rows if row.score == best_score), key=float)
    if float(best_evalue) > CUTOFF:
        return None
    ids = frozenset(
        row.panther_id for row in rows if (row.score, row.evalue) == (best_score, best_evalue)
    )
    return Best(ids, best_evalue, best_score)


def pick(ids: Iterable[str]) -> str:
    """One of the tied PANTHER IDs, by divergence 13: a family's ID is dropped when one of its own
    subfamilies is among them, then the lowest is taken, by family number, then subfamily number,
    with a family's own ID as subfamily 0. An ID of another shape, which PANTHER 19 has none of,
    comes after them all, by its text."""
    tied = set(ids)
    with_subfamilies = {panther_id.partition(":")[0] for panther_id in tied if ":" in panther_id}
    kept = [panther_id for panther_id in tied if panther_id not in with_subfamilies]
    return min(kept, key=order)


def order(panther_id: str) -> tuple[int, int, int, str]:
    match = PANTHER_ID.fullmatch(panther_id)
    if match is None:
        return (1, 0, 0, panther_id)
    return (0, int(match[1]), int(match[2] or 0), panther_id)


# The alignment and the name


def alignment(report: bytes) -> str:
    """The lines of `hmmsearch`'s report the CGI printed (scoreAlignXml.cgi 143 to 156): after the
    first line starting "Domain annotation for each sequence", up to the first line starting
    "Internal pipeline statistics summary:", as they are. The CGI escaped `>` and `<`, and the
    site read them back. Raises HmmscoreError for a report with no such first line."""
    lines: list[str] = []
    started = False
    for line in library.lines_of(report):
        if line.startswith(ALIGNMENT_END):
            break
        if line.startswith(ALIGNMENT_START):
            started = True
            continue
        if started:
            lines.append(line)
    if not started:
        raise HmmscoreError(f"hmmsearch's report has no {ALIGNMENT_START!r} line")
    return "".join(lines)


def name_of(names: Path, panther_id: str) -> str:
    """`names.tab`'s name for the ID, read strictly, or "No name" when it has no line for the ID
    or an empty name. `pantherScore.pl -n` printed an empty name for both."""
    entry = library.read_names(library.lines_of(names.read_bytes()), str(names)).get(panther_id)
    return entry.name if entry is not None and entry.name else NO_NAME
