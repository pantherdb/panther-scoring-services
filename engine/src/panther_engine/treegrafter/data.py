"""The treegrafter data: the pinned TreeGrafter library and PAINT annotation releases, `data.json`,
shipped with the package, and the list of the library's checksums, `library.sha256`.

The layout, under `treegrafter/19/` in the data folder (adopt-treegrafter, spec: Data layout):

    famhmm/binHmm                        every family's HMM, which hmmsearch reads
    Tree_MSF/PTHRnnnnn.AN.fasta          a family's alignment, a row per leaf
    Tree_MSF/PTHRnnnnn.bifurcate.newick  its tree made bifurcating, which EPA-ng places on
    Tree_MSF/PTHRnnnnn.newick            its tree, whose nodes the annotations are keyed by
    library.sha256                       the sha256 of each file above, as sha256sum writes them
    annotations/<date>/PTHRnnnnn.json    a release prepared by EBI's `prepare`
    annotations/<date>/prepared.sha256   the sha256 of each of the release's prepared files
    annotations/active                   the date of the release grafting reads

The library is `PANTHER19.0_data_trees_hmms_only.tar.gz` on `data.pantherdb.org`: 3.07 GB, 8.2 GB
unpacked. `data.json` pins it by URL, size and sha256, with its member prefix and its number of
families, and the sha256 of `library.sha256`, which pins every kept file through one digest. The
fetch skips what grafting never reads: the pressed `binHmm` files, the `.tree` files, the PAINT
README and the empty `tmp/` (design.md, decision 9).

- **manifest** writes the library's pin from its tarball, reading it once as a stream. It writes
  nothing, and names each problem, for a member the layout doesn't have, a member outside the
  prefix, or a family without one of its three tree files. The same tarball gives the same bytes.
- **fetch** streams the tarball from its URL, or reads a local copy, writes the kept files into a
  temporary folder in the data folder, hashing each as it's written, and checks the tarball's size
  and sha256 and every file before moving any under `treegrafter/19/`. It does nothing when the
  folder already matches.
- **verify** checks a data folder against the pin, every kept file included.
"""

import gzip
import hashlib
import json
import os
import re
import tarfile
import tempfile
import uuid
import zlib
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import IO, cast

from panther_engine.core.archive import ArchiveError, open_stream
from panther_engine.core.data import data_root
from panther_engine.core.download import open_https
from panther_engine.core.manifest import (
    CHUNK,
    SHA256,
    HashingReader,
    ManifestError,
    Mismatches,
    checksums,
    read_manifest,
    verify,
)

SERVICE = "treegrafter"
VERSION = "19"
FOLDER = f"{SERVICE}/{VERSION}"
MANIFEST = Path(__file__).with_name("data.json")
# PANTHER 19's member prefix: every member of the library's tarball is below it.
PREFIX = "PANTHER19.0_data/"
LIBRARY_LIST = "library.sha256"
BINHMM = "famhmm/binHmm"
TREE_MSF = "Tree_MSF"
TREE_FILES = (".AN.fasta", ".bifurcate.newick", ".newick")
# How many problems an error names.
LISTED = 20


class TreegrafterDataError(Exception):
    """The treegrafter data can't be pinned, fetched, prepared or verified."""


def joined(problems: list[str]) -> str:
    listed = "; ".join(problems[:LISTED])
    if len(problems) > LISTED:
        listed += f"; and {len(problems) - LISTED:,} more"
    return listed


# The layout


class Kind(StrEnum):
    BINHMM = "famhmm/binHmm"
    PRESSED = "a pressed binHmm file"
    TREE_FILE = "a tree file"
    DOT_TREE = "a .tree file"
    README = "PAINT_Annotations_README"
    TMP = "tmp/"
    FOLDER = "a folder"


KEPT = frozenset((Kind.BINHMM, Kind.TREE_FILE))
FAMILY = r"PTHR[0-9]{5}"
TREE_FILE = re.compile(rf"{TREE_MSF}/({FAMILY})(\.AN\.fasta|\.bifurcate\.newick|\.newick|\.tree)")
PRESSED_FILE = re.compile(r"famhmm/binHmm\.h3[fimp]")
FOLDERS = ("", TREE_MSF, "famhmm", "tmp")


@dataclass(frozen=True)
class Member:
    kind: Kind
    path: str
    """The path below the prefix, rebuilt from what matched."""
    family: str | None = None

    @property
    def kept(self) -> bool:
        return self.kind in KEPT


