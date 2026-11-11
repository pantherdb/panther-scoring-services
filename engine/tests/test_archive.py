"""core/archive.py: reading a gzipped tar as a stream, writing one, unpacking one safely."""

import gzip
import hashlib
import io
import os
import re
import tarfile
from pathlib import Path

import pytest

from panther_engine.core import archive
from panther_engine.core.archive import (
    ArchiveError,
    member_lines,
    open_stream,
    unpack,
    write_tarball,
)
from panther_engine.core.manifest import HashingReader


def tar_gz(path: Path, members: list[tuple[str, bytes]]) -> Path:
    """A gzipped tar at `path` holding regular files, in the order given."""
    with gzip.open(path, "wb") as compressed, tarfile.open(fileobj=compressed, mode="w") as tar:
        for name, content in members:
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return path


def lines_of(path: Path, name: str) -> list[bytes]:
    """The lines `member_lines` gives for the member `name`, read as a stream."""
    with path.open("rb") as raw, open_stream(HashingReader(raw)) as tar:
        for member in tar:
            if member.name == name:
                return list(member_lines(tar, member))
    raise AssertionError(f"{name} isn't in {path}")


# open_stream and member_lines


def test_a_stream_reads_the_members_in_order_through_a_reader_that_cant_seek(
    tmp_path: Path,
) -> None:
    tarball = tar_gz(tmp_path / "t.tar.gz", [("b", b"2\n"), ("a", b"1\n")])

    with tarball.open("rb") as raw:
        reader = HashingReader(raw)
        with open_stream(reader) as tar:
            names = [member.name for member in tar]
        reader.drain()

    assert names == ["b", "a"]
    assert reader.digest.hexdigest() == hashlib.sha256(tarball.read_bytes()).hexdigest()


def test_lines_keep_their_line_feeds_and_the_last_may_have_none(tmp_path: Path) -> None:
    tarball = tar_gz(tmp_path / "t.tar.gz", [("m", b"a\nbb\n\nccc")])

    assert lines_of(tarball, "m") == [b"a\n", b"bb\n", b"\n", b"ccc"]


def test_a_line_split_between_two_reads_comes_out_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(archive, "READ_SIZE", 3)
    tarball = tar_gz(tmp_path / "t.tar.gz", [("m", b"abcdefg\nhi\n")])

    assert lines_of(tarball, "m") == [b"abcdefg\n", b"hi\n"]


def test_the_lines_of_a_member_that_isnt_a_file_are_an_error(tmp_path: Path) -> None:
    tarball = tmp_path / "t.tar.gz"
    with gzip.open(tarball, "wb") as compressed, tarfile.open(fileobj=compressed, mode="w") as tar:
        folder = tarfile.TarInfo("books")
        folder.type = tarfile.DIRTYPE
        tar.addfile(folder)

    with pytest.raises(ArchiveError, match="can't read books"):
        lines_of(tarball, "books")


# write_tarball


def sources(folder: Path, contents: dict[str, bytes]) -> dict[str, Path]:
    """Each content written to its own file in `folder`, keyed by its name in the tarball."""
    files: dict[str, Path] = {}
    for index, (name, content) in enumerate(contents.items()):
        source = folder / f"source-{index}"
        source.write_bytes(content)
        files[name] = source
    return files


def test_a_tarball_is_sorted_with_its_folders_owned_by_0_and_dated_0(tmp_path: Path) -> None:
    files = sources(tmp_path, {"top/b/2.txt": b"two\n", "top/a/1.txt": b"one\n"})
    tarball = tmp_path / "out.tar.gz"

    write_tarball(tarball, files)

    with tarfile.open(tarball) as tar:
        members = tar.getmembers()
        one = tar.extractfile("top/a/1.txt")
        assert one is not None
        assert one.read() == b"one\n"
    names = [member.name for member in members]
    assert names == ["top", "top/a", "top/a/1.txt", "top/b", "top/b/2.txt"]
    for member in members:
        assert (member.uid, member.gid, member.uname, member.gname) == (0, 0, "", "")
        assert member.mtime == 0
        assert member.mode == (0o755 if member.isdir() else 0o644)
    raw = tarball.read_bytes()
    assert raw[3] & 0x08 == 0  # the gzip header holds no file name
    assert raw[4:8] == b"\0\0\0\0"  # and no date
    assert gzip.decompress(raw)[257:263] == b"ustar\0"


def test_the_same_files_give_the_same_bytes_whatever_their_dates(tmp_path: Path) -> None:
    files = sources(tmp_path, {"top/1.txt": b"one\n"})
    first, second = tmp_path / "first.tar.gz", tmp_path / "second.tar.gz"
    write_tarball(first, files)
    os.utime(files["top/1.txt"], (1_000_000_000, 1_000_000_000))

    write_tarball(second, files)

    assert first.read_bytes() == second.read_bytes()


# unpack


def with_member(path: Path, name: str, kind: bytes) -> Path:
    """A gzipped tar holding a safe file, then one member of the given type."""
    with gzip.open(path, "wb") as compressed, tarfile.open(fileobj=compressed, mode="w") as tar:
        safe = tarfile.TarInfo("hmmscore/19/README")
        safe.size = 3
        tar.addfile(safe, io.BytesIO(b"ok\n"))
        info = tarfile.TarInfo(name)
        info.type = kind
        if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
            info.linkname = "/etc/passwd"
            tar.addfile(info)
        else:
            info.size = 3
            tar.addfile(info, io.BytesIO(b"bad"))
    return path


def test_files_and_folders_under_the_top_folder_are_unpacked(tmp_path: Path) -> None:
    tarball = with_member(tmp_path / "t.tar.gz", "hmmscore/19/books", tarfile.DIRTYPE)
    folder = tmp_path / "out"
    folder.mkdir()

    unpack(tarball, folder, "hmmscore")

    assert (folder / "hmmscore" / "19" / "README").read_bytes() == b"ok\n"
    assert (folder / "hmmscore" / "19" / "books").is_dir()


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("/hmmscore/absolute", tarfile.REGTYPE),
        ("hmmscore/../../escape", tarfile.REGTYPE),
        ("hmmscore/19/link", tarfile.SYMTYPE),
        ("hmmscore/19/hard", tarfile.LNKTYPE),
        ("csnp/9/file", tarfile.REGTYPE),
    ],
)
def test_an_unsafe_member_or_one_outside_the_top_folder_unpacks_nothing(
    name: str, kind: bytes, tmp_path: Path
) -> None:
    tarball = with_member(tmp_path / "unsafe.tar.gz", name, kind)
    folder = tmp_path / "out"
    folder.mkdir()

    with pytest.raises(ArchiveError, match=re.escape(repr(name))):
        unpack(tarball, folder, "hmmscore")

    assert list(folder.iterdir()) == []
    assert not (tmp_path / "escape").exists()


def test_a_file_that_isnt_a_gzipped_tar_is_an_error(tmp_path: Path) -> None:
    tarball = tmp_path / "plain.tar.gz"
    tarball.write_text("not a tarball\n")
    folder = tmp_path / "out"
    folder.mkdir()

    with pytest.raises(ArchiveError, match="can't unpack"):
        unpack(tarball, folder, "hmmscore")
