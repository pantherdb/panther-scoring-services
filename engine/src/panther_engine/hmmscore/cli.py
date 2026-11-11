"""The `panther-engine hmmscore` subcommands: the survey of the HMM library's tarball, the pinned
library, and the data sample."""

import argparse
import json
import sys
from pathlib import Path

from panther_engine.core.data import DATA_DIR_VARIABLE, DataFolderError
from panther_engine.core.download import DownloadError
from panther_engine.core.manifest import ManifestError, checksums, read_manifest
from panther_engine.hmmscore import data, sample
from panther_engine.hmmscore.library import PREFIX
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

    data_parser = commands.add_parser(
        "data",
        help="pin the HMM library",
        description="The hmmscore data: PANTHER 19's HMM library, one tarball on "
        "data.pantherdb.org. The engine's data.json pins the tarball, its member prefix, and the "
        "sha256 of the README, each globals/ file and books.sha256, which lists every model "
        "file's sha256.",
    )
    data_commands = data_parser.add_subparsers(
        dest="data_command", metavar="COMMAND", required=True
    )
    manifest = data_commands.add_parser(
        "manifest",
        help="write the pin from the library's tarball",
        description="Write data.json from the library's tarball, reading it once as a stream, "
        "without unpacking it. The same tarball gives the same bytes. Writes nothing, and names "
        "each problem, if a member is outside the prefix or isn't in the library's layout, or if "
        "a model file doesn't read.",
    )
    manifest.add_argument(
        "tarball", type=Path, metavar="TARBALL", help="PANTHER19.0_hmmscoring.tgz"
    )
    manifest.add_argument("--url", required=True, metavar="URL", help="where it is published")
    manifest.add_argument(
        "--prefix",
        default=PREFIX,
        metavar="PREFIX",
        help=f"the folder every member is below (default: PANTHER 19's, {PREFIX})",
    )
    manifest.add_argument(
        "--manifest",
        type=Path,
        metavar="FILE",
        default=data.MANIFEST,
        help="the pin to write (default: the engine's hmmscore/data.json)",
    )

    fetch = data_commands.add_parser(
        "fetch",
        help="fetch the pinned library into the data folder",
        description="Stream the pinned tarball from its URL, or read a local copy, and keep only "
        "what scoring reads: the README, globals/ and every model file, under hmmscore/19/ in "
        "the data folder, with books.sha256. Checks the tarball's size and sha256, and every kept "
        "file, before moving any into place. Does nothing when the folder already matches, and "
        "writes nothing under hmmscore/19/ if anything fails.",
    )
    add_data_options(fetch)
    fetch.add_argument(
        "--tarball",
        type=Path,
        metavar="FILE",
        help="a local copy of the tarball, such as one downloaded with curl -C -, instead of "
        "streaming it from its URL",
    )
    verify = data_commands.add_parser(
        "verify",
        help="check the data folder against the pin",
        description="Check the data folder against the pin: the README, each globals/ file and "
        "books.sha256, then every model file books.sha256 lists. Lists up to 20 files missing "
        "and 20 that differ, with the counts, and exits with status 1 if there is any.",
    )
    add_data_options(verify)

    sample_parser = commands.add_parser(
        "sample",
        help="build, fetch or verify the hmmscore data sample",
        description="The hmmscore data sample: chosen families of the HMM library, their "
        "names.tab lines, their binHmm models pressed by the pinned HMMER, and the library's "
        "README, published as a release asset of this repository. The engine's sample.json pins "
        "it. It unpacks under the data folder at hmmscore/19/, laid out as the full library.",
    )
    sample_commands = sample_parser.add_subparsers(
        dest="sample_command", metavar="COMMAND", required=True
    )
    build = sample_commands.add_parser(
        "build",
        help="build the sample tarball and its manifest from the library's tarball",
        description="Build the sample tarball from the pinned library tarball and a list of "
        "families, reading the library once as a stream. hmmpress presses the families' models: "
        "their records cut out of binHmm.h3m, as they are, or the flat binHmm's text where the "
        "library has one. The same inputs give the same bytes on one machine. Writes nothing if "
        "the tarball isn't the pinned one, if hmmpress isn't the pinned HMMER, or if the press "
        "doesn't give the records back in binHmm.h3m: build it in the engine image.",
    )
    build.add_argument("tarball", type=Path, metavar="TARBALL", help="PANTHER19.0_hmmscoring.tgz")
    build.add_argument(
        "--families",
        type=Path,
        required=True,
        metavar="FILE",
        help="the families to include, one per line; blank lines and # comments are ignored",
    )
    build.add_argument("--tag", required=True, metavar="TAG", help="the release tag")
    build.add_argument(
        "--out", type=Path, metavar="FILE", help="the tarball to write (default: TAG.tar.gz)"
    )
    build.add_argument(
        "--manifest",
        type=Path,
        metavar="FILE",
        default=sample.MANIFEST,
        help="the manifest to write (default: the engine's hmmscore/sample.json)",
    )
    build.add_argument(
        "--pin",
        type=Path,
        metavar="FILE",
        default=data.MANIFEST,
        help="the library's pin (default: the engine's hmmscore/data.json)",
    )
    sample_fetch = sample_commands.add_parser(
        "fetch",
        help="download the sample, check it and unpack it into the data folder",
        description="Download the sample tarball the manifest names, or take a local copy, check "
        "its sha256, unpack it safely and check every file. Does nothing when the folder already "
        "matches, and leaves the folder as it was if anything fails.",
    )
    add_sample_options(sample_fetch)
    sample_fetch.add_argument(
        "--from",
        dest="source",
        type=Path,
        metavar="FILE",
        help="a local copy of the tarball, instead of downloading it",
    )
    sample_verify = sample_commands.add_parser(
        "verify",
        help="check the data folder against the manifest",
        description="Check the data folder against the manifest. Lists each file that is missing "
        "or differs, and exits with status 1 if there is any.",
    )
    add_sample_options(sample_verify)


