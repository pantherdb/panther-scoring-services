import hashlib
import json
import os
import stat
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO, NoReturn

import pytest
from hmmscore_fixtures import (
    BINHMM,
    FAMILY_MODEL,
    NAMES,
    PREFIX,
    PRESSED,
    SF1_MODEL,
    SF2_MODEL,
    clean_library,
    data,
    library_tarball,
)

from panther_engine.cli import main
from panther_engine.hmmscore import data as hmmscore_data

URL = "https://data.example.org/hmm_scoring/19.0/PANTHER19.0_hmmscoring.tgz"


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def books_list(files: dict[str, bytes]) -> bytes:
    """books.sha256 as sha256sum writes it, for the model files in `files`, sorted by path."""
    models = sorted(path for path in files if path.endswith("hmmer.hmm"))
    return b"".join(f"{sha256(files[path])}  {path}\n".encode() for path in models)


def manifest(tarball: Path, out: Path, *extra: str) -> int:
    args = ["hmmscore", "data", "manifest", str(tarball), "--url", URL, "--manifest", str(out)]
    return main([*args, *extra])


# manifest


def test_the_manifest_pins_the_tarball_its_prefix_and_every_kept_file(tmp_path: Path) -> None:
    files = clean_library(flat=True)
    tarball = library_tarball(tmp_path / "library.tgz", files)
    out = tmp_path / "data.json"

    assert manifest(tarball, out) == 0

    pinned = json.loads(out.read_text(encoding="utf-8"))
    assert pinned["version"] == "19"
    assert pinned["tarball"] == {
        "url": URL,
        "bytes": tarball.stat().st_size,
        "sha256": sha256(tarball.read_bytes()),
    }
    assert pinned["prefix"] == PREFIX
    assert pinned["books"] == {"files": 4}
    expected = {
        f"hmmscore/19/{path}": sha256(files[path]) for path in ["README", NAMES, BINHMM, *PRESSED]
    }
    expected["hmmscore/19/books.sha256"] = sha256(books_list(files))
    assert pinned["files"] == expected


def test_two_manifests_of_the_same_tarball_are_byte_identical(tmp_path: Path) -> None:
    tarball = library_tarball(tmp_path / "library.tgz", clean_library())
    first, second = tmp_path / "first.json", tmp_path / "second.json"

    assert manifest(tarball, first) == 0
    assert manifest(tarball, second) == 0

    assert first.read_bytes() == second.read_bytes()


def test_the_manifest_is_as_readable_as_any_new_file(tmp_path: Path) -> None:
    # It's committed and copied into the image, where another user than its writer reads it.
    tarball = library_tarball(tmp_path / "library.tgz", clean_library())
    out = tmp_path / "data.json"
    old = os.umask(0o022)
    try:
        assert manifest(tarball, out) == 0
    finally:
        os.umask(old)

    assert stat.S_IMODE(out.stat().st_mode) == 0o644


def test_the_folders_the_prefix_is_in_are_allowed(tmp_path: Path) -> None:
    folders = ("target", "target/famlib")
    tarball = library_tarball(tmp_path / "library.tgz", clean_library(), folders=folders)

    assert manifest(tarball, tmp_path / "data.json") == 0


