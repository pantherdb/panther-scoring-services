"""The `tools` marker, tested by running a small suite with this folder's conftest.py."""

from pathlib import Path

import pytest

CONFTEST = Path(__file__).with_name("conftest.py")

INI = """
[pytest]
addopts = --strict-markers
markers =
    tools(*names): runs the named external tools
"""

SUITE = """
import pytest


@pytest.mark.tools("sh", "no-such-tool-for-panther")
def test_needs_a_missing_tool():
    pass


@pytest.mark.tools("sh")
def test_needs_a_present_tool():
    pass


def test_needs_no_tool():
    pass
"""


@pytest.fixture
def suite(pytester: pytest.Pytester) -> pytest.Pytester:
    pytester.makeconftest(CONFTEST.read_text(encoding="utf-8"))
    pytester.makeini(INI)
    pytester.makepyfile(SUITE)
    return pytester


def test_a_missing_tool_skips_the_test_and_names_the_tool(
    suite: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PANTHER_REQUIRE_TOOLS", raising=False)

    result = suite.runpytest("-rs")

    result.assert_outcomes(passed=2, skipped=1)
    result.stdout.fnmatch_lines(["SKIPPED * needs no-such-tool-for-panther, not found on PATH"])


def test_a_missing_tool_fails_the_test_where_tools_are_required(
    suite: pytest.Pytester, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PANTHER_REQUIRE_TOOLS", "1")

    result = suite.runpytest("-rf")

    result.assert_outcomes(passed=2, failed=1)
    result.stdout.fnmatch_lines(
        [
            "*_ test_needs_a_missing_tool _*",
            "needs no-such-tool-for-panther, not found on PATH (PANTHER_REQUIRE_TOOLS=1)",
            "FAILED *::test_needs_a_missing_tool*",
        ]
    )
