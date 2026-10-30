import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest
from csnp_fixtures import FAMILY, FIXTURES, family_files, make_tar

from panther_engine.cli import main

README = """copyright (C) 2016 Paul Thomas
This file may be copied and redistributed freely, without advance permission,
provided that this Copyright statement is reproduced with each copy.

##########
PANTHER-PSEP SNP scoring tool - Version 1.01
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def inputs(tmp_path: Path) -> Path:
    folder = tmp_path / "inputs"
    folder.mkdir()
    make_tar(
        folder / "PAML_RST.tar.gz",
        [*family_files("PTHR00002"), *family_files(FAMILY), *family_files("PTHR00003_1")],
    )
    (folder / "README.txt").write_text(README, encoding="utf-8")
    (folder / "families.txt").write_text(f"# the clean family\n{FAMILY}\n\nPTHR00003_1\n")
    return folder


def build(inputs: Path, out: Path, *, archive_sha256: str | None = None) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    archive = inputs / "PAML_RST.tar.gz"
    return main(
        [
            "csnp",
            "sample",
            "build",
            str(archive),
            "--species",
            str(FIXTURES / "species.nhx"),
            "--species-sha256",
            sha256(FIXTURES / "species.nhx"),
            "--readme",
            str(inputs / "README.txt"),
            "--families",
            str(inputs / "families.txt"),
            "--tag",
            "csnp-sample-1",
            "--out",
            str(out),
            "--manifest",
            str(out.with_suffix(".json")),
            "--archive-sha256",
            archive_sha256 or sha256(archive),
        ]
    )


@pytest.fixture
def built(inputs: Path, tmp_path: Path) -> Path:
    """The sample tarball built from the fixture archive; its manifest is beside it."""
    tarball = tmp_path / "build" / "csnp-sample-1.tar.gz"
    assert build(inputs, tarball) == 0
    return tarball


def manifest_of(tarball: Path) -> Path:
    return tarball.with_suffix(".json")


# build


def test_two_builds_are_byte_identical(inputs: Path, built: Path, tmp_path: Path) -> None:
    again = tmp_path / "again" / "csnp-sample-1.tar.gz"

    assert build(inputs, again) == 0

    assert again.read_bytes() == built.read_bytes()
    assert manifest_of(again).read_text() == manifest_of(built).read_text()


def test_the_tarball_holds_the_families_the_species_tree_and_the_copyright(built: Path) -> None:
    with tarfile.open(built) as tar:
        names = tar.getnames()
        statement = tar.extractfile("csnp/9/PSEP-COPYRIGHT.txt")
        assert statement is not None
        copyright_text = statement.read().decode()

    assert names == [
        "csnp",
        "csnp/9",
        "csnp/9/PAML_RST",
        "csnp/9/PAML_RST/PTHR00001.orig.tree",
        "csnp/9/PAML_RST/PTHR00001.paml",
        "csnp/9/PAML_RST/PTHR00001.rst",
        "csnp/9/PAML_RST/PTHR00003_1.orig.tree",
        "csnp/9/PAML_RST/PTHR00003_1.paml",
        "csnp/9/PAML_RST/PTHR00003_1.rst",
        "csnp/9/PSEP-COPYRIGHT.txt",
        "csnp/9/species_pthr8_time.nhx",
    ]
    assert copyright_text == "\n".join(README.splitlines()[:3]) + "\n"


def test_the_tarballs_members_are_sorted_owned_by_0_and_dated_0(built: Path) -> None:
    raw = built.read_bytes()
    with tarfile.open(built) as tar:
        members = tar.getmembers()

    assert [member.name for member in members] == sorted(member.name for member in members)
    for member in members:
        assert (member.uid, member.gid, member.uname, member.gname) == (0, 0, "", "")
        assert member.mtime == 0
        assert member.mode == (0o755 if member.isdir() else 0o644)
    # The gzip header: no file name flag, and a zero date
    assert raw[3] & 0x08 == 0
    assert raw[4:8] == b"\0\0\0\0"
    assert gzip.decompress(raw)[257:263] == b"ustar\0"


def test_the_manifest_pins_the_tarball_the_source_and_each_file(built: Path, inputs: Path) -> None:
    manifest = json.loads(manifest_of(built).read_text())

    assert manifest["tag"] == "csnp-sample-1"
    assert manifest["asset"] == {
        "name": "csnp-sample-1.tar.gz",
        "url": "https://github.com/pantherdb/panther-scoring-services/releases/download/"
        "csnp-sample-1/csnp-sample-1.tar.gz",
        "sha256": sha256(built),
        "bytes": built.stat().st_size,
    }
    assert manifest["source"] == {
        "name": "PAML_RST.tar.gz",
        "sha256": sha256(inputs / "PAML_RST.tar.gz"),
    }
    assert manifest["families"] == [FAMILY, "PTHR00003_1"]
    assert manifest["files"]["csnp/9/PAML_RST/PTHR00001.paml"] == sha256(
        FIXTURES / "PTHR00001.paml"
    )
    assert manifest["files"]["csnp/9/species_pthr8_time.nhx"] == sha256(FIXTURES / "species.nhx")
    assert len(manifest["files"]) == 8


def test_an_archive_with_the_wrong_sha256_is_refused_and_nothing_is_written(
    inputs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "build" / "csnp-sample-1.tar.gz"
    pinned = "0" * 64

    status = build(inputs, out, archive_sha256=pinned)

    err = capsys.readouterr().err
    assert status == 1
    assert pinned in err
    assert sha256(inputs / "PAML_RST.tar.gz") in err
    assert list(out.parent.iterdir()) == []


def test_a_family_not_in_the_archive_is_refused(
    inputs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (inputs / "families.txt").write_text(f"{FAMILY}\nPTHR99999\n")
    out = tmp_path / "build" / "csnp-sample-1.tar.gz"

    assert build(inputs, out) == 1
    assert "not in" in capsys.readouterr().err
    assert list(out.parent.iterdir()) == []


# fetch and verify


def fetch(*args: str) -> int:
    return main(["csnp", "sample", "fetch", *args])


def verify(*args: str) -> int:
    return main(["csnp", "sample", "verify", *args])


def with_asset(manifest: Path, path: Path, **asset: object) -> Path:
    """A copy of `manifest`, at `path`, with some of its asset's fields changed."""
    content = json.loads(manifest.read_text())
    content["asset"].update(asset)
    path.write_text(json.dumps(content))
    return path


