"""The `.orig.tree` file of a family: the family tree with each node's AN, event and taxon.

- **The first line** is the tree in NHX Newick. Leaves are written `AN<n>:<length>`. Internal nodes
  are written `(…)<:length>[&&NHX:Ev=0>1:S=<taxon>:ID=AN<n>]`, the attributes in any order and
  each optional. `Ev=0>1` marks a speciation, `1>0` a duplication.
- **Each following line** gives a leaf's gene: `AN<n>:SPECIES|GENE|UniProtKB=ACC;`.

The format is in the legacy behaviour spec §3.5. Nodes are listed in order of appearance: a leaf at
its name, an internal node at its closing parenthesis.

The tree lines of 135 split parts end with one `)` too many, just before the `;`. That `)` is read
as absent, and `OrigTree.extra_parenthesis` says so; any other imbalance is an error.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from panther_engine.csnp.library import LibraryFormatError, numbered

LEAF = re.compile(r"AN([0-9]+)")
LENGTH = re.compile(r":[0-9]+(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?")
ATTRIBUTES = re.compile(r"\[&&NHX((?::[A-Za-z]+=[^:\[\]]*)*)\]")
AN_ID = re.compile(r"AN([0-9]+)")
GENE_LINE = re.compile(r"AN([0-9]+):([^|;]+\|[^|;]+\|[^|;]+);")


@dataclass(frozen=True)
class TreeNode:
    an: int | None
    """None for an internal node without an `ID`."""
    leaf: bool
    attributes: tuple[tuple[str, str], ...]

    def attribute(self, key: str) -> str | None:
        return next((value for name, value in self.attributes if name == key), None)

    @property
    def event(self) -> str | None:
        """The `Ev` attribute, such as `0>1`, or None where the node has none."""
        return self.attribute("Ev")

    @property
    def taxon(self) -> str | None:
        """The `S` attribute, or None."""
        return self.attribute("S")


@dataclass(frozen=True)
class OrigTree:
    nodes: tuple[TreeNode, ...]
    """Every node, in order of appearance on the first line."""
    genes: dict[int, str]
    """Each leaf AN's gene identifier, `SPECIES|GENE|UniProtKB=ACC`, in file order."""
    extra_parenthesis: bool = False
    """The tree line ended with one unmatched `)` before its `;`."""

    @property
    def ans(self) -> tuple[int | None, ...]:
        return tuple(node.an for node in self.nodes)


def read_orig_tree(lines: Iterable[str], name: str) -> OrigTree:
    rows = numbered(lines, name)
    first = next(rows, None)
    if first is None:
        raise LibraryFormatError(name, None, "empty file")
    nodes, extra = read_tree_line(first[1], name)
    leaves = {node.an for node in nodes if node.leaf}
    genes: dict[int, str] = {}
    for number, line in rows:
        match = GENE_LINE.fullmatch(line)
        if match is None:
            raise LibraryFormatError(name, number, "not a gene line 'AN<n>:SPECIES|GENE|ACC;'")
        an = int(match[1])
        if an not in leaves:
            raise LibraryFormatError(name, number, f"AN{an} isn't a leaf of the tree")
        if an in genes:
            raise LibraryFormatError(name, number, f"a second gene line for AN{an}")
        genes[an] = match[2]
    without = [an for an in sorted(a for a in leaves if a is not None) if an not in genes]
    if without:
        raise LibraryFormatError(name, None, f"leaf AN{without[0]} has no gene line")
    return OrigTree(nodes, genes, extra)


def read_tree_line(line: str, name: str) -> tuple[tuple[TreeNode, ...], bool]:
    """The tree's nodes, and whether it ended with one unmatched `)` before its `;`."""
    extra = line.endswith(");") and line.count(")") == line.count("(") + 1
    if extra:
        line = line[:-2] + ";"
    nodes: list[TreeNode] = []
    depth = 0
    position = 0
    expect_subtree = True
    while position < len(line):
        character = line[position]
        if expect_subtree and character == "(":
            depth += 1
            position += 1
        elif expect_subtree and (leaf := LEAF.match(line, position)):
            position = leaf.end()
            node, position = _node(line, position, int(leaf[1]), name)
            nodes.append(node)
            expect_subtree = False
        elif not expect_subtree and character == "," and depth > 0:
            expect_subtree = True
            position += 1
        elif not expect_subtree and character == ")" and depth > 0:
            depth -= 1
            node, position = _node(line, position + 1, None, name)
            nodes.append(node)
        elif not expect_subtree and character == ";" and depth == 0:
            position += 1
            break
        else:
            raise LibraryFormatError(name, 1, f"not an NHX tree at character {position + 1}")
    else:
        raise LibraryFormatError(name, 1, "the tree doesn't end with ';'")
    if position != len(line):
        raise LibraryFormatError(name, 1, f"text after the tree's ';' at character {position + 1}")
    ans = [node.an for node in nodes if node.an is not None]
    if len(set(ans)) != len(ans):
        raise LibraryFormatError(name, 1, "an AN appears twice in the tree")
    return tuple(nodes), extra


def _node(line: str, position: int, leaf_an: int | None, name: str) -> tuple[TreeNode, int]:
    """A node's optional length and NHX attributes, from `position`."""
    if length := LENGTH.match(line, position):
        position = length.end()
    pairs: list[tuple[str, str]] = []
    if attributes := ATTRIBUTES.match(line, position):
        position = attributes.end()
        pairs = [
            (key, value)
            for key, value in (item.split("=", 1) for item in attributes[1].split(":")[1:])
        ]
        if len({key for key, _ in pairs}) != len(pairs):
            raise LibraryFormatError(name, 1, f"an attribute given twice at character {position}")
    elif line.startswith("[", position):
        raise LibraryFormatError(name, 1, f"not NHX attributes at character {position + 1}")
    an = leaf_an
    identifier = next((value for key, value in pairs if key == "ID"), None)
    if identifier is not None:
        match = AN_ID.fullmatch(identifier)
        if match is None or (leaf_an is not None and int(match[1]) != leaf_an):
            raise LibraryFormatError(name, 1, f"ID={identifier} at character {position}")
        an = int(match[1])
    return TreeNode(an, leaf_an is not None, tuple(pairs)), position
