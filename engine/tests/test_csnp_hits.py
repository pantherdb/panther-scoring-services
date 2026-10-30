"""Step 2 on synthetic BLAST lines: the species filter, the ranking, the best hit and the mapping
(design.md, decision 4). The goldens are in test_csnp_golden.py."""

import pytest

from panther_engine.csnp.blast import BlastError
from panther_engine.csnp.hits import SnpRecord, best_hits, parse, read_snps
from panther_engine.csnp.parity import blast_line

HUMAN = "HUMAN|HGNC=1|UniProtKB=P00001:PTHR00001:SF1"
MOUSE = "MOUSE|MGI=MGI=1|UniProtKB=P00003:PTHR00002:SF2"


def snp(position: str, wt: str, *, protein: str = "P0001", mut: str = "V") -> SnpRecord:
    return SnpRecord(f"SNP_{position}", protein, position, wt, mut)


def mapped(lines: list[str], *records: SnpRecord, species: str = "NA") -> list[str]:
    """Each record's mapped position, the sixth snpParse field."""
    return [row.split(",")[5] for row in parse(lines, records, species)]


# The species filter (MAP-2)


def test_the_species_filter_keeps_the_species_hit_over_a_better_one() -> None:
    lines = [
        blast_line("P0001", MOUSE, "A" * 100, "A" * 99 + "W"),
        blast_line("P0001", HUMAN, "A" * 100, "A" * 95 + "W" * 5),
    ]
    assert [line.split(",")[2] for line in lines] == ["99.00", "95.00"]

    hits = best_hits(lines, "HUMAN")

    assert hits["P0001"].sseqid == HUMAN


def test_the_species_filter_matches_anywhere_in_the_line() -> None:
    # A MOUSE hit whose aligned query spells RAT gets through a RAT filter.
    lines = [blast_line("P0001", MOUSE, "GRATK", "GRATK")]

    assert best_hits(lines, "RAT")["P0001"].sseqid == MOUSE


def test_the_species_filter_is_case_sensitive() -> None:
    lines = [blast_line("P0001", HUMAN, "MKVA", "MKVA")]

    assert best_hits(lines, "human") == {}


def test_species_na_keeps_every_line() -> None:
    lines = [blast_line("P0001", MOUSE, "MKVA", "MKVA")]

    assert best_hits(lines, "NA")["P0001"].sseqid == MOUSE


# Ranking (MAP-1)


def test_the_highest_percent_identity_wins() -> None:
    lines = [
        blast_line("P0001", MOUSE, "MKVAL", "MKVAL"),
        blast_line("P0001", HUMAN, "MKVAL", "MKVAW"),
    ]

    assert best_hits(lines, "NA")["P0001"].sseqid == MOUSE


def test_identity_is_compared_as_a_number() -> None:
    # As text, "9.09" would sort above "10.00".
    lines = [
        blast_line("P0001", MOUSE, "A" * 11, "A" + "W" * 10),
        blast_line("P0001", HUMAN, "A" * 10, "A" + "W" * 9),
    ]

    assert best_hits(lines, "NA")["P0001"].sseqid == HUMAN


def test_equal_identities_are_ordered_by_the_whole_line_byte_by_byte() -> None:
    first = "HUMAN|HGNC=1|UniProtKB=A00001:PTHR00005:SF1"
    second = "HUMAN|HGNC=1|UniProtKB=a00001:PTHR00004:SF1"
    lines = [
        blast_line("P0001", second, "MKVA", "MKVA"),
        blast_line("P0001", first, "MKVA", "MKVA"),
    ]

    # Uppercase sorts before lowercase in C, though not in a dictionary order.
    assert best_hits(lines, "NA")["P0001"].sseqid == first


def test_identities_equal_to_two_decimals_are_a_tie() -> None:
    # 2.17.0 writes 3 decimals: 99.502 and 99.501 both become 99.50, so the line order decides.
    lines = [
        blast_line("P0001", MOUSE, "A" * 1005, "A" * 1000 + "W" * 5, decimals=3),
        blast_line("P0001", HUMAN, "A" * 1003, "A" * 998 + "W" * 5, decimals=3),
    ]
    assert [line.split(",")[2] for line in lines] == ["99.502", "99.501"]

    assert best_hits(lines, "NA")["P0001"].sseqid == HUMAN


def test_identity_is_recomputed_to_two_decimals() -> None:
    line = blast_line("P0001", HUMAN, "A" * 371, "A" * 348 + "W" * 23, decimals=3)
    assert line.split(",")[2] == "93.801"

    assert best_hits([line], "NA")["P0001"].pident == "93.80"


def test_an_identity_that_disagrees_with_the_counts_is_an_error() -> None:
    line = blast_line("P0001", HUMAN, "A" * 371, "A" * 348 + "W" * 23, pident="93.900")

    with pytest.raises(BlastError, match=r"93\.900"):
        best_hits([line], "NA")


