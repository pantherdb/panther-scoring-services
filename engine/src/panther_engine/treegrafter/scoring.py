"""`score()`: one protein grafted onto its best family's tree, as EBI's `treegrafter.sh search`
grafts it, and the rest of the interface the API calls: `check_data()`, `annotations()` and
`DATA_VERSION`.

The interface follows hmmscore's (adopt-treegrafter, design.md, decision 1): frozen dataclasses,
one protein per call, the sequence already normalised by the API, one deadline for the whole graft,
a data check that reads only names, and the PANTHER release of the library as a constant. The
steps are EBI's (decision 2), each in a folder of the call's own:

1. the query file, `>query` and the sequence, so EBI's output names it `query`;
2. `hmmsearch` with `treegrafter.sh`'s options against `famhmm/binHmm`, through `core`, with one
   thread (decision 6);
3. EBI's `parsehmmsearch`, `filter_best_domain` and `filter_evalue_cutoff` at 1e-8, as
   `treegrafter.py run -e 0.00000001` calls them, which leave at most the best family;
4. EBI's `generate_fasta_for_panthr`, the query's alignment to the family's columns;
5. the engine's check that the family can be placed (decision 4);
6. EPA-ng with EBI's arguments, through `core`, with what's left of the time limit;
7. EBI's `process_tree`, with the release read at the start, and the graft point from its entry.

EBI's `run` and `process_matches_epang` aren't called, since they run EPA-ng themselves; the
goldens prove these steps give their rows.
"""

import json
import logging
import re
import subprocess
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from panther_engine.core import epang, hmmer
from panther_engine.core.data import MissingDataError, data_root, service_folder
from panther_engine.treegrafter import data, ebi
from panther_engine.treegrafter.ebi import TreegrafterError

DATA_VERSION = data.VERSION
# The name the query is given, which EBI's output and EPA-ng's placements use.
QUERY = "query"
# treegrafter.sh's options, with one thread (design.md, decision 6).
SEARCH_OPTIONS = (
    "-Z",
    "65000000",
    "-E",
    "0.001",
    "--domE",
    "0.00000001",
    "--incdomE",
    "0.00000001",
    "--notextw",
)
# treegrafter.sh's `run -e 0.00000001`: a best family whose full-sequence E-value is over it is
# no hit.
CUTOFF = 0.00000001
THREADS = 1
TIME_LIMIT_MESSAGE = "The graft took longer than this service allows. Try a shorter sequence."
# What the engine takes: upper-case letters, `.`, `_` and `*`, with at least one letter. hmmscore's
# set without `~`, which EPA-ng aborts on (divergence 15).
SEQUENCE = re.compile(r"[A-Z._*]+")
LETTER = re.compile(r"[A-Z]")
# How much of a failing tool's standard error goes into the error, for the log.
STDERR_LINES = 3
# EBI's `-` for no value.
NONE = "-"
# A tree's leaves are the labels after `(` or `,`; a FASTA row's name follows `>`.
LEAF = re.compile(r"[(,]([^(),:;\s\[]+)")
ROW = re.compile(r"^>(\S+)", re.MULTILINE)

logger = logging.getLogger(__name__)


class TimeLimitError(Exception):
    """The graft ran past its time limit, and the running tool was killed. Raised with one
    argument, the message, which is for the CLI and the log: the API writes its own.

    Never an `InputError`, as hmmscore's isn't: a protein reaches its limit when the server is
    busy, so the input isn't at fault. It keeps its type and message when it's passed from a
    worker process to the API's.
    """


@dataclass(frozen=True)
class TreegrafterInput:
    """One protein, as the API normalised it: no header or whitespace, upper-cased, and holding
    only letters, `.`, `_` and `*`."""

    sequence: str


