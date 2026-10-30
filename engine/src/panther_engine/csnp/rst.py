"""The `.rst` file of a family: PAML codeml's supplemental output. Three parts of it are read.

- **The 12th line:** the branch list, `parent..child` tokens separated by spaces.
- **The 15th line:** the tree for TreeView, such as `((2_AN12, 21_AN13) 34 , 19_AN14) 33 ;`.
  Leaves are written `node_ANn`; each internal node is the number after its `)`.
- **The sequence list:** from the line `List of extant and reconstructed sequences` to a line
  containing `Overall`, or the end of the file. Each sequence is a line of its own: `AN<n>`, spaces,
  and the aligned sequence with a space after every block of 10.

The two lines are read by position, as the legacy scorer reads them (`SCORE-9`), and their shape is
checked. The format is in the legacy behaviour spec §3.5.
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass

from panther_engine.csnp.library import LibraryFormatError, numbered

BRANCH_LINE = 12
TREE_LINE = 15
SEQUENCES_START = "List of extant and reconstructed sequences"
SEQUENCES_END = "Overall"

BRANCH_LIST = re.compile(r" *[0-9]+\.\.[0-9]+(?: +[0-9]+\.\.[0-9]+)* *")
BRANCH = re.compile(r"([0-9]+)\.\.([0-9]+)")
TREE_TOKEN = re.compile(r" *(?:([(),;])|([0-9]+)_AN([0-9]+)|([0-9]+))")
# PAML writes a space after every full block of 10, so a sequence whose length is a multiple of 10
# ends with a space.
SEQUENCE_LINE = re.compile(r"AN([0-9]+) +((?:[A-Z\-]{10} )*[A-Z\-]{1,9}|(?:[A-Z\-]{10} )+)")
SEQUENCE_COUNT = re.compile(r" +[0-9]+ +[0-9]+")


@dataclass(frozen=True)
class TreeViewTree:
    """The 15th line: node numbers in order of appearance, and each leaf's AN."""

    nodes: tuple[int, ...]
    leaves: dict[int, int]


@dataclass(frozen=True)
class RstFile:
    branches: tuple[tuple[int, int], ...]
    """(parent, child) pairs, in the order of the 12th line."""
    tree: TreeViewTree
    sequences: dict[int, str]
    """Each AN's aligned sequence, without its label and spaces. Gaps are `-`."""


def read_rst(lines: Iterable[str], name: str) -> RstFile:
    branches: tuple[tuple[int, int], ...] | None = None
    tree: TreeViewTree | None = None
    sequences: dict[int, str] = {}
    in_sequences = False
    found_sequences = False
    last = 0
    for number, line in numbered(lines, name):
        last = number
        if number == BRANCH_LINE:
            branches = read_branches(line, name)
        elif number == TREE_LINE:
            tree = read_tree(line, name)
        elif line == SEQUENCES_START and not found_sequences:
            in_sequences = found_sequences = True
        elif in_sequences:
            if SEQUENCES_END in line:
                in_sequences = False
            else:
                _read_sequence(number, line, sequences, name)
    if last == 0:
        raise LibraryFormatError(name, None, "empty file")
    if branches is None or tree is None:
        missing = BRANCH_LINE if branches is None else TREE_LINE
        raise LibraryFormatError(name, None, f"ends at line {last}, before line {missing}")
    if not found_sequences:
        raise LibraryFormatError(name, None, f"no line {SEQUENCES_START!r}")
    if not sequences:
        raise LibraryFormatError(name, None, "no sequences in the sequence list")
    return RstFile(branches, tree, sequences)


def read_branches(line: str, name: str) -> tuple[tuple[int, int], ...]:
    """The 12th line's (parent, child) pairs."""
    if BRANCH_LIST.fullmatch(line) is None:
        raise LibraryFormatError(name, BRANCH_LINE, "not a branch list of 'parent..child' tokens")
    return tuple((int(parent), int(child)) for parent, child in BRANCH.findall(line))


def read_tree(line: str, name: str) -> TreeViewTree:
    """The 15th line's node numbers, in order of appearance, checking that it is one tree."""
    nodes: list[int] = []
    leaves: dict[int, int] = {}
    depth = 0
    expect_subtree = True
    position = 0
    finished = False
    while position < len(line) and not finished:
        match = TREE_TOKEN.match(line, position)
        if match is None:
            break
        position = match.end()
        symbol, leaf, an, internal = match.groups()
        if expect_subtree and symbol == "(":
            depth += 1
        elif expect_subtree and leaf is not None and an is not None:
            nodes.append(int(leaf))
            leaves[int(leaf)] = int(an)
            expect_subtree = False
        elif not expect_subtree and symbol == "," and depth > 0:
            expect_subtree = True
        elif not expect_subtree and symbol == ")" and depth > 0:
            depth -= 1
            label = TREE_TOKEN.match(line, position)
            if label is None or label[4] is None:
                break
            position = label.end()
            nodes.append(int(label[4]))
        elif not expect_subtree and symbol == ";" and depth == 0:
            finished = True
        elif internal is not None or symbol is not None or leaf is not None:
            break
    if not finished or line[position:].strip(" "):
        raise LibraryFormatError(
            name, TREE_LINE, f"not a TreeView tree at character {position + 1}"
        )
    if len(set(nodes)) != len(nodes):
        raise LibraryFormatError(name, TREE_LINE, "a node number appears twice in the tree")
    return TreeViewTree(tuple(nodes), leaves)


def _read_sequence(number: int, line: str, sequences: dict[int, str], name: str) -> None:
    if not line or SEQUENCE_COUNT.fullmatch(line):
        return
    match = SEQUENCE_LINE.fullmatch(line)
    if match is None:
        raise LibraryFormatError(
            name, number, "not a sequence line 'AN<n>' followed by blocks of 10"
        )
    an = int(match[1])
    if an in sequences:
        raise LibraryFormatError(name, number, f"a second sequence for AN{an}")
    sequences[an] = match[2].replace(" ", "")