def test_a_line_without_15_fields_is_an_error() -> None:
    with pytest.raises(BlastError, match="15 fields"):
        best_hits(["P0001,PTHR00001\n"], "NA")


def test_the_first_line_per_query_is_its_best_hit() -> None:
    lines = [
        blast_line("Q0002", MOUSE, "MKVA", "MKVA"),
        blast_line("P0001", HUMAN, "MKVA", "MKVA"),
        blast_line("P0001", MOUSE, "MKVA", "MKVW"),
    ]

    hits = best_hits(lines, "NA")

    assert {query: hit.sseqid for query, hit in hits.items()} == {"P0001": HUMAN, "Q0002": MOUSE}


# The snpParse record (MAP-3)


def test_the_family_and_the_gene_come_from_the_subject_id() -> None:
    line = blast_line("P0001", "HUMAN|HGNC=1|UniProtKB=P00001:PTHR23125_2:SF4", "MKVA", "MKVA")

    rows = parse([line], [snp("2", "K", mut="E")], "HUMAN")

    assert rows == ["SNP_2,P0001,PTHR23125_2,HUMAN|HGNC=1|UniProtKB=P00001,2,2,K,E\n"]


def test_no_hit_gives_empty_fields() -> None:
    line = blast_line("P0001", MOUSE, "MKVA", "MKVA")

    rows = parse([line], [snp("2", "K", mut="E")], "HUMAN")

    assert rows == ["SNP_2,P0001,,,2,,K,E\n"]


# The mapping (MAP-4)


def test_positions_map_through_an_alignment_without_gaps() -> None:
    line = blast_line("P0001", HUMAN, "KVAL", "KVAL", qstart=5, sstart=20)

    assert mapped([line], snp("6", "V"), snp("8", "L")) == ["21", "23"]


def test_the_residue_at_the_alignments_start_isnt_mapped() -> None:
    line = blast_line("P0001", HUMAN, "KVAL", "KVAL", qstart=5, sstart=20)

    assert mapped([line], snp("5", "K")) == [""]


def test_a_position_past_the_alignment_isnt_mapped() -> None:
    line = blast_line("P0001", HUMAN, "KVAL", "KVAL", qstart=5, sstart=20)

    assert mapped([line], snp("9", "L"), snp("4", "K")) == ["", ""]


def test_the_residue_after_a_gap_in_the_query_isnt_mapped() -> None:
    line = blast_line("P0001", HUMAN, "AB-CD", "ABXCD")

    assert mapped([line], snp("2", "B"), snp("3", "C"), snp("4", "D")) == ["2", "", "5"]


def test_gaps_in_the_subject_are_taken_off_the_mapped_position() -> None:
    line = blast_line("P0001", HUMAN, "ABCDE", "AB-DE")

    assert mapped([line], snp("2", "B"), snp("4", "D"), snp("5", "E")) == ["2", "3", "4"]


def test_the_wild_type_is_checked_against_the_subject() -> None:
    line = blast_line("P0001", HUMAN, "MKVA", "MKWA")

    assert mapped([line], snp("3", "V"), snp("3", "W")) == ["", "3"]


def test_a_character_other_than_a_letter_or_a_gap_shifts_the_column() -> None:
    # `*` is neither a residue nor a gap, so after it the column is one short: position 4, which
    # is D if `*` isn't a residue, lands on C.
    line = blast_line("P0001", HUMAN, "AB*CD", "ABXCD")

    assert mapped([line], snp("4", "C"), snp("4", "D")) == ["4", ""]


def test_a_leading_zero_is_echoed_but_mapped_as_a_number() -> None:
    line = blast_line("P0001", HUMAN, "MKVALSTRPEGH", "MKVALSTRPEGH")

    rows = parse([line], [snp("010", "E"), snp("03", "V")], "NA")

    assert [row.split(",")[4:6] for row in rows] == [["010", "10"], ["03", "3"]]


# The SNP input


def test_snp_lines_are_read_as_the_perl_reads_them() -> None:
    text = "e5|P26439|10|A;E;V\ne10|P26439|10|A;E\r\ndel26|P26439|341|P;L \nshort|P1|7"

    records = read_snps(text)

    assert records == [
        SnpRecord("e5", "P26439", "10", "A", "E"),
        SnpRecord("e10", "P26439", "10", "A", "E\r"),
        SnpRecord("del26", "P26439", "341", "P", "L "),
        SnpRecord("short", "P1", "7", "", ""),
    ]


def test_records_come_out_in_input_order_with_their_raw_fields() -> None:
    line = blast_line("P0001", HUMAN, "MKVAL", "MKVAL")
    records = [SnpRecord("b", "P0001", "3", "V", "E\r"), SnpRecord("a", "NOPE", "3", "V", "E")]

    rows = parse([line], records, "NA")

    assert rows == [
        "b,P0001,PTHR00001,HUMAN|HGNC=1|UniProtKB=P00001,3,3,V,E\r\n",
        "a,NOPE,,,3,,V,E\n",
    ]
