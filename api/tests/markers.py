"""The `tools` and `data` markers, as the engine's tests have them (engine/tests/conftest.py).

A test marked `tools("blastp")` runs `blastp`, and one marked `data("csnp")` reads the cSNP data
sample. Each is skipped where what it needs is missing, and fails instead where it's required:
`PANTHER_REQUIRE_TOOLS=1`, `PANTHER_REQUIRE_DATA=1`. conftest.py applies them.
"""

import os
import shutil
from pathlib import Path

import pytest
from panther_engine.core.manifest import checksums, read_manifest
from panther_engine.csnp import sample

REPO_ROOT = Path(__file__).resolve().parents[2]
# Each service's data sample, by the manifest that lists its files.
DATA_MANIFESTS = {"csnp": sample.MANIFEST}


def data_folder() -> Path:
    """`PANTHER_DATA_DIR`, or the repository's `.data/` where it isn't set."""
    return Path(os.environ.get("PANTHER_DATA_DIR") or REPO_ROOT / ".data")


def missing_tools(item: pytest.Item) -> list[str]:
    """The programs named by the test's `tools` markers that aren't on PATH."""
    names = [str(name) for marker in item.iter_markers("tools") for name in marker.args]
    return [name for name in names if shutil.which(name) is None]


def missing_data(item: pytest.Item) -> list[str]:
    """The services named by the test's `data` markers whose sample files aren't all there.

    Only presence is checked: the engine's tests hash every file against the manifest.
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


def tools_required() -> bool:
    return os.environ.get("PANTHER_REQUIRE_TOOLS") == "1"


def data_required() -> bool:
    return os.environ.get("PANTHER_REQUIRE_DATA") == "1"


def skip_if_missing(item: pytest.Item) -> None:
    """At setup: skip a test whose tools or data are missing, unless they're required."""
    missing = missing_tools(item)
    if missing and not tools_required():
        pytest.skip(f"needs {', '.join(missing)}, not found on PATH")
    missing = missing_data(item)
    if missing and not data_required():
        pytest.skip(
            f"needs the {', '.join(missing)} data sample, not found in {data_folder()} "
            "(set PANTHER_DATA_DIR, or fetch it: docs/testing/api.md)"
        )


def fail_if_missing(item: pytest.Item) -> None:
    """When the test is called: fail it if what's required is missing. Failing here, not in
    setup, reports the test as failed rather than as an error."""
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
