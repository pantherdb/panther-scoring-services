"""The PANTHER HMM library: its layout, and readers for `globals/names.tab` and HMMER3 text models.

The layout is the tarball's below its member prefix:

    README
    globals/names.tab                 an HMM key and a name per line
    globals/binHmm                    the flat library, if the tarball has it
    globals/binHmm.h3f, .h3i, .h3m, .h3p   the pressed library hmmscan reads
    books/PTHRnnnnn/hmmer.hmm         a family's model
    books/PTHRnnnnn/SFn/hmmer.hmm     a subfamily's model
    books/PTHRnnnnn/cluster.pir, tree.tree   for coding-SNP analysis; scoring never reads them

A member's path is matched against these exactly, so `..`, absolute paths and other names are
unexpected, never a path to write.

The readers are strict. Each takes an iterable of lines, as read with their line endings, and a
name for errors, so the survey can feed it tar members and the port can feed it files. The files
are ASCII, read as Latin-1, which never fails to decode. A line of any other shape is a
`LibraryFormatError` naming the file and line. `legacy.py` has `pantherScore.pl`'s looser readings.
"""

import re
import struct
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import StrEnum
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


def lines_of(content: bytes) -> list[str]:
    """A file's lines, with their line feeds, split at line feeds only, as Perl reads them."""
    parts = content.decode(ENCODING).split("\n")
    lines = [part + "\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


# The layout

# PANTHER 19's member prefix: every member of PANTHER19.0_hmmscoring.tgz is below it.
PREFIX = "target/famlib/rel/PANTHER19.0_altVersion/hmmscoring/PANTHER19.0/"


def prefix_folder(name: str, prefix: str) -> bool:
    """Whether a folder member is the prefix's own folder, or one of those it's in."""
    return prefix.startswith(name + "/")


class Kind(StrEnum):
    README = "README"
    NAMES = "globals/names.tab"
    BINHMM = "globals/binHmm"
    H3F = "globals/binHmm.h3f"
    H3I = "globals/binHmm.h3i"
    H3M = "globals/binHmm.h3m"
    H3P = "globals/binHmm.h3p"
    FAMILY_MODEL = "family model"
    SUBFAMILY_MODEL = "subfamily model"
    CLUSTER = "cluster.pir"
    TREE = "tree.tree"
    FOLDER = "folder"


GLOBALS = (Kind.README, Kind.NAMES, Kind.BINHMM, Kind.H3F, Kind.H3I, Kind.H3M, Kind.H3P)
PRESSED = (Kind.H3F, Kind.H3I, Kind.H3M, Kind.H3P)
MODELS = (Kind.FAMILY_MODEL, Kind.SUBFAMILY_MODEL)
# What fetching keeps: everything scoring reads. Folders are made as files need them.
KEPT = frozenset((*GLOBALS, *MODELS))

FAMILY = r"PTHR[0-9]{5}"
SUBFAMILY = r"SF[0-9]+"
BOOKS_FILE = re.compile(
    rf"books/({FAMILY})/(?:({SUBFAMILY})/)?(hmmer\.hmm|cluster\.pir|tree\.tree)"
)
BOOKS_FOLDER = re.compile(rf"books/({FAMILY})(?:/({SUBFAMILY}))?")
FOLDERS = ("", "globals", "books")


@dataclass(frozen=True)
class Member:
    kind: Kind
    path: str
    """The path below the prefix, rebuilt from what matched."""
    family: str | None = None
    subfamily: str | None = None

    @property
    def hmm_id(self) -> str | None:
        """A model file's HMM ID, from its path: `PTHRnnnnn` or `PTHRnnnnn:SFn`."""
        if self.kind not in MODELS or self.family is None:
            return None
        return self.family if self.subfamily is None else f"{self.family}:{self.subfamily}"

    @property
    def kept(self) -> bool:
        return self.kind in KEPT


def library_member(path: str, *, folder: bool = False) -> Member | None:
    """The kind of a member, a file or else a folder, from its path below the prefix. None for a
    path the layout doesn't have."""
    if folder:
        if path in FOLDERS:
            return Member(Kind.FOLDER, path)
        if match := BOOKS_FOLDER.fullmatch(path):
            family, subfamily = match[1], match[2]
            rebuilt = f"books/{family}" if subfamily is None else f"books/{family}/{subfamily}"
            return Member(Kind.FOLDER, rebuilt)
        return None
    for kind in GLOBALS:
        if path == kind.value:
            return Member(kind, kind.value)
    if match := BOOKS_FILE.fullmatch(path):
        family, subfamily, file = match[1], match[2], match[3]
        if file == "hmmer.hmm":
            if subfamily is None:
                return Member(Kind.FAMILY_MODEL, f"books/{family}/{file}", family)
            return Member(
                Kind.SUBFAMILY_MODEL, f"books/{family}/{subfamily}/{file}", family, subfamily
            )
        if subfamily is None:
            kind = Kind.CLUSTER if file == "cluster.pir" else Kind.TREE
            return Member(kind, f"books/{family}/{file}", family)
    return None


# names.tab


@dataclass(frozen=True)
class Name:
    hmm_id: str
    name: str
    line: int


NAMES_LINE = re.compile(rf"({FAMILY})\.(?:mag|({SUBFAMILY}))\.mod\t([^\t]*)")
NAMES_SHAPE = "not `PTHRnnnnn.mag.mod` or `PTHRnnnnn.SFn.mod`, then a tab and a name"


def name_line(line: str, number: int, name: str) -> Name:
    """One line of `names.tab`, with its line feed or without, read strictly.

    A family's line is `PTHRnnnnn.mag.mod`, a subfamily's `PTHRnnnnn.SFn.mod`, then a tab and the
    name, which may be empty.
    """
    if "\r" in line:
        raise LibraryFormatError(name, number, CARRIAGE_RETURN)
    text = line.removesuffix("\n")
    match = NAMES_LINE.fullmatch(text)
    if match is None:
        raise LibraryFormatError(name, number, f"{NAMES_SHAPE}: {text!r}")
    family, subfamily, value = match[1], match[2], match[3]
    hmm_id = family if subfamily is None else f"{family}:{subfamily}"
    return Name(hmm_id, value, number)


def read_names(lines: Iterable[str], name: str) -> dict[str, Name]:
    """Each line's HMM ID and name, by ID, in the file's order. A repeated ID is an error."""
    names: dict[str, Name] = {}
    for number, line in enumerate(lines, 1):
        entry = name_line(line, number, name)
        if (first := names.get(entry.hmm_id)) is not None:
            message = f"{entry.hmm_id} again, first on line {first.line}"
            raise LibraryFormatError(name, number, message)
        names[entry.hmm_id] = entry
    return names


# HMM files


@dataclass(frozen=True)
class Model:
    format: str
    """The model's first line, such as `HMMER3/f [3.1b2 | February 2015]`."""
    name: str
    length: int
    line: int
    """The 1-based line of its format line."""
    text: bytes
    """The model as it is in the file, from its format line to its `//` line."""


FORMAT = "HMMER3/"
END = "//"
NAME = re.compile(r"NAME  (\S+)")
LENG = re.compile(r"LENG  ([0-9]+)")


class Reading:
    """The model being read: its lines as read, and what its header gave."""

    def __init__(self, number: int, line: str, raw: str) -> None:
        self.line = number
        self.format = line
        self.raw = [raw]
        self.header = True
        self.name: str | None = None
        self.length: int | None = None


def read_models(lines: Iterable[str], name: str) -> Iterator[Model]:
    """The models in an HMMER3 text file, each from its `HMMER3/` format line to its `//` line.

    Each must have a `NAME` and a `LENG` in its header. Text outside a model, a model the file ends
    inside or one that starts before the last one's `//` is an error.
    """
    current: Reading | None = None
    last = 0
    for number, raw in enumerate(lines, 1):
        last = number
        if "\r" in raw:
            raise LibraryFormatError(name, number, CARRIAGE_RETURN)
        line = raw.removesuffix("\n")
        if line.startswith(FORMAT):
            if current is not None:
                raise LibraryFormatError(name, number, "a model starts before the last model's //")
            current = Reading(number, line, raw)
            continue
        if current is None:
            raise LibraryFormatError(name, number, f"text outside a model: {line[:40]!r}")
        current.raw.append(raw)
        if line == END:
            yield finished(current, name)
            current = None
        elif current.header:
            header(current, line, number, name)
    if current is not None:
        raise LibraryFormatError(name, last, "the file ends before the model's //")


def header(model: Reading, line: str, number: int, name: str) -> None:
    """Note a header line's NAME or LENG. The header ends at the `HMM` line before the matrix."""
    if line.startswith("HMM "):
        model.header = False
    elif line.startswith("NAME"):
        match = NAME.fullmatch(line)
        if match is None:
            raise LibraryFormatError(name, number, f"NAME isn't one word: {line!r}")
        if model.name is not None:
            raise LibraryFormatError(name, number, "a second NAME in the model")
        model.name = match[1]
    elif line.startswith("LENG"):
        match = LENG.fullmatch(line)
        if match is None:
            raise LibraryFormatError(name, number, f"LENG isn't a whole number: {line!r}")
        if model.length is not None:
            raise LibraryFormatError(name, number, "a second LENG in the model")
        model.length = int(match[1])


def finished(model: Reading, name: str) -> Model:
    if model.name is None:
        raise LibraryFormatError(name, model.line, "the model has no NAME")
    if model.length is None:
        raise LibraryFormatError(name, model.line, "the model has no LENG")
    text = "".join(model.raw).encode(ENCODING)
    return Model(model.format, model.name, model.length, model.line, text)


def read_model_file(lines: Iterable[str], name: str) -> Model:
    """A `books/` model file's one model. A second model, or none, is an error."""
    found: Model | None = None
    for model in read_models(lines, name):
        if found is not None:
            raise LibraryFormatError(name, model.line, "more than one model in a model file")
        found = model
    if found is None:
        raise LibraryFormatError(name, None, "no model in the file")
    return found


# Names, and the pressed files


def family_of(name: str) -> str:
    """The family a model name, an HMM ID or a names.tab line is for: its text before `.` or `:`."""
    return re.split(r"[.:\t]", name, maxsplit=1)[0]


def path_of(hmm_id: str) -> str:
    """The model file an HMM ID's model is in."""
    family, _, subfamily = hmm_id.partition(":")
    return f"books/{family}/hmmer.hmm" if not subfamily else f"books/{family}/{subfamily}/hmmer.hmm"


# The magic numbers that start pressed files, written in the machine's byte order: little-endian
# on amd64 and arm64 (src/impl_sse/io.c, src/impl_neon/io.c and src/p7_hmmfile.c in HMMER 3.4).
MAGIC: dict[Kind, dict[int, str]] = {
    Kind.H3F: {
        0xB3E6E6F3: "3/f", 0xB3E5E6F3: "3/e", 0xB3E4E6F3: "3/d",
        0xB3E3E6F3: "3/c", 0xB3E2E6F3: "3/b", 0xE8B3E6F3: "3/a",
    },
    Kind.H3P: {
        0xB3E6F0F3: "3/f", 0xB3E5F0F3: "3/e", 0xB3E4F0F3: "3/d",
        0xB3E3F0F3: "3/c", 0xB3E2F0F3: "3/b", 0xE8B3F0F3: "3/a",
    },
    Kind.H3M: {
        0xE8EDEDBA: "3/f", 0xE8EDEDB0: "3/e", 0xE8EDEDB9: "3/d",
        0xE8EDEDB8: "3/c", 0xE8EDEDB7: "3/b", 0xE8EDEDB6: "3/a",
    },
}  # fmt: skip
# Easel's SSI 3.0 index, written big-endian (easel/esl_ssi.c, esl_newssi_Write): the magic, flags,
# offset size, file count, primary and secondary key counts, then six sizes, then 3 offsets.
SSI_MAGIC = 0xD3D3C9B3
SSI_HEADER = struct.Struct(">IIIHQQIIIIII")


def pressed_format(kind: Kind, head: bytes) -> str:
    """The format a pressed file's first four bytes declare."""
    if len(head) < 4:
        return "unknown (shorter than 4 bytes)"
    little, big = int.from_bytes(head, "little"), int.from_bytes(head, "big")
    if kind is Kind.H3I:
        if big == SSI_MAGIC:
            return "SSI 3.0"
        return "SSI 3.0, byte-swapped" if little == SSI_MAGIC else f"unknown (0x{big:08x})"
    if little in MAGIC[kind]:
        return MAGIC[kind][little]
    if big in MAGIC[kind]:
        return f"{MAGIC[kind][big]}, big-endian"
    return f"unknown (0x{little:08x})"


def index_names(data: bytes) -> list[str]:
    """The primary keys of an SSI 3.0 index, in the order of their records in the file it
    indexes. Raises ValueError for anything else."""
    return [name for name, _ in index_records(data)]


def index_records(data: bytes) -> list[tuple[str, int]]:
    """Each primary key of an SSI 3.0 index, with its record's offset in the file it indexes, in
    the order of those offsets. For `binHmm.h3i`, each model's start in `binHmm.h3m`, whose
    records are contiguous. Raises ValueError for anything else."""
    if len(data) < SSI_HEADER.size:
        raise ValueError("shorter than an SSI header")
    magic, _, offsz, _, nprimary, _, _, plen, _, _, precsize, _ = SSI_HEADER.unpack_from(data)
    if magic != SSI_MAGIC:
        raise ValueError(f"not an SSI 3.0 index: its magic number is 0x{magic:08x}")
    if offsz not in (4, 8):
        raise ValueError(f"offsets of {offsz} bytes")
    offset = ">Q" if offsz == 8 else ">I"
    (poffset,) = struct.unpack_from(offset, data, SSI_HEADER.size + offsz)
    if precsize != plen + 2 + 2 * offsz + 8:
        raise ValueError(f"primary key records of {precsize} bytes, for keys of {plen}")
    if poffset + nprimary * precsize > len(data):
        raise ValueError(f"too short for its {nprimary:,} primary keys")
    keys: list[tuple[int, str]] = []
    for index in range(nprimary):
        record = poffset + index * precsize
        key = data[record : record + plen].split(b"\0", 1)[0].decode(ENCODING)
        (start,) = struct.unpack_from(offset, data, record + plen + 2)
        keys.append((start, key))
    return [(key, start) for start, key in sorted(keys)]
