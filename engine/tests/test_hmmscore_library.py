import pickle

import pytest
from hmmscore_fixtures import BINHMM, FAMILY_MODEL, NAMES, data, edited, lines

from panther_engine.hmmscore.library import (
    PREFIX,
    Kind,
    LibraryFormatError,
    Member,
    Model,
    Name,
    index_records,
    library_member,
    lines_of,
    prefix_folder,
    read_model_file,
    read_models,
    read_names,
)

# The layout


def member(path: str, *, folder: bool = False) -> Member:
    found = library_member(path, folder=folder)
    assert found is not None, path
    return found


@pytest.mark.parametrize(
    ("path", "kind", "family", "subfamily"),
    [
        ("README", Kind.README, None, None),
        ("globals/names.tab", Kind.NAMES, None, None),
        ("globals/binHmm", Kind.BINHMM, None, None),
        ("globals/binHmm.h3f", Kind.H3F, None, None),
        ("globals/binHmm.h3i", Kind.H3I, None, None),
        ("globals/binHmm.h3m", Kind.H3M, None, None),
        ("globals/binHmm.h3p", Kind.H3P, None, None),
        ("books/PTHR10000/hmmer.hmm", Kind.FAMILY_MODEL, "PTHR10000", None),
        ("books/PTHR10000/SF55/hmmer.hmm", Kind.SUBFAMILY_MODEL, "PTHR10000", "SF55"),
        ("books/PTHR10000/cluster.pir", Kind.CLUSTER, "PTHR10000", None),
        ("books/PTHR10000/tree.tree", Kind.TREE, "PTHR10000", None),
    ],
)
def test_each_file_below_the_prefix_has_its_kind(
    path: str, kind: Kind, family: str | None, subfamily: str | None
) -> None:
    assert member(path) == Member(kind, path, family, subfamily)


@pytest.mark.parametrize(
    "path", ["", "globals", "books", "books/PTHR10000", "books/PTHR10000/SF55"]
)
def test_the_layouts_folders_are_folders(path: str) -> None:
    assert member(path, folder=True) == Member(Kind.FOLDER, path)


@pytest.mark.parametrize(
    ("path", "folder"),
    [
        ("books/PTHR10000/notes.txt", False),
        ("books/PTHR10000/../../etc/passwd", False),
        ("books/../globals/names.tab", False),
        ("books/PTHR10000/SF55/../hmmer.hmm", False),
        ("/globals/names.tab", False),
        ("./README", False),
        ("books/PTHR1000/hmmer.hmm", False),
        ("books/PTHR10000/SF/hmmer.hmm", False),
        ("books/PTHR10000/sf55/hmmer.hmm", False),
        ("books/PTHR10000/SF55/cluster.pir", False),
        ("globals/binHmm.h3x", False),
        ("globals/names.tab", True),
        ("globals", False),
        ("books/PTHR10000/SF55/extra", True),
    ],
)
def test_anything_else_is_unexpected(path: str, folder: bool) -> None:
    assert library_member(path, folder=folder) is None


@pytest.mark.parametrize(
    ("name", "above"),
    [
        ("target", True),
        ("target/famlib/rel/PANTHER19.0_altVersion/hmmscoring", True),
        ("target/famlib/rel/PANTHER19.0_altVersion/hmmscoring/PANTHER19.0", True),
        ("target/fam", False),
        ("elsewhere", False),
        ("target/famlib/rel/PANTHER19.0_altVersion/hmmscoring/PANTHER19.0/books", False),
    ],
)
def test_the_prefixs_own_folder_and_those_it_is_in_are_prefix_folders(
    name: str, above: bool
) -> None:
    assert prefix_folder(name, PREFIX) is above


def test_a_model_files_hmm_id_is_its_paths() -> None:
    assert member("books/PTHR10000/hmmer.hmm").hmm_id == "PTHR10000"
    assert member("books/PTHR10000/SF55/hmmer.hmm").hmm_id == "PTHR10000:SF55"
    assert member("globals/names.tab").hmm_id is None


