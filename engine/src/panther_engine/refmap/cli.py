"""The `panther-engine refmap` subcommands: mapping IDs, the data's manifest, fetching and
verifying it, and parity with the legacy `map_panther.pl`."""

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from panther_engine.core.data import DATA_DIR_VARIABLE, DataFolderError, MissingDataError, data_root
from panther_engine.core.download import DownloadError
from panther_engine.core.manifest import ManifestError, checksums
from panther_engine.refmap import data, parity
from panther_engine.refmap.mapping import RefmapInput, map_ids, read_id_list, render
from panther_engine.refmap.organisms import ORGANISM_NAMES, ORGANISMS


def configure(parser: argparse.ArgumentParser) -> None:
    """Add the `refmap` subcommands to `parser`, the `refmap` command's parser."""
    commands = parser.add_subparsers(dest="refmap_command", metavar="COMMAND", required=True)

    map_parser = commands.add_parser(
        "map",
        help="map IDs to PANTHER families for one organism",
        description="Map IDs to PANTHER families and subfamilies for one organism, as the API's "
        "refmap job does. Prints one line per ID, in order: the ID and its PANTHER ID, or NOHIT, "
        "separated by a tab. The lookup is exact, as the legacy map_panther.pl's was.",
    )
    map_parser.add_argument(
        "--organism", required=True, metavar="CODE", help="the organism's code, such as ENDPU"
    )
    ids = map_parser.add_mutually_exclusive_group(required=True)
    ids.add_argument("ids", nargs="*", default=[], metavar="ID", help="an ID, such as U1G4Q5")
    ids.add_argument(
        "--file",
        type=Path,
        metavar="FILE",
        help="a list of IDs, one per line, as map_panther.pl read one: the text before the "
        "first tab, with every carriage return removed",
    )
    map_parser.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help=f"the data folder, holding refmap/19/ (default: ${DATA_DIR_VARIABLE})",
    )
    map_parser.add_argument(
        "--json", action="store_true", help="print the result as JSON, as map_ids() returns it"
    )

    data_parser = commands.add_parser(
        "data",
        help="pin, fetch or verify the refmap data",
        description="The refmap data: PANTHER 19's classification files, one per Reference "
        "Proteome organism, and their stats, from data.pantherdb.org. The engine's data.json "
        "pins the release and lists every file, under the data folder at refmap/19/. Each "
        "classification file is saved under its organism's code.",
    )
    data_commands = data_parser.add_subparsers(
        dest="data_command", metavar="COMMAND", required=True
    )
    manifest = data_commands.add_parser(
        "manifest",
        help="write the manifest and the organism list from a release",
        description="Write the manifest and the organism list from a release's tarball and "
        "stats, reading the tarball as a stream, without unpacking it. The same inputs give the "
        "same bytes. Writes nothing, and names the problem, if stats and the tarball disagree, "
        "or if a code is repeated or can't be a file name.",
    )
    manifest.add_argument(
        "tarball", type=Path, metavar="TARBALL", help="panther_classifications.tar.gz"
    )
    manifest.add_argument("stats", type=Path, metavar="STATS", help="the release's stats")
    manifest.add_argument(
        "--tarball-url", required=True, metavar="URL", help="where the tarball is published"
    )
    manifest.add_argument(
        "--stats-url", required=True, metavar="URL", help="where stats is published"
    )
    manifest.add_argument(
        "--manifest",
        type=Path,
        metavar="FILE",
        default=data.MANIFEST,
        help="the manifest to write (default: the engine's refmap/data.json)",
    )
    manifest.add_argument(
        "--organisms",
        type=Path,
        metavar="FILE",
        default=ORGANISMS,
        help="the organism list to write (default: the engine's refmap/organisms.json)",
    )

    fetch = data_commands.add_parser(
        "fetch",
        help="download the pinned release, check it and save it in the data folder",
        description="Download the pinned tarball and stats, or take local copies, and check each "
        "one's size and sha256. Then save each classification file under its organism's code, "
        "at refmap/19/panther_classification/<code>, and check every file against the manifest. "
        "Does nothing when the folder already matches, and writes nothing under refmap/19/ if "
        "anything fails.",
    )
    add_data_options(fetch)
    fetch.add_argument(
        "--organisms",
        type=Path,
        metavar="FILE",
        default=ORGANISMS,
        help="the organism list, which gives each file's code (default: the engine's "
        "refmap/organisms.json)",
    )
    fetch.add_argument(
        "--tarball",
        type=Path,
        metavar="FILE",
        help="a local copy of the tarball, instead of downloading it",
    )
    fetch.add_argument(
        "--stats",
        type=Path,
        metavar="FILE",
        help="a local copy of stats, instead of downloading it",
    )
    verify = data_commands.add_parser(
        "verify",
        help="check the data folder against the manifest",
        description="Check the data folder against the manifest. Lists each file that is missing "
        "or differs, and exits with status 1 if there is any. Files the manifest doesn't list "
        "are ignored.",
    )
    add_data_options(verify)

    parity_parser = commands.add_parser(
        "parity",
        help="run the golden cases through the legacy Perl, check the port against them",
        description="Parity with RefProteomeMapper's map_panther.pl at 4fc6a09: run the golden "
        "cases through the Perl in the refmap-reference image, and check the port against its "
        "output. See docs/parity/golden-setup.md.",
    )
    parity_commands = parity_parser.add_subparsers(
        dest="parity_command", metavar="COMMAND", required=True
    )
    reference = parity_commands.add_parser(
        "reference",
        help="run the golden cases through map_panther.pl (refmap-reference image only)",
        description="Run each golden case through map_panther.pl, and write its standard output, "
        "byte for byte, to OUT/<case>.out in the golden folder. Stops before running anything if "
        "a published organism's classification file is missing from the data folder.",
    )
    add_parity_options(reference)
    reference.add_argument(
        "--script",
        type=Path,
        metavar="FILE",
        default=parity.SCRIPT,
        help=f"map_panther.pl (default: {parity.SCRIPT})",
    )

    check = parity_commands.add_parser(
        "check",
        help="check the port against the golden outputs",
        description="Map each golden case with the port, and compare each mapping with the "
        "first two fields of the reference's line, NOHIT for none. A case the port refuses must "
        "raise the error its divergence row names, with a message holding the part the case "
        "gives. Lists every line that differs, by case and line, and exits with status 1 if any "
        "does. The cases on an organism need the refmap data; the made-up files and the refused "
        "cases don't. Without a data folder, those are still checked, the others are listed as "
        "not checked, and the command exits with status 1.",
    )
    add_parity_options(check)

    full = parity_commands.add_parser(
        "full",
        help="compare the Perl and the port on every ID of every organism (refmap-reference "
        "image only)",
        description="For each organism, one at a time: every ID of its classification file, in "
        "file order, then extras from a generator seeded with SEED:CODE (up to 20 of its IDs "
        "repeated, 20 lower-cased, 20 with -2, 20 with .1, and 20 from the next organism's file), "
        "through map_panther.pl and the port. Reports the IDs compared and every line that "
        "differs, for each organism, and exits with status 1 if any does.",
    )
    full.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help=f"the data folder, holding refmap/19/ (default: ${DATA_DIR_VARIABLE})",
    )
    full.add_argument("--seed", default=parity.SEED, help=f"the seed (default: {parity.SEED})")
    full.add_argument(
        "--organism",
        action="append",
        metavar="CODE",
        help="run this organism only; repeat for more. Its extras still come from the next "
        "organism in the list, as in the full run (default: every organism, in the list's order)",
    )
    full.add_argument(
        "--script",
        type=Path,
        metavar="FILE",
        default=parity.SCRIPT,
        help=f"map_panther.pl (default: {parity.SCRIPT})",
    )


