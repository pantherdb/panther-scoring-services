"""An organism's whole classification: `classification_mappings`, the line reader it shares with
`map_ids`, and the gzipped JSON `refmap data build-json` writes for the API to send as it is.
Made-up files; the release's are checked in test_refmap_release_data.py."""

import gzip
import json
import re
import stat
import sys
from pathlib import Path
from typing import Any

import pytest

from panther_engine.cli import main
from panther_engine.core.data import DataFolderError, MissingDataError
from panther_engine.refmap import (
    IdMapping,
    check_classification_json,
    classification_json_file,
    classification_mappings,
)
from panther_engine.refmap.data import build_classification_json
from panther_engine.refmap.mapping import classification_file, read_classification
from panther_engine.refmap.organisms import ORGANISMS

# ENDPU's classification file named in a message, with either path separator, for Windows.
ENDPU_FILE = r"panther_classification[/\\]ENDPU"

# Lines as the published files have them, and the cases `map_panther.pl`'s reading defines: NOHIT,
# a repeated ID, a carriage return, a line with no tab, an empty value, a third field and a
# Latin-1 byte.
CONTENT = (
    b"U1G4Q5\tPTHR10351\n"
    b"U1HV42\tNOHIT\n"
    b"U1G4Q5\tPTHR10351:SF2\n"
    b"U1CR\tPTHR00001\r\n"
    b"U1NOTAB\n"
    b"U1EMPTY\t\n"
    b"U1EXTRA\tPTHR11111\textra\n"
    b"U1\xe9\tPTHR22222"
)
MAPPINGS = [
    IdMapping("U1G4Q5", "PTHR10351"),
    IdMapping("U1HV42", None),
    IdMapping("U1G4Q5", "PTHR10351:SF2"),
    IdMapping("U1CR", "PTHR00001\r"),
    IdMapping("U1NOTAB", None),
    IdMapping("U1EMPTY", ""),
    IdMapping("U1EXTRA", "PTHR11111"),
    IdMapping("U1\xe9", "PTHR22222"),
]


def write_file(folder: Path, code: str, content: bytes = CONTENT) -> Path:
    path = classification_file(code, folder)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def read_json(folder: Path, code: str) -> dict[str, Any]:
    built: dict[str, Any] = json.loads(
        gzip.decompress(classification_json_file(code, folder).read_bytes())
    )
    return built


# classification_mappings


def test_every_line_is_a_mapping_in_the_files_order(tmp_path: Path) -> None:
    write_file(tmp_path, "ENDPU")

    assert list(classification_mappings("ENDPU", tmp_path)) == MAPPINGS


def test_each_line_is_read_as_map_ids_reads_it(tmp_path: Path) -> None:
    # The same reader: a job's value for each ID is the last of its lines here.
    path = write_file(tmp_path, "ENDPU")
    last = {item.id: item.panther_id for item in classification_mappings("ENDPU", tmp_path)}
    raw = read_classification(path, set(last))

    assert {key: None if value == "NOHIT" else value for key, value in raw.items()} == last


@pytest.mark.parametrize("content", [b"", b"A1\tPTHR00001\n\n", b"\n"])
def test_empty_lines_and_files(tmp_path: Path, content: bytes) -> None:
    write_file(tmp_path, "ENDPU", content)

    found = list(classification_mappings("ENDPU", tmp_path))

    assert (
        found
        == {
            b"": [],
            b"A1\tPTHR00001\n\n": [IdMapping("A1", "PTHR00001"), IdMapping("", None)],
            b"\n": [IdMapping("", None)],
        }[content]
    )


@pytest.mark.parametrize("organism", ["NOPE1", "endpu", "..", "ENDPU/x"])
def test_an_organism_refmap_doesnt_map_for_is_refused_before_reading(
    tmp_path: Path, organism: str
) -> None:
    with pytest.raises(ValueError, match="not an organism refmap maps for"):
        classification_mappings(organism, tmp_path)


def test_a_missing_file_is_missing_data_naming_it(tmp_path: Path) -> None:
    with pytest.raises(MissingDataError, match=ENDPU_FILE):
        classification_mappings("ENDPU", tmp_path)


def test_without_a_data_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PANTHER_DATA_DIR", raising=False)

    with pytest.raises(DataFolderError):
        classification_mappings("ENDPU")


# build_classification_json


def test_the_json_holds_every_mapping_in_order(tmp_path: Path) -> None:
    write_file(tmp_path, "ENDPU")

    assert build_classification_json(tmp_path, ["ENDPU"]) == 1

    assert read_json(tmp_path, "ENDPU") == {
        "organism": "ENDPU",
        "mappings": [{"id": item.id, "panther_id": item.panther_id} for item in MAPPINGS],
    }


