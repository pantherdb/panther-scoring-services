"""Scoring, with fake `hmmscan` and `hmmsearch`: the hand-written tables and the saved report in
fixtures/hmmscore/tables/ stand in for HMMER, so each rule is tested on exactly the rows it needs.
The real tools are in test_hmmscore_scoring_tools.py."""

import os
import pickle
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from hmmscore_fixtures import TABLES, install_fake_hmmer, scoring_folder

from panther_engine.core.data import MissingDataError
from panther_engine.core.errors import InputError
from panther_engine.hmmscore import (
    DATA_VERSION,
    HmmHit,
    HmmscoreError,
    HmmscoreInput,
    HmmscoreResult,
    TimeLimitError,
    check_data,
    score,
    scoring,
)

SEQUENCE = "MKVLWAALLVTFLAGCQAKVEQ"
REPORT = TABLES / "apoe.hmmsearch"
# The report's lines after "Domain annotation for each sequence (and alignments):" (its 19th
# line) and before "Internal pipeline statistics summary:" (its 49th).
REPORT_LINES = REPORT.read_bytes().decode("latin-1").splitlines(keepends=True)
ALIGNMENT = "".join(REPORT_LINES[19:48])
NAMES = (
    "PTHR18976.mag.mod\tAPOLIPOPROTEIN\n"
    "PTHR18976.SF2.mod\tAPOLIPOPROTEIN E\n"
    "PTHR34093.mag.mod\tFAMILY 34093\n"
    "PTHR10000.SF1.mod\tSUBFAMILY 10000:SF1\n"
    "PTHR10000.SF2.mod\tSUBFAMILY 10000:SF2\n"
    "PTHR20000.SF2.mod\tSUBFAMILY 20000:SF2\n"
    "PTHR30000.SF1.mod\tSUBFAMILY 30000:SF1\n"
    "PTHR35774.mag.mod\tFAMILY 35774\n"
    "PTHR35774.SF1.mod\tSUBFAMILY 35774:SF1\n"
)
MODELS = (
    "books/PTHR18976/SF2/hmmer.hmm",
    "books/PTHR34093/hmmer.hmm",
    "books/PTHR10000/SF1/hmmer.hmm",
    "books/PTHR10000/SF2/hmmer.hmm",
    "books/PTHR20000/SF2/hmmer.hmm",
    "books/PTHR30000/SF1/hmmer.hmm",
    "books/PTHR35774/SF1/hmmer.hmm",
)

type Install = Callable[[str], Path]


@pytest.fixture
def data(tmp_path: Path) -> Path:
    return scoring_folder(tmp_path / "data", models=MODELS, names=NAMES)


