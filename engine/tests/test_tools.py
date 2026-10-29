from collections.abc import Callable
from pathlib import Path

import pytest

from panther_engine.cli import main
from panther_engine.core.tools import TOOLS, Tool, report_tools

FIXTURES = Path(__file__).parent / "fixtures" / "tool-versions"

# The versions the root Dockerfile pins.
PINNED = {"blastp": "2.17.0", "hmmscan": "3.4", "hmmsearch": "3.4", "epa-ng": "0.3.8"}


def fake_tools(
    make_tool: Callable[[str, str], Path], monkeypatch: pytest.MonkeyPatch, names: list[str]
) -> Path:
    """Fake tools that print their recorded version output, alone on PATH. Returns their folder."""
    folder = Path()
    for name in names:
        folder = make_tool(name, f"exec /bin/cat '{FIXTURES / f'{name}.txt'}'").parent
    monkeypatch.setenv("PATH", str(folder))
    return folder


@pytest.mark.parametrize("tool", TOOLS, ids=lambda tool: tool.name)
def test_version_pattern_reads_the_recorded_output(tool: Tool) -> None:
    output = (FIXTURES / f"{tool.name}.txt").read_text(encoding="utf-8")

    assert tool.parse_version(output) == PINNED[tool.name]


def test_report_lists_every_tool_with_its_version_and_path(
    make_tool: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    folder = fake_tools(make_tool, monkeypatch, list(PINNED))

    status = main(["tools"])

    lines = capsys.readouterr().out.splitlines()
    assert status == 0
    assert [line.split() for line in lines] == [
        [name, version, str(folder / name)] for name, version in PINNED.items()
    ]


def test_report_names_a_missing_tool_and_still_reports_the_others(
    make_tool: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_tools(make_tool, monkeypatch, ["blastp", "hmmscan", "hmmsearch"])

    status = main(["tools"])

    lines = capsys.readouterr().out.splitlines()
    assert status == 1
    assert [line.split()[:2] for line in lines[:3]] == [
        ["blastp", "2.17.0"],
        ["hmmscan", "3.4"],
        ["hmmsearch", "3.4"],
    ]
    assert lines[3].split() == ["epa-ng", "not", "found"]


def test_a_version_that_cannot_be_read_fails_the_report(
    make_tool: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    folder = fake_tools(make_tool, monkeypatch, ["blastp", "hmmscan", "hmmsearch"])
    make_tool("epa-ng", "echo 'something else'")

    status = main(["tools"])

    lines = capsys.readouterr().out.splitlines()
    assert status == 1
    assert lines[3].split() == ["epa-ng", "version", "unknown", str(folder / "epa-ng")]


@pytest.mark.tools(*PINNED)
def test_the_installed_tools_report_the_pinned_versions() -> None:
    reports = report_tools()

    assert {report.name: report.version for report in reports} == PINNED
