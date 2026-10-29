"""The external tools the engine runs: how to find each one and read its version.

The image pins each tool's version (the root Dockerfile). Here they are found on PATH.
"""

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from panther_engine.core.process import run_tool

VERSION_TIMEOUT = 30.0


@dataclass(frozen=True)
class Tool:
    """A program, the arguments that make it print its version, and a pattern for the version."""

    name: str
    version_args: tuple[str, ...]
    version_pattern: re.Pattern[str]

    def find(self) -> Path | None:
        found = shutil.which(self.name)
        return Path(found).absolute() if found else None

    def parse_version(self, output: str) -> str | None:
        match = self.version_pattern.search(output)
        return match.group(1) if match else None


# Patterns written against the output recorded in tests/fixtures/tool-versions/.
TOOLS = (
    Tool("blastp", ("-version",), re.compile(r"^blastp: (\S+)\+$", re.MULTILINE)),
    Tool("hmmscan", ("-h",), re.compile(r"^# HMMER (\S+) ", re.MULTILINE)),
    Tool("hmmsearch", ("-h",), re.compile(r"^# HMMER (\S+) ", re.MULTILINE)),
    Tool("epa-ng", ("--version",), re.compile(r"^EPA-ng v(\S+)$", re.MULTILINE)),
)


@dataclass(frozen=True)
class ToolReport:
    """A tool's path, or None if it isn't on PATH, and its version, or None if it can't be read."""

    name: str
    path: Path | None
    version: str | None

    @property
    def ok(self) -> bool:
        return self.path is not None and self.version is not None


def report(tool: Tool) -> ToolReport:
    path = tool.find()
    if path is None:
        return ToolReport(tool.name, None, None)
    try:
        result = run_tool(path, tool.version_args, timeout=VERSION_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return ToolReport(tool.name, path, None)
    return ToolReport(tool.name, path, tool.parse_version(result.stdout))


def report_tools() -> list[ToolReport]:
    return [report(tool) for tool in TOOLS]
