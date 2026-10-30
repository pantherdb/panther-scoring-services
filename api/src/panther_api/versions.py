"""The versions behind every answer: the API's, the engine's and each external tool's.

The image fixes all of them, so the app reads them once when it starts (main.py). Job results will
carry the same model.
"""

import logging
from importlib.metadata import version as package_version

from panther_engine.core.tools import TOOLS, report_tools
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolVersion(BaseModel):
    """An external tool and the version it reports: null if it's missing or can't be read."""

    name: str
    version: str | None


class Versions(BaseModel):
    """The API, engine and tool versions. Never includes where a tool was found."""

    api: str
    engine: str
    tools: list[ToolVersion]


def read_versions() -> Versions:
    """Read the versions. This runs each tool's version command, so call it once, off the loop.

    If the tool report itself fails, every tool's version is null: the app still starts, and its
    health check never depends on the tools.
    """
    try:
        tools = [ToolVersion(name=report.name, version=report.version) for report in report_tools()]
    except Exception:
        logger.exception("Could not read the external tools' versions")
        tools = [ToolVersion(name=tool.name, version=None) for tool in TOOLS]
    return Versions(
        api=package_version("panther-api"),
        engine=package_version("panther-engine"),
        tools=tools,
    )
