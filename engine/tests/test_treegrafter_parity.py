import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from panther_engine.cli import main
from panther_engine.treegrafter import parity
from panther_engine.treegrafter.scoring import check_sequence

GOLDEN = Path(__file__).parent / "golden" / "treegrafter"
FIXTURE = Path(__file__).parent / "fixtures" / "treegrafter"


# The cases


def test_cases_json_lists_every_input_and_only_those() -> None:
    names = {case.name for case in parity.read_cases(GOLDEN)}

    assert names == {path.stem for path in (GOLDEN / "inputs").glob("*.txt")}


@pytest.mark.parametrize("case", [case.name for case in parity.read_cases(GOLDEN)])
def test_every_input_holds_only_what_the_engine_takes(case: str) -> None:
    check_sequence(parity.sequence_of(GOLDEN, case))


def test_the_full_library_set_lists_its_inputs_and_the_engine_takes_each() -> None:
    library = GOLDEN / "library"
    cases = parity.read_cases(library)

    assert {case.name for case in cases} == {
        path.stem for path in (library / "inputs").glob("*.txt")
    }
    for case in cases:
        check_sequence(parity.sequence_of(library, case.name))


def test_every_case_has_a_golden_made_on_the_fixture() -> None:
    for case in parity.read_cases(GOLDEN):
        assert (GOLDEN / "parity" / "fixture" / case.name / "result.tsv").is_file(), case.name


# The reference run, with fake tools

RECORD = 'printf "%s\\0" "$@" > "$(dirname "$0")/{name}.argv"'


def test_the_reference_runs_hmmsearch_then_ebis_run_with_treegrafter_shs_options(
    make_tool: Callable[[str, str], Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hmmsearch = make_tool("hmmsearch", RECORD.format(name="hmmsearch") + "; echo report")
    # EBI's run writes its output to the file after -o.
    treegrafter = make_tool(
        "treegrafter",
        RECORD.format(name="treegrafter")
        + '\nwhile [ $# -gt 0 ]; do [ "$1" = "-o" ] && printf "query_id\\n" > "$2"; shift; done',
    )
    monkeypatch.setenv("PATH", f"{hmmsearch.parent}:/usr/bin:/bin")
    monkeypatch.setattr(parity, "console_script", lambda: treegrafter)
    golden = tmp_path / "golden"
    shutil.copytree(GOLDEN, golden, ignore=shutil.ignore_patterns("parity"))

    names = parity.run_reference(golden, "fixture", None, ["apoe"], fixture=FIXTURE)

    assert names == ["apoe"]
    search = (hmmsearch.parent / "hmmsearch.argv").read_bytes().decode().split("\0")[:-1]
    assert search[:9] == [
        "-Z",
        "65000000",
        "-E",
        "0.001",
        "--domE",
        "0.00000001",
        "--incdomE",
        "0.00000001",
        "--notextw",
    ]
    assert search[9].endswith("treegrafter/19/famhmm/binHmm")
    assert Path(search[10]).name == "query.fasta"
    run = (hmmsearch.parent / "treegrafter.argv").read_bytes().decode().split("\0")[:-1]
    assert run[:4] == ["run", "-e", "0.00000001", "--print-go"]
    assert run[run.index("-d") + 1].endswith("treegrafter/19")
    assert run[run.index("-a") + 1].endswith("treegrafter/19/annotations/2026-08-28")
    assert [Path(path).name for path in run[-2:]] == ["query.fasta", "hmmsearch.out"]
    written = (
        golden / "parity" / ("fixture" if parity.architecture() == "amd64" else "fixture-arm64")
    )
    assert (written / "apoe" / "result.tsv").read_text() == "query_id\n"


# The check


def check(golden: Path, *cases: str) -> int:
    args = ["treegrafter", "parity", "check", "--golden", str(golden), "--fixture", str(FIXTURE)]
    return main([*args, *(f"--case={case}" for case in cases)])


@pytest.mark.tools("hmmsearch", "epa-ng")
def test_every_fixture_case_equals_its_golden(capsys: pytest.CaptureFixture[str]) -> None:
    status = check(GOLDEN)

    out = capsys.readouterr().out
    assert status == 0, out
    assert "12 of 12 cases match" in out


@pytest.mark.tools("hmmsearch", "epa-ng")
def test_a_hand_changed_graft_node_fails_and_names_the_case(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    golden = tmp_path / "golden"
    shutil.copytree(GOLDEN, golden)
    result = golden / "parity" / "fixture" / "apoe" / "result.tsv"
    result.write_text(result.read_text().replace("\tAN163\t", "\tAN162\t"))

    status = check(golden, "apoe")

    out = capsys.readouterr().out
    assert status == 1
    assert "apoe:" in out
    assert "node_id: the engine's 'AN163', the reference's 'AN162'" in out


def test_a_case_with_no_reference_output_is_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    golden = tmp_path / "golden"
    shutil.copytree(GOLDEN, golden)
    shutil.rmtree(golden / "parity" / "fixture" / "random300")

    status = check(golden, "random300")

    out = capsys.readouterr().out
    assert status == 1
    assert "random300" in out and "no reference output" in out


def test_an_unknown_case_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    assert check(GOLDEN, "nothing") == 1
    assert "no such case: nothing" in capsys.readouterr().err


def test_ebis_rows_map_as_the_engines_do() -> None:
    hit = parity.expected_hit(GOLDEN / "parity" / "fixture" / "pthr11034" / "result.tsv")

    assert hit is not None
    assert (hit.panther_id, hit.node_id, hit.go_terms, hit.protein_class) == (
        "PTHR11034",
        None,
        (),
        None,
    )
    assert parity.expected_hit(GOLDEN / "parity" / "fixture" / "random300" / "result.tsv") is None
