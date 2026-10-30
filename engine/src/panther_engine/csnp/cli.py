"""The `panther-engine csnp` subcommands: the library survey, and the data sample."""

import argparse
import json
import sys
from pathlib import Path

from panther_engine.core.data import DATA_DIR_VARIABLE, DataFolderError
from panther_engine.core.manifest import ManifestError
from panther_engine.csnp import sample
from panther_engine.csnp.survey import SurveyError, report_json, report_text, survey


def configure(parser: argparse.ArgumentParser) -> None:
    """Add the `csnp` subcommands to `parser`, the `csnp` command's parser."""
    commands = parser.add_subparsers(dest="csnp_command", metavar="COMMAND", required=True)

    survey_parser = commands.add_parser(
        "survey",
        help="survey the PAML_RST library archive, without unpacking it",
        description="Read a gzipped tar of the PAML_RST library as a stream, and check every "
        "family: its files, whether they parse and agree, and where the legacy scorer's reading "
        "differs. Prints each check's count and up to five examples, smallest family first. "
        "Exits with status 0 when the archive was read to the end, whatever the checks found.",
    )
    survey_parser.add_argument(
        "archive", type=Path, metavar="ARCHIVE", help="PAML_RST.tar.gz, or a sample tarball"
    )
    survey_parser.add_argument(
        "--species",
        type=Path,
        metavar="FILE",
        help="species_pthr8_time.nhx, for the taxon checks",
    )
    survey_parser.add_argument(
        "--blast-archive",
        type=Path,
        metavar="FILE",
        help="PANTHER9.blast.tar.gz, to check its entries against the library",
    )
    survey_parser.add_argument(
        "--json", type=Path, metavar="FILE", help="also write the report to FILE as JSON"
    )

    sample_parser = commands.add_parser(
        "sample",
        help="build, fetch or verify the cSNP data sample",
        description="The cSNP data sample: chosen families of the PAML_RST library, the "
        "species tree and the PSEP copyright statement, attached to a GitHub release and pinned "
        "by the engine's sample.json. It unpacks under the data folder at csnp/9/.",
    )
    sample_commands = sample_parser.add_subparsers(
        dest="sample_command", metavar="COMMAND", required=True
    )
    build = sample_commands.add_parser(
        "build",
        help="build the sample tarball and its manifest from PAML_RST.tar.gz",
        description="Build the sample tarball from PAML_RST.tar.gz, byte for byte the same each "
        "time, and write its manifest. Refuses an archive or species tree whose sha256 isn't "
        "the pinned one, and then writes nothing.",
    )
    build.add_argument("archive", type=Path, metavar="ARCHIVE", help="PAML_RST.tar.gz")
    build.add_argument(
        "--species", type=Path, metavar="FILE", required=True, help="species_pthr8_time.nhx"
    )
    build.add_argument(
        "--readme",
        type=Path,
        metavar="FILE",
        required=True,
        help="the PSEP 1.01 release's README.txt, for its copyright statement",
    )
    build.add_argument(
        "--families",
        type=Path,
        metavar="FILE",
        required=True,
        help="the families to include, one per line; # starts a comment",
    )
    build.add_argument("--tag", required=True, help="the release tag, such as csnp-sample-1")
    build.add_argument(
        "--out", type=Path, metavar="FILE", help="the tarball to write (default: TAG.tar.gz)"
    )
    build.add_argument(
        "--manifest",
        type=Path,
        metavar="FILE",
        default=sample.MANIFEST,
        help="the manifest to write (default: the engine's sample.json)",
    )
    build.add_argument(
        "--archive-sha256",
        metavar="HEX",
        default=sample.PINNED_ARCHIVE,
        help="the archive's expected sha256 (default: the pin in the legacy behaviour spec)",
    )
    build.add_argument(
        "--species-sha256",
        metavar="HEX",
        default=sample.PINNED_SPECIES,
        help="the species tree's expected sha256 (default: the pin in the legacy behaviour spec)",
    )

    fetch = sample_commands.add_parser(
        "fetch",
        help="download the sample, check it and unpack it into the data folder",
        description="Download the sample tarball, check its sha256, unpack it into the data "
        "folder and check every file. Does nothing when the folder already matches the "
        "manifest, and leaves the folder as it was if anything fails.",
    )
    add_data_options(fetch)
    fetch.add_argument(
        "--from",
        dest="source",
        type=Path,
        metavar="FILE",
        help="a local copy of the tarball, instead of downloading it",
    )
    verify = sample_commands.add_parser(
        "verify",
        help="check the data folder against the sample manifest",
        description="Check the data folder against the sample manifest. Lists each file that "
        "is missing or differs, and exits with status 1 if there is any.",
    )
    add_data_options(verify)


def add_data_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help=f"the data folder (default: ${DATA_DIR_VARIABLE})",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        metavar="FILE",
        default=sample.MANIFEST,
        help="the manifest (default: the engine's sample.json)",
    )


def run(args: argparse.Namespace) -> int:
    match args.csnp_command:
        case "survey":
            return run_survey(args.archive, args.species, args.blast_archive, args.json)
        case "sample":
            return run_sample(args)
        case _:
            raise AssertionError(f"unhandled command: csnp {args.csnp_command}")


def run_sample(args: argparse.Namespace) -> int:
    command = f"panther-engine csnp sample {args.sample_command}"
    try:
        match args.sample_command:
            case "build":
                families = read_families(args.families)
                out = args.out or Path(f"{args.tag}.tar.gz")
                built = sample.build(
                    args.archive,
                    species=args.species,
                    readme=args.readme,
                    families=families,
                    tag=args.tag,
                    out=out,
                    manifest=args.manifest,
                    archive_sha256=args.archive_sha256,
                    species_sha256=args.species_sha256,
                )
                print(f"wrote {out} ({len(families)} families) and {args.manifest}")
                print(f"sha256 {sample.asset_of(built).sha256}")
            case "fetch":
                if sample.fetch(args.data_dir, manifest=args.manifest, source=args.source):
                    print("fetched the cSNP data sample, and checked every file")
                else:
                    print("the cSNP data sample is already there: nothing to fetch")
            case "verify":
                mismatches = sample.verify_folder(args.data_dir, manifest=args.manifest)
                for path in mismatches.missing:
                    print(f"missing: {path}")
                for path in mismatches.differing:
                    print(f"differs: {path}")
                if not mismatches.ok:
                    return 1
                print("every file matches the manifest")
            case _:
                raise AssertionError(f"unhandled command: {command}")
    except (sample.SampleError, DataFolderError, ManifestError, OSError) as error:
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    return 0


def read_families(path: Path) -> list[str]:
    """One family per line. Blank lines and `#` comments are ignored."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [name for line in lines if (name := line.partition("#")[0].strip())]


def run_survey(
    archive: Path, species: Path | None, blast: Path | None, json_path: Path | None
) -> int:
    def progress(members: int, size: int) -> None:
        print(f"read {members:,} files, {size / 1e6:,.0f} MB", file=sys.stderr, flush=True)

    try:
        report = survey(archive, species=species, blast=blast, progress=progress)
    except (SurveyError, OSError) as error:
        print(f"panther-engine csnp survey: {error}", file=sys.stderr)
        return 1
    sys.stdout.write(report_text(report))
    if json_path is not None:
        json_path.write_text(json.dumps(report_json(report), indent=2) + "\n", encoding="utf-8")
    return 0
