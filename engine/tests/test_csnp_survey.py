import hashlib
import random
from pathlib import Path

import pytest
from csnp_fixtures import FAMILY, FIXTURES, edited, family_files, joined, make_tar

from panther_engine.csnp.survey import Report, report_json, survey

SPECIES = FIXTURES / "species.nhx"
CLEAN = family_files(FAMILY)


def member(family: str, kind: str, content: list[str]) -> tuple[str, bytes]:
    return (f"PAML_RST/{family}.{kind}", joined(content))


def replaced(members: list[tuple[str, bytes]], new: tuple[str, bytes]) -> list[tuple[str, bytes]]:
    return [new if name == new[0] else (name, content) for name, content in members]


def broken_families() -> list[tuple[str, bytes]]:
    """The clean family, and one family per broken fixture or variant, every file in place."""
    members = [*CLEAN]
    for family, kind, fixture in [
        ("PTHR00004", "paml", "no-root.paml"),
        ("PTHR00005", "paml", "bad-probability.paml"),
        ("PTHR00006", "paml", "crlf.paml"),
        ("PTHR00007", "rst", "empty.rst"),
        ("PTHR00008", "rst", "branch-list-off-line.rst"),
        ("PTHR00009", "orig.tree", "no-event.orig.tree"),
    ]:
        files = family_files(family)
        members += replaced(files, (f"PAML_RST/{family}.{kind}", (FIXTURES / fixture).read_bytes()))
    # Missing its .rst
    members += [file for file in family_files("PTHR00002") if not file[0].endswith(".rst")]
    # A split part whose base family has no files
    members += family_files("PTHR00003_1")
    return members


def surveyed(tmp_path: Path, members: list[tuple[str, bytes]], **inputs: Path) -> Report:
    archive = make_tar(tmp_path / "library.tar.gz", members)
    return survey(archive, species=inputs.get("species"), blast=inputs.get("blast"))


def families(report: Report, key: str) -> list[str]:
    return sorted(example.family for example in report.checks[key].examples)


def test_the_report_gives_the_archives_sha256_and_family_count(tmp_path: Path) -> None:
    report = surveyed(tmp_path, broken_families())

    archive = tmp_path / "library.tar.gz"
    assert report.archive.sha256 == hashlib.sha256(archive.read_bytes()).hexdigest()
    assert report.archive.size == archive.stat().st_size
    assert report.families == 9
    # The CRLF copy is the clean .paml with a carriage return on each of its 7 lines.
    assert report.largest_paml == ("PTHR00006", (FIXTURES / "crlf.paml").stat().st_size)


def test_a_family_missing_its_rst_is_reported(tmp_path: Path) -> None:
    report = surveyed(tmp_path, broken_families())

    assert families(report, "missing-rst") == ["PTHR00002"]
    assert report.checks["missing-paml"].families == 0


def test_a_split_part_whose_base_has_no_files_is_reported(tmp_path: Path) -> None:
    report = surveyed(tmp_path, broken_families())

    result = report.checks["split-without-base"]
    assert families(report, "split-without-base") == ["PTHR00003_1"]
    assert (result.families, result.items) == (1, 1)
    assert result.examples[0].detail == "PTHR00003"


def test_each_broken_file_is_reported_with_the_readers_error(tmp_path: Path) -> None:
    report = surveyed(tmp_path, broken_families())

    rejected = {
        example.family: example.detail
        for key in ("rejected-paml", "rejected-rst", "rejected-orig-tree")
        for example in report.checks[key].examples
    }
    assert sorted(rejected) == ["PTHR00004", "PTHR00005", "PTHR00006", "PTHR00007", "PTHR00008"]
    assert "no root" in rejected["PTHR00004"]
    assert "'abc' isn't a probability" in rejected["PTHR00005"]
    assert "carriage return" in rejected["PTHR00006"]
    assert "empty file" in rejected["PTHR00007"]
    assert "line 12: not a branch list" in rejected["PTHR00008"]
    assert families(report, "carriage-return") == ["PTHR00006"]


def test_every_rejected_file_is_listed_with_its_error(tmp_path: Path) -> None:
    report = surveyed(tmp_path, broken_families())

    assert [name for name, _ in report.rejected] == [
        "PTHR00004.paml",
        "PTHR00005.paml",
        "PTHR00006.paml",
        "PTHR00007.rst",
        "PTHR00008.rst",
    ]
    assert report.rejected[0][1] == "PTHR00004.paml, line 2: no root: no column is its own parent"
    assert report_json(report)["rejected"] == [
        {"file": name, "error": error} for name, error in report.rejected
    ]


def test_a_tree_with_one_unmatched_parenthesis_is_counted_and_read(tmp_path: Path) -> None:
    tree = member(FAMILY, "orig.tree", edited(f"{FAMILY}.orig.tree", "ID=AN0];", "ID=AN0]);"))

    report = surveyed(tmp_path, replaced(CLEAN, tree))

    assert families(report, "extra-parenthesis") == [FAMILY]
    assert report.found() == ["extra-parenthesis"]


