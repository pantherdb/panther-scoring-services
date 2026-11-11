import hashlib
import json
from pathlib import Path

import pytest
from hmmscore_fixtures import (
    BINHMM,
    CLUSTER,
    FAMILY_MODEL,
    NAMES,
    PREFIX,
    README,
    SF1_MODEL,
    SF2_MODEL,
    SF3_MODEL,
    TREE,
    clean_library,
    data,
    library_tarball,
)

from panther_engine.hmmscore.survey import (
    Report,
    SurveyError,
    Tally,
    report_json,
    report_text,
    survey,
)

BINHMM_ORDER = ["PTHR99999.SF2.pir", "PTHR99999.orig.30.pir", "PTHR99999.SF1.pir"]


def surveyed(
    tmp_path: Path,
    files: dict[str, bytes],
    *,
    extra: list[tuple[str, bytes]] | None = None,
    folders: tuple[str, ...] = (),
) -> Report:
    tarball = library_tarball(tmp_path / "library.tgz", files, extra=extra or [], folders=folders)
    return survey(tarball)


def counts(report: Report) -> dict[str, int]:
    """Each check that found something, with its count."""
    return {key: result.count for key, result in report.checks.items() if result.count}


def details(report: Report, key: str) -> list[str]:
    return [example.detail for example in report.checks[key].examples]


def families(report: Report, key: str) -> list[str]:
    return [example.family for example in report.checks[key].examples]


def without(files: dict[str, bytes], *names: str) -> dict[str, bytes]:
    return {name: content for name, content in files.items() if name not in names}


# The tarball and its members


def test_the_report_gives_the_tarballs_sha256_and_size(tmp_path: Path) -> None:
    tarball = library_tarball(tmp_path / "library.tgz", clean_library())

    report = survey(tarball)

    assert report.tarball.sha256 == hashlib.sha256(tarball.read_bytes()).hexdigest()
    assert report.tarball.size == tarball.stat().st_size


@pytest.mark.parametrize("flat", [True, False])
def test_the_clean_library_finds_only_its_copy_named_for_the_family(
    tmp_path: Path, flat: bool
) -> None:
    report = surveyed(tmp_path, clean_library(flat=flat))

    assert counts(report) == {"model-legacy-id": 1}
    [detail] = details(report, "model-legacy-id")
    assert SF3_MODEL in detail
    assert "PTHR99999.orig.30.pir" in detail


def test_every_member_is_counted_by_kind_with_its_bytes(tmp_path: Path) -> None:
    files = clean_library(flat=True)

    kinds = surveyed(tmp_path, files).kinds

    assert kinds["README"] == Tally(1, len(README))
    assert kinds["globals/names.tab"] == Tally(1, len(files[NAMES]))
    assert kinds["globals/binHmm"] == Tally(1, len(files[BINHMM]))
    for suffix in ("h3f", "h3i", "h3m", "h3p"):
        path = f"globals/binHmm.{suffix}"
        assert kinds[path] == Tally(1, len(files[path]))
    assert kinds["family model"] == Tally(1, len(files[FAMILY_MODEL]))
    subfamilies = sum(len(files[name]) for name in (SF1_MODEL, SF2_MODEL, SF3_MODEL))
    assert kinds["subfamily model"] == Tally(3, subfamilies)
    assert kinds["cluster.pir"] == Tally(1, len(CLUSTER))
    assert kinds["tree.tree"] == Tally(1, len(TREE))
    # The prefix's own, globals, books, PTHR99999 and its three subfamilies
    assert kinds["folder"] == Tally(7, 0)


def test_kept_bytes_are_the_readme_globals_and_models_apart_from_the_rest(tmp_path: Path) -> None:
    files = clean_library(flat=True)
    note = (PREFIX + "books/PTHR10000/notes.txt", b"note\n")

    report = surveyed(tmp_path, files, extra=[note])

    kept = [content for name, content in files.items() if not name.endswith(("pir", "tree"))]
    assert report.kept_bytes == sum(len(content) for content in kept)
    assert report.other_bytes == len(CLUSTER) + len(TREE) + len(b"note\n")


