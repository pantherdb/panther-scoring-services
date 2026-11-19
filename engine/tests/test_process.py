import contextlib
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from panther_engine.core import process
from panther_engine.core.process import run_tool

LINUX_ONLY = pytest.mark.skipif(
    sys.platform != "linux", reason="a tool dies with its parent on Linux only"
)
# A tool that writes its process ID to the file it's given, then runs until it's killed.
LONG_RUNNING = 'echo $$ > "{pid_file}"\nexec sleep 60'

# Writes each argument it receives, NUL-terminated, to argv.bin beside itself.
RECORD_ARGV = 'printf "%s\\0" "$@" > "$(dirname "$0")/argv.bin"'

SHELL_METACHARACTERS = [
    "; touch marker",
    "&& touch marker",
    "| touch marker",
    "$(touch marker)",
    "`touch marker`",
    "> marker",
    "*",
    "two words",
    "'single' \"double\"",
    "",
]


def received_argv(tool: Path) -> list[str]:
    return (tool.parent / "argv.bin").read_bytes().decode("utf-8").split("\0")[:-1]


def test_shell_metacharacters_reach_the_tool_unchanged(
    make_tool: Callable[[str, str], Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = make_tool("record-argv", RECORD_ARGV)
    # Through a shell, `touch marker` would create the file here.
    monkeypatch.chdir(tmp_path)

    result = run_tool(tool, SHELL_METACHARACTERS, timeout=10)

    assert result.returncode == 0
    assert received_argv(tool) == SHELL_METACHARACTERS
    assert not (tmp_path / "marker").exists()


def test_output_and_a_failing_status_are_returned(make_tool: Callable[[str, str], Path]) -> None:
    tool = make_tool("fails", "echo out; echo err >&2; exit 3")

    result = run_tool(tool, [], timeout=10)

    assert result.returncode == 3
    assert result.stdout == "out\n"
    assert result.stderr == "err\n"


def test_a_tool_past_its_timeout_raises(make_tool: Callable[[str, str], Path]) -> None:
    tool = make_tool("slow", "exec sleep 5")

    with pytest.raises(subprocess.TimeoutExpired):
        run_tool(tool, [], timeout=0.2)


def test_no_timeout_lets_the_tool_finish(make_tool: Callable[[str, str], Path]) -> None:
    tool = make_tool("slowish", "sleep 0.3; echo done")

    assert run_tool(tool, [], timeout=None).stdout == "done\n"


def test_a_relative_program_is_refused() -> None:
    with pytest.raises(ValueError, match="absolute path"):
        run_tool("blastp", ["-version"], timeout=10)


def test_one_string_as_the_arguments_is_refused(make_tool: Callable[[str, str], Path]) -> None:
    tool = make_tool("record-argv", RECORD_ARGV)

    with pytest.raises(TypeError, match="sequence of arguments"):
        run_tool(tool, "-version", timeout=10)


def test_input_reaches_the_tool_on_stdin_unchanged(
    make_tool: Callable[[str, str], Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = make_tool("record-stdin", 'cat > "$(dirname "$0")/stdin.txt"')
    text = ">P0001\n" + "\n".join(SHELL_METACHARACTERS) + "\nlast line, no newline"
    monkeypatch.chdir(tmp_path)

    result = run_tool(tool, [], timeout=10, input=text)

    assert result.returncode == 0
    assert (tool.parent / "stdin.txt").read_text(encoding="utf-8") == text
    assert not (tmp_path / "marker").exists()


def test_the_tool_runs_in_cwd(make_tool: Callable[[str, str], Path], tmp_path: Path) -> None:
    tool = make_tool("where", "pwd -P")
    folder = tmp_path / "work"
    folder.mkdir()

    result = run_tool(tool, [], timeout=10, cwd=folder)

    assert result.stdout == f"{folder.resolve()}\n"


def test_blasts_usage_reports_are_off_even_when_the_caller_asks_for_them(
    make_tool: Callable[[str, str], Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = make_tool("report", 'printf "%s" "${BLAST_USAGE_REPORT-unset}"')
    monkeypatch.setenv("BLAST_USAGE_REPORT", "true")

    result = run_tool(tool, [], timeout=10)

    assert result.stdout == "false"


def test_the_rest_of_the_callers_environment_reaches_the_tool(
    make_tool: Callable[[str, str], Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = make_tool("environment", 'printf "%s|%s" "$PANTHER_TEST_VALUE" "$BLAST_USAGE_REPORT"')
    monkeypatch.setenv("PANTHER_TEST_VALUE", "a value; with $(shell) characters")

    result = run_tool(tool, [], timeout=10)

    assert result.stdout == "a value; with $(shell) characters|false"


def test_the_callers_variables_are_set_over_the_environment(
    make_tool: Callable[[str, str], Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = make_tool(
        "environment",
        'printf "%s|%s|%s" "$REQUEST_METHOD" "$PANTHER_TEST_VALUE" "$BLAST_USAGE_REPORT"',
    )
    monkeypatch.setenv("PANTHER_TEST_VALUE", "kept")
    monkeypatch.setenv("REQUEST_METHOD", "GET")

    result = run_tool(
        tool,
        [],
        timeout=10,
        environment={"REQUEST_METHOD": "POST", "BLAST_USAGE_REPORT": "true"},
    )

    assert result.stdout == "POST|kept|false"


def test_stdout_to_a_file_keeps_every_byte(
    make_tool: Callable[[str, str], Path], tmp_path: Path
) -> None:
    # Carriage returns, a byte that isn't UTF-8 and no final line feed: text capture would
    # change the first two.
    tool = make_tool("bytes", "printf 'a\\r\\nb\\r\\tc\\351'; echo warning >&2; exit 3")
    out = tmp_path / "out"

    result = run_tool(tool, [], timeout=10, stdout=out)

    assert out.read_bytes() == b"a\r\nb\r\tc\xe9"
    assert result.stdout == ""
    assert result.stderr == "warning\n"
    assert result.returncode == 3


def test_text_capture_translates_carriage_returns(
    make_tool: Callable[[str, str], Path],
) -> None:
    tool = make_tool("bytes", "printf 'a\\r\\nb\\r\\tc'")

    assert run_tool(tool, [], timeout=10).stdout == "a\nb\n\tc"


# A tool doesn't outlive the process that started it (wire-hmmscore, decision 9). When a worker
# is killed, by the out-of-memory killer or a broken pool, the kernel kills its search tool, so
# the tool can't run on without its time limit beside the next job.

# What the parent runs, in its own Python process, before the test kills it.
PARENT = """
import os, sys
from pathlib import Path
from panther_engine.core import hmmer
from panther_engine.core.process import run_tool
from panther_engine.csnp import blast
work = Path(sys.argv[1])
"""
CALLS = {
    "run_tool, tied": "run_tool(work / 'bin' / 'tool', [], timeout=60, die_with_parent=True)",
    "run_tool, untied": "run_tool(work / 'bin' / 'tool', [], timeout=60)",
    "hmmscan": "hmmer.hmmscan(work / 'db', work / 'q', table=work / 't', cpu=0, timeout=60)",
    "hmmsearch": "hmmer.hmmsearch(work / 'm', work / 'q', report=work / 'r', cpu=0, timeout=60)",
    "blastp": "blast.search('MKVLW', work / 'data', timeout=60)",
}


def running(pid: int) -> bool:
    """Whether process `pid` is running. A killed process that hasn't been reaped yet, a zombie,
    isn't: an orphan is reaped only if the container's first process waits for it."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    # ProcessLookupError: reaped between opening the file and reading it.
    except (FileNotFoundError, ProcessLookupError):
        return False
    # "pid (name) state ...", where the name may hold spaces and parentheses.
    return stat.rpartition(")")[2].split()[0] != "Z"


def tool_of_a_killed_parent(
    call: str, tool: str, make_tool: Callable[[str, str], Path], tmp_path: Path
) -> int:
    """Run `call` in a parent process, with `tool` a long-running stand-in on PATH; once the tool
    has started, kill the parent with SIGKILL. Returns the tool's process ID."""
    pid_file = tmp_path / "tool.pid"
    folder = make_tool(tool, LONG_RUNNING.format(pid_file=pid_file)).parent
    (tmp_path / "data" / "blast").mkdir(parents=True)
    environment = {**os.environ, "PATH": f"{folder}:{os.environ['PATH']}"}
    parent = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", PARENT + call, str(tmp_path)], env=environment
    )
    try:
        deadline = time.monotonic() + 10
        while not pid_file.is_file() or not pid_file.read_text(encoding="utf-8").strip():
            assert parent.poll() is None, "the parent ended before its tool started"
            assert time.monotonic() < deadline, "the tool never started"
            time.sleep(0.05)
    finally:
        parent.kill()
        parent.wait()
    return int(pid_file.read_text(encoding="utf-8"))


def still_running_after(pid: int, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while running(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    return running(pid)


@LINUX_ONLY
@pytest.mark.parametrize(
    ("call", "tool"),
    [
        ("run_tool, tied", "tool"),
        ("hmmscan", "hmmscan"),
        ("hmmsearch", "hmmsearch"),
        ("blastp", "blastp"),
    ],
)
def test_a_search_tool_dies_with_its_parent(
    call: str, tool: str, make_tool: Callable[[str, str], Path], tmp_path: Path
) -> None:
    pid = tool_of_a_killed_parent(CALLS[call], tool, make_tool, tmp_path)
    try:
        assert not still_running_after(pid, 5)
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)


@LINUX_ONLY
def test_an_untied_tool_outlives_its_parent(
    make_tool: Callable[[str, str], Path], tmp_path: Path
) -> None:
    # What the tied tools are kept from, and what the version checks still do.
    pid = tool_of_a_killed_parent(CALLS["run_tool, untied"], "tool", make_tool, tmp_path)
    try:
        assert still_running_after(pid, 0.5)
    finally:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)


def test_a_tied_tool_whose_parent_lives_runs_as_before(
    make_tool: Callable[[str, str], Path],
) -> None:
    tool = make_tool("fails", 'echo "$1"; echo err >&2; exit 3')

    result = run_tool(tool, ["out"], timeout=10, die_with_parent=True)

    assert (result.returncode, result.stdout, result.stderr) == (3, "out\n", "err\n")


def test_a_tied_tool_that_cant_be_set_up_raises_an_oserror(
    make_tool: Callable[[str, str], Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    # As a program that can't start does, so each caller's handling covers it: CPython reports a
    # failure in the child, before the program starts, only as a SubprocessError.
    def fails_to_set_up() -> None:
        raise OSError("prctl(PR_SET_PDEATHSIG) failed")

    def dies_with(_parent: int) -> Callable[[], None]:
        return fails_to_set_up

    monkeypatch.setattr(process, "_dies_with", dies_with)
    tool = make_tool("never-runs", 'touch "$(dirname "$0")/ran"')

    with pytest.raises(OSError, match="couldn't be started"):
        run_tool(tool, [], timeout=10, die_with_parent=True)
    assert not (tool.parent / "ran").exists()