@dataclass(frozen=True)
class TreegrafterHit:
    """The best family's graft, with EBI's row's fields.

    `panther_id` is the graft node's subfamily, else the family. `node_id` is the graft node, such
    as AN163, `graft_point` its public ID, such as PTN002498710, from the release's entry, and
    `go_terms` and `protein_class` its annotations. All four are empty for a family that can't be
    placed. `score` and `evalue` are the full sequence's, and `domain_score` and `domain_evalue`
    the best domain's, as EBI's command line writes them. The coordinates are the best domain's.
    """

    panther_id: str
    node_id: str | None
    graft_point: str | None
    go_terms: tuple[str, ...]
    protein_class: str | None
    score: str
    evalue: str
    domain_score: str
    domain_evalue: str
    hmm_from: int
    hmm_to: int
    ali_from: int
    ali_to: int
    env_from: int
    env_to: int


@dataclass(frozen=True)
class TreegrafterResult:
    """The best family's graft, or None: no family reported, or the best one's full-sequence
    E-value over 1e-8. `annotations` is the date of the release the graft read."""

    hit: TreegrafterHit | None
    annotations: str


@dataclass(frozen=True)
class AnnotationRelease:
    """The PAINT annotation release grafting reads: its date, and the GO release its README
    states."""

    date: str
    go_release: str


def score(
    request: TreegrafterInput,
    *,
    data_dir: Path | str | None = None,
    timeout: float | None = None,
) -> TreegrafterResult:
    """Graft one protein onto its best family's tree.

    The data folder is `PANTHER_DATA_DIR`, or `data_dir` in tests. `timeout`, in seconds, covers the
    whole graft, from this call: `hmmsearch` gets what's left of it, then EPA-ng what's left after
    that, and it's checked after each of EBI's steps, which can't be stopped. None sets no limit.

    Raises ValueError, before anything runs, for a sequence the API never sends. Then raises
    MissingDataError if the data folder lacks the library or an active release (`check_data`).
    Raises TimeLimitError, with TIME_LIMIT_MESSAGE, past the time limit, once the running tool is
    killed. Raises TreegrafterError when a tool fails or writes nothing, or EBI's code exits or
    raises. The graft's folder is removed however grafting ends.
    """
    started = time.monotonic()
    check_sequence(request.sequence)
    check_data(data_dir)
    library = service_folder(data.SERVICE, data.VERSION, data_dir)
    # Read once: the graft reads this release throughout, whatever becomes active meanwhile.
    date = active(data_root(data_dir))
    if date is None:
        raise MissingDataError(f"no annotation release is active in {library}")
    release = library / data.ANNOTATIONS / date
    deadline = None if timeout is None else started + timeout
    with tempfile.TemporaryDirectory(prefix="treegrafter-") as work:
        folder = Path(work)
        query = folder / "query.fasta"
        query.write_text(f">{QUERY}\n{request.sequence}\n", encoding="ascii")
        report = folder / "hmmsearch.out"
        finish(
            "hmmsearch",
            lambda left: hmmer.hmmsearch(
                library / data.BINHMM,
                query,
                report=report,
                cpu=0,
                timeout=left,
                cwd=folder,
                options=SEARCH_OPTIONS,
            ),
            deadline,
        )
        if not report.is_file():
            raise TreegrafterError("hmmsearch exited with status 0, but wrote no report")
        matches = ebi.parse_hmmsearch(report)
        matches = ebi.filter_evalue_cutoff(ebi.filter_best_domain(matches), CUTOFF)
        remaining(deadline)
        best = best_family(matches)
        if best is None:
            return TreegrafterResult(None, date)
        family, queries = best
        alignment = ebi.generate_fasta_for_panthr(family, queries, library, folder)
        if alignment is None:
            return TreegrafterResult(None, date)
        missing = missing_leaves(library, family)
        if missing:
            logger.warning(
                "treegrafter: %s can't be placed: its tree has leaves its alignment lacks, %s; "
                "returning the family alone, as EBI's code does",
                family,
                ", ".join(missing),
            )
            return TreegrafterResult(family_alone(family, queries[QUERY]), date)
        placements = folder / f"{family}_epang"
        placements.mkdir()
        msf = library / data.TREE_MSF
        finish(
            "EPA-ng",
            lambda left: epang.place(
                msf / f"{family}.bifurcate.newick",
                msf / f"{family}.AN.fasta",
                alignment,
                placements,
                threads=THREADS,
                timeout=left,
                cwd=folder,
            ),
            deadline,
        )
        jplace = placements / "epa_result.jplace"
        if not jplace.is_file():
            raise TreegrafterError("EPA-ng exited with status 0, but wrote no epa_result.jplace")
        rows = ebi.process_tree(family, jplace, queries, library, release)
        remaining(deadline)
    row = the_row(rows)
    node = None if row[12] == NONE else row[12]
    return TreegrafterResult(hit_from_row(row, graft_point(release, family, node)), date)


