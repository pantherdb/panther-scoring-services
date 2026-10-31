"""The refmap input rules (openspec scoring-input), on the model, in the test process.

What would reach the engine isn't in any job yet (a valid request gets a 501), so it's checked
here.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from panther_api.jobs.refmap import RefmapInput

VALID: dict[str, Any] = {"organism": "HUMAN", "ids": ["P04217", "P01023"]}
MISSING = object()
MOST_IDS = 100_000
LONGEST_ID = 64


def given(**changes: object) -> dict[str, Any]:
    """The valid input with `changes`; a change to MISSING leaves the field out."""
    data = {**VALID, **changes}
    return {name: value for name, value in data.items() if value is not MISSING}


def rejected(marker: str, **changes: object) -> list[tuple[str | int, ...]]:
    """Validate, expect a rejection, and return each error's `loc`.

    No message may contain `marker`, a distinctive part of the submitted value.
    """
    with pytest.raises(ValidationError) as caught:
        RefmapInput.model_validate(given(**changes))
    errors = caught.value.errors()
    for error in errors:
        assert marker not in error["msg"], error["msg"]
    return [tuple(error["loc"]) for error in errors]


# The organism: the shape of a UniProt species code, with no default.


@pytest.mark.parametrize("organism", ["HUMAN", "ECOLI", "9BACT", "A"])
def test_an_organism_code_is_accepted(organism: str) -> None:
    assert RefmapInput.model_validate(given(organism=organism)).organism == organism


@pytest.mark.parametrize(
    ("organism", "marker"),
    [
        ("xyzzy", "xyzzy"),
        ("../../etc/passwd", "passwd"),
        ("XYZZY|", "XYZZY"),
        ("Homo_sapiens_XYZZY", "XYZZY"),
        ("XYZZY1", "XYZZY"),
        ("XYZZY\n", "XYZZY"),
        ("", "''"),
    ],
    ids=["lower case", "a path", "a pipe", "a long name", "too long", "trailing newline", "empty"],
)
def test_an_organism_of_another_shape_is_rejected(organism: str, marker: str) -> None:
    assert rejected(marker, organism=organism) == [("organism",)]


def test_an_organism_isnt_upper_cased() -> None:
    assert rejected("human", organism="human") == [("organism",)]


def test_no_organism_is_rejected() -> None:
    assert rejected("HUMAN", organism=MISSING) == [("organism",)]


def test_an_organism_that_isnt_a_string_is_rejected() -> None:
    assert rejected("12345", organism=12345) == [("organism",)]


# The IDs: kept exactly as submitted, in order, repeats included (REFMAP-1, REFMAP-4).


def test_ids_are_kept_as_submitted_and_in_order() -> None:
    ids = ["P04217", "p04217", "P04217", "P04217-2", "Q9H2F3.1"]

    assert RefmapInput.model_validate(given(ids=ids)).ids == ids


def test_ids_with_punctuation_are_accepted() -> None:
    ids = ["A0A024RBG1", "sp|P04217|A1BG_HUMAN", "P04217,P01023", "ENSG00000121410", "x+y;z"]

    assert RefmapInput.model_validate(given(ids=ids)).ids == ids


def test_the_most_ids_are_accepted() -> None:
    ids = [f"P{index:05d}" for index in range(MOST_IDS)]

    assert len(RefmapInput.model_validate(given(ids=ids)).ids) == MOST_IDS


def test_the_longest_id_is_accepted() -> None:
    longest = "X" * LONGEST_ID

    assert RefmapInput.model_validate(given(ids=[longest])).ids == [longest]


def test_too_many_ids_are_rejected() -> None:
    ids = ["P04217"] * (MOST_IDS + 1)

    assert rejected("P04217", ids=ids) == [("ids",)]


def test_no_ids_are_rejected() -> None:
    assert rejected("P04217", ids=[]) == [("ids",)]


def test_missing_ids_are_rejected() -> None:
    assert rejected("P04217", ids=MISSING) == [("ids",)]


def test_ids_that_arent_a_list_are_rejected() -> None:
    assert rejected("XYZZY", ids="XYZZY\nP04217") == [("ids",)]


@pytest.mark.parametrize(
    "bad",
    [
        "XYZZY P04217",
        "XYZZY\tvalue",
        "XYZZY ",
        " XYZZY",
        "XYZZY\r",
        "XYZZYÄ",
        "XYZZY\u0000",
        "XYZZY" + "X" * (LONGEST_ID - 4),
    ],
    ids=[
        "two ids",
        "a tab and a value",
        "a trailing space",
        "a leading space",
        "a carriage return",
        "not ascii",
        "a control character",
        "too long",
    ],
)
def test_an_id_that_isnt_one_id_is_rejected_at_its_index(bad: str) -> None:
    assert rejected("XYZZY", ids=["P04217", bad]) == [("ids", 1)]


def test_an_empty_id_is_rejected_at_its_index() -> None:
    assert rejected("''", ids=["P04217", ""]) == [("ids", 1)]


def test_an_id_that_isnt_a_string_is_rejected_at_its_index() -> None:
    assert rejected("4217", ids=["P04217", 4217]) == [("ids", 1)]


def test_each_bad_id_is_listed() -> None:
    assert rejected("XYZZY", ids=["XYZZY A", "P04217", "", "XYZZY\tB"]) == [
        ("ids", 0),
        ("ids", 2),
        ("ids", 3),
    ]


# The input as a whole.


def test_a_field_the_input_doesnt_take_is_rejected() -> None:
    assert rejected("XYZZY", fileContents="XYZZY") == [("fileContents",)]


def test_every_invalid_field_is_listed() -> None:
    assert sorted(rejected("XYZZY", organism="xyzzy", ids=[])) == [("ids",), ("organism",)]
