"""`score()`, the interface agreed on #19: its checks and its result without data, then the whole
pipeline with `blastp` and the data sample, against spec §7.3."""

import multiprocessing
import os
import shutil
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest

from panther_engine.core.errors import InputError
from panther_engine.core.process import run_tool
from panther_engine.csnp import SPECIES_CODES, CsnpInput, CsnpResult, SubstitutionScore, score
from panther_engine.csnp.blast import BlastError
from panther_engine.csnp.scoring import reported_family, to_score

GOLDEN = Path(__file__).parent / "golden" / "csnp"


def sample_proteins() -> dict[str, str]:
    """The release's sample.fasta, by id."""
    proteins: dict[str, str] = {}
    name = ""
    for line in (GOLDEN / "release" / "sample.fasta").read_text().splitlines():
        if line.startswith(">"):
            name = line[1:].strip()
            proteins[name] = ""
        elif line.strip():
            proteins[name] += line.strip()
    return proteins


def sample_rows() -> dict[str, list[tuple[str, list[str]]]]:
    """Spec §7.3's rows by protein, in order: each SNP's token, as a website user types it, and
    its output fields after the substitution."""
    inputs = (GOLDEN / "release" / "sample.input").read_text().splitlines()
    outputs = (GOLDEN / "spec" / "sample.out").read_text().splitlines()
    rows: dict[str, list[tuple[str, list[str]]]] = {}
    for line, output in zip(inputs, outputs, strict=True):
        _, protein, position, residues = line.split("|")
        wt, mut = residues.split(";")
        rows.setdefault(protein, []).append((f"{wt}{position}{mut.strip()}", output.split(",")[2:]))
    return rows


PROTEINS = sample_proteins()
ROWS = sample_rows()


def expected_result(protein: str) -> CsnpResult:
    rows = ROWS[protein]
    scores = tuple(
        SubstitutionScore(token, int(age), message, pdel) for token, (_, age, message, pdel) in rows
    )
    return CsnpResult(rows[0][1][0], scores)


def score_protein(protein: str, *tokens: str) -> CsnpResult:
    """Scores a sample protein for HUMAN, with its §7.3 substitutions by default."""
    substitutions = tokens or tuple(token for token, _ in ROWS[protein])
    return score(CsnpInput(PROTEINS[protein], substitutions, "HUMAN"))


# Without data


