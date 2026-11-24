"""Grafting with fake tools: saved `hmmsearch` reports and EPA-ng placements, from
fixtures/treegrafter-scoring/, against the treegrafter fixture prepared in a temporary data folder.
EBI's own functions run for real."""

import json
import logging
import os
import pickle
import re
import shutil
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from panther_engine.core.errors import InputError
from panther_engine.treegrafter import (
    DATA_VERSION,
    TimeLimitError,
    TreegrafterError,
    TreegrafterHit,
    TreegrafterInput,
    TreegrafterResult,
    annotations,
    score,
)
from panther_engine.treegrafter import data as treegrafter_data
from panther_engine.treegrafter.scoring import hit_from_row

FIXTURE = Path(__file__).parent / "fixtures" / "treegrafter"
SAVED = Path(__file__).parent / "fixtures" / "treegrafter-scoring"
RELEASE = "2026-08-28"
APOE = (Path(__file__).parent / "golden" / "hmmscore" / "example" / "apoe.fasta").read_text()
APOE_SEQUENCE = "".join(APOE.splitlines()[1:])
# APOE's hit against the fixture, as EBI's command line gives it: the row's fields, and the graft
# point from release 2026-08-28's entry for PTHR18976:AN163.
APOE_GO = [
    "GO:0005543",
    "GO:0008203",
    "GO:0033344",
    "GO:0033700",
    "GO:0034361",
    "GO:0034362",
    "GO:0034364",
    "GO:0042627",
    "GO:0055090",
    "GO:0060228",
    "GO:0120020",
    "GO:1903561",
]
APOE_HIT = TreegrafterHit(
    panther_id="PTHR18976:SF2",
    node_id="AN163",
    graft_point="PTN002498710",
    go_terms=tuple(APOE_GO),
    protein_class="PC00052",
    score="172.6",
    evalue="5.7e-47",
    domain_score="172.4",
    domain_evalue="6.8e-47",
    hmm_from=11,
    hmm_to=359,
    ali_from=1,
    ali_to=306,
    env_from=1,
    env_to=311,
)
SEARCH_OPTIONS = [
    "--cpu",
    "0",
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


def sections(report: str) -> dict[str, str]:
    """A report's family sections, from each `Query:` line to its `//` line, by family."""
    found = re.findall(r"^Query: +(PTHR[0-9]{5})\..*?^//\n", report, re.MULTILINE | re.DOTALL)
    bodies = re.findall(r"^Query: .*?^//\n", report, re.MULTILINE | re.DOTALL)
    return dict(zip(found, bodies, strict=True))


def saved(name: str) -> str:
    return (SAVED / name).read_text(encoding="ascii")


def header(report: str) -> str:
    return report[: report.index("Query:")]


def report_of(*families: tuple[str, str]) -> str:
    """A report of the named families' sections, from the named saved reports, in order."""
    text = header(saved("apoe.hmmsearch.out"))
    for family, name in families:
        text += sections(saved(name))[family]
    return text + "[ok]\n"


NO_HITS = report_of(("PTHR11034", "apoe.hmmsearch.out"))
# The fake hmmsearch prints NDRG1's saved report whatever the query: this stands in for NDRG1.
NDRG1_STANDIN = "MSREMQDVDL"


@pytest.fixture(scope="module")
def prepared(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The treegrafter fixture, prepared once, with release 2026-08-28 active."""
    folder = tmp_path_factory.mktemp("prepared")
    treegrafter_data.install_fixture(FIXTURE, folder)
    return folder


@pytest.fixture
def folder(prepared: Path, tmp_path: Path) -> Path:
    """A copy of the prepared fixture, for a test to change."""
    copy = tmp_path / "data"
    shutil.copytree(prepared, copy)
    return copy


class Tools:
    """Fake `hmmsearch` and `epa-ng`, first on PATH. `hmmsearch` prints `report`; `epa-ng`
    writes `jplace` into its `-w` folder as epa_result.jplace. Each records its arguments, and
    the folder it ran in, beside itself."""

    def __init__(self, make_tool: Callable[[str, str], Path], tmp_path: Path) -> None:
        self.make_tool = make_tool
        self.folder = tmp_path / "bin"
        self.report = tmp_path / "report.out"
        self.jplace = tmp_path / "placement.jplace"

    def hmmsearch(self, report: str, *, before: str = "") -> None:
        self.report.write_text(report, encoding="ascii")
        self.make_tool(
            "hmmsearch",
            'printf "%s\\0" "$@" > "$(dirname "$0")/hmmsearch.argv"; pwd > "$(dirname "$0")/'
            f'hmmsearch.pwd"; {before}\ncat "{self.report}"',
        )

    def epang(self, jplace: str | None, *, before: str = "", status: int = 0) -> None:
        if jplace is not None:
            self.jplace.write_text(jplace, encoding="ascii")
        copy = f'cp "{self.jplace}" "$out/epa_result.jplace"' if jplace is not None else ":"
        self.make_tool(
            "epa-ng",
            'printf "%s\\0" "$@" > "$(dirname "$0")/epa-ng.argv"\n'
            'out=""; while [ $# -gt 0 ]; do [ "$1" = "-w" ] && out="$2"; shift; done\n'
            f"{before}\n{copy}\nexit {status}",
        )

    def argv(self, name: str) -> list[str]:
        return (self.folder / f"{name}.argv").read_bytes().decode().split("\0")[:-1]

    def ran(self, name: str) -> bool:
        return (self.folder / f"{name}.argv").exists()


@pytest.fixture
def tools(
    make_tool: Callable[[str, str], Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Tools:
    fakes = Tools(make_tool, tmp_path)
    monkeypatch.setenv("PATH", f"{fakes.folder}:/usr/bin:/bin")
    return fakes


def graft(sequence: str, folder: Path, **options: float) -> TreegrafterResult:
    return score(TreegrafterInput(sequence), data_dir=folder, **options)


# The steps, against EBI's


def test_apoe_gets_its_hit_and_names_the_release(tools: Tools, folder: Path) -> None:
    tools.hmmsearch(saved("apoe.hmmsearch.out"))
    tools.epang(saved("apoe.jplace"))

    result = graft(APOE_SEQUENCE, folder)

    assert result == TreegrafterResult(APOE_HIT, RELEASE)


def test_hmmsearch_runs_as_treegrafter_sh_runs_it_with_one_thread(
    tools: Tools, folder: Path
) -> None:
    tools.hmmsearch(NO_HITS)

    graft(APOE_SEQUENCE, folder)

    argv = tools.argv("hmmsearch")
    library = folder / "treegrafter" / "19"
    assert argv[:-2] == SEARCH_OPTIONS
    assert argv[-2] == str(library / "famhmm" / "binHmm")
    assert Path(argv[-1]).name == "query.fasta"


def test_the_query_is_named_query(tools: Tools, folder: Path) -> None:
    tools.report.write_text(NO_HITS, encoding="ascii")
    tools.make_tool(
        "hmmsearch",
        'for last; do :; done; cp "$last" "$(dirname "$0")/query.copy"; '
        f'printf "%s\\0" "$@" > "$(dirname "$0")/hmmsearch.argv"; cat "{tools.report}"',
    )

    graft("MKVL", folder)

    assert (tools.folder / "query.copy").read_text() == ">query\nMKVL\n"


def test_epang_runs_with_ebis_arguments_on_the_familys_files(tools: Tools, folder: Path) -> None:
    tools.hmmsearch(saved("apoe.hmmsearch.out"))
    tools.epang(saved("apoe.jplace"))

    graft(APOE_SEQUENCE, folder)

    argv = tools.argv("epa-ng")
    library = folder / "treegrafter" / "19" / "Tree_MSF"
    assert argv[:6] == ["-G", "0.05", "-m", "WAG", "-T", "1"]
    assert argv[6:10] == [
        "-t",
        str(library / "PTHR18976.bifurcate.newick"),
        "-s",
        str(library / "PTHR18976.AN.fasta"),
    ]
    assert argv[10] == "-q" and Path(argv[11]).name == "PTHR18976_query.fasta"
    assert argv[12] == "-w" and Path(argv[13]).name == "PTHR18976_epang"


# The best family


def test_no_family_reported_is_no_hit_and_epang_doesnt_run(tools: Tools, folder: Path) -> None:
    tools.hmmsearch(NO_HITS)
    tools.epang(None)

    assert graft(APOE_SEQUENCE, folder) == TreegrafterResult(None, RELEASE)
    assert not tools.ran("epa-ng")


def test_of_two_families_the_higher_full_sequence_score_is_grafted(
    tools: Tools, folder: Path
) -> None:
    # PTHR18976's section first, at 172.6 bits; PTHR11442's after it, at 209.3.
    tools.hmmsearch(
        report_of(("PTHR18976", "apoe.hmmsearch.out"), ("PTHR11442", "hbb.hmmsearch.out"))
    )
    tools.epang(saved("hbb.jplace"))

    hit = graft(APOE_SEQUENCE, folder).hit

    assert hit is not None
    assert (hit.panther_id, hit.node_id, hit.score) == ("PTHR11442:SF42", "AN248", "209.3")


def test_a_best_family_over_the_cutoff_is_no_hit_even_with_another_under_it(
    tools: Tools, folder: Path
) -> None:
    # PTHR11442's 209.3 bits are the best score, at an E-value over 1e-8; PTHR18976 is under it.
    over = sections(saved("hbb.hmmsearch.out"))["PTHR11442"].replace(
        "8.4e-59  209.3", "2.0e-08  209.3"
    )
    report = (
        header(saved("apoe.hmmsearch.out")) + sections(saved("apoe.hmmsearch.out"))["PTHR18976"]
    )
    tools.hmmsearch(report + over + "[ok]\n")
    tools.epang(None)

    assert graft(APOE_SEQUENCE, folder).hit is None
    assert not tools.ran("epa-ng")


def test_one_over_the_cutoff_is_no_hit(tools: Tools, folder: Path) -> None:
    tools.hmmsearch(saved("apoe.hmmsearch.out").replace("5.7e-47  172.6", "1.1e-08  172.6"))
    tools.epang(None)

    assert graft(APOE_SEQUENCE, folder).hit is None
    assert not tools.ran("epa-ng")


# The fields


def test_ebis_dashes_are_no_value_and_its_go_terms_are_split() -> None:
    row = [
        "query",
        "PTHR10000",
        "50.1",
        "1e-10",
        "49.9",
        "2e-10",
        "1",
        "100",
        "3",
        "102",
        "1",
        "105",
        "AN7",
        "-",
        "-",
    ]

    hit = hit_from_row(row, "PTN000000007")

    assert (hit.node_id, hit.go_terms, hit.protein_class) == ("AN7", (), None)
    assert (hit.hmm_from, hit.hmm_to, hit.ali_from, hit.ali_to, hit.env_from, hit.env_to) == (
        1,
        100,
        3,
        102,
        1,
        105,
    )
    assert hit_from_row([*row[:13], "GO:0000001,GO:0000002", "PC00001"], None).go_terms == (
        "GO:0000001",
        "GO:0000002",
    )


def test_a_node_without_a_subfamily_gives_the_familys_id(tools: Tools, folder: Path) -> None:
    entries = folder / "treegrafter" / "19" / "annotations" / RELEASE / "PTHR18976.json"
    annotated = json.loads(entries.read_text())
    annotated["AN163"][0] = None
    entries.write_text(json.dumps(annotated))
    tools.hmmsearch(saved("apoe.hmmsearch.out"))
    tools.epang(saved("apoe.jplace"))

    hit = graft(APOE_SEQUENCE, folder).hit

    assert hit is not None and (hit.panther_id, hit.node_id) == ("PTHR18976", "AN163")


def test_a_family_that_cant_be_placed_is_the_family_alone_with_a_warning(
    tools: Tools, folder: Path, caplog: pytest.LogCaptureFixture
) -> None:
    tools.hmmsearch(saved("ndrg1.hmmsearch.out"))
    tools.epang(None)

    with caplog.at_level(logging.WARNING, logger="panther_engine.treegrafter"):
        hit = graft(NDRG1_STANDIN, folder).hit

    assert hit is not None
    assert (hit.panther_id, hit.score, hit.evalue) == ("PTHR11034", "494.1", "4.6e-145")
    assert (hit.node_id, hit.graft_point, hit.go_terms, hit.protein_class) == (None, None, (), None)
    assert (hit.hmm_from, hit.hmm_to, hit.env_from, hit.env_to) == (6, 326, 5, 371)
    assert not tools.ran("epa-ng")
    warning = " ".join(record.getMessage() for record in caplog.records)
    assert "PTHR11034" in warning and "AN186" in warning


# Sequences the API wouldn't send


@pytest.mark.parametrize(
    "sequence",
    [APOE_SEQUENCE[:50] + "~" + APOE_SEQUENCE[50:], "MKVL-AAG", "mkvl", "", "*", "._*", "MKV1"],
)
def test_a_sequence_the_api_never_sends_is_refused_before_any_tool(
    sequence: str, tools: Tools, folder: Path
) -> None:
    tools.hmmsearch(NO_HITS)
    tools.epang(None)

    with pytest.raises(ValueError) as caught:
        graft(sequence, folder)

    assert not isinstance(caught.value, InputError)
    assert not tools.ran("hmmsearch") and not tools.ran("epa-ng")


@pytest.mark.parametrize("sequence", ["MKVL*", "MK.V_L", "MKV*L", "BJOUXZ"])
def test_the_characters_the_engine_takes_reach_hmmsearch(
    sequence: str, tools: Tools, folder: Path
) -> None:
    tools.hmmsearch(NO_HITS)

    assert graft(sequence, folder).hit is None
    assert tools.ran("hmmsearch")


def test_a_sequence_past_the_apis_limit_is_grafted(tools: Tools, folder: Path) -> None:
    tools.hmmsearch(NO_HITS)

    assert graft("A" * 10_001, folder) == TreegrafterResult(None, RELEASE)


# The time limit


def test_hmmsearch_past_the_limit_raises_the_time_limit_error_and_removes_the_folder(
    tools: Tools, folder: Path
) -> None:
    tools.hmmsearch(NO_HITS, before="exec sleep 5")

    started = time.monotonic()
    with pytest.raises(TimeLimitError) as caught:
        graft(APOE_SEQUENCE, folder, timeout=0.5)

    assert time.monotonic() - started < 3
    assert not isinstance(caught.value, InputError)
    work = Path((tools.folder / "hmmsearch.pwd").read_text().strip())
    assert work.name.startswith("treegrafter-") and not work.exists()


def test_epang_gets_whats_left_and_is_stopped_past_it(tools: Tools, folder: Path) -> None:
    pid_file = tools.folder.parent / "epa-ng.pid"
    tools.hmmsearch(saved("apoe.hmmsearch.out"), before="sleep 0.5")
    tools.epang(saved("apoe.jplace"), before=f'echo $$ > "{pid_file}"; exec sleep 30')

    started = time.monotonic()
    with pytest.raises(TimeLimitError):
        graft(APOE_SEQUENCE, folder, timeout=1.5)

    assert time.monotonic() - started < 4
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_file.read_text()), 0)


def test_the_errors_keep_their_type_and_message_through_pickle() -> None:
    for error in (TimeLimitError("too long"), TreegrafterError("EPA-ng exited with status 1")):
        copy = pickle.loads(pickle.dumps(error))  # noqa: S301
        assert (type(copy), str(copy)) == (type(error), str(error))


# Tool failures


def test_hmmsearch_failing_is_a_treegrafter_error_with_its_stderr(
    tools: Tools, folder: Path
) -> None:
    tools.make_tool("hmmsearch", "echo 'Error: bad file format' >&2; exit 1")

    with pytest.raises(
        TreegrafterError, match="hmmsearch exited with status 1: Error: bad file format"
    ):
        graft(APOE_SEQUENCE, folder)


def test_epang_failing_is_a_treegrafter_error_with_the_end_of_its_stderr(
    tools: Tools, folder: Path
) -> None:
    tools.hmmsearch(saved("apoe.hmmsearch.out"))
    tools.epang(
        None,
        before="echo 'terminate called' >&2; echo '  what():  Set tip states during placement "
        "failed!' >&2",
        status=134,
    )

    with pytest.raises(TreegrafterError, match=r"status 134: .*Set tip states during placement"):
        graft(APOE_SEQUENCE, folder)


def test_epang_writing_no_placement_is_a_treegrafter_error(tools: Tools, folder: Path) -> None:
    tools.hmmsearch(saved("apoe.hmmsearch.out"))
    tools.epang(None)

    with pytest.raises(TreegrafterError, match=r"epa_result\.jplace"):
        graft(APOE_SEQUENCE, folder)


def test_a_report_ebis_parser_exits_on_is_a_treegrafter_error(tools: Tools, folder: Path) -> None:
    broken = saved("apoe.hmmsearch.out").replace(" [.       1     311 [. 0.96", " 0.96", 1)
    tools.hmmsearch(broken)

    with pytest.raises(TreegrafterError, match="parsehmmsearch exited with status 1"):
        graft(APOE_SEQUENCE, folder)


# The annotation release


def test_one_release_is_read_throughout_a_graft(tools: Tools, folder: Path) -> None:
    annotations_folder = folder / "treegrafter" / "19" / "annotations"
    other = annotations_folder / "2026-06-02"
    shutil.copytree(annotations_folder / RELEASE, other)
    entries = json.loads((other / "PTHR18976.json").read_text())
    entries["AN163"] = ["PTHR18976:SF99", "GO:0000001", "PC00001", "PTN999999999"]
    (other / "PTHR18976.json").write_text(json.dumps(entries))
    tools.hmmsearch(saved("apoe.hmmsearch.out"))
    # The other release becomes active while EPA-ng runs.
    tools.epang(saved("apoe.jplace"), before=f'echo 2026-06-02 > "{annotations_folder}/active"')

    result = graft(APOE_SEQUENCE, folder)

    assert result == TreegrafterResult(APOE_HIT, RELEASE)
    assert (annotations_folder / "active").read_text() == "2026-06-02\n"


# The versions


def test_the_data_version_is_19() -> None:
    assert DATA_VERSION == "19"


def test_annotations_gives_the_active_release_and_its_go_release(prepared: Path) -> None:
    assert annotations(prepared).date == RELEASE
    assert annotations(prepared).go_release == "2026-08-05"