@pytest.mark.parametrize(
    ("member", "named"),
    [
        ((PREFIX + "books/PTHR10000/notes.txt", b"note\n"), "books/PTHR10000/notes.txt"),
        (("elsewhere/file", b"x\n"), "elsewhere/file"),
        ((PREFIX + "../escape", b"x\n"), "../escape"),
    ],
)
def test_an_unexpected_member_writes_nothing_and_is_named(
    member: tuple[str, bytes], named: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tarball = library_tarball(tmp_path / "library.tgz", clean_library(), extra=[member])
    out = tmp_path / "data.json"
    out.write_text("the earlier manifest\n")

    status = manifest(tarball, out)

    assert status == 1
    assert named in capsys.readouterr().err
    assert out.read_text() == "the earlier manifest\n"


def test_a_model_file_that_doesnt_read_writes_nothing_and_is_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = clean_library()
    files[SF2_MODEL] = data("broken/truncated.hmm")
    tarball = library_tarball(tmp_path / "library.tgz", files)
    out = tmp_path / "data.json"

    status = manifest(tarball, out)

    err = capsys.readouterr().err
    assert status == 1
    assert f"{SF2_MODEL}, line 129" in err
    assert not out.exists()


def test_a_file_that_isnt_a_gzipped_tar_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plain = tmp_path / "plain.tgz"
    plain.write_text("not a tarball\n")
    out = tmp_path / "data.json"

    assert manifest(plain, out) == 1
    assert "can't read" in capsys.readouterr().err
    assert not out.exists()


# fetch and verify


@dataclass(frozen=True)
class Library:
    tarball: Path
    pin: Path
    files: dict[str, bytes]


@pytest.fixture
def library(tmp_path: Path) -> Library:
    """The clean library's tarball, and its pin, written by `data manifest`."""
    files = clean_library()
    tarball = library_tarball(tmp_path / "library.tgz", files)
    pin = tmp_path / "data.json"
    assert manifest(tarball, pin) == 0
    return Library(tarball, pin, files)


@pytest.fixture
def served(library: Library, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """open_https serves the library's tarball. The URLs it was asked for."""
    urls: list[str] = []

    @contextmanager
    def stub(url: str) -> Generator[IO[bytes]]:
        urls.append(url)
        with library.tarball.open("rb") as raw:
            yield raw

    monkeypatch.setattr(hmmscore_data, "open_https", stub)
    return urls


def refuse(url: str) -> NoReturn:
    pytest.fail(f"downloaded {url}")


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """open_https fails the test if it's called."""
    monkeypatch.setattr(hmmscore_data, "open_https", refuse)


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    path = tmp_path / "data"
    path.mkdir()
    return path


def fetch(*args: str) -> int:
    return main(["hmmscore", "data", "fetch", *args])


def verify(*args: str) -> int:
    return main(["hmmscore", "data", "verify", *args])


def snapshot(path: Path) -> dict[str, bytes]:
    return {
        str(each.relative_to(path)): each.read_bytes() if each.is_file() else b""
        for each in sorted(path.rglob("*"))
    }


def kept(files: dict[str, bytes]) -> dict[str, bytes]:
    """What a fetch should leave under hmmscore/19/: the files scoring reads and books.sha256."""
    result = {
        path: content for path, content in files.items() if not path.endswith(("pir", "tree"))
    }
    result["books.sha256"] = books_list(files)
    return result


def test_a_fresh_fetch_downloads_keeps_what_scoring_reads_and_checks_it(
    library: Library, served: list[str], folder: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pinned_url = json.loads(library.pin.read_text())["tarball"]["url"]

    status = fetch("--data-dir", str(folder), "--manifest", str(library.pin))

    assert status == 0
    assert "fetched" in capsys.readouterr().out
    assert served == [pinned_url]
    assert snapshot(folder / "hmmscore" / "19") == {
        **{path: b"" for path in ("books", "books/PTHR99999", "globals")},
        **{f"books/PTHR99999/SF{n}": b"" for n in (1, 2, 3)},
        **kept(library.files),
    }
    assert sorted(path.name for path in folder.iterdir()) == ["hmmscore"]
    assert verify("--data-dir", str(folder), "--manifest", str(library.pin)) == 0


def test_a_local_copy_is_checked_and_used_without_the_network(
    library: Library, offline: None, folder: Path
) -> None:
    args = ["--data-dir", str(folder), "--manifest", str(library.pin)]

    assert fetch(*args, "--tarball", str(library.tarball)) == 0

    assert snapshot(folder / "hmmscore" / "19")["books.sha256"] == books_list(library.files)


def test_a_folder_that_already_matches_downloads_nothing(
    library: Library, offline: None, folder: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = ["--data-dir", str(folder), "--manifest", str(library.pin)]
    assert fetch(*args, "--tarball", str(library.tarball)) == 0
    capsys.readouterr()

    status = fetch(*args)

    assert status == 0
    assert "nothing to fetch" in capsys.readouterr().out


def test_a_wrong_checksum_writes_nothing_and_names_both(
    library: Library,
    served: list[str],
    folder: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pinned = json.loads(library.pin.read_text())
    pinned["tarball"]["sha256"] = "f" * 64
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps(pinned))

    status = fetch("--data-dir", str(folder), "--manifest", str(wrong))

    err = capsys.readouterr().err
    assert status == 1
    assert "f" * 64 in err
    assert hashlib.sha256(library.tarball.read_bytes()).hexdigest() in err
    assert snapshot(folder) == {}


@pytest.mark.parametrize(
    ("member", "named"),
    [
        ((PREFIX + "books/PTHR10000/notes.txt", b"note\n"), "books/PTHR10000/notes.txt"),
        ((PREFIX + "../escape", b"x\n"), "../escape"),
        (("elsewhere/file", b"x\n"), "elsewhere/file"),
    ],
)
def test_an_unexpected_or_unsafe_member_writes_nothing_and_is_named(
    member: tuple[str, bytes],
    named: str,
    library: Library,
    offline: None,
    folder: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bad = library_tarball(tmp_path / "bad.tgz", library.files, extra=[member])

    status = fetch("--data-dir", str(folder), "--manifest", str(library.pin), "--tarball", str(bad))

    assert status == 1
    assert named in capsys.readouterr().err
    assert snapshot(folder) == {}
    assert not (tmp_path / "escape").exists()
    assert not (folder.parent / "escape").exists()


def test_a_failed_fetch_leaves_the_data_folder_as_it_was(
    library: Library, offline: None, folder: Path, tmp_path: Path
) -> None:
    args = ["--data-dir", str(folder), "--manifest", str(library.pin)]
    assert fetch(*args, "--tarball", str(library.tarball)) == 0
    readme = folder / "hmmscore" / "19" / "README"
    readme.write_bytes(b"changed\n")
    before = snapshot(folder)
    files = dict(library.files)
    files["README"] = b"another README\n"
    other = library_tarball(tmp_path / "other.tgz", files)

    assert fetch(*args, "--tarball", str(other)) == 1

    assert snapshot(folder) == before


def test_a_failed_fetch_removes_a_data_folder_it_created(
    library: Library, offline: None, tmp_path: Path
) -> None:
    folder = tmp_path / "new-data"
    plain = tmp_path / "plain.tgz"
    plain.write_text("not a tarball\n")

    status = fetch(
        "--data-dir", str(folder), "--manifest", str(library.pin), "--tarball", str(plain)
    )

    assert status == 1
    assert not folder.exists()


def test_a_fetch_replaces_a_changed_file(library: Library, offline: None, folder: Path) -> None:
    args = ["--data-dir", str(folder), "--manifest", str(library.pin)]
    assert fetch(*args, "--tarball", str(library.tarball)) == 0
    model = folder / "hmmscore" / "19" / FAMILY_MODEL
    model.write_bytes(b"changed\n")

    assert fetch(*args, "--tarball", str(library.tarball)) == 0

    assert model.read_bytes() == data(FAMILY_MODEL)


def test_verify_lists_a_changed_model_file_and_fails(
    library: Library, offline: None, folder: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = ["--data-dir", str(folder), "--manifest", str(library.pin)]
    assert fetch(*args, "--tarball", str(library.tarball)) == 0
    model = folder / "hmmscore" / "19" / SF1_MODEL
    content = bytearray(model.read_bytes())
    content[-2] ^= 1
    model.write_bytes(bytes(content))
    capsys.readouterr()

    status = verify(*args)

    out = capsys.readouterr().out
    assert status == 1
    assert f"differs: hmmscore/19/{SF1_MODEL}" in out
    assert "0 missing and 1 differing, of 11 listed files" in out


def test_verify_lists_a_changed_books_list_and_fails(
    library: Library, offline: None, folder: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = ["--data-dir", str(folder), "--manifest", str(library.pin)]
    assert fetch(*args, "--tarball", str(library.tarball)) == 0
    listing = folder / "hmmscore" / "19" / "books.sha256"
    listing.write_bytes(listing.read_bytes() + b"\n")
    capsys.readouterr()

    status = verify(*args)

    out = capsys.readouterr().out
    assert status == 1
    assert "differs: hmmscore/19/books.sha256" in out


def test_verify_names_the_first_20_of_each_and_counts_the_rest(
    offline: None, folder: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = clean_library()
    for n in range(4, 27):
        files[f"books/PTHR99999/SF{n}/hmmer.hmm"] = data(SF1_MODEL)
    tarball = library_tarball(tmp_path / "many.tgz", files)
    pin = tmp_path / "many.json"
    assert manifest(tarball, pin) == 0
    args = ["--data-dir", str(folder), "--manifest", str(pin)]
    assert fetch(*args, "--tarball", str(tarball)) == 0
    for n in range(4, 27):
        (folder / "hmmscore" / "19" / f"books/PTHR99999/SF{n}/hmmer.hmm").unlink()
    capsys.readouterr()

    status = verify(*args)

    out = capsys.readouterr().out.splitlines()
    assert status == 1
    assert out[0] == "23 missing and 0 differing, of 34 listed files"
    assert len([line for line in out if line.startswith("missing: hmmscore/19/")]) == 20
    assert "missing: and 3 more" in out


def test_without_a_data_folder_the_error_names_the_variable(
    library: Library, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PANTHER_DATA_DIR", raising=False)

    assert fetch("--manifest", str(library.pin), "--tarball", str(library.tarball)) == 1
    assert "PANTHER_DATA_DIR" in capsys.readouterr().err
