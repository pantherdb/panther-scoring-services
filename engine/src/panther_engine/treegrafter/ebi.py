"""EBI's `treegrafter`, contained: typed wrappers for the functions the engine calls.

EBI's code is one module, `treegrafter.py`, at the commit `engine/pyproject.toml` pins. It imports
Biopython at the top, so it's imported here inside each function, never when the engine is
imported: the API's process imports the engine and never grafts (adopt-treegrafter, design.md,
decision 3). The functions run unmodified:

- `parsehmmsearch`, `filter_best_domain`, `filter_evalue_cutoff`, `generate_fasta_for_panthr` and
  `process_tree`, for a graft, as `treegrafter.py run` calls them;
- `prepare`, for an annotation release.

EBI's code writes its reasons to standard error, and calls `sys.exit` on a report it can't read.
Each wrapper captures standard error, and turns `SystemExit`, or any exception EBI's code raises,
into `TreegrafterError`, with what EBI wrote, for the log. The engine's process never exits, and
nothing EBI writes reaches the caller's standard error. What a call wrote and then returned from is
logged at debug level.

This module alone relaxes basedpyright's rules on unknown types, since EBI's code has none: each
wrapper gives its function a signature, and casts what it returns.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportMissingTypeStubs=false

import argparse
import contextlib
import io
import logging
import threading
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

# The sha256 of `treegrafter.py` at the pinned commit, EBI's `5ef350f` (adopt-treegrafter, spec:
# The adopted code). ebi-pf-team/treegrafter#9 adds only a pyproject.toml, so its head commit has
# the same file.
MODULE_SHA256 = "9741da411ef4ae7c2cf5bf80b133391ee45b78149bc8aa0e2c9143ddd55de44c"
# How much of what EBI's code wrote goes into an error, for the log.
STDERR_LINES = 3

logger = logging.getLogger(__name__)
# redirect_stderr swaps sys.stderr for the whole process, so one thread at a time runs EBI's code.
# The API grafts in worker processes, one job each; this keeps threads, as in a test, safe too.
_LOCK = threading.Lock()

type Alignment = dict[str, list[str]]
"""One query's domains in one family, as `parsehmmsearch` keeps them: `hmmalign`, `matchalign`,
`hmmstart`, `hmmend`, `score`, `evalue`, `domscore`, `domevalue`, `alifrom`, `alito`, `envfrom`,
`envto` and `acc`, each a list of strings, one per domain."""
type FamilyMatches = dict[str, Alignment]
"""A family's queries, by query ID."""
type Matches = dict[str, FamilyMatches]
"""The families a report holds, by family ID, such as PTHR18976."""


class TreegrafterError(Exception):
    """Grafting failed in a way that isn't the input's fault: EBI's code exited or raised, a tool
    failed, or the data has a problem a graft found.

    Never an `InputError`: the job fails with the generic `500`, and the message goes to the log.
    """


def _module() -> ModuleType:
    """EBI's `treegrafter` module, imported on first use."""
    import treegrafter

    return treegrafter


def _call[T](step: str, run: Callable[[], T]) -> T:
    """Run one of EBI's functions with its standard error captured, and its `SystemExit` or any
    exception it raises turned into `TreegrafterError`."""
    written = io.StringIO()
    try:
        with _LOCK, contextlib.redirect_stderr(written):
            result = run()
    except SystemExit as error:
        raise TreegrafterError(
            f"EBI's {step} exited with status {error.code}{_detail(written)}"
        ) from None
    except Exception as error:
        raise TreegrafterError(
            f"EBI's {step} raised {type(error).__name__}: {error}{_detail(written)}"
        ) from error
    text = written.getvalue().strip()
    if text:
        logger.debug("EBI's %s wrote: %s", step, text)
    return result


def _detail(written: io.StringIO) -> str:
    lines = written.getvalue().strip().splitlines()[-STDERR_LINES:]
    return f": {' / '.join(lines)}" if lines else ""


def parse_hmmsearch(report: Path) -> Matches:
    """`parsehmmsearch`: the families of `hmmsearch`'s text report whose full sequence passes the
    inclusion threshold, each query's domains that do, and their alignments."""
    parse = cast(Callable[[str], Matches], _module().parsehmmsearch)
    return _call("parsehmmsearch", lambda: parse(str(report)))


def filter_best_domain(matches: Matches) -> Matches:
    """`filter_best_domain`: each query's highest-scoring domain only, in place."""
    keep = cast(Callable[[Matches], Matches], _module().filter_best_domain)
    return _call("filter_best_domain", lambda: keep(matches))


def filter_evalue_cutoff(matches: Matches, cutoff: float) -> Matches:
    """`filter_evalue_cutoff`: drops each query whose full-sequence E-value is over `cutoff`, in
    place. A family left with no query stays, empty."""
    keep = cast(Callable[[Matches, float], Matches], _module().filter_evalue_cutoff)
    return _call("filter_evalue_cutoff", lambda: keep(matches, cutoff))


def generate_fasta_for_panthr(
    family: str, queries: FamilyMatches, library: Path, folder: Path
) -> Path | None:
    """`generate_fasta_for_panthr`: the queries' alignments to the family's alignment columns,
    written to `<family>_query.fasta` in `folder`. None when there are no queries."""
    write = cast(
        Callable[[str, FamilyMatches, str, str], str | None],
        _module().generate_fasta_for_panthr,
    )
    written = _call(
        "generate_fasta_for_panthr", lambda: write(family, queries, str(library), str(folder))
    )
    return None if written is None else Path(written)


def process_tree(
    family: str, jplace: Path, queries: FamilyMatches, library: Path, annotations: Path
) -> list[list[str]]:
    """`process_tree` with `print_go`: for each placement in EPA-ng's `jplace`, EBI's output row,
    from the query ID to the protein class, as the strings `treegrafter.py run` writes."""
    graft = cast(Callable[..., list[list[object]]], _module().process_tree)
    rows = _call(
        "process_tree",
        lambda: graft(family, str(jplace), queries, str(library), str(annotations), print_go=True),
    )
    return [[str(value) for value in row] for row in rows]


def prepare(annotation_file: Path, folder: Path) -> None:
    """`prepare`: one JSON file per family in `folder`, each mapping the family's nodes to their
    subfamily, GO terms, protein class and graft point, from a PAINT TreeGrafter annotation
    file."""
    run = cast(Callable[[argparse.Namespace], None], _module().prepare)
    arguments = argparse.Namespace(annotation_file=str(annotation_file), output_dir=str(folder))
    _call("prepare", lambda: run(arguments))
