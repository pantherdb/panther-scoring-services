"""Step 1, `run_blastp.pl`: search one protein against the PANTHER9 BLAST database with `blastp`.

The legacy options (design.md, decision 3), with the query on stdin and the hits on stdout: no file
is written, so nothing is shared between searches (`CGI-6`), and no shell runs (`CGI-5`).
"""

import math
import os
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
# The search's time limit grows with the query: a base plus a time per residue, times the scale
# in TIME_SCALE_VARIABLE (design.md, decision 5). An average protein takes 4 to 6 s, titin minutes;
# the measurements behind these numbers are in docs/testing/engine.md ("The BLAST+ Time Limit").
BASE_SECONDS = 60.0
SECONDS_PER_RESIDUE = 0.021
TIME_SCALE_VARIABLE = "PANTHER_CSNP_BLAST_TIME_SCALE"
# BLAST+ exits with 1 when it can't read the query (divergence 8), and then writes a line starting
# QUERY_ERROR, such as "BLAST query error: CFastaReader: Near line 2, ...". It also exits with 1
# for an argument it rejects, after its usage text and two "Error:" lines: that's not the input.
UNREADABLE_QUERY = 1
QUERY_ERROR = "BLAST query error:"
# A line that starts with one of these is a comment to BLAST+'s FASTA reader. A sequence that does
# leaves no sequence, and BLAST+ exits with 3, an engine error. The port refuses it first, with the
# same input error (divergence 8, decided by the engine developer on 2026-10-30).
COMMENT = ("!", "#", ";")
UNREADABLE_MESSAGE = (
    "The sequence can't be read as a protein sequence. Use one-letter residue codes, such as MKVL."
)


class BlastError(Exception):
    """BLAST+ failed in a way that isn't the input's fault, can't be run as it's set up, or wrote
    output the port can't read.

    Never an `InputError`: the job fails with the generic `500`.
    """


def time_scale() -> float:
    """The scale in TIME_SCALE_VARIABLE, read on each call: 1 when it's unset or empty. Raises
    BlastError, naming the variable, when it isn't a positive finite number."""
    value = os.environ.get(TIME_SCALE_VARIABLE, "")
    if not value:
        return 1.0
    try:
        scale = float(value)
    except ValueError:
        scale = math.nan
    if not (math.isfinite(scale) and scale > 0):
        raise BlastError(f"{TIME_SCALE_VARIABLE} must be a positive number, not {value!r}")
    return scale


def time_limit(residues: int) -> float:
    """The time limit, in seconds, for searching a sequence of `residues`."""
    return (BASE_SECONDS + SECONDS_PER_RESIDUE * residues) * time_scale()


def refuse_comment(sequence: str) -> None:
    """Raise InputError if BLAST+ would read the sequence as a comment, and so search nothing."""
    if sequence.startswith(COMMENT):
        raise InputError(UNREADABLE_MESSAGE)


def search(sequence: str, data: Path, *, timeout: float | None = None) -> list[str]:
    """Step 1: `blastp` on the sequence, named `P0001`, against the cSNP data folder `data`'s
    database. Returns the output's lines as `blastp` wrote them, each ending in a line feed. The
    time limit is `timeout` seconds if given, otherwise `time_limit` for the sequence.

    Raises InputError when `blastp` can't read the query (exit status 1 with a QUERY_ERROR line),
    or would read it as a comment, with a message that quotes none of its output. Raises
    BlastError for any other failure, with the end of `blastp`'s standard error for the log: any
    other non-zero status, the time limit, an invalid time scale, no `blastp` on PATH, or no
    `blast/` folder in `data`.
    """
    refuse_comment(sequence)
    if timeout is None:
        timeout = time_limit(len(sequence))
    found = shutil.which("blastp")
    if found is None:
        raise BlastError("no blastp on PATH")
    # blastp runs in the database's folder and names it alone, since BLAST+ splits -db on spaces
    # and a quote breaks its quoting: the data folder's path reaches it only as the working folder
    # (CSNP-6). BLAST+ looks there before BLASTDB.
    folder = data.absolute() / DATABASE.parent
    if not folder.is_dir():
        raise BlastError(f"no BLAST database folder: {folder}")
    args = ["-db", DATABASE.name, "-outfmt", OUTFMT, *OPTIONS]
    # As snpScore.cgi's createFasta writes it, without a line feed after the sequence.
    query = f">{QUERY}\n{sequence}"
    try:
        result = run_tool(Path(found).absolute(), args, timeout=timeout, input=query, cwd=folder)
    except subprocess.TimeoutExpired as error:
        raise BlastError(f"blastp ran past its time limit of {timeout:g} s") from error
    except OSError as error:
        raise BlastError(f"can't run blastp: {error}") from error
    if result.returncode == UNREADABLE_QUERY and any(
        line.startswith(QUERY_ERROR) for line in result.stderr.splitlines()
    ):
        raise InputError(UNREADABLE_MESSAGE)
    if result.returncode != 0:
        detail = " / ".join(result.stderr.strip().splitlines()[-3:])
        raise BlastError(f"blastp exited with status {result.returncode}: {detail}")
    return legacy.lines_of(result.stdout)
