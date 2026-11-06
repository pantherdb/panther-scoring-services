import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from panther_engine.cli import main
from panther_engine.refmap import parity

GOLDEN = Path(__file__).parent / "golden" / "refmap"
# A stand-in for perl: prints its arguments, one per line, then the gene list it was given.
FAKE_PERL = 'printf "%s\\n" "$@"; cat "$5"'


@pytest.fixture
def golden(tmp_path: Path) -> Path:
    """A copy of the golden folder, without out/."""
    folder = tmp_path / "golden"
    shutil.copytree(GOLDEN, folder, ignore=shutil.ignore_patterns("out"))
    return folder


@pytest.fixture
def data(tmp_path: Path) -> Path:
    """A data folder with a file for ENDPU."""
    root = tmp_path / "data"
    folder = root / "refmap" / "19" / "panther_classification"
    folder.mkdir(parents=True)
    (folder / "ENDPU").write_bytes(b"U1G4Q5\tPTHR11360:SF130\n")
    return root


def test_the_cases_are_read_in_order() -> None:
    cases = parity.read_cases(GOLDEN)

    assert [case.name for case in cases[:2]] == ["test_geneList", "test_geneList_values"]
    assert len({case.name for case in cases}) == len(cases)
    for case in cases:
        assert (case.organism is None) != (case.file is None)
        assert (case.refused is None) == (case.divergence is None)


def test_each_case_runs_the_script_on_its_file_and_list(
    golden: Path, data: Path, make_tool: Callable[[str, str], Path]
) -> None:
    reference = parity.Reference(make_tool("perl", FAKE_PERL), Path("/opt/x/map_panther.pl"))

    counts = parity.run_reference(reference, golden, data)

    cases = parity.read_cases(golden)
    assert list(counts) == [case.name for case in cases]
    endpu = (golden / "out" / "repeats.out").read_bytes()
    assert (
        endpu
        == (
            f"/opt/x/map_panther.pl\n-i\n{data}/refmap/19/panther_classification/ENDPU\n"
            f"-g\n{golden}/cases/repeats.list\n"
        ).encode()
        + (golden / "cases" / "repeats.list").read_bytes()
    )
    made_up = (golden / "out" / "crlf.out").read_bytes()
    assert f"-i\n{golden}/cases/crlf.classification\n".encode() in made_up
    unknown = (golden / "out" / "unknown-organism.out").read_bytes()
    assert f"-i\n{data}/refmap/19/panther_classification/HUMAN\n".encode() in unknown


def test_a_published_organism_without_its_file_stops_the_run(
    golden: Path, data: Path, make_tool: Callable[[str, str], Path]
) -> None:
    (data / "refmap" / "19" / "panther_classification" / "ENDPU").unlink()
    reference = parity.Reference(make_tool("perl", FAKE_PERL))

    with pytest.raises(parity.ParityError, match="ENDPU"):
        parity.run_reference(reference, golden, data)

    assert not (golden / "out").exists()


def test_a_failed_run_names_the_case(
    golden: Path, data: Path, make_tool: Callable[[str, str], Path]
) -> None:
    reference = parity.Reference(make_tool("perl", "echo broken >&2; exit 2"))

    with pytest.raises(parity.ParityError, match=r"test_geneList.*status 2.*broken"):
        parity.run_reference(reference, golden, data)


def test_a_case_with_a_path_outside_the_golden_folder_is_refused(golden: Path) -> None:
    listed = json.loads((golden / "cases.json").read_text())
    listed["cases"][0]["list"] = "../../etc/passwd"
    (golden / "cases.json").write_text(json.dumps(listed))

    with pytest.raises(parity.ParityError, match="etc/passwd"):
        parity.read_cases(golden)


# The full run


IDS = [f"A0A{n:05d}" for n in range(100)]
OTHER = [f"B0B{n:05d}" for n in range(100)]


def test_the_same_seed_gives_the_same_extras() -> None:
    assert parity.extras(IDS, OTHER, "port-refmap", "ENDPU") == parity.extras(
        IDS, OTHER, "port-refmap", "ENDPU"
    )


def test_another_seed_or_organism_gives_other_extras() -> None:
    first = parity.extras(IDS, OTHER, "port-refmap", "ENDPU")

    assert parity.extras(IDS, OTHER, "another", "ENDPU") != first
    assert parity.extras(IDS, OTHER, "port-refmap", "PEA") != first


