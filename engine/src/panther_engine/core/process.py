"""Run external tools. This is the one place the engine starts a subprocess."""

import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

# Set for every tool, over the caller's environment. BLAST+ 2.17.0 otherwise sends NCBI a usage
# report on every run, `-version` included, and waits about 10 s where that traffic is dropped.
FIXED_ENVIRONMENT: Mapping[str, str] = {"BLAST_USAGE_REPORT": "false"}


def run_tool(
    program: Path | str,
    args: Sequence[str],
    *,
    timeout: float,
    input: str | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `program` with `args`, never through a shell, and return the finished process.

    `program` is an absolute path, as `shutil.which` returns. Each item of `args` reaches the
    program unchanged, as one argument. `input`, if given, reaches the program's stdin unchanged,
    as UTF-8 text. The program runs in the folder `cwd`, if given, with the caller's environment
    and `FIXED_ENVIRONMENT` set over it. Output is captured as UTF-8 text. A non-zero exit status
    is not an error here: the caller checks `returncode`. Running past `timeout` seconds kills the
    program and raises `subprocess.TimeoutExpired`.
    """
    path = Path(program)
    if not path.is_absolute():
        raise ValueError(f"program must be an absolute path, not {str(program)!r}")
    if isinstance(args, str):
        raise TypeError("args must be a sequence of arguments, not one string")

    # S603 flags every subprocess call whose arguments aren't all literals. This one is checked:
    # an absolute program, an argument list and no shell. Anywhere else in the engine, S603 stays
    # an error.
    return subprocess.run(  # noqa: S603
        [str(path), *args],
        shell=False,
        input=input,
        cwd=cwd,
        env={**os.environ, **FIXED_ENVIRONMENT},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