def test_an_unexpected_member_is_reported(tmp_path: Path) -> None:
    note = (PREFIX + "books/PTHR10000/notes.txt", b"note\n")

    report = surveyed(tmp_path, clean_library(), extra=[note])

    assert report.checks["unexpected-member"].count == 1
    assert "books/PTHR10000/notes.txt" in details(report, "unexpected-member")[0]
    assert report.kinds["unexpected"] == Tally(1, 5)


def test_a_member_outside_the_prefix_is_reported(tmp_path: Path) -> None:
    report = surveyed(tmp_path, clean_library(), extra=[("elsewhere/file", b"x\n")])

    assert report.checks["outside-prefix"].count == 1
    assert "elsewhere/file" in details(report, "outside-prefix")[0]


def test_the_folders_the_prefix_is_in_are_not_outside_it(tmp_path: Path) -> None:
    folders = ("target", "target/famlib", "target/famlib/rel")

    report = surveyed(tmp_path, clean_library(), folders=folders)

    assert counts(report) == {"model-legacy-id": 1}


def test_a_member_that_appears_twice_is_reported(tmp_path: Path) -> None:
    report = surveyed(tmp_path, clean_library(), extra=[(PREFIX + "README", README)])

    assert report.checks["duplicate-member"].count == 1
    assert "README" in details(report, "duplicate-member")[0]


# names.tab and the model files


def test_a_names_id_without_its_model_file_is_reported(tmp_path: Path) -> None:
    files = clean_library()
    files[NAMES] += b"PTHR10000.SF5.mod\tA NAME\n"

    report = surveyed(tmp_path, files)

    assert report.checks["name-without-model"].count == 1
    assert families(report, "name-without-model") == ["PTHR10000"]
    assert "PTHR10000:SF5" in details(report, "name-without-model")[0]


def test_a_model_file_without_its_names_line_is_reported(tmp_path: Path) -> None:
    files = clean_library()
    files[NAMES] = files[NAMES].replace(b"PTHR99999.SF2.mod\tTEST SUBFAMILY 2\n", b"")

    report = surveyed(tmp_path, files)

    assert report.checks["model-without-name"].count == 1
    assert "PTHR99999:SF2" in details(report, "model-without-name")[0]


def test_a_subfamily_model_named_for_its_family_is_reported(tmp_path: Path) -> None:
    files = clean_library()
    path = "books/PTHR38402/SF1/hmmer.hmm"
    files[path] = data(FAMILY_MODEL).replace(b"PTHR99999.orig.30.pir", b"PTHR38402.orig.30.pir")

    report = surveyed(tmp_path, files)

    [example] = [
        each for each in report.checks["model-legacy-id"].examples if each.family == "PTHR38402"
    ]
    assert path in example.detail
    assert "legacy ID PTHR38402," in example.detail


def test_a_model_file_that_doesnt_read_is_reported_with_the_error(tmp_path: Path) -> None:
    files = clean_library()
    files[SF2_MODEL] = data("broken/two-models.hmm")

    report = surveyed(tmp_path, files)

    assert report.checks["model-rejected"].count == 1
    assert "more than one model" in details(report, "model-rejected")[0]


def test_format_lines_and_name_shapes_are_counted(tmp_path: Path) -> None:
    report = surveyed(tmp_path, clean_library())

    assert report.formats == {"HMMER3/f [3.4 | Aug 2023]": 4}
    assert report.name_shapes == {"PTHR<n>.orig.<n>.pir": 2, "PTHR<n>.SF<n>.pir": 2}


def test_a_names_line_the_strict_reader_rejects_is_reported_with_its_legacy_key(
    tmp_path: Path,
) -> None:
    files = clean_library()
    files[NAMES] = files[NAMES].replace(b"PTHR99999.SF1.mod\t", b"PTHR99999.SF1\t")

    report = surveyed(tmp_path, files)

    assert report.checks["names-rejected"].count == 1
    assert "line 2" in details(report, "names-rejected")[0]
    assert report.checks["names-legacy-key"].count == 1
    assert "PTHR99999:SF1\\tTEST SUBFAMILY 1" in details(report, "names-legacy-key")[0]


