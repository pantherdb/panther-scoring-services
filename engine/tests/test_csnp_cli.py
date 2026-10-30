import gzip
import hashlib
import json
from pathlib import Path

import pytest
from csnp_fixtures import FAMILY, FIXTURES, family_files, make_tar

from panther_engine.cli import main


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    return make_tar(inputs / "library.tar.gz", family_files(FAMILY))


def test_survey_prints_the_sha256_the_family_count_and_each_check(
    archive: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = main(["csnp", "survey", str(archive), "--species", str(FIXTURES / "species.nhx")])

    out = capsys.readouterr().out
    assert status == 0
    assert f"sha256:   {hashlib.sha256(archive.read_bytes()).hexdigest()}" in out
    assert "Families: 1 (1 with a root; 3 leaves)" in out
    assert "legacy-start-column: 0 families, 0 leaves" in out
    assert "blast-no-paml: not checked" in out


def test_survey_exits_0_whatever_the_checks_found(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = family_files(FAMILY)
    archive = make_tar(tmp_path / "broken.tar.gz", [*files[:1], (files[1][0], b""), files[2]])

    assert main(["csnp", "survey", str(archive)]) == 0
    assert "rejected-rst: 1 families" in capsys.readouterr().out


def test_survey_writes_nothing_but_the_json_report(
    archive: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    before = sorted(tmp_path.rglob("*"))

    status = main(["csnp", "survey", str(archive), "--json", "survey.json"])

    assert status == 0
    assert sorted(tmp_path.rglob("*")) == sorted([*before, work / "survey.json"])
    report = json.loads((work / "survey.json").read_text(encoding="utf-8"))
    assert report["families"] == 1
    assert report["archive"]["sha256"] == hashlib.sha256(archive.read_bytes()).hexdigest()


def test_a_truncated_archive_is_reported_with_a_non_zero_status(
    archive: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    content = archive.read_bytes()
    truncated = tmp_path / "truncated.tar.gz"
    truncated.write_bytes(content[: len(content) // 2])

    status = main(["csnp", "survey", str(truncated)])

    assert status == 1
    assert "can't read" in capsys.readouterr().err


def test_a_truncated_tar_inside_good_gzip_is_reported(
    archive: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tar = gzip.decompress(archive.read_bytes())
    truncated = tmp_path / "short.tar.gz"
    truncated.write_bytes(gzip.compress(tar[:700]))

    assert main(["csnp", "survey", str(truncated)]) == 1
    assert "can't read" in capsys.readouterr().err


def test_a_file_that_isnt_a_gzipped_tar_is_reported_with_a_non_zero_status(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = tmp_path / "notes.txt"
    text.write_text("not an archive\n", encoding="utf-8")

    status = main(["csnp", "survey", str(text)])

    assert status == 1
    assert "can't read" in capsys.readouterr().err


def test_a_missing_archive_is_reported_with_a_non_zero_status(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["csnp", "survey", str(tmp_path / "missing.tar.gz")]) == 1
    assert "missing.tar.gz" in capsys.readouterr().err


def test_survey_help_lists_the_options(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exited:
        main(["csnp", "survey", "--help"])

    out = capsys.readouterr().out
    assert exited.value.code == 0
    for option in ("ARCHIVE", "--species FILE", "--blast-archive FILE", "--json FILE"):
        assert option in out
