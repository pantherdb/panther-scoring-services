"""Mapping IDs to PANTHER families for one organism, as `map_panther.pl` does.

The Perl reads the organism's classification file into a hash, one line at a time: `chomp`, then
`my ($id, $pthr) = split(/\t/, $line)`, and a later line for an ID replaces an earlier one. Then
it looks up each ID of the list exactly, and prints the PANTHER ID, or `NOHIT` where the hash has
no defined value. Here the file is read the same way, as bytes, keeping only the requested IDs.
"""

import re
from collections.abc import Collection, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from panther_engine.core.data import MissingDataError, service_folder
from panther_engine.refmap.organisms import (
    CLASSIFICATION,
    ORGANISM_CODES,
    ORGANISM_NAMES,
    SERVICE,
    STATS,
    VERSION,
)

ENCODING = "latin-1"
NOHIT = "NOHIT"
# Each organism's whole classification as JSON, gzipped, built from its file by `refmap data
# build-json`: `refmap/19/classification_json/<code>.json.gz`.
CLASSIFICATION_JSON = "classification_json"
JSON_SUFFIX = ".json.gz"
# The API's rule for an ID (`add-refmap-job`, design decision 4): 1 to 64 printable ASCII
# characters, with no whitespace.
ID = re.compile(r"[!-~]{1,64}")
# How many missing files check_data names.
NAMED = 5


@dataclass(frozen=True)
class RefmapInput:
    """IDs to map for one organism, given by its code, such as `ENDPU`."""

    organism: str
    ids: tuple[str, ...]


@dataclass(frozen=True)
class IdMapping:
    """One ID as submitted, and its PANTHER ID: a subfamily such as `PTHR11360:SF130`, or a family
    such as `PTHR28011`. `None` where the legacy printed `NOHIT`."""

    id: str
    panther_id: str | None


@dataclass(frozen=True)
class RefmapResult:
    """The organism mapped against, and one mapping per input ID, in input order."""

    organism: str
    mappings: tuple[IdMapping, ...]


def check_input(request: RefmapInput) -> None:
    """Raise ValueError for a request the API would reject. Not an InputError: callers check
    first, so reaching the engine with one is a bug."""
    if request.organism not in ORGANISM_CODES:
        raise ValueError(f"not an organism refmap maps for: {request.organism!r}")
    if not request.ids:
        raise ValueError("no IDs to map")
    for number, value in enumerate(request.ids, 1):
        if not ID.fullmatch(value):
            raise ValueError(
                f"ID {number} isn't 1 to 64 printable ASCII characters with no whitespace: "
                f"{value!r}"
            )


def classification_file(organism: str, data_dir: Path | str | None = None) -> Path:
    """An organism's classification file: `refmap/19/panther_classification/<code>` in the data
    folder (`PANTHER_DATA_DIR` by default)."""
    return service_folder(SERVICE, VERSION, data_dir) / CLASSIFICATION / organism


def classification_json_file(organism: str, data_dir: Path | str | None = None) -> Path:
    """An organism's whole classification as gzipped JSON, built from its classification file:
    `refmap/19/classification_json/<code>.json.gz` in the data folder (`PANTHER_DATA_DIR` by
    default). It holds `{"organism": <code>, "mappings": [{"id", "panther_id"}, ...]}`, one
    mapping per line of the file (`classification_mappings`)."""
    folder = service_folder(SERVICE, VERSION, data_dir) / CLASSIFICATION_JSON
    return folder / (organism + JSON_SUFFIX)


def classification_lines(path: Path) -> Iterator[tuple[str, str | None]]:
    """Each line of the classification file at `path`, in order, as `map_panther.pl` splits it:
    the ID, and the value, `None` where the line has no tab. Read a line at a time.

    - **Lines** end at `\\n` alone, so a `\\r` stays in the value (`REFMAP-3`). There's no line
      after a final `\\n`, as Perl's `<FH>` gives none.
    - **Fields:** assigned to two scalars, Perl's `split` has an implicit limit of 3, so a
      trailing empty field is kept. The ID is the text before the first tab, and the value the
      text after it, up to the next tab: `A1` has no value, and `A1\\t` an empty one.
    - **Bytes** are decoded as Latin-1, so each byte is one character, as in Perl.

    Raises OSError if the file can't be opened or read.
    """
    with path.open("rb") as lines:
        for raw in lines:
            line = raw.decode(ENCODING).removesuffix("\n")
            key, tab, rest = line.partition("\t")
            yield key, rest.partition("\t")[0] if tab else None


def classification_mappings(
    organism: str, data_dir: Path | str | None = None
) -> Iterator[IdMapping]:
    """Every line of the organism's classification file as a mapping, in the file's order, a
    repeated ID once for each of its lines: the line's ID, and its PANTHER ID, or `None` for
    `NOHIT` or no value. Each line is read as `map_ids` reads it (`classification_lines`); unlike
    `map_ids`, which gives the last line's value for a repeated ID, every line is kept, so the
    mappings rebuild the file.

    Raises ValueError for an organism refmap doesn't map for, before reading anything;
    DataFolderError if no data folder is given or set; and MissingDataError, naming the file, if
    it is missing or can't be read.
    """
    if organism not in ORGANISM_CODES:
        raise ValueError(f"not an organism refmap maps for: {organism!r}")
    path = classification_file(organism, data_dir)
    try:
        path.stat()
    except OSError as error:
        raise MissingDataError(f"can't read the classification file {path}: {error}") from error
    return _mappings(path)