def test_a_repeated_names_id_is_reported(tmp_path: Path) -> None:
    files = clean_library()
    files[NAMES] = data("broken/names-repeated.tab")

    report = surveyed(tmp_path, files)

    assert report.checks["names-repeated"].count == 1
    assert "lines 2 and 5" in details(report, "names-repeated")[0]


# One-subfamily families


def test_a_one_subfamily_family_whose_subfamily_is_a_copy_is_counted(tmp_path: Path) -> None:
    files = without(clean_library(), SF2_MODEL, SF3_MODEL)
    files[SF1_MODEL] = data(FAMILY_MODEL)

    report = surveyed(tmp_path, files)

    assert report.checks["one-subfamily-copy"].count == 1
    assert families(report, "one-subfamily-copy") == ["PTHR99999"]
    assert report.checks["one-subfamily-differs"].count == 0


def test_a_one_subfamily_family_whose_subfamily_differs_is_given_as_an_example(
    tmp_path: Path,
) -> None:
    files = without(clean_library(), SF2_MODEL, SF3_MODEL)

    report = surveyed(tmp_path, files)

    assert report.checks["one-subfamily-differs"].count == 1
    assert families(report, "one-subfamily-differs") == ["PTHR99999"]
    assert "SF1" in details(report, "one-subfamily-differs")[0]
    assert report.checks["one-subfamily-copy"].count == 0


# binHmm


@pytest.mark.parametrize(("flat", "source"), [(True, BINHMM), (False, "globals/binHmm.h3i")])
def test_binhmms_models_are_listed_in_order_from_the_flat_file_or_else_the_index(
    tmp_path: Path, flat: bool, source: str
) -> None:
    report = surveyed(tmp_path, clean_library(flat=flat))

    assert report.binhmm_source == source
    assert report.binhmm_models == BINHMM_ORDER
    assert report.checks["binhmm-differs"].checked is flat


def test_a_repeated_binhmm_name_is_reported(tmp_path: Path) -> None:
    files = clean_library(flat=True)
    files[BINHMM] = data(FAMILY_MODEL) * 2

    report = surveyed(tmp_path, files)

    assert report.checks["binhmm-repeated"].count == 1
    assert "PTHR99999.orig.30.pir" in details(report, "binhmm-repeated")[0]


@pytest.mark.parametrize("flat", [True, False])
def test_a_binhmm_model_without_a_model_file_to_align_with_is_reported(
    tmp_path: Path, flat: bool
) -> None:
    files = without(clean_library(flat=flat), SF2_MODEL)

    report = surveyed(tmp_path, files)

    assert report.checks["binhmm-no-model-file"].count == 1
    assert "PTHR99999.SF2.pir" in details(report, "binhmm-no-model-file")[0]


def test_a_model_name_binhmm_lacks_is_reported(tmp_path: Path) -> None:
    files = clean_library()
    path = "books/PTHR99999/SF4/hmmer.hmm"
    files[path] = data(SF2_MODEL).replace(b"PTHR99999.SF2.pir", b"PTHR99999.SF4.pir")

    report = surveyed(tmp_path, files)

    assert report.checks["binhmm-lacks"].count == 1
    assert "PTHR99999.SF4.pir" in details(report, "binhmm-lacks")[0]


@pytest.mark.parametrize("flat", [True, False])
def test_a_binhmm_model_no_model_file_holds_is_reported_with_the_file_the_cgi_aligns_with(
    tmp_path: Path, flat: bool
) -> None:
    # As in PANTHER 19's one-subfamily families: binHmm holds the subfamily's own model, while
    # its model file in books/ is the family's.
    files = clean_library(flat=flat)
    renamed = (b"PTHR99999.SF1.pir", b"PTHR99999.SF3.pir")
    source = BINHMM if flat else "globals/binHmm.h3i"
    files[source] = files[source].replace(*renamed)

    report = surveyed(tmp_path, files)

    assert report.checks["binhmm-not-in-books"].count == 1
    [detail] = details(report, "binhmm-not-in-books")
    assert detail.startswith("PTHR99999.SF3.pir: ")
    assert f"{SF3_MODEL}, which holds PTHR99999.orig.30.pir" in detail


