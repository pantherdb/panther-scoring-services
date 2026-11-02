"""Step 1 with fake `blastp` programs (design.md, decision 3). The real one is tested in
test_csnp_scoring.py, against the data sample."""

import os
from collections.abc import Callable
from pathlib import Path

import pytest
from csnp_fixtures import FIXTURES

from panther_engine.core.errors import InputError
from panther_engine.csnp.blast import (
    OUTFMT,
    TIME_SCALE_VARIABLE,
    UNREADABLE_MESSAGE,
    BlastError,
    search,
    time_limit,
)

# Writes its arguments, NUL-terminated, its stdin and its working folder beside itself.
RECORD = (
    'printf "%s\\0" "$@" > "$(dirname "$0")/argv.bin"; cat > "$(dirname "$0")/stdin.txt"; '
    'pwd -P > "$(dirname "$0")/cwd.txt"'
)
LINE = "P0001,HUMAN|HGNC=1|UniProtKB=P00001:PTHR00001:SF1,100.000,4,0,0,0,1,4,1,4,MKVL,MKVL,1e-5,9"


@pytest.fixture
def blastp(
    make_tool: Callable[[str, str], Path], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Callable[[str], Path]:
    """Returns `fake(script)`, which writes a fake `blastp` and puts it first on PATH. The test's
    `tmp_path` gets a `blast/` folder, where `blastp` runs."""
    (tmp_path / "blast").mkdir()

    def fake(script: str) -> Path:
        tool = make_tool("blastp", script)
        monkeypatch.setenv("PATH", f"{tool.parent}{os.pathsep}{os.environ['PATH']}")
        return tool

    return fake


def test_blastp_gets_the_legacy_options_and_the_query_on_stdin(
    blastp: Callable[[str], Path], tmp_path: Path
) -> None:
    tool = blastp(RECORD)

    search("MKVL", tmp_path)

    arguments = (tool.parent / "argv.bin").read_bytes().decode().split("\0")[:-1]
    # The database by name, in its own folder: the data folder's path never reaches -db (CSNP-6).
    assert (tool.parent / "cwd.txt").read_text() == f"{(tmp_path / 'blast').resolve()}\n"
    assert arguments == [
        "-db",
        "blast",
        "-outfmt",
        OUTFMT,
        "-best_hit_overhang",
        "0.1",
        "-best_hit_score_edge",
        "0.1",
    ]
    assert OUTFMT == (
        "10 qseqid sseqid pident length mismatch gapopen gaps qstart qend sstart send qseq sseq "
        "evalue bitscore"
    )
    # As snpScore.cgi's createFasta wrote it: no line feed after the sequence.
    assert (tool.parent / "stdin.txt").read_text() == ">P0001\nMKVL"


def test_exit_status_0_returns_the_lines_as_written(
    blastp: Callable[[str], Path], tmp_path: Path
) -> None:
    blastp(f"printf '%s\\n%s\\n' '{LINE}' '{LINE}'")

    assert search("MKVL", tmp_path) == [f"{LINE}\n", f"{LINE}\n"]


def test_no_hit_returns_no_lines(blastp: Callable[[str], Path], tmp_path: Path) -> None:
    blastp("exit 0")

    assert search("MKVL", tmp_path) == []


def test_exit_status_1_is_an_input_error_without_the_tools_output(
    blastp: Callable[[str], Path], tmp_path: Path
) -> None:
    blastp("echo 'BLAST query error: CFastaReader: Near line 2, in /secret/query' >&2; exit 1")

    with pytest.raises(InputError) as raised:
        search("12345", tmp_path)

    message = str(raised.value)
    assert message
    for leaked in ("BLAST", "CFastaReader", "/secret", "line 2", str(tmp_path)):
        assert leaked not in message


def test_exit_status_1_for_an_argument_blastp_rejects_is_a_blast_error_with_its_message(
    blastp: Callable[[str], Path], tmp_path: Path
) -> None:
    # What BLAST+ 2.17.0 wrote for -bogus_option: its usage text, then two Error: lines.
    stderr = FIXTURES / "blastp-unknown-argument.stderr"
    blastp(f"cat '{stderr}' >&2; exit 1")

    with pytest.raises(BlastError, match="status 1") as raised:
        search("MKVL", tmp_path)

    assert not isinstance(raised.value, InputError)
    assert 'Error: Unknown argument: "bogus_option"' in str(raised.value)


def test_exit_status_1_with_nothing_on_standard_error_is_a_blast_error(
    blastp: Callable[[str], Path], tmp_path: Path
) -> None:
    blastp("exit 1")

    with pytest.raises(BlastError, match="status 1") as raised:
        search("MKVL", tmp_path)

    assert not isinstance(raised.value, InputError)


@pytest.mark.parametrize("status", [2, 3, 4, 255])
def test_another_exit_status_is_a_blast_error(
    blastp: Callable[[str], Path], tmp_path: Path, status: int
) -> None:
    blastp(f"echo 'BLAST Database error: No alias or index file found' >&2; exit {status}")

    with pytest.raises(BlastError, match=f"status {status}") as raised:
        search("MKVL", tmp_path)

    assert not isinstance(raised.value, InputError)
    assert "No alias or index file found" in str(raised.value)


def test_a_search_past_its_time_limit_is_a_blast_error(
    blastp: Callable[[str], Path], tmp_path: Path
) -> None:
    blastp("exec sleep 5")

    with pytest.raises(BlastError, match="time limit"):
        search("MKVL", tmp_path, timeout=0.2)


# The time limit (CSNP-4): a base plus a time per residue, times PANTHER_CSNP_BLAST_TIME_SCALE.

# The slowest of three searches, in seconds, as docs/testing/engine.md records them ("The BLAST+
# Time Limit"): titin (Q8WZ42, 34,350 residues), and the API's longest accepted sequence, 50,000
# residues (titin, then its first 15,650).
TITIN_SECONDS = 274.6
LONGEST_SECONDS = 436.9


def test_titins_limit_is_at_least_two_and_a_half_times_its_search() -> None:
    assert time_limit(34_350) >= 2.5 * TITIN_SECONDS


def test_the_longest_sequences_limit_is_at_least_two_and_a_half_times_its_search() -> None:
    assert time_limit(50_000) >= 2.5 * LONGEST_SECONDS


def test_an_ordinary_proteins_limit_is_one_to_two_minutes() -> None:
    assert 60 <= time_limit(400) < 120


def test_the_limit_grows_with_the_sequence() -> None:
    assert time_limit(1) < time_limit(400) < time_limit(34_350) < time_limit(50_000)


def test_a_scale_of_2_doubles_the_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    lengths = (1, 400, 34_350, 50_000)
    default = [time_limit(length) for length in lengths]
    monkeypatch.setenv(TIME_SCALE_VARIABLE, "2")

    assert [time_limit(length) for length in lengths] == [2 * limit for limit in default]


def test_an_empty_scale_is_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    default = time_limit(400)
    monkeypatch.setenv(TIME_SCALE_VARIABLE, "")

    assert time_limit(400) == default


@pytest.mark.parametrize("value", ["0", "-1", "fast", "inf", "nan", "-inf"])
def test_a_scale_that_isnt_a_positive_number_fails_before_blastp_runs(
    blastp: Callable[[str], Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    tool = blastp(RECORD)
    monkeypatch.setenv(TIME_SCALE_VARIABLE, value)

    with pytest.raises(BlastError, match=TIME_SCALE_VARIABLE) as raised:
        search("MKVL", tmp_path)

    assert not isinstance(raised.value, InputError)
    assert not (tool.parent / "stdin.txt").exists()


def test_a_search_without_a_timeout_uses_the_scaled_limit(
    blastp: Callable[[str], Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blastp("exec sleep 5")
    # About 6 ms for a 4-residue query.
    monkeypatch.setenv(TIME_SCALE_VARIABLE, "0.0001")

    with pytest.raises(BlastError, match="time limit"):
        search("MKVL", tmp_path)


def test_no_blastp_on_the_path_is_a_blast_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))

    with pytest.raises(BlastError, match="no blastp"):
        search("MKVL", tmp_path)


def test_a_data_folder_without_a_blast_folder_is_a_blast_error_naming_it(
    blastp: Callable[[str], Path], tmp_path: Path
) -> None:
    tool = blastp(RECORD)
    data = tmp_path / "elsewhere"
    data.mkdir()

    with pytest.raises(BlastError, match="no BLAST database folder") as raised:
        search("MKVL", data)

    assert str(data / "blast") in str(raised.value)
    assert not (tool.parent / "stdin.txt").exists()


def test_a_blast_error_isnt_an_input_error() -> None:
    assert not issubclass(BlastError, InputError)


@pytest.mark.parametrize("sequence", ["!MKVL", "#MKVL", ";MKVL", "!"])
def test_a_sequence_blast_would_read_as_a_comment_is_an_input_error_without_a_search(
    blastp: Callable[[str], Path], tmp_path: Path, sequence: str
) -> None:
    tool = blastp(RECORD)

    with pytest.raises(InputError) as raised:
        search(sequence, tmp_path)

    assert str(raised.value) == UNREADABLE_MESSAGE
    assert not (tool.parent / "stdin.txt").exists()


def test_a_comment_character_after_the_first_residue_is_left_to_blastp(
    blastp: Callable[[str], Path], tmp_path: Path
) -> None:
    tool = blastp(RECORD)

    search("MKV;", tmp_path)

    assert (tool.parent / "stdin.txt").read_text() == ">P0001\nMKV;"
