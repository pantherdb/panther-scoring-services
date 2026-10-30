"""What the PAML_RST library readers share: their one error, and how they take lines.

Each reader takes an iterable of lines, as read with their line endings, and a name for errors. The
survey feeds it tar members and the port feeds it files (`open_lines`). The files are ASCII apart
from the odd NUL byte, so they are read as Latin-1, which never fails to decode.
"""

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Self

ENCODING = "latin-1"
CARRIAGE_RETURN = "carriage return in the line (CRLF line ends?)"


class LibraryFormatError(Exception):
    """A library file that doesn't have the expected shape. Names the file and the 1-based line.

    This is never an `InputError`: a broken data file isn't the user's fault.
    """

    def __init__(self, name: str, line: int | None, message: str) -> None:
        self.name = name
        self.line = line
        self.message = message
        where = name if line is None else f"{name}, line {line}"
        super().__init__(f"{where}: {message}")

    def __reduce__(self) -> tuple[type[Self], tuple[str, int | None, str]]:
        # Rebuilt from its own fields, so it survives the API's worker processes.
        return type(self), (self.name, self.line, self.message)


def numbered(lines: Iterable[str], name: str) -> Iterator[tuple[int, str]]:
    """Each line with its 1-based number, without its line feed. A carriage return is an error."""
    for number, line in enumerate(lines, 1):
        if "\r" in line:
            raise LibraryFormatError(name, number, CARRIAGE_RETURN)
        yield number, line.removesuffix("\n")


def open_lines(path: Path) -> Iterator[str]:
    """The lines of a library file, with their line endings as they are on disk."""
    with path.open(encoding=ENCODING, newline="") as stream:
        yield from stream
