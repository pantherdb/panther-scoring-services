import pytest

from panther_engine.core.fasta import read_protein


@pytest.mark.parametrize(
    ("text", "protein"),
    [
        (">sequence\nMKV\nLW\n", "MKVLW"),
        (">sp|P02649|APOE_HUMAN Apolipoprotein E\r\nMKVL\r\nWAAL\r\n", "MKVLWAAL"),
        ("MKVL", "MKVL"),
        ("  mk vl\tw\x0b\x0c \n", "MKVLW"),
        ("\n\n>sequence\nMKVL", "MKVL"),
    ],
)
def test_one_header_and_whitespace_are_removed_and_letters_upper_cased(
    text: str, protein: str
) -> None:
    assert read_protein(text) == protein


def test_only_the_first_line_is_a_header() -> None:
    # As the API's form: `^>[^\n]*` without MULTILINE, after trimming. Scoring refuses the `>`.
    assert read_protein("MKVL\n>x") == "MKVL>X"


def test_more_than_one_sequence_is_refused() -> None:
    with pytest.raises(ValueError, match="more than one sequence"):
        read_protein(">a\nMKVL\n>b\nWAAL\n")


@pytest.mark.parametrize("text", ["", ">sequence\n", "  \n\t"])
def test_no_sequence_is_refused(text: str) -> None:
    with pytest.raises(ValueError, match="no sequence"):
        read_protein(text)
