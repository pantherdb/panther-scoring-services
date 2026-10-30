"""The `data` marker, tested by running a small suite with this folder's conftest.py."""

from pathlib import Path

import pytest

from panther_engine.core.manifest import checksums, read_manifest
from panther_engine.csnp import sample

CONFTEST = Path(__file__).with_name("conftest.py")

INI = """
[pytest]
addopts = --strict-markers
markers =
    tools(*names): runs the named external tools
    data(*services): reads the named services' data sample
"""

SUITE = """
import pytest


@pytest.mark.data("csnp")
def test_needs_the_csnp_sample():
    pass


def test_needs_no_data():
    pass
"""


@pytest.fixture
def suite(pytester: pytest.Pytester) -> pytest.Pytester:
    pytester.makeconftest(CONFTEST.read_text(encoding="utf-8"))
    pytester.makeini(INI)
    pytester.makepyfile(SUITE)
    return pytester


@pytest.fixture
def empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "empty-data"
    folder.mkdir()
    monkeypatch.setenv("PANTHER_DATA_DIR", str(folder))
    return folder


def test_without_the_data_the_test_is_skipped_naming_the_data_and_the_variable(
    suite: pytest.Pytester, empty: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PANTHER_REQUIRE_DATA", raising=False)

    result = suite.runpytest("-rs")

    result.assert_outcomes(passed=1, skipped=1)
    result.stdout.fnmatch_lines(
        [f"SKIPPED * needs the csnp data sample, not found in {empty} (set PANTHER_DATA_DIR, *"]
    )


def test_where_data_is_required_the_test_fails_naming_the_data(
    suite: pytest.Pytester, empty: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PANTHER_REQUIRE_DATA", "1")

    result = suite.runpytest("-rf")

    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(
        [
            "*_ test_needs_the_csnp_sample _*",
            f"needs the csnp data sample, not found in {empty} (PANTHER_REQUIRE_DATA=1)",
            "FAILED *::test_needs_the_csnp_sample*",
        ]
    )


def test_with_every_file_there_the_test_runs(
    suite: pytest.Pytester, empty: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PANTHER_REQUIRE_DATA", "1")
    # Only presence is checked, so empty files will do.
    for path in checksums(read_manifest(sample.MANIFEST)):
        (empty / path).parent.mkdir(parents=True, exist_ok=True)
        (empty / path).touch()

    suite.runpytest().assert_outcomes(passed=2)
