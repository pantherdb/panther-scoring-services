import gzip
import hashlib
import io
import json
import tarfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pytest
from hmmscore_fixtures import (
    BINHMM,
    FAMILY_MODEL,
    NAMES,
    README,
    SF1_MODEL,
    SF2_MODEL,
    SF3_MODEL,
    clean_library,
    data,
    library_tarball,
)

from panther_engine.cli import main

URL = "https://data.example.org/hmm_scoring/19.0/PANTHER19.0_hmmscoring.tgz"
TAG = "hmmscore-sample-1"
MODELS = (FAMILY_MODEL, SF1_MODEL, SF2_MODEL, SF3_MODEL)
# The fake hmmpress: HMMER's version line for -h. Otherwise it copies its input to the .h3m, as
# HMMER 3.4 does for binary records, so a test sees which models it was given, and writes a
# stand-in for each other pressed file, holding the arguments it was given.
FAKE_HMMPRESS = """if [ "$1" = "-h" ]; then
  echo "# HMMER {version} (Aug 2023); http://hmmer.org/"
  exit 0
fi
/bin/cat "$1" > "$1.h3m"
for suffix in h3f h3i h3p; do printf '%s\\n' "$*" > "$1.$suffix"; done"""


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def other_family(content: bytes) -> bytes:
    """A model of PTHR99999 renamed as PTHR88888's."""
    return content.replace(b"PTHR99999", b"PTHR88888")


@dataclass(frozen=True)
class Library:
    tarball: Path
    pin: Path


class FakeHmmer(Protocol):
    def __call__(self, version: str) -> Path: ...


def library_of(tmp_path: Path, files: dict[str, bytes]) -> Library:
    tarball = library_tarball(tmp_path / "library.tgz", files)
    pin = tmp_path / "data.json"
    args = ["hmmscore", "data", "manifest", str(tarball), "--url", URL, "--manifest", str(pin)]
    assert main(args) == 0
    return Library(tarball, pin)


@pytest.fixture
def library(tmp_path: Path) -> Library:
    return library_of(tmp_path, clean_library())


@pytest.fixture
def hmmpress(make_tool: Callable[[str, str], Path], monkeypatch: pytest.MonkeyPatch) -> FakeHmmer:
    """Returns `fake(version)`, which puts a fake hmmpress of that version on PATH, and nothing
    else."""

    def fake(version: str) -> Path:
        tool = make_tool("hmmpress", FAKE_HMMPRESS.replace("{version}", version))
        monkeypatch.setenv("PATH", str(tool.parent))
        return tool

    return fake


def build(library: Library, out: Path, families: str = "PTHR99999\n", *extra: str) -> int:
    listing = out.parent / "families.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    listing.write_text(families)
    return main(
        [
            "hmmscore",
            "sample",
            "build",
            str(library.tarball),
            "--families",
            str(listing),
            "--tag",
            TAG,
            "--out",
            str(out),
            "--manifest",
            str(out.with_suffix(".json")),
            "--pin",
            str(library.pin),
            *extra,
        ]
    )


def unpacked(tarball: Path) -> dict[str, bytes]:
    """The tarball's files, by path, and its folders, as empty."""
    with tarfile.open(tarball) as tar:
        result: dict[str, bytes] = {}
        for member in tar.getmembers():
            stream = tar.extractfile(member)
            result[member.name] = stream.read() if stream is not None else b""
        return result


def pressed(args: str, models: bytes) -> dict[str, bytes]:
    """The fake hmmpress's four files, as written for `args` and its input `models`."""
    return {
        **{
            f"hmmscore/19/globals/binHmm.{suffix}": f"{args}\n".encode()
            for suffix in ("h3f", "h3i", "h3p")
        },
        "hmmscore/19/globals/binHmm.h3m": models,
    }


# build


@pytest.mark.parametrize(
    ("flat", "binhmm"),
    [
        # Without a flat binHmm: hmmpress is given the family's records cut from binHmm.h3m, in
        # binHmm's order, and the sample holds no flat binHmm, like the library.
        (False, {}),
        # With one: hmmpress is given its models for the family, byte for byte, in its order, and
        # the sample holds them as its flat binHmm.
        (True, {"hmmscore/19/globals/binHmm": data(BINHMM)}),
    ],
)
def test_the_sample_holds_the_familys_files_names_and_pressed_files(
    tmp_path: Path, hmmpress: FakeHmmer, flat: bool, binhmm: dict[str, bytes]
) -> None:
    hmmpress("3.4")
    files = clean_library(flat=flat)
    library = library_of(tmp_path, files)
    out = tmp_path / "build" / f"{TAG}.tar.gz"

    assert build(library, out) == 0

    content = unpacked(out)
    folders = ["hmmscore", "hmmscore/19", "hmmscore/19/books", "hmmscore/19/books/PTHR99999"]
    folders += [f"hmmscore/19/books/PTHR99999/SF{n}" for n in (1, 2, 3)]
    folders.append("hmmscore/19/globals")
    models = data(BINHMM) if flat else data("globals/binHmm.h3m")
    assert content == {
        **dict.fromkeys(folders, b""),
        "hmmscore/19/README": README,
        "hmmscore/19/globals/names.tab": data(NAMES),
        **binhmm,
        **pressed("binHmm", models),
        **{f"hmmscore/19/{path}": data(path) for path in MODELS},
    }


