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


# score

GOLDEN = Path(__file__).parent / "golden" / "csnp"


def p26439(tmp_path: Path) -> Path:
    """P26439 alone, from the release's sample.fasta, as a user would save it: a header line and
    the sequence in lines of 60, in lower case."""
    sequence = (GOLDEN / "release" / "sample.fasta").read_text().split(">")[1].split("\n", 1)[1]
    residues = "".join(sequence.split()).lower()
    lines = [residues[start : start + 60] for start in range(0, len(residues), 60)]
    path = tmp_path / "P26439.fasta"
    path.write_text(">sp|P26439|3BHS2_HUMAN\n" + "\n".join(lines) + "\n")
    return path


@pytest.mark.tools("blastp")
@pytest.mark.data("csnp")
def test_score_prints_the_family_and_each_score(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = main(["csnp", "score", str(p26439(tmp_path)), "--species", "HUMAN", "a10e", "G15D"])

    assert status == 0
    assert capsys.readouterr().out.splitlines() == [
        "family\tPTHR10366",
        "substitution\tage\tmessage\tpdel",
        "A10E\t220\tpossibly damaging\t0.50",
        "G15D\t4200\tprobably damaging\t0.95",
    ]


@pytest.mark.tools("blastp")
@pytest.mark.data("csnp")
def test_score_prints_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    status = main(["csnp", "score", str(p26439(tmp_path)), "--species", "HUMAN", "M1V", "--json"])

    assert status == 0
    assert json.loads(capsys.readouterr().out) == {
        "family": "PTHR10366",
        "scores": [
            {
                "substitution": "M1V",
                "age": None,
                "message": "Not scored: Invalid substitution",
                "pdel": None,
            }
        ],
    }


def test_score_refuses_more_than_one_sequence_and_scores_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # No blastp and no data: scoring would fail differently.
    monkeypatch.setenv("PATH", str(tmp_path))
    fasta = tmp_path / "two.fasta"
    fasta.write_text(">one\nMKVL\n>two\nMKVL\n")

    status = main(["csnp", "score", str(fasta), "--species", "HUMAN", "K2E"])

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert "more than one" in captured.err


@pytest.mark.parametrize(
    ("args", "error"),
    [
        (["--species", "HUMAN", "2KE"], "substitution"),
        (["--species", "XXXXX", "K2E"], "species"),
    ],
)
def test_score_refuses_a_bad_substitution_or_species(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    args: list[str],
    error: str,
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    fasta = tmp_path / "one.fasta"
    fasta.write_text(">one\nMKVL\n")

    status = main(["csnp", "score", str(fasta), *args])

    assert status == 1
    assert error in capsys.readouterr().err


def test_score_help_lists_the_options(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["csnp", "score", "--help"])

    out = capsys.readouterr().out
    for option in ("FASTA", "--species", "SUBSTITUTION", "--data-dir", "--json"):
        assert option in out