def library_member(relative: str, *, folder: bool = False) -> Member | None:
    """A member's place in the layout, from its path below the prefix, or None if the layout
    doesn't have it. The path is matched exactly, so `..`, absolute paths and other names are
    unexpected, never a path to write."""
    if folder:
        name = relative.rstrip("/")
        return Member(Kind.FOLDER, name) if name in FOLDERS else None
    if relative == BINHMM:
        return Member(Kind.BINHMM, BINHMM)
    if relative == Kind.README:
        return Member(Kind.README, relative)
    if PRESSED_FILE.fullmatch(relative):
        return Member(Kind.PRESSED, relative)
    match = TREE_FILE.fullmatch(relative)
    if match is None:
        return None
    family, suffix = match.groups()
    kind = Kind.DOT_TREE if suffix == ".tree" else Kind.TREE_FILE
    return Member(kind, f"{TREE_MSF}/{family}{suffix}", family)


def prefix_folder(name: str, prefix: str) -> bool:
    """Whether a folder member is one of the folders the prefix is in."""
    return prefix.startswith(name.rstrip("/") + "/")


def kept_member(member: tarfile.TarInfo, prefix: str) -> Member | None:
    """The member's place in the layout, if fetching keeps it. None for a folder or a file
    fetching skips. Raises TreegrafterDataError for a member outside the prefix, or one the layout
    doesn't have, such as a link or a path with `..`."""
    if not member.name.startswith(prefix):
        if member.isdir() and (prefix_folder(member.name, prefix) or member.name == prefix[:-1]):
            return None
        raise TreegrafterDataError(f"a member outside the prefix: {member.name!r}")
    relative = member.name.removeprefix(prefix)
    found = None
    if member.isdir():
        found = library_member(relative, folder=True)
    elif member.isfile():
        found = library_member(relative)
    if found is None:
        raise TreegrafterDataError(f"a member the layout doesn't have: {relative!r}")
    return found if found.kept else None


def family_of(path: str) -> str | None:
    match = TREE_FILE.fullmatch(path)
    return match.group(1) if match else None


def library_problems(paths: list[str]) -> list[str]:
    """What the kept files lack: `binHmm`, or one of a family's three tree files."""
    present = set(paths)
    problems = [] if BINHMM in present else [f"no {BINHMM}"]
    families = sorted({family for path in paths if (family := family_of(path)) is not None})
    for family in families:
        for suffix in TREE_FILES:
            if f"{TREE_MSF}/{family}{suffix}" not in present:
                problems.append(f"{family} lacks {TREE_MSF}/{family}{suffix}")
    return problems


def library_list(hashes: Mapping[str, str]) -> bytes:
    """`library.sha256` for the kept files' hashes, by path below the prefix, sorted by path."""
    paths = sorted(hashes, key=lambda path: path.encode("utf-8"))
    return b"".join(f"{hashes[path]}  {path}\n".encode() for path in paths)


def families_in(hashes: Mapping[str, str]) -> int:
    return len({family for path in hashes if (family := family_of(path)) is not None})


@dataclass
class Hashed:
    """A tarball's sha256 and size, and the sha256 of each member fetching keeps."""

    sha256: str = ""
    size: int = 0
    files: dict[str, str] = field(default_factory=dict[str, str])
    """Each kept file's, by path below the prefix."""
    problems: list[str] = field(default_factory=list[str])


def hash_library(tarball: Path, prefix: str) -> Hashed:
    """Read the tarball once, as a stream, hashing every member fetching keeps. Each member the
    layout doesn't allow, and each missing tree file, is a problem."""
    hashed = Hashed()
    with tarball.open("rb") as raw:
        reader = HashingReader(raw)
        try:
            with open_stream(reader) as tar:
                for member in tar:
                    try:
                        found = kept_member(member, prefix)
                    except TreegrafterDataError as error:
                        hashed.problems.append(str(error))
                        continue
                    if found is None:
                        continue
                    if found.path in hashed.files:
                        hashed.problems.append(f"{found.path} appears twice")
                        continue
                    stream = tar.extractfile(member)
                    if stream is None:
                        raise ArchiveError(f"can't read {member.name}")
                    digest = hashlib.sha256()
                    while chunk := stream.read(CHUNK):
                        digest.update(chunk)
                    hashed.files[found.path] = digest.hexdigest()
            reader.drain()
        except (tarfile.TarError, EOFError, zlib.error, OSError, ArchiveError) as error:
            raise TreegrafterDataError(f"can't read {tarball}: {error}") from error
    hashed.problems.extend(library_problems(list(hashed.files)))
    hashed.sha256, hashed.size = reader.digest.hexdigest(), reader.size
    return hashed


# The pin


@dataclass(frozen=True)
class Pin:
    url: str
    sha256: str
    size: int

    def to_json(self) -> dict[str, object]:
        return {"url": self.url, "bytes": self.size, "sha256": self.sha256}


