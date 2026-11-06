"""The refmap data's manifest, `data.json`, and the organism list, `organisms.json`, both shipped
with the package; fetching the pinned release and checking a data folder against it.

The release is PANTHER 19's classification files on `data.pantherdb.org`, as one tarball, and its
`stats`. `data.json` pins both by URL, size and sha256, and lists every file as laid out in the
data folder, in `core/manifest.py`'s format.

- **build** writes `data.json` and `organisms.json` from a release's tarball and `stats`, reading
  the tarball once as a stream, without unpacking it. It checks that `stats` and the tarball agree,
  file by file and count by count, and that every organism's code can be a file name on every
  platform. It writes nothing if any check fails. The same inputs give the same bytes.
- **fetch** downloads the tarball and `stats`, or takes local copies, checks each against its pin,
  and saves each classification file under its organism's code. A member's name is never used as
  a path. It does nothing when the folder already matches, and writes nothing under `refmap/19/`
  if anything fails.
- **verify** checks a data folder against `data.json`.
"""

import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
import urllib.parse
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import IO, cast

from panther_engine.core.data import data_root
from panther_engine.core.download import download
from panther_engine.core.manifest import (
    CHUNK,
    Mismatches,
    checksums,
    read_manifest,
    sha256_file,
    verify,
)
from panther_engine.refmap.organisms import (
    CLASSIFICATION,
    CODE,
    FOLDER,
    ORGANISMS,
    STATS,
    VERSION,
    code_of,
    read_organisms,
)

MANIFEST = Path(__file__).with_name("data.json")
# The tarball's folder. The published folder, and the data folder's, are `panther_classification/`.
TARBALL_FOLDER = "panther_classifications"
WINDOWS_DEVICES = frozenset(
    {"CON", "PRN", "AUX", "NUL", *(f"COM{n}" for n in range(10)), *(f"LPT{n}" for n in range(10))}
)
# A line whose second tab field is exactly NOHIT, as `split /\t/` would give it.
NOHIT_LINE = re.compile(rb"^[^\t\n]*\tNOHIT(?=\t|$)", re.MULTILINE)
# How many problems an error names.
LISTED = 20


class RefmapDataError(Exception):
    """The refmap data can't be pinned, fetched or verified."""


@dataclass(frozen=True)
class Pin:
    url: str
    sha256: str
    size: int

    def to_json(self) -> dict[str, object]:
        return {"url": self.url, "sha256": self.sha256, "bytes": self.size}


@dataclass(frozen=True)
class StatsLine:
    """One organism in `stats`: its long name, its genes, and those with a PANTHER ID."""

    long_name: str
    genes: int
    mapped: int


class HashingReader:
    """A binary file that hashes and counts what is read from it."""

    def __init__(self, raw: IO[bytes]) -> None:
        self.raw = raw
        self.digest = hashlib.sha256()
        self.size = 0

    def read(self, size: int = -1) -> bytes:
        data = self.raw.read(size)
        self.digest.update(data)
        self.size += len(data)
        return data

    def drain(self) -> None:
        while self.read(CHUNK):
            pass


def joined(problems: list[str]) -> str:
    listed = "; ".join(problems[:LISTED])
    if len(problems) > LISTED:
        listed += f"; and {len(problems) - LISTED:,} more"
    return listed


def pin_of(manifest: Mapping[str, object], name: str) -> Pin:
    value = manifest.get(name)
    if not isinstance(value, dict):
        raise RefmapDataError(f"the manifest has no {name}")
    fields = cast(dict[str, object], value)
    url, sha256, size = fields.get("url"), fields.get("sha256"), fields.get("bytes")
    if not (isinstance(url, str) and isinstance(sha256, str) and isinstance(size, int)):
        raise RefmapDataError(f"the manifest's {name} needs a url, sha256 and bytes")
    return Pin(url, sha256, size)


def read_stats(path: Path) -> tuple[list[StatsLine], list[str]]:
    """`stats`'s organisms, in its order, and a problem for each line that can't be read."""
    entries: list[StatsLine] = []
    problems: list[str] = []
    text = path.read_bytes().decode("utf-8", errors="replace")
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    for number, line in enumerate(lines, 1):
        fields = line.split("\t")
        if len(fields) != 3 or not fields[0] or not all(f.isdigit() for f in fields[1:]):
            problems.append(f"{path.name} line {number} isn't a long name and two counts: {line!r}")
            continue
        entries.append(StatsLine(fields[0], int(fields[1]), int(fields[2])))
    return entries, problems


