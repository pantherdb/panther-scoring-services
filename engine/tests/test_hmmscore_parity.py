"""Parity with the legacy CGI and `pantherScore.pl`: the goldens in tests/golden/hmmscore/parity/,
how a case's expected result comes from the reference's files, and the reference's commands,
tested without Perl."""

import json
import re
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from hmmscore_fixtures import TABLES, install_fake_hmmer, scoring_folder

from panther_engine.hmmscore import HmmHit, HmmscoreResult, parity
from panther_engine.hmmscore.scoring import alignment

GOLDEN = Path(__file__).parent / "golden" / "hmmscore" / "parity"
CASES = parity.read_cases(GOLDEN)
REPORT = (TABLES / "apoe.hmmsearch").read_bytes()
ALIGNMENT = alignment(REPORT)


def escaped(text: str) -> str:
    return text.replace(">", "&gt;").replace("<", "&lt;")


def write_case(
    folder: Path, best: str, cgi: str | None = None, reports: tuple[str, ...] = ()
) -> Path:
    """A made-up case folder: `best.tsv`, `cgi.xml`, and the saved APOE report for each ID in
    `reports`."""
    (folder / parity.HMMSEARCH).mkdir(parents=True)
    (folder / parity.BEST).write_text(best, encoding="latin-1")
    if cgi is not None:
        (folder / parity.CGI_XML).write_text(cgi, encoding="latin-1")
    for panther_id in reports:
        (folder / parity.HMMSEARCH / parity.report_name(panther_id)).write_bytes(REPORT)
    return folder


def cgi_xml(panther_id: str, evalue: str) -> str:
    return (
        f"<scores>\n  <id>{panther_id}</id>\n  <eval>{evalue}</eval>\n  <align>\n"
        f"{escaped(ALIGNMENT)}  </align>\n</scores>\n"
    )


APOE_LINE = "sequence\tPTHR18976:SF2\tAPOLIPOPROTEIN E\t2.2e-133\t439.0\t1-309\n"
TIE = (
    "sequence\tPTHR35774\tFAMILY 35774\t4.1e-60\t200.3\t1-34\n"
    "sequence\tPTHR35774:SF1\tSUBFAMILY 35774:SF1\t4.1e-60\t200.3\t1-34\n"
)


# The goldens


def test_cases_json_lists_every_input() -> None:
    listed = {f"{case.name}.txt" for case in CASES}

    assert listed == {path.name for path in (GOLDEN / parity.INPUTS).iterdir()}


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_each_input_holds_only_what_the_api_sends(case: parity.Case) -> None:
    sequence = case.sequence(GOLDEN)

    assert re.fullmatch(r"[A-Z._~*]*[A-Z][A-Z._~*]*", sequence)
    assert len(sequence.removesuffix("*")) <= 10_000


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_each_sample_golden_agrees_with_itself(case: parity.Case) -> None:
    folder = GOLDEN / "sample" / case.name

    assert parity.cross_check(case.name, folder) == []


@pytest.mark.tools("hmmscan", "hmmsearch")
@pytest.mark.data("hmmscore")
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.name)
def test_each_sample_case_gives_its_golden_result(case: parity.Case, hmmscore_data: Path) -> None:
    checked = parity.check_case(case, GOLDEN, "sample", hmmscore_data.parents[1])

    assert checked.differences == ()


# The expected result


def test_the_expected_hit_is_best_tsvs_line_with_its_report(tmp_path: Path) -> None:
    folder = write_case(tmp_path / "apoe", APOE_LINE, reports=("PTHR18976:SF2",))

    assert parity.expected(folder) == HmmscoreResult(
        HmmHit("PTHR18976:SF2", "APOLIPOPROTEIN E", "2.2e-133", "439.0", ALIGNMENT)
    )


def test_an_empty_best_tsv_is_no_hit(tmp_path: Path) -> None:
    assert parity.expected(write_case(tmp_path / "none", "")) == HmmscoreResult(None)


def test_divergence_13_picks_among_the_tied_lines(tmp_path: Path) -> None:
    folder = write_case(tmp_path / "tie", TIE, reports=("PTHR35774", "PTHR35774:SF1"))

    hit = parity.expected(folder).hit

    assert hit is not None
    assert (hit.panther_id, hit.name) == ("PTHR35774:SF1", "SUBFAMILY 35774:SF1")


