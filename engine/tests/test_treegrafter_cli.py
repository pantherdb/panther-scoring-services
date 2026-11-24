import json
from pathlib import Path

import pytest

from panther_engine.cli import main
from panther_engine.treegrafter import data as treegrafter_data

FIXTURE = Path(__file__).parent / "fixtures" / "treegrafter"
EXAMPLE = Path(__file__).parent / "golden" / "treegrafter" / "example" / "apoe.fasta"
APOE_GO = (
    "GO:0005543,GO:0008203,GO:0033344,GO:0033700,GO:0034361,GO:0034362,GO:0034364,GO:0042627,"
    "GO:0055090,GO:0060228,GO:0120020,GO:1903561"
)


@pytest.fixture(scope="module")
def folder(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The treegrafter fixture, prepared once, with release 2026-08-28 active."""
    prepared = tmp_path_factory.mktemp("prepared")
    treegrafter_data.install_fixture(FIXTURE, prepared)
    return prepared


def graft(folder: Path, *args: str) -> int:
    return main(["treegrafter", "score", *args, "--data-dir", str(folder)])


@pytest.mark.tools("hmmsearch", "epa-ng")
def test_the_example_prints_the_hits_fields(
    folder: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = graft(folder, str(EXAMPLE))

    out = capsys.readouterr().out
    fields = dict(line.split("\t") for line in out.splitlines())
    assert status == 0
    assert fields == {
        "panther_id": "PTHR18976:SF2",
        "node_id": "AN163",
        "graft_point": "PTN002498710",
        "go_terms": APOE_GO,
        "protein_class": "PC00052",
        "score": "172.6",
        "evalue": "5.7e-47",
        "domain_score": "172.4",
        "domain_evalue": "6.8e-47",
        "hmm_from": "11",
        "hmm_to": "359",
        "ali_from": "1",
        "ali_to": "306",
        "env_from": "1",
        "env_to": "311",
        "annotations": "2026-08-28",
    }


@pytest.mark.tools("hmmsearch", "epa-ng")
def test_json_prints_one_object_with_the_release_and_the_hit(
    folder: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = graft(folder, str(EXAMPLE), "--json")

    printed = json.loads(capsys.readouterr().out)
    assert status == 0
    assert printed["annotations"] == "2026-08-28"
    assert printed["hit"]["panther_id"] == "PTHR18976:SF2"
    assert printed["hit"]["go_terms"] == APOE_GO.split(",")
    assert printed["hit"]["hmm_from"] == 11


def test_a_refused_sequence_is_an_error_on_standard_error(
    folder: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fasta = tmp_path / "tilde.fasta"
    fasta.write_text(">tilde\nMKVLW~AALL\n")

    status = graft(folder, str(fasta))

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert captured.err.startswith("panther-engine treegrafter score: ")


def test_standard_input_is_read_for_a_dash(
    folder: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(">x\nmkvl-aa\n"))

    assert graft(folder, "-") == 1
    assert "'.', '_' and '*'" in capsys.readouterr().err


def test_missing_data_is_an_error_naming_what_s_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert graft(tmp_path, str(EXAMPLE)) == 1
    assert "lacks: famhmm/binHmm" in capsys.readouterr().err
