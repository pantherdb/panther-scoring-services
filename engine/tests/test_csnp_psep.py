"""Step 3 on the hand-written fixture families (design.md, decision 5).

`PTHR00004` (csnp_fixtures.py) has a node of each kind: a leaf, a speciation, a duplication, a `0>0`
node, an `Ev=UNK` root and a speciation in Sauria, which the species tree lacks. Its ages:

| Node | Event | Age |
| ---- | ----- | --- |
| 11 | `0>1` Homo-Pan | 6 |
| 10 | `0>1` Euarchontoglires | 91 |
| 12 | `0>0` Homo-Pan | empty |
| 9 | `1>0`; children 10 and 12 | 92 |
| 13 | `0>1` Sauria, missing: a duplication; children are leaves | 1 |
| 8, the root | `Ev=UNK`: a duplication; children 9 and 13 | 93 |

The rows here were checked against `PANTHER_PSEP1.01.pl` in the reference image.
"""

import shutil
from pathlib import Path

import pytest
from csnp_fixtures import FIXTURES, edited, lines

from panther_engine.csnp.psep import message, pdel, step3

FAMILY = "PTHR00004"
BROKEN = "PTHR00005"
GENES = {
    20: "HUMAN|HGNC=20|UniProtKB=Q00020",
    21: "PANTR|Ensembl=ENSPTRG21|UniProtKB=Q00021",
    23: "HUMAN|HGNC=23|UniProtKB=Q00023",
    25: "CHICK|Ensembl=ENSGALG25|UniProtKB=Q00025",
}
NO_FAMILY = "Not scored: No PANTHER family for input sequence"
INVALID = "Not scored: Invalid substitution"


@pytest.fixture
def data(tmp_path: Path) -> Path:
    """A cSNP data folder with the fixture families and species tree."""
    folder = tmp_path / "csnp" / "9"
    library = folder / "PAML_RST"
    library.mkdir(parents=True)
    for kind in ("paml", "rst", "orig.tree"):
        shutil.copy(FIXTURES / f"{FAMILY}.{kind}", library / f"{FAMILY}.{kind}")
    # No sequence list, and a .paml the strict reader rejects.
    shutil.copy(FIXTURES / "empty.rst", library / f"{BROKEN}.rst")
    shutil.copy(FIXTURES / "no-root.paml", library / f"{BROKEN}.paml")
    shutil.copy(FIXTURES / "PTHR00001.orig.tree", library / f"{BROKEN}.orig.tree")
    shutil.copy(FIXTURES / "species.nhx", folder / "species_pthr8_time.nhx")
    return folder


def replace(data: Path, kind: str, old: str, new: str) -> None:
    """Edit the fixture family's file in the data folder: `old`, once, becomes `new`."""
    content = "".join(edited(f"{FAMILY}.{kind}", old, new))
    (data / "PAML_RST" / f"{FAMILY}.{kind}").write_bytes(content.encode("latin-1"))


def row(
    snp_id: str,
    an: int,
    mapped: str,
    wt: str,
    *,
    family: str = FAMILY,
    position: str | None = None,
    mut: str = "V",
) -> str:
    gene = GENES.get(an, "")
    return f"{snp_id},P0001,{family},{gene},{position or mapped},{mapped},{wt},{mut}\n"


def scored(data: Path, *rows: str) -> list[str]:
    """Each result row without its SNP id and substitution: `family,age,message,pDel`, or the
    message alone where it isn't scored."""
    return [line.removesuffix("\n").split(",", 2)[2] for line in step3(rows, data)]


# The walk


def test_a_site_kept_up_to_the_root_gives_the_roots_age(data: Path) -> None:
    assert scored(data, row("s", 20, "1", "M")) == [f"{FAMILY},93,probably benign,0.19"]


def test_the_walk_stops_at_the_first_node_not_kept_and_gives_its_age(data: Path) -> None:
    # Node 10's probability is 0.500.
    assert scored(data, row("s", 20, "2", "A")) == [f"{FAMILY},91,probably benign,0.19"]


