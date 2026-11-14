"""The pinned refmap release in the data folder. Needs the refmap data."""

import gzip
import json
import shutil
from pathlib import Path

import pytest

from panther_engine.core.manifest import checksums, read_manifest, verify
from panther_engine.refmap import (
    ORGANISM_CODES,
    ORGANISM_GENES,
    classification_json_file,
    classification_mappings,
)
from panther_engine.refmap.data import (
    MANIFEST,
    build_classification_json,
    code_problems,
    read_stats,
)
from panther_engine.refmap.mapping import classification_file, render
from panther_engine.refmap.organisms import GeneCounts, Organism, code_of, read_organisms

pytestmark = pytest.mark.data("refmap")


def test_every_file_matches_the_manifest(refmap_data: Path) -> None:
    mismatches = verify(refmap_data.parents[1], checksums(read_manifest(MANIFEST)))

    assert mismatches.missing == ()
    assert mismatches.differing == ()


def test_the_organism_list_is_the_one_the_data_folders_stats_gives(refmap_data: Path) -> None:
    entries, problems = read_stats(refmap_data / "stats")

    assert problems == []
    assert code_problems(entries) == []
    generated = tuple(
        Organism(
            code_of(entry.long_name),
            entry.long_name,
            GeneCounts(entry.genes, entry.genes_with_panther_id),
        )
        for entry in sorted(entries, key=lambda entry: entry.long_name)
    )
    assert generated == read_organisms()
    assert len(ORGANISM_CODES) == len(entries) == 1533


def test_every_organisms_mappings_rebuild_its_published_file(refmap_data: Path) -> None:
    """`classification_mappings`, written back with `render`, one a line, is each organism's
    file byte for byte, with `stats`'s counts: the whole file the PANTHER website read from
    data.pantherdb.org, which the API's classification endpoint now sends."""
    root = refmap_data.parents[1]
    for code in sorted(ORGANISM_CODES):
        mappings = list(classification_mappings(code, root))
        rebuilt = "".join(render(item) + "\n" for item in mappings)
        assert rebuilt.encode("latin-1") == classification_file(code, root).read_bytes(), code
        assert len(mappings) == ORGANISM_GENES[code].genes, code
        with_id = sum(item.panther_id is not None for item in mappings)
        assert with_id == ORGANISM_GENES[code].genes_with_panther_id, code


@pytest.mark.parametrize("code", ["ENDPU", "ABSGL", "ARAVE"])
def test_the_built_json_holds_the_mappings(refmap_data: Path, tmp_path: Path, code: str) -> None:
    """The JSON `build-json` writes, for the smallest example, the website's example and the
    largest organism, built in a copy so the data folder is only read."""
    root = refmap_data.parents[1]
    copy = classification_file(code, tmp_path)
    copy.parent.mkdir(parents=True)
    shutil.copyfile(classification_file(code, root), copy)

    build_classification_json(tmp_path, [code])

    built = json.loads(gzip.decompress(classification_json_file(code, tmp_path).read_bytes()))
    assert built == {
        "organism": code,
        "mappings": [
            {"id": item.id, "panther_id": item.panther_id}
            for item in classification_mappings(code, root)
        ],
    }
