"""The `panther-engine hmmscore` subcommands: scoring one protein, the survey of the HMM library's
tarball, the pinned library, and the data sample."""

import argparse
import dataclasses
import json
import resource
import sys
import time
from pathlib import Path

from panther_engine.core.data import DATA_DIR_VARIABLE, DataFolderError, MissingDataError
from panther_engine.core.download import DownloadError
from panther_engine.core.errors import InputError
from panther_engine.core.fasta import read_protein
from panther_engine.core.manifest import ManifestError, checksums, read_manifest
from panther_engine.hmmscore import data, parity, sample
from panther_engine.hmmscore.library import PREFIX, LibraryFormatError
from panther_engine.hmmscore.scoring import (
    HmmscoreError,
    HmmscoreInput,
    HmmscoreResult,
    TimeLimitError,
    score,
)
from panther_engine.hmmscore.survey import SurveyError, report_json, report_text, survey


def configure(parser: argparse.ArgumentParser) -> None:
    """Add the `hmmscore` subcommands to `parser`, the `hmmscore` command's parser."""
    commands = parser.add_subparsers(dest="hmmscore_command", metavar="COMMAND", required=True)

    score_parser = commands.add_parser(
        "score",
        help="score one protein against the HMM library",
        description="Score one protein, as the API's hmmscore job does: hmmscan against "
        "globals/binHmm, the legacy best hit and its 1e-3 cutoff, then hmmsearch of the hit's "
        "model file for the alignment. The sequence is normalised as the API normalises it: one "
        "header line and all whitespace removed, upper case. Prints the hit's PANTHER ID, name, "
        "E-value and score, then the alignment, or No hit.",
    )
    score_parser.add_argument(
        "fasta",
        nargs="?",
        default="-",
        metavar="FILE",
        help="one protein: FASTA with one header line, or the sequence alone; - or none for "
        "standard input",
    )
    score_parser.add_argument(
        "--cpu",
        type=int,
        default=0,
        metavar="N",
        help="hmmscan's and hmmsearch's --cpu: worker threads (default: 0, the least memory)",
    )
    score_parser.add_argument(
        "--timeout",
        type=float,
        metavar="S",
        help="a time limit in seconds for the whole search (default: none)",
    )
    score_parser.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help=f"the data folder, holding hmmscore/19/ (default: ${DATA_DIR_VARIABLE})",
    )
    score_parser.add_argument(
        "--json", action="store_true", help="print the result as JSON, as score() returns it"
    )
    score_parser.add_argument(
        "--usage",
        action="store_true",
        help="also print, to standard error, the wall time and the largest peak memory of the "
        "tools it ran, from the kernel's accounting of child processes",
    )

    parity_parser = commands.add_parser(
        "parity",
        help="run the golden cases through the legacy CGI, check the port against them",
        description="Parity with pantherScoring's scoreAlignXml.cgi and pantherScore.pl at "
        "89ea0ae, with HMMER 3.1b2: run the golden cases through the Perl in the "
        "hmmscore-reference image, and check the port against its outputs. See "
        "docs/parity/golden-setup.md.",
    )
    parity_commands = parity_parser.add_subparsers(
        dest="parity_command", metavar="COMMAND", required=True
    )
    reference = parity_commands.add_parser(
        "reference",
        help="run the golden cases through the CGI and pantherScore.pl (hmmscore-reference "
        "image only)",
        description="First the self-check: the example must give PTHR18976:SF2 at 439.0 bits. "
        "Then, for each case, one at a time, in a fresh folder: the CGI posted the case's text, "
        "saved as cgi.xml without its Content-type header; pantherScore.pl -D B -n, saved as "
        "best.tsv; and the CGI's hmmsearch for each ID in best.tsv, saved in hmmsearch/. Each "
        "case's outputs replace GOLDENS/<case>/ in the golden folder once it has run. For "
        "sample, HMMER 3.1b2 reads its own presses of the data folder's models; for full, the "
        "library's shipped pressed files.",
    )
    add_parity_options(reference)
    check = parity_commands.add_parser(
        "check",
        help="check the port against the golden outputs",
        description="Score each case with the port, and compare the result with the one the "
        "reference's outputs give: best.tsv's tied IDs, with divergence 13 picking one, and the "
        "alignment from that ID's hmmsearch report. Also checks that cgi.xml agrees with them. "
        "Prints each case's time and every difference, and exits with status 1 if any case "
        "differs or has no reference outputs.",
    )
    add_parity_options(check)

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


