"""Checksum manifests: data files listed by path, relative to the data folder, with their sha256.

A manifest is a JSON object whose `files` member maps each path to its sha256. Other members are
the business of whoever wrote it, such as the cSNP sample's release tag. Files the manifest doesn't
list are ignored, so a folder holding the full data still passes a check against a sample.
"""

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import IO, cast

CHUNK = 1 << 20
SHA256 = re.compile(r"[0-9a-f]{64}")


class ManifestError(Exception):
    """A manifest that can't be read, or that lists a path outside the data folder."""


@dataclass(frozen=True)
class Mismatches:
    """The listed files missing from a folder, and those whose checksum differs, in path order."""

    missing: tuple[str, ...]
    differing: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing and not self.differing


def sha256_stream(stream: IO[bytes]) -> str:
    digest = hashlib.sha256()
    while chunk := stream.read(CHUNK):
        digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return sha256_stream(stream)


def relative_path(path: str) -> PurePosixPath:
    """`path` as a relative path inside the data folder. Raises ManifestError otherwise."""
    parsed = PurePosixPath(path)
    if (
        not path
        or "\\" in path
        or parsed.is_absolute()
        or any(part in ("", ".", "..") for part in path.split("/"))
    ):
        raise ManifestError(f"not a relative path inside the data folder: {path!r}")
    return parsed


def checksums(manifest: Mapping[str, object]) -> dict[str, str]:
    """The manifest's `files` member, checked: relative paths mapped to sha256 digests."""
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise ManifestError("the manifest has no files object")
    result: dict[str, str] = {}
    for path, digest in cast(dict[object, object], files).items():
        if not isinstance(path, str) or not isinstance(digest, str):
            raise ManifestError(f"not a path and a sha256: {path!r}: {digest!r}")
        relative_path(path)
        if not SHA256.fullmatch(digest):
            raise ManifestError(f"not a sha256 for {path}: {digest!r}")
        result[path] = digest
    return result


def read_manifest(path: Path) -> dict[str, object]:
    """The manifest at `path`, with its `files` member checked."""
    try:
        manifest: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ManifestError(f"can't read the manifest {path}: {error}") from error
    if not isinstance(manifest, dict):
        raise ManifestError(f"the manifest {path} isn't a JSON object")
    result = {str(key): value for key, value in cast(dict[object, object], manifest).items()}
    checksums(result)
    return result


def verify(folder: Path, files: Mapping[str, str]) -> Mismatches:
    """Check each listed file under `folder` against its sha256."""
    missing: list[str] = []
    differing: list[str] = []
    for path in sorted(files):
        target = folder / relative_path(path)
        if not target.is_file():
            missing.append(path)
        elif sha256_file(target) != files[path]:
            differing.append(path)
    return Mismatches(tuple(missing), tuple(differing))