@pytest.fixture
def fake_hmmer(
    make_tool: Callable[[str, str], Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Install:
    """Returns `install(table)`, which puts a fake `hmmscan` and `hmmsearch` first on PATH, and
    returns their folder. `hmmscan` copies `table` to its `--domtblout` file and keeps a copy of
    its query as `query.fasta`; `hmmsearch` prints the saved report. Each records its arguments
    in `<name>.argv`."""
    folder = tmp_path / "bin"
    monkeypatch.setenv("PATH", f"{folder}:/usr/bin:/bin")

    def install(table: str) -> Path:
        install_fake_hmmer(make_tool, folder, table)
        return folder

    return install


def argv(folder: Path, name: str) -> list[str]:
    return (folder / f"{name}.argv").read_bytes().decode("utf-8").split("\0")[:-1]


def hit(table: str, install: Install, data: Path) -> HmmHit | None:
    install(table)
    return score(HmmscoreInput(SEQUENCE), data_dir=data).hit


# The columns and the IDs


def test_the_examples_table_gives_its_best_model(fake_hmmer: Install, data: Path) -> None:
    fake_hmmer("apoe.domtblout")

    result = score(HmmscoreInput(SEQUENCE), data_dir=data)

    assert result == HmmscoreResult(
        HmmHit("PTHR18976:SF2", "APOLIPOPROTEIN E", "2.2e-133", "439.0", ALIGNMENT)
    )


def test_a_family_pir_model_reads_as_its_family(fake_hmmer: Install, data: Path) -> None:
    found = hit("pir.domtblout", fake_hmmer, data)

    assert found is not None
    assert (found.panther_id, found.name, found.evalue, found.score) == (
        "PTHR34093",
        "FAMILY 34093",
        "3.3e-36",
        "120.5",
    )


def test_two_models_of_one_id_are_one_hit(fake_hmmer: Install, data: Path) -> None:
    found = hit("tie-one-id.domtblout", fake_hmmer, data)

    assert found is not None
    assert found.panther_id == "PTHR34093"


# The best hit


def test_score_comes_before_the_e_value(fake_hmmer: Install, data: Path) -> None:
    found = hit("score-first.domtblout", fake_hmmer, data)

    assert found is not None
    assert (found.panther_id, found.evalue, found.score) == ("PTHR10000:SF1", "2e-05", "50.1")


def test_scores_are_compared_as_numbers(fake_hmmer: Install, data: Path) -> None:
    # As strings, "9.5" is the larger.
    found = hit("numbers.domtblout", fake_hmmer, data)

    assert found is not None
    assert (found.panther_id, found.score) == ("PTHR20000:SF2", "10.2")


def test_the_smallest_e_value_wins_for_the_best_score(fake_hmmer: Install, data: Path) -> None:
    # As strings, "1e-10" is the smaller.
    found = hit("same-score.domtblout", fake_hmmer, data)

    assert found is not None
    assert (found.panther_id, found.evalue) == ("PTHR30000:SF1", "2e-100")


def test_a_best_hit_over_the_cutoff_is_no_hit(fake_hmmer: Install, data: Path) -> None:
    # The lower-scoring model's 1e-05 passes the cutoff, but only the best hit is tested.
    folder = fake_hmmer("over-cutoff.domtblout")

    assert score(HmmscoreInput(SEQUENCE), data_dir=data) == HmmscoreResult(None)
    assert not (folder / "hmmsearch.argv").exists()


def test_a_best_hit_at_the_cutoff_is_kept(fake_hmmer: Install, data: Path) -> None:
    found = hit("at-cutoff.domtblout", fake_hmmer, data)

    assert found is not None
    assert (found.panther_id, found.evalue) == ("PTHR10000:SF1", "0.001")


def test_a_table_with_no_rows_is_no_hit(fake_hmmer: Install, data: Path) -> None:
    folder = fake_hmmer("empty.domtblout")

    assert score(HmmscoreInput(SEQUENCE), data_dir=data) == HmmscoreResult(None)
    assert not (folder / "hmmsearch.argv").exists()


# Ties (divergence 13)


def test_a_tied_subfamily_comes_before_its_family(fake_hmmer: Install, data: Path) -> None:
    found = hit("tie-family.domtblout", fake_hmmer, data)

    assert found is not None
    assert (found.panther_id, found.evalue, found.score) == ("PTHR35774:SF1", "4.1e-60", "200.3")


def test_ties_give_the_lowest_panther_id(fake_hmmer: Install, data: Path) -> None:
    found = hit("tie-lowest.domtblout", fake_hmmer, data)

    assert found is not None
    assert found.panther_id == "PTHR10000:SF2"


@pytest.mark.parametrize(
    ("tied", "picked"),
    [
        (("PTHR35774", "PTHR35774:SF1"), "PTHR35774:SF1"),
        (("PTHR35774:SF1", "PTHR35774"), "PTHR35774:SF1"),
        (("PTHR10000:SF10", "PTHR10000:SF2", "PTHR20000"), "PTHR10000:SF2"),
        (("PTHR20000", "PTHR10000:SF10"), "PTHR10000:SF10"),
        (("PTHR10000", "PTHR05000:SF3"), "PTHR05000:SF3"),
        (("PTHR10000", "PTHR20000:SF1"), "PTHR10000"),
        (("PTHR10000:SF3", "PTHR10000", "PTHR10000:SF1"), "PTHR10000:SF1"),
    ],
)
def test_pick(tied: tuple[str, ...], picked: str) -> None:
    assert scoring.pick(tied) == picked


# The alignment


def test_the_alignment_is_the_reports_domain_annotation(fake_hmmer: Install, data: Path) -> None:
    found = hit("apoe.domtblout", fake_hmmer, data)

    assert found is not None
    assert found.alignment.startswith(">> sequence  \n   #    score  bias  c-Evalue")
    assert found.alignment.endswith(" PP\n\n\n\n")
    assert "Domain annotation" not in found.alignment
    assert "Internal pipeline" not in found.alignment
    assert "&gt;" not in found.alignment


def test_hmmsearch_aligns_the_query_with_the_hits_model_file(
    fake_hmmer: Install, data: Path
) -> None:
    folder = fake_hmmer("pir.domtblout")

    score(HmmscoreInput(SEQUENCE), data_dir=data, cpu=3)

    scanned, searched = argv(folder, "hmmscan"), argv(folder, "hmmsearch")
    model = data / "hmmscore" / "19" / "books" / "PTHR34093" / "hmmer.hmm"
    assert searched == ["--cpu", "3", str(model), scanned[5]]


def test_hmmscan_searches_the_whole_library(fake_hmmer: Install, data: Path) -> None:
    folder = fake_hmmer("apoe.domtblout")

    score(HmmscoreInput(SEQUENCE), data_dir=data, cpu=2)

    scanned = argv(folder, "hmmscan")
    library = data / "hmmscore" / "19" / "globals" / "binHmm"
    assert scanned[0] == "--domtblout"
    assert scanned[2:5] == ["--cpu", "2", str(library)]
    assert Path(scanned[1]).parent == Path(scanned[5]).parent


def test_the_query_is_named_sequence_as_the_cgi_wrote_it(fake_hmmer: Install, data: Path) -> None:
    folder = fake_hmmer("apoe.domtblout")

    score(HmmscoreInput(SEQUENCE), data_dir=data)

    assert (folder / "query.fasta").read_bytes() == f">sequence\n{SEQUENCE}".encode("ascii")


# The name


def test_an_id_names_tab_lacks_is_no_name(fake_hmmer: Install, tmp_path: Path) -> None:
    data = scoring_folder(
        tmp_path / "other", models=MODELS, names="PTHR18976.mag.mod\tAPOLIPOPROTEIN\n"
    )

    found = hit("apoe.domtblout", fake_hmmer, data)

    assert found is not None
    assert (found.panther_id, found.name) == ("PTHR18976:SF2", "No name")


# Sequences the API never sends


@pytest.mark.parametrize("sequence", ["mkvl", "*", "", "MKVL-", "MK VL", "MKVL1", ">MKVL"])
def test_a_sequence_the_api_never_sends_is_a_value_error(
    fake_hmmer: Install, data: Path, sequence: str
) -> None:
    folder = fake_hmmer("apoe.domtblout")

    with pytest.raises(ValueError) as raised:
        score(HmmscoreInput(sequence), data_dir=data)

    assert not isinstance(raised.value, InputError)
    assert not (folder / "hmmscan.argv").exists()


@pytest.mark.parametrize("sequence", ["M", "MKVL*", "MK.VL_W~A*L", "*M", "BJOUXZ"])
def test_the_characters_the_api_accepts_are_scored(
    fake_hmmer: Install, data: Path, sequence: str
) -> None:
    folder = fake_hmmer("apoe.domtblout")

    score(HmmscoreInput(sequence), data_dir=data)

    assert (folder / "query.fasta").read_bytes() == f">sequence\n{sequence}".encode("ascii")


def test_past_the_apis_residue_limit_is_scored(fake_hmmer: Install, data: Path) -> None:
    fake_hmmer("apoe.domtblout")

    result = score(HmmscoreInput("M" * 10_001), data_dir=data)

    assert result.hit is not None


# The data check


def test_the_data_check_passes_with_the_files_in_place(data: Path) -> None:
    check_data(data)


@pytest.mark.parametrize(
    "missing",
    [
        "globals/names.tab",
        "globals/binHmm.h3f",
        "globals/binHmm.h3i",
        "globals/binHmm.h3m",
        "globals/binHmm.h3p",
    ],
)
def test_the_data_check_names_a_missing_file(data: Path, missing: str) -> None:
    (data / "hmmscore" / "19" / missing).unlink()

    with pytest.raises(MissingDataError, match=missing.replace(".", r"\.")):
        check_data(data)


def test_the_data_check_names_a_missing_books_folder(tmp_path: Path) -> None:
    data = scoring_folder(tmp_path / "data", models=(), names=NAMES)
    (data / "hmmscore" / "19" / "books").rmdir()

    with pytest.raises(MissingDataError, match="books/"):
        check_data(data)


def test_scoring_checks_the_data_before_searching(fake_hmmer: Install, data: Path) -> None:
    folder = fake_hmmer("apoe.domtblout")
    (data / "hmmscore" / "19" / "globals" / "binHmm.h3p").unlink()

    with pytest.raises(MissingDataError, match=r"globals/binHmm\.h3p"):
        score(HmmscoreInput(SEQUENCE), data_dir=data)

    assert not (folder / "hmmscan.argv").exists()


def test_the_data_version_needs_no_data_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PANTHER_DATA_DIR", raising=False)

    assert DATA_VERSION == "19"


# The time limit


@pytest.fixture
def work_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The folder scoring's temporary folders are made in, for this test alone."""
    folder = tmp_path / "tmp"
    folder.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder


def test_past_the_time_limit_is_the_time_limit_error(
    make_tool: Callable[[str, str], Path],
    fake_hmmer: Install,
    data: Path,
    work_folder: Path,
    tmp_path: Path,
) -> None:
    fake_hmmer("apoe.domtblout")
    pid = tmp_path / "hmmscan.pid"
    make_tool("hmmscan", f'echo $$ > "{pid}"\nexec sleep 30')

    with pytest.raises(TimeLimitError) as raised:
        score(HmmscoreInput(SEQUENCE), data_dir=data, timeout=0.5)

    # A short query reaches its limit only on a busy server: not the input's fault.
    assert not isinstance(raised.value, InputError)
    assert str(raised.value) == (
        "The search took longer than this service allows. Try a shorter sequence."
    )
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid.read_text()), 0)
    assert list(work_folder.iterdir()) == []