def add_parity_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--goldens",
        choices=parity.GOLDEN_SETS,
        default="sample",
        help="the goldens: sample, made on the data sample, or full, on the full library "
        "(default: sample)",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        metavar="DIR",
        default=parity.GOLDEN,
        help=f"the golden folder, with cases.json (default: {parity.GOLDEN})",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help=f"the data folder, holding hmmscore/19/ (default: ${DATA_DIR_VARIABLE})",
    )
    parser.add_argument(
        "--case",
        action="append",
        metavar="NAME",
        help="this case only; repeat for more (default: every case)",
    )


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
        case "score":
            return run_score(args)
        case "parity":
            return run_parity(args)
        case "survey":
            return run_survey(args.tarball, args.json)
        case "data":
            return run_data(args)
        case "sample":
            return run_sample(args)
        case _:
            raise AssertionError(f"unhandled command: hmmscore {args.hmmscore_command}")


def run_score(args: argparse.Namespace) -> int:
    started = time.monotonic()
    try:
        text = sys.stdin.read() if args.fasta == "-" else Path(args.fasta).read_text("utf-8")
        result = score(
            HmmscoreInput(read_protein(text)),
            data_dir=args.data_dir,
            cpu=args.cpu,
            timeout=args.timeout,
        )
    except (
        ValueError,
        InputError,
        TimeLimitError,
        HmmscoreError,
        MissingDataError,
        LibraryFormatError,
        DataFolderError,
        OSError,
    ) as error:
        print(f"panther-engine hmmscore score: {error}", file=sys.stderr)
        return 1
    print_result(result, as_json=args.json)
    if args.usage:
        print(f"wall time: {time.monotonic() - started:.1f} s", file=sys.stderr)
        print(f"peak memory of the tools: {peak_memory_mib():,.0f} MiB", file=sys.stderr)
    return 0


def run_parity(args: argparse.Namespace) -> int:
    command = f"panther-engine hmmscore parity {args.parity_command}"
    try:
        match args.parity_command:
            case "reference":
                reference = parity.Reference.find()
                names = parity.run_reference(
                    reference, args.golden, args.goldens, args.data_dir, args.case
                )
                print(f"wrote {len(names)} cases to {args.golden / args.goldens}")
            case "check":
                checks = parity.run_check(args.golden, args.goldens, args.data_dir, args.case)
                for checked in checks:
                    print(f"{checked.name}: {checked.seconds:.1f} s")
                    for difference in checked.differences:
                        print(f"  {difference}")
                differing = [checked for checked in checks if checked.differences]
                print(f"{len(checks) - len(differing)} of {len(checks)} cases match")
                return 1 if differing else 0
            case _:
                raise AssertionError(f"unhandled command: {command}")
    except (parity.ParityError, DataFolderError, MissingDataError, OSError) as error:
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    return 0


def print_result(result: HmmscoreResult, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(dataclasses.asdict(result), indent=2))
        return
    hit = result.hit
    if hit is None:
        print("No hit")
        return
    print(f"panther_id\t{hit.panther_id}")
    print(f"name\t{hit.name}")
    print(f"evalue\t{hit.evalue}")
    print(f"score\t{hit.score}")
    print("alignment")
    sys.stdout.write(hit.alignment)


def peak_memory_mib() -> float:
    """The largest peak resident memory of the child processes that have ended, in MiB: in a
    fresh process, the tools scoring ran. Linux counts it in KiB, macOS in bytes."""
    peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return peak / (2**20 if sys.platform == "darwin" else 2**10)


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
