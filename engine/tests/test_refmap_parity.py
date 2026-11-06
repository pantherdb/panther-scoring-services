import json
import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from panther_engine.cli import main
from panther_engine.refmap import ORGANISM_NAMES, parity

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


CODES = list(ORGANISM_NAMES)


def successor(code: str) -> str:
    """The organism after `code` in the published list, whose IDs give `code`'s last extras."""
    return CODES[(CODES.index(code) + 1) % len(CODES)]


@pytest.fixture
def two_organisms(tmp_path: Path) -> Path:
    """A data folder with made-up files for ENDPU and PEA, and for the organism after each."""
    root = tmp_path / "full"
    folder = root / "refmap" / "19" / "panther_classification"
    folder.mkdir(parents=True)
    (folder / "ENDPU").write_bytes(b"E1\tPTHR00001\nE2\tNOHIT\nE3\tPTHR00003:SF1\n")
    (folder / "PEA").write_bytes(b"P1\tNOHIT\nP2\tPTHR00002\n")
    for code in ("ENDPU", "PEA"):
        (folder / successor(code)).write_bytes(b"N1\tNOHIT\nN2\tPTHR00004\n")
    return root


@pytest.fixture
def fake_perl(
    tmp_path: Path, make_tool: Callable[[str, str], Path], monkeypatch: pytest.MonkeyPatch
) -> Callable[[str], Path]:
    """Returns `make(script)`: puts a fake `perl` running `script` first on PATH, and returns a
    stand-in for map_panther.pl to pass as --script."""

    def make(script: str) -> Path:
        perl = make_tool("perl", script)
        monkeypatch.setenv("PATH", f"{perl.parent}:{os.environ['PATH']}")
        stand_in = tmp_path / "map_panther.pl"
        stand_in.touch()
        return stand_in

    return make


def full(root: Path, script: Path, *args: str) -> int:
    return main(
        ["refmap", "parity", "full", "--data-dir", str(root), "--script", str(script), *args]
    )


# ENDPU: 3 IDs, 3 of each kind of its own extras, and 2 from the next organism's file.
ENDPU_IDS = 3 + 3 * 4 + 2
# PEA: 2 IDs, 2 of each kind of its own extras, and 2 from the next organism's file.
PEA_IDS = 2 + 2 * 4 + 2


def test_the_full_run_reports_a_difference_and_fails(
    two_organisms: Path,
    fake_perl: Callable[[str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = fake_perl(FAKE_MAP_PANTHER)

    status = full(two_organisms, script, "--organism", "ENDPU", "--organism", "PEA")

    captured = capsys.readouterr()
    assert status == 1
    assert f"ENDPU: {ENDPU_IDS} IDs, 0 differences" in captured.out
    assert f"PEA: {PEA_IDS} IDs, 1 differences" in captured.out
    assert (
        "PEA line 2: the reference has 'P2\\tPTHR99999', the port 'P2\\tPTHR00002'" in captured.out
    )
    assert f"2 organisms, {ENDPU_IDS + PEA_IDS} IDs compared, 1 differences" in captured.err


def test_the_full_run_passes_when_the_perl_agrees(
    two_organisms: Path,
    fake_perl: Callable[[str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = fake_perl(FAKE_MAP_PANTHER.replace("PTHR99999", "PTHR00002"))

    assert full(two_organisms, script, "--organism", "ENDPU", "--organism", "PEA") == 0
    total = ENDPU_IDS + PEA_IDS
    assert f"2 organisms, {total} IDs compared, no differences" in capsys.readouterr().out


def test_one_organism_still_gets_the_next_organisms_ids(
    two_organisms: Path,
    fake_perl: Callable[[str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = fake_perl(FAKE_MAP_PANTHER.replace("PTHR99999", "PTHR00002"))

    assert full(two_organisms, script, "--organism", "ENDPU") == 0
    # With its own IDs in place of the next organism's, it would be 3 + 3 * 5.
    assert f"ENDPU: {ENDPU_IDS} IDs, 0 differences" in capsys.readouterr().out


def test_the_list_takes_its_last_extras_from_the_next_organism_in_the_order(
    two_organisms: Path,
) -> None:
    folder = two_organisms / "refmap" / "19" / "panther_classification"

    pea = parity.organism_list(folder, "PEA", "port-refmap", ["ENDPU", "PEA"])
    endpu = parity.organism_list(folder, "ENDPU", "port-refmap")

    assert pea[:2] == ["P1", "P2"]
    assert set(pea[-2:]) <= {"E1", "E2", "E3"}
    assert set(endpu[-2:]) == {"N1", "N2"}
    assert endpu == parity.organism_list(folder, "ENDPU", "port-refmap", CODES)


def test_the_full_run_needs_every_organisms_file_and_the_next_ones(
    two_organisms: Path,
    fake_perl: Callable[[str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = fake_perl(FAKE_MAP_PANTHER)
    folder = two_organisms / "refmap" / "19" / "panther_classification"
    (folder / successor("PEA")).unlink()

    assert full(two_organisms, script, "--organism", "ENDPU", "--organism", "ARAVE") == 1
    assert "ARAVE" in capsys.readouterr().err
    assert full(two_organisms, script, "--organism", "PEA") == 1
    assert successor("PEA") in capsys.readouterr().err


def test_the_full_run_refuses_an_organism_refmap_doesnt_publish(
    two_organisms: Path,
    fake_perl: Callable[[str], Path],
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = fake_perl(FAKE_MAP_PANTHER)

    assert full(two_organisms, script, "--organism", "HUMAN") == 1
    assert "'HUMAN'" in capsys.readouterr().err


# A failed reference run


def test_a_failed_run_leaves_the_goldens_as_they_were(
    tmp_path: Path, data: Path, make_tool: Callable[[str, str], Path]
) -> None:
    golden = tmp_path / "committed"
    shutil.copytree(GOLDEN, golden)
    before = {path.name: path.read_bytes() for path in (golden / "out").iterdir()}
    # Succeeds until the crlf case, which comes after several others.
    perl = make_tool("perl", 'case "$5" in *crlf.list) echo broken >&2; exit 2 ;; esac; echo new')

    with pytest.raises(parity.ParityError, match="crlf"):
        parity.run_reference(parity.Reference(perl), golden, data)

    assert {path.name: path.read_bytes() for path in (golden / "out").iterdir()} == before
    assert sorted(path.name for path in golden.iterdir()) == sorted(
        path.name for path in GOLDEN.iterdir()
    )


def test_a_successful_run_replaces_every_output(
    tmp_path: Path, data: Path, make_tool: Callable[[str, str], Path]
) -> None:
    golden = tmp_path / "committed"
    shutil.copytree(GOLDEN, golden)

    parity.run_reference(parity.Reference(make_tool("perl", "echo new")), golden, data)

    assert {path.read_bytes() for path in (golden / "out").iterdir()} == {b"new\n"}
    assert sorted(path.name for path in golden.iterdir()) == sorted(
        path.name for path in GOLDEN.iterdir()
    )
