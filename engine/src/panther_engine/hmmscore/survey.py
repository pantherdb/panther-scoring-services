"""The survey of the PANTHER HMM library's tarball: one streamed pass, with every member checked.

The tarball is read as a stream, `r|gz`, and never unpacked to disk. Its sha256 and size come from
the same pass. Each member is sorted by its path below the prefix (library.py). The survey holds
names and hashes, never model text: per `names.tab` line its ID; per model file its path, sha256,
`NAME` and `LENG`; per `binHmm` model its name, and the sha256 of its text when the tarball has
the flat file. The checks that compare them run when the pass ends.

`binHmm`'s models are listed from the flat `globals/binHmm` when the tarball has it, and otherwise
from the pressed index `binHmm.h3i`. That is an Easel SSI file (`easel/esl_ssi.c`): its keys, in
the order of their offsets in `binHmm.h3m`, are `binHmm`'s models in order.

Each check counts what it finds, with up to five examples, smallest family first. A family's size
is the bytes of its model files.
"""

import hashlib
import re
import struct
import tarfile
import zlib
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

from panther_engine.core.archive import ArchiveError, member_lines, open_stream
from panther_engine.core.manifest import CHUNK, HashingReader
from panther_engine.hmmscore import legacy
from panther_engine.hmmscore.library import (
    ENCODING,
    KEPT,
    MODELS,
    PREFIX,
    PRESSED,
    Kind,
    LibraryFormatError,
    family_of,
    index_names,
    library_member,
    lines_of,
    name_line,
    path_of,
    prefix_folder,
    pressed_format,
    read_model_file,
    read_models,
)

EXAMPLES = 5
UNEXPECTED = "unexpected"
OUTSIDE = "outside the prefix"
KEPT_KINDS = frozenset(kind.value for kind in KEPT)


class SurveyError(Exception):
    """A tarball that can't be read to the end."""


@dataclass(frozen=True)
class Check:
    key: str
    description: str
    unit: str
    family: bool = True
    """A check on families or models, which the sample must show too. The rest are on members."""


CHECKS = (
    # The tarball's members
    Check("unexpected-member", "members the layout doesn't have", "members", family=False),
    Check("outside-prefix", "members outside the prefix", "members", family=False),
    Check("duplicate-member", "members that appear twice", "members", family=False),
    # names.tab
    Check("names-rejected", "names.tab lines the strict reader rejects", "lines"),
    Check(
        "names-repeated", "names.tab lines that repeat an ID; getHmmNames keeps the last", "lines"
    ),
    Check("names-legacy-key", "names.tab lines getHmmNames keys other than by their ID", "lines"),
    # names.tab and the model files
    Check("name-without-model", "names.tab IDs without a model file in books/", "IDs"),
    Check("model-without-name", "model files without a names.tab line", "files"),
    Check("model-rejected", "model files the strict reader rejects", "files"),
    Check(
        "model-legacy-id",
        "model files whose legacy ID, from the model's name, isn't their path's",
        "files",
    ),
    Check(
        "one-subfamily-copy",
        "one-subfamily families whose subfamily's file is the family's",
        "families",
    ),
    Check(
        "one-subfamily-differs", "one-subfamily families whose subfamily's file differs", "families"
    ),
    # binHmm
    Check("binhmm-repeated", "names that binHmm holds more than once", "names"),
    Check(
        "binhmm-no-model-file", "binHmm models without the model file the CGI aligns with", "models"
    ),
    Check("binhmm-lacks", "model names in books/ that binHmm lacks", "names"),
    Check(
        "binhmm-not-in-books",
        "binHmm models no model file holds, aligned by the CGI with another model",
        "models",
    ),
    Check("binhmm-differs", "binHmm models whose text differs from their model file's", "models"),
)
BINHMM_CHECKS = frozenset(
    {
        "binhmm-repeated",
        "binhmm-no-model-file",
        "binhmm-lacks",
        "binhmm-not-in-books",
        "binhmm-differs",
    }
)


@dataclass(frozen=True)
class Example:
    family: str
    size: int
    """The bytes of the family's model files."""
    detail: str


