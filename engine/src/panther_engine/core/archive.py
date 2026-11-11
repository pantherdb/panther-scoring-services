"""Gzipped tarballs: read as a stream, written reproducibly and unpacked safely.

Shared by the services whose data comes as a tarball: cSNP's survey, sample and full data, and
hmmscore's survey, pin and sample.
"""

import gzip
import tarfile
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import IO, cast

from panther_engine.core.manifest import HashingReader

READ_SIZE = 1 << 20


class ArchiveError(Exception):
    """A member that can't be read, or a tarball that can't be unpacked safely."""


def open_stream(reader: HashingReader) -> tarfile.TarFile:
    """A gzipped tar read as a stream, front to back, through `reader`.

    tarfile's default buffer is kept: with a large one, each small read of a member copies the
    rest of a large decompressed buffer, and the pass runs many times slower.
    """
    return tarfile.open(fileobj=cast(IO[bytes], reader), mode="r|gz")


def member_lines(tar: tarfile.TarFile, member: tarfile.TarInfo) -> Iterator[bytes]:
    """A member's lines, with their line feeds, read in large chunks."""
    stream = tar.extractfile(member)
    if stream is None:
        raise ArchiveError(f"can't read {member.name}")
    rest = b""
    while chunk := stream.read(READ_SIZE):
        lines = (rest + chunk).split(b"\n")
        rest = lines.pop()
        for line in lines:
            yield line + b"\n"
    if rest:
        yield rest


def write_tarball(path: Path, files: dict[str, Path], compresslevel: int = 9) -> None:
    """A reproducible tarball: members sorted by path, USTAR, owned by 0 and dated 0, modes 0644
    and 0755, gzip level 9 with no name or date in its header. Tests can compress less."""
    folders = {str(parent) for name in files for parent in PurePosixPath(name).parents}
    folders.discard(".")
    with (
        path.open("wb") as raw,
        gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, compresslevel=compresslevel, mtime=0
        ) as compressed,
        tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as tar,
    ):
        for name in sorted(folders | set(files)):
            info = tarfile.TarInfo(name)
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            if name in folders:
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
                continue
            info.mode = 0o644
            info.size = files[name].stat().st_size
            with files[name].open("rb") as source:
                tar.addfile(info, source)


def unpack(tarball: Path, folder: Path, top: str) -> None:
    """Unpack `tarball` into `folder`, after checking that every member is a regular file or a
    folder at a relative path under `top`, such as `csnp`. Nothing is unpacked if one isn't."""
    try:
        with tarfile.open(tarball, "r:gz") as tar:
            members = tar.getmembers()
            for member in members:
                path = PurePosixPath(member.name)
                if (
                    not (member.isfile() or member.isdir())
                    or path.is_absolute()
                    or ".." in path.parts
                    or path.parts[:1] != (top,)
                ):
                    raise ArchiveError(f"unsafe member in {tarball.name}: {member.name!r}")
            # The data filter refuses such members too, and anything else unsafe.
            tar.extractall(folder, members, filter="data")
    except (tarfile.TarError, EOFError, OSError) as error:
        raise ArchiveError(f"can't unpack {tarball}: {error}") from error
