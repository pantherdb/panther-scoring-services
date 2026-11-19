"""hmmscore: scores protein sequences against the PANTHER HMM library, with HMMER3.

Reference: the legacy Perl in pantherScoring/, `scoreAlignXml.cgi` and the `pantherScore.pl` it
runs, at `89ea0ae`. `score()` is the interface the API calls, and `check_data()` its startup
check. `DATA_VERSION` is the PANTHER release of the library it reads.
"""

from panther_engine.hmmscore.scoring import (
    DATA_VERSION,
    HmmHit,
    HmmscoreError,
    HmmscoreInput,
    HmmscoreResult,
    TimeLimitError,
    check_data,
    score,
)

__all__ = [
    "DATA_VERSION",
    "HmmHit",
    "HmmscoreError",
    "HmmscoreInput",
    "HmmscoreResult",
    "TimeLimitError",
    "check_data",
    "score",
]