def read_pin(path: Path) -> dict[str, object]:
    """The pin at `path`, with its `files` member checked."""
    try:
        return read_manifest(path)
    except ManifestError as error:
        raise TreegrafterDataError(str(error)) from error


def write_pin(out: Path, pinned: Mapping[str, object]) -> None:
    write_file(out, (json.dumps(pinned, indent=2, sort_keys=True) + "\n").encode("utf-8"))


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


def releases_of(pinned: Mapping[str, object]) -> dict[str, object]:
    value = pinned.get("releases", {})
    if not isinstance(value, dict):
        raise TreegrafterDataError("the manifest's releases needs to be an object")
    return {str(key): item for key, item in cast(dict[object, object], value).items()}


def manifest(
    tarball: Path, *, url: str, prefix: str = PREFIX, out: Path = MANIFEST
) -> dict[str, object]:
    """Write the library's pin for its tarball to `out`, keeping the releases `out` already pins,
    and return it. Nothing is written if the tarball has a problem."""
    hashed = hash_library(tarball, prefix)
    if hashed.problems:
        raise TreegrafterDataError(f"can't pin the library: {joined(hashed.problems)}")
    releases = releases_of(read_pin(out)) if out.is_file() else {}
    result: dict[str, object] = {
        "version": VERSION,
        "tarball": Pin(url, hashed.sha256, hashed.size).to_json(),
        "prefix": prefix,
        "families": families_in(hashed.files),
        "files": {
            f"{FOLDER}/{LIBRARY_LIST}": hashlib.sha256(library_list(hashed.files)).hexdigest()
        },
        "releases": releases,
    }
    write_pin(out, result)
    return result


def pin_of(pinned: Mapping[str, object]) -> Pin:
    value = pinned.get("tarball")
    if isinstance(value, dict):
        fields = cast(dict[str, object], value)
        url, sha256, size = fields.get("url"), fields.get("sha256"), fields.get("bytes")
        if isinstance(url, str) and isinstance(sha256, str) and isinstance(size, int):
            return Pin(url, sha256, size)
    raise TreegrafterDataError("the manifest's tarball needs a url, sha256 and bytes")


def prefix_of(pinned: Mapping[str, object]) -> str:
    prefix = pinned.get("prefix")
    if not isinstance(prefix, str) or not prefix.endswith("/"):
        raise TreegrafterDataError("the manifest needs a prefix ending in /")
    return prefix


def family_count(pinned: Mapping[str, object]) -> int:
    count = pinned.get("families")
    if isinstance(count, int) and not isinstance(count, bool):
        return count
    raise TreegrafterDataError("the manifest needs a families count")


# fetch and verify the library


def read_library_list(path: Path) -> dict[str, str]:
    """`library.sha256`'s files, by path below `treegrafter/19/`, with their sha256."""
    hashes: dict[str, str] = {}
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise TreegrafterDataError(f"{path} isn't UTF-8: {error}") from error
    for number, line in enumerate(text.splitlines(), 1):
        digest, separator, kept = line.partition("  ")
        found = library_member(kept)
        if not separator or not SHA256.fullmatch(digest) or found is None or not found.kept:
            raise TreegrafterDataError(
                f"{path}, line {number}: not a sha256 and a library file: {line!r}"
            )
        hashes[found.path] = digest
    return hashes


def verify_library(folder: Path | str | None = None, manifest: Path = MANIFEST) -> Mismatches:
    """Check the data folder's library (`PANTHER_DATA_DIR` by default) against the pin:
    `library.sha256`, then, if it matched, every file it lists."""
    root = data_root(folder)
    files = checksums(read_pin(manifest))
    found = verify(root, files)
    listing = f"{FOLDER}/{LIBRARY_LIST}"
    if listing not in files or listing in found.missing or listing in found.differing:
        return found
    kept = verify(root / FOLDER, read_library_list(root / listing))
    return Mismatches(
        tuple(sorted([*found.missing, *(f"{FOLDER}/{path}" for path in kept.missing)])),
        tuple(sorted([*found.differing, *(f"{FOLDER}/{path}" for path in kept.differing)])),
    )


@contextmanager
def opened(local: Path | None, url: str) -> Generator[IO[bytes]]:
    """The local copy if there is one, otherwise the response from its URL."""
    if local is not None:
        with local.open("rb") as raw:
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
                if found.path in hashed.files:
                    raise TreegrafterDataError(f"{found.path} appears twice")
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
                hashed.files[found.path] = digest.hexdigest()
        reader.drain()
    except (tarfile.TarError, EOFError, zlib.error, OSError, ArchiveError) as error:
        raise TreegrafterDataError(
            f"can't read the tarball, or write what it holds: {error}"
        ) from error
    hashed.sha256, hashed.size = reader.digest.hexdigest(), reader.size
    return hashed


