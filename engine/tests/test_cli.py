import sys
from importlib.metadata import version
from pathlib import Path

from panther_engine.core.process import run_tool

PYTHON = Path(sys.executable)
INSTALLED_COMMAND = PYTHON.parent / "panther-engine"


def test_installed_command_prints_the_installed_version() -> None:
    result = run_tool(INSTALLED_COMMAND, ["--version"], timeout=30)

    assert result.returncode == 0
    assert result.stdout == f"panther-engine {version('panther-engine')}\n"


def test_module_prints_the_same_version_as_the_installed_command() -> None:
    installed = run_tool(INSTALLED_COMMAND, ["--version"], timeout=30)
    module = run_tool(PYTHON, ["-m", "panther_engine", "--version"], timeout=30)

    assert module.returncode == 0
    assert module.stdout == installed.stdout