def test_the_time_limit_covers_both_tools(
    make_tool: Callable[[str, str], Path], fake_hmmer: Install, data: Path, work_folder: Path
) -> None:
    folder = fake_hmmer("apoe.domtblout")
    # Each tool alone takes less than the limit; together they take more.
    scan = (folder / "hmmscan").read_text(encoding="utf-8").removeprefix("#!/bin/sh\n")
    make_tool("hmmscan", f"sleep 0.6\n{scan}")
    make_tool("hmmsearch", "exec sleep 0.6")

    with pytest.raises(TimeLimitError, match="took longer"):
        score(HmmscoreInput(SEQUENCE), data_dir=data, timeout=1.0)

    assert list(work_folder.iterdir()) == []


def test_no_time_left_for_the_next_tool_is_the_time_limit_error() -> None:
    # hmmscan can end just at the deadline, leaving hmmsearch nothing.
    with pytest.raises(TimeLimitError, match="took longer"):
        scoring.remaining(time.monotonic() - 1)


def test_the_time_limit_error_keeps_its_type_across_processes() -> None:
    # A worker pickles the exception it raises; the API sorts it by its type.
    error = TimeLimitError("The search took longer than this service allows.")

    copy = pickle.loads(pickle.dumps(error))  # noqa: S301

    assert type(copy) is TimeLimitError
    assert str(copy) == "The search took longer than this service allows."