@dataclass
class CheckResult:
    check: Check
    count: int = 0
    examples: list[Example] = field(default_factory=list[Example])
    checked: bool = True


@dataclass
class Tally:
    count: int = 0
    size: int = 0


@dataclass(frozen=True)
class Source:
    path: str
    sha256: str
    size: int


@dataclass(frozen=True)
class Global:
    path: str
    size: int
    sha256: str
    format: str | None = None
    """For a pressed file, the HMMER format its first bytes declare."""


@dataclass
class Report:
    tarball: Source
    prefix: str
    members: int = 0
    kinds: dict[str, Tally] = field(default_factory=dict[str, Tally])
    globals: dict[str, Global] = field(default_factory=dict[str, Global])
    name_lines: int = 0
    name_families: int = 0
    name_subfamilies: int = 0
    formats: Counter[str] = field(default_factory=Counter[str])
    name_shapes: Counter[str] = field(default_factory=Counter[str])
    one_subfamily: int = 0
    binhmm_source: str | None = None
    binhmm_models: list[str] = field(default_factory=list[str])
    binhmm_error: str | None = None
    checks: dict[str, CheckResult] = field(
        default_factory=lambda: {check.key: CheckResult(check) for check in CHECKS}
    )

    @property
    def kept_bytes(self) -> int:
        """The bytes of the members fetching keeps: the README, globals/ and the model files."""
        return sum(tally.size for kind, tally in self.kinds.items() if kind in KEPT_KINDS)

    @property
    def other_bytes(self) -> int:
        return sum(tally.size for kind, tally in self.kinds.items() if kind not in KEPT_KINDS)

    def found(self) -> list[str]:
        """The keys of the checks that found something."""
        return [key for key, result in self.checks.items() if result.count]


@dataclass
class ModelFile:
    path: str
    hmm_id: str
    family: str
    subfamily: str | None
    size: int
    sha256: str
    name: str | None = None
    """The model's NAME, if the file reads."""


Progress = Callable[[int, int], None]
"""Called now and then with the members and the compressed bytes read so far."""


def survey(tarball: Path, *, prefix: str = PREFIX, progress: Progress | None = None) -> Report:
    """Survey `tarball`, the library's gzipped tar. Raises SurveyError if it can't be read."""
    state = Survey(prefix)
    with tarball.open("rb") as raw:
        reader = HashingReader(raw)
        try:
            with open_stream(reader) as tar:
                for member in tar:
                    state.member(tar, member)
                    if progress is not None and state.members % 1000 == 0:
                        progress(state.members, reader.size)
            reader.drain()
        except (tarfile.TarError, EOFError, zlib.error, OSError, ArchiveError) as error:
            raise SurveyError(f"can't read {tarball} to the end: {error}") from error
    return state.finish(Source(str(tarball), reader.digest.hexdigest(), reader.size))


