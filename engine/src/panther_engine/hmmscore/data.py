"""The hmmscore data's pin, `data.json`, shipped with the package, and the list of the model
files' checksums, `books.sha256`.

The library is PANTHER 19's HMM library on `data.pantherdb.org`: one tarball of about 18.5 GB.
`data.json` pins it by URL, size and sha256, with its member prefix and its number of model
files. Its `files`, in `core/manifest.py`'s format, give the sha256 of the README, each `globals/`
file and `books.sha256` (design.md, decision 4).

`books.sha256` has a line per model file, `<sha256>  books/PTHRnnnnn/[SFn/]hmmer.hmm`, as
`sha256sum` writes them, sorted by path as bytes. Its own sha256 is in `files`, so it pins every
model file through one digest, without a 15 MB manifest in the package. It's generated from the
tarball, never committed or edited.

- **manifest** writes `data.json` from the tarball, reading it once as a stream. It writes
  nothing, and names each problem, for a member the layout doesn't have, a member outside the
  prefix, or a model file the strict reader rejects. The same tarball gives the same bytes.
- **fetch** streams the tarball from its URL, or reads a local copy, and keeps only what scoring
  reads: the README, `globals/` and the model files, never `cluster.pir` or `tree.tree`. It
  writes them into a temporary folder in the data folder, hashing each as it's written, and
  checks the tarball's size and sha256 and every file before moving any under `hmmscore/19/`. It
  does nothing when the folder already matches (decision 5).
- **verify** checks a data folder against the pin, every model file included.
"""

import hashlib
import json
import os
import tarfile
import tempfile
import uuid
import zlib
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, cast

from panther_engine.core.archive import ArchiveError, open_stream
from panther_engine.core.data import data_root
from panther_engine.core.download import open_https
from panther_engine.core.manifest import (
    CHUNK,
    SHA256,
    HashingReader,
    Mismatches,
    checksums,
    read_manifest,
    sha256_stream,
    verify,
)
from panther_engine.hmmscore.library import (
    MODELS,
    PREFIX,
    LibraryFormatError,
    Member,
    library_member,
    lines_of,
    prefix_folder,
    read_model_file,
)

SERVICE = "hmmscore"
VERSION = "19"
FOLDER = f"{SERVICE}/{VERSION}"
BOOKS_LIST = "books.sha256"
MANIFEST = Path(__file__).with_name("data.json")
# How many problems an error names.
LISTED = 20


class HmmscoreDataError(Exception):
    """The hmmscore data can't be pinned, fetched or verified."""


@dataclass(frozen=True)
class Pin:
    url: str
    sha256: str
    size: int

    def to_json(self) -> dict[str, object]:
        return {"url": self.url, "bytes": self.size, "sha256": self.sha256}


def book_count(manifest: Mapping[str, object]) -> int:
    """The number of model files the pin lists in `books.sha256`."""
    books = manifest.get("books")
    if isinstance(books, dict):
        count = cast(dict[str, object], books).get("files")
        if isinstance(count, int) and not isinstance(count, bool):
            return count
    raise HmmscoreDataError("the manifest's books needs a files count")


def joined(problems: list[str]) -> str:
    listed = "; ".join(problems[:LISTED])
    if len(problems) > LISTED:
        listed += f"; and {len(problems) - LISTED:,} more"
    return listed


def books_list(hashes: Mapping[str, str]) -> bytes:
    """`books.sha256` for the model files' hashes, by path below the prefix."""
    paths = sorted(hashes, key=lambda path: path.encode("utf-8"))
    return b"".join(f"{hashes[path]}  {path}\n".encode() for path in paths)


def kept_member(member: tarfile.TarInfo, prefix: str) -> Member | None:
    """The member's place in the layout, if fetching keeps it. None for a folder, a `cluster.pir`
    or a `tree.tree`. Raises HmmscoreDataError for a member outside the prefix, or one the layout
    doesn't have, such as a link or a path with `..`."""
    if not member.name.startswith(prefix):
        if member.isdir() and prefix_folder(member.name, prefix):
            return None
        raise HmmscoreDataError(f"a member outside the prefix: {member.name!r}")
    relative = member.name.removeprefix(prefix)
    found = None
    if member.isdir():
        found = library_member(relative, folder=True)
    elif member.isfile():
        found = library_member(relative)
    if found is None:
        raise HmmscoreDataError(f"a member the layout doesn't have: {relative!r}")
    return found if found.kept else None