def add_data_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help=f"the data folder, holding hmmscore/19/ (default: ${DATA_DIR_VARIABLE})",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        metavar="FILE",
        default=data.MANIFEST,
        help="the pin (default: the engine's hmmscore/data.json)",
    )


def add_sample_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help=f"the data folder, holding hmmscore/19/ (default: ${DATA_DIR_VARIABLE})",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        metavar="FILE",
        default=sample.MANIFEST,
        help="the sample's manifest (default: the engine's hmmscore/sample.json)",
    )


def run(args: argparse.Namespace) -> int:
    match args.hmmscore_command:
        case "survey":
            return run_survey(args.tarball, args.json)
        case "data":
            return run_data(args)
        case "sample":
            return run_sample(args)
        case _:
            raise AssertionError(f"unhandled command: hmmscore {args.hmmscore_command}")


def read_families(path: Path) -> list[str]:
    """One family per line. Blank lines and `#` comments are ignored."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [name for line in lines if (name := line.partition("#")[0].strip())]


def run_sample(args: argparse.Namespace) -> int:
    command = f"panther-engine hmmscore sample {args.sample_command}"
    try:
        match args.sample_command:
            case "build":
                out = args.out or Path(f"{args.tag}.tar.gz")
                built = sample.build(
                    args.tarball,
                    families=read_families(args.families),
                    tag=args.tag,
                    out=out,
                    manifest=args.manifest,
                    pin=args.pin,
                )
                print(f"wrote {out} and {args.manifest}: {len(checksums(built)):,} files")
            case "fetch":
                if sample.fetch(args.data_dir, manifest=args.manifest, source=args.source):
                    print("fetched the hmmscore sample, and checked every file")
                else:
                    print("the hmmscore sample is already there: nothing to fetch")
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
    except (
        sample.SampleError,
        data.HmmscoreDataError,
        DownloadError,
        DataFolderError,
        ManifestError,
        OSError,
    ) as error:
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    return 0


def run_data(args: argparse.Namespace) -> int:
    command = f"panther-engine hmmscore data {args.data_command}"
    try:
        match args.data_command:
            case "manifest":
                pinned = data.manifest(
                    args.tarball, url=args.url, prefix=args.prefix, out=args.manifest
                )
                print(
                    f"wrote {args.manifest}: {len(checksums(pinned)):,} files, "
                    f"{data.book_count(pinned):,} model files in books.sha256"
                )
            case "fetch":
                if data.fetch(args.data_dir, manifest=args.manifest, tarball=args.tarball):
                    print("fetched the hmmscore library, and checked every file")
                else:
                    print("the hmmscore library is already there: nothing to fetch")
            case "verify":
                pinned = read_manifest(args.manifest)
                listed = len(checksums(pinned)) + data.book_count(pinned)
                mismatches = data.verify_folder(args.data_dir, manifest=args.manifest)
                print(
                    f"{len(mismatches.missing):,} missing and {len(mismatches.differing):,} "
                    f"differing, of {listed:,} listed files"
                )
                for kind, paths in (
                    ("missing", mismatches.missing),
                    ("differs", mismatches.differing),
                ):
                    for path in paths[: data.LISTED]:
                        print(f"{kind}: {path}")
                    if len(paths) > data.LISTED:
                        print(f"{kind}: and {len(paths) - data.LISTED:,} more")
                if not mismatches.ok:
                    return 1
                print("every file matches the pin")
            case _:
                raise AssertionError(f"unhandled command: {command}")
    except (
        data.HmmscoreDataError,
        DownloadError,
        DataFolderError,
        ManifestError,
        OSError,
    ) as error:
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    return 0


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
