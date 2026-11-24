"""treegrafter: places a sequence in a PANTHER family tree, and infers its subfamily and GO terms,
with HMMER3 and EPA-ng.

Reference: EBI's Python treegrafter (https://github.com/ebi-pf-team/treegrafter), at the commit
`engine/pyproject.toml` pins. It is adopted, not ported from the legacy Perl TreeGrafter/
(divergence 1). `score()` is the interface the API calls, `check_data()` its startup check,
`annotations()` the active annotation release, and `DATA_VERSION` the PANTHER release of the
library grafting reads. Importing the package loads neither EBI's code nor Biopython: they load
when a protein is grafted or a release prepared.
"""

from panther_engine.treegrafter.scoring import (
    DATA_VERSION,
    AnnotationRelease,
    TimeLimitError,
    TreegrafterError,
    TreegrafterHit,
    TreegrafterInput,
    TreegrafterResult,
    annotations,
    check_data,
    score,
)

__all__ = [
    "DATA_VERSION",
    "AnnotationRelease",
    "TimeLimitError",
    "TreegrafterError",
    "TreegrafterHit",
    "TreegrafterInput",
    "TreegrafterResult",
    "annotations",
    "check_data",
    "score",
]
