"""EPA-ng, which places a query alignment on a reference tree, for `treegrafter`.

A thin layer over `run_tool`, as `core/hmmer.py`'s runners are: an argument list and no shell, the
program found on PATH, and the finished process returned, so checking its exit status and its
`epa_result.jplace` is the caller's job. EPA-ng dies with the process that started it, on Linux
(`run_tool`'s `die_with_parent`). EBI's `treegrafter` ran it with `subprocess.call`, with no time
limit and its output discarded (`_run_epang`, treegrafter.py 153 to 175).
"""

import subprocess
from pathlib import Path

from panther_engine.core.hmmer import program
from panther_engine.core.process import run_tool

# EBI's options (treegrafter.py 160 to 167): prescore the 5% most likely branches, then place with
# the WAG substitution model.
PRESCORING = "0.05"
MODEL = "WAG"


def place(
    tree: Path,
    msa: Path,
    query: Path,
    outdir: Path,
    *,
    threads: int = 1,
    timeout: float | None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """`epa-ng -G 0.05 -m WAG -T threads -t tree -s msa -q query -w outdir`, in the folder `cwd`.

    `tree` is the reference tree, `msa` its alignment and `query` the query's alignment to the same
    columns. EPA-ng writes `epa_result.jplace` and `epa_info.log` into `outdir`, which must exist.
    Its standard output and error are returned. Running past `timeout` seconds kills it and raises
    `subprocess.TimeoutExpired`.
    """
    args = [
        "-G",
        PRESCORING,
        "-m",
        MODEL,
        "-T",
        str(threads),
        "-t",
        str(tree),
        "-s",
        str(msa),
        "-q",
        str(query),
        "-w",
        str(outdir),
    ]
    return run_tool(program("epa-ng"), args, timeout=timeout, cwd=cwd, die_with_parent=True)
