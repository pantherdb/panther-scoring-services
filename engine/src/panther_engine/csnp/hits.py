"""Step 2, `parse_blastp.pl`: each query's best BLAST hit, and each substitution's position on it.

A port of `parse_blastp.pl` at `cebb5ab` (design.md, decision 4), citing its lines (`parse:n`) and
the quirk IDs of the legacy behaviour spec §6:

- **Rank (`MAP-1`):** `sort -t, -k1,1 -k3nr,3` in the C locale: by query, then percent identity
  descending, then the whole line byte by byte. BLAST+ 2.17.0 writes the identity with 3 decimals,
  where the legacy BLAST+ wrote 2, so each line's identity is recomputed and written with 2 first.
- **Filter (`MAP-2`):** with a species other than `NA`, only the lines that contain it, anywhere,
  as `grep` keeps them.
- **Best hit:** the first line per query.
- **Family and gene (`MAP-3`):** the subject id split on `:`.
- **Mapping (`MAP-4`):** `getCorrectPosition`, line for line. The residue at the alignment's start,
  and one right after a gap in the query, are never mapped.

Records are text, as the Perl reads and writes them: fields are kept as written, carriage returns
included.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from panther_engine.csnp import legacy
from panther_engine.csnp.blast import BlastError

FIELDS = 15
QSEQID, SSEQID, PIDENT, LENGTH, MISMATCH, GAPOPEN, GAPS, QSTART, QEND, SSTART, SEND = range(11)
QSEQ, SSEQ = 11, 12
# parse:9, `-s`: no species filter
NO_SPECIES = "NA"
# parse:89, `readBLASToutput`'s first `$lastline`: a query named NA never gets a hit
FIRST_QUERY = "NA"
SNP_SEPARATOR = re.compile(r"[|;]")
# GNU sort's -n: blanks, an optional minus, digits and a decimal point
SORT_NUMBER = re.compile(r"[ \t]*(-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))")


@dataclass(frozen=True)
class SnpRecord:
    """A line of step 2's SNP input, `snpId|proteinId|position|WT;MUT`, fields as written."""

    snp_id: str
    protein: str
    position: str
    wt: str
    mut: str


@dataclass(frozen=True)
class Hit:
    """The fields of a BLAST line that step 2 reads, as written; the identity with 2 decimals."""

    qseqid: str
    sseqid: str
    pident: str
    qstart: str
    sstart: str
    qseq: str
    sseq: str

    @property
    def family(self) -> str:
        """The subject id's second `:` field, such as `PTHR10366` (parse:63, 69)."""
        return self._parts()[1]

    @property
    def an_info(self) -> str:
        """The subject id's first `:` field, `SPECIES|GENE|UniProtKB=ACC`."""
        return self._parts()[0]

    def _parts(self) -> list[str]:
        return [*legacy.split_fields(self.sseqid, ":"), "", ""]


def read_snps(text: str) -> list[SnpRecord]:
    """The SNP input file, read as `readSNPfile` reads it (parse:121-141): each line chomped and
    split on `|` or `;`. Fields past the fifth are ignored; missing ones are empty."""
    records: list[SnpRecord] = []
    for line in legacy.lines_of(text):
        fields = SNP_SEPARATOR.split(legacy.chomp(line))
        while fields and not fields[-1]:
            fields.pop()
        snp_id, protein, position, wt, mut = [*fields, "", "", "", "", ""][:5]
        records.append(SnpRecord(snp_id, protein, position, wt, mut))
    return records


def parse(lines: Iterable[str], records: Sequence[SnpRecord], species: str) -> list[str]:
    """Step 2: one snpParse record per SNP record, in order, each ending in a line feed (parse:57).

    `snpId,proteinId,family,ANinfo,position,mappedPos,WT,MUT`. Family and ANinfo are empty when the
    protein has no hit, and mappedPos when the position isn't mapped.
    """
    hits = best_hits(lines, species)
    rows: list[str] = []
    for record in records:
        hit = hits.get(record.protein)
        mapped = map_position(hit, record.position, record.wt)
        family, an_info = (hit.family, hit.an_info) if hit is not None else ("", "")
        fields = (
            record.snp_id,
            record.protein,
            family,
            an_info,
            record.position,
            mapped or "",
            record.wt,
            record.mut,
        )
        rows.append(",".join(fields) + "\n")
    return rows


