import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from panther_engine.core.manifest import checksums, read_manifest
from panther_engine.csnp import sample

REPO_ROOT = Path(__file__).resolve().parents[2]
# Each service's data sample, by the manifest that lists its files.
DATA_MANIFESTS = {"csnp": sample.MANIFEST}


def missing_tools(item: pytest.Item) -> list[str]:
    """The programs named by the test's `tools` markers that aren't on PATH."""
    names = [str(name) for marker in item.iter_markers("tools") for name in marker.args]
    return [name for name in names if shutil.which(name) is None]


def tools_required() -> bool:
    """True where the tools must be present, as in the engine image."""
    return os.environ.get("PANTHER_REQUIRE_TOOLS") == "1"


def data_folder() -> Path:
    """`PANTHER_DATA_DIR`, or the repository's `.data/` where it isn't set."""
    return Path(os.environ.get("PANTHER_DATA_DIR") or REPO_ROOT / ".data")


def missing_data(item: pytest.Item) -> list[str]:
    """The services named by the test's `data` markers whose sample files aren't all there.

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
        pytest.skip(f"needs {', '.join(missing)}, not found on PATH")
    missing = missing_data(item)
    if missing and not data_required():
        pytest.skip(
            f"needs the {', '.join(missing)} data sample, not found in {data_folder()} "
            "(set PANTHER_DATA_DIR, or fetch it: docs/testing/engine.md)"
        )


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_call(item: pytest.Item) -> None:
    # Failing here, not in setup, reports the test as failed rather than as an error.
    missing = missing_tools(item)
    if missing and tools_required():
        pytest.fail(
            f"needs {', '.join(missing)}, not found on PATH (PANTHER_REQUIRE_TOOLS=1)",
            pytrace=False,
        )
    missing = missing_data(item)
    if missing and data_required():
        pytest.fail(
            f"needs the {', '.join(missing)} data sample, not found in {data_folder()} "
            "(PANTHER_REQUIRE_DATA=1)",
            pytrace=False,
        )


@pytest.fixture
def csnp_data() -> Path:
    """cSNP's data folder, `csnp/9/` in the data folder."""
    return data_folder() / sample.FOLDER


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
