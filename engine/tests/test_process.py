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
