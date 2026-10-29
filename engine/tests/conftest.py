import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest


def missing_tools(item: pytest.Item) -> list[str]:
    """The programs named by the test's `tools` markers that aren't on PATH."""
    names = [str(name) for marker in item.iter_markers("tools") for name in marker.args]
    return [name for name in names if shutil.which(name) is None]


def tools_required() -> bool:
    """True where the tools must be present, as in the engine image."""
    return os.environ.get("PANTHER_REQUIRE_TOOLS") == "1"


def pytest_runtest_setup(item: pytest.Item) -> None:
    missing = missing_tools(item)
    if missing and not tools_required():
        pytest.skip(f"needs {', '.join(missing)}, not found on PATH")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_call(item: pytest.Item) -> None:
    # Failing here, not in setup, reports the test as failed rather than as an error.
    missing = missing_tools(item)
    if missing and tools_required():
        pytest.fail(
            f"needs {', '.join(missing)}, not found on PATH (PANTHER_REQUIRE_TOOLS=1)",
            pytrace=False,
        )


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
