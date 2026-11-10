"""The `data` marker, tested by running a small suite with this folder's conftest.py."""

from pathlib import Path

import pytest

from panther_engine.core.manifest import checksums, read_manifest
from panther_engine.csnp import sample as csnp_sample
from panther_engine.hmmscore import sample as hmmscore_sample

CONFTEST = Path(__file__).with_name("conftest.py")
# Each service with a data sample, by the manifest that lists its files.
SAMPLES = {"csnp": csnp_sample.MANIFEST, "hmmscore": hmmscore_sample.MANIFEST}

INI = """
[pytest]
addopts = --strict-markers
markers =
    tools(*names): runs the named external tools
    data(*services): reads the named services' data
"""

SUITE = """
import pytest


@pytest.mark.data("{service}")
def test_needs_the_sample():
    pass


def test_needs_no_data():
    pass
"""


@pytest.fixture(params=sorted(SAMPLES))
def service(request: pytest.FixtureRequest) -> str:
    return str(request.param)


@pytest.fixture
def suite(pytester: pytest.Pytester, service: str) -> pytest.Pytester:
    pytester.makeconftest(CONFTEST.read_text(encoding="utf-8"))
    pytester.makeini(INI)
    pytester.makepyfile(SUITE.replace("{service}", service))
    return pytester


@pytest.fixture
def empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "empty-data"
    folder.mkdir()
    monkeypatch.setenv("PANTHER_DATA_DIR", str(folder))
    return folder


def test_without_the_data_the_test_is_skipped_naming_the_data_and_the_variable(
    suite: pytest.Pytester, service: str, empty: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PANTHER_REQUIRE_DATA", raising=False)

    result = suite.runpytest("-rs")

    result.assert_outcomes(passed=1, skipped=1)
    result.stdout.fnmatch_lines(
        [f"SKIPPED * needs the {service} data, not found in {empty} (set PANTHER_DATA_DIR, *"]
    )


def test_where_data_is_required_the_test_fails_naming_the_data(
    suite: pytest.Pytester, service: str, empty: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PANTHER_REQUIRE_DATA", "1")

    result = suite.runpytest("-rf")

    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(
        [
            "*_ test_needs_the_sample _*",
            f"needs the {service} data, not found in {empty} (PANTHER_REQUIRE_DATA=1)",
            "FAILED *::test_needs_the_sample*",
        ]
    )


def test_with_every_file_there_the_test_runs(
    suite: pytest.Pytester, service: str, empty: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PANTHER_REQUIRE_DATA", "1")
    # Only presence is checked, so empty files will do.
    for path in checksums(read_manifest(SAMPLES[service])):
        (empty / path).parent.mkdir(parents=True, exist_ok=True)
        (empty / path).touch()

    suite.runpytest().assert_outcomes(passed=2)


def test_the_hmmscore_data_fixture_is_hmmscore_19_in_the_data_folder(
    pytester: pytest.Pytester, empty: Path
) -> None:
    pytester.makeconftest(CONFTEST.read_text(encoding="utf-8"))
    pytester.makeini(INI)
    pytester.makepyfile(
        f"""
from pathlib import Path


def test_the_folder(hmmscore_data):
    assert hmmscore_data == Path({str(empty)!r}) / "hmmscore" / "19"
"""
    )

    pytester.runpytest().assert_outcomes(passed=1)
