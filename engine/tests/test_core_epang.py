import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from panther_engine.core import epang

# Writes each argument it receives, NUL-terminated, to argv.bin beside itself.
RECORD_ARGV = 'printf "%s\\0" "$@" > "$(dirname "$0")/argv.bin"'

# A four-leaf tree with branch lengths, its alignment, and a query aligned to the same columns:
# the query is A's sequence with one change, so EPA-ng places it on A's branch.
TREE = "((A:0.1,B:0.2):0.05,(C:0.3,D:0.4):0.05);\n"
ALIGNMENT = (
    ">A\nMKVLAAGIVGLLLAQSWAEELRQKVEELLRERLAEAAPSHE\n"
    ">B\nMKVLAAGIVALLLAQSWAEELRQKVEELLKERLADAAPSHE\n"
    ">C\nMRVLWAALVVTLLAGCQAKVEQAVETEPEPELRQQTEWQSG\n"
    ">D\nMRVLWAALVVTFLAGCQAKVEQPVETEPEPELRQQTEWQAG\n"
)
QUERY = ">query\nMKVLAAGIVGLLLAQSWAEELRQKVEELLRERLAEAAPSHD\n"


def received_argv(tool: Path) -> list[str]:
    return (tool.parent / "argv.bin").read_bytes().decode("utf-8").split("\0")[:-1]


@pytest.fixture
def on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The folder make_tool writes to, first on PATH, so the runner finds the fake there."""
    folder = tmp_path / "bin"
    monkeypatch.setenv("PATH", f"{folder}:/usr/bin:/bin")
    return folder


def test_epang_gets_ebis_arguments_as_a_list(
    make_tool: Callable[[str, str], Path], on_path: Path, tmp_path: Path
) -> None:
    tool = make_tool("epa-ng", RECORD_ARGV)
    # Through a shell, `touch marker` would create the file in the working folder.
    tree = tmp_path / "PTHR1; touch marker" / "PTHR1.bifurcate.newick"
    msa, query, out = tmp_path / "PTHR1.AN.fasta", tmp_path / "q $(touch marker)", tmp_path / "o"

    result = epang.place(tree, msa, query, out, timeout=10, cwd=tmp_path)

    assert result.returncode == 0
    # EBI's _run_epang (treegrafter.py 160 to 167), with one thread.
    assert received_argv(tool) == [
        "-G",
        "0.05",
        "-m",
        "WAG",
        "-T",
        "1",
        "-t",
        str(tree),
        "-s",
        str(msa),
        "-q",
        str(query),
        "-w",
        str(out),
    ]
    assert not (tmp_path / "marker").exists()


def test_threads_reach_epang(
    make_tool: Callable[[str, str], Path], on_path: Path, tmp_path: Path
) -> None:
    tool = make_tool("epa-ng", RECORD_ARGV)

    epang.place(Path("t"), Path("s"), Path("q"), Path("o"), threads=4, timeout=10)

    argv = received_argv(tool)
    assert argv[argv.index("-T") + 1] == "4"


def test_epang_runs_in_cwd(
    make_tool: Callable[[str, str], Path], on_path: Path, tmp_path: Path
) -> None:
    make_tool("epa-ng", 'pwd > "$(dirname "$0")/epa-ng.pwd"')
    work = tmp_path / "work"
    work.mkdir()

    epang.place(Path("t"), Path("s"), Path("q"), Path("o"), timeout=10, cwd=work)

    assert (on_path / "epa-ng.pwd").read_text().strip() == str(work.resolve())


def test_a_failing_status_is_returned_not_raised(
    make_tool: Callable[[str, str], Path], on_path: Path
) -> None:
    make_tool("epa-ng", "echo 'ERROR: Bad tree/ref msa combination' >&2; exit 1")

    result = epang.place(Path("t"), Path("s"), Path("q"), Path("o"), timeout=10)

    assert result.returncode == 1
    assert result.stderr == "ERROR: Bad tree/ref msa combination\n"


def test_a_timeout_passes_through(make_tool: Callable[[str, str], Path], on_path: Path) -> None:
    make_tool("epa-ng", "exec sleep 5")

    with pytest.raises(subprocess.TimeoutExpired):
        epang.place(Path("t"), Path("s"), Path("q"), Path("o"), timeout=0.2)


def test_no_time_limit_lets_epang_finish(
    make_tool: Callable[[str, str], Path], on_path: Path
) -> None:
    make_tool("epa-ng", "sleep 0.3; exit 0")

    assert epang.place(Path("t"), Path("s"), Path("q"), Path("o"), timeout=None).returncode == 0


def test_epang_not_on_path_is_an_os_error(on_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="no epa-ng on PATH"):
        epang.place(Path("t"), Path("s"), Path("q"), Path("o"), timeout=10)


@pytest.mark.tools("epa-ng")
def test_the_real_epang_places_a_query_on_a_four_leaf_tree(tmp_path: Path) -> None:
    tree, msa, query = tmp_path / "tree.newick", tmp_path / "ref.fasta", tmp_path / "query.fasta"
    tree.write_text(TREE, encoding="ascii")
    msa.write_text(ALIGNMENT, encoding="ascii")
    query.write_text(QUERY, encoding="ascii")
    out = tmp_path / "out"
    out.mkdir()

    result = epang.place(tree, msa, query, out, timeout=60, cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    placed = cast(dict[str, object], json.loads((out / "epa_result.jplace").read_text()))
    placements = cast(list[dict[str, object]], placed["placements"])
    assert [placement["n"] for placement in placements] == [["query"]]
    assert placements[0]["p"]