def test_an_empty_name_is_no_name(tmp_path: Path) -> None:
    line = APOE_LINE.replace("APOLIPOPROTEIN E", "")
    folder = write_case(tmp_path / "apoe", line, reports=("PTHR18976:SF2",))

    hit = parity.expected(folder).hit

    assert hit is not None
    assert hit.name == "No name"


def test_tied_lines_must_share_their_numbers(tmp_path: Path) -> None:
    best = TIE.replace("4.1e-60\t200.3\t1-34\n", "4.2e-60\t200.3\t1-34\n", 1)
    folder = write_case(tmp_path / "tie", best, reports=("PTHR35774", "PTHR35774:SF1"))

    with pytest.raises(parity.ParityError, match="E-value and score"):
        parity.expected(folder)


def test_a_missing_report_is_an_error(tmp_path: Path) -> None:
    folder = write_case(tmp_path / "apoe", APOE_LINE)

    with pytest.raises(parity.ParityError, match=r"PTHR18976\.SF2\.out"):
        parity.expected(folder)


def test_missing_outputs_are_an_error(tmp_path: Path) -> None:
    with pytest.raises(parity.ParityError, match="no reference outputs"):
        parity.expected(tmp_path / "missing")


# The cross-checks


def test_a_cgi_xml_that_agrees_passes(tmp_path: Path) -> None:
    folder = write_case(
        tmp_path / "apoe",
        APOE_LINE,
        cgi_xml("PTHR18976:SF2", "2.2e-133"),
        reports=("PTHR18976:SF2",),
    )

    assert parity.cross_check("apoe", folder) == []


def test_the_cgi_may_show_any_tied_id(tmp_path: Path) -> None:
    folder = write_case(
        tmp_path / "tie",
        TIE,
        cgi_xml("PTHR35774", "4.1e-60"),
        reports=("PTHR35774", "PTHR35774:SF1"),
    )

    assert parity.cross_check("tie", folder) == []


@pytest.mark.parametrize(
    ("cgi", "found"),
    [
        (cgi_xml("PTHR18976:SF1", "2.2e-133"), "isn't among best.tsv's"),
        (cgi_xml("PTHR18976:SF2", "2.3e-133"), "isn't among best.tsv's"),
        (cgi_xml("PTHR18976:SF2", "2.2e-133").replace("&gt;", ">"), "doesn't match"),
        ("<scores>\n</scores>\n", "isn't among best.tsv's"),
    ],
)
def test_a_cgi_xml_that_disagrees_is_named(tmp_path: Path, cgi: str, found: str) -> None:
    folder = write_case(tmp_path / "apoe", APOE_LINE, cgi, reports=("PTHR18976:SF2",))

    differences = parity.cross_check("apoe", folder)

    assert len(differences) == 1
    assert differences[0].startswith("apoe: ")
    assert found in differences[0]


def test_no_hit_needs_an_empty_scores(tmp_path: Path) -> None:
    good = write_case(tmp_path / "good", "", "<scores>\n</scores>\n")
    bad = write_case(tmp_path / "bad", "", cgi_xml("PTHR18976:SF2", "2.2e-133"))

    assert parity.cross_check("good", good) == []
    assert parity.cross_check("bad", bad) == [
        "bad: best.tsv is empty, but cgi.xml isn't an empty <scores>"
    ]


# The check


