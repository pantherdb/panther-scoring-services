import hashlib
import json
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path

import pytest
from refmap_fixtures import (
    ORGANISMS,
    STATS_URL,
    TARBALL_URL,
    Release,
    make_release,
    stats_line,
    write_manifest,
)

from panther_engine.cli import main
from panther_engine.refmap import data as data_module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def release(tmp_path: Path) -> Release:
    return make_release(tmp_path / "release")


# data manifest


def test_the_manifest_pins_the_release_and_every_file(release: Release, tmp_path: Path) -> None:
    out = tmp_path / "out"

    assert write_manifest(release, out) == 0

    manifest = json.loads((out / "data.json").read_text())
    assert manifest["release"] == "2024-06-20"
    assert manifest["version"] == "19"
    assert manifest["tarball"] == {
        "url": TARBALL_URL,
        "sha256": sha256(release.tarball),
        "bytes": release.tarball.stat().st_size,
    }
    assert manifest["stats"] == {
        "url": STATS_URL,
        "sha256": sha256(release.stats),
        "bytes": release.stats.stat().st_size,
    }
    assert manifest["files"] == {
        "refmap/19/panther_classification/ECO57": hashlib.sha256(
            ORGANISMS["Escherichia_coli_O157:H7_ECO57"]
        ).hexdigest(),
        "refmap/19/panther_classification/ENDPU": hashlib.sha256(
            ORGANISMS["Endocarpon_pusillum_ENDPU"]
        ).hexdigest(),
        "refmap/19/panther_classification/PEA": hashlib.sha256(
            ORGANISMS["Pisum_sativum_PEA"]
        ).hexdigest(),
        "refmap/19/stats": sha256(release.stats),
    }


def test_the_organism_list_is_in_long_name_order_with_the_gene_counts(
    release: Release, tmp_path: Path
) -> None:
    out = tmp_path / "out"

    assert write_manifest(release, out) == 0

    assert json.loads((out / "organisms.json").read_text()) == [
        {
            "code": "ENDPU",
            "long_name": "Endocarpon_pusillum_ENDPU",
            "genes": 3,
            "genes_with_panther_id": 2,
        },
        {
            "code": "ECO57",
            "long_name": "Escherichia_coli_O157:H7_ECO57",
            "genes": 1,
            "genes_with_panther_id": 1,
        },
        {"code": "PEA", "long_name": "Pisum_sativum_PEA", "genes": 2, "genes_with_panther_id": 1},
    ]


def test_the_same_inputs_give_the_same_bytes(release: Release, tmp_path: Path) -> None:
    assert write_manifest(release, tmp_path / "one") == 0
    assert write_manifest(release, tmp_path / "two") == 0

    for name in ("data.json", "organisms.json"):
        first = (tmp_path / "one" / name).read_bytes()
        assert first == (tmp_path / "two" / name).read_bytes()
        assert first.endswith(b"}\n") or first.endswith(b"]\n")


