import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from panther_engine.core import hmmer

# Writes each argument it receives, NUL-terminated, to argv.bin beside itself.
RECORD_ARGV = 'printf "%s\\0" "$@" > "$(dirname "$0")/argv.bin"'
# Bytes a text-mode capture would change: a CR alone, a CRLF, and no final line feed.
TABLE = b"PTHR1.SF1.pir - 10 sequence - 5 1e-05 50.1\r\nline two\rend"


def received_argv(tool: Path) -> list[str]:
    return (tool.parent / "argv.bin").read_bytes().decode("utf-8").split("\0")[:-1]


@pytest.fixture
def on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The folder make_tool writes to, first on PATH, so the runners find the fakes there."""
    folder = tmp_path / "bin"
    monkeypatch.setenv("PATH", f"{folder}:/usr/bin:/bin")
    return folder


def test_hmmscan_gets_its_arguments_as_a_list_with_cpu(
    make_tool: Callable[[str, str], Path], on_path: Path, tmp_path: Path
) -> None:
    tool = make_tool("hmmscan", RECORD_ARGV)
    # Through a shell, `touch marker` would create the file in the working folder.
    database, query = tmp_path / "lib; touch marker" / "binHmm", tmp_path / "q $(touch marker)"
    table = tmp_path / "hits.domtblout"

    result = hmmer.hmmscan(database, query, table=table, cpu=2, timeout=10, cwd=tmp_path)

    assert result.returncode == 0
    assert received_argv(tool) == [
        "--domtblout",
        str(table),
        "--cpu",
        "2",
        str(database),
        str(query),
    ]
    assert not (tmp_path / "marker").exists()


def test_hmmsearch_gets_its_arguments_as_a_list_with_cpu(
    make_tool: Callable[[str, str], Path], on_path: Path, tmp_path: Path
) -> None:
    tool = make_tool("hmmsearch", RECORD_ARGV)
    model, query = tmp_path / "SF1; touch marker" / "hmmer.hmm", tmp_path / "query"

    result = hmmer.hmmsearch(
        model, query, report=tmp_path / "report", cpu=0, timeout=10, cwd=tmp_path
    )

    assert result.returncode == 0
    assert received_argv(tool) == ["--cpu", "0", str(model), str(query)]
    assert not (tmp_path / "marker").exists()


def test_hmmsearchs_options_come_before_the_model_and_the_query_each_as_one_argument(
    make_tool: Callable[[str, str], Path], on_path: Path, tmp_path: Path
) -> None:
    tool = make_tool("hmmsearch", RECORD_ARGV)
    model, query = tmp_path / "binHmm", tmp_path / "query.fasta"
    # treegrafter's options (treegrafter.sh), and one with a space and a shell command in it.
    options = ("-Z", "65000000", "-E", "0.001", "--notextw", "--tblout x; touch marker")

    hmmer.hmmsearch(
        model, query, report=tmp_path / "r", cpu=0, timeout=10, cwd=tmp_path, options=options
    )

    assert received_argv(tool) == ["--cpu", "0", *options, str(model), str(query)]
    assert not (tmp_path / "marker").exists()


def test_hmmsearchs_options_as_one_string_are_refused(on_path: Path, tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="not one string"):
        hmmer.hmmsearch(
            Path("m"), Path("q"), report=tmp_path / "r", cpu=0, timeout=10, options="-Z 1"
        )


def test_the_tools_run_in_cwd(
    make_tool: Callable[[str, str], Path], on_path: Path, tmp_path: Path
) -> None:
    make_tool("hmmscan", 'pwd > "$(dirname "$0")/hmmscan.pwd"')
    make_tool("hmmsearch", 'pwd > "$(dirname "$0")/hmmsearch.pwd"')
    work = tmp_path / "work"
    work.mkdir()

    hmmer.hmmscan(Path("db"), Path("q"), table=work / "t", cpu=0, timeout=10, cwd=work)
    hmmer.hmmsearch(Path("m"), Path("q"), report=work / "r", cpu=0, timeout=10, cwd=work)

    assert (on_path / "hmmscan.pwd").read_text().strip() == str(work.resolve())
    assert (on_path / "hmmsearch.pwd").read_text().strip() == str(work.resolve())


def test_hmmscans_table_lands_in_the_file_byte_for_byte(
    make_tool: Callable[[str, str], Path], on_path: Path, tmp_path: Path
) -> None:
    (tmp_path / "table.bin").write_bytes(TABLE)
    # The table goes where --domtblout says; what hmmscan prints is thrown away.
    make_tool("hmmscan", f'cat "{tmp_path / "table.bin"}" > "$2"; echo printed')
    table = tmp_path / "hits.domtblout"

    result = hmmer.hmmscan(Path("db"), Path("q"), table=table, cpu=0, timeout=10)

    assert table.read_bytes() == TABLE
    assert result.stdout == ""


def test_hmmsearchs_report_lands_in_the_file_byte_for_byte(
    make_tool: Callable[[str, str], Path], on_path: Path, tmp_path: Path
) -> None:
    (tmp_path / "report.bin").write_bytes(TABLE)
    make_tool("hmmsearch", f'cat "{tmp_path / "report.bin"}"')
    report = tmp_path / "search.out"

    hmmer.hmmsearch(Path("m"), Path("q"), report=report, cpu=0, timeout=10)

    assert report.read_bytes() == TABLE


@pytest.mark.parametrize("name", ["hmmscan", "hmmsearch"])
def test_a_failing_status_is_returned_not_raised(
    make_tool: Callable[[str, str], Path], on_path: Path, tmp_path: Path, name: str
) -> None:
    make_tool(name, "echo 'Error: bad file format' >&2; exit 3")

    result = run(name, tmp_path, timeout=10)

    assert result.returncode == 3
    assert result.stderr == "Error: bad file format\n"


@pytest.mark.parametrize("name", ["hmmscan", "hmmsearch"])
def test_a_timeout_passes_through(
    make_tool: Callable[[str, str], Path], on_path: Path, tmp_path: Path, name: str
) -> None:
    make_tool(name, "exec sleep 5")

    with pytest.raises(subprocess.TimeoutExpired):
        run(name, tmp_path, timeout=0.2)


@pytest.mark.parametrize("name", ["hmmscan", "hmmsearch"])
def test_no_time_limit_lets_the_tool_finish(
    make_tool: Callable[[str, str], Path], on_path: Path, tmp_path: Path, name: str
) -> None:
    make_tool(name, "sleep 0.3; exit 0")

    assert run(name, tmp_path, timeout=None).returncode == 0


@pytest.mark.parametrize("name", ["hmmscan", "hmmsearch"])
def test_a_tool_not_on_path_is_an_os_error(on_path: Path, tmp_path: Path, name: str) -> None:
    with pytest.raises(FileNotFoundError, match=f"no {name} on PATH"):
        run(name, tmp_path, timeout=10)


def run(name: str, folder: Path, *, timeout: float | None) -> subprocess.CompletedProcess[str]:
    if name == "hmmscan":
        return hmmer.hmmscan(
            Path("db"), Path("q"), table=folder / "t", cpu=0, timeout=timeout, cwd=folder
        )
    return hmmer.hmmsearch(
        Path("m"), Path("q"), report=folder / "r", cpu=0, timeout=timeout, cwd=folder
    )
