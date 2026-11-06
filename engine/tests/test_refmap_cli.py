import json
from pathlib import Path

import pytest

from panther_engine.cli import main
from panther_engine.refmap import parity

GOLDEN = Path(__file__).parent / "golden" / "refmap"


@pytest.mark.data("refmap")
def test_a_file_of_ids_prints_the_goldens_first_two_fields(
    refmap_data: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = main(
        [
            "refmap",
            "map",
            "--organism",
            "ENDPU",
            "--file",
            str(GOLDEN / "release" / "test_geneList"),
            "--data-dir",
            str(refmap_data.parents[1]),
        ]
    )

    captured = capsys.readouterr()
    assert status == 0
    expected = parity.golden_lines(GOLDEN / "out" / "test_geneList.out")
    assert captured.out.splitlines() == expected
    assert len(expected) == 450
    assert captured.err == ""


@pytest.mark.data("refmap")
def test_json_prints_the_result(refmap_data: Path, capsys: pytest.CaptureFixture[str]) -> None:
    status = main(
        [
            "refmap",
            "map",
            "U1G4Q5",
            "U1HQ27",
            "U1G4Q5",
            "--organism",
            "ENDPU",
            "--json",
            "--data-dir",
            str(refmap_data.parents[1]),
        ]
    )

    assert status == 0
    assert json.loads(capsys.readouterr().out) == {
        "organism": "ENDPU",
        "mappings": [
            {"id": "U1G4Q5", "panther_id": "PTHR11360:SF130"},
            {"id": "U1HQ27", "panther_id": None},
            {"id": "U1G4Q5", "panther_id": "PTHR11360:SF130"},
        ],
    }


def test_ids_on_the_command_line_print_one_line_each(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = tmp_path / "refmap" / "19" / "panther_classification"
    folder.mkdir(parents=True)
    (folder / "PEA").write_bytes(b"P1\tPTHR00002:SF3\nP2\tNOHIT\nP3\t\n")

    status = main(
        ["refmap", "map", "P1", "P2", "P3", "P4", "--organism", "PEA", "--data-dir", str(tmp_path)]
    )

    assert status == 0
    assert capsys.readouterr().out == "P1\tPTHR00002:SF3\nP2\tNOHIT\nP3\t\nP4\tNOHIT\n"


def test_an_organism_refmap_doesnt_publish_fails_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = main(["refmap", "map", "P04217", "--organism", "HUMAN", "--data-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert captured.err.startswith("panther-engine refmap map: ")
    assert "'HUMAN'" in captured.err


def test_without_a_data_folder_it_fails_with_the_message_and_no_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PANTHER_DATA_DIR", raising=False)

    status = main(["refmap", "map", "U1G4Q5", "--organism", "ENDPU"])

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert "PANTHER_DATA_DIR" in captured.err
    assert "Traceback" not in captured.err


def test_a_missing_classification_file_fails_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = main(["refmap", "map", "U1G4Q5", "--organism", "ENDPU", "--data-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert status == 1
    assert captured.out == ""
    assert "refmap/19/panther_classification/ENDPU" in captured.err


def test_a_missing_list_file_fails_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "ids.txt"

    status = main(["refmap", "map", "--organism", "ENDPU", "--file", str(missing)])

    assert status == 1
    assert str(missing) in capsys.readouterr().err


@pytest.mark.parametrize("args", [[], ["U1G4Q5", "--file", "ids.txt"]])
def test_ids_come_from_the_arguments_or_a_file_not_both(
    args: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["refmap", "map", "--organism", "ENDPU", *args])

    assert raised.value.code == 2
    assert "--file" in capsys.readouterr().err


def test_help_lists_the_options(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["refmap", "map", "--help"])

    out = capsys.readouterr().out
    assert raised.value.code == 0
    for option in ("--organism", "--file", "--data-dir", "--json", "ID"):
        assert option in out