def test_without_a_time_limit_scoring_waits(
    make_tool: Callable[[str, str], Path], fake_hmmer: Install, data: Path
) -> None:
    folder = fake_hmmer("apoe.domtblout")
    scan = (folder / "hmmscan").read_text(encoding="utf-8").removeprefix("#!/bin/sh\n")
    make_tool("hmmscan", f"sleep 0.3\n{scan}")

    assert score(HmmscoreInput(SEQUENCE), data_dir=data, timeout=None).hit is not None


def test_the_folder_is_removed_after_scoring(
    fake_hmmer: Install, data: Path, work_folder: Path
) -> None:
    fake_hmmer("apoe.domtblout")

    score(HmmscoreInput(SEQUENCE), data_dir=data)

    assert list(work_folder.iterdir()) == []


# Failures that aren't the input's


@pytest.mark.parametrize("name", ["hmmscan", "hmmsearch"])
def test_a_tool_that_fails_is_an_error_not_no_hit(
    make_tool: Callable[[str, str], Path],
    fake_hmmer: Install,
    data: Path,
    work_folder: Path,
    name: str,
) -> None:
    fake_hmmer("apoe.domtblout")
    make_tool(name, "echo 'Error: File format problem, trying to open HMM file' >&2; exit 1")

    with pytest.raises(HmmscoreError, match=f"{name} exited with status 1: Error: File format"):
        score(HmmscoreInput(SEQUENCE), data_dir=data)

    assert list(work_folder.iterdir()) == []