def code_problems(entries: list[StatsLine]) -> list[str]:
    """Each long name repeated, each code shared, and each code that can't be a file name."""
    problems: list[str] = []
    by_code: defaultdict[str, list[str]] = defaultdict(list)
    for entry in entries:
        by_code[code_of(entry.long_name)].append(entry.long_name)
    for code, names in sorted(by_code.items()):
        if len(names) > 1:
            problems.append(f"{len(names)} organisms have the code {code!r}: {', '.join(names)}")
        if not CODE.fullmatch(code):
            problems.append(f"{names[0]}'s code {code!r} isn't 1 to 5 upper-case letters or digits")
        elif code.upper() in WINDOWS_DEVICES:
            problems.append(f"{names[0]}'s code {code!r} is a Windows device name")
    return problems


def long_name_of(member: tarfile.TarInfo) -> str | None:
    """The long name a member is the classification file of, or None for the tarball's folder.

    Raises RefmapDataError for anything else: a link, another folder, or a file elsewhere.
    """
    if member.isdir() and member.name == TARBALL_FOLDER:
        return None
    path = PurePosixPath(member.name)
    if member.isfile() and len(path.parts) == 2 and path.parts[0] == TARBALL_FOLDER:
        return path.parts[1]
    raise RefmapDataError(f"unexpected member in the tarball: {member.name!r}")


@dataclass(frozen=True)
class Member:
    sha256: str
    lines: int
    nohit: int


def count_lines(content: bytes) -> int:
    """Lines as Perl's `<FH>` reads them: one per line feed, and a last line without one."""
    return content.count(b"\n") + (1 if content and not content.endswith(b"\n") else 0)


def read_members(tarball: Path) -> tuple[Pin, dict[str, Member], list[str]]:
    """The tarball's size and sha256 (with no URL), each classification file by long name, and a
    problem for each member that isn't one. Reads the tarball once, as a stream."""
    members: dict[str, Member] = {}
    problems: list[str] = []
    with tarball.open("rb") as raw:
        reader = HashingReader(raw)
        try:
            with tarfile.open(fileobj=cast(IO[bytes], reader), mode="r|gz") as tar:
                for member in tar:
                    try:
                        long_name = long_name_of(member)
                    except RefmapDataError as error:
                        problems.append(str(error))
                        continue
                    if long_name is None:
                        continue
                    stream = tar.extractfile(member)
                    if stream is None:
                        raise RefmapDataError(f"can't read {member.name!r} in {tarball}")
                    content = stream.read()
                    if long_name in members:
                        problems.append(f"the tarball holds {member.name!r} twice")
                    members[long_name] = Member(
                        hashlib.sha256(content).hexdigest(),
                        count_lines(content),
                        len(NOHIT_LINE.findall(content)),
                    )
            reader.drain()
        except (tarfile.TarError, EOFError, OSError) as error:
            raise RefmapDataError(f"can't read {tarball}: {error}") from error
    return Pin("", reader.digest.hexdigest(), reader.size), members, problems


def build(
    tarball: Path,
    stats: Path,
    *,
    tarball_url: str,
    stats_url: str,
    manifest: Path = MANIFEST,
    organisms: Path = ORGANISMS,
) -> dict[str, object]:
    """Write the manifest and the organism list for a release, and return the manifest.

    The release's name is the folder its tarball is in, such as `2024-06-20` for
    `.../archive/2024-06-20/panther_classifications.tar.gz`. Nothing is written if a check fails.
    """
    entries, problems = read_stats(stats)
    problems += code_problems(entries)
    tarball_pin, members, member_problems = read_members(tarball)
    problems += member_problems
    listed = {entry.long_name: entry for entry in entries}
    for entry in entries:
        found = members.get(entry.long_name)
        if found is None:
            problems.append(f"{entry.long_name} is in {stats.name}, but has no file")
        elif (found.lines, found.lines - found.nohit) != (entry.genes, entry.mapped):
            problems.append(
                f"{entry.long_name} has {found.lines:,} lines, {found.lines - found.nohit:,} of "
                f"them with a PANTHER ID, but {stats.name} says {entry.genes:,} and "
                f"{entry.mapped:,}"
            )
    for long_name in sorted(members.keys() - listed.keys()):
        problems.append(f"{long_name} has a file, but no line in {stats.name}")
    if problems:
        raise RefmapDataError(f"can't pin the release: {joined(problems)}")

    stats_sha256 = sha256_file(stats)
    files = {
        f"{FOLDER}/{CLASSIFICATION}/{code_of(name)}": member.sha256
        for name, member in members.items()
    }
    files[f"{FOLDER}/{STATS}"] = stats_sha256
    result: dict[str, object] = {
        "release": PurePosixPath(urllib.parse.urlsplit(tarball_url).path).parent.name,
        "version": VERSION,
        "tarball": Pin(tarball_url, tarball_pin.sha256, tarball_pin.size).to_json(),
        "stats": Pin(stats_url, stats_sha256, stats.stat().st_size).to_json(),
        "files": dict(sorted(files.items())),
    }
    listing = [
        {"code": code_of(name), "long_name": name}
        for name in sorted(entry.long_name for entry in entries)
    ]
    write_together({manifest: as_json(result), organisms: as_json(listing)})
    return result