def best_hits(lines: Iterable[str], species: str) -> dict[str, Hit]:
    """Each query's best hit: the first of its ranked lines that the species filter keeps
    (parse:36-46, `readBLASToutput` at parse:80-112)."""
    hits: dict[str, Hit] = {}
    last = FIRST_QUERY
    for row in ranked(lines):
        if species != NO_SPECIES and species not in row:
            continue
        fields = row.split(",")
        if fields[QSEQID] == last:
            continue
        last = fields[QSEQID]
        hits[last] = Hit(
            last,
            fields[SSEQID],
            fields[PIDENT],
            fields[QSTART],
            fields[SSTART],
            fields[QSEQ],
            fields[SSEQ],
        )
    return hits


def ranked(lines: Iterable[str]) -> list[str]:
    """The lines, without line feeds, each with its identity written with 2 decimals, in the order
    of `sort -t, -k1,1 -k3nr,3` in the C locale (parse:36, `MAP-1`)."""
    rows: list[str] = []
    for line in lines:
        fields = line.removesuffix("\n").split(",")
        if len(fields) != FIELDS:
            raise BlastError(f"not a BLAST line of {FIELDS} fields: {_preview(line)}")
        fields[PIDENT] = two_decimals(fields)
        rows.append(",".join(fields))
    # Python compares strings by code point, which is byte order for these ASCII lines.
    return sorted(rows, key=lambda row: (row.split(",", 1)[0], -_sort_number(row), row))


def two_decimals(fields: Sequence[str]) -> str:
    """The identity, `100 * (length - mismatch - gaps) / length`, written with 2 decimals as the
    legacy BLAST+ wrote it. Raises BlastError if it doesn't round to the line's own value."""
    try:
        length, mismatch, gaps = (int(fields[index]) for index in (LENGTH, MISMATCH, GAPS))
    except ValueError as error:
        raise BlastError(f"not a BLAST line: {_preview(','.join(fields))}") from error
    if length <= 0:
        raise BlastError(f"an alignment of length {length}: {_preview(','.join(fields))}")
    value = 100 * (length - mismatch - gaps) / length
    written = fields[PIDENT]
    decimals = len(written.partition(".")[2])
    if f"{value:.{decimals}f}" != written:
        raise BlastError(
            f"the identity {written} isn't 100 * (length - mismatch - gaps) / length = "
            f"{value:.{decimals + 2}f}: {_preview(','.join(fields))}"
        )
    return f"{value:.2f}"


def map_position(hit: Hit | None, position: str, wt: str) -> str | None:
    """The position on the hit's subject sequence, or None where it isn't mapped: a line-for-line
    port of `getCorrectPosition` (parse:146-197, `MAP-4`).

    The query is walked residue by residue from `qstart`, counting `A`-`Z` as residues and `-` as
    gaps, and stops just after the residue before `position`. So `num` is the alignment column of
    `position` only when the next character is that residue: never at `qstart`, and not right after
    a gap in the query. The position is mapped when the subject's residue in that column is the
    wild type.
    """
    qseq = hit.qseq if hit is not None else ""
    sseq = hit.sseq if hit is not None else ""
    qstart = legacy.numify(hit.qstart if hit is not None else None)
    sstart = legacy.numify(hit.sstart if hit is not None else None)
    target = legacy.numify(position)
    residues = qstart
    gaps = 0
    for character in qseq:
        if "A" <= character <= "Z":
            residues += 1
        if character == "-":
            gaps += 1
        if residues == target:
            break
    column = int(residues + gaps - qstart + 1)
    subject = sseq[column - 1] if 0 < column <= len(sseq) else ""
    if subject != wt:
        return None
    subject_gaps = sseq[:column].count("-")
    return legacy.number_text(sstart + column - 1 - subject_gaps)


def _sort_number(row: str) -> float:
    """The third field as GNU sort's -n reads it: its leading number, or 0."""
    match = SORT_NUMBER.match(row.split(",")[PIDENT])
    return float(match[1]) if match else 0.0


def _preview(line: str) -> str:
    line = line.removesuffix("\n")
    return repr(line if len(line) <= 60 else line[:57] + "...")
