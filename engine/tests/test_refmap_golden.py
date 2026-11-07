"""The port against `map_panther.pl`'s output for each golden case (tests/golden/refmap/).

The made-up files and the divergence cases need no data. The cases on ENDPU need the refmap data.
"""

import json
import shutil
from pathlib import Path

import pytest

from panther_engine.cli import main
from panther_engine.refmap import parity
from panther_engine.refmap.mapping import read_id_list
from panther_engine.refmap.organisms import CLASSIFICATION

GOLDEN = Path(__file__).parent / "golden" / "refmap"
CASES = parity.read_cases(GOLDEN)
WITHOUT_DATA = [case for case in CASES if case.file is not None or case.refused is not None]
ON_DATA = [case for case in CASES if case.file is None and case.refused is None]


def name(case: parity.Case) -> str:
    return case.name


def test_every_case_has_its_output() -> None:
    assert sorted(path.name for path in (GOLDEN / "out").iterdir()) == sorted(
        f"{case.name}.out" for case in CASES
    )


@pytest.mark.parametrize("case", WITHOUT_DATA, ids=name)
def test_made_up_and_divergence_cases(case: parity.Case, tmp_path: Path) -> None:
    assert parity.check_case(case, GOLDEN, tmp_path / "no-data") == []


@pytest.mark.data("refmap")
@pytest.mark.parametrize("case", ON_DATA, ids=name)
def test_cases_on_the_pinned_data(case: parity.Case, refmap_data: Path) -> None:
    assert parity.check_case(case, GOLDEN, refmap_data.parents[1]) == []


@pytest.mark.data("refmap")
def test_the_release_lists_cover_every_endpu_id(refmap_data: Path) -> None:
    ids = parity.file_ids(refmap_data / CLASSIFICATION / "ENDPU")
    listed = read_id_list((GOLDEN / "release" / "test_geneList_values").read_bytes())

    assert sorted(listed) == sorted(ids)
    assert len(read_id_list((GOLDEN / "release" / "test_geneList").read_bytes())) == 450


@pytest.fixture
def copy(tmp_path: Path) -> Path:
    folder = tmp_path / "golden"
    shutil.copytree(GOLDEN, folder)
    return folder


def test_a_changed_golden_line_is_one_difference_naming_the_case_and_the_line(
    copy: Path, tmp_path: Path
) -> None:
    out = copy / "out" / "repeated-id.out"
    out.write_bytes(out.read_bytes().replace(b"A1\tPTHR00002", b"A1\tPTHR00009"))
    case = next(case for case in parity.read_cases(copy) if case.name == "repeated-id")

    differences = parity.check_case(case, copy, tmp_path / "no-data")

    assert differences == [
        "repeated-id line 1: the reference has 'A1\\tPTHR00009', the port 'A1\\tPTHR00002'"
    ]


def test_a_refused_case_the_port_maps_is_a_difference(copy: Path, tmp_path: Path) -> None:
    listed = json.loads((copy / "cases.json").read_text())
    for item in listed["cases"]:
        if item["name"] == "stored-nohit":
            item.update(refused="ValueError", message="ID 1", divergence=10)
    (copy / "cases.json").write_text(json.dumps(listed))
    case = next(case for case in parity.read_cases(copy) if case.name == "stored-nohit")

    assert parity.check_case(case, copy, tmp_path / "no-data") == [
        "stored-nohit: the port mapped the IDs, but divergence 10 has it raise ValueError"
    ]


def test_a_case_refused_for_another_reason_is_a_difference(copy: Path, tmp_path: Path) -> None:
    listed = json.loads((copy / "cases.json").read_text())
    for item in listed["cases"]:
        if item["name"] == "empty-line":
            item["message"] = "not an organism refmap maps for"
    (copy / "cases.json").write_text(json.dumps(listed))
    case = next(case for case in parity.read_cases(copy) if case.name == "empty-line")

    assert parity.check_case(case, copy, tmp_path / "no-data") == [
        "empty-line: the port raised ValueError (ID 2 isn't 1 to 64 printable ASCII characters "
        "with no whitespace: ''), not ValueError with 'not an organism refmap maps for'"
    ]


def test_parity_check_reports_the_difference_and_fails(
    copy: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    listed = json.loads((copy / "cases.json").read_text())
    listed["cases"] = [item for item in listed["cases"] if "file" in item]
    (copy / "cases.json").write_text(json.dumps(listed))
    out = copy / "out" / "crlf.out"
    out.write_bytes(out.read_bytes().replace(b"B2\tPTHR00002:SF1\r", b"B2\tPTHR00002:SF1"))

    status = main(["refmap", "parity", "check", "--golden", str(copy), "--data-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert status == 1
    assert "crlf line 2: the reference has 'B2\\tPTHR00002:SF1', the port" in captured.out
    assert "repeated-id: 2 lines, 0 differences" in captured.out
    assert "1 differences" in captured.err


def test_parity_check_without_a_data_folder_still_checks_what_needs_none(
    copy: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PANTHER_DATA_DIR", raising=False)

    status = main(["refmap", "parity", "check", "--golden", str(copy)])

    captured = capsys.readouterr()
    assert status == 1
    assert "crlf: 4 lines, 0 differences" in captured.out
    assert (
        "empty-line: refused (ValueError: \"ID 2 isn't 1 to 64 printable ASCII characters with no "
        'whitespace"), 0 differences' in captured.out
    )
    assert (
        "unknown-organism: refused (ValueError: \"not an organism refmap maps for: 'HUMAN'\"), "
        "0 differences" in captured.out
    )
    assert "test_geneList: not checked: it needs the refmap data" in captured.out
    assert f"{len(ON_DATA)} cases not checked" in captured.err
    assert "PANTHER_DATA_DIR" in captured.err
    assert "Traceback" not in captured.err


def test_parity_check_of_cases_that_need_no_data_passes_without_it(
    copy: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PANTHER_DATA_DIR", raising=False)
    listed = json.loads((copy / "cases.json").read_text())
    listed["cases"] = [item for item in listed["cases"] if "file" in item or "refused" in item]
    (copy / "cases.json").write_text(json.dumps(listed))

    assert main(["refmap", "parity", "check", "--golden", str(copy)]) == 0
    assert "not checked" not in capsys.readouterr().out
