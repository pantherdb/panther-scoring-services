import pytest
from csnp_fixtures import edited, lines

from panther_engine.csnp.library import LibraryFormatError
from panther_engine.csnp.rst import read_rst

RST = "PTHR00001.rst"


def test_the_branch_list_and_the_tree_are_read_from_lines_12_and_15() -> None:
    rst = read_rst(lines(RST), RST)

    assert rst.branches == ((4, 5), (5, 1), (5, 2), (4, 3))
    assert rst.tree.nodes == (1, 2, 5, 3, 4)
    assert rst.tree.leaves == {1: 2, 2: 3, 3: 4}


def test_sequences_lose_their_label_and_spaces_and_keep_gaps() -> None:
    long = "MAGSGSRPRS WGWRETG-RD EAA"
    rst = edited(RST, f"{'AN4':<18}MG", f"{'AN4':<18}{long}")

    sequences = read_rst(rst, RST).sequences

    assert sequences == {2: "MA", 3: "M-", 4: long.replace(" ", "")}


def test_a_sequence_whose_length_is_a_multiple_of_10_ends_with_a_space() -> None:
    # PAML writes a space after every full block of 10, so such a line ends with one.
    rst = edited(RST, f"{'AN4':<18}MG", f"{'AN4':<18}MAGSGSRPRS WGWRETG-RD ")

    assert read_rst(rst, RST).sequences[4] == "MAGSGSRPRSWGWRETG-RD"


@pytest.mark.parametrize("sequence", ["MAGSGSRPRS WGWRETG-RD", "MAGS ", "MAGSGSRPRS  WG"])
def test_a_sequence_line_not_written_as_paml_writes_it_is_an_error(sequence: str) -> None:
    with pytest.raises(LibraryFormatError, match="not a sequence line"):
        read_rst(edited(RST, f"{'AN4':<18}MG", f"{'AN4':<18}{sequence}"), RST)


def test_an_empty_file_is_an_error_naming_the_file() -> None:
    with pytest.raises(LibraryFormatError, match="empty file") as raised:
        read_rst(lines("empty.rst"), "empty.rst")

    assert raised.value.name == "empty.rst"


def test_a_branch_list_off_its_line_is_an_error_at_line_12() -> None:
    with pytest.raises(LibraryFormatError, match="not a branch list") as raised:
        read_rst(lines("branch-list-off-line.rst"), "branch-list-off-line.rst")

    assert raised.value.line == 12


def test_a_malformed_branch_token_is_an_error() -> None:
    with pytest.raises(LibraryFormatError, match="not a branch list"):
        read_rst(edited(RST, "5..2 ", "5.2 "), RST)


@pytest.mark.parametrize(
    "tree",
    [
        "((1_AN2, 2_AN3) 5 , 3_AN4) 4",  # no ;
        "((1_AN2, 2_AN3) , 3_AN4) 4 ;",  # an internal node without its number
        "((1_AN2, 2_AN3) 5 , 3_AN4 4 ;",  # one ) missing
        "((1_AN2, 2_AN3) 5 , 3_AN4) 4 ; 6",  # text after the ;
        "((1_AN2, 2_AN3) 5 , 1_AN4) 4 ;",  # a node number twice
    ],
)
def test_a_malformed_tree_is_an_error_at_line_15(tree: str) -> None:
    with pytest.raises(LibraryFormatError) as raised:
        read_rst(edited(RST, "((1_AN2, 2_AN3) 5 , 3_AN4) 4 ;", tree), RST)

    assert raised.value.line == 15


def test_the_sequence_list_ends_at_overall() -> None:
    rst = lines(RST)
    rst[-1:-1] = ["Overall accuracy of the 5 ancestral sequences:\n"]

    assert set(read_rst(rst, RST).sequences) == {2, 3}


def test_a_second_sequence_for_an_an_is_an_error() -> None:
    with pytest.raises(LibraryFormatError, match="a second sequence for AN3") as raised:
        read_rst(edited(RST, f"{'AN4':<18}MG", f"{'AN3':<18}MG"), RST)

    assert raised.value.line == 27


def test_a_line_in_the_sequence_list_that_isnt_a_sequence_is_an_error() -> None:
    with pytest.raises(LibraryFormatError, match="not a sequence line") as raised:
        read_rst(edited(RST, f"{'AN4':<18}MG", f"{'AN4':<18}M G"), RST)

    assert raised.value.line == 27