def add_parity_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help=f"the data folder, holding refmap/19/ (default: ${DATA_DIR_VARIABLE})",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        metavar="DIR",
        default=parity.GOLDEN,
        help=f"the golden folder, with cases.json (default: {parity.GOLDEN})",
    )


def add_data_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help=f"the data folder, holding refmap/19/ (default: ${DATA_DIR_VARIABLE})",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        metavar="FILE",
        default=data.MANIFEST,
        help="the manifest (default: the engine's refmap/data.json)",
    )


def run(args: argparse.Namespace) -> int:
    match args.refmap_command:
        case "map":
            return run_map(args)
        case "data":
            return run_data(args)
        case "parity":
            return run_parity(args)
        case _:
            raise AssertionError(f"unhandled command: refmap {args.refmap_command}")


def run_map(args: argparse.Namespace) -> int:
    try:
        ids = read_id_list(args.file.read_bytes()) if args.file else tuple(args.ids)
        result = map_ids(RefmapInput(args.organism, ids), data_dir=args.data_dir)
    except (ValueError, MissingDataError, DataFolderError, OSError) as error:
        print(f"panther-engine refmap map: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(dataclasses.asdict(result), indent=2))
    else:
        for mapping in result.mappings:
            print(render(mapping))
    return 0


def run_data(args: argparse.Namespace) -> int:
    command = f"panther-engine refmap data {args.data_command}"
    try:
        match args.data_command:
            case "manifest":
                built = data.build(
                    args.tarball,
                    args.stats,
                    tarball_url=args.tarball_url,
                    stats_url=args.stats_url,
                    manifest=args.manifest,
                    organisms=args.organisms,
                )
                files = checksums(built)
                print(f"wrote {args.manifest} ({len(files):,} files) and {args.organisms}")
            case "fetch":
                fetched = data.fetch(
                    args.data_dir,
                    manifest=args.manifest,
                    organisms=args.organisms,
                    tarball=args.tarball,
                    stats=args.stats,
                )
                if fetched:
                    print("fetched the refmap data, and checked every file")
                else:
                    print("the refmap data is already there: nothing to fetch")
            case "verify":
                mismatches = data.verify_folder(args.data_dir, manifest=args.manifest)
                for path in mismatches.missing:
                    print(f"missing: {path}")
                for path in mismatches.differing:
                    print(f"differs: {path}")
                if not mismatches.ok:
                    return 1
                print("every file matches the manifest")
            case _:
                raise AssertionError(f"unhandled command: {command}")
    except (data.RefmapDataError, DownloadError, DataFolderError, ManifestError, OSError) as error:
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    return 0


def run_parity(args: argparse.Namespace) -> int:
    command = f"panther-engine refmap parity {args.parity_command}"
    try:
        match args.parity_command:
            case "reference":
                reference = parity.Reference.find(args.script)
                counts = parity.run_reference(reference, args.golden, data_root(args.data_dir))
                for name, lines in counts.items():
                    print(f"{name}: {lines:,} lines")
                print(f"wrote {len(counts)} cases to {args.golden / parity.OUT}")
            case "check":
                return run_check(args)
            case "full":
                return run_full(args, data_root(args.data_dir))
            case _:
                raise AssertionError(f"unhandled command: {command}")
    except (parity.ParityError, DataFolderError, MissingDataError, OSError) as error:
        print(f"{command}: {error}", file=sys.stderr)
        return 1
    return 0


def run_check(args: argparse.Namespace) -> int:
    """Check every case. Without a data folder, the cases that need it are listed as not checked,
    the others are checked, and the command fails."""
    folder: Path | None
    try:
        folder, no_data = data_root(args.data_dir), ""
    except DataFolderError as error:
        folder, no_data = None, str(error)
    differences: list[str] = []
    unchecked = 0
    for case in parity.read_cases(args.golden):
        if folder is None and parity.needs_data(case):
            print(f"{case.name}: not checked: it needs the refmap data")
            unchecked += 1
            continue
        found = parity.check_case(case, args.golden, folder)
        lines = len(parity.golden_lines(args.golden / parity.OUT / f"{case.name}.out"))
        kind = f"refused ({case.refused}: {case.message!r})" if case.refused else f"{lines:,} lines"
        print(f"{case.name}: {kind}, {len(found)} differences")
        differences += found
    for difference in differences:
        print(difference)
    if unchecked:
        print(f"{unchecked} cases not checked: {no_data}", file=sys.stderr)
    if differences:
        print(f"{len(differences)} differences", file=sys.stderr)
    return 1 if differences or unchecked else 0


def run_full(args: argparse.Namespace, folder: Path) -> int:
    """The full run, printing each organism's line as it finishes."""
    reference = parity.Reference.find(args.script)
    codes: list[str] = args.organism or list(ORGANISM_NAMES)
    organisms = ids = differences = 0
    for run in parity.run_full(reference, folder, codes, args.seed):
        organisms += 1
        ids += run.ids
        differences += len(run.differences)
        print(f"{run.code}: {run.ids:,} IDs, {len(run.differences)} differences", flush=True)
        for difference in run.differences[: parity.EXTRAS]:
            print(difference)
        if len(run.differences) > parity.EXTRAS:
            print(f"{run.code}: and {len(run.differences) - parity.EXTRAS:,} more")
    summary = f"{organisms:,} organisms, {ids:,} IDs compared"
    if differences:
        print(f"{summary}, {differences:,} differences", file=sys.stderr)
        return 1
    print(f"{summary}, no differences")
    return 0
