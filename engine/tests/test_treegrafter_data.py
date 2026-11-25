import hashlib
import io
import json
import re
import shutil
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import IO, NoReturn

import pytest
from treegrafter_fixtures import (
    BINHMM,
    PREFIX,
    PRESSED,
    README,
    annotation_file,
    annotation_lines,
    kept,
    library_files,
    library_tarball,
    model,
    release_readme,
)

from panther_engine.cli import main
from panther_engine.core.data import MissingDataError
from panther_engine.treegrafter import (
    DATA_VERSION,
    AnnotationRelease,
    annotations,
    check_data,
    data,
)

URL = "https://data.example.org/TreeGrafter/PANTHER19.0_data_trees_hmms_only.tar.gz"


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def library_list(files: dict[str, bytes]) -> bytes:
    """library.sha256 as sha256sum writes it, for the kept files of `files`, sorted by path."""
    kept_files = kept(files)
    return b"".join(f"{sha256(kept_files[path])}  {path}\n".encode() for path in sorted(kept_files))


def manifest(tarball: Path, out: Path, *extra: str) -> int:
    args = ["treegrafter", "data", "manifest", str(tarball), "--url", URL, "--manifest", str(out)]
    return main([*args, *extra])


# manifest


def test_the_manifest_pins_the_tarball_its_prefix_families_and_list(tmp_path: Path) -> None:
    files = library_files()
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
    assert pinned["families"] == 3
    assert pinned["files"] == {"treegrafter/19/library.sha256": sha256(library_list(files))}
    assert pinned["releases"] == {}


def test_the_list_holds_binhmm_and_three_tree_files_a_family_sorted(tmp_path: Path) -> None:
    files = library_files()
    hashed = data.hash_library(library_tarball(tmp_path / "library.tgz", files), PREFIX)

    listing = data.library_list(hashed.files).decode().splitlines()

    # Sorted by path as bytes, so Tree_MSF/ comes before famhmm/.
    assert [line.partition("  ")[2] for line in listing] == [
        *(
            f"Tree_MSF/{family}{suffix}"
            for family in ("PTHR10000", "PTHR10001", "PTHR10002")
            for suffix in (".AN.fasta", ".bifurcate.newick", ".newick")
        ),
        BINHMM,
    ]
    # The skipped files: the pressed binHmm, the .tree files and the PAINT README.
    assert not set(hashed.files) & {README, *PRESSED, "Tree_MSF/PTHR10000.tree"}


def test_two_manifests_of_the_same_tarball_are_byte_identical(tmp_path: Path) -> None:
    tarball = library_tarball(tmp_path / "library.tgz", library_files())
    first, second = tmp_path / "first.json", tmp_path / "second.json"

    assert manifest(tarball, first) == 0
    assert manifest(tarball, second) == 0

    assert first.read_bytes() == second.read_bytes()


def test_a_new_library_pin_keeps_the_releases_already_pinned(tmp_path: Path) -> None:
    tarball = library_tarball(tmp_path / "library.tgz", library_files())
    out = tmp_path / "data.json"
    assert manifest(tarball, out) == 0
    pinned = json.loads(out.read_text())
    release = {"url": "u", "bytes": 1, "sha256": "0" * 64, "go_release": "2026-08-05"}
    pinned["releases"] = {"2026-08-28": {**release, "prepared": "1" * 64}}
    out.write_text(json.dumps(pinned))

    assert manifest(tarball, out) == 0

    assert json.loads(out.read_text())["releases"] == pinned["releases"]


