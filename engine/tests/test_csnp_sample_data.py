"""The cSNP data sample, read with the strict readers. Needs the sample in the data folder."""

import json
from pathlib import Path

import pytest

from panther_engine.core.manifest import sha256_file
from panther_engine.csnp import legacy, sample
from panther_engine.csnp.library import LibraryFormatError, open_lines
from panther_engine.csnp.orig_tree import read_orig_tree
from panther_engine.csnp.paml import read_header, read_paml
from panther_engine.csnp.rst import read_rst
from panther_engine.csnp.sample import write_tarball
from panther_engine.csnp.species import read_species
from panther_engine.csnp.survey import BLAST_CHECKS, survey

pytestmark = pytest.mark.data("csnp")

MANIFEST = json.loads(sample.MANIFEST.read_text(encoding="utf-8"))
FAMILIES: list[str] = MANIFEST["families"]
READERS = {"paml": read_paml, "rst": read_rst, "orig.tree": read_orig_tree}
# Each sample file the strict readers reject, with the start of its error, as the library survey
# found them. The four known broken files (DATA-1) are the .rst of PTHR11711 and PTHR19241 and the
# .paml of PTHR21493 and PTHR23125_2.
NO_SEQUENCES = ".rst: no line 'List of extant and reconstructed sequences'"
REJECTED: dict[tuple[str, str], str] = {
    ("PTHR11711", "rst"): "PTHR11711.rst: empty file",
    ("PTHR19241", "rst"): "PTHR19241.rst: empty file",
    ("PTHR21493", "paml"): "PTHR21493.paml, line 2: no root",
    ("PTHR23125_2", "paml"): "PTHR23125_2.paml, line 2: no root",
    ("PTHR11711", "paml"): "PTHR11711.paml, line 4: not a row 'Site 1' of 615 residues",
    ("PTHR19241", "paml"): "PTHR19241.paml, line 4: not a row 'Site 1' of 615 residues",
    ("PTHR21493", "rst"): f"PTHR21493{NO_SEQUENCES}",
    ("PTHR23125_2", "rst"): f"PTHR23125_2{NO_SEQUENCES}",
    ("PTHR24073_10_1", "paml"): "PTHR24073_10_1.paml, line 2: column 1's parent, Node359,",
    ("PTHR24073_10_1", "rst"): f"PTHR24073_10_1{NO_SEQUENCES}",
}
# Legacy behaviour spec §7.1: the first digits of each golden family file's sha256.
GOLDEN = {
    "PTHR10366.paml": "bfcc359dfa90",
    "PTHR10366.rst": "137c6a7c17c7",
    "PTHR10366.orig.tree": "15717561b5a3",
    "PTHR15126.paml": "92cb57457d24",
    "PTHR15126.rst": "c6089bb3e49f",
    "PTHR15126.orig.tree": "ca777eaf3d3e",
}
# The checks that found something in the full library (docs/parity/csnp-library-survey.md),
# without the BLAST checks, which need the BLAST archive.
FULL_LIBRARY_FOUND = [
    "split-without-base",
    "rejected-paml",
    "rejected-rst",
    "unreconstructed",
    "internal-without-an",
    "extra-parenthesis",
    "legacy-start-column",
    "event-0>0",
    "event-other",
    "missing-taxon",
]


def library_file(csnp_data: Path, family: str, kind: str) -> Path:
    return csnp_data / sample.LIBRARY / f"{family}.{kind}"


def test_the_sample_matches_its_manifest(csnp_data: Path) -> None:
    mismatches = sample.verify_folder(csnp_data.parents[1])

    assert mismatches.missing == ()
    assert mismatches.differing == ()


@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("kind", READERS)
def test_every_sample_file_reads_or_raises_the_error_the_survey_found(
    csnp_data: Path, family: str, kind: str
) -> None:
    path = library_file(csnp_data, family, kind)
    if not path.exists():
        pytest.skip(f"the sample has no {path.name}: the family lacks it")
    expected = REJECTED.get((family, kind))
    if expected is None:
        READERS[kind](open_lines(path), path.name)
    else:
        with pytest.raises(LibraryFormatError) as raised:
            READERS[kind](open_lines(path), path.name)
        assert str(raised.value).startswith(expected)


def test_the_golden_families_and_the_species_tree_match_spec_7_1(csnp_data: Path) -> None:
    for name, prefix in GOLDEN.items():
        assert sha256_file(csnp_data / sample.LIBRARY / name).startswith(prefix), name
    assert sha256_file(csnp_data / sample.SPECIES) == sample.PINNED_SPECIES


def test_the_species_tree_gives_each_taxon_its_age(csnp_data: Path) -> None:
    ages = read_species(open_lines(csnp_data / sample.SPECIES), sample.SPECIES)

    assert ages["LUCA"] == 4200
    # Written `[&&NXH:S=Eukaryota:A=1628]`
    assert ages["Eukaryota"] == 1628
    assert ages == legacy.species_ages(next(open_lines(csnp_data / sample.SPECIES)))


def test_del28_starts_from_an_internal_node_in_the_legacy_reading(csnp_data: Path) -> None:
    # Q9H2F3, AN 911, in PTHR10366: SCORE-2, legacy behaviour spec §6.
    paml = library_file(csnp_data, "PTHR10366", "paml")
    tree = read_orig_tree(open_lines(library_file(csnp_data, "PTHR10366", "orig.tree")), "tree")
    assert tree.genes[911] == "HUMAN|Ensembl=ENSG00000099377|UniProtKB=Q9H2F3"

    header = read_header(open_lines(paml), paml.name)
    rows = legacy.paml_rows(open_lines(paml))

    assert [column for column in header.leaves if header.ans[column - 1] == 911] == [1238]
    assert legacy.start_node(rows, "911") == 1380


def test_the_golden_families_rst_reads_their_sequences(csnp_data: Path) -> None:
    rst = library_file(csnp_data, "PTHR15126", "rst")

    sequences = read_rst(open_lines(rst), rst.name).sequences

    assert len(sequences) == 22
    assert {len(sequence) for sequence in sequences.values()} == {752}


def test_surveying_the_sample_finds_every_variant_the_full_library_has(
    csnp_data: Path, tmp_path: Path
) -> None:
    files = {
        f"{sample.FOLDER}/{path.relative_to(csnp_data)}": path
        for path in sorted(csnp_data.rglob("*"))
        if path.is_file() and f"{sample.FOLDER}/{path.relative_to(csnp_data)}" in MANIFEST["files"]
    }
    tarball = tmp_path / "sample.tar.gz"
    write_tarball(tarball, files, compresslevel=1)

    report = survey(tarball, species=csnp_data / sample.SPECIES)

    found = set(report.found())
    assert found.isdisjoint(BLAST_CHECKS)
    assert [key for key in FULL_LIBRARY_FOUND if key not in found] == []
