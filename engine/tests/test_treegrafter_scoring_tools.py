"""Grafting with the real tools, HMMER 3.4 and EPA-ng 0.3.8, against the treegrafter fixture: in
the engine image, or wherever both are on PATH."""

import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pytest

from panther_engine.treegrafter import (
    TimeLimitError,
    TreegrafterHit,
    TreegrafterInput,
    TreegrafterResult,
    ebi,
    score,
)
from panther_engine.treegrafter import data as treegrafter_data

FIXTURE = Path(__file__).parent / "fixtures" / "treegrafter"
INPUTS = Path(__file__).parent / "golden" / "treegrafter" / "inputs"
RELEASE = "2026-08-28"
APOE_HIT = TreegrafterHit(
    panther_id="PTHR18976:SF2",
    node_id="AN163",
    graft_point="PTN002498710",
    go_terms=(
        "GO:0005543",
        "GO:0008203",
        "GO:0033344",
        "GO:0033700",
        "GO:0034361",
        "GO:0034362",
        "GO:0034364",
        "GO:0042627",
        "GO:0055090",
        "GO:0060228",
        "GO:0120020",
        "GO:1903561",
    ),
    protein_class="PC00052",
    score="172.6",
    evalue="5.7e-47",
    domain_score="172.4",
    domain_evalue="6.8e-47",
    hmm_from=11,
    hmm_to=359,
    ali_from=1,
    ali_to=306,
    env_from=1,
    env_to=311,
)

pytestmark = pytest.mark.tools("hmmsearch", "epa-ng")


def sequence(case: str) -> TreegrafterInput:
    return TreegrafterInput((INPUTS / f"{case}.txt").read_text(encoding="ascii"))


@pytest.fixture(scope="module")
def folder(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The treegrafter fixture, prepared once, with release 2026-08-28 active."""
    prepared = tmp_path_factory.mktemp("prepared")
    treegrafter_data.install_fixture(FIXTURE, prepared)
    return prepared


def test_apoe_gets_the_hit_the_spec_gives(folder: Path) -> None:
    assert score(sequence("apoe"), data_dir=folder) == TreegrafterResult(APOE_HIT, RELEASE)


def test_hbb_gets_several_placements(folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    placements: list[int] = []
    process_tree = ebi.process_tree

    def counting(
        family: str, jplace: Path, queries: ebi.FamilyMatches, library: Path, annotations: Path
    ) -> list[list[str]]:
        placed = json.loads(jplace.read_text(encoding="utf-8"))
        placements.append(len(placed["placements"][0]["p"]))
        return process_tree(family, jplace, queries, library, annotations)

    monkeypatch.setattr(ebi, "process_tree", counting)

    hit = score(sequence("hbb"), data_dir=folder).hit

    assert hit is not None and hit.panther_id.startswith("PTHR11442")
    assert hit.node_id is not None and hit.graft_point is not None
    assert placements and placements[0] > 1


def test_the_pthr11034_member_gets_the_family_alone(folder: Path) -> None:
    hit = score(sequence("pthr11034"), data_dir=folder).hit

    assert hit is not None
    assert (hit.panther_id, hit.node_id, hit.go_terms, hit.protein_class) == (
        "PTHR11034",
        None,
        (),
        None,
    )


def test_two_proteins_at_once_each_get_their_result_alone(folder: Path) -> None:
    alone = [score(sequence(case), data_dir=folder) for case in ("apoe", "hbb")]
    context = multiprocessing.get_context("spawn")

    with ProcessPoolExecutor(max_workers=2, mp_context=context) as pool:
        futures = [pool.submit(score, sequence(case), data_dir=folder) for case in ("apoe", "hbb")]
        together = [future.result(timeout=120) for future in futures]

    assert together == alone


def test_apoe_then_hbb_then_apoe_gives_apoe_the_same_result(folder: Path) -> None:
    first = score(sequence("apoe"), data_dir=folder)
    score(sequence("hbb"), data_dir=folder)

    assert score(sequence("apoe"), data_dir=folder) == first


def test_a_time_limit_in_a_worker_process_reaches_the_caller(folder: Path) -> None:
    context = multiprocessing.get_context("spawn")

    with ProcessPoolExecutor(max_workers=1, mp_context=context) as pool:
        future = pool.submit(score, sequence("apoe"), data_dir=folder, timeout=0.001)
        with pytest.raises(TimeLimitError):
            future.result(timeout=120)
