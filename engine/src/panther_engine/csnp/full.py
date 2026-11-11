"""The full cSNP data's checksum manifest, `full.json`, shipped with the package.

The full data is the whole PAML_RST library, the PANTHER9 BLAST database, the species tree and the
PSEP copyright statement, unpacked under the data folder at `csnp/9/`, as docs/testing/engine.md's
"Using the Full Library" says. A deploy checks it against `full.json` before it takes traffic
(`fix-csnp-blast-handling`, design.md, decisions 6 to 8).

- **build** writes the manifest from the pinned archives, the species tree and the release's
  README, reading each archive as a stream and never unpacking it. It refuses any input whose
  sha256 isn't the pinned one, and then writes nothing. The same inputs give the same bytes.
- **verify** is `sample.verify_folder` with this manifest.

The manifest is in `sample.json`'s format: `files` maps each path, relative to the data folder, to
its sha256, and `source`, `blast` and `species` pin what it was built from.
"""

import hashlib
import json
import tarfile
from pathlib import Path

from panther_engine.core.archive import open_stream
from panther_engine.core.manifest import (
    CHUNK,
    HashingReader,
    ManifestError,
    checksums,
    read_manifest,
    relative_path,
    sha256_file,
)
from panther_engine.csnp import sample

MANIFEST = Path(__file__).with_name("full.json")


class FullDataError(Exception):
    """The full data's manifest can't be built from the inputs given."""


def pinned_copyright() -> str:
    """The copyright statement's sha256, as the sample's manifest pins it."""
    digest = checksums(read_manifest(sample.MANIFEST)).get(f"{sample.FOLDER}/{sample.COPYRIGHT}")
    if digest is None:
        raise FullDataError(f"{sample.MANIFEST} doesn't pin {sample.COPYRIGHT}")
    return digest


def build(
    archive: Path,
    *,
    blast: Path,
    species: Path,
    readme: Path,
    manifest: Path,
    archive_sha256: str = sample.PINNED_ARCHIVE,
    blast_sha256: str = sample.PINNED_BLAST,
    species_sha256: str = sample.PINNED_SPECIES,
    copyright_sha256: str | None = None,
) -> dict[str, object]:
    """Write the full data's manifest at `manifest`, and return it.

    Nothing is written unless every input's checksum matches its pin. `copyright_sha256` is the
    sample's pin by default.
    """
    expected_copyright = copyright_sha256 or pinned_copyright()
    actual = sha256_file(species)
    if actual != species_sha256:
        raise FullDataError(f"{species}'s sha256 is {actual}, not the pinned {species_sha256}")
    statement = sample.copyright_statement(readme)
    actual = hashlib.sha256(statement).hexdigest()
    if actual != expected_copyright:
        raise FullDataError(
            f"the copyright statement in {readme} has sha256 {actual}, not the pinned "
            f"{expected_copyright}"
        )

    files: dict[str, str] = {}
    digest, database = hash_members(blast, wanted=set(sample.BLAST_FILES))
    if digest != blast_sha256:
        raise FullDataError(f"{blast}'s sha256 is {digest}, not the pinned {blast_sha256}")
    missing = [name for name in sample.BLAST_FILES if name not in database]
    if missing:
        raise FullDataError(f"not in {blast}: {', '.join(missing)}")
    files.update(database)
    digest, library = hash_members(archive)
    if digest != archive_sha256:
        raise FullDataError(f"{archive}'s sha256 is {digest}, not the pinned {archive_sha256}")
    files.update(library)
    files[sample.SPECIES] = species_sha256
    files[sample.COPYRIGHT] = expected_copyright

    result: dict[str, object] = {
        "source": {"name": archive.name, "sha256": archive_sha256},
        "blast": {"name": blast.name, "sha256": blast_sha256},
        "species": {"name": sample.SPECIES, "sha256": species_sha256},
        "files": {f"{sample.FOLDER}/{name}": files[name] for name in sorted(files)},
    }
    manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def hash_members(archive: Path, wanted: set[str] | None = None) -> tuple[str, dict[str, str]]:
    """The archive's sha256, and the sha256 of each regular member, or of each one named in
    `wanted`, by its path in the archive. The archive is read once, front to back, as a stream.

    Raises FullDataError for a member whose path would land outside the cSNP data folder.
    """
    members: dict[str, str] = {}
    with archive.open("rb") as raw:
        reader = HashingReader(raw)
        try:
            with open_stream(reader) as tar:
                for member in tar:
                    if not member.isfile() or (wanted is not None and member.name not in wanted):
                        continue
                    try:
                        relative_path(member.name)
                    except ManifestError as error:
                        raise FullDataError(f"{archive}: {error}") from error
                    stream = tar.extractfile(member)
                    if stream is None:
                        raise FullDataError(f"can't read {member.name} in {archive}")
                    digest = hashlib.sha256()
                    while chunk := stream.read(CHUNK):
                        digest.update(chunk)
                    members[member.name] = digest.hexdigest()
            reader.drain()
        except (tarfile.TarError, EOFError, OSError) as error:
            raise FullDataError(f"can't read {archive}: {error}") from error
    return reader.digest.hexdigest(), members
