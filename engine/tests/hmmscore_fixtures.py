"""The hmmscore library files in fixtures/hmmscore/, which its README describes.

`PTHR99999` is one family: its model, named `PTHR99999.orig.30.pir`; two subfamily models, SF1 and
SF2; and SF3, a byte-for-byte copy of the family's model. `globals/binHmm` holds SF2's, the
family's and SF1's models, in that order, and `globals/names.tab` a line for each of the four.
"""

import gzip
import io
import tarfile
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath

FIXTURES = Path(__file__).parent / "fixtures" / "hmmscore"
FAMILY = "PTHR99999"
FAMILY_MODEL = "books/PTHR99999/hmmer.hmm"
SF1_MODEL = "books/PTHR99999/SF1/hmmer.hmm"
SF2_MODEL = "books/PTHR99999/SF2/hmmer.hmm"
SF3_MODEL = "books/PTHR99999/SF3/hmmer.hmm"
NAMES = "globals/names.tab"
BINHMM = "globals/binHmm"
PRESSED = ("globals/binHmm.h3f", "globals/binHmm.h3i", "globals/binHmm.h3m", "globals/binHmm.h3p")
# PANTHER 19's member prefix, and stand-ins for the files scoring never reads.
PREFIX = "target/famlib/rel/PANTHER19.0_altVersion/hmmscoring/PANTHER19.0/"
README = b"PANTHER 19.0 HMM library: a stand-in for the tests\n"
CLUSTER = b">P1\nMKV\n"
TREE = b"(P1:0.1,P2:0.2);\n"


def data(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def text(name: str) -> str:
    return data(name).decode("latin-1")


def lines(name: str) -> list[str]:
    """The file's lines, with their line endings, as the readers take them."""
    return text(name).splitlines(keepends=True)


def edited(name: str, old: str, new: str) -> list[str]:
    """The lines of `name` with `old`, which must appear once, replaced by `new`."""
    content = text(name)
    assert content.count(old) == 1, old
    return content.replace(old, new).splitlines(keepends=True)


def clean_library(*, flat: bool = False) -> dict[str, bytes]:
    """The clean library's files by their paths below the prefix: the README, names.tab, the
    pressed binHmm (and the flat one too, if `flat`), PTHR99999's four model files, its
    cluster.pir and its tree.tree."""
    files = {"README": README, NAMES: data(NAMES)}
    if flat:
        files[BINHMM] = data(BINHMM)
    files.update({name: data(name) for name in PRESSED})
    files.update({name: data(name) for name in (FAMILY_MODEL, SF1_MODEL, SF2_MODEL, SF3_MODEL)})
    files["books/PTHR99999/cluster.pir"] = CLUSTER
    files["books/PTHR99999/tree.tree"] = TREE
    return files


def library_tarball(
    path: Path,
    files: Mapping[str, bytes],
    *,
    prefix: str = PREFIX,
    extra: Iterable[tuple[str, bytes]] = (),
    folders: Iterable[str] = (),
) -> Path:
    """A gzipped tar of `files` under `prefix`, in the PANTHER tarball's order: the prefix's own
    folder, the README, globals/, then books/, each folder before its files. Then `extra` files
    and `folders`, at their own paths, not under the prefix."""
    order = sorted(files, key=lambda name: (not name.startswith("README"), name))
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
        for name in order:
            parents = reversed(PurePosixPath(name).parents)
            for parent in (str(each) for each in parents if str(each) != "."):
                folder(prefix + parent)
            file(prefix + name, files[name])
        for name, content in extra:
            file(name, content)
        for name in folders:
            folder(name)
    return path
