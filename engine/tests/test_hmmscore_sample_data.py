"""The hmmscore data sample, read with the strict readers and searched with `hmmscan`. Needs the
sample in the data folder."""

import json
import platform
import shutil
from pathlib import Path

import pytest

from panther_engine.core.archive import write_tarball
from panther_engine.core.manifest import sha256_file
from panther_engine.core.process import run_tool
from panther_engine.hmmscore import data, sample
from panther_engine.hmmscore.library import PREFIX, lines_of, read_model_file, read_names
from panther_engine.hmmscore.survey import survey

pytestmark = pytest.mark.data("hmmscore")

GOLDEN = Path(__file__).parent / "golden" / "hmmscore"
EXAMPLE = GOLDEN / "example" / "apoe.fasta"
# The engine image's architectures, by the names platform.machine() gives them. HMMER 3.4's
# hmmscan gives a few different numbers on each, so each has its own committed table.
ARCHITECTURES = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}
# The example's highest-scoring model on the full library, 439.0 bits
# (docs/parity/hmmscore-library-survey.md, "The Sample").
FULL_LIBRARY_BEST = "PTHR18976.SF2.pir"

MANIFEST = json.loads(sample.MANIFEST.read_text(encoding="utf-8"))
PIN = json.loads(data.MANIFEST.read_text(encoding="utf-8"))
MODEL_FILES = sorted(
    name.removeprefix(f"{sample.FOLDER}/") for name in MANIFEST["files"] if name.endswith(".hmm")
)
# The checks on families or models that found something in the full library
# (docs/parity/hmmscore-library-survey.md).
FULL_LIBRARY_FOUND = [
    "name-without-model",
    "model-legacy-id",
    "one-subfamily-copy",
    "binhmm-not-in-books",
]


def test_the_sample_matches_its_manifest(hmmscore_data: Path) -> None:
    mismatches = sample.verify_folder(hmmscore_data.parents[1])

    assert mismatches.missing == ()
    assert mismatches.differing == ()


def test_its_readme_is_the_pinned_librarys(hmmscore_data: Path) -> None:
    assert sha256_file(hmmscore_data / "README") == PIN["files"][f"{sample.FOLDER}/README"]


def test_every_names_tab_line_reads(hmmscore_data: Path) -> None:
    content = (hmmscore_data / "globals" / "names.tab").read_bytes()

    names = read_names(lines_of(content), "names.tab")

    assert {hmm_id.split(":")[0] for hmm_id in names} == set(MANIFEST["families"])


@pytest.mark.parametrize("path", MODEL_FILES)
def test_every_model_file_reads(hmmscore_data: Path, path: str) -> None:
    model = read_model_file(lines_of((hmmscore_data / path).read_bytes()), path)

    assert model.name.startswith(f"{path.split('/')[1]}.")


def test_surveying_the_sample_finds_every_variant_the_full_library_has(
    hmmscore_data: Path, tmp_path: Path
) -> None:
    files = {
        f"{PREFIX}{name.removeprefix(f'{sample.FOLDER}/')}": hmmscore_data.parents[1] / name
        for name in MANIFEST["files"]
    }
    tarball = tmp_path / "sample.tar.gz"
    write_tarball(tarball, files, compresslevel=1)

    report = survey(tarball)

    found = set(report.found())
    assert [key for key in FULL_LIBRARY_FOUND if key not in found] == []
    assert sorted(found) == sorted(FULL_LIBRARY_FOUND)


def example_table(hmmscore_data: Path, tmp_path: Path) -> str:
    """`hmmscan`'s table for the example against the sample, without its `#` lines."""
    program = shutil.which("hmmscan")
    assert program is not None
    table = tmp_path / "apoe.domtblout"
    # No flat binHmm: hmmscan opens binHmm.h3m and the other pressed files beside the name.
    args = ["--domtblout", str(table), str(hmmscore_data / "globals" / "binHmm"), str(EXAMPLE)]

    result = run_tool(Path(program), args, timeout=600, stdout=tmp_path / "hmmscan.out")

    assert result.returncode == 0, result.stderr
    lines = table.read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(line for line in lines if not line.startswith("#"))


@pytest.mark.tools("hmmscan")
def test_hmmscans_table_for_the_example_is_this_architectures(
    hmmscore_data: Path, tmp_path: Path
) -> None:
    committed = GOLDEN / "sample-hmmscan" / ARCHITECTURES[platform.machine()] / "apoe.domtblout"

    assert example_table(hmmscore_data, tmp_path) == committed.read_text(encoding="utf-8")


@pytest.mark.tools("hmmscan")
def test_the_examples_best_hit_is_the_full_librarys(hmmscore_data: Path, tmp_path: Path) -> None:
    rows = [line.split() for line in example_table(hmmscore_data, tmp_path).splitlines()]

    best = max(rows, key=lambda row: float(row[7]))

    assert best[0] == FULL_LIBRARY_BEST
