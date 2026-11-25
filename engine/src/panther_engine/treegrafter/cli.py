"""The `panther-engine treegrafter` subcommands: grafting one protein, and the pinned library and
annotation releases."""

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

from panther_engine.core.data import DATA_DIR_VARIABLE, DataFolderError, MissingDataError
from panther_engine.core.download import DownloadError
from panther_engine.core.errors import InputError
from panther_engine.core.fasta import read_protein
from panther_engine.core.manifest import ManifestError
from panther_engine.core.process import peak_memory_mib
from panther_engine.treegrafter import data, parity
from panther_engine.treegrafter.scoring import (
    TimeLimitError,
    TreegrafterError,
    TreegrafterInput,
    TreegrafterResult,
    score,
)


def configure(parser: argparse.ArgumentParser) -> None:
    """Add the `treegrafter` subcommands to `parser`, the `treegrafter` command's parser."""
    commands = parser.add_subparsers(dest="treegrafter_command", metavar="COMMAND", required=True)

    score_parser = commands.add_parser(
        "score",
        help="graft one protein onto its best family's tree",
        description="Graft one protein as the API's treegrafter job will, and as EBI's "
        "treegrafter.sh search does: hmmsearch against famhmm/binHmm, EBI's best family and its "
        "1e-8 cutoff, then EPA-ng on the family's tree, and EBI's graft node with the active "
        "annotation release. The sequence is normalised as the API normalises it: one header line "
        "and all whitespace removed, upper case. Prints the hit's fields, tab-separated, with - "
        "for no value, or No hit, then the annotation release.",
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
        "--timeout",
        type=float,
        metavar="S",
        help="a time limit in seconds for the whole graft (default: none)",
    )
    add_data_dir_option(score_parser)
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
        help="run the golden cases through EBI's command line, check the engine against them",
        description="Parity with EBI's treegrafter at the pinned commit, with the engine's tools: "
        "run the golden cases through EBI's command line, and check the engine against its "
        "outputs. With the fixture set, both install the committed fixture, prepared, in a "
        "temporary data folder. See docs/parity/golden-setup.md.",
    )
    parity_commands = parity_parser.add_subparsers(
        dest="parity_command", metavar="COMMAND", required=True
    )
    reference = parity_commands.add_parser(
        "reference",
        help="run the golden cases through EBI's command line",
        description="For each case, one at a time, in a temporary folder: hmmsearch with "
        "treegrafter.sh's flags, then EBI's console script, treegrafter run -e 0.00000001 "
        "--print-go, with the active release. Each case's output replaces "
        "parity/GOLDENS/CASE/result.tsv in the golden folder once it has run, or "
        "parity/GOLDENS-arm64/ on arm64.",
    )
    add_parity_options(reference)
    check = parity_commands.add_parser(
        "check",
        help="check the engine against the reference's outputs",
        description="Graft each case with the engine, and compare its hit, field by field, with "
        "the one the reference's result.tsv gives, with - as no value: the arm64 copy on arm64, "
        "if there is one. Prints each case's time and every difference, and exits with status 1 "
        "if any case differs or has no reference output.",
    )
    add_parity_options(check)

    data_parser = commands.add_parser(
        "data",
        help="pin, fetch and verify the library and annotation releases",
        description="The treegrafter data: PANTHER 19's TreeGrafter library, one tarball on "
        "data.pantherdb.org, and the PAINT annotation releases. The engine's data.json pins the "
        "tarball, its member prefix, its number of families and the sha256 of library.sha256, "
        "which lists every kept file's sha256.",
    )
    data_commands = data_parser.add_subparsers(
        dest="data_command", metavar="COMMAND", required=True
    )
    manifest = data_commands.add_parser(
        "manifest",
        help="pin the library from its tarball, or an annotation release from its file",
        description="Without --release: write the library's part of data.json from its tarball, "
        "reading it once as a stream, without unpacking it, and keep the releases data.json "
        "already pins. The same tarball gives the same bytes. Writes nothing, and names each "
        "problem, if a member is outside the prefix or isn't in the library's layout, or a family "
        "lacks one of its three tree files. With --release DATE: pin that release from its "
        "PAINT_TreeGrafter_Annotations_TOTAL.txt.gz: its size and sha256, the GO release its "
        "README states, and the sha256 of its prepared files' list. It's prepared with EBI's "
        "prepare in a temporary folder, against the data folder's library, which must match the "
        "pin, and refused, naming them, if any tree node has no entry.",
    )
    manifest.add_argument(
        "file",
        type=Path,
        metavar="FILE",
        help="PANTHER19.0_data_trees_hmms_only.tar.gz, or with --release, the release's "
        "PAINT_TreeGrafter_Annotations_TOTAL.txt.gz",
    )
    manifest.add_argument(
        "--url",
        metavar="URL",
        help="where it is published: needed for the library; for a release, by default, "
        f"{data.RELEASE_URL}",
    )
    manifest.add_argument(
        "--release", metavar="DATE", help="pin the annotation release of this date, YYYY-MM-DD"
    )
    manifest.add_argument(
        "--readme",
        type=Path,
        metavar="FILE",
        help=f"with --release, a local copy of the release's README (default: {data.PAINT}/"
        "19.0/DATE/README)",
    )
    add_data_dir_option(manifest)
    manifest.add_argument(
        "--prefix",
        default=data.PREFIX,
        metavar="PREFIX",
        help=f"the folder every member is below (default: PANTHER 19's, {data.PREFIX})",
    )
    add_manifest_option(manifest)

    fetch = data_commands.add_parser(
        "fetch",
        help="fetch the pinned library and an annotation release into the data folder",
        description="Put the pinned library under treegrafter/19/ in the data folder, then make "
        "an annotation release the active one. The library is streamed from its URL, or read "
        "from a local copy, keeping only what grafting reads: famhmm/binHmm and each family's "
        ".AN.fasta, .bifurcate.newick and .newick, with library.sha256. Its size and sha256, and "
        "every kept file, are checked before anything moves into place, and nothing is "
        "downloaded when the folder already matches. The release is the pinned one of the date "
        "given, or the one paint/current/ holds, resolved by its sha256. Unless it's already "
        "prepared and verified, it's downloaded or read from a local copy, checked, prepared "
        "with EBI's prepare, checked to have an entry for every tree node, and checked against "
        "the pin, before it's moved into annotations/DATE/ and made active.",
    )
    add_data_dir_option(fetch)
    add_manifest_option(fetch)
    fetch.add_argument(
        "--library",
        type=Path,
        metavar="FILE",
        help="a local copy of the library's tarball, instead of streaming it from its URL",
    )
    fetch.add_argument(
        "--annotations",
        default=data.CURRENT,
        metavar="DATE",
        help="the release to make active: a pinned date, YYYY-MM-DD, or current, the one "
        "paint/current/ holds (default: current)",
    )
    fetch.add_argument(
        "--annotation-file",
        type=Path,
        metavar="FILE",
        help="a local copy of the release's PAINT_TreeGrafter_Annotations_TOTAL.txt.gz; with "
        "current, it's resolved to its pinned date by its sha256",
    )

    verify = data_commands.add_parser(
        "verify",
        help="check the data folder against the pin",
        description="Check the data folder against the pin: library.sha256, then every library "
        "file it lists, then the active release's prepared.sha256 and every prepared file it "
        "lists. Lists up to 20 files missing and 20 that differ, with the counts, and exits with "
        "status 1 if there is any.",
    )
    add_data_dir_option(verify)
    add_manifest_option(verify)

    fixture = data_commands.add_parser(
        "fixture",
        help="cut the test fixture from the fetched library and a pinned release",
        description="Cut the fixture the engine's tests graft against: the families' models "
        "from famhmm/binHmm, their tree files, and their lines of a pinned release's file, with a "
        "README giving each file's source and sha256. The data folder's library must match the "
        "pin, and the release's file its pin. The same library, release and families give the "
        "same bytes.",
    )
    fixture.add_argument("families", nargs="+", metavar="FAMILY", help="such as PTHR18976")
    fixture.add_argument("--release", required=True, metavar="DATE", help="a pinned release")
    fixture.add_argument(
        "--annotation-file",
        type=Path,
        required=True,
        metavar="FILE",
        help="the release's PAINT_TreeGrafter_Annotations_TOTAL.txt.gz",
    )
    fixture.add_argument(
        "--out", type=Path, required=True, metavar="DIR", help="the fixture's folder, new"
    )
    add_data_dir_option(fixture)
    add_manifest_option(fixture)