@pytest.fixture
def never_searched(make_tool: Callable[[str, str], Path], monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fake `blastp`, first on PATH, that leaves a marker if it runs."""
    tool = make_tool("blastp", 'touch "$(dirname "$0")/searched"')
    monkeypatch.setenv("PATH", f"{tool.parent}{os.pathsep}{os.environ['PATH']}")
    return tool.parent / "searched"


@pytest.mark.parametrize(
    "request_",
    [
        CsnpInput("MKVL", ("K2E",), "XXXXX"),
        CsnpInput("MKVL", ("K2E",), "human"),
        CsnpInput("MKVL", ("K2E", "k2e"), "HUMAN"),
        CsnpInput("MKVL", ("2KE",), "HUMAN"),
        CsnpInput("MKVL", ("K2E ",), "HUMAN"),
        CsnpInput("", ("K2E",), "HUMAN"),
        CsnpInput("MK VL", ("K2E",), "HUMAN"),
        CsnpInput("MKVLé", ("K2E",), "HUMAN"),
    ],
    ids=[
        "unknown species",
        "lower-case species",
        "lower-case token",
        "token order",
        "token space",
        "empty sequence",
        "space in sequence",
        "non-ASCII sequence",
    ],
)
def test_a_request_the_api_would_reject_is_a_value_error_and_nothing_is_searched(
    request_: CsnpInput, never_searched: Path, tmp_path: Path
) -> None:
    with pytest.raises(ValueError) as raised:
        score(request_, data_dir=tmp_path)

    assert not isinstance(raised.value, InputError)
    assert not never_searched.exists()


def test_the_species_codes_include_the_ones_the_spec_names() -> None:
    assert len(SPECIES_CODES) == 85
    assert {"HUMAN", "PLAF7", "SYNY3"} <= SPECIES_CODES


@pytest.mark.parametrize(
    ("field", "family"),
    [("PTHR23125_2", "PTHR23125"), ("PTHR10366", "PTHR10366"), ("AN12345", "AN12345"), ("", None)],
)
def test_the_family_is_cut_as_the_cgi_cut_it(field: str, family: str | None) -> None:
    assert reported_family(field) == family


def test_a_scored_record_becomes_a_score() -> None:
    record = "SNP_1,A10E,PTHR10366,220,possibly damaging,0.50\n"

    assert to_score(record) == SubstitutionScore("A10E", 220, "possibly damaging", "0.50")


def test_an_empty_age_becomes_none_and_keeps_its_message_and_pdel() -> None:
    record = "SNP_1,A10E,PTHR10366,,probably benign,0.02\n"

    assert to_score(record) == SubstitutionScore("A10E", None, "probably benign", "0.02")


def test_a_record_not_scored_has_no_age_and_no_pdel() -> None:
    record = "SNP_2,M1V,Not scored: Invalid substitution\n"

    assert to_score(record) == SubstitutionScore(
        "M1V", None, "Not scored: Invalid substitution", None
    )


def test_no_substitutions_give_no_family_and_nothing_is_searched(
    never_searched: Path, tmp_path: Path
) -> None:
    result = score(CsnpInput("MKVL", (), "HUMAN"), data_dir=tmp_path)

    assert result == CsnpResult(None, ())
    assert not never_searched.exists()


# With blastp and the data sample


@pytest.mark.tools("blastp")
@pytest.mark.data("csnp")
@pytest.mark.parametrize("protein", ["P26439", "Q9H2F3", "P78314"])
def test_each_sample_protein_gives_its_spec_7_3_rows(protein: str) -> None:
    assert score_protein(protein) == expected_result(protein)


@pytest.mark.tools("blastp")
@pytest.mark.data("csnp")
def test_a_proteins_scores_dont_depend_on_the_calls_before_it() -> None:
    first = score_protein("P78314")
    middle = score_protein("P26439")
    last = score_protein("P78314")

    assert first == last == expected_result("P78314")
    assert middle == expected_result("P26439")


@pytest.mark.tools("blastp")
@pytest.mark.data("csnp")
def test_a_leading_zero_is_kept_in_the_substitution_and_scored_as_the_position() -> None:
    result = score_protein("P26439", "A010E", "A10V")

    assert result.scores == (
        SubstitutionScore("A010E", 220, "possibly damaging", "0.50"),
        SubstitutionScore("A10V", 220, "possibly damaging", "0.50"),
    )


@pytest.mark.tools("blastp")
@pytest.mark.data("csnp")
def test_the_spec_7_5_cases_the_api_accepts() -> None:
    result = score_protein("P26439", "M1V", "G2V", "E10A", "Q372R", "X373R")

    assert [(item.age, item.message, item.pdel) for item in result.scores] == [
        (None, "Not scored: Invalid substitution", None),
        (910, "probably damaging", "0.85"),
        (None, "Not scored: Invalid substitution", None),
        (97, "probably benign", "0.19"),
        (None, "Not scored: Invalid substitution", None),
    ]


@pytest.mark.tools("blastp")
@pytest.mark.data("csnp")
def test_a_species_without_a_hit_gives_no_family() -> None:
    result = score(CsnpInput(PROTEINS["P26439"], ("A10E",), "PLAF7"))

    assert result == CsnpResult(
        None,
        (
            SubstitutionScore(
                "A10E", None, "Not scored: No PANTHER family for input sequence", None
            ),
        ),
    )


@pytest.mark.tools("blastp")
@pytest.mark.data("csnp")
def test_a_query_blastp_cant_read_is_an_input_error() -> None:
    # blastp 2.17.0 exits with status 1: "a line that doesn't look like plausible data".
    with pytest.raises(InputError) as raised:
        score(CsnpInput("1234567890", ("A10E",), "HUMAN"))

    message = str(raised.value)
    assert "BLAST" not in message
    assert "/" not in message


@pytest.mark.tools("blastp")
@pytest.mark.data("csnp")
def test_a_data_folder_without_the_database_is_a_failure_not_an_input_error(
    tmp_path: Path,
) -> None:
    with pytest.raises(BlastError) as raised:
        score(CsnpInput(PROTEINS["P26439"], ("A10E",), "HUMAN"), data_dir=tmp_path)

    assert not isinstance(raised.value, InputError)


@pytest.mark.tools("blastp")
@pytest.mark.data("csnp")
def test_two_proteins_scored_at_the_same_time_get_their_own_results() -> None:
    with ProcessPoolExecutor(2, mp_context=multiprocessing.get_context("spawn")) as pool:
        futures = {protein: pool.submit(score_protein, protein) for protein in ("P26439", "P78314")}
        results = {protein: future.result(timeout=300) for protein, future in futures.items()}

    assert results == {protein: expected_result(protein) for protein in results}


@pytest.mark.tools("blastdbcmd")
@pytest.mark.data("csnp")
def test_the_species_codes_are_the_blast_databases(csnp_data: Path) -> None:
    program = shutil.which("blastdbcmd")
    assert program is not None
    database = str(csnp_data / "blast" / "blast")

    result = run_tool(
        Path(program), ["-db", database, "-entry", "all", "-outfmt", "%t"], timeout=300
    )

    assert result.returncode == 0, result.stderr
    found = {title.split("|", 1)[0] for title in result.stdout.splitlines()}
    assert found == SPECIES_CODES


@pytest.mark.tools("blastp")
@pytest.mark.data("csnp")
def test_blastp_exits_with_3_for_a_sequence_it_reads_as_a_comment(csnp_data: Path) -> None:
    # Why search() refuses one before running blastp: BLAST+ finds no sequence, and fails with
    # "BLAST engine error: Warning: Sequence contains no data", which isn't status 1.
    program = shutil.which("blastp")
    assert program is not None
    database = str(csnp_data / "blast" / "blast")

    result = run_tool(Path(program), ["-db", database], timeout=300, input=">P0001\n#MKVL")

    assert result.returncode == 3
    assert "no data" in result.stderr


def test_score_raises_the_input_error_for_a_sequence_blast_reads_as_a_comment(
    never_searched: Path, tmp_path: Path
) -> None:
    with pytest.raises(InputError):
        score(CsnpInput(";MKVL", ("K2E",), "HUMAN"), data_dir=tmp_path)

    assert not never_searched.exists()
