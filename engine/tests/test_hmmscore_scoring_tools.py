"""Scoring with the real `hmmscan` and `hmmsearch`: on the fixture library, and on the data
sample. The rules are tested with fake tools in test_hmmscore_scoring.py; the goldens in
test_hmmscore_parity.py."""

import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from hmmscore_fixtures import FAMILY_MODEL, FIXTURES, NAMES, PRESSED, SF1_MODEL, SF2_MODEL

from panther_engine.hmmscore import HmmscoreInput, HmmscoreResult, score

INPUTS = Path(__file__).parent / "golden" / "hmmscore" / "parity" / "inputs"
APOE = (INPUTS / "apoe.txt").read_text(encoding="ascii")
TEST = (INPUTS / "test.txt").read_text(encoding="ascii")
# The consensus of the fixture library's SF2 model, by HMMER 3.4's `hmmemit -c`.
SF2_CONSENSUS = "MTNVKVAILGASGFIGKELIRLLAQHPDIELIAISA"


@pytest.fixture
def sample(hmmscore_data: Path) -> Path:
    """The data folder holding the data sample, at hmmscore/19/."""
    return hmmscore_data.parents[1]


@pytest.fixture
def fixture_library(tmp_path: Path) -> Path:
    """A data folder holding the fixture library, PTHR99999, under hmmscore/19/."""
    folder = tmp_path / "hmmscore" / "19"
    for name in (NAMES, *PRESSED, FAMILY_MODEL, SF1_MODEL, SF2_MODEL):
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURES / name, folder / name)
    return tmp_path


@pytest.mark.tools("hmmscan", "hmmsearch")
def test_a_models_consensus_gets_that_models_id(fixture_library: Path) -> None:
    hit = score(HmmscoreInput(SF2_CONSENSUS), data_dir=fixture_library).hit

    assert hit is not None
    assert (hit.panther_id, hit.name) == ("PTHR99999:SF2", "TEST SUBFAMILY 2")
    assert ">> sequence" in hit.alignment
    assert "PTHR99999.SF2.pir" in hit.alignment


@pytest.mark.tools("hmmscan", "hmmsearch")
@pytest.mark.data("hmmscore")
def test_the_example_against_the_sample(sample: Path) -> None:
    hit = score(HmmscoreInput(APOE), data_dir=sample).hit

    assert hit is not None
    assert (hit.panther_id, hit.score) == ("PTHR18976:SF2", "439.0")
    names = (sample / "hmmscore" / "19" / "globals" / "names.tab").read_text("latin-1")
    assert f"PTHR18976.SF2.mod\t{hit.name}\n" in names
    assert hit.alignment.startswith(">> sequence  \n")
    assert "  PTHR18976.SF2.pir   1 " in hit.alignment


@pytest.mark.tools("hmmscan", "hmmsearch")
@pytest.mark.data("hmmscore")
def test_the_thread_count_changes_nothing(sample: Path) -> None:
    results = [score(HmmscoreInput(APOE), data_dir=sample, cpu=cpu) for cpu in (0, 2)]

    assert results[0] == results[1]


@pytest.mark.tools("hmmscan", "hmmsearch")
@pytest.mark.data("hmmscore")
def test_a_result_doesnt_depend_on_what_was_scored_before(sample: Path) -> None:
    first = score(HmmscoreInput(APOE), data_dir=sample)
    score(HmmscoreInput(TEST), data_dir=sample)

    assert score(HmmscoreInput(APOE), data_dir=sample) == first


@pytest.mark.tools("hmmscan", "hmmsearch")
@pytest.mark.data("hmmscore")
def test_two_proteins_at_once_each_get_their_own_result(sample: Path) -> None:
    alone = [score(HmmscoreInput(sequence), data_dir=sample) for sequence in (APOE, TEST)]

    def scored(sequence: str) -> HmmscoreResult:
        return score(HmmscoreInput(sequence), data_dir=sample)

    with ThreadPoolExecutor(max_workers=2) as pool:
        together = list(pool.map(scored, (APOE, TEST)))

    assert together == alone
    assert alone[0] != alone[1]
