"""A hand-made treegrafter library and annotation release, for the data tests.

Three families in the real library's layout (`PANTHER19.0_data/`), with trees small enough to read:

- `PTHR10000`: nodes AN0 to AN4, leaves AN2, AN3 and AN4;
- `PTHR10001`: a multifurcation, AN0 over AN1, AN2 and AN3, made bifurcating with BI0;
- `PTHR10002`: leaf AN4 is in its trees, but not in its alignment, like the real PTHR11034.

The annotation lines cover every node, in the real file's format: the node, then the subfamily, GO
terms and protein class, then the graft point's public ID.
"""

import gzip
import io
import tarfile
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath

PREFIX = "PANTHER19.0_data/"
FAMILIES = ("PTHR10000", "PTHR10001", "PTHR10002")
BINHMM = "famhmm/binHmm"
PRESSED = tuple(f"{BINHMM}.{suffix}" for suffix in ("h3f", "h3i", "h3m", "h3p"))
README = "PAINT_Annotations_README"
TREES = {
    "PTHR10000": (
        "((AN2:0.1,AN3:0.2)AN1:0.3,AN4:0.4)AN0;\n",
        "((AN2:0.1,AN3:0.2)AN1:0.3,AN4:0.4)AN0;\n",
        ("AN2", "AN3", "AN4"),
    ),
    "PTHR10001": (
        "(AN1:0.1,AN2:0.2,AN3:0.3)AN0;\n",
        "((AN1:0.1,AN2:0.2)BI0:0.0,AN3:0.3)AN0;\n",
        ("AN1", "AN2", "AN3"),
    ),
    "PTHR10002": (
        "((AN1:0.1,AN2:0.2)AN3:0.1,AN4:0.2)AN0;\n",
        "((AN1:0.1,AN2:0.2)AN3:0.1,AN4)AN0;\n",
        ("AN1", "AN2"),
    ),
}
NODES = {
    "PTHR10000": ("AN0", "AN1", "AN2", "AN3", "AN4"),
    "PTHR10001": ("AN0", "AN1", "AN2", "AN3"),
    "PTHR10002": ("AN0", "AN1", "AN2", "AN3", "AN4"),
}


def model(family: str) -> bytes:
    """A stand-in for a family's HMM in binHmm: its NAME line is what matters here."""
    return (
        f"HMMER3/f [3.1b2 | February 2015]\nNAME  {family}.orig.30.pir\nLENG  10\nHMM\n//\n"
    ).encode("ascii")


def alignment(leaves: Iterable[str]) -> bytes:
    return b"".join(f">{leaf}\nMKV-LAAGIV\n".encode("ascii") for leaf in leaves)


def library_files() -> dict[str, bytes]:
    """The library's files by their paths below the prefix: those the fetch keeps, and those it
    skips (the pressed files, the `.tree` files and the PAINT README)."""
    files: dict[str, bytes] = {README: b"### PAINT_TreeGrafter_Annotations_TOTAL.txt README ###\n"}
    for family in FAMILIES:
        newick, bifurcate, leaves = TREES[family]
        files[f"Tree_MSF/{family}.AN.fasta"] = alignment(leaves)
        files[f"Tree_MSF/{family}.bifurcate.newick"] = bifurcate.encode("ascii")
        files[f"Tree_MSF/{family}.newick"] = newick.encode("ascii")
        files[f"Tree_MSF/{family}.tree"] = newick.replace(";", "[&&NHX];").encode("ascii")
    files[BINHMM] = b"".join(model(family) for family in FAMILIES)
    files.update({name: name.encode("ascii") for name in PRESSED})
    return files


def kept(files: Mapping[str, bytes]) -> dict[str, bytes]:
    """The files the fetch keeps, of `files`."""
    return {
        path: content
        for path, content in files.items()
        if path == BINHMM or path.endswith((".AN.fasta", ".newick"))
    }


def library_tarball(
    path: Path,
    files: Mapping[str, bytes],
    *,
    prefix: str = PREFIX,
    extra: Iterable[tuple[str, bytes]] = (),
    folders: Iterable[str] = (),
) -> Path:
    """A gzipped tar of `files` under `prefix`, in the real tarball's order: the prefix's folder,
    the README, Tree_MSF/, then famhmm/ and an empty tmp/, each folder before its files. Then
    `extra` files and `folders`, at their own paths, not under the prefix."""

    def order(name: str) -> tuple[int, str]:
        return (0 if name == README else 1 if name.startswith("Tree_MSF/") else 2, name)

    with gzip.open(path, "wb") as compressed, tarfile.open(fileobj=compressed, mode="w") as tar:
        added: set[str] = set()

        def folder(name: str) -> None:
            if name not in added:
                added.add(name)
                info = tarfile.TarInfo(name)
                info.type = tarfile.DIRTYPE
                tar.addfile(info)

        def file(name: str, content: bytes) -> None:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))

        folder(prefix.rstrip("/"))
        for name in sorted(files, key=order):
            parents = reversed(PurePosixPath(name).parents)
            for parent in (str(each) for each in parents if str(each) != "."):
                folder(prefix + parent)
            file(prefix + name, files[name])
        folder(prefix + "tmp")
        for name, content in extra:
            file(name, content)
        for name in folders:
            folder(name)
    return path


# The annotation release


def annotation_lines(*, skip: Iterable[str] = (), subfamily: str = "SF1") -> list[str]:
    """A line for each node of each family, but those in `skip`, such as `PTHR10000:AN4`. Every
    node of a family is in `subfamily`, with two GO terms and a protein class."""
    skipped = set(skip)
    lines: list[str] = []
    number = 0
    for family in FAMILIES:
        for node in NODES[family]:
            number += 1
            if f"{family}:{node}" in skipped:
                continue
            annotations = f"{family}:{subfamily}  GO:0005515;GO:0008150;  PC00052;"
            lines.append(f"{family}:{node}\t{annotations}\tPTN{number:09d}\n")
    return lines


def annotation_file(path: Path, lines: Iterable[str]) -> Path:
    """The lines, gzipped reproducibly, as `PAINT_TreeGrafter_Annotations_TOTAL.txt.gz` is."""
    with path.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as out:
        out.write("".join(lines).encode("ascii"))
    return path


def release_readme(go_release: str) -> bytes:
    """A release's README: the GO release is on its second line."""
    return (
        f"GO source files downloaded on 2026-08-17\nGO release date: {go_release}\n"
        f"https://release.geneontology.org/{go_release}/annotations/gaf/HUMAN-uniprot.gaf.gz\n"
    ).encode("ascii")
