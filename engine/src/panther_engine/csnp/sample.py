"""The cSNP data sample: chosen families of the PAML_RST library, the PANTHER9 BLAST database, the
species tree and the PSEP copyright statement, as one tarball attached to a GitHub release of this
repository.

`sample.json`, shipped with the package, pins the release: its tag, the tarball's URL and sha256,
the source archives' checksums and each file's sha256. The files unpack under the data folder at
`csnp/9/`, laid out as the full data is (`csnp/9/PAML_RST/PTHR10366.paml`,
`csnp/9/blast/blast.psq` and so on).

- **build** makes the tarball from `PAML_RST.tar.gz` and `PANTHER9.blast.tar.gz`, byte for byte the
  same each time, and writes the manifest. It refuses an archive whose sha256 isn't the pinned
  one. The BLAST archive's `blast.fasta` stays out: `blastp` doesn't read it.
- **fetch** downloads the tarball, or takes a local copy, checks it, unpacks it safely and checks
  every file. It does nothing when the folder already matches. A failure leaves the folder as it
  was.
- **verify** checks a data folder against the manifest.

A different zlib can compress differently, so the tarball's sha256 only matters to `fetch`. The
per-file checksums are the lasting contract.
"""

import gzip
import json
import os
import shutil
import tarfile
import tempfile
import urllib.parse
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import IO, cast

from panther_engine.core.data import data_root
from panther_engine.core.manifest import (
    CHUNK,
    Mismatches,
    checksums,
    read_manifest,
    sha256_file,
    verify,
)
from panther_engine.csnp.survey import FAMILY_FILE, FAMILY_NAME, HashingReader, open_stream

SERVICE = "csnp"
VERSION = "9"
FOLDER = f"{SERVICE}/{VERSION}"
LIBRARY = "PAML_RST"
SPECIES = "species_pthr8_time.nhx"
BLAST = "blast"
# The database files in PANTHER9.blast.tar.gz, at the same paths under csnp/9/.
BLAST_FILES = ("blast/blast.phr", "blast/blast.pin", "blast/blast.psq")
COPYRIGHT = "PSEP-COPYRIGHT.txt"
MANIFEST = Path(__file__).with_name("sample.json")
RELEASES = "https://github.com/pantherdb/panther-scoring-services/releases/download"
# Legacy behaviour spec §7.1
PINNED_ARCHIVE = "6791f43325afdae3a1872c7655d103f9cdd98d5dbf6695a1187bb30985a869c5"
PINNED_SPECIES = "23b035c293337966bd766628dd721c0a264230a49e4763188c607e301623d1e9"
PINNED_BLAST = "2cf4428c97b99c4bce3705a80dc7f55c17779e54a0bcae9ddb7d75a67b40dcc9"
DOWNLOAD_TIMEOUT = 60.0


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


# build


def build(
    archive: Path,
    *,
    species: Path,
    readme: Path,
    families: Iterable[str],
    blast: Path,
    tag: str,
    out: Path,
    manifest: Path,
    archive_sha256: str = PINNED_ARCHIVE,
    species_sha256: str = PINNED_SPECIES,
    blast_sha256: str = PINNED_BLAST,
) -> dict[str, object]:
    """Build the sample tarball at `out` and its manifest at `manifest`. Returns the manifest.

    Nothing is written unless the two archives' and the species tree's checksums match.
    """
    wanted = sorted(set(families))
    for family in wanted:
        if not FAMILY_NAME.fullmatch(family):
            raise SampleError(f"not a family name: {family!r}")
    actual = sha256_file(species)
    if actual != species_sha256:
        raise SampleError(f"{species}'s sha256 is {actual}, not the pinned {species_sha256}")
    statement = copyright_statement(readme)

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent, prefix=".csnp-sample-") as work:
        database = Path(work) / BLAST
        database.mkdir()
        digest = extract_blast(blast, database)
        if digest != blast_sha256:
            raise SampleError(f"{blast}'s sha256 is {digest}, not the pinned {blast_sha256}")
        library = Path(work) / "library"
        library.mkdir()
        digest = extract_families(archive, set(wanted), library)
        if digest != archive_sha256:
            raise SampleError(f"{archive}'s sha256 is {digest}, not the pinned {archive_sha256}")
        found = {
            match[1] for path in library.iterdir() if (match := FAMILY_FILE.fullmatch(path.name))
        }
        missing = [family for family in wanted if family not in found]
        if missing:
            raise SampleError(f"not in {archive}: {', '.join(missing)}")
        (Path(work) / COPYRIGHT).write_bytes(statement)

        files = {f"{FOLDER}/{LIBRARY}/{path.name}": path for path in library.iterdir()}
        files.update({f"{FOLDER}/{name}": Path(work) / name for name in BLAST_FILES})
        files[f"{FOLDER}/{SPECIES}"] = species
        files[f"{FOLDER}/{COPYRIGHT}"] = Path(work) / COPYRIGHT
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
        "source": {"name": archive.name, "sha256": archive_sha256},
        "blast": {"name": blast.name, "sha256": blast_sha256},
        "species": {"name": SPECIES, "sha256": species_sha256},
        "families": wanted,
        "files": digests,
    }
    manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def copyright_statement(readme: Path) -> bytes:
    """The PSEP 1.01 README's opening statement: the lines before its first `####` line."""
    lines = readme.read_text(encoding="utf-8").splitlines()
    end = next((index for index, line in enumerate(lines) if line.startswith("####")), None)
    statement = "\n".join(lines[:end]).strip()
    if end is None or not statement.lower().startswith("copyright"):
        raise SampleError(f"{readme} doesn't start with a copyright statement")
    return (statement + "\n").encode("utf-8")


