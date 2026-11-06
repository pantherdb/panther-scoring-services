import json
import sys
from pathlib import Path

import pytest

from panther_engine.core.process import run_tool
from panther_engine.refmap import DATA_VERSION, ORGANISM_CODES, ORGANISM_NAMES
from panther_engine.refmap.organisms import read_organisms


def test_there_are_1533_codes_none_of_them_panthers_own_genomes() -> None:
    assert len(ORGANISM_CODES) == 1533
    assert {"ENDPU", "ECO57", "PEA", "ARAVE"} <= ORGANISM_CODES
    assert not {"HUMAN", "MOUSE", "YEAST", "ECOLI"} & ORGANISM_CODES
    assert frozenset(ORGANISM_NAMES) == ORGANISM_CODES


def test_names_are_the_long_names_parts_but_the_code_joined_by_spaces() -> None:
    assert ORGANISM_NAMES["ECO57"] == "Escherichia coli O157:H7"
    assert ORGANISM_NAMES["PEA"] == "Pisum sativum"
    assert ORGANISM_NAMES["CAMJE"] == "Campylobacter jejuni subsp jejuni serotype O:2"
    assert ORGANISM_NAMES["ENDPU"] == "Endocarpon pusillum"


def test_organisms_are_in_long_name_order() -> None:
    codes = list(ORGANISM_NAMES)

    assert codes[0] == "ABRPR"
    assert ORGANISM_NAMES["ABRPR"] == "Abrus precatorius"
    assert codes[-1] == "ZYMTI"
    assert ORGANISM_NAMES["ZYMTI"] == "Zymoseptoria tritici"


def test_the_names_are_read_only() -> None:
    with pytest.raises(TypeError):
        ORGANISM_NAMES["HUMAN"] = "Homo sapiens"  # pyright: ignore[reportIndexIssue]


def test_the_data_version_is_panther_19() -> None:
    assert DATA_VERSION == "19"


def test_the_organisms_need_no_data_folder_and_no_tarfile_or_urllib() -> None:
    script = (
        "import os, sys\n"
        "os.environ.pop('PANTHER_DATA_DIR', None)\n"
        "import panther_engine.refmap as refmap\n"
        "assert len(refmap.ORGANISM_CODES) == 1533\n"
        "print(sorted(name for name in ('tarfile', 'urllib.request') if name in sys.modules))\n"
    )

    result = run_tool(sys.executable, ["-c", script], timeout=60)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "[]\n"


@pytest.mark.parametrize(
    "listing",
    [
        [
            {"code": "PEA", "long_name": "Pisum_sativum_PEA"},
            {"code": "PEA", "long_name": "Pisum_arvense_PEA"},
        ],
        [
            {"code": "PEA", "long_name": "Pisum_sativum_PEA"},
            {"code": "PEA", "long_name": "Pisum_sativum_PEA"},
        ],
    ],
    ids=["two-long-names", "the-same-twice"],
)
def test_a_list_that_repeats_a_code_is_refused(
    listing: list[dict[str, str]], tmp_path: Path
) -> None:
    path = tmp_path / "organisms.json"
    path.write_text(json.dumps(listing))

    with pytest.raises(ValueError, match="PEA") as raised:
        read_organisms(path)

    assert "Pisum_sativum_PEA" in str(raised.value)
    assert listing[1]["long_name"] in str(raised.value)