def test_a_probability_of_0_99_isnt_kept_but_0_991_is(data: Path) -> None:
    # AN25: node 13 has 0.990. AN23 at site 4: node 12 has 0.991, node 9 has 0.200.
    assert scored(data, row("a", 25, "3", "K"), row("b", 23, "3", "L")) == [
        f"{FAMILY},1,probably benign,0.02",
        f"{FAMILY},92,probably benign,0.19",
    ]


def test_an_unreconstructed_cell_stops_the_walk(data: Path) -> None:
    # Node 11 has a NUL residue and -nan at site 3.
    assert scored(data, row("s", 20, "3", "K")) == [f"{FAMILY},6,probably benign,0.02"]


def test_the_walk_starts_at_the_last_header_column_labelled_with_the_an(data: Path) -> None:
    # SCORE-2: column 13 is labelled AN21 too, so AN21 starts there, not at its leaf, column 2.
    # From the leaf, the walk would stop at node 11 and give 6.
    assert scored(data, row("s", 21, "3", "K")) == [f"{FAMILY},1,probably benign,0.02"]


def test_no_start_column_gives_an_empty_age(data: Path) -> None:
    replace(data, "paml", "Node1 AN20,", "Node1 AN90,")

    assert scored(data, row("s", 20, "1", "M")) == [f"{FAMILY},,probably benign,0.02"]


def test_no_start_column_keeps_the_previous_genes_start(data: Path) -> None:
    # SCORE-8: the Perl keeps the start column of the previous gene it read.
    replace(data, "paml", "Node1 AN20,", "Node1 AN90,")

    assert scored(data, row("a", 23, "3", "L"), row("b", 20, "1", "M")) == [
        f"{FAMILY},92,probably benign,0.19",
        f"{FAMILY},93,probably benign,0.19",
    ]


# getCorrectnum: the column of the mapped position in the gene's .rst sequence


def test_a_gap_in_the_genes_sequence_is_a_column_but_not_a_position(data: Path) -> None:
    # AN23 is M-KLW: position 2 is K, in column 3.
    assert scored(data, row("s", 23, "2", "K")) == [f"{FAMILY},93,probably benign,0.19"]


def test_a_position_past_the_end_takes_the_last_column(data: Path) -> None:
    # AN23 has 4 residues: position 5 gets column 5, W, as position 4 does.
    assert scored(data, row("a", 23, "5", "W"), row("b", 23, "4", "W")) == [
        f"{FAMILY},,probably benign,0.02",
        f"{FAMILY},,probably benign,0.02",
    ]


def test_a_wrong_wild_type_isnt_scored(data: Path) -> None:
    assert scored(data, row("s", 20, "2", "G")) == [INVALID]


# Ages (getYear)


def test_a_zero_zero_node_with_a_known_taxon_has_an_empty_age(data: Path) -> None:
    # AN23 at site 5: node 12, Ev=0>0 in Homo-Pan, isn't kept. getYear falls through.
    assert scored(data, row("s", 23, "4", "W")) == [f"{FAMILY},,probably benign,0.02"]


def test_a_duplication_is_its_oldest_child_plus_one(data: Path) -> None:
    # Node 9 (1>0): children 10 (91) and 12 (empty, counted as 0).
    assert scored(data, row("s", 23, "3", "L")) == [f"{FAMILY},92,probably benign,0.19"]


def test_a_taxon_missing_from_the_species_tree_is_aged_as_a_duplication(data: Path) -> None:
    # Node 13 is a speciation in Sauria: its children are leaves, so 0 + 1.
    assert scored(data, row("s", 25, "3", "K")) == [f"{FAMILY},1,probably benign,0.02"]


def test_a_root_without_an_event_is_aged_as_a_duplication(data: Path) -> None:
    # Node 8, Ev=UNK: children 9 (92) and 13 (1).
    assert scored(data, row("s", 23, "1", "M")) == [f"{FAMILY},93,probably benign,0.19"]