def test_without_a_flat_binhmm_only_the_chosen_families_records_are_cut(
    tmp_path: Path, hmmpress: FakeHmmer
) -> None:
    hmmpress("3.4")
    files = clean_library()
    # The index now says the last record, SF1's, is another family's model.
    renamed = (b"PTHR99999.SF1.pir", b"PTHR88888.SF1.pir")
    files["globals/binHmm.h3i"] = files["globals/binHmm.h3i"].replace(*renamed)
    library = library_of(tmp_path, files)
    out = tmp_path / "build" / f"{TAG}.tar.gz"

    assert build(library, out) == 0

    # SF2's record and the family's: the first 14,558 bytes of binHmm.h3m.
    content = unpacked(out)
    assert content["hmmscore/19/globals/binHmm.h3m"] == data("globals/binHmm.h3m")[:14558]
    assert "hmmscore/19/globals/binHmm" not in content


@pytest.mark.tools("hmmpress")
def test_hmmpress_gives_the_records_back_in_binhmm_h3m(library: Library, tmp_path: Path) -> None:
    out = tmp_path / "build" / f"{TAG}.tar.gz"

    assert build(library, out) == 0

    content = unpacked(out)
    assert content["hmmscore/19/globals/binHmm.h3m"] == data("globals/binHmm.h3m")
    assert "hmmscore/19/globals/binHmm" not in content


