"""The `panther-engine` command. Each service adds its own subcommand."""

import argparse
from collections.abc import Sequence

from panther_engine import __version__
from panther_engine.core.tools import report_tools
from panther_engine.csnp import cli as csnp_cli
from panther_engine.hmmscore import cli as hmmscore_cli
from panther_engine.refmap import cli as refmap_cli


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
    csnp_cli.configure(
        commands.add_parser(
            "csnp",
            help="cSNP: score a protein, survey the library, the data sample, parity checks",
            description="The cSNP service: scoring, the PAML_RST library survey, the data sample "
            "that developers and CI test against, and parity with the legacy scripts.",
        )
    )
    refmap_cli.configure(
        commands.add_parser(
            "refmap",
            help="refmap: map IDs to PANTHER families, the data, parity checks",
            description="The refmap service: mapping protein IDs to PANTHER families and "
            "subfamilies for one Reference Proteome organism, the PANTHER 19 classification "
            "files it reads, and parity with the legacy map_panther.pl.",
        )
    )
    hmmscore_cli.configure(
        commands.add_parser(
            "hmmscore",
            help="hmmscore: survey the HMM library",
            description="The hmmscore service: the survey of the PANTHER 19 HMM library's tarball.",
        )
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
        case "csnp":
            return csnp_cli.run(args)
        case "refmap":
            return refmap_cli.run(args)
        case "hmmscore":
            return hmmscore_cli.run(args)
        case _:
            raise AssertionError(f"unhandled command: {args.command}")