@pytest.mark.parametrize(
    ("path", "kept"),
    [
        ("README", True),
        ("globals/names.tab", True),
        ("globals/binHmm", True),
        ("globals/binHmm.h3p", True),
        ("books/PTHR10000/hmmer.hmm", True),
        ("books/PTHR10000/SF55/hmmer.hmm", True),
        ("books/PTHR10000/cluster.pir", False),
        ("books/PTHR10000/tree.tree", False),
    ],
)
def test_only_what_scoring_reads_is_kept(path: str, kept: bool) -> None:
    assert member(path).kept is kept


# The pressed index


def test_the_index_gives_each_models_offset_in_binhmms_order() -> None:
    # Its keys are sorted by name; binHmm's order is their records' order in binHmm.h3m.
    assert index_records(data("globals/binHmm.h3i")) == [
        ("PTHR99999.SF2.pir", 0),
        ("PTHR99999.orig.30.pir", 7277),
        ("PTHR99999.SF1.pir", 14558),
    ]


# Lines


def test_lines_are_split_at_line_feeds_only_as_perl_reads_them() -> None:
    assert lines_of(b"a\rb\nc\x0bd\n\ne") == ["a\rb\n", "c\x0bd\n", "\n", "e"]
    assert lines_of(b"a\n") == ["a\n"]
    assert lines_of(b"") == []


# names.tab


def test_a_family_line_gives_the_family_id_and_its_name() -> None:
    names = read_names(["PTHR10003.mag.mod\tCU/ZN SUPEROXIDE DISMUTASE\n"], "names.tab")

    assert names == {"PTHR10003": Name("PTHR10003", "CU/ZN SUPEROXIDE DISMUTASE", 1)}


def test_a_subfamily_line_gives_the_subfamily_id() -> None:
    names = read_names(["PTHR10003.SF38.mod\tEXTRACELLULAR SUPEROXIDE DISMUTASE\n"], "names.tab")

    assert names == {
        "PTHR10003:SF38": Name("PTHR10003:SF38", "EXTRACELLULAR SUPEROXIDE DISMUTASE", 1)
    }


def test_the_clean_file_gives_each_id_in_its_order() -> None:
    names = read_names(lines(NAMES), NAMES)

    assert list(names) == ["PTHR99999", "PTHR99999:SF1", "PTHR99999:SF2", "PTHR99999:SF3"]
    assert names["PTHR99999:SF3"] == Name(
        "PTHR99999:SF3", "TEST SUBFAMILY 3, A COPY OF THE FAMILY", 4
    )


def test_a_name_can_be_empty_and_the_last_line_can_lack_a_line_feed() -> None:
    names = read_names(["PTHR10000.mag.mod\t\n", "PTHR10000.SF1.mod\tA NAME"], "names.tab")

    assert names == {
        "PTHR10000": Name("PTHR10000", "", 1),
        "PTHR10000:SF1": Name("PTHR10000:SF1", "A NAME", 2),
    }


def test_line_7_without_a_tab_is_an_error_naming_the_file_and_line_7() -> None:
    content = [f"PTHR1000{n}.mag.mod\tFAMILY {n}\n" for n in range(6)]
    content.append("PTHR10006.mag.mod FAMILY 6\n")

    with pytest.raises(LibraryFormatError) as raised:
        read_names(content, "names.tab")

    assert (raised.value.name, raised.value.line) == ("names.tab", 7)


@pytest.mark.parametrize(
    ("fixture", "line", "message"),
    [
        ("broken/names-no-tab.tab", 2, "a tab and a name"),
        ("broken/names-no-mod.tab", 2, "a tab and a name"),
        ("broken/names-repeated.tab", 5, "PTHR99999:SF1 again, first on line 2"),
        ("broken/names-crlf.tab", 1, "carriage return"),
    ],
)
def test_each_broken_names_file_is_an_error_naming_its_line(
    fixture: str, line: int, message: str
) -> None:
    with pytest.raises(LibraryFormatError, match=message) as raised:
        read_names(lines(fixture), fixture)

    assert (raised.value.name, raised.value.line) == (fixture, line)


@pytest.mark.parametrize(
    "line",
    [
        "PTHR10000.mag.mod\tA NAME\tAND MORE\n",
        "PTHR10000.mag\tA NAME\n",
        "PTHR10000.SF1.pir\tA NAME\n",
        "PTHR1000.mag.mod\tA NAME\n",
        "\n",
    ],
)
def test_a_line_of_any_other_shape_is_an_error(line: str) -> None:
    with pytest.raises(LibraryFormatError, match="a tab and a name") as raised:
        read_names([line], "names.tab")

    assert raised.value.line == 1