class Survey:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.members = 0
        self.kinds: dict[str, Tally] = {}
        self.globals: dict[str, Global] = {}
        self.seen: set[str] = set()
        self.findings: list[tuple[str, str, str]] = []
        self.names: dict[str, int] = {}
        """Each names.tab ID the strict reader read, with its line."""
        self.name_lines = 0
        self.models: dict[str, ModelFile] = {}
        self.formats: Counter[str] = Counter()
        self.flat: list[tuple[str, str]] | None = None
        """binHmm's models, by name and the sha256 of their text, from the flat file."""
        self.flat_error: str | None = None
        self.index: list[str] | None = None
        self.index_error: str | None = None

    def find(self, key: str, family: str, detail: str) -> None:
        self.findings.append((key, family, detail))

    def tally(self, kind: str, size: int) -> None:
        tally = self.kinds.setdefault(kind, Tally())
        tally.count += 1
        tally.size += size

    # Each member

    def member(self, tar: tarfile.TarFile, member: tarfile.TarInfo) -> None:
        self.members += 1
        if not member.name.startswith(self.prefix):
            if member.isdir() and prefix_folder(member.name, self.prefix):
                self.tally(Kind.FOLDER.value, 0)
            else:
                self.tally(OUTSIDE, member.size)
                self.find("outside-prefix", "", f"{member.name} ({member.size:,} bytes)")
            return
        relative = member.name.removeprefix(self.prefix)
        found = None
        if member.isdir():
            found = library_member(relative, folder=True)
        elif member.isfile():
            found = library_member(relative)
        if found is None:
            self.tally(UNEXPECTED, member.size)
            detail = f"{relative} ({member.size:,} bytes)"
            self.find("unexpected-member", family_of(relative.removeprefix("books/")), detail)
            return
        self.tally(found.kind.value, member.size)
        if found.kind is Kind.FOLDER:
            return
        if found.path in self.seen:
            self.find("duplicate-member", found.family or "", f"{found.path} again")
            return
        self.seen.add(found.path)
        stream = tar.extractfile(member)
        if stream is None:
            raise ArchiveError(f"can't read {member.name}")
        if found.kind in MODELS:
            content = stream.read()
            self.model_file(found.path, found.family or "", found.subfamily, content)
        elif found.kind is Kind.BINHMM:
            self.globals[found.path] = self.flat_file(tar, member, found.path)
        elif found.kind in PRESSED:
            self.globals[found.path] = self.pressed_file(stream, found.kind, found.path)
        elif found.kind in (Kind.README, Kind.NAMES):
            content = stream.read()
            digest = hashlib.sha256(content).hexdigest()
            self.globals[found.path] = Global(found.path, len(content), digest)
            if found.kind is Kind.NAMES:
                self.names_file(content, found.path)

    def names_file(self, content: bytes, path: str) -> None:
        for number, line in enumerate(lines_of(content), 1):
            self.name_lines += 1
            key = legacy.names_key(line)
            family = family_of(line)
            try:
                entry = name_line(line, number, path)
            except LibraryFormatError as error:
                self.find("names-rejected", family, f"line {number}: {error.message}")
                self.find("names-legacy-key", family, f"line {number}, keyed {key!r}")
                continue
            if entry.hmm_id != key:
                self.find("names-legacy-key", family, f"line {number}, keyed {key!r}")
            if (first := self.names.get(entry.hmm_id)) is not None:
                self.find("names-repeated", family, f"{entry.hmm_id} on lines {first} and {number}")
                continue
            self.names[entry.hmm_id] = number

    def model_file(self, path: str, family: str, subfamily: str | None, content: bytes) -> None:
        hmm_id = family if subfamily is None else f"{family}:{subfamily}"
        digest = hashlib.sha256(content).hexdigest()
        entry = ModelFile(path, hmm_id, family, subfamily, len(content), digest)
        try:
            model = read_model_file(lines_of(content), path)
        except LibraryFormatError as error:
            self.find("model-rejected", family, str(error))
        else:
            entry.name = model.name
            self.formats[model.format] += 1
        self.models[path] = entry

    def flat_file(self, tar: tarfile.TarFile, member: tarfile.TarInfo, path: str) -> Global:
        """binHmm's models from its text, read as a stream, with the file's size and sha256."""
        digest = hashlib.sha256()
        size = 0

        def decoded() -> Iterator[str]:
            nonlocal size
            for line in member_lines(tar, member):
                digest.update(line)
                size += len(line)
                yield line.decode(ENCODING)

        lines = decoded()
        models: list[tuple[str, str]] = []
        try:
            for model in read_models(lines, path):
                models.append((model.name, hashlib.sha256(model.text).hexdigest()))
        except LibraryFormatError as error:
            self.flat_error = str(error)
            for _ in lines:
                pass
        self.flat = models
        return Global(path, size, digest.hexdigest())

    def pressed_file(self, stream: IO[bytes], kind: Kind, path: str) -> Global:
        """A pressed file's size, sha256 and format. The index is kept, to list its keys."""
        digest = hashlib.sha256()
        head = stream.read(4)
        digest.update(head)
        size = len(head)
        kept = [head] if kind is Kind.H3I else None
        while chunk := stream.read(CHUNK):
            digest.update(chunk)
            size += len(chunk)
            if kept is not None:
                kept.append(chunk)
        if kept is not None:
            try:
                self.index = index_names(b"".join(kept))
            except (ValueError, struct.error) as error:
                self.index_error = f"{path}: {error}"
        return Global(path, size, digest.hexdigest(), pressed_format(kind, head))

    # When the pass ends

    def finish(self, tarball: Source) -> Report:
        report = Report(tarball, self.prefix, self.members, self.kinds, self.globals)
        report.name_lines = self.name_lines
        report.name_families = sum(":" not in hmm_id for hmm_id in self.names)
        report.name_subfamilies = len(self.names) - report.name_families
        report.formats = self.formats
        by_id = {entry.hmm_id: entry for entry in self.models.values()}
        self.names_and_models(by_id, report)
        self.one_subfamily(report)
        self.binhmm(by_id, report)
        sizes: Counter[str] = Counter()
        for entry in self.models.values():
            sizes[entry.family] += entry.size
        for key, family, detail in self.findings:
            result = report.checks[key]
            result.count += 1
            result.examples.append(Example(family, sizes[family], detail))
        for result in report.checks.values():
            result.examples.sort(key=lambda each: (each.size, each.family, each.detail))
            del result.examples[EXAMPLES:]
        return report

    def names_and_models(self, by_id: dict[str, ModelFile], report: Report) -> None:
        for hmm_id, line in self.names.items():
            if hmm_id not in by_id:
                self.find("name-without-model", family_of(hmm_id), f"{hmm_id}, line {line}")
        for entry in self.models.values():
            if entry.hmm_id not in self.names:
                self.find("model-without-name", entry.family, f"{entry.path}: {entry.hmm_id}")
            if entry.name is None:
                continue
            report.name_shapes[re.sub(r"[0-9]+", "<n>", entry.name)] += 1
            legacy_id = legacy.model_id(entry.name)
            if legacy_id != entry.hmm_id:
                detail = (
                    f"{entry.path} holds {entry.name}, legacy ID {legacy_id}, not {entry.hmm_id}"
                )
                self.find("model-legacy-id", entry.family, detail)

    def one_subfamily(self, report: Report) -> None:
        families: dict[str, ModelFile] = {}
        subfamilies: dict[str, list[ModelFile]] = {}
        for entry in self.models.values():
            if entry.subfamily is None:
                families[entry.family] = entry
            else:
                subfamilies.setdefault(entry.family, []).append(entry)
        for family, entries in subfamilies.items():
            if len(entries) != 1:
                continue
            report.one_subfamily += 1
            [entry] = entries
            whole = families.get(family)
            if whole is not None and whole.sha256 == entry.sha256:
                self.find("one-subfamily-copy", family, f"{entry.subfamily}'s file is the family's")
            else:
                why = "has no family model" if whole is None else "differs from the family's"
                self.find("one-subfamily-differs", family, f"{entry.subfamily}'s file {why}")

    def binhmm(self, by_id: dict[str, ModelFile], report: Report) -> None:
        report.binhmm_error = self.flat_error or self.index_error
        if self.flat is not None and self.flat_error is None:
            report.binhmm_source = Kind.BINHMM.value
            names = [name for name, _ in self.flat]
        elif self.index is not None:
            report.binhmm_source = Kind.H3I.value
            names = self.index
        else:
            for key in BINHMM_CHECKS:
                report.checks[key].checked = False
            return
        report.binhmm_models = names
        for name, times in Counter(names).items():
            if times > 1:
                self.find("binhmm-repeated", family_of(name), f"{name}, {times} times")
        for name in dict.fromkeys(names):
            legacy_id = legacy.model_id(name)
            if legacy_id not in by_id:
                self.find(
                    "binhmm-no-model-file", family_of(name), f"{name}: no {path_of(legacy_id)}"
                )
        held = set(names)
        by_name: dict[str, list[ModelFile]] = {}
        for entry in self.models.values():
            if entry.name is not None:
                by_name.setdefault(entry.name, []).append(entry)
        for name, entries in by_name.items():
            if name not in held:
                paths = ", ".join(entry.path for entry in entries)
                self.find("binhmm-lacks", family_of(name), f"{name}, in {paths}")
        for name in dict.fromkeys(names):
            aligned = by_id.get(legacy.model_id(name))
            if name in by_name or aligned is None:
                continue
            detail = (
                f"{name}: the CGI aligns its hits with {aligned.path}, which holds {aligned.name}"
            )
            self.find("binhmm-not-in-books", family_of(name), detail)
        if report.binhmm_source != Kind.BINHMM.value or self.flat is None:
            report.checks["binhmm-differs"].checked = False
            return
        for name, digest in self.flat:
            entries = by_name.get(name, [])
            if entries and all(entry.sha256 != digest for entry in entries):
                paths = ", ".join(entry.path for entry in entries)
                self.find("binhmm-differs", family_of(name), f"{name}'s text differs from {paths}")