def check_sequence(sequence: str) -> None:
    """Raise ValueError for a sequence the API never sends."""
    if not SEQUENCE.fullmatch(sequence):
        raise ValueError("the sequence must be upper-case letters, '.', '_' and '*', and not empty")
    if not LETTER.search(sequence):
        raise ValueError("the sequence must hold a letter")


def finish(
    name: str,
    run: Callable[[float | None], subprocess.CompletedProcess[str]],
    deadline: float | None,
) -> None:
    """Run one tool with what's left of the time limit, and check how it ended."""
    try:
        result = run(remaining(deadline))
    except subprocess.TimeoutExpired as error:
        raise TimeLimitError(TIME_LIMIT_MESSAGE) from error
    except OSError as error:
        raise TreegrafterError(f"can't run {name}: {error}") from error
    if result.returncode != 0:
        detail = " / ".join(result.stderr.strip().splitlines()[-STDERR_LINES:])
        raise TreegrafterError(f"{name} exited with status {result.returncode}: {detail}")


def remaining(deadline: float | None) -> float | None:
    """The seconds left before `deadline`, or None for no limit. Raises TimeLimitError when none
    are left."""
    if deadline is None:
        return None
    left = deadline - time.monotonic()
    if left <= 0:
        raise TimeLimitError(TIME_LIMIT_MESSAGE)
    return left


def best_family(matches: ebi.Matches) -> tuple[str, ebi.FamilyMatches] | None:
    """The family EBI's filters left the query in, if any. `parsehmmsearch` keeps each query's
    highest full-sequence score only, the first family's on a tie, and the cutoff leaves that
    family empty when its E-value is over it."""
    found = [(family, queries) for family, queries in matches.items() if QUERY in queries]
    if len(found) > 1:
        raise TreegrafterError(f"EBI's parser kept the query in {len(found)} families")
    return found[0] if found else None


def missing_leaves(library: Path, family: str) -> list[str]:
    """The leaves of the family's bifurcating tree that its alignment has no row for: EPA-ng
    refuses such a tree (design.md, decision 4)."""
    msf = library / data.TREE_MSF
    leaves = LEAF.findall((msf / f"{family}.bifurcate.newick").read_text(encoding="ascii"))
    rows = set(ROW.findall((msf / f"{family}.AN.fasta").read_text(encoding="ascii")))
    return [leaf for leaf in leaves if leaf not in rows]


def family_alone(family: str, alignment: ebi.Alignment) -> TreegrafterHit:
    """EBI's row for a family it doesn't place (treegrafter.py 39 to 57), as a hit."""
    fields = ("score", "evalue", "domscore", "domevalue", "hmmstart", "hmmend")
    fields += ("alifrom", "alito", "envfrom", "envto")
    row = [QUERY, family, *(alignment[field][0] for field in fields), NONE, NONE, NONE]
    return hit_from_row(row, None)


def the_row(rows: Sequence[Sequence[str]]) -> Sequence[str]:
    found = [row for row in rows if row and row[0] == QUERY]
    if len(found) != 1:
        raise TreegrafterError(f"EBI's process_tree gave {len(found)} rows for the query, not 1")
    return found[0]


