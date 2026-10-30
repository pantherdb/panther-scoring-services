"""Each of the Perl's readings agrees with the strict reader on the clean family, and differs on a
copy made to trigger it."""

import pytest
from csnp_fixtures import FAMILY, edited, lines

from panther_engine.csnp import legacy
from panther_engine.csnp.library import LibraryFormatError
from panther_engine.csnp.orig_tree import read_orig_tree
from panther_engine.csnp.paml import read_header
from panther_engine.csnp.rst import read_rst
from panther_engine.csnp.species import read_species

PAML = f"{FAMILY}.paml"
RST = f"{FAMILY}.rst"
TREE = f"{FAMILY}.orig.tree"
SPECIES = "species.nhx"


def strict_starts(paml: list[str]) -> dict[str, int]:
    """Each leaf AN's own column, as the strict reader gives it."""
    header = read_header(paml, PAML)
    return {str(header.ans[leaf - 1]): leaf for leaf in header.leaves}


def legacy_starts(paml: list[str], ans: list[str]) -> dict[str, int | None]:
    rows = legacy.paml_rows(paml)
    return {an: legacy.start_node(rows, an) for an in ans}


def strict_pairing(rst: list[str], tree: list[str]) -> dict[int, int | None]:
    nodes = read_rst(rst, RST).tree.nodes
    return dict(zip(nodes, read_orig_tree(tree, TREE).ans, strict=True))


def legacy_pairing(rst: list[str], tree: list[str]) -> dict[int, int | None]:
    nodes = legacy.tree_nodes(legacy.rst_lines(rst)[1])
    return legacy.pairing(nodes, legacy.tree_ans(tree[0]))


def strict_events(tree: list[str]) -> dict[int, tuple[str, str]]:
    return {
        node.an: (node.event, node.taxon)
        for node in read_orig_tree(tree, TREE).nodes
        if node.an is not None and node.event is not None and node.taxon is not None
    }


# Start column (SCORE-2)


def test_start_column_agrees_on_the_clean_family() -> None:
    starts = strict_starts(lines(PAML))

    assert legacy_starts(lines(PAML), list(starts)) == starts


def test_start_column_differs_where_an_internal_label_collides_with_a_leafs() -> None:
    paml = edited(PAML, "Node5 AN1", "Node5 AN2")

    assert strict_starts(paml)["2"] == 1
    assert legacy_starts(paml, ["2"]) == {"2": 5}


def test_start_nodes_gives_the_same_as_start_node_for_every_an() -> None:
    paml = edited(PAML, "Node5 AN1", "Node5 AN2")
    rows = legacy.paml_rows(paml)

    every = legacy.start_nodes(rows)

    assert every == {an: legacy.start_node(rows, an) for an in ["0", "2", "3", "4"]}


# Root


def test_root_agrees_on_the_clean_family() -> None:
    assert legacy.root_node(legacy.paml_rows(lines(PAML))) == read_header(lines(PAML), PAML).root


def stray_node_header() -> list[str]:
    """30 columns rooted at column 2. Column 3's parent is Node30, which holds `Node3`."""
    columns = range(1, 31)
    parents = ["Node2"] * 30
    parents[2] = "Node30"
    return [
        "Node number," + ",".join(f"Node{column} AN{column + 100}" for column in columns) + "\n",
        "root number," + ",".join(parents) + "\n",
        "Branch," + ",".join("0.1" for _ in columns) + "\n",
    ]


def test_root_differs_where_a_parent_cell_holds_a_stray_node_number() -> None:
    header = stray_node_header()

    assert read_header(header, PAML).root == 2
    assert legacy.root_node(legacy.paml_rows(header)) == 3


# Branch list (SCORE-9)


def strict_branches(rst: list[str]) -> dict[int, int]:
    return {child: parent for parent, child in read_rst(rst, RST).branches}


def test_branch_list_agrees_on_the_clean_family() -> None:
    rst = lines(RST)

    assert legacy.branches(legacy.rst_lines(rst)[0]) == strict_branches(rst)


def test_branch_list_differs_where_a_token_is_malformed() -> None:
    rst = edited(RST, "5..2 ", "5.2  ")

    with pytest.raises(LibraryFormatError, match="not a branch list"):
        read_rst(rst, RST)
    assert legacy.branches(legacy.rst_lines(rst)[0]) == {5: 4, 1: 5, 3: 4}


# Tree nodes and the pairing of nodes with ANs


def test_tree_nodes_agree_on_the_clean_family() -> None:
    rst = lines(RST)

    assert legacy.tree_nodes(legacy.rst_lines(rst)[1]) == list(read_rst(rst, RST).tree.nodes)


def test_tree_nodes_differ_where_the_tree_has_no_semicolon() -> None:
    rst = edited(RST, ") 4 ;", ") 4")

    with pytest.raises(LibraryFormatError):
        read_rst(rst, RST)
    assert legacy.tree_nodes(legacy.rst_lines(rst)[1]) == [1, 2, 5, 3]


