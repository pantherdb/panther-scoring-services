import re
from pathlib import Path

import pytest

from panther_engine.core.data import DataFolderError, MissingDataError
from panther_engine.core.errors import InputError
from panther_engine.refmap import (
    ORGANISM_CODES,
    IdMapping,
    RefmapInput,
    RefmapResult,
    check_data,
    map_ids,
    mapping,
)
from panther_engine.refmap.mapping import panther_id_of, read_classification


def values(tmp_path: Path, content: bytes, *ids: str) -> dict[str, str | None]:
    path = tmp_path / "classification"
    path.write_bytes(content)
    return read_classification(path, set(ids))


# Reading a classification file


def test_only_the_requested_ids_are_kept(tmp_path: Path) -> None:
    found = values(tmp_path, b"A1\tPTHR00001\nB2\tPTHR00002:SF3\nC3\tPTHR00003\n", "A1", "C3", "D4")

    assert found == {"A1": "PTHR00001", "C3": "PTHR00003"}


def test_a_later_line_for_an_id_replaces_an_earlier_one(tmp_path: Path) -> None:
    # REFMAP-2
    found = values(tmp_path, b"A1\tPTHR00001\nB2\tPTHR00003\nA1\tPTHR00002\n", "A1", "B2")

    assert found == {"A1": "PTHR00002", "B2": "PTHR00003"}


def test_a_carriage_return_stays_in_the_value(tmp_path: Path) -> None:
    # REFMAP-3: chomp drops the final \n only
    found = values(tmp_path, b"A1\tPTHR00001\r\nB2\tNOHIT\r\n", "A1", "B2")

    assert found == {"A1": "PTHR00001\r", "B2": "NOHIT\r"}


def test_a_later_line_with_no_tab_leaves_no_value(tmp_path: Path) -> None:
    assert values(tmp_path, b"A1\tPTHR00001\nA1\n", "A1") == {"A1": None}


def test_a_later_line_ending_in_a_tab_leaves_an_empty_value(tmp_path: Path) -> None:
    # `my ($id, $pthr) = split /\t/` has an implicit limit of 3, so the empty field stays.
    assert values(tmp_path, b"A1\tPTHR00001\nA1\t\n", "A1") == {"A1": ""}


@pytest.mark.parametrize("line", [b"A1\t\tPTHR00001\n", b"A1\t\t\n", b"A1\t\t\t\n"])
def test_an_empty_second_field_is_an_empty_value(line: bytes, tmp_path: Path) -> None:
    assert values(tmp_path, line, "A1") == {"A1": ""}


def test_fields_after_the_second_are_ignored(tmp_path: Path) -> None:
    found = values(tmp_path, b"A1\tPTHR00001\textra\tmore\nB2\tPTHR00002\t\n", "A1", "B2")

    assert found == {"A1": "PTHR00001", "B2": "PTHR00002"}


def test_latin_1_bytes_are_kept(tmp_path: Path) -> None:
    found = values(tmp_path, b"A1\tPTHR\xe9\xff1\n", "A1")

    assert found == {"A1": "PTHR\xe9\xff1"}
    assert found["A1"] is not None
    assert found["A1"].encode("latin-1") == b"PTHR\xe9\xff1"


def test_there_is_no_line_after_a_final_line_feed(tmp_path: Path) -> None:
    # Perl's <FH> gives no empty line there, so an empty ID gets no entry from it.
    assert values(tmp_path, b"A1\tPTHR00001\n", "A1", "") == {"A1": "PTHR00001"}


def test_a_last_line_without_a_line_feed_is_read(tmp_path: Path) -> None:
    found = values(tmp_path, b"A1\tPTHR00001\nB2\tPTHR00002", "A1", "B2")

    assert found == {"A1": "PTHR00001", "B2": "PTHR00002"}


def test_an_empty_file_gives_nothing(tmp_path: Path) -> None:
    assert values(tmp_path, b"", "A1") == {}


@pytest.mark.parametrize(
    ("value", "panther_id"),
    [
        (None, None),
        ("NOHIT", None),
        ("NOHIT\r", "NOHIT\r"),
        ("nohit", "nohit"),
        ("", ""),
        ("PTHR11360:SF130", "PTHR11360:SF130"),
    ],
)
def test_a_stored_nohit_or_no_value_is_no_panther_id(
    value: str | None, panther_id: str | None
) -> None:
    assert panther_id_of(value) == panther_id


