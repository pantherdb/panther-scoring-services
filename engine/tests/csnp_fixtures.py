"""The hand-written cSNP library files in fixtures/csnp/.

`PTHR00001` is a clean family: three leaves (nodes 1-3, AN2-AN4), the root (node 4, AN0) and one
internal node (node 5, AN1), with two sites. The other files are broken copies of it.
"""

import gzip
import io
import tarfile
from collections.abc import Iterable
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "csnp"
FAMILY = "PTHR00001"


def text(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("latin-1")


def lines(name: str) -> list[str]:
    """The file's lines, with their line endings, as the readers take them."""
    return text(name).splitlines(keepends=True)


def edited(name: str, old: str, new: str) -> list[str]:
    """The lines of `name` with `old`, which must appear once, replaced by `new`."""
    content = text(name)
    assert content.count(old) == 1, old
    return content.replace(old, new).splitlines(keepends=True)


def family_files(
    family: str,
    *,
    paml: str = f"{FAMILY}.paml",
    rst: str = f"{FAMILY}.rst",
    tree: str = f"{FAMILY}.orig.tree",
) -> list[tuple[str, bytes]]:
    """Archive members for `family`, in a `PAML_RST/` folder, from the named fixture files."""
    return [
        (f"PAML_RST/{family}.paml", (FIXTURES / paml).read_bytes()),
        (f"PAML_RST/{family}.rst", (FIXTURES / rst).read_bytes()),
        (f"PAML_RST/{family}.orig.tree", (FIXTURES / tree).read_bytes()),
    ]


def joined(content: list[str]) -> bytes:
    return "".join(content).encode("latin-1")


def make_tar(path: Path, members: Iterable[tuple[str, bytes]]) -> Path:
    """A gzipped tar at `path` holding `members`, in the order given."""
    with gzip.open(path, "wb") as compressed, tarfile.open(fileobj=compressed, mode="w") as tar:
        for name, content in members:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return path
