"""The pinned refmap release in the data folder. Needs the refmap data."""

from pathlib import Path

import pytest

from panther_engine.core.manifest import checksums, read_manifest, verify
from panther_engine.refmap import ORGANISM_CODES
from panther_engine.refmap.data import MANIFEST, code_problems, read_stats
from panther_engine.refmap.organisms import Organism, code_of, read_organisms

pytestmark = pytest.mark.data("refmap")


def test_every_file_matches_the_manifest(refmap_data: Path) -> None:
    mismatches = verify(refmap_data.parents[1], checksums(read_manifest(MANIFEST)))

    assert mismatches.missing == ()
    assert mismatches.differing == ()


def test_the_organism_list_is_the_one_the_data_folders_stats_gives(refmap_data: Path) -> None:
    entries, problems = read_stats(refmap_data / "stats")

    assert problems == []
    assert code_problems(entries) == []
    names = sorted(entry.long_name for entry in entries)
    assert tuple(Organism(code_of(name), name) for name in names) == read_organisms()
    assert len(ORGANISM_CODES) == len(entries) == 1533
