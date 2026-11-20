"""The `tools` marker counts an HMMER program only at the image's version (markers.py; openspec
wire-hmmscore, design.md, decision 7), with stand-in programs that report a version."""

import re
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from markers import fail_if_missing, missing_tools, skip_if_missing
from panther_engine.hmmscore.sample import HMMER_VERSION


class Marked:
    """Stands in for a test item, with the markers it was given."""

    def __init__(self, *marks: pytest.MarkDecorator) -> None:
        self._marks = [mark.mark for mark in marks]

    def iter_markers(self, name: str) -> Iterator[pytest.Mark]:
        return (mark for mark in self._marks if mark.name == name)


def item(*marks: pytest.MarkDecorator) -> pytest.Item:
    # Only iter_markers is read.
    return Marked(*marks)  # pyright: ignore[reportReturnType]


@pytest.fixture
def on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[str, str], None]:
    """Puts a program on PATH, alone, that prints `-h`'s first line as an HMMER of `version`.
    Tools aren't required unless a test says so, whatever the run sets, as in the image."""
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.delenv("PANTHER_REQUIRE_TOOLS", raising=False)

    def write(name: str, version: str) -> None:
        line = f"# HMMER {version} (Aug 2023); http://hmmer.org/"
        if sys.platform == "win32":
            (tmp_path / f"{name}.cmd").write_text(f"@echo {line}\r\n", encoding="ascii")
        else:
            program = tmp_path / name
            program.write_text(f"#!/bin/sh\necho '{line}'\n", encoding="ascii")
            program.chmod(0o755)

    return write


def test_the_images_hmmer_counts(on_path: Callable[[str, str], None]) -> None:
    on_path("hmmscan", HMMER_VERSION)
    on_path("hmmsearch", HMMER_VERSION)

    assert missing_tools(item(pytest.mark.tools("hmmscan", "hmmsearch"))) == []


def test_another_hmmer_is_missing_naming_what_was_found(
    on_path: Callable[[str, str], None],
) -> None:
    on_path("hmmscan", "3.3")
    on_path("hmmsearch", HMMER_VERSION)

    [problem] = missing_tools(item(pytest.mark.tools("hmmscan", "hmmsearch")))

    assert problem.startswith(f"hmmscan {HMMER_VERSION}, found HMMER 3.3 at ")


def test_a_program_not_on_path_is_missing(on_path: Callable[[str, str], None]) -> None:
    on_path("hmmscan", HMMER_VERSION)

    assert missing_tools(item(pytest.mark.tools("hmmscan", "hmmsearch"))) == [
        "hmmsearch, not found on PATH"
    ]


def test_another_hmmer_skips_the_test(on_path: Callable[[str, str], None]) -> None:
    on_path("hmmscan", "3.1b2")

    with pytest.raises(pytest.skip.Exception, match=re.escape("found HMMER 3.1b2")):
        skip_if_missing(item(pytest.mark.tools("hmmscan")))


def test_another_hmmer_fails_the_test_where_tools_are_required(
    on_path: Callable[[str, str], None], monkeypatch: pytest.MonkeyPatch
) -> None:
    on_path("hmmscan", "3.3")
    monkeypatch.setenv("PANTHER_REQUIRE_TOOLS", "1")

    skip_if_missing(item(pytest.mark.tools("hmmscan")))
    with pytest.raises(pytest.fail.Exception, match=re.escape("found HMMER 3.3")):
        fail_if_missing(item(pytest.mark.tools("hmmscan")))


def test_only_hmmer_programs_have_their_version_checked(
    on_path: Callable[[str, str], None],
) -> None:
    # A blastp that reports itself as an old HMMER still counts: only presence is checked.
    on_path("blastp", "3.1b2")

    assert missing_tools(item(pytest.mark.tools("blastp"))) == []