def test_the_error_survives_a_trip_to_a_worker_process() -> None:
    error = LibraryFormatError("names.tab", 7, "a message")

    copy = pickle.loads(pickle.dumps(error))  # noqa: S301

    assert (copy.name, copy.line, copy.message, str(copy)) == (
        "names.tab",
        7,
        "a message",
        "names.tab, line 7: a message",
    )


# HMM files


def test_a_model_file_gives_its_format_line_name_length_and_bytes() -> None:
    content = edited(FAMILY_MODEL, "HMMER3/f [3.4 | Aug 2023]", "HMMER3/f [3.1b2 | February 2015]")

    model = read_model_file(content, FAMILY_MODEL)

    assert model == Model(
        format="HMMER3/f [3.1b2 | February 2015]",
        name="PTHR99999.orig.30.pir",
        length=36,
        line=1,
        text="".join(content).encode("latin-1"),
    )


def test_a_models_bytes_are_the_files_even_without_a_last_line_feed() -> None:
    content = lines(FAMILY_MODEL)
    content[-1] = "//"

    model = read_model_file(content, FAMILY_MODEL)

    assert model.text == data(FAMILY_MODEL)[:-1]


def test_a_flat_library_gives_its_models_in_order() -> None:
    models = list(read_models(lines(BINHMM), BINHMM))

    assert [(model.name, model.length, model.line) for model in models] == [
        ("PTHR99999.SF2.pir", 36, 1),
        ("PTHR99999.orig.30.pir", 36, 131),
        ("PTHR99999.SF1.pir", 36, 261),
    ]
    assert models[1].text == data(FAMILY_MODEL)


def test_two_models_in_a_model_file_are_an_error_at_the_second_models_first_line() -> None:
    with pytest.raises(LibraryFormatError, match="more than one model") as raised:
        read_model_file(lines("broken/two-models.hmm"), "two-models.hmm")

    assert (raised.value.name, raised.value.line) == ("two-models.hmm", 131)


def test_a_file_that_ends_before_its_last_models_end_is_an_error_at_its_last_line() -> None:
    with pytest.raises(LibraryFormatError, match="ends before the model's //") as raised:
        list(read_models(lines("broken/truncated.hmm"), "truncated.hmm"))

    assert (raised.value.name, raised.value.line) == ("truncated.hmm", 129)


def test_a_model_that_starts_before_the_last_one_ends_is_an_error_at_its_first_line() -> None:
    content = [*lines("broken/truncated.hmm"), *lines(FAMILY_MODEL)]

    with pytest.raises(LibraryFormatError, match="before the last model's //") as raised:
        list(read_models(content, "binHmm"))

    assert raised.value.line == 130


@pytest.mark.parametrize(
    ("content", "line", "message"),
    [
        (lines("broken/no-name.hmm"), 1, "no NAME"),
        ([line for line in lines(FAMILY_MODEL) if not line.startswith("LENG")], 1, "no LENG"),
        (edited(FAMILY_MODEL, "LENG  36\n", "LENG  thirty-six\n"), 3, "LENG isn't"),
        (edited(FAMILY_MODEL, "LENG  36\n", "LENG  36\nNAME  OTHER\n"), 4, "a second NAME"),
        (edited(FAMILY_MODEL, "LENG  36\n", "LENG  36\r\n"), 3, "carriage return"),
        (["# a comment\n", *lines(FAMILY_MODEL)], 1, "outside a model"),
        ([*lines(FAMILY_MODEL), "\n"], 131, "outside a model"),
    ],
)
def test_a_broken_model_is_an_error_naming_its_line(
    content: list[str], line: int, message: str
) -> None:
    with pytest.raises(LibraryFormatError, match=message) as raised:
        list(read_models(content, "hmmer.hmm"))

    assert (raised.value.name, raised.value.line) == ("hmmer.hmm", line)


def test_a_model_file_without_a_model_is_an_error() -> None:
    with pytest.raises(LibraryFormatError, match="no model"):
        read_model_file([], "hmmer.hmm")