def snapshot(folder: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(folder)): path.read_bytes() if path.is_file() else b""
        for path in sorted(folder.rglob("*"))
    }


@pytest.fixture
def data(tmp_path: Path) -> Path:
    folder = tmp_path / "data"
    folder.mkdir()
    return folder


@pytest.fixture
def offline(built: Path, tmp_path: Path) -> Path:
    """The built manifest, with a URL that fails if anything tries to download it."""
    return with_asset(manifest_of(built), tmp_path / "offline.json", url="https://localhost:9/x")


def test_a_fresh_fetch_unpacks_every_file_and_checks_it(
    built: Path, offline: Path, data: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = fetch("--data-dir", str(data), "--manifest", str(offline), "--from", str(built))

    assert status == 0
    assert "fetched" in capsys.readouterr().out
    files = json.loads(offline.read_text())["files"]
    for name, digest in files.items():
        assert sha256(data / name) == digest
    assert sorted(path.name for path in data.iterdir()) == ["csnp"]
    assert verify("--data-dir", str(data), "--manifest", str(offline)) == 0


def test_a_fetch_into_a_folder_that_already_matches_downloads_nothing(
    built: Path, offline: Path, data: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert fetch("--data-dir", str(data), "--manifest", str(offline), "--from", str(built)) == 0
    capsys.readouterr()

    # No --from, and the manifest's URL can't be reached: a download would fail.
    status = fetch("--data-dir", str(data), "--manifest", str(offline))

    assert status == 0
    assert "nothing to fetch" in capsys.readouterr().out


def test_a_wrong_checksum_unpacks_nothing_and_names_both(
    built: Path, offline: Path, data: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    wrong = with_asset(offline, tmp_path / "wrong.json", sha256="f" * 64)
    before = snapshot(data)

    status = fetch("--data-dir", str(data), "--manifest", str(wrong), "--from", str(built))

    err = capsys.readouterr().err
    assert status == 1
    assert "f" * 64 in err
    assert sha256(built) in err
    assert snapshot(data) == before


def unsafe_tarball(path: Path, name: str, kind: bytes = tarfile.REGTYPE) -> Path:
    with gzip.open(path, "wb") as compressed, tarfile.open(fileobj=compressed, mode="w") as tar:
        info = tarfile.TarInfo(name)
        info.type = kind
        if kind == tarfile.SYMTYPE:
            info.linkname = "/etc/passwd"
            tar.addfile(info)
        else:
            info.size = 3
            tar.addfile(info, io.BytesIO(b"bad"))
    return path


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("/csnp/absolute", tarfile.REGTYPE),
        ("csnp/../../escape", tarfile.REGTYPE),
        ("csnp/9/link", tarfile.SYMTYPE),
        ("elsewhere/file", tarfile.REGTYPE),
    ],
)
def test_an_unsafe_member_unpacks_nothing_and_is_named(
    name: str,
    kind: bytes,
    offline: Path,
    data: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tarball = unsafe_tarball(tmp_path / "unsafe.tar.gz", name, kind)
    manifest = with_asset(offline, tmp_path / "unsafe.json", sha256=sha256(tarball))
    before = snapshot(data)

    status = fetch("--data-dir", str(data), "--manifest", str(manifest), "--from", str(tarball))

    assert status == 1
    assert repr(name) in capsys.readouterr().err
    assert snapshot(data) == before
    assert not (tmp_path / "escape").exists()


def test_an_http_url_is_refused(
    offline: Path, data: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plain = with_asset(offline, tmp_path / "http.json", url="http://example.org/sample.tar.gz")

    status = fetch("--data-dir", str(data), "--manifest", str(plain))

    assert status == 1
    assert "only https" in capsys.readouterr().err
    assert snapshot(data) == {}


def test_a_failed_fetch_doesnt_leave_a_folder_it_created(
    offline: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plain = with_asset(offline, tmp_path / "http.json", url="http://example.org/sample.tar.gz")
    data = tmp_path / "new-data"

    assert fetch("--data-dir", str(data), "--manifest", str(plain)) == 1
    assert not data.exists()


def test_without_a_data_folder_the_error_names_the_variable(
    offline: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PANTHER_DATA_DIR", raising=False)

    assert fetch("--manifest", str(offline)) == 1
    assert "PANTHER_DATA_DIR" in capsys.readouterr().err


def test_the_data_folder_comes_from_panther_data_dir(
    built: Path, offline: Path, data: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PANTHER_DATA_DIR", str(data))

    assert fetch("--manifest", str(offline), "--from", str(built)) == 0
    assert (data / "csnp" / "9" / "species_pthr8_time.nhx").is_file()


def test_verify_lists_a_changed_file_and_fails(
    built: Path, offline: Path, data: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert fetch("--data-dir", str(data), "--manifest", str(offline), "--from", str(built)) == 0
    paml = data / "csnp" / "9" / "PAML_RST" / f"{FAMILY}.paml"
    content = bytearray(paml.read_bytes())
    content[-2] ^= 1
    paml.write_bytes(bytes(content))
    capsys.readouterr()

    status = verify("--data-dir", str(data), "--manifest", str(offline))

    assert status == 1
    assert capsys.readouterr().out == f"differs: csnp/9/PAML_RST/{FAMILY}.paml\n"


def test_a_fetch_replaces_a_changed_file(built: Path, offline: Path, data: Path) -> None:
    assert fetch("--data-dir", str(data), "--manifest", str(offline), "--from", str(built)) == 0
    paml = data / "csnp" / "9" / "PAML_RST" / f"{FAMILY}.paml"
    paml.write_bytes(b"changed\n")

    assert fetch("--data-dir", str(data), "--manifest", str(offline), "--from", str(built)) == 0
    assert paml.read_bytes() == (FIXTURES / f"{FAMILY}.paml").read_bytes()
