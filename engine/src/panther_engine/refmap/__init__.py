"""refmap: maps protein IDs, such as UniProt accessions, to PANTHER families.

Reference: RefProteomeMapper's `map_panther.pl`, at `4fc6a09`. `map_ids()` is the interface the API
calls, and `check_data()` its startup check. `classification_mappings()` gives an organism's whole
classification file, and `classification_json_file()` the gzipped JSON of it that `refmap data
build-json` builds, checked by `check_classification_json()`. `ORGANISM_CODES` are the organisms it
maps for, `ORGANISM_NAMES` their names, `ORGANISM_GENES` their gene counts, and `DATA_VERSION` the
PANTHER release of the data it reads.
Importing the package reads no data, and doesn't load the fetch or parity code.
"""

from panther_engine.refmap.mapping import (
    IdMapping,
    RefmapInput,
    RefmapResult,
    check_classification_json,
    check_data,
    classification_json_file,
    classification_mappings,
    map_ids,
)
from panther_engine.refmap.organisms import (
    ORGANISM_CODES,
    ORGANISM_GENES,
    ORGANISM_NAMES,
    GeneCounts,
)
from panther_engine.refmap.organisms import VERSION as DATA_VERSION

__all__ = [
    "DATA_VERSION",
    "ORGANISM_CODES",
    "ORGANISM_GENES",
    "ORGANISM_NAMES",
    "GeneCounts",
    "IdMapping",
    "RefmapInput",
    "RefmapResult",
    "check_classification_json",
    "check_data",
    "classification_json_file",
    "classification_mappings",
    "map_ids",
]
