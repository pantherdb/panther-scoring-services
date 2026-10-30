import multiprocessing
import pickle
from concurrent.futures import ProcessPoolExecutor

import pytest

from panther_engine.core.errors import InputError


class UnknownPair(InputError):
    """A subclass whose constructor doesn't take the message."""

    def __init__(self, family: str, species: str) -> None:
        self.family = family
        self.species = species
        super().__init__(f"No {species} sequences in {family}.")


def raise_input_error() -> None:
    raise InputError("Unknown organism.")


def raise_subclass() -> None:
    raise UnknownPair("PTHR10366", "XENLA")


def succeed() -> str:
    return "done"


def test_copied_between_processes() -> None:
    copy = pickle.loads(pickle.dumps(InputError("Unknown organism.")))  # noqa: S301

    assert type(copy) is InputError
    assert str(copy) == "Unknown organism."


def test_a_subclass_survives_pickling_with_its_attributes() -> None:
    copy = pickle.loads(pickle.dumps(UnknownPair("PTHR10366", "XENLA")))  # noqa: S301

    assert type(copy) is UnknownPair
    assert str(copy) == "No XENLA sequences in PTHR10366."
    assert (copy.family, copy.species) == ("PTHR10366", "XENLA")


def test_raised_in_a_worker_process() -> None:
    with ProcessPoolExecutor(1, mp_context=multiprocessing.get_context("spawn")) as pool:
        future = pool.submit(raise_input_error)

        with pytest.raises(InputError) as raised:
            future.result(timeout=60)

    assert type(raised.value) is InputError
    assert str(raised.value) == "Unknown organism."


def test_a_subclass_with_its_own_constructor_crosses_a_worker() -> None:
    with ProcessPoolExecutor(2, mp_context=multiprocessing.get_context("spawn")) as pool:
        failing = pool.submit(raise_subclass)
        other = pool.submit(succeed)

        with pytest.raises(UnknownPair) as raised:
            failing.result(timeout=60)
        result = other.result(timeout=60)

    assert str(raised.value) == "No XENLA sequences in PTHR10366."
    assert (raised.value.family, raised.value.species) == ("PTHR10366", "XENLA")
    assert result == "done"
