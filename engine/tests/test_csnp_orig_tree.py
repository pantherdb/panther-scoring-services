import pytest
from csnp_fixtures import edited, lines

from panther_engine.csnp.library import LibraryFormatError
from panther_engine.csnp.orig_tree import read_orig_tree

TREE = "PTHR00001.orig.tree"


def test_the_tree_line_gives_every_an_in_order_and_each_internal_nodes_event_and_taxon() -> None:
    tree = read_orig_tree(lines(TREE), TREE)

    assert tree.ans == (2, 3, 1, 4, 0)
    assert [node.leaf for node in tree.nodes] == [True, True, False, True, False]
    internal = {node.an: (node.event, node.taxon) for node in tree.nodes if not node.leaf}
    assert internal == {1: ("0>1", "Homo-Pan"), 0: ("1>0", None)}


def test_a_node_without_an_event_reports_it_as_absent() -> None:
    tree = read_orig_tree(lines("no-event.orig.tree"), "no-event.orig.tree")

    node = next(node for node in tree.nodes if node.an == 1)
    assert node.event is None
    assert node.taxon == "Homo-Pan"


def test_gene_lines_give_each_leaf_its_gene_identifier() -> None:
    tree = read_orig_tree(lines(TREE), TREE)

    assert tree.genes == {
        2: "HUMAN|HGNC=1|UniProtKB=P00001",
        3: "PANTR|Ensembl=ENSPTRG00000000001|UniProtKB=P00002",
        4: "MOUSE|MGI=MGI=1|UniProtKB=P00003",
    }


def test_attributes_in_another_order_are_read_all_the_same() -> None:
    tree = read_orig_tree(
        edited(TREE, "[&&NHX:Ev=0>1:S=Homo-Pan:ID=AN1]", "[&&NHX:ID=AN1:S=Homo-Pan:Ev=0>1]"), TREE
    )

    node = next(node for node in tree.nodes if node.an == 1)
    assert (node.event, node.taxon) == ("0>1", "Homo-Pan")


def test_an_internal_node_without_an_id_has_no_an() -> None:
    tree = read_orig_tree(edited(TREE, "[&&NHX:Ev=1>0:ID=AN0]", ""), TREE)

    assert tree.ans == (2, 3, 1, 4, None)


def test_one_unmatched_parenthesis_before_the_semicolon_is_read_as_absent() -> None:
    # As in 135 split parts, PTHR23125_2 among them
    tree = read_orig_tree(edited(TREE, "ID=AN0];", "ID=AN0]);"), TREE)

    assert tree.ans == (2, 3, 1, 4, 0)
    assert tree.extra_parenthesis
    assert not read_orig_tree(lines(TREE), TREE).extra_parenthesis


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (",AN4:0.300)", ",AN4:0.300))"),  # one ( too few, and not at the end
        ("ID=AN0];", "ID=AN0]));"),  # two ) too many at the end
        ("[&&NHX:Ev=1>0:ID=AN0];", "[&&NHX:Ev=1>0:ID=AN0]"),  # no ;
        ("(AN2:0.100,", "(AN2:0.100,,"),  # an empty node
        ("ID=AN1]", "ID=1]"),  # an ID that isn't an AN
        ("Ev=1>0:ID=AN0", "Ev=1>0:Ev=0>1:ID=AN0"),  # an attribute twice
        ("ID=AN1]", "ID=AN2]"),  # an AN twice
    ],
)
def test_a_malformed_tree_line_is_an_error_at_line_1(old: str, new: str) -> None:
    with pytest.raises(LibraryFormatError) as raised:
        read_orig_tree(edited(TREE, old, new), TREE)

    assert raised.value.line == 1


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("AN4:MOUSE", "AN1:MOUSE", "AN1 isn't a leaf"),
        ("AN4:MOUSE", "AN3:MOUSE", "a second gene line for AN3"),
        ("|UniProtKB=P00003;", "|UniProtKB=P00003", "not a gene line"),
    ],
)
def test_a_bad_gene_line_is_an_error_at_its_line(old: str, new: str, message: str) -> None:
    with pytest.raises(LibraryFormatError, match=message) as raised:
        read_orig_tree(edited(TREE, old, new), TREE)

    assert raised.value.line == 4


def test_a_leaf_without_a_gene_line_is_an_error() -> None:
    with pytest.raises(LibraryFormatError, match="leaf AN4 has no gene line"):
        read_orig_tree(lines(TREE)[:-1], TREE)
