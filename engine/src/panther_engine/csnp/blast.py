"""Step 1, `run_blastp.pl`: search one protein against the PANTHER9 BLAST database with `blastp`.

The legacy options (design.md, decision 3), with the query on stdin and the hits on stdout: no file
is written, so nothing is shared between searches (`CGI-6`), and no shell runs (`CGI-5`).
"""

import shutil
import subprocess
from pathlib import Path

from panther_engine.core.errors import InputError
from panther_engine.core.process import run_tool
from panther_engine.csnp import legacy

# run_blastp.pl:22
OUTFMT = (
    "10 qseqid sseqid pident length mismatch gapopen gaps qstart qend sstart send qseq sseq "
    "evalue bitscore"
)
OPTIONS = ("-best_hit_overhang", "0.1", "-best_hit_score_edge", "0.1")
# snpScore.cgi names the one query P0001; step 2's species filter sees it in every line.
QUERY = "P0001"
DATABASE = Path("blast") / "blast"
# The search takes seconds against the 570,173 sequences.
TIMEOUT = 300.0
# BLAST+ exits with 1 when it can't read the query (divergence 8).
UNREADABLE_QUERY = 1
# A line that starts with one of these is a comment to BLAST+'s FASTA reader. A sequence that does
# leaves no sequence, and BLAST+ exits with 3, an engine error. The port refuses it first, with the
# same input error (divergence 8, decided by the engine developer on 2026-10-30).
COMMENT = ("!", "#", ";")
UNREADABLE_MESSAGE = (
    "The sequence can't be read as a protein sequence. Use one-letter residue codes, such as MKVL."
)


class BlastError(Exception):
    """BLAST+ failed in a way that isn't the input's fault, or wrote output the port can't read.

    Never an `InputError`: the job fails with the generic `500`.
    """


def search(sequence: str, data: Path, *, timeout: float = TIMEOUT) -> list[str]:
    """Step 1: `blastp` on the sequence, named `P0001`, against the cSNP data folder `data`'s
    database. Returns the output's lines as `blastp` wrote them, each ending in a line feed.

    Raises InputError when `blastp` can't read the query (exit status 1), or would read it as a
    comment, with a message that quotes none of its output. Raises BlastError for any other
    failure: another exit status, the time limit, or no `blastp` on PATH.
    """
    if sequence.startswith(COMMENT):
        raise InputError(UNREADABLE_MESSAGE)
    found = shutil.which("blastp")
    if found is None:
        raise BlastError("no blastp on PATH")
    args = ["-db", str(data.absolute() / DATABASE), "-outfmt", OUTFMT, *OPTIONS]
    # As snpScore.cgi's createFasta writes it, without a line feed after the sequence.
    query = f">{QUERY}\n{sequence}"
    try:
        result = run_tool(Path(found).absolute(), args, timeout=timeout, input=query)
    except subprocess.TimeoutExpired as error:
        raise BlastError(f"blastp ran past its time limit of {timeout:g} s") from error
    except OSError as error:
        raise BlastError(f"can't run blastp: {error}") from error
    if result.returncode == UNREADABLE_QUERY:
        raise InputError(UNREADABLE_MESSAGE)
    if result.returncode != 0:
        detail = " / ".join(result.stderr.strip().splitlines()[-3:])
        raise BlastError(f"blastp exited with status {result.returncode}: {detail}")
    return legacy.lines_of(result.stdout)