def test_a_duplication_is_capped_at_4200(data: Path) -> None:
    # With node 10 in LUCA (4200), node 9 would be 4201.
    replace(data, "orig.tree", "S=Euarchontoglires:ID=AN2", "S=LUCA:ID=AN2")

    assert scored(data, row("a", 20, "2", "A"), row("b", 23, "3", "L")) == [
        f"{FAMILY},4200,probably damaging,0.95",
        f"{FAMILY},4200,probably damaging,0.95",
    ]


def test_a_duplication_without_children_has_an_empty_age(data: Path) -> None:
    replace(data, "rst", "8..13    13..6    13..7  ", "8..13  ")

    assert scored(data, row("s", 25, "3", "K")) == [f"{FAMILY},,probably benign,0.02"]


# The order of checks (SCORE-1)


def test_a_family_without_a_paml_isnt_scored_before_anything_else(data: Path) -> None:
    rows = [
        row("a", 20, "", "M", family="PTHR99999"),
        row("b", 20, "1", "M", family="AN12345"),
        row("c", 20, "1", "M", family="../PAML_RST/PTHR00004"),
        row("d", 20, "1", "M", family=""),
    ]

    assert scored(data, *rows) == [NO_FAMILY] * 4


def test_an_unmapped_position_isnt_scored_before_the_gene_is_looked_up(data: Path) -> None:
    # The gene would make the lookup fail: Perl would interpolate the $.
    rows = [row("s", 0, "", "M").replace(f"{FAMILY},,", f"{FAMILY},A|$x|y,")]

    assert scored(data, *rows) == [INVALID]


def test_a_family_without_a_sequence_list_isnt_scored_and_its_paml_isnt_read(data: Path) -> None:
    rows = [f"s,P0001,{BROKEN},HUMAN|HGNC=1|UniProtKB=P00001,1,1,M,V\n"]

    assert scored(data, *rows) == [INVALID]


# The record


def test_the_record_keeps_the_submitted_substitution_and_the_family_field(data: Path) -> None:
    rows = [row("s", 20, "1", "M", position="010", mut="E\r"), row("n", 20, "", "a", mut="")]

    assert step3(rows, data) == [
        f"s,M010E\r,{FAMILY},93,probably benign,0.19\n",
        f"n,a,{INVALID}\n",
    ]


def test_records_come_out_in_order_whatever_their_gene(data: Path) -> None:
    rows = [row("a", 23, "3", "L"), row("b", 20, "2", "G"), row("c", 20, "2", "A")]

    assert [line.split(",")[0] for line in step3(rows, data)] == ["a", "b", "c"]


# Message and pDel (SCORE-5, SCORE-6)


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (None, "0.02"),
        (0, "0.02"),
        (24, "0.02"),
        (25, "0.13"),
        (84, "0.13"),
        (85, "0.17"),
        (90, "0.17"),
        (91, "0.19"),
        (98, "0.19"),
        (99, "0.27"),
        (198, "0.27"),
        (199, "0.50"),
        (398, "0.50"),
        (399, "0.57"),
        (698, "0.57"),
        (699, "0.74"),
        (798, "0.74"),
        (799, "0.78"),
        (898, "0.78"),
        (899, "0.85"),
        (1298, "0.85"),
        (1299, "0.86"),
        (1598, "0.86"),
        (1599, "0.89"),
        (3998, "0.89"),
        (3999, "0.95"),
        (4200, "0.95"),
    ],
)
def test_pdel_tests_age_below_each_bound(age: int | None, expected: str) -> None:
    assert pdel(age) == expected


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (None, "probably benign"),
        (179, "probably benign"),
        (180, "possibly damaging"),
        (379, "possibly damaging"),
        (380, "probably damaging"),
    ],
)
def test_the_message_changes_at_180_and_380(age: int | None, expected: str) -> None:
    assert message(age) == expected


def test_the_fixture_family_reads_cleanly() -> None:
    # The walk relies on these: a guard against editing the fixture by accident.
    assert lines(f"{FAMILY}.paml")[1].startswith("root number,Node11,Node11,Node10,")
