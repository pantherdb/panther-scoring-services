"""The refmap input rules (openspec scoring-input), on the model, in the test process.

What reaches the engine is checked here, on the model, without a job.
"""

from typing import Annotated, Any

import pytest
from panther_engine.refmap import ORGANISM_CODES
from pydantic import Field, TypeAdapter, ValidationError

from panther_api.jobs.fields import Unlisted
from panther_api.jobs.refmap import ProteinId, RefmapInput

VALID: dict[str, Any] = {"organism": "ENDPU", "ids": ["P04217", "P01023"]}
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


# The organism: one of the engine's organism codes, with no default.


@pytest.mark.parametrize("organism", ["ENDPU", "ARAVE", "ECO57"])
def test_an_organism_code_is_accepted(organism: str) -> None:
    assert RefmapInput.model_validate(given(organism=organism)).organism == organism


def test_every_engine_organism_is_accepted() -> None:
    for organism in ORGANISM_CODES:
        assert RefmapInput.model_validate(given(organism=organism)).organism == organism


# PANTHER's own genomes, such as HUMAN, aren't in the generic mapping data (#52).
@pytest.mark.parametrize("organism", ["HUMAN", "ECOLI", "ZZZZZ", "A"])
def test_a_code_the_engine_doesnt_map_for_is_rejected(organism: str) -> None:
    assert rejected(organism, organism=organism) == [("organism",)]


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
    assert rejected("endpu", organism="endpu") == [("organism",)]


def test_no_organism_is_rejected() -> None:
    assert rejected("ENDPU", organism=MISSING) == [("organism",)]


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


# Many bad IDs: checked in one pass, with the errors Pydantic's own check gives (#41).

# The IDs as Pydantic checks them item by item, without the list validator.
PER_ITEM: TypeAdapter[list[str]] = TypeAdapter(
    Annotated[list[ProteinId], Field(min_length=1, max_length=MOST_IDS)]
)
# One of each way an ID can fail.
EACH_FAILURE: list[object] = ["", 4217, "X" * (LONGEST_ID + 1), "XYZZY A", None, "XYZZYÄ", True]


def errors_of(ids: list[object]) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]]]:
    """The model's errors on `ids`, with `loc`s from the list, and Pydantic's own item-by-item
    errors: each error's type, loc, msg and ctx, its values as text, since a ValueError isn't
    equal to its copy."""
    with pytest.raises(ValidationError) as model:
        RefmapInput.model_validate(given(ids=ids))
    with pytest.raises(ValidationError) as per_item:
        PER_ITEM.validate_python(ids)

    def described(error: Any, loc: tuple[str | int, ...]) -> tuple[object, ...]:
        ctx = {name: str(value) for name, value in error.get("ctx", {}).items()}
        return (error["type"], loc, error["msg"], ctx)

    return (
        [described(error, error["loc"][1:]) for error in model.value.errors()],
        [described(error, error["loc"]) for error in per_item.value.errors()],
    )


@pytest.mark.parametrize("bad", [1, 100, 101, 250])
def test_bad_ids_get_pydantics_own_errors(bad: int) -> None:
    # Each bad ID followed by a valid one.
    ids: list[object] = []
    for index in range(bad):
        ids += [EACH_FAILURE[index % len(EACH_FAILURE)], "P04217"]

    model_errors, per_item_errors = errors_of(ids)

    assert model_errors == per_item_errors[:100]


def test_past_100_bad_ids_the_last_error_counts_the_rest() -> None:
    with pytest.raises(ValidationError) as caught:
        RefmapInput.model_validate(given(ids=[""] * MOST_IDS))
    errors = caught.value.errors()

    assert [error["loc"] for error in errors] == [("ids", index) for index in range(100)]
    assert errors[-1]["input"] == Unlisted(MOST_IDS - 100)
    assert not any(isinstance(error["input"], Unlisted) for error in errors[:-1])


def test_up_to_100_bad_ids_are_all_pydantics() -> None:
    with pytest.raises(ValidationError) as caught:
        RefmapInput.model_validate(given(ids=[""] * 100))

    assert len(caught.value.errors()) == 100
    assert all(error["input"] == "" for error in caught.value.errors())


def test_ids_pydantic_would_take_as_strings_are_left_to_it() -> None:
    # Bytes can't come from JSON, but Pydantic takes them as strings: the one pass mustn't count
    # them as bad.
    ids: list[object] = [b"P04217", *[""] * 200]

    model_errors, per_item_errors = errors_of(ids)

    assert len(per_item_errors) == 200
    assert model_errors == per_item_errors


def test_too_many_bad_ids_are_rejected_as_too_many() -> None:
    assert rejected("XYZZY", ids=["XYZZY A"] * (MOST_IDS + 1)) == [("ids",)]


# The input as a whole.


def test_a_field_the_input_doesnt_take_is_rejected() -> None:
    assert rejected("XYZZY", fileContents="XYZZY") == [("fileContents",)]


def test_every_invalid_field_is_listed() -> None:
    assert sorted(rejected("XYZZY", organism="xyzzy", ids=[])) == [("ids",), ("organism",)]


# The log's summary (openspec change add-api-logging; scoring-jobs: The size of a job's input).


def test_the_log_summary_gives_the_organism_and_a_count_not_the_ids() -> None:
    summary = RefmapInput.model_validate(VALID).log_summary()

    assert summary == "ENDPU, 2 IDs"
    for value in VALID["ids"]:
        assert value not in summary
