import functools
import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from panther_engine.core.manifest import checksums, read_manifest
from panther_engine.csnp import sample
from panther_engine.hmmscore import sample as hmmscore_sample
from panther_engine.hmmscore.sample import HMMER_VERSION, SampleError, hmmer_version
from panther_engine.refmap import organisms as refmap_organisms
from panther_engine.refmap.data import MANIFEST as REFMAP_MANIFEST

REPO_ROOT = Path(__file__).resolve().parents[2]
# Each service's data, by the manifest that lists its files: the cSNP and hmmscore data samples,
# and the whole refmap release.
DATA_MANIFESTS = {
    "csnp": sample.MANIFEST,
    "hmmscore": hmmscore_sample.MANIFEST,
    "refmap": REFMAP_MANIFEST,
}
# HMMER programs count only at the image's version: tests compare with what it gives, so a
# developer's own HMMER, such as 3.1b2, is as good as missing.
HMMER_PROGRAMS = frozenset({"hmmbuild", "hmmconvert", "hmmpress", "hmmscan", "hmmsearch"})


@functools.cache
def other_hmmer(name: str) -> str | None:
    """What was found, for an HMMER program on PATH at a version other than the image's."""
    found = shutil.which(name)
    if name not in HMMER_PROGRAMS or found is None:
        return None
    try:
        version = hmmer_version(Path(found).absolute())
    except SampleError:
        version = None
    if version == HMMER_VERSION:
        return None
    return f"{name} {HMMER_VERSION}, found HMMER {version} at {found}"


def missing_tools(item: pytest.Item) -> list[str]:
    """What the test's `tools` markers name that it can't use: programs that aren't on PATH, and
    HMMER programs at another version than the image's."""
    names = [str(name) for marker in item.iter_markers("tools") for name in marker.args]
    absent = [name for name in names if shutil.which(name) is None]
    problems = [f"{', '.join(absent)}, not found on PATH"] if absent else []
    return problems + [found for name in names if (found := other_hmmer(name)) is not None]


def tools_required() -> bool:
    """True where the tools must be present, as in the engine image."""
    return os.environ.get("PANTHER_REQUIRE_TOOLS") == "1"


def data_folder() -> Path:
    """`PANTHER_DATA_DIR`, or the repository's `.data/` where it isn't set."""
    return Path(os.environ.get("PANTHER_DATA_DIR") or REPO_ROOT / ".data")


def missing_data(item: pytest.Item) -> list[str]:
    """The services named by the test's `data` markers whose data files aren't all there.

    Only presence is checked here. One test hashes every file against the manifest.
    """
    names = [str(name) for marker in item.iter_markers("data") for name in marker.args]
    folder = data_folder()
    return [
        name
        for name in names
        if not all(
            (folder / path).is_file() for path in checksums(read_manifest(DATA_MANIFESTS[name]))
        )
    ]


def data_required() -> bool:
    """True where the data must be present, as in CI."""
    return os.environ.get("PANTHER_REQUIRE_DATA") == "1"


def pytest_runtest_setup(item: pytest.Item) -> None:
    missing = missing_tools(item)
    if missing and not tools_required():
        pytest.skip(f"needs {'; '.join(missing)}")
    missing = missing_data(item)
    if missing and not data_required():
        pytest.skip(
            f"needs the {', '.join(missing)} data, not found in {data_folder()} "
            "(set PANTHER_DATA_DIR, or fetch it: docs/testing/engine.md)"
        )


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_call(item: pytest.Item) -> None:
    # Failing here, not in setup, reports the test as failed rather than as an error.
    missing = missing_tools(item)
    if missing and tools_required():
        pytest.fail(
            f"needs {'; '.join(missing)} (PANTHER_REQUIRE_TOOLS=1)",
            pytrace=False,
        )
    missing = missing_data(item)
    if missing and data_required():
        pytest.fail(
            f"needs the {', '.join(missing)} data, not found in {data_folder()} "
            "(PANTHER_REQUIRE_DATA=1)",
            pytrace=False,
        )


@pytest.fixture
def csnp_data() -> Path:
    """cSNP's data folder, `csnp/9/` in the data folder."""
    return data_folder() / sample.FOLDER


@pytest.fixture
def refmap_data() -> Path:
    """refmap's data folder, `refmap/19/` in the data folder."""
    return data_folder() / refmap_organisms.FOLDER


@pytest.fixture
def hmmscore_data() -> Path:
    """hmmscore's data folder, `hmmscore/19/` in the data folder."""
    return data_folder() / hmmscore_sample.FOLDER


@pytest.fixture
def make_tool(tmp_path: Path) -> Callable[[str, str], Path]:
    """Returns `make(name, script)`, which writes an executable /bin/sh script to tmp_path/bin."""
    folder = tmp_path / "bin"
    folder.mkdir()

    def make(name: str, script: str) -> Path:
        path = folder / name
        path.write_text(f"#!/bin/sh\n{script}\n", encoding="utf-8")
        path.chmod(0o755)
        return path

    return make
