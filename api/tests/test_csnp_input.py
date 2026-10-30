"""The cSNP input rules (openspec scoring-input), on the model, in the test process.

The normalised values reach the engine, not the job, so they're checked here.
"""

from typing import Any

import pytest
from panther_engine.csnp import SPECIES_CODES
from pydantic import ValidationError

from panther_api.jobs.csnp import CsnpInput

VALID: dict[str, Any] = {"sequence": "MKVLWAALLV", "substitutions": ["L4P"], "species": "HUMAN"}
MISSING = object()
LONGEST = 50_000
RAW_LIMIT = 1_000_000
MOST_SUBSTITUTIONS = 1_000
LONGEST_TOKEN = 32


def given(**changes: object) -> dict[str, Any]:
    """The valid input with `changes`; a change to MISSING leaves the field out."""
    data = {**VALID, **changes}
    return {name: value for name, value in data.items() if value is not MISSING}


def rejected(marker: str, **changes: object) -> list[tuple[str | int, ...]]:
    """Validate, expect a rejection, and return each error's `loc`.

    No message may contain `marker`, a distinctive part of the submitted value.
    """
    with pytest.raises(ValidationError) as caught:
        CsnpInput.model_validate(given(**changes))
    errors = caught.value.errors()
    for error in errors:
        assert marker not in error["msg"], error["msg"]
    return [tuple(error["loc"]) for error in errors]


# The sequence: normalised as the website's form did (CsnpScoreForm.java).


def test_a_fasta_header_and_line_breaks_are_removed() -> None:
    sequence = ">sp|P02649|APOE_HUMAN Apolipoprotein E\nMKVLWAALLV\nTFLAGCQAKV\n"

    assert CsnpInput.model_validate(given(sequence=sequence)).sequence == "MKVLWAALLVTFLAGCQAKV"


def test_lower_case_and_spaces_are_normalised() -> None:
    assert CsnpInput.model_validate(given(sequence="  mkvl waal\r\n")).sequence == "MKVLWAAL"


def test_every_kind_of_whitespace_is_removed() -> None:
    sequence = "MK\tVL\x0bWA\x0cAL\r\nLV"

    assert CsnpInput.model_validate(given(sequence=sequence)).sequence == "MKVLWAALLV"


def test_a_header_with_crlf_is_removed() -> None:
    sequence = ">P02649 xyzzy\r\nMKVL\r\nWAAL\r\n"

    assert CsnpInput.model_validate(given(sequence=sequence)).sequence == "MKVLWAAL"


def test_one_greater_than_sign_not_at_the_start_is_kept() -> None:
    # The form removed a header only at the start, and counted two `>` as two sequences.
    assert CsnpInput.model_validate(given(sequence="MKV>L")).sequence == "MKV>L"


def test_the_longest_sequence_is_accepted() -> None:
    assert len(CsnpInput.model_validate(given(sequence="A" * LONGEST)).sequence) == LONGEST