def extract_families(archive: Path, families: set[str], folder: Path) -> str:
    """Copy the named families' files from the archive into `folder`, reading the whole archive
    as a stream. Returns its sha256."""
    with archive.open("rb") as raw:
        reader = HashingReader(raw)
        try:
            with open_stream(reader) as tar:
                for member in tar:
                    found = FAMILY_FILE.fullmatch(PurePosixPath(member.name).name)
                    if member.isfile() and found is not None and found[1] in families:
                        stream = tar.extractfile(member)
                        if stream is None:
                            raise SampleError(f"can't read {member.name}")
                        with (folder / found[0]).open("wb") as target:
                            shutil.copyfileobj(stream, target, CHUNK)
            reader.drain()
        except (tarfile.TarError, EOFError, OSError) as error:
            raise SampleError(f"can't read {archive}: {error}") from error
    return reader.digest.hexdigest()


def extract_blast(archive: Path, folder: Path) -> str:
    """Copy the BLAST database's files from the archive into `folder`, reading the whole archive
    as a stream. Returns its sha256."""
    found: set[str] = set()
    with archive.open("rb") as raw:
        reader = HashingReader(raw)
        try:
            with open_stream(reader) as tar:
                for member in tar:
                    if member.isfile() and member.name in BLAST_FILES:
                        stream = tar.extractfile(member)
                        if stream is None:
                            raise SampleError(f"can't read {member.name}")
                        with (folder / PurePosixPath(member.name).name).open("wb") as target:
                            shutil.copyfileobj(stream, target, CHUNK)
                        found.add(member.name)
            reader.drain()
        except (tarfile.TarError, EOFError, OSError) as error:
            raise SampleError(f"can't read {archive}: {error}") from error
    missing = [name for name in BLAST_FILES if name not in found]
    if missing:
        raise SampleError(f"not in {archive}: {', '.join(missing)}")
    return reader.digest.hexdigest()


def write_tarball(path: Path, files: dict[str, Path], compresslevel: int = 9) -> None:
    """A reproducible tarball: members sorted by path, USTAR, owned by 0 and dated 0, modes 0644
    and 0755, gzip level 9 with no name or date in its header. Tests can compress less."""
    folders = {str(parent) for name in files for parent in PurePosixPath(name).parents}
    folders.discard(".")
    with (
        path.open("wb") as raw,
        gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, compresslevel=compresslevel, mtime=0
        ) as compressed,
        tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as tar,
    ):
        for name in sorted(folders | set(files)):
            info = tarfile.TarInfo(name)
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            if name in folders:
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
                continue
            info.mode = 0o644
            info.size = files[name].stat().st_size
            with files[name].open("rb") as source:
                tar.addfile(info, source)


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
        with tempfile.TemporaryDirectory(dir=root, prefix=".csnp-sample-") as work:
            tarball = source if source is not None else download(asset.url, Path(work) / asset.name)
            actual = sha256_file(tarball)
            if actual != asset.sha256:
                raise SampleError(
                    f"{tarball}'s sha256 is {actual}, not the manifest's {asset.sha256}"
                )
            unpacked = Path(work) / "unpacked"
            unpacked.mkdir()
            unpack(tarball, unpacked)
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


def download(url: str, target: Path) -> Path:
    """Download `url` to `target` over HTTPS only, redirects included."""
    if urllib.parse.urlsplit(url).scheme != "https":
        raise SampleError(f"refusing to download {url}: only https is allowed")
    # S310 flags opening a URL, for its file: and other schemes. The URL is https, checked
    # above, and where a redirect led is checked below.
    request = urllib.request.Request(url, headers={"User-Agent": "panther-engine"})  # noqa: S310
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:  # noqa: S310
        final = cast(str, response.geturl())
        if urllib.parse.urlsplit(final).scheme != "https":
            raise SampleError(f"refusing to download {final}: only https is allowed")
        with target.open("wb") as out:
            shutil.copyfileobj(cast(IO[bytes], response), out, CHUNK)
    return target


def unpack(tarball: Path, folder: Path) -> None:
    """Unpack `tarball` into `folder`, after checking that every member is a regular file or a
    folder at a relative path under `csnp/`. Nothing is unpacked if one isn't."""
    try:
        with tarfile.open(tarball, "r:gz") as tar:
            members = tar.getmembers()
            for member in members:
                path = PurePosixPath(member.name)
                if (
                    not (member.isfile() or member.isdir())
                    or path.is_absolute()
                    or ".." in path.parts
                    or path.parts[:1] != (SERVICE,)
                ):
                    raise SampleError(f"unsafe member in {tarball.name}: {member.name!r}")
            # The data filter refuses such members too, and anything else unsafe.
            tar.extractall(folder, members, filter="data")
    except (tarfile.TarError, EOFError, OSError) as error:
        raise SampleError(f"can't unpack {tarball}: {error}") from error