def test_an_order_and_pairing_agree_on_the_clean_family() -> None:
    tree = lines(TREE)

    assert legacy.tree_ans(tree[0]) == list(read_orig_tree(tree, TREE).ans)
    assert legacy_pairing(lines(RST), tree) == strict_pairing(lines(RST), tree)


def test_an_order_and_pairing_differ_where_a_leaf_has_no_length() -> None:
    tree = edited(TREE, ",AN4:0.300)", ",AN4)")

    assert read_orig_tree(tree, TREE).ans == (2, 3, 1, 4, 0)
    assert legacy.tree_ans(tree[0]) == [2, 3, 1, 0]
    assert legacy_pairing(lines(RST), tree) == {1: 2, 2: 3, 5: 1, 3: 0, 4: None}
    assert strict_pairing(lines(RST), tree) == {1: 2, 2: 3, 5: 1, 3: 4, 4: 0}


# Events and taxa (DATA-3)


def test_events_agree_on_the_clean_family() -> None:
    tree = lines(TREE)

    assert legacy.events(tree[0]) == strict_events(tree)


def test_events_differ_where_the_attributes_are_in_another_order() -> None:
    tree = edited(TREE, "Ev=0>1:S=Homo-Pan:ID=AN1", "S=Homo-Pan:Ev=0>1:ID=AN1")

    assert strict_events(tree) == {1: ("0>1", "Homo-Pan")}
    assert legacy.events(tree[0]) == {}


# Sequences


def test_sequences_agree_on_the_clean_family() -> None:
    rst = lines(RST)
    strict = read_rst(rst, RST).sequences

    assert {an: legacy.sequence(rst, str(an)) for an in strict} == strict
    assert legacy.sequences(rst) == {str(an): sequence for an, sequence in strict.items()}


def test_sequences_keep_a_trailing_carriage_return() -> None:
    rst = [line.replace("\n", "\r\n") for line in lines(RST)]

    with pytest.raises(LibraryFormatError, match="carriage return"):
        read_rst(rst, RST)
    assert legacy.sequence(rst, "4") == "MG\r"


def test_the_sequence_list_ends_on_the_line_with_overall() -> None:
    rst = lines(RST)
    rst[-1:-1] = ["Overall\n"]

    assert legacy.sequence(rst, "3") == "M-"
    assert legacy.sequence(rst, "4") is None


# Gene lookup (DATA-2, SCORE-8)


def test_gene_lookup_agrees_on_the_clean_family() -> None:
    tree = lines(TREE)
    lookup = legacy.GeneLookup(tree)

    for an, gene in read_orig_tree(tree, TREE).genes.items():
        assert legacy.find_an(tree, gene) == an
        assert lookup.find_an(gene) == an


def test_gene_lookup_differs_where_a_gene_is_a_prefix_of_an_earlier_one() -> None:
    tree = edited(
        TREE,
        "AN2:HUMAN|HGNC=1|UniProtKB=P00001;",
        "AN2:PANTR|Ensembl=ENSPTRG00000000001|UniProtKB=P000021;",
    )
    gene = read_orig_tree(tree, TREE).genes[3]

    assert legacy.find_an(tree, gene) == 2
    assert legacy.GeneLookup(tree).find_an(gene) == 2


def test_gene_lookup_reads_a_dot_as_any_character() -> None:
    tree = lines(TREE)

    assert legacy.find_an(tree, "HUMAN|HGNC=.|UniProtKB=P00001") == 2
    assert legacy.GeneLookup(tree).find_an("HUMAN|HGNC=.|UniProtKB=P00001") == 2


def test_a_gene_perl_would_interpolate_is_refused() -> None:
    with pytest.raises(ValueError, match="isn't emulated"):
        legacy.find_an(lines(TREE), "HUMAN|HGNC=$x|UniProtKB=P00001")


# Species ages


def test_species_ages_agree_on_the_species_fixture() -> None:
    species = lines(SPECIES)

    assert legacy.species_ages(species[0]) == read_species(species, SPECIES)


def test_species_ages_differ_where_the_age_comes_first() -> None:
    species = edited(SPECIES, "[&&NHX:S=Homo-Pan:A=6]", "[&&NHX:A=6:S=Homo-Pan]")

    assert read_species(species, SPECIES)["Homo-Pan"] == 6
    assert "Homo-Pan" not in legacy.species_ages(species[0])


# Line ends


def test_a_carriage_return_stays_in_the_last_header_label() -> None:
    paml = lines("crlf.paml")

    with pytest.raises(LibraryFormatError, match="carriage return"):
        read_header(paml, "crlf.paml")
    assert legacy.paml_rows(paml)[0][-1] == "Node5 AN1\r"
    assert legacy.start_node(legacy.paml_rows(paml), "1") is None
    assert legacy.start_node(legacy.paml_rows(lines(PAML)), "1") == 5
