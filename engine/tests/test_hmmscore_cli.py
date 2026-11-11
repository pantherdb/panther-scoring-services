import hashlib
import json
from pathlib import Path

import pytest
from hmmscore_fixtures import SF2_MODEL, clean_library, data, library_tarball

from panther_engine.cli import main

# survey


@pytest.fixture
def tarball(tmp_path: Path) -> Path:
    return library_tarball(tmp_path / "library.tgz", clean_library())


def test_survey_prints_the_sha256_the_size_and_each_check(
    tarball: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = main(["hmmscore", "survey", str(tarball)])

    out = capsys.readouterr().out
    assert status == 0
    assert f"sha256:   {hashlib.sha256(tarball.read_bytes()).hexdigest()}" in out
    assert f"Bytes:    {tarball.stat().st_size:,}" in out
    assert "model-legacy-id: 1 files" in out
    assert "names-rejected: 0 lines" in out
    assert "binhmm-differs: not checked" in out


def test_survey_exits_0_whatever_the_checks_found(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = clean_library()
    files[SF2_MODEL] = data("broken/two-models.hmm")
    broken = library_tarball(tmp_path / "broken.tgz", files)

    assert main(["hmmscore", "survey", str(broken)]) == 0
    assert "model-rejected: 1 files" in capsys.readouterr().out


def test_survey_writes_nothing_but_the_json_report(
    tarball: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    before = sorted(tmp_path.rglob("*"))

    status = main(["hmmscore", "survey", str(tarball), "--json", "survey.json"])

    assert status == 0
    assert sorted(tmp_path.rglob("*")) == sorted([*before, work / "survey.json"])
    report = json.loads((work / "survey.json").read_text(encoding="utf-8"))
    assert report["tarball"]["sha256"] == hashlib.sha256(tarball.read_bytes()).hexdigest()
    assert report["checks"]["model-legacy-id"]["count"] == 1


@pytest.mark.parametrize("kind", ["truncated gzip", "plain text"])
def test_an_unreadable_tarball_is_reported_with_a_non_zero_status(
    kind: str, tarball: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    unreadable = tmp_path / "unreadable.tgz"
    if kind == "truncated gzip":
        content = tarball.read_bytes()
        unreadable.write_bytes(content[: len(content) // 2])
    else:
        unreadable.write_text("not a tarball\n")

    status = main(["hmmscore", "survey", str(unreadable)])

    captured = capsys.readouterr()
    assert status == 1
    assert "panther-engine hmmscore survey: can't read" in captured.err
    assert "sha256:" not in captured.out


def test_survey_help_lists_the_options(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exited:
        main(["hmmscore", "survey", "--help"])

    out = capsys.readouterr().out
    assert exited.value.code == 0
    for option in ("TARBALL", "--json FILE"):
        assert option in out
