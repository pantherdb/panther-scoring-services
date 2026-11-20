"""HMMER3's `hmmscan` and `hmmsearch`, for every service that scores against HMMs.

Thin layers over `run_tool`: an argument list and no shell, the program found on PATH as
`core/tools.py` finds it, and the output written to a file byte for byte. `hmmscan` writes its
`--domtblout` table, which `hmmscore` reads; `hmmsearch` writes its full text report, with the
alignments, which `hmmscore` shows and `treegrafter` will read. Each returns the finished process:
checking its exit status is the caller's job, as with `run_tool`. Each dies with the process that
started it, on Linux (`run_tool`'s `die_with_parent`).
"""

import os
import shutil
import subprocess
from pathlib import Path

from panther_engine.core.process import run_tool


def program(name: str) -> Path:
    """The absolute path of `name` on PATH. Raises FileNotFoundError if it isn't there."""
    found = shutil.which(name)
    if found is None:
        raise FileNotFoundError(f"no {name} on PATH")
    return Path(found).absolute()


def hmmscan(
    database: Path,
    query: Path,
    *,
    table: Path,
    cpu: int,
    timeout: float | None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """`hmmscan --domtblout table --cpu cpu database query`, in the folder `cwd`.

    The table goes to `table`; what `hmmscan` prints is discarded. Running past `timeout` seconds
    kills it and raises `subprocess.TimeoutExpired`.
    """
    args = ["--domtblout", str(table), "--cpu", str(cpu), str(database), str(query)]
    return run_tool(
        program("hmmscan"),
        args,
        timeout=timeout,
        cwd=cwd,
        stdout=Path(os.devnull),
        die_with_parent=True,
    )


def hmmsearch(
    model: Path,
    query: Path,
    *,
    report: Path,
    cpu: int,
    timeout: float | None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """`hmmsearch --cpu cpu model query > report`, in the folder `cwd`.

    The report, `hmmsearch`'s standard output, goes to `report` byte for byte. Running past
    `timeout` seconds kills it and raises `subprocess.TimeoutExpired`.
    """
    args = ["--cpu", str(cpu), str(model), str(query)]
    return run_tool(
        program("hmmsearch"), args, timeout=timeout, cwd=cwd, stdout=report, die_with_parent=True
    )