def fetch_library(
    folder: Path | str | None = None, *, manifest: Path = MANIFEST, tarball: Path | None = None
) -> bool:
    """Put the pinned library in the data folder. Returns False if it was already there.

    `tarball` is a local copy; without one, the tarball is streamed from its URL and never saved.
    Every kept file is checked before any is moved under `treegrafter/19/`.
    """
    pinned = read_pin(manifest)
    files = checksums(pinned)
    pin, prefix, count = pin_of(pinned), prefix_of(pinned), family_count(pinned)
    root = data_root(folder)
    if verify_library(root, manifest).ok:
        return False
    created = not root.exists()
    root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=root, prefix=".treegrafter-fetch-") as work:
            staged = Path(work)
            with opened(tarball, pin.url) as raw:
                hashed = extract(raw, prefix, staged / FOLDER)
            source = tarball if tarball is not None else pin.url
            if (hashed.sha256, hashed.size) != (pin.sha256, pin.size):
                raise TreegrafterDataError(
                    f"{source} has the sha256 {hashed.sha256} and {hashed.size:,} bytes, not the "
                    f"pinned {pin.sha256} and {pin.size:,} bytes"
                )
            problems = library_problems(list(hashed.files))
            if problems:
                raise TreegrafterDataError(f"the tarball isn't a library: {joined(problems)}")
            (staged / FOLDER / LIBRARY_LIST).write_bytes(library_list(hashed.files))
            mismatches = verify(staged, files)
            if not mismatches.ok:
                raise TreegrafterDataError(
                    "the tarball doesn't match the pin: "
                    + joined([*mismatches.missing, *mismatches.differing])
                )
            if families_in(hashed.files) != count:
                raise TreegrafterDataError(
                    f"the tarball has {families_in(hashed.files):,} families, not the pinned "
                    f"{count:,}"
                )
            for path in [*hashed.files, LIBRARY_LIST]:
                target = root / FOLDER / path
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged / FOLDER / path, target)
    except BaseException:
        if created and not any(root.iterdir()):
            root.rmdir()
        raise
    return True


# The annotation releases

# Each release's file and README, by date, and the release `paint/current/` holds. Not `pango/`:
# the library's README lists it first, but it holds a third, older file (design.md, decision 9).
PAINT = "https://data.pantherdb.org/ftp/downloads/paint"
RELEASE_FILE = "PAINT_TreeGrafter_Annotations_TOTAL.txt.gz"
RELEASE_URL = f"{PAINT}/19.0/{{date}}/{RELEASE_FILE}"
RELEASE_README_URL = f"{PAINT}/19.0/{{date}}/README"
CURRENT_URL = f"{PAINT}/current/{RELEASE_FILE}"
CURRENT_README_URL = f"{PAINT}/current/README"
CURRENT = "current"
ANNOTATIONS = "annotations"
ACTIVE = "active"
PREPARED_LIST = "prepared.sha256"
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
# A release README's second line (design.md, decision 9).
GO_RELEASE = re.compile(r"GO release date: ([0-9]{4}-[0-9]{2}-[0-9]{2})")
# Every node of a family's `.newick` tree is labelled ANn, and the annotations are keyed by them.
NODE = re.compile(r"AN[0-9]+")


@dataclass(frozen=True)
class Release:
    """A pinned annotation release: its file's URL, sha256 and size, the GO release its README
    states, and the sha256 of its prepared files' list."""

    date: str
    url: str
    sha256: str
    size: int
    go_release: str
    prepared: str

    def to_json(self) -> dict[str, object]:
        return {
            "url": self.url,
            "bytes": self.size,
            "sha256": self.sha256,
            "go_release": self.go_release,
            "prepared": self.prepared,
        }


def release_pins(pinned: Mapping[str, object]) -> dict[str, Release]:
    """The manifest's releases, by date."""
    result: dict[str, Release] = {}
    for date, value in releases_of(pinned).items():
        fields = cast(dict[str, object], value) if isinstance(value, dict) else {}
        url, sha256, size = fields.get("url"), fields.get("sha256"), fields.get("bytes")
        go_release, prepared = fields.get("go_release"), fields.get("prepared")
        if not (
            DATE.fullmatch(date)
            and isinstance(url, str)
            and isinstance(sha256, str)
            and isinstance(size, int)
            and isinstance(go_release, str)
            and isinstance(prepared, str)
        ):
            raise TreegrafterDataError(
                f"the manifest's release {date!r} needs a url, bytes, sha256, go_release and "
                "prepared"
            )
        result[date] = Release(date, url, sha256, size, go_release, prepared)
    return result