def test_each_kind_of_extra_is_there() -> None:
    extras = parity.extras(IDS, OTHER, "port-refmap", "ENDPU")

    assert len(extras) == 100
    repeated, lower, isoform, version, other = (extras[n : n + 20] for n in range(0, 100, 20))
    assert set(repeated) <= set(IDS)
    assert all(id.lower() == id and id.upper() in IDS for id in lower)
    assert all(id.endswith("-2") and id[:-2] in IDS for id in isoform)
    assert all(id.endswith(".1") and id[:-2] in IDS for id in version)
    assert set(other) <= set(OTHER)
    assert len(set(repeated)) == 20


def test_a_small_file_gives_fewer_extras() -> None:
    extras = parity.extras(["A1", "A2"], ["B1"], "port-refmap", "ENDPU")

    assert sorted(extras) == sorted(["A1", "A2", "a1", "a2", "A1-2", "A2-2", "A1.1", "A2.1", "B1"])


# Stands in for map_panther.pl, for files without CRLF endings or empty values. It changes the
# first PTHR00002 it prints to PTHR99999: one difference.
FAKE_MAP_PANTHER = r"""
awk -F '\t' '
  NR == FNR { if (NF > 1) value[$1] = $2; else delete value[$1]; next }
  { gsub(/\r/, ""); id = $1
    line = (id in value) ? id "\t" value[id] "\t" : id "\tNOHIT\t"
    if (!changed && sub(/PTHR00002/, "PTHR99999", line)) changed = 1
    print line }
' "$3" "$5"
"""


@pytest.fixture
def two_organisms(tmp_path: Path) -> Path:
    root = tmp_path / "full"
    folder = root / "refmap" / "19" / "panther_classification"
    folder.mkdir(parents=True)
    (folder / "ENDPU").write_bytes(b"E1\tPTHR00001\nE2\tNOHIT\nE3\tPTHR00003:SF1\n")
    (folder / "PEA").write_bytes(b"P1\tNOHIT\nP2\tPTHR00002\n")
    return root


def full(root: Path, script: Path, *args: str) -> int:
    return main(
        ["refmap", "parity", "full", "--data-dir", str(root), "--script", str(script), *args]
    )


def test_the_full_run_reports_a_difference_and_fails(
    two_organisms: Path,
    tmp_path: Path,
    make_tool: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    perl = make_tool("perl", FAKE_MAP_PANTHER)
    monkeypatch.setenv("PATH", f"{perl.parent}:{os.environ['PATH']}")
    script = tmp_path / "map_panther.pl"
    script.touch()

    status = full(two_organisms, script, "--organism", "ENDPU", "--organism", "PEA")

    captured = capsys.readouterr()
    assert status == 1
    endpu = 3 + 3 + 3 + 3 + 3 + 2
    pea = 2 + 2 + 2 + 2 + 2 + 3
    assert f"ENDPU: {endpu} IDs, 0 differences" in captured.out
    assert f"PEA: {pea} IDs, 1 differences" in captured.out
    assert (
        "PEA line 2: the reference has 'P2\\tPTHR99999', the port 'P2\\tPTHR00002'" in captured.out
    )
    assert f"2 organisms, {endpu + pea} IDs compared, 1 differences" in captured.err


def test_the_full_run_passes_when_the_perl_agrees(
    two_organisms: Path,
    tmp_path: Path,
    make_tool: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    perl = make_tool("perl", FAKE_MAP_PANTHER.replace("PTHR99999", "PTHR00002"))
    monkeypatch.setenv("PATH", f"{perl.parent}:{os.environ['PATH']}")
    script = tmp_path / "map_panther.pl"
    script.touch()

    assert full(two_organisms, script, "--organism", "ENDPU", "--organism", "PEA") == 0
    assert "2 organisms, 30 IDs compared, no differences" in capsys.readouterr().out


def test_the_full_run_needs_every_organisms_file(
    two_organisms: Path,
    tmp_path: Path,
    make_tool: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    perl = make_tool("perl", FAKE_MAP_PANTHER)
    monkeypatch.setenv("PATH", f"{perl.parent}:{os.environ['PATH']}")
    script = tmp_path / "map_panther.pl"
    script.touch()

    status = full(two_organisms, script, "--organism", "ENDPU", "--organism", "ARAVE")

    assert status == 1
    assert "ARAVE" in capsys.readouterr().err
