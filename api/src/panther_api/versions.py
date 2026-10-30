"""The versions behind every answer: the API's, the engine's, each service's data and each
external tool's.

The image fixes all of them, so the app reads them once when it starts (main.py), and every job
carries them.
"""

import logging
from importlib.metadata import version as package_version

from panther_engine.core.tools import TOOLS, report_tools
from panther_engine.csnp import DATA_VERSION as CSNP_DATA_VERSION
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DataVersion(BaseModel):
    """The PANTHER release whose data a scoring service reads, such as "9" for cSNP's frozen
    PANTHER 9 data. It names the release the engine reads, not whether the data is installed."""

    service: str
    panther: str


class ToolVersion(BaseModel):
    """An external tool and the version it reports: null if it's missing or can't be read."""

    name: str
    version: str | None


class Versions(BaseModel):
    """The API, engine, tool and data versions. Never includes where a tool or data was found."""

    api: str
    engine: str
    tools: list[ToolVersion]
    data: list[DataVersion]


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
        # One entry per ported service, in the order the services were ported.
        data=[DataVersion(service="csnp", panther=CSNP_DATA_VERSION)],
    )
