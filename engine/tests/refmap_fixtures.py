"""Small refmap releases, built in a test's tmp_path: a tarball of classification files in a
`panther_classifications/` folder, as the published one is, and its `stats`.

The organisms are a few of the real ones, with made-up files. `stats` lists them out of long-name
order, as the published `stats` does, and one long name holds a `:`.
"""

import gzip
import io
import tarfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from panther_engine.cli import main

TARBALL_URL = "https://data.example.org/archive/2024-06-20/panther_classifications.tar.gz"
STATS_URL = "https://data.example.org/archive/2024-06-20/stats"
ORGANISMS: Mapping[str, bytes] = {
    "Pisum_sativum_PEA": b"P1\tPTHR00002:SF3\nP2\tNOHIT\n",
    "Endocarpon_pusillum_ENDPU": (b"U1G4Q5\tPTHR11360:SF130\nU1GLV9\tPTHR28011\nU1HQ27\tNOHIT\n"),
    "Escherichia_coli_O157:H7_ECO57": b"Q1\tPTHR00001\n",
}


@dataclass(frozen=True)
class Release:
    tarball: Path
    stats: Path


def stats_line(long_name: str, content: bytes) -> str:
    """`stats`'s line for one classification file: its lines, and those with a PANTHER ID."""
    lines = content.splitlines()
    mapped = [line for line in lines if line.split(b"\t")[1:2] != [b"NOHIT"]]
    return f"{long_name}\t{len(lines)}\t{len(mapped)}\n"


def make_release(
    folder: Path,
    organisms: Mapping[str, bytes] = ORGANISMS,
    *,
    stats: str | None = None,
    members: Iterable[tarfile.TarInfo | tuple[str, bytes]] | None = None,
) -> Release:
    """A release in `folder`. `stats` replaces the generated `stats`, and `members` the tarball's
    members, which are otherwise the folder and one file per organism."""
    folder.mkdir(parents=True, exist_ok=True)
    if members is None:
        directory = tarfile.TarInfo("panther_classifications")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o755
        members = [
            directory,
            *((f"panther_classifications/{name}", content) for name, content in organisms.items()),
        ]
    tarball = folder / "panther_classifications.tar.gz"
    with gzip.open(tarball, "wb") as compressed, tarfile.open(fileobj=compressed, mode="w") as tar:
        for member in members:
            if isinstance(member, tarfile.TarInfo):
                tar.addfile(member)
                continue
            name, content = member
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    path = folder / "stats"
    if stats is None:
        stats = "".join(stats_line(name, content) for name, content in organisms.items())
    path.write_text(stats, encoding="ascii", newline="\n")
    return Release(tarball, path)


def write_manifest(release: Release, out: Path) -> int:
    """`refmap data manifest` on `release`, writing `data.json` and `organisms.json` to `out`."""
    out.mkdir(parents=True, exist_ok=True)
    return main(
        [
            "refmap",
            "data",
            "manifest",
            str(release.tarball),
            str(release.stats),
            "--tarball-url",
            TARBALL_URL,
            "--stats-url",
            STATS_URL,
            "--manifest",
            str(out / "data.json"),
            "--organisms",
            str(out / "organisms.json"),
        ]
    )