def add_parity_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--goldens",
        choices=parity.GOLDEN_SETS,
        default="fixture",
        help="the goldens: fixture, made on the committed fixture, or full, on the full library "
        "in the data folder (default: fixture)",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        metavar="DIR",
        default=parity.GOLDEN,
        help=f"the golden folder, with cases.json (default: {parity.GOLDEN})",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        metavar="DIR",
        default=parity.FIXTURE,
        help=f"the fixture, for the fixture set (default: {parity.FIXTURE})",
    )
    add_data_dir_option(parser)
    parser.add_argument(
        "--case",
        action="append",
        metavar="NAME",
        help="this case only; repeat for more (default: every case)",
    )


def add_manifest_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--manifest",
        type=Path,
        metavar="FILE",
        default=data.MANIFEST,
        help="the pin (default: the engine's treegrafter/data.json)",
    )


def add_data_dir_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help=f"the data folder, holding treegrafter/19/ (default: ${DATA_DIR_VARIABLE})",
    )


def run(args: argparse.Namespace) -> int:
    match args.treegrafter_command:
        case "score":
            return run_score(args)
        case "parity":
            return run_parity(args)
        case "data":
            return run_data(args)
        case _:
            raise AssertionError(f"unhandled command: treegrafter {args.treegrafter_command}")