def graft_point(release: Path, family: str, node: str | None) -> str | None:
    """The node's public ID: the fourth value of its entry in the release, which EBI's
    `process_tree` reads and drops."""
    if node is None:
        return None
    entries = cast(
        dict[str, list[str | None]],
        json.loads((release / f"{family}.json").read_text(encoding="utf-8")),
    )
    entry = entries.get(node)
    if entry is None or len(entry) != 4:
        raise TreegrafterError(f"release {release.name} has no entry for {family}:{node}")
    return entry[3]


def hit_from_row(row: Sequence[str], point: str | None) -> TreegrafterHit:
    """A hit from EBI's `--print-go` row: the query, the PANTHER ID, the scores, the coordinates,
    the node, the GO terms and the protein class, with EBI's `-` as no value."""
    if len(row) != 15:
        raise TreegrafterError(f"EBI's row has {len(row)} fields, not 15: {list(row)!r}")

    def value(text: str) -> str | None:
        return None if text == NONE else text

    try:
        coordinates = [int(text) for text in row[6:12]]
    except ValueError as error:
        raise TreegrafterError(
            f"EBI's row has a coordinate that isn't a number: {error}"
        ) from error
    hmm_from, hmm_to, ali_from, ali_to, env_from, env_to = coordinates
    return TreegrafterHit(
        panther_id=row[1],
        node_id=value(row[12]),
        graft_point=point,
        go_terms=() if row[13] == NONE else tuple(row[13].split(",")),
        protein_class=value(row[14]),
        score=row[2],
        evalue=row[3],
        domain_score=row[4],
        domain_evalue=row[5],
        hmm_from=hmm_from,
        hmm_to=hmm_to,
        ali_from=ali_from,
        ali_to=ali_to,
        env_from=env_from,
        env_to=env_to,
    )


def check_data(data_dir: Path | str | None = None) -> None:
    """Check that the treegrafter data folder holds what every graft needs: `famhmm/binHmm`,
    `Tree_MSF/`, and an active annotation release with its folder. Raises MissingDataError, naming
    the folder and each missing part, if it doesn't.

    It's cheap: a few `stat`s, and the date in `annotations/active`. No library or release file is
    read. `treegrafter data verify` checks the contents.
    """
    folder = service_folder(data.SERVICE, data.VERSION, data_dir)
    missing: list[str] = []
    if not (folder / data.BINHMM).is_file():
        missing.append(data.BINHMM)
    if not (folder / data.TREE_MSF).is_dir():
        missing.append(f"{data.TREE_MSF}/")
    date = active(folder.parent.parent)
    if date is None:
        missing.append(f"an active annotation release ({data.ANNOTATIONS}/{data.ACTIVE})")
    elif not (folder / data.ANNOTATIONS / date).is_dir():
        missing.append(f"{data.ANNOTATIONS}/{date}/, the active release")
    if missing:
        raise MissingDataError(f"the treegrafter data folder {folder} lacks: {', '.join(missing)}")


def active(root: Path) -> str | None:
    """The active release's date in the data folder `root`, or None for none, or one that isn't a
    date."""
    try:
        return data.active_date(root)
    except (data.TreegrafterDataError, OSError, UnicodeDecodeError):
        return None


def annotations(
    data_dir: Path | str | None = None, *, manifest: Path = data.MANIFEST
) -> AnnotationRelease:
    """The active annotation release of the data folder, `PANTHER_DATA_DIR` by default, and the GO
    release its pin states. Raises MissingDataError when no release is active, or the active one
    isn't pinned."""
    root = service_folder(data.SERVICE, data.VERSION, data_dir).parent.parent
    date = active(root)
    if date is None:
        raise MissingDataError(f"no annotation release is active in {root / data.FOLDER}")
    releases = data.release_pins(data.read_pin(manifest))
    if date not in releases:
        raise MissingDataError(f"the active annotation release, {date}, isn't pinned")
    return AnnotationRelease(date, releases[date].go_release)
