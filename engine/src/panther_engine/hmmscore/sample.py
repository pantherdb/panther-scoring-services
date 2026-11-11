"""The hmmscore data sample: chosen families of the PANTHER 19 HMM library, their `names.tab`
lines, their `binHmm` models pressed by the pinned HMMER, and the library's README, as one
tarball attached to a GitHub release of this repository.

`sample.json`, shipped with the package, pins the release: its tag, the tarball's URL, sha256 and
size, the library tarball it was built from, the HMMER that pressed it, the families, and each
file's sha256. The files unpack under the data folder at `hmmscore/19/`, laid out as the full
library is, so code never needs to know which it has.

- **build** makes the tarball from the pinned library tarball and a list of families, byte for
  byte the same each time on one machine (design.md, decisions 6 and 7). It refuses a tarball
  whose sha256 isn't the pin's and an `hmmpress` that isn't the pinned HMMER, and then writes
  nothing. `hmmpress` runs on the relative name `binHmm` in the build's temporary folder, so the
  index records no temporary path.
- **fetch** downloads the tarball, or takes a local copy, checks it, unpacks it safely and checks
  every file. It does nothing when the folder already matches. A failure leaves the folder as it
  was.
- **verify** checks a data folder against the manifest.

The sample's pressed `binHmm` holds the models the library's `binHmm` holds for the chosen
families, in its order. With a flat `binHmm` in the tarball, its text models, byte for byte, which
the sample holds too. Otherwise, as for PANTHER 19, their records cut out of `binHmm.h3m` at the
pressed index's offsets, which `hmmpress` reads as a binary model file and gives back in the
sample's `binHmm.h3m` byte for byte; the build checks that it does. Converting them to text first
would round some probabilities (design.md, decision 6).
"""

import json
import os
import re
import shutil
import struct
import subprocess
import tarfile
import tempfile
import zlib
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, cast

from panther_engine.core.archive import (
    ArchiveError,
    member_lines,
    open_stream,
    unpack,
    write_tarball,
)
from panther_engine.core.data import data_root
from panther_engine.core.download import download
from panther_engine.core.manifest import (
    CHUNK,
    HashingReader,
    Mismatches,
    checksums,
    read_manifest,
    sha256_file,
    verify,
)
from panther_engine.core.process import run_tool
from panther_engine.core.tools import TOOLS, VERSION_TIMEOUT
from panther_engine.hmmscore import data
from panther_engine.hmmscore.library import (
    ENCODING,
    MODELS,
    Kind,
    LibraryFormatError,
    family_of,
    index_records,
    lines_of,
    read_models,
)

SERVICE = data.SERVICE
FOLDER = data.FOLDER
MANIFEST = Path(__file__).with_name("sample.json")
RELEASES = "https://github.com/pantherdb/panther-scoring-services/releases/download"
# The HMMER the root Dockerfile pins. Any HMMER program's -h names its version as hmmscan's does.
HMMER_VERSION = "3.4"
HMMER = next(tool for tool in TOOLS if tool.name == "hmmscan")
PRESSED = ("binHmm.h3f", "binHmm.h3i", "binHmm.h3m", "binHmm.h3p")
PRESS_TIMEOUT = 3600.0
FAMILY_NAME = re.compile(r"PTHR[0-9]{5}")


class SampleError(Exception):
    """The sample can't be built, fetched or verified."""


@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    sha256: str
    size: int


def asset_of(manifest: dict[str, object]) -> Asset:
    asset = manifest.get("asset")
    if not isinstance(asset, dict):
        raise SampleError("the manifest has no asset")
    fields = cast(dict[str, object], asset)
    name, url, sha256, size = (fields.get(key) for key in ("name", "url", "sha256", "bytes"))
    if not (
        isinstance(name, str)
        and isinstance(url, str)
        and isinstance(sha256, str)
        and isinstance(size, int)
    ):
        raise SampleError("the manifest's asset needs a name, url, sha256 and bytes")
    return Asset(name, url, sha256, size)


