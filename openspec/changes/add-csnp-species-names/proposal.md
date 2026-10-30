# Proposal

**Area:** engine. It adds to the engine's interface, so the API developer reviews it too (CONTRIBUTING, Review Rules).

## Why

The cSNP form asks the user to type a species code such as `HUMAN`. The old site offered a list of its 85 organisms by name, and `docs/design/frontend-stack.md` asks the UI to match its species selector. On #20, and again when asked on #24, the engine developer said the engine would publish each code's name, so the API can serve the list to the form. `port-csnp` published only the codes, `SPECIES_CODES`.

## What Changes

- **`SPECIES_NAMES`,** exported by `panther_engine.csnp`: a read-only mapping from each of the 85 species codes to its name, such as `HUMAN` to `Homo sapiens`.
- **The names are the old site's,** as written in its cSNP list, `CSNP_SHORT_LONG_ORG_LIST` in `panther-site-java`'s `OrganismConstants.java`.
  - That list has exactly the 85 codes of the PANTHER9 BLAST database (checked 2026-10-30).
  - It has scientific names only, so a selector can show "Homo sapiens (HUMAN)" but not "Human".
- **`SPECIES_CODES` becomes the mapping's keys,** so the two can't drift. Its value and type don't change, and the existing test against the BLAST database then covers the names' codes too.

Not in this change:

- **Serving the names** (API developer), and checking a request's species against `SPECIES_CODES`, which is already planned with removing the `501`.
- **A species selector** in the form (frontend developer). `scoring-input` and `scoring-ui` don't change here.
- **Updating any name** to today's taxonomy (Open Questions).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `psep-engine`: a new requirement, Species names. The Species codes requirement doesn't change.

## Impact

- **Code:** `engine/src/panther_engine/csnp/codes.py` holds the names, and `csnp/__init__.py` exports them.
- **Tests:** unit tests in `engine/tests/test_csnp_scoring.py`, beside the codes' tests.
- **API contract:** not affected. Nothing in `api/` or `frontend/` changes, and the API's import of `SPECIES_CODES` keeps working.
- **Dependencies:** none.
- **Parity with the reference:** not affected, and no divergence row is needed. Names aren't part of any score, and the legacy pipeline never saw them: the site turned the chosen name into a code before calling `snpScore.cgi` (`CsnpScoreAction.java`).
- **Size:** about 430 changed lines, a little over the 400-line norm. 190 are `codes.py`, where the names' 85-entry literal replaces the codes' line for line, and about 180 are this change's own artifacts.

## Open Questions

Each needs team verification:

- **Which names production showed.** The old site took an organism's name from its database's organism table when that table had the code, and from this list only otherwise (`OrganismConstants.handleCsnpOrgs`). That table isn't in `panther-workspace`, so whether production showed other names for some codes is unknown. The list is the only source we have.
- **Order.** The old site listed the organisms by a rank from the same table, then by name. The engine gives the mapping in code order; the order on screen is the frontend's choice.
- **Older names.** Some names predate today's taxonomy, such as `Canis familiaris` and `Emericella nidulans`. This change keeps them as the list has them. Updating them is the science owner's call.

For review:

- **Copying the names from `panther-site-java`.** `CLAUDE.md` asks for a team decision before copying legacy source into this repo. The 85 names are data, not code, and the review of this change is that decision.