def test_an_hmmpress_that_changes_the_records_writes_nothing(
    library: Library,
    tmp_path: Path,
    make_tool: Callable[[str, str], Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    changed = FAKE_HMMPRESS.replace('/bin/cat "$1" >', "printf 'changed' >").replace(
        "{version}", "3.4"
    )
    monkeypatch.setenv("PATH", str(make_tool("hmmpress", changed).parent))
    out = tmp_path / "build" / f"{TAG}.tar.gz"

    status = build(library, out)

    assert status == 1
    assert "binHmm.h3m" in capsys.readouterr().err
    assert sorted(path.name for path in out.parent.iterdir()) == ["families.txt"]


def test_only_the_chosen_families_are_in_the_sample_in_the_libraries_order(
    tmp_path: Path, hmmpress: FakeHmmer
) -> None:
    hmmpress("3.4")
    files = clean_library(flat=True)
    for path in MODELS:
        files[other_family(path.encode()).decode()] = other_family(data(path))
    files[NAMES] = other_family(data(NAMES)) + data(NAMES)
    files[BINHMM] = data(BINHMM) + other_family(data(BINHMM))
    library = library_of(tmp_path, files)
    out = tmp_path / "build" / f"{TAG}.tar.gz"

    assert build(library, out, "# the second family\nPTHR88888\n") == 0

    content = unpacked(out)
    assert content["hmmscore/19/globals/names.tab"] == other_family(data(NAMES))
    assert content["hmmscore/19/globals/binHmm"] == other_family(data(BINHMM))
    models = sorted(name for name in content if name.endswith("hmmer.hmm"))
    assert models == sorted(
        f"hmmscore/19/{other_family(path.encode()).decode()}" for path in MODELS
    )


def test_the_manifest_pins_the_tarball_the_source_the_hmmer_and_each_file(
    library: Library, tmp_path: Path, hmmpress: FakeHmmer
) -> None:
    hmmpress("3.4")
    out = tmp_path / "build" / f"{TAG}.tar.gz"

    assert build(library, out) == 0

    manifest = json.loads(out.with_suffix(".json").read_text())
    assert manifest["tag"] == TAG
    assert manifest["asset"] == {
        "name": f"{TAG}.tar.gz",
        "url": "https://github.com/pantherdb/panther-scoring-services/releases/download/"
        f"{TAG}/{TAG}.tar.gz",
        "sha256": sha256(out.read_bytes()),
        "bytes": out.stat().st_size,
    }
    assert manifest["source"] == {
        "name": "library.tgz",
        "sha256": sha256(library.tarball.read_bytes()),
    }
    assert manifest["hmmer"] == "3.4"
    assert manifest["families"] == ["PTHR99999"]
    files = {name: sha256(content) for name, content in unpacked(out).items() if content}
    assert manifest["files"] == files


def test_the_tarballs_members_are_sorted_owned_by_0_and_dated_0(
    library: Library, tmp_path: Path, hmmpress: FakeHmmer
) -> None:
    hmmpress("3.4")
    out = tmp_path / "build" / f"{TAG}.tar.gz"

    assert build(library, out) == 0

    raw = out.read_bytes()
    with tarfile.open(out) as tar:
        members = tar.getmembers()
    assert [member.name for member in members] == sorted(member.name for member in members)
    for member in members:
        assert (member.uid, member.gid, member.uname, member.gname) == (0, 0, "", "")
        assert member.mtime == 0
    assert raw[4:8] == b"\0\0\0\0"


def test_a_tarball_whose_sha256_isnt_the_pin_writes_nothing_and_names_both(
    library: Library,
    tmp_path: Path,
    hmmpress: FakeHmmer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    hmmpress("3.4")
    pinned = json.loads(library.pin.read_text())
    pinned["tarball"]["sha256"] = "f" * 64
    library.pin.write_text(json.dumps(pinned))
    out = tmp_path / "build" / f"{TAG}.tar.gz"

    status = build(library, out)

    err = capsys.readouterr().err
    assert status == 1
    assert "f" * 64 in err
    assert sha256(library.tarball.read_bytes()) in err
    assert sorted(path.name for path in out.parent.iterdir()) == ["families.txt"]


def test_an_hmmpress_that_isnt_the_pinned_version_writes_nothing_and_names_both(
    library: Library,
    tmp_path: Path,
    hmmpress: FakeHmmer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    hmmpress("3.3.2")
    out = tmp_path / "build" / f"{TAG}.tar.gz"

    status = build(library, out)

    err = capsys.readouterr().err
    assert status == 1
    assert "3.3.2" in err
    assert "3.4" in err
    assert sorted(path.name for path in out.parent.iterdir()) == ["families.txt"]


@pytest.mark.parametrize("families", ["PTHR77777\n", "PTHR9999\n"])
def test_a_family_that_isnt_in_the_library_or_isnt_a_family_writes_nothing(
    families: str,
    library: Library,
    tmp_path: Path,
    hmmpress: FakeHmmer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    hmmpress("3.4")
    out = tmp_path / "build" / f"{TAG}.tar.gz"

    assert build(library, out, families) == 1

    assert families.strip() in capsys.readouterr().err
    assert sorted(path.name for path in out.parent.iterdir()) == ["families.txt"]


@pytest.mark.tools("hmmpress")
def test_two_builds_are_byte_identical(library: Library, tmp_path: Path) -> None:
    first = tmp_path / "first" / f"{TAG}.tar.gz"
    second = tmp_path / "second" / f"{TAG}.tar.gz"

    assert build(library, first) == 0
    assert build(library, second) == 0

    assert first.read_bytes() == second.read_bytes()
    assert unpacked(first)["hmmscore/19/globals/binHmm.h3i"][:4] == b"\xd3\xd3\xc9\xb3"


# fetch and verify


@dataclass(frozen=True)
class Sample:
    tarball: Path
    manifest: Path


@pytest.fixture
def sample(library: Library, tmp_path: Path, hmmpress: FakeHmmer) -> Sample:
    """The sample built from the clean library, and a manifest whose URL can't be reached."""
    hmmpress("3.4")
    out = tmp_path / "build" / f"{TAG}.tar.gz"
    assert build(library, out) == 0
    return Sample(out, with_asset(out.with_suffix(".json"), tmp_path / "offline.json"))


def with_asset(manifest: Path, path: Path, **asset: object) -> Path:
    """A copy of `manifest` at `path`, its URL one that fails, and other asset fields changed."""
    content = json.loads(manifest.read_text())
    content["asset"].update({"url": "https://localhost:9/sample.tar.gz", **asset})
    path.write_text(json.dumps(content))
    return path


def snapshot(folder: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(folder)): path.read_bytes() if path.is_file() else b""
        for path in sorted(folder.rglob("*"))
    }


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    path = tmp_path / "data"
    path.mkdir()
    return path


def fetch(*args: str) -> int:
    return main(["hmmscore", "sample", "fetch", *args])


def verify(*args: str) -> int:
    return main(["hmmscore", "sample", "verify", *args])


def test_a_fresh_fetch_unpacks_every_file_and_checks_it(
    sample: Sample, folder: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = fetch(
        "--data-dir", str(folder), "--manifest", str(sample.manifest), "--from", str(sample.tarball)
    )

    assert status == 0
    assert "fetched" in capsys.readouterr().out
    for name, digest in json.loads(sample.manifest.read_text())["files"].items():
        assert sha256((folder / name).read_bytes()) == digest
    assert sorted(path.name for path in folder.iterdir()) == ["hmmscore"]
    assert verify("--data-dir", str(folder), "--manifest", str(sample.manifest)) == 0


def test_a_fetch_into_a_folder_that_already_matches_downloads_nothing(
    sample: Sample, folder: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = ["--data-dir", str(folder), "--manifest", str(sample.manifest)]
    assert fetch(*args, "--from", str(sample.tarball)) == 0
    capsys.readouterr()

    # No --from, and the manifest's URL can't be reached: a download would fail.
    status = fetch(*args)

    assert status == 0
    assert "nothing to fetch" in capsys.readouterr().out


def test_a_wrong_checksum_unpacks_nothing_and_names_both(
    sample: Sample, folder: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    wrong = with_asset(sample.manifest, tmp_path / "wrong.json", sha256="f" * 64)

    status = fetch(
        "--data-dir", str(folder), "--manifest", str(wrong), "--from", str(sample.tarball)
    )

    err = capsys.readouterr().err
    assert status == 1
    assert "f" * 64 in err
    assert sha256(sample.tarball.read_bytes()) in err
    assert snapshot(folder) == {}


def unsafe_tarball(path: Path, name: str, kind: bytes) -> Path:
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
        ("/hmmscore/absolute", tarfile.REGTYPE),
        ("hmmscore/../../escape", tarfile.REGTYPE),
        ("hmmscore/19/link", tarfile.SYMTYPE),
        ("csnp/9/file", tarfile.REGTYPE),
    ],
)
def test_an_unsafe_member_unpacks_nothing_and_is_named(
    name: str,
    kind: bytes,
    sample: Sample,
    folder: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tarball = unsafe_tarball(tmp_path / "unsafe.tar.gz", name, kind)
    digest = sha256(tarball.read_bytes())
    manifest = with_asset(sample.manifest, tmp_path / "unsafe.json", sha256=digest)

    status = fetch("--data-dir", str(folder), "--manifest", str(manifest), "--from", str(tarball))

    assert status == 1
    assert repr(name) in capsys.readouterr().err
    assert snapshot(folder) == {}
    assert not (tmp_path / "escape").exists()


def test_an_http_url_is_refused(
    sample: Sample, folder: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plain = with_asset(sample.manifest, tmp_path / "http.json", url="http://example.org/s.tar.gz")

    status = fetch("--data-dir", str(folder), "--manifest", str(plain))

    assert status == 1
    assert "only https" in capsys.readouterr().err
    assert snapshot(folder) == {}


def test_a_failed_fetch_leaves_the_data_folder_as_it_was(
    sample: Sample, folder: Path, tmp_path: Path
) -> None:
    args = ["--data-dir", str(folder), "--manifest", str(sample.manifest)]
    assert fetch(*args, "--from", str(sample.tarball)) == 0
    names = folder / "hmmscore" / "19" / "globals" / "names.tab"
    names.write_bytes(b"changed\n")
    before = snapshot(folder)
    wrong = with_asset(sample.manifest, tmp_path / "wrong.json", sha256="f" * 64)

    assert (
        fetch("--data-dir", str(folder), "--manifest", str(wrong), "--from", str(sample.tarball))
        == 1
    )

    assert snapshot(folder) == before


def test_a_failed_fetch_doesnt_leave_a_folder_it_created(sample: Sample, tmp_path: Path) -> None:
    folder = tmp_path / "new-data"
    plain = with_asset(sample.manifest, tmp_path / "http.json", url="http://example.org/s.tar.gz")

    assert fetch("--data-dir", str(folder), "--manifest", str(plain)) == 1
    assert not folder.exists()


def test_verify_lists_a_changed_file_and_fails(
    sample: Sample, folder: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = ["--data-dir", str(folder), "--manifest", str(sample.manifest)]
    assert fetch(*args, "--from", str(sample.tarball)) == 0
    model = folder / "hmmscore" / "19" / SF2_MODEL
    content = bytearray(model.read_bytes())
    content[-2] ^= 1
    model.write_bytes(bytes(content))
    capsys.readouterr()

    status = verify(*args)

    assert status == 1
    assert capsys.readouterr().out == f"differs: hmmscore/19/{SF2_MODEL}\n"


def test_a_fetch_replaces_a_changed_file(sample: Sample, folder: Path) -> None:
    args = ["--data-dir", str(folder), "--manifest", str(sample.manifest)]
    assert fetch(*args, "--from", str(sample.tarball)) == 0
    model = folder / "hmmscore" / "19" / SF2_MODEL
    model.write_bytes(b"changed\n")

    assert fetch(*args, "--from", str(sample.tarball)) == 0
    assert model.read_bytes() == data(SF2_MODEL)