# The report


def report_json(report: Report) -> dict[str, object]:
    return {
        "tarball": {
            "path": report.tarball.path,
            "sha256": report.tarball.sha256,
            "bytes": report.tarball.size,
        },
        "prefix": report.prefix,
        "members": report.members,
        "kinds": {kind: {"count": t.count, "bytes": t.size} for kind, t in report.kinds.items()},
        "kept_bytes": report.kept_bytes,
        "other_bytes": report.other_bytes,
        "globals": {
            path: {"bytes": each.size, "sha256": each.sha256, "format": each.format}
            for path, each in report.globals.items()
        },
        "names": {
            "lines": report.name_lines,
            "families": report.name_families,
            "subfamilies": report.name_subfamilies,
        },
        "formats": dict(report.formats),
        "name_shapes": dict(report.name_shapes),
        "one_subfamily_families": report.one_subfamily,
        "binhmm": {
            "source": report.binhmm_source,
            "models": len(report.binhmm_models),
            "error": report.binhmm_error,
        },
        "checks": {
            key: {
                "description": result.check.description,
                "unit": result.check.unit,
                "family_level": result.check.family,
                "checked": result.checked,
                "count": result.count,
                "examples": [
                    {"family": each.family, "bytes": each.size, "detail": each.detail}
                    for each in result.examples
                ],
            }
            for key, result in report.checks.items()
        },
    }