def run_data(args: argparse.Namespace) -> int:
    command = f"panther-engine treegrafter data {args.data_command}"
    try:
        match args.data_command:
            case "manifest":
                return run_manifest(args)
            case "fetch":
                return run_fetch(args)
            case "fixture":
                files = data.build_fixture(
                    args.families,
                    release=args.release,
                    annotation_file=args.annotation_file,
                    out=args.out,
                    folder=args.data_dir,
                    manifest=args.manifest,
                )
                print(f"wrote {len(files)} files to {args.out}")
            case "verify":
                mismatches = data.verify_folder(args.data_dir, manifest=args.manifest)
                print(
                    f"{len(mismatches.missing):,} missing and {len(mismatches.differing):,} "
                    "differing"
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
        data.TreegrafterDataError,
        DownloadError,
        DataFolderError,
        ManifestError,
        OSError,
    ) as error:
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    return 0


def run_manifest(args: argparse.Namespace) -> int:
    if args.release is None:
        if args.url is None:
            raise data.TreegrafterDataError("pinning the library needs --url")
        pinned = data.manifest(args.file, url=args.url, prefix=args.prefix, out=args.manifest)
        print(
            f"wrote {args.manifest}: {data.family_count(pinned):,} families, with their files in "
            "library.sha256"
        )
        return 0
    release = data.pin_release(
        args.release,
        args.file,
        readme=args.readme,
        url=args.url,
        folder=args.data_dir,
        manifest=args.manifest,
    )
    print(
        f"wrote {args.manifest}: release {release.date}, GO release {release.go_release}, "
        f"{release.size:,} bytes, sha256 {release.sha256}"
    )
    return 0


def run_fetch(args: argparse.Namespace) -> int:
    if data.fetch_library(args.data_dir, manifest=args.manifest, tarball=args.library):
        print("fetched the treegrafter library, and checked every file")
    else:
        print("the treegrafter library is already there: nothing to fetch")
    fetched = data.fetch_release(
        args.data_dir,
        manifest=args.manifest,
        annotations=args.annotations,
        annotation_file=args.annotation_file,
    )
    if fetched.resolved_current:
        print(f"current is release {fetched.date}")
    if fetched.prepared:
        print(f"prepared release {fetched.date}, with an entry for every tree node")
    else:
        print(f"release {fetched.date} is already prepared, and matches the pin")
    print(f"release {fetched.date} is active")
    return 0


def run_score(args: argparse.Namespace) -> int:
    started = time.monotonic()
    try:
        text = sys.stdin.read() if args.fasta == "-" else Path(args.fasta).read_text("utf-8")
        result = score(
            TreegrafterInput(read_protein(text)), data_dir=args.data_dir, timeout=args.timeout
        )
    except (
        ValueError,
        InputError,
        TimeLimitError,
        TreegrafterError,
        MissingDataError,
        DataFolderError,
        OSError,
    ) as error:
        print(f"panther-engine treegrafter score: {error}", file=sys.stderr)
        return 1
    print_result(result, as_json=args.json)
    if args.usage:
        print(f"wall time: {time.monotonic() - started:.1f} s", file=sys.stderr)
        print(f"peak memory of the tools: {peak_memory_mib():,.0f} MiB", file=sys.stderr)
    return 0


def print_result(result: TreegrafterResult, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(dataclasses.asdict(result), indent=2))
        return
    if result.hit is None:
        print("No hit")
    else:
        hit = result.hit
        for field in dataclasses.fields(hit):
            value: object = getattr(hit, field.name)
            if field.name == "go_terms":
                shown = ",".join(hit.go_terms) or "-"
            else:
                shown = "-" if value is None else str(value)
            print(f"{field.name}\t{shown}")
    print(f"annotations\t{result.annotations}")


def run_parity(args: argparse.Namespace) -> int:
    command = f"panther-engine treegrafter parity {args.parity_command}"
    try:
        match args.parity_command:
            case "reference":
                names = parity.run_reference(
                    args.golden, args.goldens, args.data_dir, args.case, fixture=args.fixture
                )
                print(f"wrote {len(names)} cases to {args.golden / parity.PARITY}")
            case "check":
                checks = parity.run_check(
                    args.golden, args.goldens, args.data_dir, args.case, fixture=args.fixture
                )
                for checked in checks:
                    print(f"{checked.name}: {checked.seconds:.1f} s")
                    for difference in checked.differences:
                        print(f"  {difference}")
                differing = [checked for checked in checks if checked.differences]
                print(f"{len(checks) - len(differing)} of {len(checks)} cases match")
                return 1 if differing else 0
            case _:
                raise AssertionError(f"unhandled command: {command}")
    except (
        parity.ParityError,
        data.TreegrafterDataError,
        DataFolderError,
        MissingDataError,
        OSError,
    ) as error:
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    return 0