@pytest.mark.parametrize(
    ("member", "named"),
    [
        ((PREFIX + "Tree_MSF/notes.txt", b"note\n"), "Tree_MSF/notes.txt"),
        ((PREFIX + "famhmm/binHmm.old", b"x\n"), "famhmm/binHmm.old"),
        (("elsewhere/file", b"x\n"), "elsewhere/file"),
        ((PREFIX + "../escape", b"x\n"), "../escape"),
    ],
)
def test_an_unexpected_member_writes_nothing_and_is_named(
    member: tuple[str, bytes], named: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tarball = library_tarball(tmp_path / "library.tgz", library_files(), extra=[member])
    out = tmp_path / "data.json"
    out.write_text("the earlier manifest\n")

    status = manifest(tarball, out)

    assert status == 1
    assert named in capsys.readouterr().err
    assert out.read_text() == "the earlier manifest\n"


@pytest.mark.parametrize("suffix", [".AN.fasta", ".bifurcate.newick", ".newick"])
def test_a_family_missing_a_tree_file_writes_nothing_and_is_named(
    suffix: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = library_files()
    del files[f"Tree_MSF/PTHR10001{suffix}"]
    tarball = library_tarball(tmp_path / "library.tgz", files)
    out = tmp_path / "data.json"

    status = manifest(tarball, out)

    assert status == 1
    assert f"PTHR10001 lacks Tree_MSF/PTHR10001{suffix}" in capsys.readouterr().err
    assert not out.exists()


def test_a_library_without_binhmm_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = library_files()
    del files[BINHMM]
    out = tmp_path / "data.json"

    assert manifest(library_tarball(tmp_path / "library.tgz", files), out) == 1

    assert f"no {BINHMM}" in capsys.readouterr().err
    assert not out.exists()


def test_the_folders_the_prefix_is_in_are_allowed(tmp_path: Path) -> None:
    tarball = library_tarball(
        tmp_path / "library.tgz", library_files(), prefix="x/" + PREFIX, folders=["x"]
    )

    assert manifest(tarball, tmp_path / "data.json", "--prefix", "x/" + PREFIX) == 0


def test_a_file_that_isnt_a_gzipped_tar_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tarball = tmp_path / "library.tgz"
    tarball.write_bytes(b"not a tarball")

    assert manifest(tarball, tmp_path / "data.json") == 1

    assert "can't read" in capsys.readouterr().err
    assert not (tmp_path / "data.json").exists()


# fetching the library


@dataclass(frozen=True)
class Library:
    tarball: Path
    pin: Path
    files: dict[str, bytes]


@pytest.fixture
def library(tmp_path: Path) -> Library:
    """The hand-made library's tarball, and its pin, written by `data manifest`."""
    files = library_files()
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

    monkeypatch.setattr(data, "open_https", stub)
    return urls


def refuse(url: str) -> NoReturn:
    pytest.fail(f"downloaded {url}")


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """open_https fails the test if it's called."""
    monkeypatch.setattr(data, "open_https", refuse)


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    path = tmp_path / "data"
    path.mkdir()
    return path


def snapshot(path: Path) -> dict[str, bytes]:
    return {
        str(each.relative_to(path)): each.read_bytes() if each.is_file() else b""
        for each in sorted(path.rglob("*"))
    }


def library_snapshot(files: dict[str, bytes]) -> dict[str, bytes]:
    """What a fetch leaves under treegrafter/19/: the kept files, their folders, library.sha256."""
    return {
        "Tree_MSF": b"",
        "famhmm": b"",
        **kept(files),
        "library.sha256": library_list(files),
    }


def test_a_fresh_fetch_downloads_keeps_the_layout_and_checks_it(
    library: Library, served: list[str], folder: Path
) -> None:
    assert data.fetch_library(folder, manifest=library.pin) is True

    assert served == [URL]
    assert snapshot(folder / "treegrafter" / "19") == library_snapshot(library.files)
    assert sorted(path.name for path in folder.iterdir()) == ["treegrafter"]
    assert data.verify_library(folder, manifest=library.pin).ok


def test_the_list_checks_by_hand(library: Library, offline: None, folder: Path) -> None:
    data.fetch_library(folder, manifest=library.pin, tarball=library.tarball)
    root = folder / "treegrafter" / "19"

    for line in (root / "library.sha256").read_text().splitlines():
        digest, _, path = line.partition("  ")
        assert sha256((root / path).read_bytes()) == digest


def test_a_local_copy_is_checked_and_used_without_the_network(
    library: Library, offline: None, folder: Path
) -> None:
    assert data.fetch_library(folder, manifest=library.pin, tarball=library.tarball) is True

    assert snapshot(folder / "treegrafter" / "19") == library_snapshot(library.files)


def test_a_folder_that_already_matches_downloads_nothing(
    library: Library, offline: None, folder: Path
) -> None:
    data.fetch_library(folder, manifest=library.pin, tarball=library.tarball)

    assert data.fetch_library(folder, manifest=library.pin) is False


def test_a_wrong_checksum_writes_nothing_and_names_both(
    library: Library, offline: None, folder: Path, tmp_path: Path
) -> None:
    other = library_files()
    other["Tree_MSF/PTHR10000.newick"] = b"(AN1:0.1,AN2:0.2)AN0;\n"
    tarball = library_tarball(tmp_path / "other.tgz", other)
    pinned = json.loads(library.pin.read_text())["tarball"]["sha256"]

    with pytest.raises(data.TreegrafterDataError) as caught:
        data.fetch_library(folder, manifest=library.pin, tarball=tarball)

    assert sha256(tarball.read_bytes()) in str(caught.value)
    assert pinned in str(caught.value)
    assert list(folder.iterdir()) == []


@pytest.mark.parametrize(
    ("member", "named"),
    [
        ((PREFIX + "Tree_MSF/notes.txt", b"note\n"), "Tree_MSF/notes.txt"),
        ((PREFIX + "Tree_MSF/../../escape", b"x\n"), "escape"),
    ],
)
def test_an_unexpected_or_unsafe_member_writes_nothing_and_is_named(
    member: tuple[str, bytes],
    named: str,
    library: Library,
    offline: None,
    folder: Path,
    tmp_path: Path,
) -> None:
    tarball = library_tarball(tmp_path / "bad.tgz", library.files, extra=[member])

    with pytest.raises(data.TreegrafterDataError, match=named):
        data.fetch_library(folder, manifest=library.pin, tarball=tarball)

    assert list(folder.iterdir()) == []
    assert not (tmp_path / "escape").exists()


def test_a_failed_fetch_removes_a_data_folder_it_created(
    library: Library, offline: None, tmp_path: Path
) -> None:
    folder = tmp_path / "new"
    broken = tmp_path / "broken.tgz"
    broken.write_bytes(b"not a tarball")

    with pytest.raises(data.TreegrafterDataError):
        data.fetch_library(folder, manifest=library.pin, tarball=broken)

    assert not folder.exists()


def test_a_fetch_replaces_a_changed_file(library: Library, offline: None, folder: Path) -> None:
    data.fetch_library(folder, manifest=library.pin, tarball=library.tarball)
    changed = folder / "treegrafter" / "19" / "Tree_MSF" / "PTHR10000.AN.fasta"
    changed.write_bytes(b">AN2\nXXXX\n")

    assert data.fetch_library(folder, manifest=library.pin, tarball=library.tarball) is True

    assert changed.read_bytes() == library.files["Tree_MSF/PTHR10000.AN.fasta"]


# annotation releases

RELEASE = "2026-08-28"
OLDER = "2026-06-02"


@dataclass(frozen=True)
class Releases:
    """A data folder holding the hand-made library, a pin for it and two releases, and the
    releases' files: RELEASE's every node in SF1, OLDER's in SF2."""

    folder: Path
    pin: Path
    files: dict[str, Path]


def pin_release(date: str, file: Path, readme: Path, pin: Path, folder: Path, *extra: str) -> int:
    args = ["treegrafter", "data", "manifest", "--release", date, str(file)]
    return main(
        [*args, "--readme", str(readme), "--manifest", str(pin), "--data-dir", str(folder), *extra]
    )


def fetch(releases: Releases, *args: str) -> int:
    common = ["--data-dir", str(releases.folder), "--manifest", str(releases.pin)]
    return main(["treegrafter", "data", "fetch", *common, *args])


@pytest.fixture
def releases(library: Library, offline: None, folder: Path, tmp_path: Path) -> Releases:
    data.fetch_library(folder, manifest=library.pin, tarball=library.tarball)
    files: dict[str, Path] = {}
    for date, subfamily, go_release in (
        (RELEASE, "SF1", "2026-08-05"),
        (OLDER, "SF2", "2026-04-28"),
    ):
        files[date] = annotation_file(
            tmp_path / f"{date}.txt.gz", annotation_lines(subfamily=subfamily)
        )
        readme = tmp_path / f"{date}.README"
        readme.write_bytes(release_readme(go_release))
        assert pin_release(date, files[date], readme, library.pin, folder) == 0
    return Releases(folder, library.pin, files)


def annotations_folder(releases: Releases) -> Path:
    return releases.folder / "treegrafter" / "19" / "annotations"


def active(releases: Releases) -> str:
    return (annotations_folder(releases) / "active").read_text()


def test_a_release_pin_has_its_file_go_release_and_prepared_list(
    releases: Releases,
) -> None:
    pinned = json.loads(releases.pin.read_text())["releases"][RELEASE]
    content = releases.files[RELEASE].read_bytes()

    assert pinned["url"] == (
        "https://data.pantherdb.org/ftp/downloads/paint/19.0/2026-08-28/"
        "PAINT_TreeGrafter_Annotations_TOTAL.txt.gz"
    )
    assert (pinned["bytes"], pinned["sha256"]) == (len(content), sha256(content))
    assert pinned["go_release"] == "2026-08-05"
    assert len(pinned["prepared"]) == 64
    # Pinning prepares in a temporary folder, and leaves the data folder's annotations alone.
    assert not annotations_folder(releases).exists()


def test_a_pinned_date_ends_prepared_and_active(
    releases: Releases, capsys: pytest.CaptureFixture[str]
) -> None:
    status = fetch(
        releases, "--annotations", RELEASE, "--annotation-file", str(releases.files[RELEASE])
    )

    assert status == 0
    prepared = annotations_folder(releases) / RELEASE
    assert sorted(path.name for path in prepared.iterdir()) == [
        "PTHR10000.json",
        "PTHR10001.json",
        "PTHR10002.json",
        "prepared.sha256",
    ]
    entries = json.loads((prepared / "PTHR10000.json").read_text())
    assert entries["AN1"] == ["PTHR10000:SF1", "GO:0005515,GO:0008150", "PC00052", "PTN000000002"]
    assert active(releases) == f"{RELEASE}\n"
    assert f"release {RELEASE} is active" in capsys.readouterr().out
    assert data.verify_folder(releases.folder, manifest=releases.pin).ok


def test_a_wrong_release_checksum_changes_nothing_and_names_both(
    releases: Releases, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    other = annotation_file(tmp_path / "other.txt.gz", annotation_lines(subfamily="SF9"))

    status = fetch(releases, "--annotations", RELEASE, "--annotation-file", str(other))

    err = capsys.readouterr().err
    assert status == 1
    assert sha256(other.read_bytes()) in err
    assert sha256(releases.files[RELEASE].read_bytes()) in err
    assert not annotations_folder(releases).exists()


def test_an_unpinned_date_writes_nothing_and_lists_the_pinned_dates(
    releases: Releases, capsys: pytest.CaptureFixture[str]
) -> None:
    status = fetch(releases, "--annotations", "2026-01-05")

    err = capsys.readouterr().err
    assert status == 1
    assert f"pinned: {OLDER}, {RELEASE}" in err
    assert not annotations_folder(releases).exists()


def test_a_release_missing_a_node_isnt_pinned_and_names_it(
    library: Library,
    offline: None,
    folder: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    data.fetch_library(folder, manifest=library.pin, tarball=library.tarball)
    file = annotation_file(tmp_path / "gap.txt.gz", annotation_lines(skip=["PTHR10001:AN2"]))
    readme = tmp_path / "README"
    readme.write_bytes(release_readme("2026-08-05"))

    status = pin_release(RELEASE, file, readme, library.pin, folder)

    assert status == 1
    assert "PTHR10001:AN2" in capsys.readouterr().err
    assert json.loads(library.pin.read_text())["releases"] == {}


def test_a_release_missing_a_node_doesnt_become_active_and_names_it(
    releases: Releases, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        fetch(releases, "--annotations", OLDER, "--annotation-file", str(releases.files[OLDER]))
        == 0
    )
    # A pin for a file with a gap, as no `data manifest --release` would write.
    gap = annotation_file(tmp_path / "gap.txt.gz", annotation_lines(skip=["PTHR10002:AN4"]))
    pinned = json.loads(releases.pin.read_text())
    content = gap.read_bytes()
    pinned["releases"][RELEASE] |= {"bytes": len(content), "sha256": sha256(content)}
    releases.pin.write_text(json.dumps(pinned))

    status = fetch(releases, "--annotations", RELEASE, "--annotation-file", str(gap))

    assert status == 1
    assert "PTHR10002:AN4" in capsys.readouterr().err
    assert active(releases) == f"{OLDER}\n"
    assert sorted(path.name for path in annotations_folder(releases).iterdir()) == [OLDER, "active"]


def test_another_release_becomes_active_and_both_stay_prepared(releases: Releases) -> None:
    assert (
        fetch(releases, "--annotations", RELEASE, "--annotation-file", str(releases.files[RELEASE]))
        == 0
    )

    assert (
        fetch(releases, "--annotations", OLDER, "--annotation-file", str(releases.files[OLDER]))
        == 0
    )

    assert active(releases) == f"{OLDER}\n"
    assert sorted(path.name for path in annotations_folder(releases).iterdir()) == [
        OLDER,
        RELEASE,
        "active",
    ]
    assert data.verify_folder(releases.folder, manifest=releases.pin).ok


def test_a_prepared_release_becomes_active_again_without_a_download(
    releases: Releases, capsys: pytest.CaptureFixture[str]
) -> None:
    for date in (RELEASE, OLDER):
        assert (
            fetch(releases, "--annotations", date, "--annotation-file", str(releases.files[date]))
            == 0
        )
    capsys.readouterr()

    # offline: a download would fail the test.
    assert fetch(releases, "--annotations", RELEASE) == 0

    assert active(releases) == f"{RELEASE}\n"
    assert f"release {RELEASE} is already prepared" in capsys.readouterr().out


def test_a_fresh_fetch_puts_the_library_and_a_release_in_place(
    library: Library, offline: None, folder: Path, tmp_path: Path
) -> None:
    # Pinned against a library fetched elsewhere, then fetched into an empty folder.
    elsewhere = tmp_path / "elsewhere"
    data.fetch_library(elsewhere, manifest=library.pin, tarball=library.tarball)
    file = annotation_file(tmp_path / "release.txt.gz", annotation_lines())
    readme = tmp_path / "README"
    readme.write_bytes(release_readme("2026-08-05"))
    assert pin_release(RELEASE, file, readme, library.pin, elsewhere) == 0
    args = ["--data-dir", str(folder), "--manifest", str(library.pin)]

    status = main(
        [
            "treegrafter",
            "data",
            "fetch",
            *args,
            "--library",
            str(library.tarball),
            "--annotations",
            RELEASE,
            "--annotation-file",
            str(file),
        ]
    )

    assert status == 0
    assert data.verify_folder(folder, manifest=library.pin).ok


# the current release


@dataclass(frozen=True)
class Paint:
    """What open_https serves for paint/current/, by URL, and the URLs it was asked for."""

    served: dict[str, bytes]
    asked: list[str]


@pytest.fixture
def paint(releases: Releases, monkeypatch: pytest.MonkeyPatch) -> Paint:
    """open_https serves paint/current/, holding RELEASE's file and README to begin with."""
    paint = Paint(
        {
            data.CURRENT_URL: releases.files[RELEASE].read_bytes(),
            data.CURRENT_README_URL: release_readme("2026-08-05"),
        },
        [],
    )

    @contextmanager
    def stub(url: str) -> Generator[IO[bytes]]:
        paint.asked.append(url)
        if url not in paint.served:
            pytest.fail(f"downloaded {url}")
        yield io.BytesIO(paint.served[url])

    monkeypatch.setattr(data, "open_https", stub)
    return paint


def test_a_pinned_current_resolves_to_its_date(
    releases: Releases, paint: Paint, capsys: pytest.CaptureFixture[str]
) -> None:
    status = fetch(releases)

    assert status == 0
    assert "current is release 2026-08-28" in capsys.readouterr().out
    assert active(releases) == f"{RELEASE}\n"
    # The file paint/current/ served is the one prepared: the dated URL isn't downloaded.
    assert paint.asked == [data.CURRENT_URL, data.CURRENT_README_URL]


def test_a_current_that_has_moved_on_writes_nothing_and_names_its_sha256_and_go_release(
    releases: Releases, paint: Paint, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    moved = annotation_file(tmp_path / "next.txt.gz", annotation_lines(subfamily="SF3"))
    paint.served[data.CURRENT_URL] = moved.read_bytes()
    paint.served[data.CURRENT_README_URL] = release_readme("2026-09-30")

    status = fetch(releases, "--annotations", "current")

    err = capsys.readouterr().err
    assert status == 1
    assert sha256(moved.read_bytes()) in err
    assert "GO release 2026-09-30" in err
    assert not annotations_folder(releases).exists()
    assert sorted(path.name for path in releases.folder.iterdir()) == ["treegrafter"]


def test_a_local_file_with_current_is_resolved_by_its_sha256(
    releases: Releases, capsys: pytest.CaptureFixture[str]
) -> None:
    # offline: a download would fail the test.
    status = fetch(releases, "--annotation-file", str(releases.files[OLDER]))

    assert status == 0
    assert f"current is release {OLDER}" in capsys.readouterr().out
    assert active(releases) == f"{OLDER}\n"


# verify, and the data check


@pytest.fixture
def fetched(releases: Releases) -> Releases:
    """The data folder with RELEASE prepared and active."""
    file = releases.files[RELEASE]
    assert fetch(releases, "--annotations", RELEASE, "--annotation-file", str(file)) == 0
    return releases


def verify_data(releases: Releases) -> int:
    common = ["--data-dir", str(releases.folder), "--manifest", str(releases.pin)]
    return main(["treegrafter", "data", "verify", *common])


def test_verify_passes_on_a_fetched_folder(
    fetched: Releases, capsys: pytest.CaptureFixture[str]
) -> None:
    assert verify_data(fetched) == 0
    assert "every file matches the pin" in capsys.readouterr().out


def test_verify_lists_a_changed_alignment_and_fails(
    fetched: Releases, capsys: pytest.CaptureFixture[str]
) -> None:
    changed = fetched.folder / "treegrafter" / "19" / "Tree_MSF" / "PTHR10000.AN.fasta"
    content = bytearray(changed.read_bytes())
    content[-2] = ord("W")
    changed.write_bytes(bytes(content))

    assert verify_data(fetched) == 1

    assert "differs: treegrafter/19/Tree_MSF/PTHR10000.AN.fasta" in capsys.readouterr().out


def test_verify_lists_a_changed_prepared_file_and_fails(
    fetched: Releases, capsys: pytest.CaptureFixture[str]
) -> None:
    changed = annotations_folder(fetched) / RELEASE / "PTHR10001.json"
    changed.write_text(changed.read_text().replace("SF1", "SF7"))

    assert verify_data(fetched) == 1

    assert f"differs: treegrafter/19/annotations/{RELEASE}/PTHR10001.json" in (
        capsys.readouterr().out
    )


def test_verify_lists_no_active_release_and_fails(
    releases: Releases, capsys: pytest.CaptureFixture[str]
) -> None:
    assert verify_data(releases) == 1

    assert "missing: treegrafter/19/annotations/active" in capsys.readouterr().out


def test_the_data_check_passes_on_a_fetched_folder_without_reading_the_library(
    fetched: Releases,
) -> None:
    library = fetched.folder / "treegrafter" / "19"
    # Unreadable: the check looks at names only.
    (library / "famhmm" / "binHmm").chmod(0)
    try:
        check_data(fetched.folder)
    finally:
        (library / "famhmm" / "binHmm").chmod(0o644)


@pytest.mark.parametrize(
    ("remove", "named"),
    [
        ("famhmm/binHmm", "famhmm/binHmm"),
        ("Tree_MSF", "Tree_MSF/"),
        ("annotations/active", "an active annotation release (annotations/active)"),
        (f"annotations/{RELEASE}", f"annotations/{RELEASE}/"),
    ],
)
def test_the_data_check_names_whats_missing(fetched: Releases, remove: str, named: str) -> None:
    target = fetched.folder / "treegrafter" / "19" / remove
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    with pytest.raises(MissingDataError, match=re.escape(named)):
        check_data(fetched.folder)


def test_the_active_release_is_named_with_its_go_release(fetched: Releases) -> None:
    assert annotations(fetched.folder, manifest=fetched.pin) == AnnotationRelease(
        RELEASE, "2026-08-05"
    )


def test_the_data_version_needs_no_data_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PANTHER_DATA_DIR", raising=False)

    assert DATA_VERSION == "19"


# the fixture


def build_fixture(releases: Releases, out: Path, *families: str) -> int:
    common = ["--data-dir", str(releases.folder), "--manifest", str(releases.pin)]
    file = str(releases.files[RELEASE])
    return main(
        [
            "treegrafter",
            "data",
            "fixture",
            *common,
            "--release",
            RELEASE,
            "--annotation-file",
            file,
            "--out",
            str(out),
            *families,
        ]
    )


def test_the_fixture_holds_the_families_models_trees_and_lines(
    fetched: Releases, tmp_path: Path
) -> None:
    out = tmp_path / "fixture"

    assert build_fixture(fetched, out, "PTHR10002", "PTHR10000") == 0

    files = snapshot(out)
    assert sorted(files) == [
        "PAINT_TreeGrafter_Annotations_TOTAL.txt",
        "README.md",
        "Tree_MSF",
        *(
            f"Tree_MSF/{family}{suffix}"
            for family in ("PTHR10000", "PTHR10002")
            for suffix in (".AN.fasta", ".bifurcate.newick", ".newick")
        ),
        "famhmm",
        "famhmm/binHmm",
        "fixture.json",
    ]
    assert files["famhmm/binHmm"] == model("PTHR10000") + model("PTHR10002")
    library = library_files()
    assert files["Tree_MSF/PTHR10002.newick"] == library["Tree_MSF/PTHR10002.newick"]
    lines = files["PAINT_TreeGrafter_Annotations_TOTAL.txt"].decode().splitlines(keepends=True)
    assert lines == [line for line in annotation_lines() if not line.startswith("PTHR10001")]
    readme = files["README.md"].decode()
    for path in ("famhmm/binHmm", "Tree_MSF/PTHR10000.newick"):
        assert f"`{path}`" in readme
        assert sha256(files[path]) in readme
    assert json.loads(files["fixture.json"])["release"] == RELEASE


def test_the_same_inputs_give_the_same_fixture(fetched: Releases, tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"

    assert build_fixture(fetched, first, "PTHR10000", "PTHR10001") == 0
    assert build_fixture(fetched, second, "PTHR10001", "PTHR10000") == 0

    assert snapshot(first) == snapshot(second)


def test_a_family_the_library_lacks_builds_no_fixture(
    fetched: Releases, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "fixture"

    assert build_fixture(fetched, out, "PTHR10000", "PTHR99999") == 1

    assert "PTHR99999" in capsys.readouterr().err
    assert not out.exists()


def test_an_installed_fixture_passes_the_data_check(fetched: Releases, tmp_path: Path) -> None:
    out = tmp_path / "fixture"
    assert build_fixture(fetched, out, "PTHR10000", "PTHR10001", "PTHR10002") == 0
    folder = tmp_path / "installed"

    data.install_fixture(out, folder)

    check_data(folder)
    assert (folder / "treegrafter" / "19" / "annotations" / "active").read_text() == f"{RELEASE}\n"


# the committed fixture

FIXTURE = Path(__file__).parent / "fixtures" / "treegrafter"


def test_the_committed_fixtures_files_have_its_readmes_sha256s() -> None:
    readme = (FIXTURE / "README.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| `([^`]+)` \| .* \| `([0-9a-f]{64})` \|$", readme, re.MULTILINE)

    assert len(rows) == 12
    for path, digest in rows:
        assert sha256((FIXTURE / path).read_bytes()) == digest, path


def test_the_committed_fixture_is_under_1_mb() -> None:
    assert sum(path.stat().st_size for path in FIXTURE.rglob("*") if path.is_file()) < 1_000_000


def test_the_committed_fixture_prepared_in_a_test_passes_the_data_check(tmp_path: Path) -> None:
    date = data.install_fixture(FIXTURE, tmp_path)

    check_data(tmp_path)
    assert annotations(tmp_path) == AnnotationRelease("2026-08-28", "2026-08-05")
    assert date == "2026-08-28"