# map_ids


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    """A data folder with a made-up file for ENDPU."""
    root = tmp_path / "data"
    folder = root / "refmap" / "19" / "panther_classification"
    folder.mkdir(parents=True)
    (folder / "ENDPU").write_bytes(b"U1G4Q5\tPTHR11360:SF130\nU1GLV9\tPTHR28011\nU1HQ27\tNOHIT\n")
    return root


@pytest.fixture
def unread(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any attempt to read a classification file fails the test."""

    def read(path: Path, ids: object) -> dict[str, str | None]:
        pytest.fail(f"read {path}")

    monkeypatch.setattr(mapping, "read_classification", read)


@pytest.mark.parametrize(
    ("organism", "ids", "message"),
    [
        ("HUMAN", ("P04217",), "HUMAN"),
        ("endpu", ("U1G4Q5",), "endpu"),
        ("ENDPU", (), "no IDs"),
        ("ENDPU", ("U1G4Q5", ""), "''"),
        ("ENDPU", ("A" * 65,), "A" * 65),
        ("ENDPU", ("P04 217",), "'P04 217'"),
        ("ENDPU", ("P04\t217",), "'P04\\t217'"),
        ("ENDPU", ("P04217\n",), "P04217"),
        ("ENDPU", ("P04217é",), "P04217é"),
    ],
)
def test_a_request_the_api_would_reject_is_a_value_error_before_any_file_is_read(
    organism: str, ids: tuple[str, ...], message: str, data_root: Path, unread: None
) -> None:
    with pytest.raises(ValueError, match=re.escape(message)) as raised:
        map_ids(RefmapInput(organism, ids), data_dir=data_root)

    assert not isinstance(raised.value, InputError)


def test_an_id_of_64_printable_characters_is_accepted(data_root: Path) -> None:
    longest = "!" + "~" * 62 + "A"

    result = map_ids(RefmapInput("ENDPU", (longest,)), data_dir=data_root)

    assert result.mappings == (IdMapping(longest, None),)


def test_the_result_has_the_organism_and_one_mapping_per_id_in_order(data_root: Path) -> None:
    ids = ("U1G4Q5", "U1GLV9", "U1G4Q5", "U1HQ27", "P04217", "P04217")

    result = map_ids(RefmapInput("ENDPU", ids), data_dir=data_root)

    assert result == RefmapResult(
        organism="ENDPU",
        mappings=(
            IdMapping("U1G4Q5", "PTHR11360:SF130"),
            IdMapping("U1GLV9", "PTHR28011"),
            IdMapping("U1G4Q5", "PTHR11360:SF130"),
            IdMapping("U1HQ27", None),
            IdMapping("P04217", None),
            IdMapping("P04217", None),
        ),
    )


def test_the_data_folder_comes_from_panther_data_dir(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PANTHER_DATA_DIR", str(data_root))

    result = map_ids(RefmapInput("ENDPU", ("U1GLV9",)))

    assert result.mappings == (IdMapping("U1GLV9", "PTHR28011"),)


def test_a_missing_file_is_missing_data_naming_it(data_root: Path) -> None:
    path = data_root / "refmap" / "19" / "panther_classification" / "ENDPU"
    path.unlink()

    with pytest.raises(MissingDataError, match=re.escape(str(path))) as raised:
        map_ids(RefmapInput("ENDPU", ("U1G4Q5",)), data_dir=data_root)

    assert not isinstance(raised.value, InputError)


def test_a_folder_in_place_of_the_file_is_missing_data_naming_it(data_root: Path) -> None:
    path = data_root / "refmap" / "19" / "panther_classification" / "PEA"
    path.mkdir()

    with pytest.raises(MissingDataError, match=re.escape(str(path))):
        map_ids(RefmapInput("PEA", ("P1",)), data_dir=data_root)


def test_there_is_no_cap_on_the_number_of_ids(data_root: Path) -> None:
    ids = tuple(f"Q{n:05d}" for n in range(150_000))
    folder = data_root / "refmap" / "19" / "panther_classification"
    (folder / "ENDPU").write_text("".join(f"{id}\tPTHR{n:05d}\n" for n, id in enumerate(ids)))

    result = map_ids(RefmapInput("ENDPU", ids), data_dir=data_root)

    assert len(result.mappings) == 150_000
    assert result.mappings[-1] == IdMapping("Q149999", "PTHR149999")


# map_ids on the pinned data


@pytest.mark.data("refmap")
@pytest.mark.parametrize(
    ("id", "panther_id"),
    [
        ("U1G4Q5", "PTHR11360:SF130"),
        ("U1GLV9", "PTHR28011"),
        ("U1HQ27", None),
        ("A0A4Y2E0M5", None),
        ("u1g4q5", None),
        ("U1G4Q5-2", None),
        ("U1G4Q5.1", None),
    ],
)
def test_endpu(id: str, panther_id: str | None, refmap_data: Path) -> None:
    result = map_ids(RefmapInput("ENDPU", (id,)), data_dir=refmap_data.parents[1])

    assert result.mappings == (IdMapping(id, panther_id),)


@pytest.mark.data("refmap")
def test_an_id_from_another_organism_maps_there(refmap_data: Path) -> None:
    result = map_ids(RefmapInput("ARAVE", ("A0A4Y2E0M5",)), data_dir=refmap_data.parents[1])

    assert result.mappings == (IdMapping("A0A4Y2E0M5", "PTHR47331"),)


@pytest.mark.data("refmap")
def test_a_repeated_id_is_mapped_each_time(refmap_data: Path) -> None:
    ids = ("U1G4Q5", "U1GLV9", "U1G4Q5")

    result = map_ids(RefmapInput("ENDPU", ids), data_dir=refmap_data.parents[1])

    assert [item.panther_id for item in result.mappings] == [
        "PTHR11360:SF130",
        "PTHR28011",
        "PTHR11360:SF130",
    ]


@pytest.mark.data("refmap")
def test_a_whole_genome(refmap_data: Path) -> None:
    lines = (refmap_data / "panther_classification" / "ARAVE").read_text().splitlines()
    ids = tuple(line.split("\t")[0] for line in lines)

    result = map_ids(RefmapInput("ARAVE", ids), data_dir=refmap_data.parents[1])

    assert len(result.mappings) == len(lines) == 246_021
    expected = [None if line.split("\t")[1] == "NOHIT" else line.split("\t")[1] for line in lines]
    assert [mapping.panther_id for mapping in result.mappings] == expected


# check_data


@pytest.fixture
def complete(tmp_path: Path) -> Path:
    """A data folder with refmap's stats and an empty file for every organism."""
    root = tmp_path / "complete"
    folder = root / "refmap" / "19"
    (folder / "panther_classification").mkdir(parents=True)
    (folder / "stats").touch()
    for code in ORGANISM_CODES:
        (folder / "panther_classification" / code).touch()
    return root


def test_check_data_passes_with_stats_and_every_organisms_file(complete: Path) -> None:
    check_data(complete)


def test_check_data_names_a_missing_file(complete: Path) -> None:
    (complete / "refmap" / "19" / "panther_classification" / "ENDPU").unlink()

    with pytest.raises(MissingDataError, match="panther_classification/ENDPU") as raised:
        check_data(complete)

    assert "1 of 1,534" in str(raised.value)
    assert str(complete / "refmap" / "19") in str(raised.value)


def test_check_data_names_missing_stats(complete: Path) -> None:
    (complete / "refmap" / "19" / "stats").unlink()

    with pytest.raises(MissingDataError, match="stats"):
        check_data(complete)


def test_check_data_counts_and_names_the_first_few_of_many(tmp_path: Path) -> None:
    with pytest.raises(MissingDataError) as raised:
        check_data(tmp_path)

    message = str(raised.value)
    assert "1,534 of 1,534" in message
    assert "stats, panther_classification/ABRPR" in message
    assert "ZYMTI" not in message


def test_check_data_without_a_data_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PANTHER_DATA_DIR", raising=False)

    with pytest.raises(DataFolderError, match="PANTHER_DATA_DIR"):
        check_data()


@pytest.mark.data("refmap")
def test_check_data_passes_on_the_fetched_data(refmap_data: Path) -> None:
    check_data(refmap_data.parents[1])