def hmmer_version(program: Path) -> str | None:
    """The version an HMMER program's `-h` names, or None."""
    try:
        result = run_tool(program, ["-h"], timeout=VERSION_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SampleError(f"can't run {program}: {error}") from error
    return HMMER.parse_version(result.stdout)


# build


@dataclass
class Picked:
    """What the build takes from the library tarball, read once as a stream."""

    sha256: str = ""
    size: int = 0
    readme: bytes | None = None
    names: list[str] = field(default_factory=list[str])
    """The chosen families' names.tab lines, in its order."""
    models: dict[str, bytes] = field(default_factory=dict[str, bytes])
    """The chosen families' model files, by path below the prefix."""
    flat: list[bytes] | None = None
    """The chosen families' models in the flat binHmm, in its order, if the tarball has it."""
    cuts: list[tuple[int, int | None, str]] | None = None
    """Where the chosen families' records are in binHmm.h3m, by the pressed index: each one's
    start, its end (None for the last), and its model's name, in binHmm's order."""
    records: list[bytes] | None = None
    """Those records, cut from binHmm.h3m."""


def pinned_tool(name: str) -> Path:
    """An HMMER program on PATH, at the pinned version."""
    found = shutil.which(name)
    if found is None:
        raise SampleError(f"{name} isn't on PATH: build the sample in the engine image")
    program = Path(found).absolute()
    version = hmmer_version(program)
    if version != HMMER_VERSION:
        raise SampleError(f"{name} is HMMER {version}, not the pinned {HMMER_VERSION}: {program}")
    return program


def build(
    tarball: Path,
    *,
    families: Iterable[str],
    tag: str,
    out: Path,
    manifest: Path = MANIFEST,
    pin: Path = data.MANIFEST,
) -> dict[str, object]:
    """Build the sample tarball at `out` and its manifest at `manifest`. Returns the manifest.

    Nothing is written unless the tarball is the pinned one, `hmmpress` is the pinned HMMER, and
    the press gives back the records cut from `binHmm.h3m`.
    """
    wanted = sorted(set(families))
    for family in wanted:
        if not FAMILY_NAME.fullmatch(family):
            raise SampleError(f"not a family: {family!r}")
    pinned = read_manifest(pin)
    tarball_pin, prefix = data.pin_of(pinned), data.prefix_of(pinned)
    hmmpress = pinned_tool("hmmpress")

    picked = pick(tarball, prefix, set(wanted))
    if (picked.sha256, picked.size) != (tarball_pin.sha256, tarball_pin.size):
        raise SampleError(
            f"{tarball} has the sha256 {picked.sha256} and {picked.size:,} bytes, not the pinned "
            f"{tarball_pin.sha256} and {tarball_pin.size:,} bytes"
        )
    missing = [family for family in wanted if f"books/{family}/hmmer.hmm" not in picked.models]
    if missing:
        raise SampleError(f"not in {tarball}: {', '.join(missing)}")
    if picked.readme is None:
        raise SampleError(f"{tarball} has no README")
    if picked.flat is None and picked.records is None:
        raise SampleError(f"{tarball} has neither a flat binHmm nor binHmm.h3i and binHmm.h3m")

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent, prefix=".hmmscore-sample-") as work:
        root = Path(work) / FOLDER
        contents = {
            "README": picked.readme,
            "globals/names.tab": "".join(picked.names).encode(ENCODING),
            **picked.models,
        }
        for path, content in contents.items():
            (root / path).parent.mkdir(parents=True, exist_ok=True)
            (root / path).write_bytes(content)
        # The flat binHmm's text models, or else the records cut from binHmm.h3m: HMMER reads
        # them as a binary model file, so the press keeps the library's models as they are.
        binhmm = root / "globals" / "binHmm"
        binhmm.write_bytes(
            b"".join(picked.flat if picked.flat is not None else picked.records or [])
        )
        press(hmmpress, root / "globals")
        if (
            picked.flat is None
            and (root / "globals/binHmm.h3m").read_bytes() != binhmm.read_bytes()
        ):
            raise SampleError(
                f"{hmmpress} didn't give back the records cut from the library's binHmm.h3m, byte "
                "for byte, in the sample's binHmm.h3m"
            )
        flat = ["globals/binHmm"] if picked.flat is not None else []
        paths = [*contents, *flat, *(f"globals/{name}" for name in PRESSED)]
        files = {f"{FOLDER}/{path}": root / path for path in paths}
        digests = {name: sha256_file(source) for name, source in sorted(files.items())}
        partial = Path(work) / out.name
        write_tarball(partial, files)
        os.replace(partial, out)

    result: dict[str, object] = {
        "tag": tag,
        "asset": {
            "name": out.name,
            "url": f"{RELEASES}/{tag}/{out.name}",
            "sha256": sha256_file(out),
            "bytes": out.stat().st_size,
        },
        "source": {"name": tarball.name, "sha256": tarball_pin.sha256},
        "hmmer": HMMER_VERSION,
        "families": wanted,
        "files": digests,
    }
    manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def pick(tarball: Path, prefix: str, wanted: set[str]) -> Picked:
    """Read the library tarball once, as a stream, taking what the sample needs from it."""
    picked = Picked()
    with tarball.open("rb") as raw:
        reader = HashingReader(raw)
        try:
            with open_stream(reader) as tar:
                for member in tar:
                    kept = data.kept_member(member, prefix)
                    if kept is None or kept.kind in (Kind.H3F, Kind.H3P):
                        continue
                    if kept.kind is Kind.H3M:
                        if picked.cuts is None:
                            raise SampleError("binHmm.h3m comes before binHmm.h3i in the tarball")
                        stream = tar.extractfile(member)
                        if stream is None:
                            raise ArchiveError(f"can't read {member.name}")
                        picked.records = cut(stream, picked.cuts)
                        continue
                    if kept.kind is Kind.BINHMM:
                        picked.flat = flat_models(member_lines(tar, member), kept.path, wanted)
                        continue
                    if kept.kind in MODELS and kept.family not in wanted:
                        continue
                    stream = tar.extractfile(member)
                    if stream is None:
                        raise ArchiveError(f"can't read {member.name}")
                    if kept.kind is Kind.README:
                        picked.readme = stream.read()
                    elif kept.kind is Kind.NAMES:
                        lines = lines_of(stream.read())
                        picked.names = [line for line in lines if family_of(line) in wanted]
                    elif kept.kind is Kind.H3I:
                        picked.cuts = cuts_for(index_records(stream.read()), wanted)
                    else:
                        picked.models[kept.path] = stream.read()
            reader.drain()
        except data.HmmscoreDataError as error:
            raise SampleError(str(error)) from error
        except (ValueError, struct.error, LibraryFormatError) as error:
            raise SampleError(f"can't read {tarball}'s binHmm: {error}") from error
        except (tarfile.TarError, EOFError, zlib.error, OSError, ArchiveError) as error:
            raise SampleError(f"can't read {tarball}: {error}") from error
    picked.sha256, picked.size = reader.digest.hexdigest(), reader.size
    return picked