def test_a_binhmm_model_whose_text_differs_from_its_model_file_is_reported(
    tmp_path: Path,
) -> None:
    files = clean_library(flat=True)
    files[BINHMM] = files[BINHMM].replace(b"NSEQ  3", b"NSEQ  4", 1)

    report = surveyed(tmp_path, files)

    assert report.checks["binhmm-differs"].count == 1
    assert "PTHR99999.SF2.pir" in details(report, "binhmm-differs")[0]


def test_an_index_that_doesnt_read_is_reported_and_binhmm_isnt_checked(tmp_path: Path) -> None:
    files = clean_library()
    files["globals/binHmm.h3i"] = b"not an index\n"

    report = surveyed(tmp_path, files)

    assert report.binhmm_error is not None
    assert "binHmm.h3i" in report.binhmm_error
    assert report.binhmm_source is None
    assert not report.checks["binhmm-no-model-file"].checked


# The pressed files


def test_each_pressed_files_size_and_format_are_reported(tmp_path: Path) -> None:
    files = clean_library()

    report = surveyed(tmp_path, files)

    for suffix, format_ in [("h3f", "3/f"), ("h3m", "3/f"), ("h3p", "3/f"), ("h3i", "SSI 3.0")]:
        path = f"globals/binHmm.{suffix}"
        assert (report.globals[path].size, report.globals[path].format) == (
            len(files[path]),
            format_,
        )
        assert report.globals[path].sha256 == hashlib.sha256(files[path]).hexdigest()


def test_a_pressed_file_with_another_magic_number_has_an_unknown_format(tmp_path: Path) -> None:
    files = clean_library()
    files["globals/binHmm.h3f"] = b"\0\0\0\0" + files["globals/binHmm.h3f"][4:]

    report = surveyed(tmp_path, files)

    assert report.globals["globals/binHmm.h3f"].format == "unknown (0x00000000)"


# Examples


def test_examples_are_at_most_five_and_the_smallest_families_first(tmp_path: Path) -> None:
    files = clean_library()
    files[NAMES] += b"".join(f"PTHR1000{n}.mag.mod\tFAMILY {n}\n".encode() for n in range(9, 3, -1))
    files["books/PTHR10001/hmmer.hmm"] = data("broken/two-models.hmm")
    files["books/PTHR10002/hmmer.hmm"] = data("broken/truncated.hmm")

    report = surveyed(tmp_path, files)

    assert report.checks["name-without-model"].count == 6
    assert families(report, "name-without-model") == [f"PTHR1000{n}" for n in range(4, 9)]
    # PTHR10002's file is the smaller
    assert families(report, "model-rejected") == ["PTHR10002", "PTHR10001"]


# Unreadable tarballs


def test_a_file_that_isnt_a_gzipped_tar_is_an_error(tmp_path: Path) -> None:
    plain = tmp_path / "plain.tgz"
    plain.write_text("not a tarball\n")

    with pytest.raises(SurveyError, match="can't read"):
        survey(plain)


def test_a_tarball_that_ends_early_is_an_error(tmp_path: Path) -> None:
    whole = library_tarball(tmp_path / "library.tgz", clean_library()).read_bytes()
    cut = tmp_path / "cut.tgz"
    cut.write_bytes(whole[: len(whole) // 2])

    with pytest.raises(SurveyError, match="can't read"):
        survey(cut)


# The report


def test_the_report_as_json_and_as_text(tmp_path: Path) -> None:
    report = surveyed(tmp_path, clean_library())

    payload = json.loads(json.dumps(report_json(report)))
    text = report_text(report)

    assert payload["tarball"]["sha256"] == report.tarball.sha256
    assert payload["checks"]["model-legacy-id"]["count"] == 1
    assert payload["binhmm"] == {"source": "globals/binHmm.h3i", "models": 3, "error": None}
    assert report.tarball.sha256 in text
    assert "model-legacy-id: 1 files" in text