def refused(release: Release, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> str:
    """Runs `data manifest`, expects it to fail and write nothing, and returns its stderr."""
    out = tmp_path / "out"

    status = write_manifest(release, out)

    assert status == 1
    assert list(out.iterdir()) == []
    return capsys.readouterr().err


def test_a_file_with_one_more_line_than_stats_counts_is_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stats = "".join(stats_line(name, content) for name, content in ORGANISMS.items())
    organisms = {**ORGANISMS, "Pisum_sativum_PEA": ORGANISMS["Pisum_sativum_PEA"] + b"P3\tNOHIT\n"}

    err = refused(make_release(tmp_path / "release", organisms, stats=stats), tmp_path, capsys)

    assert "Pisum_sativum_PEA" in err
    assert "Endocarpon" not in err


def test_a_file_with_a_different_mapped_count_is_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stats = "".join(stats_line(name, content) for name, content in ORGANISMS.items())
    organisms = {**ORGANISMS, "Pisum_sativum_PEA": b"P1\tPTHR00002:SF3\nP2\tPTHR00002\n"}

    err = refused(make_release(tmp_path / "release", organisms, stats=stats), tmp_path, capsys)

    assert "Pisum_sativum_PEA" in err


def test_two_long_names_ending_in_the_same_code_are_both_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    organisms = {**ORGANISMS, "Pisum_arvense_PEA": b"P9\tPTHR00009\n"}

    err = refused(make_release(tmp_path / "release", organisms), tmp_path, capsys)

    assert "Pisum_sativum_PEA" in err
    assert "Pisum_arvense_PEA" in err


@pytest.mark.parametrize("long_name", ["Some_thing_CON", "Some_thing_con", "Some_thing_LPT1"])
def test_a_device_name_or_a_lower_case_code_is_named(
    long_name: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    organisms = {**ORGANISMS, long_name: b"X1\tPTHR00009\n"}

    err = refused(make_release(tmp_path / "release", organisms), tmp_path, capsys)

    assert long_name in err


def test_a_member_with_no_stats_line_is_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    organisms = {**ORGANISMS, "Extra_organism_EXTRA": b"X1\tPTHR00009\n"}
    stats = "".join(stats_line(name, content) for name, content in ORGANISMS.items())

    err = refused(make_release(tmp_path / "release", organisms, stats=stats), tmp_path, capsys)

    assert "Extra_organism_EXTRA" in err


def test_a_stats_line_with_no_member_is_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stats = "".join(stats_line(name, content) for name, content in ORGANISMS.items())
    stats += "Missing_organism_MISS\t1\t1\n"

    err = refused(make_release(tmp_path / "release", stats=stats), tmp_path, capsys)

    assert "Missing_organism_MISS" in err


@pytest.mark.parametrize(
    "name",
    [
        "panther_classification/Pisum_sativum_PEA",
        "Pisum_sativum_PEA",
        "panther_classifications/a/b",
    ],
)
def test_a_member_outside_the_folder_is_named(
    name: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    members = [(f"panther_classifications/{long}", content) for long, content in ORGANISMS.items()]
    members.append((name, b"X1\tPTHR00009\n"))

    err = refused(make_release(tmp_path / "release", members=members), tmp_path, capsys)

    assert repr(name) in err


def test_a_link_is_named(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    link = tarfile.TarInfo("panther_classifications/Pisum_sativum_PEA")
    link.type = tarfile.SYMTYPE
    link.linkname = "/etc/passwd"
    members: list[tarfile.TarInfo | tuple[str, bytes]] = [
        (f"panther_classifications/{long}", content)
        for long, content in ORGANISMS.items()
        if long != "Pisum_sativum_PEA"
    ]
    members.append(link)

    err = refused(make_release(tmp_path / "release", members=members), tmp_path, capsys)

    assert "'panther_classifications/Pisum_sativum_PEA'" in err


@pytest.mark.parametrize("count", ["many", "\u00b2", "\u0663", "-1", ""])
def test_a_count_that_isnt_ascii_digits_is_named(
    count: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stats = "".join(stats_line(name, content) for name, content in ORGANISMS.items())
    stats += f"Broken_line_BROKE\t{count}\t1\n"

    err = refused(make_release(tmp_path / "release", stats=stats), tmp_path, capsys)

    assert "Broken_line_BROKE" in err
    assert "Traceback" not in err


def test_a_malformed_stats_line_is_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    stats = "".join(stats_line(name, content) for name, content in ORGANISMS.items())
    stats += "Broken_line_BROKE\tmany\t1\n"

    err = refused(make_release(tmp_path / "release", stats=stats), tmp_path, capsys)

    assert "Broken_line_BROKE" in err


# data fetch and verify


@dataclass(frozen=True)
class Pinned:
    """A small release, and the manifest and organism list `data manifest` wrote for it."""

    release: Release
    manifest: Path
    organisms: Path


@pytest.fixture
def pinned(release: Release, tmp_path: Path) -> Pinned:
    out = tmp_path / "pins"
    assert write_manifest(release, out) == 0
    return Pinned(release, out / "data.json", out / "organisms.json")


@pytest.fixture
def data(tmp_path: Path) -> Path:
    folder = tmp_path / "data"
    folder.mkdir()
    return folder


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Any download fails the test."""

    def download(url: str, target: Path) -> Path:
        pytest.fail(f"downloaded {url}")

    monkeypatch.setattr(data_module, "download", download)


def fetch(pinned: Pinned, data: Path, *args: str, manifest: Path | None = None) -> int:
    return main(
        [
            "refmap",
            "data",
            "fetch",
            "--data-dir",
            str(data),
            "--manifest",
            str(manifest or pinned.manifest),
            "--organisms",
            str(pinned.organisms),
            *args,
        ]
    )


def local(pinned: Pinned) -> list[str]:
    return ["--tarball", str(pinned.release.tarball), "--stats", str(pinned.release.stats)]


def verify(pinned: Pinned, data: Path) -> int:
    return main(
        ["refmap", "data", "verify", "--data-dir", str(data), "--manifest", str(pinned.manifest)]
    )


def snapshot(folder: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(folder)): path.read_bytes() if path.is_file() else b""
        for path in sorted(folder.rglob("*"))
    }


def with_pin(pinned: Pinned, path: Path, name: str, **fields: object) -> Path:
    """A copy of the manifest, at `path`, with some of the tarball's or stats's pin changed."""
    content = json.loads(pinned.manifest.read_text())
    content[name].update(fields)
    path.write_text(json.dumps(content))
    return path


def test_a_fresh_fetch_downloads_the_pinned_urls_and_saves_each_file_under_its_code(
    pinned: Pinned,
    data: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    urls: list[str] = []
    sources = {TARBALL_URL: pinned.release.tarball, STATS_URL: pinned.release.stats}

    def download(url: str, target: Path) -> Path:
        urls.append(url)
        shutil.copyfile(sources[url], target)
        return target

    monkeypatch.setattr(data_module, "download", download)

    status = fetch(pinned, data)

    assert status == 0
    assert "fetched" in capsys.readouterr().out
    assert sorted(urls) == sorted(sources)
    assert snapshot(data) == {
        "refmap": b"",
        "refmap/19": b"",
        "refmap/19/panther_classification": b"",
        "refmap/19/panther_classification/ECO57": ORGANISMS["Escherichia_coli_O157:H7_ECO57"],
        "refmap/19/panther_classification/ENDPU": ORGANISMS["Endocarpon_pusillum_ENDPU"],
        "refmap/19/panther_classification/PEA": ORGANISMS["Pisum_sativum_PEA"],
        "refmap/19/stats": pinned.release.stats.read_bytes(),
    }
    assert verify(pinned, data) == 0


def test_no_file_name_holds_a_colon(pinned: Pinned, data: Path, no_network: None) -> None:
    assert fetch(pinned, data, *local(pinned)) == 0

    names = [path.name for path in data.rglob("*")]
    assert "ECO57" in names
    assert not [name for name in names if set(name) & set(':<>"/\\|?*')]


def test_local_copies_are_used_without_the_network(
    pinned: Pinned, data: Path, no_network: None
) -> None:
    assert fetch(pinned, data, *local(pinned)) == 0
    assert verify(pinned, data) == 0


def test_a_folder_that_already_matches_downloads_nothing(
    pinned: Pinned, data: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert fetch(pinned, data, *local(pinned)) == 0
    capsys.readouterr()

    def download(url: str, target: Path) -> Path:
        pytest.fail(f"downloaded {url}")

    monkeypatch.setattr(data_module, "download", download)

    assert fetch(pinned, data) == 0
    assert "nothing to fetch" in capsys.readouterr().out


@pytest.mark.parametrize("name", ["tarball", "stats"])
@pytest.mark.parametrize(("field", "wrong"), [("sha256", "f" * 64), ("bytes", 12345)])
def test_a_wrong_pin_writes_nothing_and_names_both_values(
    name: str,
    field: str,
    wrong: object,
    pinned: Pinned,
    data: Path,
    tmp_path: Path,
    no_network: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = pinned.release.tarball if name == "tarball" else pinned.release.stats
    actual = sha256(source) if field == "sha256" else source.stat().st_size
    manifest = with_pin(pinned, tmp_path / "wrong.json", name, **{field: wrong})

    status = fetch(pinned, data, *local(pinned), manifest=manifest)

    err = capsys.readouterr().err
    assert status == 1
    assert str(wrong) in err
    assert str(actual) in err
    assert snapshot(data) == {}


def bad_release(
    pinned: Pinned, tmp_path: Path, member: tarfile.TarInfo | tuple[str, bytes]
) -> Path:
    """The release with one more member, and a manifest pinning its tarball."""
    members: list[tarfile.TarInfo | tuple[str, bytes]] = [
        (f"panther_classifications/{long}", content) for long, content in ORGANISMS.items()
    ]
    members.append(member)
    bad = make_release(tmp_path / "bad", members=members)
    return with_pin(
        pinned,
        tmp_path / "bad.json",
        "tarball",
        sha256=sha256(bad.tarball),
        bytes=bad.tarball.stat().st_size,
    )


def link(name: str) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type = tarfile.SYMTYPE
    info.linkname = "/etc/passwd"
    return info


@pytest.mark.parametrize(
    "member",
    [
        link("panther_classifications/Pisum_sativum_PEA"),
        ("panther_classifications/Homo_sapiens_HUMAN", b"P04217\tPTHR1\n"),
        ("panther_classifications/../escape", b"x\n"),
        ("/etc/escape", b"x\n"),
    ],
    ids=["link", "not-listed", "dot-dot", "absolute"],
)
def test_an_unexpected_member_writes_nothing_and_is_named(
    member: tarfile.TarInfo | tuple[str, bytes],
    pinned: Pinned,
    data: Path,
    tmp_path: Path,
    no_network: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    name = member.name if isinstance(member, tarfile.TarInfo) else member[0]
    manifest = bad_release(pinned, tmp_path, member)
    bad = tmp_path / "bad" / "panther_classifications.tar.gz"

    status = fetch(
        pinned, data, "--tarball", str(bad), "--stats", str(pinned.release.stats), manifest=manifest
    )

    assert status == 1
    assert repr(name) in capsys.readouterr().err
    assert snapshot(data) == {}
    assert not (tmp_path / "escape").exists()


def test_a_failed_fetch_doesnt_leave_a_folder_it_created(
    pinned: Pinned, tmp_path: Path, no_network: None
) -> None:
    manifest = with_pin(pinned, tmp_path / "wrong.json", "tarball", sha256="f" * 64)
    folder = tmp_path / "new-data"

    assert fetch(pinned, folder, *local(pinned), manifest=manifest) == 1
    assert not folder.exists()


def test_verify_lists_a_changed_file_and_fails(
    pinned: Pinned, data: Path, no_network: None, capsys: pytest.CaptureFixture[str]
) -> None:
    assert fetch(pinned, data, *local(pinned)) == 0
    endpu = data / "refmap" / "19" / "panther_classification" / "ENDPU"
    content = bytearray(endpu.read_bytes())
    content[0] ^= 1
    endpu.write_bytes(bytes(content))
    capsys.readouterr()

    status = verify(pinned, data)

    assert status == 1
    assert capsys.readouterr().out == "differs: refmap/19/panther_classification/ENDPU\n"


def test_a_fetch_restores_a_changed_file_and_leaves_the_others(
    pinned: Pinned, data: Path, no_network: None
) -> None:
    assert fetch(pinned, data, *local(pinned)) == 0
    folder = data / "refmap" / "19" / "panther_classification"
    (folder / "ENDPU").write_bytes(b"changed\n")
    before = {path.name: path.stat().st_ino for path in folder.iterdir()}

    assert fetch(pinned, data, *local(pinned)) == 0

    assert (folder / "ENDPU").read_bytes() == ORGANISMS["Endocarpon_pusillum_ENDPU"]
    after = {path.name: path.stat().st_ino for path in folder.iterdir()}
    assert {name for name in after if after[name] != before[name]} == {"ENDPU"}
    assert verify(pinned, data) == 0


def test_without_a_data_folder_the_error_names_the_variable(
    pinned: Pinned, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PANTHER_DATA_DIR", raising=False)

    assert main(["refmap", "data", "verify", "--manifest", str(pinned.manifest)]) == 1
    assert "PANTHER_DATA_DIR" in capsys.readouterr().err
