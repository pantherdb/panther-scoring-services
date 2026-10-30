import hashlib
import json
from pathlib import Path

import pytest

from panther_engine.core.manifest import (
    ManifestError,
    checksums,
    read_manifest,
    relative_path,
    sha256_file,
    verify,
)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    (data / "csnp" / "9").mkdir(parents=True)
    (data / "csnp" / "9" / "a.paml").write_bytes(b"alpha\n")
    (data / "csnp" / "9" / "b.rst").write_bytes(b"beta\n")
    return data


def test_all_files_match(folder: Path) -> None:
    files = {"csnp/9/a.paml": digest(b"alpha\n"), "csnp/9/b.rst": digest(b"beta\n")}

    result = verify(folder, files)

    assert result.ok
    assert result.missing == result.differing == ()


def test_a_missing_file_and_a_differing_file_are_both_named(folder: Path) -> None:
    files = {
        "csnp/9/a.paml": digest(b"something else\n"),
        "csnp/9/b.rst": digest(b"beta\n"),
        "csnp/9/c.orig.tree": digest(b"gamma\n"),
    }

    result = verify(folder, files)

    assert not result.ok
    assert result.missing == ("csnp/9/c.orig.tree",)
    assert result.differing == ("csnp/9/a.paml",)


def test_files_the_manifest_does_not_list_are_ignored(folder: Path) -> None:
    (folder / "csnp" / "9" / "PTHR99999.paml").write_bytes(b"the full library\n")

    assert verify(folder, {"csnp/9/a.paml": digest(b"alpha\n")}).ok


def test_files_are_hashed_in_chunks(tmp_path: Path) -> None:
    content = bytes(range(256)) * 10_000  # bigger than one chunk
    path = tmp_path / "big"
    path.write_bytes(content)

    assert sha256_file(path) == digest(content)


@pytest.mark.parametrize(
    "path", ["/etc/passwd", "../outside", "csnp/../../outside", "csnp//9", "./csnp", "", "a\\b"]
)
def test_a_path_outside_the_data_folder_is_rejected(path: str) -> None:
    with pytest.raises(ManifestError, match="not a relative path"):
        relative_path(path)


def test_a_manifest_listing_an_unsafe_path_is_rejected(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"files": {"../escape": digest(b"")}}), encoding="utf-8")

    with pytest.raises(ManifestError, match="not a relative path"):
        read_manifest(manifest)


def test_a_manifest_with_a_bad_checksum_is_rejected() -> None:
    with pytest.raises(ManifestError, match="not a sha256"):
        checksums({"files": {"csnp/9/a.paml": "ABC"}})


def test_other_members_of_a_manifest_are_kept(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"tag": "csnp-sample-1", "files": {"csnp/9/a.paml": digest(b"")}}),
        encoding="utf-8",
    )

    loaded = read_manifest(manifest)

    assert loaded["tag"] == "csnp-sample-1"
    assert checksums(loaded) == {"csnp/9/a.paml": digest(b"")}
