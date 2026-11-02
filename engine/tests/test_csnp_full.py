"""The full cSNP data's manifest: building it from the archives, and checking a data folder
against it (`fix-csnp-blast-handling`, design.md, decisions 6 to 8)."""

import hashlib
import json
from pathlib import Path

import pytest
from csnp_fixtures import FAMILY, FIXTURES, family_files, make_tar

from panther_engine.cli import main
from panther_engine.core.manifest import checksums, read_manifest
from panther_engine.csnp import full, sample

README = """copyright (C) 2016 Paul Thomas
This file may be copied and redistributed freely, without advance permission,
provided that this Copyright statement is reproduced with each copy.

##########
PANTHER-PSEP SNP scoring tool - Version 1.01
"""
COPYRIGHT = README.partition("\n\n")[0].encode("utf-8") + b"\n"
# A stand-in for PANTHER9.blast.tar.gz: the database files, and the FASTA nothing reads.
BLAST_FILES = {
    "blast/blast.phr": b"headers\n",
    "blast/blast.pin": b"index\n",
    "blast/blast.psq": b"sequences\n",
    "blast/blast.fasta": b">P1\nMKV\n",
}


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_of(path: Path) -> str:
    return sha256(path.read_bytes())


@pytest.fixture
def inputs(tmp_path: Path) -> Path:
    folder = tmp_path / "inputs"
    folder.mkdir()
    make_tar(
        folder / "PAML_RST.tar.gz",
        [*family_files(FAMILY), *family_files("PTHR00003_1")],
    )
    make_tar(folder / "PANTHER9.blast.tar.gz", BLAST_FILES.items())
    (folder / "README.txt").write_text(README, encoding="utf-8")
    return folder


def build(inputs: Path, manifest: Path, **pins: str) -> int:
    """`csnp data manifest` on the fixture inputs, with each pin the input's own sha256 unless
    `pins` overrides it, such as `archive="0" * 64`."""
    archive, blast = inputs / "PAML_RST.tar.gz", inputs / "PANTHER9.blast.tar.gz"
    species = FIXTURES / "species.nhx"
    actual = {
        "archive": sha256_of(archive),
        "blast": sha256_of(blast),
        "species": sha256_of(species),
        "copyright": sha256(COPYRIGHT),
    }
    actual.update(pins)
    return main(
        [
            "csnp",
            "data",
            "manifest",
            str(archive),
            "--blast-archive",
            str(blast),
            "--species",
            str(species),
            "--readme",
            str(inputs / "README.txt"),
            "--manifest",
            str(manifest),
            *(arg for name, digest in actual.items() for arg in (f"--{name}-sha256", digest)),
        ]
    )


@pytest.fixture
def built(inputs: Path, tmp_path: Path) -> Path:
    """The manifest built from the fixture inputs."""
    manifest = tmp_path / "build" / "full.json"
    manifest.parent.mkdir()
    assert build(inputs, manifest) == 0
    return manifest


# The manifest


def test_two_builds_are_byte_identical(inputs: Path, built: Path, tmp_path: Path) -> None:
    again = tmp_path / "again.json"

    assert build(inputs, again) == 0

    assert again.read_bytes() == built.read_bytes()


def test_the_manifest_lists_the_library_the_database_the_species_tree_and_the_copyright(
    built: Path,
) -> None:

    manifest = json.loads(built.read_text(encoding="utf-8"))

    expected = {f"csnp/9/{name}": sha256(content) for name, content in family_files(FAMILY)}
    expected.update(
        {f"csnp/9/{name}": sha256(content) for name, content in family_files("PTHR00003_1")}
    )
    expected.update(
        {
            f"csnp/9/{name}": sha256(content)
            for name, content in BLAST_FILES.items()
            if name != "blast/blast.fasta"
        }
    )
    expected["csnp/9/species_pthr8_time.nhx"] = sha256_of(FIXTURES / "species.nhx")
    expected["csnp/9/PSEP-COPYRIGHT.txt"] = sha256(COPYRIGHT)
    assert manifest["files"] == expected
    assert list(manifest["files"]) == sorted(expected)


@pytest.mark.parametrize("pin", ["archive", "blast", "species", "copyright"])
def test_an_input_that_isnt_pinned_is_refused_and_nothing_is_written(
    inputs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], pin: str
) -> None:
    manifest = tmp_path / "full.json"
    pinned = "0" * 64

    status = build(inputs, manifest, **{pin: pinned})

    err = capsys.readouterr().err
    assert status == 1
    assert pinned in err
    assert not manifest.exists()