@dataclass
class Hashed:
    """A tarball's sha256 and size, and the sha256 of each member fetching keeps."""

    sha256: str = ""
    size: int = 0
    globals: dict[str, str] = field(default_factory=dict[str, str])
    """The README's and each `globals/` file's, by path below the prefix."""
    books: dict[str, str] = field(default_factory=dict[str, str])
    """Each model file's, by path below the prefix."""
    problems: list[str] = field(default_factory=list[str])


def hash_library(tarball: Path, prefix: str) -> Hashed:
    """Read the tarball once, as a stream, hashing every member fetching keeps. Each member the
    layout doesn't allow, and each model file the strict reader rejects, is a problem."""
    hashed = Hashed()
    with tarball.open("rb") as raw:
        reader = HashingReader(raw)
        try:
            with open_stream(reader) as tar:
                for member in tar:
                    try:
                        found = kept_member(member, prefix)
                    except HmmscoreDataError as error:
                        hashed.problems.append(str(error))
                        continue
                    if found is None:
                        continue
                    if found.path in hashed.globals or found.path in hashed.books:
                        hashed.problems.append(f"{found.path} appears twice")
                        continue
                    stream = tar.extractfile(member)
                    if stream is None:
                        raise ArchiveError(f"can't read {member.name}")
                    if found.kind not in MODELS:
                        hashed.globals[found.path] = sha256_stream(stream)
                        continue
                    content = stream.read()
                    try:
                        read_model_file(lines_of(content), found.path)
                    except LibraryFormatError as error:
                        hashed.problems.append(f"a model file the strict reader rejects: {error}")
                        continue
                    hashed.books[found.path] = hashlib.sha256(content).hexdigest()
            reader.drain()
        except (tarfile.TarError, EOFError, zlib.error, OSError, ArchiveError) as error:
            raise HmmscoreDataError(f"can't read {tarball}: {error}") from error
    hashed.sha256, hashed.size = reader.digest.hexdigest(), reader.size
    return hashed