@pytest.fixture
def made_up_golden(
    make_tool: Callable[[str, str], Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    """A golden folder with one case, `apoe`, whose goldens agree with fake HMMER, and a data
    folder for it. Returns both."""
    folder = tmp_path / "bin"
    monkeypatch.setenv("PATH", f"{folder}:/usr/bin:/bin")
    install_fake_hmmer(make_tool, folder, "apoe.domtblout")
    data = scoring_folder(
        tmp_path / "data",
        models=("books/PTHR18976/SF2/hmmer.hmm",),
        names="PTHR18976.SF2.mod\tAPOLIPOPROTEIN E\n",
    )
    golden = tmp_path / "golden"
    (golden / parity.INPUTS).mkdir(parents=True)
    shutil.copyfile(GOLDEN / parity.INPUTS / "apoe.txt", golden / parity.INPUTS / "apoe.txt")
    (golden / parity.CASES).write_text(
        json.dumps({"cases": [{"name": "apoe", "why": "The example"}]}), encoding="utf-8"
    )
    write_case(
        golden / "sample" / "apoe",
        APOE_LINE,
        cgi_xml("PTHR18976:SF2", "2.2e-133"),
        reports=("PTHR18976:SF2",),
    )
    return golden, data


def test_the_check_passes_when_the_port_agrees(made_up_golden: tuple[Path, Path]) -> None:
    golden, data = made_up_golden
    (case,) = parity.read_cases(golden)

    checked = parity.check_case(case, golden, "sample", data)

    assert checked.differences == ()
    assert checked.seconds >= 0


def test_a_hand_changed_e_value_fails_naming_the_case(made_up_golden: tuple[Path, Path]) -> None:
    golden, data = made_up_golden
    best = golden / "sample" / "apoe" / parity.BEST
    best.write_text(APOE_LINE.replace("2.2e-133", "2.3e-133"), encoding="latin-1")
    (case,) = parity.read_cases(golden)

    checked = parity.check_case(case, golden, "sample", data)

    assert "apoe: the reference's evalue is '2.3e-133', the port's '2.2e-133'" in (
        checked.differences
    )


def test_a_case_without_outputs_fails_naming_it(made_up_golden: tuple[Path, Path]) -> None:
    golden, data = made_up_golden
    (case,) = parity.read_cases(golden)

    checked = parity.check_case(case, golden, "full", data)

    assert len(checked.differences) == 1
    assert checked.differences[0].startswith("apoe: no reference outputs")


def test_an_arm64_copy_replaces_the_expected_result_on_arm64(
    made_up_golden: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    golden, data = made_up_golden
    (golden / "sample-arm64").mkdir()
    hit = parity.expected(golden / "sample" / "apoe").hit
    assert hit is not None
    arm64 = HmmscoreResult(HmmHit(hit.panther_id, hit.name, "9.9e-133", hit.score, hit.alignment))
    parity.write_result(golden / "sample-arm64" / "apoe.json", arm64)
    (case,) = parity.read_cases(golden)

    monkeypatch.setattr(parity, "architecture", lambda: "arm64")
    on_arm64 = parity.check_case(case, golden, "sample", data)
    monkeypatch.setattr(parity, "architecture", lambda: "amd64")
    on_amd64 = parity.check_case(case, golden, "sample", data)

    assert on_arm64.differences == (
        "apoe: the reference's evalue is '9.9e-133', the port's '2.2e-133'",
    )
    assert on_amd64.differences == ()


# The reference's commands, without Perl


def test_the_cgis_config(tmp_path: Path) -> None:
    text = parity.config_yaml(
        data=Path("/data/hmmscore/19"),
        library=Path("/work/run/presses"),
        tmp=Path("/work/run/apoe/tmp"),
        hmmer=Path("/opt/hmmer-3.1b2/bin"),
    )

    # Double-quoted, as JSON writes strings: YAML reads them so, whatever the path holds.
    assert text == (
        'library_directory: "/data/hmmscore/19"\n'
        'binHmm_library_directory: "/work/run/presses"\n'
        'tmp_directory: "/work/run/apoe/tmp"\n'
        'hmmer_bin_directory: "/opt/hmmer-3.1b2/bin"\n'
    )


def test_the_cgis_environment_and_body() -> None:
    body = parity.cgi_body("MKVL*")

    assert body == "sequence=MKVL*"
    assert parity.cgi_environment(body) == {"REQUEST_METHOD": "POST", "CONTENT_LENGTH": "14"}


def test_pantherscore_runs_as_the_cgi_runs_it_with_names() -> None:
    arguments = parity.score_arguments(
        library=Path("/work/run/presses"),
        query=Path("query.fasta"),
        out=Path("/work/out/best.tsv"),
        hmmer=Path("/opt/hmmer-3.1b2/bin"),
    )

    assert arguments == [
        "pantherScore.pl",
        "-l",
        "/work/run/presses",
        "-D",
        "B",
        "-n",
        "-i",
        "query.fasta",
        "-o",
        "/work/out/best.tsv",
        "-H",
        "/opt/hmmer-3.1b2/bin",
    ]


def test_a_report_is_named_without_a_colon() -> None:
    assert parity.report_name("PTHR18976:SF2") == "PTHR18976.SF2.out"
    assert parity.report_name("PTHR34093") == "PTHR34093.out"


def test_the_self_check_wants_the_example_at_439_bits() -> None:
    assert parity.self_check_problem(APOE_LINE) is None
    assert parity.self_check_problem(APOE_LINE.replace("439.0", "438.9")) is not None
    assert parity.self_check_problem("") is not None