def test_a_node_without_an_event_is_counted_not_rejected(tmp_path: Path) -> None:
    report = surveyed(tmp_path, broken_families())

    assert families(report, "event-none") == ["PTHR00009"]
    assert report.checks["event-none"].items == 1
    assert report.events["none"] == 1


def test_files_that_agree_give_zero_for_every_check(tmp_path: Path) -> None:
    report = surveyed(tmp_path, CLEAN, species=SPECIES)

    assert report.found() == []
    assert report.families == 1
    assert (report.rooted, report.leaves) == (1, 3)


def test_files_in_any_order_give_the_same_report(tmp_path: Path) -> None:
    members = broken_families()
    # S311 flags the pseudo-random generator: a repeatable shuffle is what's wanted here.
    shuffled = random.Random(1).sample(members, len(members))  # noqa: S311
    (tmp_path / "in-order").mkdir()
    (tmp_path / "shuffled").mkdir()

    in_order = report_json(surveyed(tmp_path / "in-order", members))
    out_of_order = report_json(surveyed(tmp_path / "shuffled", shuffled))

    del in_order["archive"], out_of_order["archive"]
    assert out_of_order == in_order


def test_members_are_matched_by_file_name_in_any_folder(tmp_path: Path) -> None:
    members = [(name.replace("PAML_RST/", "csnp/9/PAML_RST/"), content) for name, content in CLEAN]
    members.append(("csnp/9/PSEP-COPYRIGHT.txt", b"copyright\n"))

    report = surveyed(tmp_path, members)

    assert report.families == 1
    assert report.other_members == 1
    assert report.found() == []


@pytest.mark.parametrize(
    ("kind", "old", "new"),
    [
        ("paml", "root number,Node5,Node5,", "root number,Node4,Node5,"),
        ("rst", "  4..5     5..1     5..2 ", "  4..5     5..1     4..2 "),
    ],
)
def test_parents_that_disagree_are_reported(tmp_path: Path, kind: str, old: str, new: str) -> None:
    changed = member(FAMILY, kind, edited(f"{FAMILY}.{kind}", old, new))

    report = surveyed(tmp_path, replaced(CLEAN, changed))

    assert families(report, "parents") == [FAMILY]


def test_sequences_of_the_wrong_length_are_reported(tmp_path: Path) -> None:
    changed = member(FAMILY, "rst", edited(f"{FAMILY}.rst", f"{'AN4':<18}MG", f"{'AN4':<18}MGA"))

    report = surveyed(tmp_path, replaced(CLEAN, changed))

    assert families(report, "sequence-length") == [FAMILY]
    assert report.checks["sequence-length"].examples[0].detail == "AN4: 3 residues, 2 sites"


def test_a_leaf_label_that_isnt_a_tree_leaf_is_reported(tmp_path: Path) -> None:
    paml = member(FAMILY, "paml", edited(f"{FAMILY}.paml", "Node3 AN4", "Node3 AN9"))

    report = surveyed(tmp_path, replaced(CLEAN, paml))

    assert families(report, "leaf-labels") == [FAMILY]
    assert report.checks["leaf-labels"].items == 2


def test_node_counts_that_differ_are_reported(tmp_path: Path) -> None:
    # One more internal node, without attributes, around the root
    content = joined(edited(f"{FAMILY}.orig.tree", "ID=AN0];", "ID=AN0]);"))
    tree = (f"PAML_RST/{FAMILY}.orig.tree", b"(" + content)

    report = surveyed(tmp_path, replaced(CLEAN, tree))

    assert families(report, "node-count") == [FAMILY]


def test_a_colliding_label_is_counted_under_the_start_column(tmp_path: Path) -> None:
    paml = member(FAMILY, "paml", edited(f"{FAMILY}.paml", "Node5 AN1", "Node5 AN2"))

    report = surveyed(tmp_path, replaced(CLEAN, paml))

    result = report.checks["legacy-start-column"]
    assert (result.families, result.items) == (1, 1)
    assert result.examples[0].detail == "1 of 3; AN2: column 1, legacy 5"


def test_an_event_the_legacy_pattern_misses_is_counted(tmp_path: Path) -> None:
    tree = member(
        FAMILY,
        "orig.tree",
        edited(f"{FAMILY}.orig.tree", "Ev=0>1:S=Homo-Pan:ID=AN1", "S=Homo-Pan:Ev=0>1:ID=AN1"),
    )

    report = surveyed(tmp_path, replaced(CLEAN, tree))

    assert families(report, "legacy-events") == [FAMILY]
    assert report.checks["legacy-events"].items == 1


def test_a_leaf_without_a_length_is_counted_under_an_order_and_pairing(tmp_path: Path) -> None:
    tree = member(FAMILY, "orig.tree", edited(f"{FAMILY}.orig.tree", ",AN4:0.300)", ",AN4)"))

    report = surveyed(tmp_path, replaced(CLEAN, tree))

    assert families(report, "legacy-an-order") == [FAMILY]
    assert families(report, "legacy-pairing") == [FAMILY]


