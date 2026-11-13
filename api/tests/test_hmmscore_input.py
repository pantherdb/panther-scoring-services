"""The hmmscore input rules (openspec scoring-input), on the model, in the test process.

The normalised values reach the engine, not the job, so they're checked here. The residue limit is
a setting the router checks (test_jobs.py).
"""

from typing import Any

import pytest
from pydantic import ValidationError
from pydantic_core import ErrorDetails

from panther_api.jobs.hmmscore import HmmHit, HmmscoreInput, HmmscoreResult

MISSING = object()
RAW_LIMIT = 1_000_000


def given(sequence: object) -> dict[str, Any]:
    """The input with this sequence; MISSING leaves it out."""
    return {} if sequence is MISSING else {"sequence": sequence}


def accepted(sequence: str) -> str:
    """Validate, and return the sequence that would be scored."""
    return HmmscoreInput.model_validate(given(sequence)).sequence


def rejected(sequence: object, marker: str) -> list[ErrorDetails]:
    """Validate, expect a rejection, and return the errors.

    No message may contain `marker`, a distinctive part of the submitted value.
    """
    with pytest.raises(ValidationError) as caught:
        HmmscoreInput.model_validate(given(sequence))
    errors = caught.value.errors()
    for error in errors:
        assert marker not in error["msg"], error["msg"]
    return errors


def locs(errors: list[ErrorDetails]) -> list[tuple[str | int, ...]]:
    return [tuple(error["loc"]) for error in errors]


# Normalised as cSNP's sequence is.


def test_a_fasta_header_and_line_breaks_are_removed() -> None:
    sequence = ">sp|P02649|APOE_HUMAN Apolipoprotein E\nMKVLWAALLV\nTFLAGCQAKV\n"

    assert accepted(sequence) == "MKVLWAALLVTFLAGCQAKV"


def test_lower_case_and_spaces_are_normalised() -> None:
    assert accepted("  mkvl waal\r\n") == "MKVLWAAL"


def test_a_header_after_a_blank_line_is_removed() -> None:
    # The website removed a header only at the first character, so it left this one in
    # (HMMSCORE-6). The API trims first, as for cSNP.
    assert accepted("\n  >sp|P02649|APOE_HUMAN\nMKVLWAALLV\n") == "MKVLWAALLV"


def test_every_kind_of_whitespace_is_removed() -> None:
    assert accepted("MK\tVL\x0bWA\x0cAL\r\nLV") == "MKVLWAALLV"


# Only letters, and a single `*` at the end.


def test_a_stop_at_the_end_and_the_uncommon_letters_are_accepted() -> None:
    assert accepted("mkvbjouxz*\n") == "MKVBJOUXZ*"


def test_every_letter_is_accepted() -> None:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    assert accepted(letters.lower() + letters) == letters + letters


@pytest.mark.parametrize(
    "sequence",
    ["MKV1L", "MKV-L", "MKV+L", "MKV>LW", "MKVÄL", "MKV\u0000L", "MKVß"],
    ids=["digit", "dash", "plus", "greater-than", "not ascii", "control", "upper-cases to ascii"],
)
def test_a_character_hmmscan_doesnt_read_is_rejected(sequence: str) -> None:
    errors = rejected(sequence, sequence)

    assert locs(errors) == [("sequence",)]
    assert errors[0]["type"] == "value_error"


@pytest.mark.parametrize(
    "sequence",
    ["MKV*L", "MKV.L", "MKV_L", "MKV~L", "MKVL**"],
    ids=["inner stop", "dot", "underscore", "tilde", "two stops"],
)
def test_characters_the_two_hmmer_versions_score_differently_are_rejected(sequence: str) -> None:
    assert locs(rejected(sequence, sequence)) == [("sequence",)]


def test_a_rejected_character_isnt_in_the_message() -> None:
    errors = rejected(">xyzzy\nQWERTYXYZZY1QWERTY", "QWERTY")

    assert locs(errors) == [("sequence",)]
    assert "xyzzy" not in errors[0]["msg"].lower()


