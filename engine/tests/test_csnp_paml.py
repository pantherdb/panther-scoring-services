import math
import pickle

import pytest
from csnp_fixtures import edited, lines

from panther_engine.csnp.library import LibraryFormatError
from panther_engine.csnp.paml import iter_sites, read_header, read_paml, read_site, read_sites

PAML = "PTHR00001.paml"


def test_header_rows_give_each_column_its_an_and_parent_and_the_root() -> None:
    header = read_header(lines(PAML), PAML)

    assert header.ans == (2, 3, 4, 0, 1)
    assert header.parents == (5, 5, 4, 4, 4)
    assert header.root == 4
    assert list(header.leaves) == [1, 2, 3]


def test_one_site_gives_each_column_its_residue_and_probability() -> None:
    site = read_site(lines(PAML), PAML, 2)

    assert site.number == 2
    assert site.residues == ("A", "-", "G", "A", "A")
    assert site.probabilities == (1.0, 0.0, 1.0, 0.982, 0.640)


def test_a_site_past_the_last_is_an_error() -> None:
    with pytest.raises(LibraryFormatError, match="no site 3"):
        read_site(lines(PAML), PAML, 3)


def test_several_sites_in_one_pass_equal_each_site_read_alone() -> None:
    header, sites = read_sites(lines(PAML), PAML, [2, 1, 2])

    assert header == read_header(lines(PAML), PAML)
    assert sites == {1: read_site(lines(PAML), PAML, 1), 2: read_site(lines(PAML), PAML, 2)}


def test_a_site_past_the_last_is_absent_from_several_sites() -> None:
    _, sites = read_sites(lines(PAML), PAML, [5, 1])

    assert list(sites) == [1]


def test_several_sites_stop_after_the_last_one_needed() -> None:
    broken = edited(PAML, "Site 2,A,-,G,A,A", "Site 2,broken")

    _, sites = read_sites(broken, PAML, [1])

    assert list(sites) == [1]
    with pytest.raises(LibraryFormatError, match="Site 2"):
        read_sites(broken, PAML, [1, 2])


def test_each_site_in_turn_equals_each_site_read_alone() -> None:
    header, sites = iter_sites(lines(PAML), PAML)

    assert header.root == 4
    assert list(sites) == [read_site(lines(PAML), PAML, site) for site in (1, 2)]


def test_no_sites_reads_the_header_only() -> None:
    header, sites = read_sites(lines(PAML), PAML, [])

    assert header.root == 4
    assert sites == {}


def test_the_whole_file_is_checked() -> None:
    summary = read_paml(lines(PAML), PAML)

    assert summary.header.root == 4
    assert summary.sites == 2
    assert summary.unreconstructed == 0


def test_no_root_is_an_error_naming_the_file() -> None:
    with pytest.raises(LibraryFormatError, match="no root") as raised:
        read_header(lines("no-root.paml"), "no-root.paml")

    assert raised.value.name == "no-root.paml"
    assert raised.value.line == 2


def test_a_bad_probability_is_an_error_naming_its_line() -> None:
    with pytest.raises(LibraryFormatError, match="'abc' isn't a probability") as raised:
        read_paml(lines("bad-probability.paml"), "bad-probability.paml")

    assert raised.value.line == 7


def test_reading_the_site_with_a_bad_probability_is_an_error_too() -> None:
    with pytest.raises(LibraryFormatError, match="'abc'"):
        read_site(lines("bad-probability.paml"), "bad-probability.paml", 2)


def test_crlf_line_endings_are_an_error_at_the_first_line() -> None:
    with pytest.raises(LibraryFormatError, match="carriage return") as raised:
        read_paml(lines("crlf.paml"), "crlf.paml")

    assert str(raised.value).startswith("crlf.paml, line 1: ")


def test_an_unreconstructed_cell_reads_as_no_residue_and_nan() -> None:
    paml = edited(
        PAML,
        "Site 2,A,-,G,A,A\nProbability of site 2,1,0,1,0.982,0.640",
        "Site 2,A,-,G,\x00,A\nProbability of site 2,1,0,1, -nan,0.640",
    )

    site = read_site(paml, PAML, 2)

    assert site.residues == ("A", "-", "G", None, "A")
    assert math.isnan(site.probabilities[3])
    assert read_paml(paml, PAML).unreconstructed == 1


@pytest.mark.parametrize(
    ("residues", "probabilities"),
    [("A,-,G,\x00,A", "1,0,1,0.982,0.640"), ("A,-,G,A,A", "1,0,1, -nan,0.640")],
    ids=["nul-alone", "nan-alone"],
)
def test_half_an_unreconstructed_cell_is_an_error(residues: str, probabilities: str) -> None:
    paml = edited(
        PAML,
        "Site 2,A,-,G,A,A\nProbability of site 2,1,0,1,0.982,0.640",
        f"Site 2,{residues}\nProbability of site 2,{probabilities}",
    )

    with pytest.raises(LibraryFormatError, match="column 4") as raised:
        read_paml(paml, PAML)

    assert raised.value.line == 7


def test_an_internal_column_without_an_an_reads_as_none() -> None:
    header = read_header(edited(PAML, "Node5 AN1", "Node5 "), PAML)

    assert header.ans == (2, 3, 4, 0, None)


def test_a_leaf_column_without_an_an_is_an_error() -> None:
    with pytest.raises(LibraryFormatError, match="leaf column 2 has no AN"):
        read_header(edited(PAML, "Node2 AN3", "Node2 "), PAML)


def test_a_column_out_of_order_is_an_error() -> None:
    with pytest.raises(LibraryFormatError, match="column 2 is 'Node3 AN3'") as raised:
        read_header(edited(PAML, "Node2 AN3", "Node3 AN3"), PAML)

    assert raised.value.line == 1


def test_a_row_with_a_missing_cell_is_an_error() -> None:
    with pytest.raises(LibraryFormatError, match="not a row 'Site 1' of 5 residues") as raised:
        read_paml(edited(PAML, "Site 1,M,M,M,M,M", "Site 1,M,M,M,M"), PAML)

    assert raised.value.line == 4


def test_a_file_that_ends_inside_a_site_is_an_error() -> None:
    truncated = lines(PAML)[:-1]

    with pytest.raises(LibraryFormatError, match="ends before the probability row of site 2"):
        read_paml(truncated, PAML)


def test_an_empty_file_is_an_error() -> None:
    with pytest.raises(LibraryFormatError, match="empty file"):
        read_header([], PAML)


def test_the_error_survives_pickling() -> None:
    error = LibraryFormatError("PTHR00001.paml", 7, "bad")

    copy = pickle.loads(pickle.dumps(error))  # noqa: S301

    assert (copy.name, copy.line, copy.message, str(copy)) == (
        error.name,
        error.line,
        error.message,
        str(error),
    )
