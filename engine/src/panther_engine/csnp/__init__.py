"""csnp: coding-SNP impact scoring, the PANTHER-PSEP method, with BLAST+.

Reference: the legacy Perl in cSNP_analysis/ (`snpScore.cgi` and the three scripts it runs), at
`main` `cebb5ab`. `score()` is the interface the API calls; `SPECIES_CODES` the species it accepts,
`SPECIES_NAMES` their names, and `DATA_VERSION` the PANTHER release of the data it reads.
"""

from panther_engine.csnp.codes import SPECIES_CODES, SPECIES_NAMES
from panther_engine.csnp.scoring import VERSION as DATA_VERSION
from panther_engine.csnp.scoring import CsnpInput, CsnpResult, SubstitutionScore, score

__all__ = [
    "DATA_VERSION",
    "SPECIES_CODES",
    "SPECIES_NAMES",
    "CsnpInput",
    "CsnpResult",
    "SubstitutionScore",
    "score",
]
