import pytest
from hmmscore_fixtures import NAMES, lines

from panther_engine.hmmscore.legacy import model_id, names_key
from panther_engine.hmmscore.library import read_names


@pytest.mark.parametrize(
    ("name", "hmm_id"),
    [
        ("PTHR32401.SF33.pir", "PTHR32401:SF33"),
        ("PTHR38402.orig.30.pir", "PTHR38402"),
        # /^SF\d+/ isn't anchored at its end
        ("PTHR10000.SF5x.pir", "PTHR10000:SF5x"),
        ("PTHR10000.SF.pir", "PTHR10000"),
        ("PTHR10000.xSF5.pir", "PTHR10000"),
        ("PTHR10000", "PTHR10000"),
        ("PTHR10000..SF5", "PTHR10000"),
    ],
)
def test_a_model_name_maps_to_its_hmm_id_as_runhmmscan_maps_it(name: str, hmm_id: str) -> None:
    assert model_id(name) == hmm_id


@pytest.mark.parametrize(
    ("line", "key"),
    [
        ("PTHR10003.mag.mod\tCU/ZN SUPEROXIDE DISMUTASE\n", "PTHR10003"),
        ("PTHR10003.SF38.mod\tEXTRACELLULAR SUPEROXIDE DISMUTASE\n", "PTHR10003:SF38"),
        # The tab doesn't stop the split on "."
        ("PTHR10000.SF55\tA NAME\n", "PTHR10000:SF55\tA NAME"),
        # "0" is false in Perl, like an empty part
        ("PTHR10000.0.mod\tA NAME\n", "PTHR10000"),
        ("PTHR10000..mod\tA NAME\n", "PTHR10000"),
        # chomp drops the line feed only
        ("PTHR10000.SF1\r\n", "PTHR10000:SF1\r"),
        ("PTHR10000.SF1.mod\tA NAME\r\n", "PTHR10000:SF1"),
        ("PTHR10000.SF1", "PTHR10000:SF1"),
    ],
)
def test_a_names_line_is_keyed_as_gethmmnames_keys_it(line: str, key: str) -> None:
    assert names_key(line) == key


def test_the_clean_names_file_is_keyed_the_same_by_both_readers() -> None:
    content = lines(NAMES)

    assert [names_key(line) for line in content] == list(read_names(content, NAMES))