def test_a_file_longer_than_a_batch_keeps_every_mapping(tmp_path: Path) -> None:
    lines = [f"ID{number}\tPTHR{number:05}\n".encode() for number in range(25_001)]
    write_file(tmp_path, "ENDPU", b"".join(lines))

    build_classification_json(tmp_path, ["ENDPU"])

    mappings = read_json(tmp_path, "ENDPU")["mappings"]
    assert len(mappings) == 25_001
    assert mappings[0] == {"id": "ID0", "panther_id": "PTHR00000"}
    assert mappings[-1] == {"id": "ID25000", "panther_id": "PTHR25000"}


def test_the_same_file_gives_the_same_bytes(tmp_path: Path) -> None:
    write_file(tmp_path, "ENDPU")
    build_classification_json(tmp_path, ["ENDPU"])
    first = classification_json_file("ENDPU", tmp_path).read_bytes()

    build_classification_json(tmp_path, ["ENDPU"])

    assert classification_json_file("ENDPU", tmp_path).read_bytes() == first


def test_the_json_leaves_no_partial_file(tmp_path: Path) -> None:
    write_file(tmp_path, "ENDPU")

    build_classification_json(tmp_path, ["ENDPU"])

    path = classification_json_file("ENDPU", tmp_path)
    assert [item.name for item in path.parent.iterdir()] == ["ENDPU.json.gz"]


@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no group or other permissions")
def test_the_json_is_readable_by_everyone(tmp_path: Path) -> None:
    write_file(tmp_path, "ENDPU")

    build_classification_json(tmp_path, ["ENDPU"])

    assert stat.S_IMODE(classification_json_file("ENDPU", tmp_path).stat().st_mode) == 0o644


def test_missing_only_skips_what_is_there(tmp_path: Path) -> None:
    write_file(tmp_path, "ENDPU")
    write_file(tmp_path, "ABSGL")
    build_classification_json(tmp_path, ["ENDPU"])

    assert build_classification_json(tmp_path, ["ENDPU", "ABSGL"], missing_only=True) == 1
    assert classification_json_file("ABSGL", tmp_path).is_file()


def test_a_missing_classification_file_writes_nothing_for_it(tmp_path: Path) -> None:
    with pytest.raises(MissingDataError, match=ENDPU_FILE):
        build_classification_json(tmp_path, ["ENDPU"])

    folder = classification_json_file("ENDPU", tmp_path).parent
    assert list(folder.iterdir()) == []


# check_classification_json


def test_the_check_names_what_is_missing(tmp_path: Path) -> None:
    write_file(tmp_path, "ENDPU")
    build_classification_json(tmp_path, ["ENDPU"])

    check_classification_json(tmp_path, ["ENDPU"])
    with pytest.raises(MissingDataError, match=r"lacks 1 of 2 files: ABSGL\.json\.gz"):
        check_classification_json(tmp_path, ["ENDPU", "ABSGL"])


# refmap data build-json


def organism_list(tmp_path: Path, *codes: str) -> Path:
    listing = [item for item in json.loads(ORGANISMS.read_text()) if item["code"] in codes]
    path = tmp_path / "organisms.json"
    path.write_text(json.dumps(listing))
    return path


def test_build_json_builds_every_listed_organism(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = tmp_path / "data"
    write_file(data, "ENDPU")
    write_file(data, "ABSGL")
    listed = organism_list(tmp_path, "ENDPU", "ABSGL")

    args = ["refmap", "data", "build-json", "--data-dir", str(data), "--organisms", str(listed)]
    status = main(args)

    assert status == 0
    assert "built the classification JSON of 2 organisms" in capsys.readouterr().out
    assert read_json(data, "ABSGL") == read_json(data, "ENDPU") | {"organism": "ABSGL"}


def test_build_json_without_a_classification_file_fails_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    listed = organism_list(tmp_path, "ENDPU")

    args = ["refmap", "data", "build-json", "--data-dir", str(tmp_path), "--organisms", str(listed)]
    status = main(args)

    captured = capsys.readouterr()
    assert status == 1
    assert re.search(ENDPU_FILE, captured.err)
    assert "Traceback" not in captured.err


def test_build_json_refuses_a_list_naming_an_organism_refmap_doesnt_map_for(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Well formed, so the organism list reads it; not the engine's, so it has no file to build.
    data = tmp_path / "data"
    write_file(data, "ENDPU")
    listing = json.loads(organism_list(tmp_path, "ENDPU").read_text())
    listing.append({**listing[0], "code": "NOPE1", "long_name": "Made_up_NOPE1"})
    listed = tmp_path / "organisms.json"
    listed.write_text(json.dumps(listing))

    args = ["refmap", "data", "build-json", "--data-dir", str(data), "--organisms", str(listed)]
    status = main(args)

    captured = capsys.readouterr()
    assert status == 1
    assert "lists organisms refmap doesn't map for: NOPE1" in captured.err
    assert "Traceback" not in captured.err
    assert not classification_json_file("ENDPU", data).exists()
