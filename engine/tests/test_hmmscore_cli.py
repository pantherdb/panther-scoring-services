import hashlib
import io
import json
import re
from collections.abc import Callable
from pathlib import Path

import pytest
from hmmscore_fixtures import (
    SF2_MODEL,
    clean_library,
    data,
    install_fake_hmmer,
    library_tarball,
    scoring_folder,
)

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


# score

APOE_FASTA = Path(__file__).parent / "golden" / "hmmscore" / "example" / "apoe.fasta"
APOE = (
    Path(__file__).parent / "golden" / "hmmscore" / "parity" / "inputs" / "apoe.txt"
).read_text()
SCORING_NAMES = "PTHR18976.SF2.mod\tAPOLIPOPROTEIN E\n"


@pytest.fixture
def fake_scoring(
    make_tool: Callable[[str, str], Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Callable[[str], tuple[Path, Path]]:
    """Returns `install(table)`: fake HMMER first on PATH, giving `table`, and a data folder its
    hit's model file is in. Returns the fakes' folder and the data folder."""
    folder = tmp_path / "bin"
    monkeypatch.setenv("PATH", f"{folder}:/usr/bin:/bin")

    def install(table: str) -> tuple[Path, Path]:
        install_fake_hmmer(make_tool, folder, table)
        root = scoring_folder(
            tmp_path / "data", models=("books/PTHR18976/SF2/hmmer.hmm",), names=SCORING_NAMES
        )
        return folder, root

    return install


def recorded(folder: Path, name: str) -> list[str]:
    return (folder / f"{name}.argv").read_bytes().decode("utf-8").split("\0")[:-1]


@pytest.mark.tools("hmmscan", "hmmsearch")
@pytest.mark.data("hmmscore")
def test_score_prints_the_examples_hit(
    hmmscore_data: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = hmmscore_data.parents[1]

    status = main(["hmmscore", "score", str(APOE_FASTA), "--data-dir", str(root)])

    out = capsys.readouterr().out
    names = (hmmscore_data / "globals" / "names.tab").read_text(encoding="latin-1")
    lines = out.splitlines()
    assert status == 0
    assert lines[0] == "panther_id\tPTHR18976:SF2"
    assert f"PTHR18976.SF2.mod\t{lines[1].removeprefix('name' + chr(9))}\n" in names
    assert lines[2].startswith("evalue\t")
    assert lines[3] == "score\t439.0"
    assert lines[4] == "alignment"
    assert lines[5] == ">> sequence  "


def test_score_prints_json(
    fake_scoring: Callable[[str], tuple[Path, Path]], capsys: pytest.CaptureFixture[str]
) -> None:
    folder, root = fake_scoring("apoe.domtblout")

    status = main(["hmmscore", "score", str(APOE_FASTA), "--json", "--data-dir", str(root)])

    result = json.loads(capsys.readouterr().out)
    assert status == 0
    assert list(result) == ["hit"]
    assert list(result["hit"]) == ["panther_id", "name", "evalue", "score", "alignment"]
    assert result["hit"]["panther_id"] == "PTHR18976:SF2"
    assert result["hit"]["name"] == "APOLIPOPROTEIN E"
    assert result["hit"]["alignment"].startswith(">> sequence  \n")
    # Normalised as the API normalises it.
    assert (folder / "query.fasta").read_text() == f">sequence\n{APOE}"


def test_score_reads_standard_input(
    fake_scoring: Callable[[str], tuple[Path, Path]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    folder, root = fake_scoring("apoe.domtblout")
    monkeypatch.setattr("sys.stdin", io.StringIO("  mkvlwaall\n  tfla \n"))

    status = main(["hmmscore", "score", "--data-dir", str(root)])

    assert status == 0
    assert (folder / "query.fasta").read_text() == ">sequence\nMKVLWAALLTFLA"
    assert capsys.readouterr().out.startswith("panther_id\tPTHR18976:SF2\n")


def test_score_says_no_hit(
    fake_scoring: Callable[[str], tuple[Path, Path]], capsys: pytest.CaptureFixture[str]
) -> None:
    _, root = fake_scoring("empty.domtblout")

    status = main(["hmmscore", "score", str(APOE_FASTA), "--data-dir", str(root)])

    assert status == 0
    assert capsys.readouterr().out == "No hit\n"


def test_score_passes_the_thread_count(
    fake_scoring: Callable[[str], tuple[Path, Path]], capsys: pytest.CaptureFixture[str]
) -> None:
    folder, root = fake_scoring("apoe.domtblout")

    status = main(["hmmscore", "score", str(APOE_FASTA), "--cpu", "3", "--data-dir", str(root)])

    assert status == 0
    assert recorded(folder, "hmmscan")[2:4] == ["--cpu", "3"]
    assert recorded(folder, "hmmsearch")[0:2] == ["--cpu", "3"]


def test_score_applies_the_time_limit(
    make_tool: Callable[[str, str], Path],
    fake_scoring: Callable[[str], tuple[Path, Path]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, root = fake_scoring("apoe.domtblout")
    make_tool("hmmscan", "exec sleep 5")

    status = main(
        ["hmmscore", "score", str(APOE_FASTA), "--timeout", "0.2", "--data-dir", str(root)]
    )

    captured = capsys.readouterr()
    assert status == 1
    assert captured.err == (
        "panther-engine hmmscore score: The search took longer than this service allows. "
        "Try a shorter sequence.\n"
    )


def test_score_reports_its_usage(
    fake_scoring: Callable[[str], tuple[Path, Path]], capsys: pytest.CaptureFixture[str]
) -> None:
    _, root = fake_scoring("apoe.domtblout")

    status = main(["hmmscore", "score", str(APOE_FASTA), "--usage", "--data-dir", str(root)])

    captured = capsys.readouterr()
    assert status == 0
    assert captured.out.startswith("panther_id\t")
    assert re.fullmatch(
        r"wall time: [0-9]+\.[0-9] s\npeak memory of the tools: [0-9,]+ MiB\n", captured.err
    )


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (">q\nMKVL1\n", "upper-case letters"),
        (">a\nMKVL\n>b\nWAAL\n", "more than one sequence"),
        (">q\n", "no sequence"),
    ],
)
def test_score_refuses_a_sequence_the_api_would(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str, message: str
) -> None:
    fasta = tmp_path / "query.fasta"
    fasta.write_text(text, encoding="ascii")

    status = main(["hmmscore", "score", str(fasta), "--data-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert captured.err.startswith("panther-engine hmmscore score: ")
    assert message in captured.err


def test_score_names_missing_data(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    status = main(["hmmscore", "score", str(APOE_FASTA), "--data-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert status == 1
    assert captured.err.startswith("panther-engine hmmscore score: the hmmscore data folder ")
    assert "globals/names.tab" in captured.err
