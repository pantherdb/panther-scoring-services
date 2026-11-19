"""Run external tools. This is the one place the engine starts a subprocess."""

import contextlib
import ctypes
import os
import signal
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

# Set for every tool, over the caller's environment. BLAST+ 2.17.0 otherwise sends NCBI a usage
# report on every run, `-version` included, and waits about 10 s where that traffic is dropped.
FIXED_ENVIRONMENT: Mapping[str, str] = {"BLAST_USAGE_REPORT": "false"}

if sys.platform == "linux":
    # prctl(2)'s option that has the kernel send a process a signal when its parent dies. Looked
    # up here, in the parent, so the child does as little as it can between fork and exec.
    PR_SET_PDEATHSIG = 1
    _prctl = ctypes.CDLL(None, use_errno=True).prctl
    _prctl.argtypes = (ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong)
    _prctl.restype = ctypes.c_int


def run_tool(
    program: Path | str,
    args: Sequence[str],
    *,
    timeout: float | None,
    input: str | None = None,
    cwd: Path | None = None,
    stdout: Path | None = None,
    environment: Mapping[str, str] | None = None,
    die_with_parent: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run `program` with `args`, never through a shell, and return the finished process.

    `program` is an absolute path, as `shutil.which` returns. Each item of `args` reaches the
    program unchanged, as one argument. `input`, if given, reaches the program's stdin unchanged,
    as UTF-8 text. The program runs in the folder `cwd`, if given, with the caller's environment,
    then `environment`'s variables, if given, then `FIXED_ENVIRONMENT`, each set over the one
    before. Output is captured as UTF-8 text, in which a carriage
    return, alone or before a line feed, is read as a line feed. With `stdout`, the program's
    standard output goes to that file instead, byte for byte, as a shell's `>` would send it, and
    the result's `stdout` is empty. A non-zero exit status is not an error here: the caller checks
    `returncode`. Running past `timeout` seconds kills the program and raises
    `subprocess.TimeoutExpired`; with `timeout` None, the program runs until it ends.

    With `die_with_parent`, on Linux, the kernel kills the program with SIGKILL when the thread
    that started it ends, however it ends. In a job's worker that's the main thread, so the program
    dies with the worker. It's for the search tools a job runs, which mustn't run on without their
    time limit beside the next job (wire-hmmscore, decision 9); elsewhere than Linux it changes
    nothing. It runs a little Python in the child before the program starts (`preexec_fn`), which
    Python's documentation calls unsafe where other threads exist, so the tool version checks,
    which the API's threaded process runs, don't use it. If that set-up fails, `run_tool` raises
    `OSError`, as for a program that can't start.
    """
    path = Path(program)
    if not path.is_absolute():
        raise ValueError(f"program must be an absolute path, not {str(program)!r}")
    if isinstance(args, str):
        raise TypeError("args must be a sequence of arguments, not one string")

    with contextlib.ExitStack() as stack:
        out = subprocess.PIPE if stdout is None else stack.enter_context(stdout.open("wb"))
        try:
            # S603 flags every subprocess call whose arguments aren't all literals. This one is
            # checked: an absolute program, an argument list and no shell. Anywhere else in the
            # engine, S603 stays an error.
            result = subprocess.run(  # noqa: S603
                [str(path), *args],
                shell=False,
                input=input,
                cwd=cwd,
                env={**os.environ, **(environment or {}), **FIXED_ENVIRONMENT},
                stdout=out,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                preexec_fn=_dies_with(os.getpid()) if die_with_parent else None,
            )
        except subprocess.TimeoutExpired:
            raise
        except subprocess.SubprocessError as error:
            # With check=False, only a failure in the child before the program starts, in
            # die_with_parent's set-up, and CPython reports no more than that it failed.
            raise OSError(f"{path} couldn't be started: {error}") from error
    if stdout is not None:
        result.stdout = ""
    return result


def _dies_with(parent: int) -> Callable[[], None] | None:
    """What a child runs before its program, so the kernel kills it when `parent` dies. None
    except on Linux."""
    if sys.platform != "linux":
        return None

    def set_up() -> None:
        if _prctl(PR_SET_PDEATHSIG, int(signal.SIGKILL), 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "prctl(PR_SET_PDEATHSIG) failed")
        # A parent that died before prctl sends nothing: the child was already an orphan.
        if os.getppid() != parent:
            raise OSError("the parent ended before the tool started")

    return set_up
