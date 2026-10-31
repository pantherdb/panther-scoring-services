"""The port against the reference's goldens, byte for byte: the legacy behaviour spec's §7.3 and
§7.5, and the reference image's output for the generated cases and for the scoring form's example
(tests/golden/csnp/README.md).

Step 2 needs no data. Step 3 reads the data sample's library. The comparison functions are the ones
`panther-engine csnp parity check` runs.
"""

import shutil
from pathlib import Path

import pytest

from panther_engine.csnp import blast, hits, legacy, parity, psep

GOLDEN = Path(__file__).parent / "golden" / "csnp"
CASES = GOLDEN / "generated"
LISTED = parity.read_cases(CASES)
# The scoring form's example: the legacy site's human APOE, with its four substitutions.
EXAMPLE = GOLDEN / "example"
# The sample families whose .rst has no sequence list: their files are broken (DATA-1).
NO_SEQUENCES = ("PTHR11711", "PTHR19241", "PTHR21493", "PTHR23125_2", "PTHR24073_10_1")


def step2(snps: str, species: str) -> str:
    blast = legacy.lines_of(parity.read(GOLDEN / "release" / "HUMAN"))
    return "".join(hits.parse(blast, hits.read_snps(parity.read(GOLDEN / snps)), species))


# Step 2


def test_step_2_on_the_release_sample_gives_the_references_snpparse() -> None:
    expected = parity.read(CASES / "sample.snpparse")

    assert parity.diff_records(expected, step2("release/sample.input", "HUMAN"), "sample") == []


def test_step_2_on_the_edge_cases_gives_the_references_snpparse() -> None:
    expected = parity.read(CASES / "edge-cases.snpparse")

    assert parity.diff_records(expected, step2("spec/edge-cases.input", "NA"), "edge") == []


@pytest.mark.parametrize("run", LISTED.step2, ids=lambda run: run.name)
def test_step_2_on_each_generated_run_gives_the_references_snpparse(run: parity.Step2Run) -> None:
    assert parity.check_step2(CASES, run) == []


# Step 3


@pytest.mark.data("csnp")
def test_steps_2_and_3_give_the_spec_goldens(csnp_data: Path) -> None:
    assert parity.check_self(GOLDEN, CASES, csnp_data) == []


@pytest.mark.data("csnp")
def test_steps_2_and_3_on_the_forms_example_give_the_references_output(csnp_data: Path) -> None:
    lines = legacy.lines_of(parity.read(GOLDEN / "blast" / "APOE.csv"))
    snps = hits.read_snps(parity.read(EXAMPLE / "apoe.input"))

    parsed = "".join(hits.parse(lines, snps, "HUMAN"))
    result = "".join(psep.step3(legacy.lines_of(parsed), csnp_data))

    assert parity.diff_records(parity.read(EXAMPLE / "apoe.snpparse"), parsed, "example") == []
    assert parity.diff_records(parity.read(EXAMPLE / "apoe.out"), result, "example") == []


@pytest.mark.data("csnp")
@pytest.mark.parametrize("family", LISTED.step3)
def test_step_3_on_each_familys_cases_gives_the_references_output(
    family: str, csnp_data: Path
) -> None:
    assert parity.check_step3(CASES, family, csnp_data) == []


@pytest.mark.data("csnp")
@pytest.mark.parametrize("family", NO_SEQUENCES)
def test_a_family_with_broken_files_gives_invalid_substitution(
    family: str, csnp_data: Path
) -> None:
    rows = legacy.lines_of(parity.read(CASES / parity.STEP3 / f"{family}.snpparse"))
    genes = [row for row in rows if row.startswith("g")]

    results = psep.step3(genes, csnp_data)

    assert results
    assert {result.removesuffix("\n").split(",", 2)[2] for result in results} == {psep.INVALID}


@pytest.mark.data("csnp")
def test_a_golden_row_changed_by_hand_fails_naming_its_case(
    csnp_data: Path, tmp_path: Path
) -> None:
    copy = tmp_path / "cases"
    shutil.copytree(CASES, copy)
    golden = copy / parity.STEP3 / "PTHR10366.out"
    rows = legacy.lines_of(parity.read(golden))
    scored = next(index for index, row in enumerate(rows) if row.count(",") == 5)
    case = rows[scored].split(",", 1)[0]
    rows[scored] = rows[scored].rsplit(",", 1)[0] + ",9.99\n"
    parity.write(golden, "".join(rows))

    differences = parity.check_step3(copy, "PTHR10366", csnp_data)

    assert len(differences) == 1
    assert differences[0].startswith(f"PTHR10366, case {case} (line {scored + 1})")


# Step 1


def sample_proteins() -> dict[str, str]:
    proteins: dict[str, str] = {}
    for block in parity.read(GOLDEN / "release" / "sample.fasta").split(">")[1:]:
        name, _, sequence = block.partition("\n")
        proteins[name.strip()] = "".join(sequence.split())
    return proteins


@pytest.mark.tools("blastp")
@pytest.mark.data("csnp")
@pytest.mark.parametrize("protein", ["P26439", "Q9H2F3", "P78314"])
def test_step_1_gives_the_blast_golden_and_the_human_fixtures_best_hit(
    protein: str, csnp_data: Path
) -> None:
    lines = blast.search(sample_proteins()[protein], csnp_data)

    assert "".join(lines) == parity.read(GOLDEN / "blast" / f"{protein}.csv")
    best = hits.best_hits(lines, "HUMAN")[blast.QUERY]
    fixture = next(
        line.split(",")
        for line in legacy.lines_of(parity.read(GOLDEN / "release" / "HUMAN"))
        if line.startswith(f"{protein},")
    )
    fields = (hits.SSEQID, hits.QSTART, hits.SSTART, hits.QSEQ, hits.SSEQ)
    assert (best.sseqid, best.qstart, best.sstart, best.qseq, best.sseq) == tuple(
        fixture[field] for field in fields
    )


@pytest.mark.tools("blastp")
@pytest.mark.data("csnp")
def test_step_1_on_the_forms_example_gives_its_blast_golden(csnp_data: Path) -> None:
    # Its own test: the HUMAN fixture above has no APOE to compare the best hit with.
    sequence = "".join(parity.read(EXAMPLE / "apoe.fasta").partition("\n")[2].split())

    lines = blast.search(sequence, csnp_data)

    assert "".join(lines) == parity.read(GOLDEN / "blast" / "APOE.csv")
