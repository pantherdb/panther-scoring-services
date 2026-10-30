"""Generating parity cases, and comparing outputs, without the data sample: on the fixture families
in test_csnp_psep.py's data folder."""

import shutil
from pathlib import Path

import pytest
from csnp_fixtures import FIXTURES

from panther_engine.csnp import legacy, parity

FAMILY = "PTHR00004"
BROKEN = "PTHR00005"


@pytest.fixture
def data(tmp_path: Path) -> Path:
    folder = tmp_path / "csnp" / "9"
    library = folder / "PAML_RST"
    library.mkdir(parents=True)
    for kind in ("paml", "rst", "orig.tree"):
        shutil.copy(FIXTURES / f"{FAMILY}.{kind}", library / f"{FAMILY}.{kind}")
    shutil.copy(FIXTURES / "empty.rst", library / f"{BROKEN}.rst")
    shutil.copy(FIXTURES / "no-root.paml", library / f"{BROKEN}.paml")
    shutil.copy(FIXTURES / "PTHR00001.orig.tree", library / f"{BROKEN}.orig.tree")
    shutil.copy(FIXTURES / "species.nhx", folder / "species_pthr8_time.nhx")
    return folder


def generate(data: Path, out: Path, seed: str = "1") -> dict[str, bytes]:
    parity.write_cases(out, data, seed=seed)
    return {
        str(path.relative_to(out)): path.read_bytes()
        for path in sorted(out.rglob("*"))
        if path.is_file()
    }


def rows(out: Path, family: str) -> dict[str, list[str]]:
    """The family's cases, by SNP id: the snpParse fields."""
    text = parity.read(out / parity.STEP3 / f"{family}.snpparse")
    return {
        line.split(",")[0]: line.removesuffix("\n").split(",") for line in legacy.lines_of(text)
    }


def letters(an: str) -> str:
    sequences = legacy.sequences(legacy.lines_of(parity.read(FIXTURES / f"{FAMILY}.rst")))
    return "".join(character for character in sequences[an] if character.isupper())


def test_the_same_seed_gives_identical_cases(data: Path, tmp_path: Path) -> None:
    assert generate(data, tmp_path / "a") == generate(data, tmp_path / "b")


def test_another_seed_gives_other_cases(data: Path, tmp_path: Path) -> None:
    first = generate(data, tmp_path / "a", "1")
    second = generate(data, tmp_path / "b", "2")

    assert first.keys() == second.keys()
    assert first != second


def test_the_cases_list_every_family_and_step_2_run(data: Path, tmp_path: Path) -> None:
    out = tmp_path / "cases"
    generate(data, out)

    cases = parity.read_cases(out)

    assert cases.step3 == (FAMILY, BROKEN)
    assert (cases.seed, cases.genes, cases.positions) == ("1", 5, 8)
    for run in cases.step2:
        assert (out / parity.STEP2 / f"{run.name}.blast").is_file()
        assert (out / parity.STEP2 / f"{run.name}.input").is_file()


def test_each_gene_gets_both_ends_one_past_the_end_and_a_wrong_wild_type(
    data: Path, tmp_path: Path
) -> None:
    out = tmp_path / "cases"
    generate(data, out)
    cases = rows(out, FAMILY)
    genes = {snp_id.split("-", 1)[0] for snp_id in cases if snp_id.startswith("g")}

    assert len(genes) == 5
    for gene in sorted(genes):
        an = legacy.GeneLookup(legacy.lines_of(parity.read(FIXTURES / f"{FAMILY}.orig.tree")))
        found = an.find_an(cases[f"{gene}-start"][3])
        residues = letters(str(found))
        start, end, past = (cases[f"{gene}-{label}"] for label in ("start", "end", "past-end"))
        assert (start[5], start[6]) == ("1", residues[0])
        assert (end[5], end[6]) == (str(len(residues)), residues[-1])
        assert past[5] == str(len(residues) + 1)
        wrong = cases[f"{gene}-wrong-wt"]
        assert wrong[6] != residues[int(wrong[5]) - 1]


def test_each_family_gets_a_no_family_row_and_an_unmapped_row(data: Path, tmp_path: Path) -> None:
    out = tmp_path / "cases"
    generate(data, out)

    for family in (FAMILY, BROKEN):
        cases = rows(out, family)
        assert not (data / "PAML_RST" / f"{cases['no-family'][2]}.paml").exists()
        assert cases["unmapped"][2] == family
        assert cases["unmapped"][5] == ""


def test_the_genes_cover_every_kind_of_node_on_the_familys_paths(
    data: Path, tmp_path: Path
) -> None:
    out = tmp_path / "cases"
    generate(data, out)

    walks = parity.trace_cases(out, data)

    # The walks of PTHR00004's cases stop at nodes of every kind it has.
    stopped = {walk.kinds[-1] for walk in walks if walk.family == FAMILY}
    assert stopped >= {"0>1", "1>0", "0>0", "missing taxon", "Ev=UNK, not read"}


def test_step_2_cases_hold_ties_species_substrings_and_alignments_with_gaps(
    tmp_path: Path, data: Path
) -> None:
    out = tmp_path / "cases"
    generate(data, out)
    blast = parity.read(out / parity.STEP2 / "listed.blast")

    assert "MK-VL" in blast  # a gap in the query
    assert "UniProtKB=a00001" in blast  # a tie broken by case
    assert "RAT" in parity.read(out / parity.STEP2 / "species.blast")


def test_a_difference_names_its_case_and_line() -> None:
    expected = "a,A1V,PTHR1,10,probably benign,0.02\nb,A2V,PTHR1,10,probably benign,0.02\n"
    actual = expected.replace("b,A2V,PTHR1,10", "b,A2V,PTHR1,11")

    differences = parity.diff_records(expected, actual, "PTHR1")

    assert len(differences) == 1
    assert differences[0].startswith("PTHR1, case b (line 2): expected ")


def test_a_carriage_return_doesnt_split_a_record() -> None:
    text = "e10,A10E\r,PTHR10366,220,possibly damaging,0.50\n"

    assert parity.diff_records(text, text, "spec") == []
    assert parity.diff_records(text, text.replace("\r", ""), "spec")[0].startswith(
        "spec, case e10 (line 1)"
    )


def test_a_missing_or_extra_row_is_a_difference() -> None:
    expected = "a,x\nb,y\n"

    assert parity.diff_records(expected, "a,x\n", "f") == [
        "f, case b (line 2): expected 'b,y\\n', got None"
    ]
