"""The built-in `tools` job: the engine's external tool report, run in a worker process.

It runs no scoring. It lets a developer check that the API, the worker pool, the engine and the
tools work together before any scoring service exists.
"""

from panther_engine.core.tools import report_tools
from pydantic import BaseModel, ConfigDict

from panther_api.versions import ToolVersion


class ToolsInput(BaseModel):
    """The `tools` job takes no input: `{}`."""

    model_config = ConfigDict(extra="forbid")


class ToolsResult(BaseModel):
    """Each external tool the engine uses, in the engine's order. Never where it was found."""

    tools: list[ToolVersion]


def run_tools(_input: ToolsInput) -> ToolsResult:
    """Run the engine's tool report. Runs in a worker process, never on the event loop."""
    return ToolsResult(
        tools=[ToolVersion(name=report.name, version=report.version) for report in report_tools()]
    )