def test_variants_in_the_paml_are_counted(tmp_path: Path) -> None:
    paml = edited(
        f"{FAMILY}.paml",
        "Node5 AN1\nroot number,Node5,Node5,Node4,Node4,Node4\nBranch,0.10000,0.20000,0.30000,"
        "100,0.05000\nSite 1,M,M,M,M,M\nProbability of site 1,1,1,1,1.000,0.999",
        "Node5 \nroot number,Node5,Node5,Node4,Node4,Node4\nBranch,0.10000,0.20000,0.30000,"
        "100,0.05000\nSite 1,M,M,M,\x00,M\nProbability of site 1,1,1,1, -nan,0.999",
    )

    report = surveyed(tmp_path, replaced(CLEAN, member(FAMILY, "paml", paml)))

    assert report.checks["unreconstructed"].items == 1
    assert report.checks["internal-without-an"].items == 1
    assert report.checks["rejected-paml"].families == 0


def test_a_taxon_missing_from_the_species_tree_is_counted_and_listed(tmp_path: Path) -> None:
    tree = member(
        FAMILY, "orig.tree", edited(f"{FAMILY}.orig.tree", "S=Homo-Pan", "S=Artiodactyla")
    )

    report = surveyed(tmp_path, replaced(CLEAN, tree), species=SPECIES)

    assert families(report, "missing-taxon") == [FAMILY]
    assert report.checks["missing-taxon"].items == 1
    assert report.missing_taxa == {"Artiodactyla": 1}


def test_without_a_species_tree_the_taxon_checks_are_not_run(tmp_path: Path) -> None:
    report = surveyed(tmp_path, CLEAN)

    assert not report.checks["missing-taxon"].checked
    assert not report.checks["legacy-species-ages"].checked


def test_examples_are_the_smallest_families_first(tmp_path: Path) -> None:
    members: list[tuple[str, bytes]] = []
    broken = (FIXTURES / "branch-list-off-line.rst").read_bytes()
    for number in range(7):
        files = family_files(f"PTHR1000{number}")
        # Rejected at line 12, so the lines added after it only change the family's size.
        members += replaced(files, (files[1][0], broken + b"\n" * (10 * (7 - number))))

    report = surveyed(tmp_path, members)

    examples = report.checks["rejected-rst"].examples
    assert [example.family for example in examples] == [f"PTHR1000{n}" for n in range(6, 1, -1)]
    assert report.checks["rejected-rst"].families == 7


# The BLAST database (DATA-2, SCORE-8)


def blast_archive(path: Path, headers: list[str]) -> Path:
    fasta = "".join(f">{header}\nMAGS\n" for header in headers).encode()
    return make_tar(path, [("blast/blast.phr", b"\0" * 10), ("blast/blast.fasta", fasta)])


def test_a_blast_entry_whose_family_has_no_paml_is_counted(tmp_path: Path) -> None:
    blast = blast_archive(
        tmp_path / "blast.tar.gz",
        [
            f"HUMAN|HGNC=1|UniProtKB=P00001:{FAMILY}:SF1",
            "HUMAN|HGNC=9|UniProtKB=P00009:PTHR09999:SF1",
            "HUMAN|HGNC=8|UniProtKB=P00008:AN12:PTHR09998",
        ],
    )

    report = surveyed(tmp_path, CLEAN, blast=blast)

    assert report.blast_entries == 3
    assert report.checks["blast-no-paml"].items == 2
    assert sorted(families(report, "blast-no-paml")) == ["AN12", "PTHR09999"]
    assert report.checks["blast-not-a-family"].items == 1
    assert report.checks["blast-gene-not-found"].items == 0
    assert report.checks["blast-legacy-lookup"].items == 0


def test_a_blast_gene_that_is_a_prefix_of_an_earlier_gene_line_is_counted(tmp_path: Path) -> None:
    tree = edited(
        f"{FAMILY}.orig.tree",
        "AN2:HUMAN|HGNC=1|UniProtKB=P00001;",
        "AN2:PANTR|Ensembl=ENSPTRG00000000001|UniProtKB=P000021;",
    )
    blast = blast_archive(
        tmp_path / "blast.tar.gz",
        [
            f"PANTR|Ensembl=ENSPTRG00000000001|UniProtKB=P00002:{FAMILY}:SF1",
            f"MOUSE|MGI=MGI=1|UniProtKB=P00003:{FAMILY}:SF1",
            f"HUMAN|HGNC=7|UniProtKB=P00007:{FAMILY}:SF1",
        ],
    )

    report = surveyed(tmp_path, replaced(CLEAN, member(FAMILY, "orig.tree", tree)), blast=blast)

    lookup = report.checks["blast-legacy-lookup"]
    assert (lookup.families, lookup.items) == (1, 1)
    assert lookup.examples[0].detail.startswith(
        "PANTR|Ensembl=ENSPTRG00000000001|UniProtKB=P00002: AN3, legacy 2"
    )
    assert report.checks["blast-gene-not-found"].items == 1