def check_date(date: str) -> None:
    if not DATE.fullmatch(date):
        raise TreegrafterDataError(f"not a release date, YYYY-MM-DD: {date!r}")


def go_release_of(readme: bytes) -> str:
    """The GO release a release's README states on its second line."""
    lines = readme.decode("utf-8", errors="replace").splitlines()
    match = GO_RELEASE.fullmatch(lines[1].strip()) if len(lines) > 1 else None
    if match is None:
        raise TreegrafterDataError(
            "the release's README doesn't state its GO release on its second line"
        )
    return match.group(1)


def hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def download_to(url: str, target: Path) -> Path:
    with opened(None, url) as response, target.open("wb") as out:
        while chunk := response.read(CHUNK):
            out.write(chunk)
    return target


def library_folder(root: Path) -> Path:
    return root / FOLDER


def release_folder(root: Path, date: str) -> Path:
    return root / FOLDER / ANNOTATIONS / date


def prepared_list(folder: Path) -> bytes:
    """`prepared.sha256` for a prepared release: each family's file and its sha256, by name."""
    names = sorted(path.name for path in folder.glob("*.json"))
    return b"".join(f"{hash_file(folder / name)[0]}  {name}\n".encode() for name in names)


def missing_nodes(library: Path, prepared: Path) -> tuple[int, list[str]]:
    """How many nodes the library's trees have, and those the prepared release has no entry for,
    as `PTHRnnnnn:ANn`."""
    count = 0
    missing: list[str] = []
    for newick in sorted((library / TREE_MSF).glob("*.newick")):
        if newick.name.endswith(".bifurcate.newick"):
            continue
        family = newick.name.removesuffix(".newick")
        nodes = NODE.findall(newick.read_text(encoding="ascii"))
        count += len(nodes)
        annotated = prepared / f"{family}.json"
        entries: dict[str, object] = (
            cast(dict[str, object], json.loads(annotated.read_text(encoding="utf-8")))
            if annotated.is_file()
            else {}
        )
        missing.extend(f"{family}:{node}" for node in nodes if node not in entries)
    return count, missing


@dataclass(frozen=True)
class Prepared:
    folder: Path
    listing: bytes
    nodes: int


def prepare_release(annotation_file: Path, library: Path, work: Path) -> Prepared:
    """Run EBI's `prepare` on a release's gzipped file into `work/prepared`, check that every node
    of every tree in `library` has an entry, and write `prepared.sha256` there."""
    from panther_engine.treegrafter import ebi

    text = work / "annotations.txt"
    try:
        with gzip.open(annotation_file, "rb") as source, text.open("wb") as out:
            while chunk := source.read(CHUNK):
                out.write(chunk)
    except (OSError, EOFError, zlib.error) as error:
        raise TreegrafterDataError(f"can't read {annotation_file}: {error}") from error
    prepared = work / "prepared"
    try:
        ebi.prepare(text, prepared)
    except ebi.TreegrafterError as error:
        raise TreegrafterDataError(f"can't prepare the release: {error}") from error
    finally:
        text.unlink(missing_ok=True)
    count, missing = missing_nodes(library, prepared)
    if missing:
        raise TreegrafterDataError(
            f"the release has no entry for {len(missing):,} of the library's {count:,} tree "
            f"nodes: {joined(missing)}"
        )
    listing = prepared_list(prepared)
    (prepared / PREPARED_LIST).write_bytes(listing)
    return Prepared(prepared, listing, count)


def pin_release(
    date: str,
    annotation_file: Path,
    *,
    readme: Path | None = None,
    url: str | None = None,
    folder: Path | str | None = None,
    manifest: Path = MANIFEST,
) -> Release:
    """Pin a release in `manifest`: its file's size and sha256, the GO release its README states,
    and the sha256 of its prepared files' list. It's prepared in a temporary folder against the
    data folder's library, which must match the pin, and refused if a tree node has no entry.
    `readme` is a local copy of the release's README; without one, it's downloaded."""
    check_date(date)
    pinned = read_pin(manifest)
    root = data_root(folder)
    if not verify_library(root, manifest).ok:
        raise TreegrafterDataError(
            f"the data folder {root} doesn't hold the pinned library: fetch it first"
        )
    sha256, size = hash_file(annotation_file)
    with tempfile.TemporaryDirectory(dir=root, prefix=".treegrafter-pin-") as work:
        readme_path = readme or download_to(
            RELEASE_README_URL.format(date=date), Path(work) / "README"
        )
        go_release = go_release_of(readme_path.read_bytes())
        prepared = prepare_release(annotation_file, library_folder(root), Path(work))
    release = Release(
        date,
        url or RELEASE_URL.format(date=date),
        sha256,
        size,
        go_release,
        hashlib.sha256(prepared.listing).hexdigest(),
    )
    releases = releases_of(pinned)
    releases[date] = release.to_json()
    write_pin(manifest, {**pinned, "releases": dict(sorted(releases.items()))})
    return release


