"""The `panther-engine csnp` subcommands: scoring, the library survey, the data sample, and parity
with the legacy scripts."""

import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path

from panther_engine.core.data import DATA_DIR_VARIABLE, DataFolderError, service_folder
from panther_engine.core.errors import InputError
from panther_engine.core.manifest import ManifestError
from panther_engine.csnp import parity, sample
from panther_engine.csnp.blast import BlastError
from panther_engine.csnp.library import LibraryFormatError
from panther_engine.csnp.scoring import SUBSTITUTION, CsnpInput, CsnpResult, score
from panther_engine.csnp.survey import SurveyError, report_json, report_text, survey

# The API's normalisation (`scoring-input`), as the legacy website's form did it: trim every
# character up to U+0020, drop one header line at the very start, and all whitespace.
TRIMMED = "".join(chr(code) for code in range(0x21))
HEADER = re.compile(r"\A>[^\n]*")
WHITESPACE = re.compile(r"[ \t\n\x0b\x0c\r]+")


def configure(parser: argparse.ArgumentParser) -> None:
    """Add the `csnp` subcommands to `parser`, the `csnp` command's parser."""
    commands = parser.add_subparsers(dest="csnp_command", metavar="COMMAND", required=True)

    score_parser = commands.add_parser(
        "score",
        help="score one protein's substitutions for one species",
        description="Score one protein's substitutions, as the API's csnp job does: BLAST+ "
        "against the PANTHER9 database, then the legacy mapping and trace-back. The sequence is "
        "normalised as the API normalises it: one header line and all whitespace removed, upper "
        "case. Prints the family, then each substitution's age, message and pDel.",
    )
    score_parser.add_argument(
        "fasta",
        type=Path,
        metavar="FASTA",
        help="one protein: FASTA with one header line, or the sequence alone",
    )
    score_parser.add_argument(
        "substitutions",
        nargs="+",
        metavar="SUBSTITUTION",
        help="a wild-type residue, a position and a residue, such as A10E",
    )
    score_parser.add_argument(
        "--species", required=True, metavar="CODE", help="a PANTHER species code, such as HUMAN"
    )
    score_parser.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help=f"the data folder, holding csnp/9/ (default: ${DATA_DIR_VARIABLE})",
    )
    score_parser.add_argument(
        "--json", action="store_true", help="print the result as JSON, as score() returns it"
    )

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
        description="The cSNP data sample: chosen families of the PAML_RST library, the PANTHER9 "
        "BLAST database, the species tree and the PSEP copyright statement, attached to a GitHub "
        "release and pinned by the engine's sample.json. It unpacks under the data folder at "
        "csnp/9/.",
    )
    sample_commands = sample_parser.add_subparsers(
        dest="sample_command", metavar="COMMAND", required=True
    )
    build = sample_commands.add_parser(
        "build",
        help="build the sample tarball and its manifest from the two archives",
        description="Build the sample tarball from PAML_RST.tar.gz and PANTHER9.blast.tar.gz, "
        "byte for byte the same each time, and write its manifest. Refuses an archive or species "
        "tree whose sha256 isn't the pinned one, and then writes nothing.",
    )
    build.add_argument("archive", type=Path, metavar="ARCHIVE", help="PAML_RST.tar.gz")
    build.add_argument(
        "--species", type=Path, metavar="FILE", required=True, help="species_pthr8_time.nhx"
    )
    build.add_argument(
        "--blast-archive",
        type=Path,
        metavar="FILE",
        required=True,
        help="PANTHER9.blast.tar.gz, for the BLAST database",
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
    build.add_argument(
        "--blast-sha256",
        metavar="HEX",
        default=sample.PINNED_BLAST,
        help="the BLAST archive's expected sha256 (default: the pin in the legacy behaviour spec)",
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

    parity_parser = commands.add_parser(
        "parity",
        help="generate parity cases, run them through the legacy scripts, check the port",
        description="Parity with the legacy cSNP scripts at cebb5ab: generate cases from the "
        "data folder's families, run them through the Perl in the csnp-reference image, and "
        "check the port's output against the Perl's. See docs/parity/golden-setup.md.",
    )
    parity_commands = parity_parser.add_subparsers(
        dest="parity_command", metavar="COMMAND", required=True
    )
    cases = parity_commands.add_parser(
        "cases",
        help="generate step-2 and step-3 cases from the data folder's families",
        description="Generate parity cases into a folder: for each family in the data folder's "
        "library, step-3 cases grouped by gene, and the step-2 cases. The same data and seed give "
        "the same files.",
    )
    cases.add_argument("out", type=Path, metavar="OUT", help="the cases folder to write")
    add_parity_options(cases)
    cases.add_argument(
        "--seed", default=parity.SEED, help=f"the random seed (default: {parity.SEED})"
    )
    cases.add_argument(
        "--genes",
        type=int,
        default=parity.GENES,
        metavar="N",
        help=f"genes per family (default: {parity.GENES})",
    )
    cases.add_argument(
        "--positions",
        type=int,
        default=parity.POSITIONS,
        metavar="N",
        help=f"positions per gene (default: {parity.POSITIONS})",
    )
    cases.add_argument(
        "--family",
        action="append",
        metavar="FAMILY",
        help="generate for this family only; repeat for more (default: every family)",
    )

    reference = parity_commands.add_parser(
        "reference",
        help="run the cases through the legacy scripts (csnp-reference image only)",
        description="First the self-check: the legacy behaviour spec's §7.3 and §7.5 inputs "
        "must give their goldens byte for byte, or nothing else runs. Then every case in the "
        "folder, one Perl process per family, each output written beside its input. Exits with "
        "status 1 if the self-check fails.",
    )
    reference.add_argument(
        "cases", type=Path, metavar="CASES", help="the cases folder, such as GOLDEN/generated"
    )
    add_parity_options(reference)
    reference.add_argument(
        "--scripts",
        type=Path,
        metavar="DIR",
        default=parity.SCRIPTS,
        help=f"the legacy scripts (default: {parity.SCRIPTS})",
    )
    reference.add_argument(
        "--family",
        action="append",
        metavar="FAMILY",
        help="run step 3 for this family only; repeat for more (default: every family)",
    )

    check = parity_commands.add_parser(
        "check",
        help="check the port against the reference's outputs",
        description="Run the port on the self-check's inputs and on every case in the folder, "
        "and compare its output with the reference's, byte for byte. Lists every case that "
        "differs, and the kinds of node the walks reached. Exits with status 1 if any differs.",
    )
    check.add_argument(
        "cases", type=Path, metavar="CASES", help="the cases folder, such as GOLDEN/generated"
    )
    add_parity_options(check)


def add_parity_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--data-dir",
        type=Path,
        metavar="DIR",
        help=f"the data folder, holding csnp/9/ (default: ${DATA_DIR_VARIABLE})",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        metavar="DIR",
        default=parity.GOLDEN,
        help=f"the golden folder, with release/ and spec/ (default: {parity.GOLDEN})",
    )


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
        case "score":
            return run_score(args)
        case "survey":
            return run_survey(args.archive, args.species, args.blast_archive, args.json)
        case "sample":
            return run_sample(args)
        case "parity":
            return run_parity(args)
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
                    blast=args.blast_archive,
                    tag=args.tag,
                    out=out,
                    manifest=args.manifest,
                    archive_sha256=args.archive_sha256,
                    species_sha256=args.species_sha256,
                    blast_sha256=args.blast_sha256,
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


def run_score(args: argparse.Namespace) -> int:
    try:
        sequence = read_protein(args.fasta.read_text(encoding="utf-8"))
        substitutions = tuple(token.upper() for token in args.substitutions)
        for token in substitutions:
            if not SUBSTITUTION.fullmatch(token):
                raise ValueError(
                    f"not a substitution: {token!r}. Write a residue letter, a position and a "
                    "residue letter, such as A10E"
                )
        result = score(CsnpInput(sequence, substitutions, args.species), data_dir=args.data_dir)
    except (
        ValueError,
        InputError,
        BlastError,
        LibraryFormatError,
        DataFolderError,
        OSError,
    ) as error:
        print(f"panther-engine csnp score: {error}", file=sys.stderr)
        return 1
    print_result(result, as_json=args.json)
    return 0


def read_protein(text: str) -> str:
    """One protein from a FASTA file, normalised as the API normalises it."""
    text = text.strip(TRIMMED)
    if text.count(">") > 1:
        raise ValueError("the file holds more than one sequence: give one protein")
    residues = WHITESPACE.sub("", HEADER.sub("", text))
    if not residues:
        raise ValueError("the file has no sequence")
    return residues.upper()


def print_result(result: CsnpResult, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(dataclasses.asdict(result), indent=2))
        return
    print(f"family\t{result.family or ''}")
    print("substitution\tage\tmessage\tpdel")
    for item in result.scores:
        age = "" if item.age is None else item.age
        print(f"{item.substitution}\t{age}\t{item.message}\t{item.pdel or ''}")


def run_parity(args: argparse.Namespace) -> int:
    command = f"panther-engine csnp parity {args.parity_command}"
    try:
        data = service_folder(sample.SERVICE, sample.VERSION, args.data_dir)
        match args.parity_command:
            case "cases":
                listed = parity.write_cases(
                    args.out,
                    data,
                    seed=args.seed,
                    genes=args.genes,
                    positions=args.positions,
                    families=args.family,
                )
                print(
                    f"wrote cases for {len(listed.step3)} families and {len(listed.step2)} "
                    f"step-2 runs to {args.out}"
                )
                return 0
            case "reference":
                return run_reference(args, data)
            case "check":
                return run_check(args, data)
            case _:
                raise AssertionError(f"unhandled command: {command}")
    except (parity.ParityError, DataFolderError, OSError) as error:
        print(f"{command}: {error}", file=sys.stderr)
        return 1


def run_reference(args: argparse.Namespace, data: Path) -> int:
    reference = parity.Reference.find(args.scripts)
    differences = parity.self_check(reference, args.golden, data, args.cases)
    for difference in differences:
        print(difference)
    if differences:
        print(f"self-check failed: {len(differences)} differences", file=sys.stderr)
        return 1
    print("self-check: spec §7.3 and §7.5 reproduced byte for byte")
    if not (args.cases / parity.CASES).exists():
        print(f"no {parity.CASES} in {args.cases}: nothing else to run")
        return 0
    for name, count in parity.run_reference(reference, args.cases, data, args.family).items():
        print(f"{name}: {count} cases")
    return 0


def run_check(args: argparse.Namespace, data: Path) -> int:
    listed = parity.read_cases(args.cases)
    differences = parity.check_self(args.golden, args.cases, data)
    print(f"self-check inputs: {len(differences)} differences")
    for run in listed.step2:
        found = parity.check_step2(args.cases, run)
        cases = len(parity.read(args.cases / parity.STEP2 / f"{run.name}.input").splitlines())
        print(f"step 2 {run.name}: {cases} cases, {len(found)} differences")
        differences += found
    for family in listed.step3:
        found = parity.check_step3(args.cases, family, data)
        cases = len(parity.read(args.cases / parity.STEP3 / f"{family}.snpparse").splitlines())
        print(f"{family}: {cases} cases, {len(found)} differences")
        differences += found
    print("walks, by kind of node: stopped at, visited")
    for kind, (stopped, visited) in parity.coverage(parity.trace_cases(args.cases, data)).items():
        print(f"  {kind}: {stopped}, {visited}")
    for difference in differences:
        print(difference)
    if differences:
        print(f"{len(differences)} differences", file=sys.stderr)
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
