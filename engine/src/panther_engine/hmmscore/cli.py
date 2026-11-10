"""The `panther-engine hmmscore` subcommands: the survey of the HMM library's tarball."""

import argparse
import json
import sys
from pathlib import Path

from panther_engine.hmmscore.survey import SurveyError, report_json, report_text, survey


def configure(parser: argparse.ArgumentParser) -> None:
    """Add the `hmmscore` subcommands to `parser`, the `hmmscore` command's parser."""
    commands = parser.add_subparsers(dest="hmmscore_command", metavar="COMMAND", required=True)

    survey_parser = commands.add_parser(
        "survey",
        help="survey the HMM library's tarball, without unpacking it",
        description="Read the PANTHER HMM library's tarball as a stream, and check every member: "
        "its kind, names.tab, every model file, binHmm and the pressed files, and where "
        "pantherScore.pl's readings differ from the strict readers. Prints the tarball's sha256 "
        "and size, and each check's count with up to five examples, smallest family first. "
        "Writes no library file. Exits with status 0 when the tarball was read to the end, "
        "whatever the checks found.",
    )
    survey_parser.add_argument(
        "tarball", type=Path, metavar="TARBALL", help="PANTHER19.0_hmmscoring.tgz"
    )
    survey_parser.add_argument(
        "--json", type=Path, metavar="FILE", help="also write the report to FILE as JSON"
    )


def run(args: argparse.Namespace) -> int:
    match args.hmmscore_command:
        case "survey":
            return run_survey(args.tarball, args.json)
        case _:
            raise AssertionError(f"unhandled command: hmmscore {args.hmmscore_command}")


def run_survey(tarball: Path, json_path: Path | None) -> int:
    def progress(members: int, size: int) -> None:
        print(f"read {members:,} members, {size / 1e6:,.0f} MB", file=sys.stderr, flush=True)

    try:
        report = survey(tarball, progress=progress)
    except (SurveyError, OSError) as error:
        print(f"panther-engine hmmscore survey: {error}", file=sys.stderr)
        return 1
    sys.stdout.write(report_text(report))
    if json_path is not None:
        json_path.write_text(json.dumps(report_json(report), indent=2) + "\n", encoding="utf-8")
    return 0
