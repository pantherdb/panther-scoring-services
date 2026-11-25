import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from panther_engine.treegrafter import ebi
from panther_engine.treegrafter.ebi import TreegrafterError

# A report with one family and one domain, in two alignment blocks: EBI's own test's
# (tests/test_parsehmmsearch.py at 5ef350f), shortened, with the domain table's columns closer.
REPORT = """\
# hmmsearch :: search profile(s) against a sequence database
Query:       PTHR00001.orig.30.pir  [M=10]
Scores for complete sequences (score includes all domains):
   --- full sequence ---   --- best 1 domain ---    -#dom-
    E-value  score  bias    E-value  score  bias    exp  N  Sequence  Description
    ------- ------ -----    ------- ------ -----   ---- --  --------  -----------
    1.0e-10  100.0   0.0    1.0e-10  100.0   0.0    1.0  1  query1    test query


Domain annotation for each sequence (and alignments):
>> query1  test query
   #  score bias c-Evalue i-Evalue hmmfrom hmm to   alifrom ali to   envfrom env to   acc
 --- ------ ---- -------- -------- ------- ------   ------- ------   ------- ------   ----
   1 ! 100.0  0.0  1.0e-10  1.0e-10       1     10 ..       1     12 ..       1     12 .. 0.99

  Alignments for each domain:
  == domain 1  score: 100.0 bits;  conditional E-value: 1.0e-10
                  PTHR00001.orig.30.pir  1 abcde 5
                                           ABCDE
                             query1  1 ABCDE 5
                                       99999 PP

                  PTHR00001.orig.30.pir  6 fghij 10
                                           FGHIJ
                             query1  6 FGHIJ 10
                                       99999 PP



Internal pipeline statistics summary:
//
"""
# The same report with a domain line of 15 columns, where parsehmmsearch expects 16: it writes its
# reason to standard error and calls sys.exit(1) (treegrafter.py 343 to 348).
BROKEN = REPORT.replace(".. 0.99\n", "0.99\n", 1)


def test_importing_the_engine_doesnt_load_ebis_code_or_biopython() -> None:
    code = (
        "import sys, panther_engine.treegrafter, panther_engine.treegrafter.ebi\n"
        "print(sorted(name for name in sys.modules if name in ('treegrafter', 'Bio')))"
    )
    # S603: the test's own interpreter, with a fixed program.
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "[]"


def test_the_installed_module_is_the_pinned_commits() -> None:
    spec = importlib.util.find_spec("treegrafter")

    assert spec is not None and spec.origin is not None
    assert hashlib.sha256(Path(spec.origin).read_bytes()).hexdigest() == ebi.MODULE_SHA256


def test_a_report_is_read_into_ebis_matches(tmp_path: Path) -> None:
    report = tmp_path / "hmmsearch.out"
    report.write_text(REPORT, encoding="ascii")

    matches = ebi.parse_hmmsearch(report)

    assert list(matches) == ["PTHR00001"]
    align = matches["PTHR00001"]["query1"]
    assert align["hmmalign"] == ["abcdefghij"]
    assert align["matchalign"] == ["ABCDEFGHIJ"]
    assert (align["score"], align["evalue"], align["domscore"]) == (["100.0"], ["1e-10"], ["100.0"])


def test_a_report_ebi_exits_on_is_a_treegrafter_error_with_its_message(tmp_path: Path) -> None:
    report = tmp_path / "hmmsearch.out"
    report.write_text(BROKEN, encoding="ascii")

    with pytest.raises(TreegrafterError) as caught:
        ebi.parse_hmmsearch(report)

    message = str(caught.value)
    assert "parsehmmsearch exited with status 1" in message
    assert "domain info length is 15, expected 16 for query1." in message
    # The test process is still here to check: SystemExit didn't escape.


def test_ebis_messages_stay_off_standard_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = tmp_path / "hmmsearch.out"
    report.write_text(BROKEN, encoding="ascii")

    with pytest.raises(TreegrafterError):
        ebi.parse_hmmsearch(report)

    assert capsys.readouterr().err == ""