def test_the_residue_limit_counts_after_normalising() -> None:
    sequence = ">header\n" + "\n".join(["A" * 60] * (LONGEST // 60)) + "\n" + "A" * (LONGEST % 60)

    assert len(CsnpInput.model_validate(given(sequence=sequence)).sequence) == LONGEST


@pytest.mark.parametrize(
    ("sequence", "marker"),
    [
        (">only a header xyzzy", "xyzzy"),
        ("", "MKV"),
        (" \n\t ", "MKV"),
        (">one xyzzy\nMKV\n>two\nMKV", "xyzzy"),
        ("MKVxyzzy>>", "xyzzy"),
        ("A" * (LONGEST + 1), "AAAAAAAAAA"),
        ("MKVÄL", "Ä"),
        ("MKV\u0000L", "\u0000"),
        ("MKVß", "ß"),
        ("A" * (RAW_LIMIT + 1), "AAAAAAAAAA"),
    ],
    ids=[
        "only a header",
        "empty",
        "only whitespace",
        "two sequences",
        "two greater-than signs",
        "too long",
        "not ascii",
        "control character",
        "upper-cases to ascii",
        "raw value too long",
    ],
)
def test_a_sequence_that_cant_be_one_protein_is_rejected(sequence: str, marker: str) -> None:
    assert rejected(marker, sequence=sequence) == [("sequence",)]


def test_a_sequence_that_isnt_a_string_is_rejected() -> None:
    assert rejected("12345", sequence=12345) == [("sequence",)]


def test_no_sequence_is_rejected() -> None:
    assert rejected("MKV", sequence=MISSING) == [("sequence",)]


# The substitutions: a list of tokens, upper-cased, each in the legacy CGI's form
# `[A-Z][0-9]+[A-Z]` (decided with the engine developer on PR #19, 2026-10-30).


def test_tokens_are_upper_cased_and_kept_in_order() -> None:
    substitutions = CsnpInput.model_validate(given(substitutions=["L46P", "c130r"])).substitutions

    assert substitutions == ["L46P", "C130R"]


def test_substitutions_that_cant_be_mapped_are_still_accepted() -> None:
    # In the CGI's form, so the legacy scored them: a position past the end, or a wrong
    # wild-type residue, comes back as a "Not scored: Invalid substitution" row.
    tokens = ["G99999R", "M1P", "a10v"]

    assert CsnpInput.model_validate(given(substitutions=tokens)).substitutions == [
        "G99999R",
        "M1P",
        "A10V",
    ]


@pytest.mark.parametrize(
    "token",
    # chr(0x131) is the dotless i, which str.upper() turns into an ASCII I.
    [
        "XYZQW",
        "G1299",
        "G1299|",
        "A1099*",
        "QQ1299R",
        "1299R",
        "G-1299R",
        "G12.99R",
        "a1099" + chr(0x131),
    ],
    ids=[
        "letters",
        "no mutant",
        "pipe as mutant",
        "stop as mutant",
        "two wild-type",
        "no wild-type",
        "dash",
        "dot",
        "non-ascii that upper-cases to ascii",
    ],
)
def test_a_token_that_isnt_a_substitution_is_rejected(token: str) -> None:
    assert rejected(token, substitutions=["L4P", token]) == [("substitutions", 1)]


def test_the_most_substitutions_are_accepted() -> None:
    tokens = [f"A{position}P" for position in range(1, MOST_SUBSTITUTIONS + 1)]

    assert len(CsnpInput.model_validate(given(substitutions=tokens)).substitutions) == 1000


def test_the_longest_token_is_accepted() -> None:
    token = "G" + "1" * (LONGEST_TOKEN - 2) + "R"

    assert CsnpInput.model_validate(given(substitutions=[token])).substitutions == [token]


@pytest.mark.parametrize(
    ("substitutions", "marker"),
    [
        ([], "L4P"),
        ([f"A{position}P" for position in range(1, MOST_SUBSTITUTIONS + 2)], "A1001P"),
        ("L46P xyzzy", "xyzzy"),
        (MISSING, "L4P"),
    ],
    ids=["none", "too many", "not a list", "missing"],
)
def test_substitutions_that_arent_a_list_of_tokens_are_rejected(
    substitutions: object, marker: str
) -> None:
    assert rejected(marker, substitutions=substitutions) == [("substitutions",)]


@pytest.mark.parametrize(
    ("token", "marker"),
    [
        ("L46P xyzzy", "xyzzy"),
        ("xyzzy\t", "xyzzy"),
        ("", "L4P"),
        ("G" + "9" * (LONGEST_TOKEN - 1) + "R", "99999"),
        ("xyzzyÄ", "xyzzy"),
        (46, "46"),
    ],
    ids=["two tokens", "trailing tab", "empty", "too long", "not ascii", "not a string"],
)
def test_a_token_that_isnt_one_token_is_rejected(token: object, marker: str) -> None:
    assert rejected(marker, substitutions=["L4P", token]) == [("substitutions", 1)]


# The species: a species code, required.


@pytest.mark.parametrize("species", ["HUMAN", "RAT", "PLAF7", "SYNY3", "PIG"])
def test_a_species_code_is_accepted(species: str) -> None:
    assert CsnpInput.model_validate(given(species=species)).species == species


def test_every_species_the_engine_scores_is_accepted() -> None:
    for species in SPECIES_CODES:
        assert CsnpInput.model_validate(given(species=species)).species == species


# A species code's shape, but no sequences for it in the PANTHER9 BLAST database: XENLA and
# SALSA are newer PANTHER species, and 9PRIM no species at all.
@pytest.mark.parametrize("species", ["ZZZZZ", "XENLA", "SALSA", "9PRIM"])
def test_a_species_the_engine_doesnt_score_is_rejected(species: str) -> None:
    assert species not in SPECIES_CODES
    assert rejected(species, species=species) == [("species",)]


@pytest.mark.parametrize(
    ("species", "marker"),
    [
        ("xyzzy", "xyzzy"),
        ("HUMAN; rm -rf /", "rm -rf"),
        ("HOMOSAPIENS", "HOMOSAPIENS"),
        ("", "''"),
        ("HUM'N", "HUM'N"),
        ("XYZZY\n", "XYZZY"),
        (9606, "9606"),
        (MISSING, "xyzzy"),
    ],
    ids=[
        "lower case",
        "shell",
        "too long",
        "empty",
        "quote",
        "trailing newline",
        "not a string",
        "missing",
    ],
)
def test_a_species_that_isnt_a_code_is_rejected(species: object, marker: str) -> None:
    assert rejected(marker, species=species) == [("species",)]


# The input as a whole.


def test_every_invalid_field_is_listed() -> None:
    locs = rejected("xyzzy", sequence="", substitutions=[], species=MISSING)

    assert sorted(locs) == [("sequence",), ("species",), ("substitutions",)]


def test_a_field_the_input_doesnt_take_is_rejected() -> None:
    assert rejected("xyzzy", organism="xyzzy") == [("organism",)]