def as_json(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_together(contents: Mapping[Path, bytes]) -> None:
    """Write each file beside itself first, then move them all into place."""
    written: list[tuple[Path, Path]] = []
    try:
        for path, content in contents.items():
            handle, partial = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
            with os.fdopen(handle, "wb") as out:
                out.write(content)
            written.append((Path(partial), path))
        for partial, path in written:
            os.replace(partial, path)
    finally:
        for partial, _ in written:
            partial.unlink(missing_ok=True)


# fetch and verify


def verify_folder(folder: Path | str | None = None, manifest: Path = MANIFEST) -> Mismatches:
    """Check the data folder (`PANTHER_DATA_DIR` by default) against the manifest."""
    return verify(data_root(folder), checksums(read_manifest(manifest)))


def fetch(
    folder: Path | str | None = None,
    *,
    manifest: Path = MANIFEST,
    organisms: Path = ORGANISMS,
    tarball: Path | None = None,
    stats: Path | None = None,
) -> bool:
    """Put the pinned release in the data folder. Returns False if it was already there.

    `tarball` and `stats` are local copies; without them, each is downloaded from its pinned URL.
    Only the files that are missing or differ are replaced.
    """
    pinned = read_manifest(manifest)
    files = checksums(pinned)
    tarball_pin, stats_pin = pin_of(pinned, "tarball"), pin_of(pinned, "stats")
    try:
        codes = {organism.long_name: organism.code for organism in read_organisms(organisms)}
    except ValueError as error:
        raise RefmapDataError(str(error)) from error
    root = data_root(folder)
    before = verify(root, files)
    if before.ok:
        return False
    created = not root.exists()
    root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=root, prefix=".refmap-fetch-") as work:
            downloads = Path(work)
            if tarball is None:
                tarball = download(tarball_pin.url, downloads / "panther_classifications.tar.gz")
            check_pin(tarball, tarball_pin)
            if stats is None:
                stats = download(stats_pin.url, downloads / "stats")
            check_pin(stats, stats_pin)
            unpacked = downloads / "unpacked"
            save_classification_files(tarball, codes, unpacked / FOLDER / CLASSIFICATION)
            shutil.copyfile(stats, unpacked / FOLDER / STATS)
            mismatches = verify(unpacked, files)
            if not mismatches.ok:
                raise RefmapDataError(
                    "the release doesn't match the manifest: "
                    + joined([*mismatches.missing, *mismatches.differing])
                )
            for name in [*before.missing, *before.differing]:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(unpacked / name, target)
    except BaseException:
        if created and not any(root.iterdir()):
            root.rmdir()
        raise
    return True


def check_pin(path: Path, pin: Pin) -> None:
    size = path.stat().st_size
    if size != pin.size:
        raise RefmapDataError(f"{path} has {size} bytes, not the manifest's {pin.size}")
    actual = sha256_file(path)
    if actual != pin.sha256:
        raise RefmapDataError(f"{path}'s sha256 is {actual}, not the manifest's {pin.sha256}")


def save_classification_files(tarball: Path, codes: Mapping[str, str], folder: Path) -> None:
    """Write each classification file in `tarball` to `folder/<code>`, reading the tarball as a
    stream. The path comes from the organism list, never from the member's name. Raises
    RefmapDataError for a member that isn't the file of an organism in the list."""
    folder.mkdir(parents=True)
    try:
        with tarfile.open(tarball, mode="r|gz") as tar:
            for member in tar:
                long_name = long_name_of(member)
                if long_name is None:
                    continue
                code = codes.get(long_name)
                if code is None:
                    raise RefmapDataError(
                        f"unexpected member in the tarball: {member.name!r}, an organism that "
                        "isn't in the list"
                    )
                stream = tar.extractfile(member)
                if stream is None:
                    raise RefmapDataError(f"can't read {member.name!r} in {tarball}")
                with (folder / code).open("wb") as out:
                    shutil.copyfileobj(stream, out, CHUNK)
    except (tarfile.TarError, EOFError, OSError) as error:
        raise RefmapDataError(f"can't read {tarball}: {error}") from error