def _mappings(path: Path) -> Iterator[IdMapping]:
    try:
        for key, value in classification_lines(path):
            yield IdMapping(key, panther_id_of(value))
    except OSError as error:
        raise MissingDataError(f"can't read the classification file {path}: {error}") from error


def check_classification_json(
    data_dir: Path | str | None = None, organisms: Iterable[str] = ORGANISM_NAMES
) -> None:
    """Check that the data folder holds every organism's classification JSON. Raises
    MissingDataError, naming the folder, how many files are missing and the first few, if it
    doesn't. One `stat` a file; no file is read."""
    folder = service_folder(SERVICE, VERSION, data_dir) / CLASSIFICATION_JSON
    expected = list(organisms)
    missing = [code for code in expected if not classification_json_file(code, data_dir).is_file()]
    if missing:
        named = ", ".join(code + JSON_SUFFIX for code in missing[:NAMED])
        more = f" and {len(missing) - NAMED:,} more" if len(missing) > NAMED else ""
        raise MissingDataError(
            f"the refmap classification JSON folder {folder} lacks {len(missing):,} of "
            f"{len(expected):,} files: {named}{more}"
        )


def map_ids(request: RefmapInput, *, data_dir: Path | str | None = None) -> RefmapResult:
    """Map each ID for the request's organism, as `map_panther.pl` does: exactly as given, in
    order, a repeated ID each time.

    Raises ValueError for a request the API would reject, before reading anything;
    DataFolderError if no data folder is given or set; and MissingDataError, naming the file, if
    the organism's file is missing or can't be read (divergence 9: the Perl answered `NOHIT` for
    every ID).
    """
    check_input(request)
    path = classification_file(request.organism, data_dir)
    try:
        values = read_classification(path, set(request.ids))
    except OSError as error:
        raise MissingDataError(f"can't read the classification file {path}: {error}") from error
    return RefmapResult(
        organism=request.organism,
        mappings=tuple(IdMapping(id, panther_id_of(values.get(id))) for id in request.ids),
    )


def check_data(data_dir: Path | str | None = None) -> None:
    """Check that the refmap data folder holds `stats` and every organism's classification file.
    Raises MissingDataError, naming the folder, how many files are missing and the first few, if
    it doesn't.

    It's cheap: one `stat` a file, 1,534 in all, and no file is read. `refmap data verify` checks
    the files' contents.
    """
    folder = service_folder(SERVICE, VERSION, data_dir)
    expected = [STATS, *(f"{CLASSIFICATION}/{code}" for code in ORGANISM_NAMES)]
    missing = [name for name in expected if not (folder / name).is_file()]
    if missing:
        named = ", ".join(missing[:NAMED])
        more = f" and {len(missing) - NAMED:,} more" if len(missing) > NAMED else ""
        raise MissingDataError(
            f"the refmap data folder {folder} lacks {len(missing):,} of {len(expected):,} files: "
            f"{named}{more}"
        )


def read_classification(path: Path, ids: Collection[str]) -> dict[str, str | None]:
    """The value the Perl's hash holds for each of `ids` found in the classification file at
    `path`: the last line's, `None` where that line has no tab. IDs not in the file are absent.
    Lines and fields are read by `classification_lines`, which `classification_mappings` shares.

    Raises OSError if the file can't be read.
    """
    wanted = ids if isinstance(ids, set | frozenset) else set(ids)
    found: dict[str, str | None] = {}
    for key, value in classification_lines(path):
        if key in wanted:
            found[key] = value
    return found


def read_id_list(content: bytes) -> tuple[str, ...]:
    """The IDs in a gene list, as `map_panther.pl` reads its `-g` file: one per line, with every
    `\r` removed, and the text before the first tab. Lines end at `\n`, with none after a final
    `\n`. An empty line gives an empty ID, which `map_ids` refuses. Decoded as Latin-1."""
    lines = content.decode(ENCODING).split("\n")
    if lines[-1] == "":
        lines.pop()
    return tuple(line.replace("\r", "").partition("\t")[0] for line in lines)


def render(mapping: IdMapping) -> str:
    """A mapping as the first two fields of the Perl's line: the ID, a tab, and the PANTHER ID or
    `NOHIT`."""
    return f"{mapping.id}\t{NOHIT if mapping.panther_id is None else mapping.panther_id}"


def panther_id_of(value: str | None) -> str | None:
    """The PANTHER ID for a value from the file: `None` for no value, or for `NOHIT` exactly,
    which the Perl printed as it prints an ID that isn't in the file."""
    return None if value is None or value == NOHIT else value
