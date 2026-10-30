"""`score()`: one protein's substitutions, scored through the legacy pipeline's three steps.

The interface agreed with the API developer on #19 (`add-csnp-job` design): frozen dataclasses,
one protein per call, the input already normalised by the API. `score()` only joins the steps
(design.md, decisions 1 and 6): it builds the SNP records `snpScore.cgi` built, runs `blastp`
(step 1), `parse_blastp.pl` (step 2) and `PANTHER_PSEP1.01.pl` (step 3), and reads the result
records the CGI read.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from panther_engine.core.data import service_folder
from panther_engine.csnp import blast, hits, psep
from panther_engine.csnp.codes import SPECIES_CODES

SERVICE = "csnp"
VERSION = "9"
# The API's rules (`scoring-input`): printable ASCII without whitespace, and the legacy CGI's
# substitution form.
SEQUENCE = re.compile(r"[!-~]+")
SUBSTITUTION = re.compile(r"([A-Z])([0-9]+)([A-Z])")
# snpScore.cgi: hmm_acc is the first record's family, cut with s/(PTHR[0-9]+).*/$1/.
FAMILY_PREFIX = re.compile(r"(PTHR[0-9]+).*")


@dataclass(frozen=True)
class CsnpInput:
    """One protein, its substitutions and its species, as the API normalised them: the sequence
    without header or whitespace, upper-cased; substitutions such as `A10E`; a species code."""

    sequence: str
    substitutions: tuple[str, ...]
    species: str


@dataclass(frozen=True)
class SubstitutionScore:
    """One substitution's score, as the legacy service reported it.

    `age` is how long the position has been preserved, in millions of years, or None where the
    legacy age is empty or the substitution isn't scored. `pdel` is the legacy two-decimal string,
    such as "0.50", or None where it isn't scored. `message` is the prediction, or the legacy
    "Not scored: ..." text.
    """

    substitution: str
    age: int | None
    message: str
    pdel: str | None


@dataclass(frozen=True)
class CsnpResult:
    """The family the protein was placed in, None without a hit, and one score per substitution,
    in input order."""

    family: str | None
    scores: tuple[SubstitutionScore, ...]


def score(request: CsnpInput, *, data_dir: Path | str | None = None) -> CsnpResult:
    """Score one protein's substitutions for one species.

    The data folder is `PANTHER_DATA_DIR`, or `data_dir` in tests. Raises ValueError, before
    anything is searched, for input the API rejects: an unknown species, a sequence that isn't
    printable ASCII without whitespace, or a substitution not in the form `A10E`. Raises
    InputError when BLAST+ can't read the sequence (divergence 8), and BlastError when it fails
    otherwise.
    """
    if request.species not in SPECIES_CODES:
        raise ValueError(f"not a species in the PANTHER9 BLAST database: {request.species!r}")
    if not SEQUENCE.fullmatch(request.sequence):
        raise ValueError("the sequence must be printable ASCII without whitespace")
    tokens = [SUBSTITUTION.fullmatch(token) for token in request.substitutions]
    if not all(tokens):
        raise ValueError("each substitution must be a residue letter, a position and a letter")
    if not request.substitutions:
        # snpScore.cgi ran the steps on no records, and showed no family.
        return CsnpResult(None, ())
    data = service_folder(SERVICE, VERSION, data_dir)
    lines = blast.search(request.sequence, data)
    records = [
        hits.SnpRecord(f"SNP_{number}", blast.QUERY, match[2], match[1], match[3])
        for number, match in enumerate(tokens, 1)
        if match is not None
    ]
    parsed = hits.parse(lines, records, request.species)
    results = psep.step3(parsed, data)
    family = reported_family(hits.legacy.split_fields(parsed[0], ",")[2] if parsed else "")
    return CsnpResult(family, tuple(to_score(record) for record in results))


def reported_family(field: str) -> str | None:
    """The family the CGI showed (`hmm_acc`): the family field cut to `PTHR` and its digits, the
    field as it is without them, or None when it's empty."""
    return FAMILY_PREFIX.sub(r"\1", field, count=1) or None


def to_score(record: str) -> SubstitutionScore:
    """A step-3 result record as a score: `snpId,subst,family,age,message,pDel`, or
    `snpId,subst,Not scored: ...`."""
    fields = record.removesuffix("\n").split(",")
    if len(fields) == 3:
        return SubstitutionScore(fields[1], None, fields[2], None)
    _, substitution, _, age, message, pdel = fields
    return SubstitutionScore(substitution, int(age) if age else None, message, pdel)
