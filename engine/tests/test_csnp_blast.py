"""Step 1 with fake `blastp` programs (design.md, decision 3). The real one is tested in
test_csnp_scoring.py, against the data sample."""

import os
from collections.abc import Callable
from pathlib import Path

import pytest

from panther_engine.core.errors import InputError
from panther_engine.csnp.blast import OUTFMT, UNREADABLE_MESSAGE, BlastError, search

# Writes its arguments, NUL-terminated, and its stdin beside itself.
RECORD = 'printf "%s\\0" "$@" > "$(dirname "$0")/argv.bin"; cat > "$(dirname "$0")/stdin.txt"'
LINE = "P0001,HUMAN|HGNC=1|UniProtKB=P00001:PTHR00001:SF1,100.000,4,0,0,0,1,4,1,4,MKVL,MKVL,1e-5,9"


@pytest.fixture
def blastp(
    make_tool: Callable[[str, str], Path], monkeypatch: pytest.MonkeyPatch
) -> Callable[[str], Path]:
    """Returns `fake(script)`, which writes a fake `blastp` and puts it first on PATH."""

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
    assert arguments == [
        "-db",
        str(tmp_path.absolute() / "blast" / "blast"),
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


def test_no_blastp_on_the_path_is_a_blast_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))

    with pytest.raises(BlastError, match="no blastp"):
        search("MKVL", tmp_path)


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
