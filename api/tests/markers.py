"""The `tools` and `data` markers, as the engine's tests have them (engine/tests/conftest.py).

A test marked `tools("blastp")` runs `blastp`, one marked `data("csnp")` reads the cSNP data
sample, one marked `data("refmap")` the refmap data, and one marked `data("hmmscore")` the
hmmscore data sample. Each is skipped where what it needs is missing, and fails instead where it's
required: `PANTHER_REQUIRE_TOOLS=1`, `PANTHER_REQUIRE_DATA=1`. conftest.py applies them.

An HMMER program counts only at the image's version, as in the engine's tests (`other_hmmer`):
the hmmscore goldens are the image's HMMER's, and HMMER 3.1b2 can't read the sample's presses, so
another version on PATH is a skip, not a failure (openspec wire-hmmscore, design.md, decision 7).
"""

import os
import shutil
from pathlib import Path

import pytest
from panther_engine.core.manifest import checksums, read_manifest
from panther_engine.csnp import sample
from panther_engine.hmmscore import sample as hmmscore_sample
from panther_engine.hmmscore.sample import HMMER_VERSION, SampleError, hmmer_version
from panther_engine.refmap import data as refmap_data

REPO_ROOT = Path(__file__).resolve().parents[2]
# Each service's data, by the manifest that lists its files: the cSNP and hmmscore data samples,
# and refmap's release.
DATA_MANIFESTS = {
    "csnp": sample.MANIFEST,
    "hmmscore": hmmscore_sample.MANIFEST,
    "refmap": refmap_data.MANIFEST,
}
# The HMMER programs, which count only at the image's version.
HMMER_PROGRAMS = frozenset({"hmmscan", "hmmsearch"})


def data_folder() -> Path:
    """`PANTHER_DATA_DIR`, or the repository's `.data/` where it isn't set."""
    return Path(os.environ.get("PANTHER_DATA_DIR") or REPO_ROOT / ".data")


def other_hmmer(name: str) -> str | None:
    """What was found, for an HMMER program on PATH at another version than the image's."""
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
        pytest.skip(f"needs {'; '.join(missing)}")
    missing = missing_data(item)
    if missing and not data_required():
        pytest.skip(
            f"needs the {', '.join(missing)} data, not found in {data_folder()} "
            "(set PANTHER_DATA_DIR, or fetch it: docs/testing/api.md)"
        )


def fail_if_missing(item: pytest.Item) -> None:
    """When the test is called: fail it if what's required is missing. Failing here, not in
    setup, reports the test as failed rather than as an error."""
    missing = missing_tools(item)
    if missing and tools_required():
        pytest.fail(f"needs {'; '.join(missing)} (PANTHER_REQUIRE_TOOLS=1)", pytrace=False)
    missing = missing_data(item)
    if missing and data_required():
        pytest.fail(
            f"needs the {', '.join(missing)} data, not found in {data_folder()} "
            "(PANTHER_REQUIRE_DATA=1)",
            pytrace=False,
        )
