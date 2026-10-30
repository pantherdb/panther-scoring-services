"""csnp: coding-SNP impact scoring, the PANTHER-PSEP method, with BLAST+.

Reference: the legacy Perl in cSNP_analysis/ (`snpScore.cgi` and the three scripts it runs), at
`main` `cebb5ab`. `score()` is the interface the API calls; `SPECIES_CODES` the species it accepts.
"""

from panther_engine.csnp.codes import SPECIES_CODES
from panther_engine.csnp.scoring import CsnpInput, CsnpResult, SubstitutionScore, score

__all__ = ["SPECIES_CODES", "CsnpInput", "CsnpResult", "SubstitutionScore", "score"]