def report_text(report: Report) -> str:
    lines = [
        f"Tarball:  {report.tarball.path}",
        f"sha256:   {report.tarball.sha256}",
        f"Bytes:    {report.tarball.size:,}",
        f"Prefix:   {report.prefix}",
        f"Members:  {report.members:,}; {report.kept_bytes:,} bytes kept by fetching, "
        f"{report.other_bytes:,} not",
        "",
        "Members by kind:",
    ]
    order = [kind.value for kind in Kind] + [UNEXPECTED, OUTSIDE]
    for kind in order:
        tally = report.kinds.get(kind, Tally())
        lines.append(f"    {kind}: {tally.count:,}, {tally.size:,} bytes")
    lines.append("Globals:")
    for path, each in report.globals.items():
        format_ = f", format {each.format}" if each.format is not None else ""
        lines.append(f"    {path}: {each.size:,} bytes{format_}, sha256 {each.sha256}")
    lines.append(
        f"names.tab: {report.name_lines:,} lines; {report.name_families:,} family and "
        f"{report.name_subfamilies:,} subfamily IDs read"
    )
    lines.append("Model format lines:")
    lines.extend(f"    {line}: {count:,}" for line, count in report.formats.most_common())
    lines.append("Model name shapes:")
    lines.extend(f"    {shape}: {count:,}" for shape, count in report.name_shapes.most_common())
    lines.append(f"One-subfamily families: {report.one_subfamily:,}")
    source = report.binhmm_source or "not listed"
    lines.append(f"binHmm: {len(report.binhmm_models):,} models, from {source}")
    if report.binhmm_error is not None:
        lines.append(f"    error: {report.binhmm_error}")
    lines.append("")
    for result in report.checks.values():
        if not result.checked:
            lines.append(f"{result.check.key}: not checked")
            continue
        lines.append(
            f"{result.check.key}: {result.count:,} {result.check.unit}  "
            f"({result.check.description})"
        )
        lines.extend(
            f"    {each.family or '-'} ({each.size:,} bytes): {each.detail}"
            for each in result.examples
        )
    return "\n".join(lines) + "\n"