def manifest(
    tarball: Path, *, url: str, prefix: str = PREFIX, out: Path = MANIFEST
) -> dict[str, object]:
    """Write the pin for the library's tarball to `out`, and return it. Nothing is written if the
    tarball has a problem."""
    hashed = hash_library(tarball, prefix)
    if hashed.problems:
        raise HmmscoreDataError(f"can't pin the library: {joined(hashed.problems)}")
    files = {f"{FOLDER}/{path}": digest for path, digest in hashed.globals.items()}
    files[f"{FOLDER}/{BOOKS_LIST}"] = hashlib.sha256(books_list(hashed.books)).hexdigest()
    result: dict[str, object] = {
        "version": VERSION,
        "tarball": Pin(url, hashed.sha256, hashed.size).to_json(),
        "prefix": prefix,
        "books": {"files": len(hashed.books)},
        "files": dict(sorted(files.items())),
    }
    write_file(out, (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return result


def write_file(path: Path, content: bytes) -> None:
    """Write the file beside itself first, then move it into place. It's created as any new file
    is, so the umask sets its mode: it's committed, and read in the image by another user."""
    partial = path.with_name(f".{path.name}.{uuid.uuid4().hex}")
    try:
        with partial.open("xb") as out:
            out.write(content)
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


# fetch and verify


def pin_of(manifest: Mapping[str, object]) -> Pin:
    value = manifest.get("tarball")
    if isinstance(value, dict):
        fields = cast(dict[str, object], value)
        url, sha256, size = fields.get("url"), fields.get("sha256"), fields.get("bytes")
        if isinstance(url, str) and isinstance(sha256, str) and isinstance(size, int):
            return Pin(url, sha256, size)
    raise HmmscoreDataError("the manifest's tarball needs a url, sha256 and bytes")


def prefix_of(manifest: Mapping[str, object]) -> str:
    prefix = manifest.get("prefix")
    if not isinstance(prefix, str) or not prefix.endswith("/"):
        raise HmmscoreDataError("the manifest needs a prefix ending in /")
    return prefix


def read_books_list(path: Path) -> dict[str, str]:
    """`books.sha256`'s model files, by path below `hmmscore/19/`, with their sha256."""
    hashes: dict[str, str] = {}
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise HmmscoreDataError(f"{path} isn't UTF-8: {error}") from error
    for number, line in enumerate(text.splitlines(), 1):
        digest, separator, model = line.partition("  ")
        found = library_member(model)
        if (
            not separator
            or not SHA256.fullmatch(digest)
            or found is None
            or found.kind not in MODELS
        ):
            raise HmmscoreDataError(
                f"{path}, line {number}: not a sha256 and a model file: {line!r}"
            )
        hashes[found.path] = digest
    return hashes


def verify_folder(folder: Path | str | None = None, manifest: Path = MANIFEST) -> Mismatches:
    """Check the data folder (`PANTHER_DATA_DIR` by default) against the pin: the README,
    each `globals/` file and `books.sha256`, then, if `books.sha256` matched, every model file
    it lists."""
    root = data_root(folder)
    files = checksums(read_manifest(manifest))
    found = verify(root, files)
    listing = f"{FOLDER}/{BOOKS_LIST}"
    if listing not in files or listing in found.missing or listing in found.differing:
        return found
    books = verify(root / FOLDER, read_books_list(root / listing))
    return Mismatches(
        tuple(sorted([*found.missing, *(f"{FOLDER}/{path}" for path in books.missing)])),
        tuple(sorted([*found.differing, *(f"{FOLDER}/{path}" for path in books.differing)])),
    )


@contextmanager
def opened(tarball: Path | None, url: str) -> Generator[IO[bytes]]:
    """The local copy of the tarball if there is one, otherwise the response from its URL."""
    if tarball is not None:
        with tarball.open("rb") as raw:
            yield raw
    else:
        with open_https(url) as response:
            yield response


def extract(raw: IO[bytes], prefix: str, folder: Path) -> Hashed:
    """Write each member fetching keeps under `folder`, at its path below the prefix as the
    layout rebuilds it, hashing it as it's written. Stops at the first member the layout doesn't
    allow: a member's name is never used as a path."""
    hashed = Hashed()
    reader = HashingReader(raw)
    try:
        with open_stream(reader) as tar:
            for member in tar:
                found = kept_member(member, prefix)
                if found is None:
                    continue
                if found.path in hashed.globals or found.path in hashed.books:
                    raise HmmscoreDataError(f"{found.path} appears twice")
                stream = tar.extractfile(member)
                if stream is None:
                    raise ArchiveError(f"can't read {member.name}")
                target = folder / found.path
                target.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                with target.open("xb") as out:
                    while chunk := stream.read(CHUNK):
                        digest.update(chunk)
                        out.write(chunk)
                hashes = hashed.books if found.kind in MODELS else hashed.globals
                hashes[found.path] = digest.hexdigest()
        reader.drain()
    except (tarfile.TarError, EOFError, zlib.error, OSError, ArchiveError) as error:
        raise HmmscoreDataError(
            f"can't read the tarball, or write what it holds: {error}"
        ) from error
    hashed.sha256, hashed.size = reader.digest.hexdigest(), reader.size
    return hashed


def fetch(
    folder: Path | str | None = None, *, manifest: Path = MANIFEST, tarball: Path | None = None
) -> bool:
    """Put the pinned library in the data folder. Returns False if it was already there.

    `tarball` is a local copy; without one, the tarball is streamed from its URL and never saved.
    Every kept file is checked before any is moved under `hmmscore/19/`.
    """
    pinned = read_manifest(manifest)
    files = checksums(pinned)
    pin, prefix, count = pin_of(pinned), prefix_of(pinned), book_count(pinned)
    root = data_root(folder)
    if verify_folder(root, manifest).ok:
        return False
    created = not root.exists()
    root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=root, prefix=".hmmscore-fetch-") as work:
            staged = Path(work)
            with opened(tarball, pin.url) as raw:
                hashed = extract(raw, prefix, staged / FOLDER)
            source = tarball if tarball is not None else pin.url
            if (hashed.sha256, hashed.size) != (pin.sha256, pin.size):
                raise HmmscoreDataError(
                    f"{source} has the sha256 {hashed.sha256} and {hashed.size:,} bytes, not the "
                    f"pinned {pin.sha256} and {pin.size:,} bytes"
                )
            (staged / FOLDER / BOOKS_LIST).write_bytes(books_list(hashed.books))
            mismatches = verify(staged, files)
            if not mismatches.ok:
                raise HmmscoreDataError(
                    "the tarball doesn't match the pin: "
                    + joined([*mismatches.missing, *mismatches.differing])
                )
            if len(hashed.books) != count:
                raise HmmscoreDataError(
                    f"the tarball has {len(hashed.books):,} model files, not the pinned {count:,}"
                )
            for path in [*hashed.globals, *hashed.books, BOOKS_LIST]:
                target = root / FOLDER / path
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged / FOLDER / path, target)
    except BaseException:
        if created and not any(root.iterdir()):
            root.rmdir()
        raise
    return True