@pytest.mark.parametrize(
    ("sequence", "marker"),
    [
        (">only a header xyzzy", "xyzzy"),
        (">only a header xyzzy\n*", "xyzzy"),
        ("*", "MKV"),
        ("", "MKV"),
        (" \n\t ", "MKV"),
        (">one xyzzy\nMKV\n>two\nMKV", "xyzzy"),
        ("MKVxyzzy>>", "xyzzy"),
    ],
    ids=[
        "only a header",
        "a stop with no residues",
        "only a stop",
        "empty",
        "only whitespace",
        "two sequences",
        "two greater-than signs",
    ],
)
def test_a_sequence_that_cant_be_one_protein_is_rejected(sequence: str, marker: str) -> None:
    assert locs(rejected(sequence, marker)) == [("sequence",)]


def test_too_long_before_normalising_is_rejected_by_its_length() -> None:
    # One residue once normalised: the raw length rejects it, not the residue limit.
    errors = rejected("M" + " " * RAW_LIMIT, "MMM")

    assert locs(errors) == [("sequence",)]
    assert errors[0]["type"] == "string_too_long"


def test_the_longest_raw_sequence_is_accepted() -> None:
    assert accepted("M" + " " * (RAW_LIMIT - 1)) == "M"


def test_no_residue_limit_in_the_model() -> None:
    # The configured limit is the router's (design.md, decision 7).
    assert len(accepted("A" * 50_001)) == 50_001


def test_a_sequence_that_isnt_a_string_is_rejected() -> None:
    assert locs(rejected(12345, "12345")) == [("sequence",)]


def test_no_sequence_is_rejected() -> None:
    assert locs(rejected(MISSING, "MKV")) == [("sequence",)]


def test_a_field_the_input_doesnt_take_is_rejected() -> None:
    # The website's form also sent `opType`.
    with pytest.raises(ValidationError) as caught:
        HmmscoreInput.model_validate({"sequence": "MKV", "opType": "hmm"})

    assert locs(caught.value.errors()) == [("opType",)]


# Residues: letters only. A final `*` isn't counted.


def test_residues_are_the_letters() -> None:
    assert HmmscoreInput.model_validate(given("MKVLW")).residues == 5


def test_a_final_stop_isnt_a_residue() -> None:
    assert HmmscoreInput.model_validate(given("MKVLW*")).residues == 5


# The log's summary (scoring-jobs: The size of a job's input).


def test_the_log_summary_gives_the_residues_not_the_sequence() -> None:
    summary = HmmscoreInput.model_validate(given(">sp|header\nMKVLW AALLV\nQWERT*")).log_summary()

    assert summary == "15 residues"
    for value in ("MKVLW", "QWERT", "header"):
        assert value not in summary


def test_the_log_summary_says_one_in_the_singular() -> None:
    assert HmmscoreInput.model_validate(given("M")).log_summary() == "1 residue"


# The result: every field required, only `hit` nullable.


def test_a_hit_needs_every_field() -> None:
    with pytest.raises(ValidationError) as caught:
        HmmHit.model_validate({"panther_id": "PTHR00000"})

    assert sorted(locs(caught.value.errors())) == [
        ("alignment",),
        ("evalue",),
        ("name",),
        ("score",),
    ]


def test_the_result_needs_hit_even_when_null() -> None:
    with pytest.raises(ValidationError):
        HmmscoreResult.model_validate({})

    assert HmmscoreResult.model_validate({"hit": None}).hit is None


def test_a_hit_keeps_its_strings_as_given() -> None:
    # Made-up values: no real family, name or score.
    hit = HmmHit(
        panther_id="PTHR00000:SF0",
        name="MADE-UP NAME",
        evalue="1.0e-00",
        score="0.0",
        alignment="made-up alignment",
    )

    assert HmmscoreResult(hit=hit).model_dump()["hit"]["evalue"] == "1.0e-00"
