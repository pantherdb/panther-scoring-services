"""The refmap goldens the API's tests use, read from the engine's tests (read-only).

`test_geneList.out` is `map_panther.pl`'s output for the release's own ENDPU test list
(`engine/tests/golden/refmap/README.md`): one line per ID, the ID, a tab and its PANTHER ID or
`NOHIT`. As an ENDPU classification file it gives the same answers, so a made-up data folder
holding it lets a job run the real engine on real values without the 523 MB release
(openspec wire-refmap, design.md, decision 8).
"""

from pathlib import Path

from markers import REPO_ROOT

GOLDEN_LIST = REPO_ROOT / "engine" / "tests" / "golden" / "refmap" / "out" / "test_geneList.out"

ORGANISM = "ENDPU"

EXAMPLE_IDS = ("U1G4Q5", "U1GCA1", "U1HRR6", "U1GLV9", "U1GJ40", "U1HQ27")
"""The form's example: subfamilies, families and an ID with no PANTHER ID."""

EXAMPLE_PANTHER_IDS = (
    "PTHR11360:SF130",
    "PTHR21058:SF0",
    "PTHR42765:SF2",
    "PTHR28011",
    "PTHR13401",
    None,
)
"""What `map_panther.pl` gives the example, in order (openspec scoring-jobs, The form's example)."""


def golden_mappings() -> dict[str, str | None]:
    """The golden's PANTHER ID for each of its IDs, `None` for `NOHIT`."""
    mappings: dict[str, str | None] = {}
    for line in GOLDEN_LIST.read_text(encoding="ascii").splitlines():
        an_id, panther_id = line.split("\t")[:2]
        mappings[an_id] = None if panther_id == "NOHIT" else panther_id
    return mappings


def write_endpu_folder(data_dir: Path) -> Path:
    """A made-up refmap data folder in `data_dir` holding only ENDPU's classification file, the
    golden's lines. Its path."""
    path = data_dir / "refmap" / "19" / "panther_classification" / ORGANISM
    path.parent.mkdir(parents=True)
    path.write_bytes(GOLDEN_LIST.read_bytes())
    return path
