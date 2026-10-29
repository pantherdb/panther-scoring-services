"""The `panther-engine` command. Each service adds its own subcommand."""

import argparse
from collections.abc import Sequence

from panther_engine import __version__
from panther_engine.core.tools import report_tools


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="panther-engine",
        description="Scoring engine for the PANTHER services.",
    )
    parser.add_argument("--version", action="version", version=f"panther-engine {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)
    commands.add_parser(
        "tools",
        help="list the external tools with each one's version and path",
        description="List the external tools with each one's version and path. "
        "Exits with status 1 if any tool is missing or its version can't be read.",
    )
    return parser


def tools() -> int:
    reports = report_tools()
    versions = [report.version or "version unknown" for report in reports]
    name_width = max(len(report.name) for report in reports)
    version_width = max(len(version) for version in versions)
    for report, version in zip(reports, versions, strict=True):
        if report.path is None:
            detail = "not found"
        else:
            detail = f"{version:<{version_width}}  {report.path}"
        print(f"{report.name:<{name_width}}  {detail}")
    return 0 if all(report.ok for report in reports) else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    match args.command:
        case "tools":
            return tools()
        case _:
            raise AssertionError(f"unhandled command: {args.command}")
