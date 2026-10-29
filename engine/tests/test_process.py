import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from panther_engine.core.process import run_tool

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


def test_a_relative_program_is_refused() -> None:
    with pytest.raises(ValueError, match="absolute path"):
        run_tool("blastp", ["-version"], timeout=10)


def test_one_string_as_the_arguments_is_refused(make_tool: Callable[[str, str], Path]) -> None:
    tool = make_tool("record-argv", RECORD_ARGV)

    with pytest.raises(TypeError, match="sequence of arguments"):
        run_tool(tool, "-version", timeout=10)