def test_the_error_for_an_archive_that_isnt_pinned_names_both_checksums(
    inputs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status = build(inputs, tmp_path / "full.json", archive="0" * 64)

    assert status == 1
    assert sha256_of(inputs / "PAML_RST.tar.gz") in capsys.readouterr().err


def test_a_blast_archive_without_the_database_is_refused(
    inputs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blast = make_tar(inputs / "PANTHER9.blast.tar.gz", [("blast/blast.fasta", b">P1\nMKV\n")])
    manifest = tmp_path / "full.json"

    assert build(inputs, manifest, blast=sha256_of(blast)) == 1
    assert "blast/blast.phr" in capsys.readouterr().err
    assert not manifest.exists()


def test_the_cli_reports_how_many_files_it_listed(
    inputs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert build(inputs, tmp_path / "full.json") == 0

    # 6 library files, 3 database files, the species tree and the copyright statement.
    assert "11 files" in capsys.readouterr().out


def test_a_member_outside_the_data_folder_is_refused(
    inputs: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive = make_tar(inputs / "PAML_RST.tar.gz", [("../PAML_RST/PTHR00001.paml", b"x\n")])
    manifest = tmp_path / "full.json"

    assert build(inputs, manifest, archive=sha256_of(archive)) == 1
    assert "../PAML_RST/PTHR00001.paml" in capsys.readouterr().err
    assert not manifest.exists()


# Verifying a data folder


def verify(data: Path, manifest: Path) -> int:
    return main(["csnp", "data", "verify", "--data-dir", str(data), "--manifest", str(manifest)])


def write_manifest(path: Path, files: dict[str, bytes]) -> Path:
    """A manifest at `path` listing `files`, paths relative to the data folder, by content."""
    content = {"files": {name: sha256(data) for name, data in sorted(files.items())}}
    path.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
    return path


def install(data: Path, files: dict[str, bytes]) -> None:
    for name, content in files.items():
        (data / name).parent.mkdir(parents=True, exist_ok=True)
        (data / name).write_bytes(content)


LISTED_FILES = {
    "csnp/9/PAML_RST/PTHR00001.paml": b"paml\n",
    "csnp/9/PAML_RST/PTHR00001.rst": b"rst\n",
    "csnp/9/blast/blast.psq": b"sequences\n",
    "csnp/9/species_pthr8_time.nhx": b"species\n",
}


def test_a_matching_folder_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    install(tmp_path / "data", LISTED_FILES)
    manifest = write_manifest(tmp_path / "full.json", LISTED_FILES)

    assert verify(tmp_path / "data", manifest) == 0
    assert "0 missing and 0 differing, of 4 listed files" in capsys.readouterr().out


def test_a_deleted_file_and_a_truncated_file_are_both_named(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = tmp_path / "data"
    install(data, LISTED_FILES)
    manifest = write_manifest(tmp_path / "full.json", LISTED_FILES)
    (data / "csnp/9/PAML_RST/PTHR00001.paml").unlink()
    (data / "csnp/9/PAML_RST/PTHR00001.rst").write_bytes(b"rs")

    assert verify(data, manifest) == 1

    out = capsys.readouterr().out
    assert "1 missing and 1 differing, of 4 listed files" in out
    assert "missing: csnp/9/PAML_RST/PTHR00001.paml" in out
    assert "differs: csnp/9/PAML_RST/PTHR00001.rst" in out


def test_a_folder_missing_30_files_reports_30_and_names_20(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = {f"csnp/9/PAML_RST/PTHR{number:05}.paml": b"paml\n" for number in range(31)}
    data = tmp_path / "data"
    install(data, {"csnp/9/PAML_RST/PTHR00000.paml": b"paml\n"})
    manifest = write_manifest(tmp_path / "full.json", files)

    assert verify(data, manifest) == 1

    out = capsys.readouterr().out
    assert "30 missing and 0 differing, of 31 listed files" in out
    named = [line for line in out.splitlines() if line.startswith("missing: csnp/")]
    assert named == [f"missing: csnp/9/PAML_RST/PTHR{number:05}.paml" for number in range(1, 21)]
    assert "missing: and 10 more" in out


def test_a_file_the_manifest_doesnt_list_is_ignored(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = tmp_path / "data"
    install(data, {**LISTED_FILES, "csnp/9/blast/blast.fasta": b">P1\nMKV\n"})
    manifest = write_manifest(tmp_path / "full.json", LISTED_FILES)

    assert verify(data, manifest) == 0
    assert "blast.fasta" not in capsys.readouterr().out


def test_verify_uses_the_engines_full_manifest_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    listed = len(checksums(read_manifest(full.MANIFEST)))

    assert main(["csnp", "data", "verify", "--data-dir", str(tmp_path)]) == 1

    assert f"{listed:,} missing and 0 differing, of {listed:,} listed files" in (
        capsys.readouterr().out
    )


# The committed manifest


def test_the_full_manifest_lists_every_sample_file_with_the_same_sha256() -> None:
    full_files = checksums(read_manifest(full.MANIFEST))
    sample_files = checksums(read_manifest(sample.MANIFEST))

    assert {path: full_files.get(path) for path in sample_files} == sample_files


def test_the_full_manifest_pins_the_same_sources_as_the_sample() -> None:
    full_manifest = read_manifest(full.MANIFEST)
    sample_manifest = read_manifest(sample.MANIFEST)

    for key in ("source", "blast", "species"):
        assert full_manifest[key] == sample_manifest[key]