def flat_models(lines: Iterator[bytes], path: str, wanted: set[str]) -> list[bytes]:
    """The chosen families' models in the flat binHmm, byte for byte, in its order."""
    decoded = (line.decode(ENCODING) for line in lines)
    return [model.text for model in read_models(decoded, path) if family_of(model.name) in wanted]


def cuts_for(entries: list[tuple[str, int]], wanted: set[str]) -> list[tuple[int, int | None, str]]:
    """Where the chosen families' records are in binHmm.h3m: each runs from its start to the next
    model's, as the records are contiguous, and the last to the file's end."""
    ends = [start for _, start in entries[1:]]
    return [
        (start, end, name)
        for (name, start), end in zip(entries, [*ends, None], strict=True)
        if family_of(name) in wanted
    ]


def cut(stream: IO[bytes], cuts: list[tuple[int, int | None, str]]) -> list[bytes]:
    """The records at `cuts`, read from binHmm.h3m as it streams past."""
    records: list[bytes] = []
    position = 0
    for start, end, name in cuts:
        while position < start:
            skipped = stream.read(min(CHUNK, start - position))
            if not skipped:
                raise SampleError(f"binHmm.h3m ends before {name}'s record")
            position += len(skipped)
        record = stream.read(-1 if end is None else end - start)
        if end is not None and len(record) != end - start:
            raise SampleError(f"binHmm.h3m ends inside {name}'s record")
        position += len(record)
        records.append(record)
    return records


def press(hmmpress: Path, folder: Path) -> None:
    """Press `folder/binHmm`, run on its relative name in `folder`."""
    try:
        result = run_tool(hmmpress, ["binHmm"], timeout=PRESS_TIMEOUT, cwd=folder)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SampleError(f"can't run {hmmpress}: {error}") from error
    if result.returncode != 0:
        raise SampleError(f"hmmpress exited with {result.returncode}: {result.stderr.strip()}")
    missing = [name for name in PRESSED if not (folder / name).is_file()]
    if missing:
        raise SampleError(f"hmmpress didn't write {', '.join(missing)}")


# fetch and verify


def verify_folder(folder: Path | str | None = None, manifest: Path = MANIFEST) -> Mismatches:
    """Check the data folder (`PANTHER_DATA_DIR` by default) against the manifest."""
    return verify(data_root(folder), checksums(read_manifest(manifest)))


def fetch(
    folder: Path | str | None = None,
    *,
    manifest: Path = MANIFEST,
    source: Path | None = None,
) -> bool:
    """Put the sample in the data folder. Returns False if it was already there.

    `source` is a local copy of the tarball; without one, it's downloaded from the manifest's URL.
    """
    pinned = read_manifest(manifest)
    files = checksums(pinned)
    asset = asset_of(pinned)
    root = data_root(folder)
    if verify(root, files).ok:
        return False
    created = not root.exists()
    root.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=root, prefix=".hmmscore-sample-") as work:
            tarball = source if source is not None else download(asset.url, Path(work) / asset.name)
            actual = sha256_file(tarball)
            if actual != asset.sha256:
                raise SampleError(
                    f"{tarball}'s sha256 is {actual}, not the manifest's {asset.sha256}"
                )
            unpacked = Path(work) / "unpacked"
            unpacked.mkdir()
            try:
                unpack(tarball, unpacked, SERVICE)
            except ArchiveError as error:
                raise SampleError(str(error)) from error
            mismatches = verify(unpacked, files)
            if not mismatches.ok:
                raise SampleError(
                    "the tarball doesn't match the manifest: "
                    + ", ".join([*mismatches.missing, *mismatches.differing])
                )
            for name in files:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(unpacked / name, target)
    except BaseException:
        if created and not any(root.iterdir()):
            root.rmdir()
        raise
    return True
