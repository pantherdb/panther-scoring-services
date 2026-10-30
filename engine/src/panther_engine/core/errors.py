"""The engine's input error: input that a service can't process as a whole."""

from typing import Any, Self


class InputError(Exception):
    """Input that a service can't process as a whole. Raised with one argument, the message.

    The API reports it as a failed job with status 422, and shows the message as it is. So the
    message:

    - is written for the person who submitted the input, and says what to fix;
    - contains no file paths, tool output or internal identifiers;
    - is only for a problem with the input as a whole. A problem with one item, such as one
      substitution that can't be mapped, belongs in the service's result.

    Subclasses may take other constructor arguments. `__reduce__` rebuilds an instance without
    calling the subclass's `__init__`, so every subclass keeps its type, message and attributes
    when it's passed from a worker process to the API's.
    """

    def __reduce__(self) -> tuple[Any, tuple[type[Self], str, dict[str, Any]]]:
        return _rebuild, (type(self), str(self), dict(self.__dict__))


def _rebuild[E: InputError](cls: type[E], message: str, state: dict[str, Any]) -> E:
    error = cls.__new__(cls)
    Exception.__init__(error, message)
    error.__dict__.update(state)
    return error