def test_hmmscan_writing_no_table_is_an_error(
    make_tool: Callable[[str, str], Path], fake_hmmer: Install, data: Path
) -> None:
    fake_hmmer("apoe.domtblout")
    make_tool("hmmscan", "exit 0")

    with pytest.raises(HmmscoreError, match="no table"):
        score(HmmscoreInput(SEQUENCE), data_dir=data)


def test_a_report_without_its_domain_annotation_is_an_error(
    make_tool: Callable[[str, str], Path], fake_hmmer: Install, data: Path
) -> None:
    fake_hmmer("apoe.domtblout")
    make_tool("hmmsearch", "echo '# hmmsearch :: search profile(s) against a sequence database'")

    with pytest.raises(HmmscoreError, match="Domain annotation"):
        score(HmmscoreInput(SEQUENCE), data_dir=data)


def test_a_table_line_that_isnt_a_domain_is_an_error(
    make_tool: Callable[[str, str], Path], fake_hmmer: Install, data: Path
) -> None:
    fake_hmmer("apoe.domtblout")
    make_tool("hmmscan", "echo 'PTHR18976.SF2.pir - 290 sequence' > \"$2\"")

    with pytest.raises(HmmscoreError, match="table"):
        score(HmmscoreInput(SEQUENCE), data_dir=data)


def test_a_missing_model_file_is_an_error_naming_it(
    fake_hmmer: Install, data: Path, work_folder: Path
) -> None:
    folder = fake_hmmer("apoe.domtblout")
    model = data / "hmmscore" / "19" / "books" / "PTHR18976" / "SF2" / "hmmer.hmm"
    model.unlink()

    with pytest.raises(HmmscoreError, match=r"books/PTHR18976/SF2/hmmer\.hmm"):
        score(HmmscoreInput(SEQUENCE), data_dir=data)

    assert not (folder / "hmmsearch.argv").exists()
    assert list(work_folder.iterdir()) == []


def test_a_tool_not_on_path_is_an_error(
    monkeypatch: pytest.MonkeyPatch, data: Path, tmp_path: Path
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "nothing"))

    with pytest.raises(HmmscoreError, match="no hmmscan on PATH"):
        score(HmmscoreInput(SEQUENCE), data_dir=data)


def test_a_table_is_split_on_perls_whitespace_only() -> None:
    # Python's \s would also split at \xa0, which Perl's \s on bytes doesn't, and shift every
    # column after it.
    line = (
        "PTHR10000.SF1.pir\xa0x -  300 sequence - 317 1e-05 50.1 1.0 1 1 1e-10 1e-10 50.1 1.0 "
        "1 290 1 300 1 310 0.95 a\xa0description\n"
    ).encode("latin-1")

    assert scoring.read_table(line) == [
        scoring.Row("PTHR10000.SF1.pir\xa0x", "PTHR10000:SF1", "1e-05", "50.1")
    ]


def test_an_empty_name_in_names_tab_is_no_name(fake_hmmer: Install, tmp_path: Path) -> None:
    # pantherScore.pl -n prints an empty name for both, so parity can't tell them apart.
    data = scoring_folder(tmp_path / "other", models=MODELS, names="PTHR18976.SF2.mod\t\n")

    found = hit("apoe.domtblout", fake_hmmer, data)

    assert found is not None
    assert found.name == "No name"