def read_prepared_list(path: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        digest, separator, name = line.partition("  ")
        if (
            not separator
            or not SHA256.fullmatch(digest)
            or not re.fullmatch(rf"{FAMILY}\.json", name)
        ):
            raise TreegrafterDataError(f"{path}, line {number}: not a sha256 and a family's file")
        hashes[name] = digest
    return hashes


def verify_release(root: Path, release: Release) -> Mismatches:
    """Check a prepared release against its pin: `prepared.sha256`, then, if it matched, every
    file it lists. Paths are relative to the data folder."""
    folder = release_folder(root, release.date)
    base = f"{FOLDER}/{ANNOTATIONS}/{release.date}"
    listing = folder / PREPARED_LIST
    if not listing.is_file():
        return Mismatches((f"{base}/{PREPARED_LIST}",), ())
    if hash_file(listing)[0] != release.prepared:
        return Mismatches((), (f"{base}/{PREPARED_LIST}",))
    found = verify(folder, read_prepared_list(listing))
    return Mismatches(
        tuple(f"{base}/{path}" for path in found.missing),
        tuple(f"{base}/{path}" for path in found.differing),
    )


def active_date(root: Path) -> str | None:
    """The active release's date, or None if no release is active."""
    path = root / FOLDER / ANNOTATIONS / ACTIVE
    if not path.is_file():
        return None
    date = path.read_text(encoding="ascii").strip()
    check_date(date)
    return date


def activate(root: Path, date: str) -> None:
    """Make the release at `date` the one grafting reads: a new `active` file beside the old one,
    then moved over it, so a graft reads either."""
    check_date(date)
    write_file(root / FOLDER / ANNOTATIONS / ACTIVE, f"{date}\n".encode("ascii"))


@dataclass(frozen=True)
class Fetched:
    """What fetching a release did: the release's date, whether `current` was resolved to it,
    whether its file was downloaded, and whether it was prepared or already was."""

    date: str
    resolved_current: bool
    downloaded: bool
    prepared: bool


def resolve_current(releases: Mapping[str, Release], file: Path, readme: Path | None) -> str:
    """The pinned release whose file has `file`'s sha256. Raises TreegrafterDataError, naming
    the sha256 and the GO release `readme` states, when no pinned release has it."""
    sha256, _ = hash_file(file)
    for release in releases.values():
        if release.sha256 == sha256:
            return release.date
    go_release = "unknown, with a local file"
    if readme is not None:
        try:
            go_release = go_release_of(readme.read_bytes())
        except TreegrafterDataError as error:
            go_release = str(error)
    raise TreegrafterDataError(
        f"the current release isn't pinned: its file has the sha256 {sha256}, and GO release "
        f"{go_release}. Pin it with `panther-engine treegrafter data manifest --release DATE FILE`"
    )


def fetch_release(
    folder: Path | str | None = None,
    *,
    manifest: Path = MANIFEST,
    annotations: str = CURRENT,
    annotation_file: Path | None = None,
) -> Fetched:
    """Make a pinned release the active one, fetching and preparing it if it isn't already.

    `annotations` is a pinned date, or `current`, the release `paint/current/` holds, resolved to
    its pinned date by its file's sha256. `annotation_file` is a local copy of the release's file.
    A release that's already prepared and verified is made active without downloading it. The
    library must be in the data folder: the node check reads its trees.
    """
    releases = release_pins(read_pin(manifest))
    root = data_root(folder)
    if annotations != CURRENT and annotations not in releases:
        check_date(annotations)
        raise TreegrafterDataError(
            f"release {annotations} isn't pinned (pinned: {', '.join(sorted(releases))})"
        )
    library = library_folder(root)
    if not (library / BINHMM).is_file() or not (library / TREE_MSF).is_dir():
        raise TreegrafterDataError(f"no library in {library}: fetch it first")
    with tempfile.TemporaryDirectory(dir=root, prefix=".treegrafter-fetch-") as work:
        staged = Path(work)
        source = annotation_file
        downloaded = False
        resolved = annotations == CURRENT
        if resolved:
            readme = None
            if source is None:
                source = download_to(CURRENT_URL, staged / RELEASE_FILE)
                readme = download_to(CURRENT_README_URL, staged / "README")
                downloaded = True
            date = resolve_current(releases, source, readme)
        else:
            date = annotations
        release = releases[date]
        if verify_release(root, release).ok:
            activate(root, date)
            return Fetched(date, resolved, downloaded, prepared=False)
        if source is None:
            source = download_to(release.url, staged / RELEASE_FILE)
            downloaded = True
        sha256, size = hash_file(source)
        if (sha256, size) != (release.sha256, release.size):
            raise TreegrafterDataError(
                f"{annotation_file or release.url} has the sha256 {sha256} and {size:,} bytes, "
                f"not release {date}'s pinned {release.sha256} and {release.size:,} bytes"
            )
        prepared = prepare_release(source, library, staged)
        listed = hashlib.sha256(prepared.listing).hexdigest()
        if listed != release.prepared:
            raise TreegrafterDataError(
                f"release {date}'s prepared files don't match the pin: their list has the sha256 "
                f"{listed}, not the pinned {release.prepared}"
            )
        target = release_folder(root, date)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            os.replace(target, staged / "replaced")
        os.replace(prepared.folder, target)
        activate(root, date)
    return Fetched(date, resolved, downloaded, prepared=True)


def verify_folder(folder: Path | str | None = None, manifest: Path = MANIFEST) -> Mismatches:
    """Check the data folder against the pin: the library, every file included, and the active
    release's prepared files. A missing `annotations/active` is listed as missing."""
    root = data_root(folder)
    found = verify_library(root, manifest)
    date = active_date(root)
    if date is None:
        return Mismatches(
            tuple(sorted([*found.missing, f"{FOLDER}/{ANNOTATIONS}/{ACTIVE}"])), found.differing
        )
    releases = release_pins(read_pin(manifest))
    if date not in releases:
        raise TreegrafterDataError(f"the active release, {date}, isn't pinned")
    prepared = verify_release(root, releases[date])
    return Mismatches(
        tuple(sorted([*found.missing, *prepared.missing])),
        tuple(sorted([*found.differing, *prepared.differing])),
    )


# The fixture

FIXTURE_ANNOTATIONS = "PAINT_TreeGrafter_Annotations_TOTAL.txt"
FIXTURE_JSON = "fixture.json"
FIXTURE_README = "README.md"
MODEL_NAME = re.compile(rb"NAME  (PTHR[0-9]{5})\.")


def family_models(binhmm: Path, families: frozenset[str]) -> dict[str, bytes]:
    """The models of `families` in `binHmm`, by family, read a line at a time: each model runs
    from its `HMMER3` line to its `//` line, and its NAME is the family's, as
    `PTHR18976.orig.30.pir`."""
    models: dict[str, bytes] = {}
    lines: list[bytes] = []
    family: str | None = None
    with binhmm.open("rb") as stream:
        for line in stream:
            if line.startswith(b"HMMER3"):
                lines, family = [], None
            lines.append(line)
            if family is None and (match := MODEL_NAME.match(line)):
                family = match.group(1).decode("ascii")
            if line.startswith(b"//") and family in families:
                models[family] = b"".join(lines)
    return models


def family_lines(annotation_file: Path, families: frozenset[str]) -> bytes:
    """The release's lines for `families`, in the file's order."""
    kept: list[bytes] = []
    try:
        with gzip.open(annotation_file, "rb") as stream:
            for line in stream:
                if line.split(b":", 1)[0].decode("ascii", errors="replace") in families:
                    kept.append(line)
    except (OSError, EOFError, zlib.error) as error:
        raise TreegrafterDataError(f"can't read {annotation_file}: {error}") from error
    return b"".join(kept)


def fixture_readme(
    families: list[str], release: Release, pin: Pin, files: Mapping[str, bytes]
) -> bytes:
    """The fixture's README: what it is, how to rebuild it, and each file's source and sha256."""
    rows = [
        f"| `{path}` | {source} | {len(files[path]):,} | "
        f"`{hashlib.sha256(files[path]).hexdigest()}` |"
        for path, source in sorted(fixture_sources(files, release).items())
    ]
    lines = [
        "# The treegrafter Fixture",
        "",
        f"PANTHER 19's TreeGrafter library cut to {len(families)} whole families, "
        f"{', '.join(families)}, with their lines of PAINT annotation release {release.date}. "
        "The engine's tests prepare it with EBI's `prepare` into a temporary data folder, and "
        "graft against it. With `hmmsearch -Z` fixed, a protein whose best family is one of "
        "these gets the full library's numbers.",
        "",
        "Generated by `panther-engine treegrafter data fixture`, never edited by hand: "
        "rebuilding it from the pinned library and release gives the same bytes. From "
        "`engine/`, with both fetched:",
        "",
        "```sh",
        f"uv run panther-engine treegrafter data fixture --data-dir ../.data --release "
        f"{release.date} \\",
        "  --annotation-file PAINT_TreeGrafter_Annotations_TOTAL.txt.gz \\",
        f"  --out tests/fixtures/treegrafter {' '.join(families)}",
        "```",
        "",
        f"- **The library:** `{pin.url}`, sha256 `{pin.sha256}`.",
        f"- **The release:** `{release.url}`, sha256 `{release.sha256}`, GO release "
        f"{release.go_release}.",
        "",
        "| File | Source | Bytes | sha256 |",
        "| ---- | ------ | ----: | ------ |",
        *rows,
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def fixture_sources(files: Mapping[str, bytes], release: Release) -> dict[str, str]:
    sources: dict[str, str] = {}
    for path in files:
        if path == BINHMM:
            sources[path] = "The families' models from the library's `famhmm/binHmm`, by family"
        elif path == FIXTURE_ANNOTATIONS:
            sources[path] = f"The families' lines of release {release.date}'s file, in its order"
        elif path == FIXTURE_JSON:
            sources[path] = "The release's date and the families, for the tests"
        else:
            sources[path] = f"The library's `{path}`, as it is"
    return sources


def build_fixture(
    families: list[str],
    *,
    release: str,
    annotation_file: Path,
    out: Path,
    folder: Path | str | None = None,
    manifest: Path = MANIFEST,
) -> dict[str, bytes]:
    """Cut the fixture from the data folder's library, which must match the pin, and a pinned
    release's file, for `families`, into `out`, which must not exist. Returns its files by path.
    The same library, release and families, in any order, give the same bytes."""
    chosen = sorted(set(families))
    bad = [family for family in chosen if not re.fullmatch(FAMILY, family)]
    if bad or not chosen:
        raise TreegrafterDataError(f"not PANTHER families: {', '.join(bad) or 'none given'}")
    pinned = read_pin(manifest)
    releases = release_pins(pinned)
    if release not in releases:
        raise TreegrafterDataError(f"release {release} isn't pinned")
    pinned_release = releases[release]
    if hash_file(annotation_file) != (pinned_release.sha256, pinned_release.size):
        raise TreegrafterDataError(f"{annotation_file} isn't release {release}'s pinned file")
    root = data_root(folder)
    if not verify_library(root, manifest).ok:
        raise TreegrafterDataError(f"the data folder {root} doesn't hold the pinned library")
    if out.exists():
        raise TreegrafterDataError(f"{out} already exists")
    library = library_folder(root)
    models = family_models(library / BINHMM, frozenset(chosen))
    lines = family_lines(annotation_file, frozenset(chosen))
    missing = [family for family in chosen if family not in models]
    missing += [
        f"{TREE_MSF}/{family}{suffix}"
        for family in chosen
        for suffix in TREE_FILES
        if not (library / TREE_MSF / f"{family}{suffix}").is_file()
    ]
    if missing:
        raise TreegrafterDataError(f"the library lacks: {', '.join(missing)}")
    files: dict[str, bytes] = {BINHMM: b"".join(models[family] for family in chosen)}
    for family in chosen:
        for suffix in TREE_FILES:
            path = f"{TREE_MSF}/{family}{suffix}"
            files[path] = (library / path).read_bytes()
    files[FIXTURE_ANNOTATIONS] = lines
    files[FIXTURE_JSON] = (
        json.dumps({"families": chosen, "release": release}, indent=2) + "\n"
    ).encode("utf-8")
    files[FIXTURE_README] = fixture_readme(chosen, pinned_release, pin_of(pinned), files)
    for path, content in files.items():
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return files


def install_fixture(fixture: Path, folder: Path | str) -> str:
    """Lay the fixture out in the data folder `folder` as a fetch would, with its release prepared
    by EBI's `prepare` and active, and return the release's date. Nothing is checked against the
    pin, which is the full library's: a test's data folder only."""
    root = Path(folder)
    library = library_folder(root)
    for path in [
        BINHMM,
        *(str(each.relative_to(fixture)) for each in (fixture / TREE_MSF).iterdir()),
    ]:
        target = library / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((fixture / path).read_bytes())
    described = cast(dict[str, object], json.loads((fixture / FIXTURE_JSON).read_text("utf-8")))
    date = str(described["release"])
    check_date(date)
    with tempfile.TemporaryDirectory(dir=root, prefix=".treegrafter-fixture-") as work:
        annotations = Path(work) / f"{RELEASE_FILE}"
        with gzip.GzipFile(annotations, "wb", mtime=0) as out:
            out.write((fixture / FIXTURE_ANNOTATIONS).read_bytes())
        prepared = prepare_release(annotations, library, Path(work))
        target = release_folder(root, date)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            os.replace(target, Path(work) / "replaced")
        os.replace(prepared.folder, target)
    activate(root, date)
    return date
