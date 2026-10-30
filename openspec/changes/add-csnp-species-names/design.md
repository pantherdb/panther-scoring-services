# Design

## Context

See proposal.md, Why.

- **`csnp/codes.py` today:** `SPECIES_CODES` is a literal `frozenset` of the 85 codes, sorted, read once from the PANTHER9 BLAST database. It's a literal so the API can check a request's species without the data folder. `test_the_species_codes_are_the_blast_databases`, marked `tools("blastdbcmd")` and `data("csnp")`, checks it against the data sample's database.
- **The boundary:** the API imports the engine, and the boundary is a typed function call, not HTTP ([tech-stack.md](../../../docs/design/tech-stack.md#engine-engine-agree-with-conditions), Engine condition 1). The names cross it as a Python value, as the codes do.
- **The source:** `CSNP_SHORT_LONG_ORG_LIST`, line 79 of `legacy/panther-site-java/src/com/ab/scienceSite/constant/OrganismConstants.java`, is 85 strings of the form `CODE-Name`. `handleCsnpOrgs` splits each at its first hyphen. Its codes are exactly `SPECIES_CODES`.
- **Why the UI needs them:** [frontend-stack.md](../../../docs/design/frontend-stack.md#rules-that-come-with-it), rule 4, asks the UI to match the legacy species selector.

## Goals / Non-Goals

**Goals:**

- One literal holds each code with its name, so the codes and the names can't disagree.
- CI can tell when a name no longer matches the old site's list, without reading `panther-workspace`.

**Non-Goals:**

- A `panther-engine` command that lists the species. Nothing needs one yet.
- Names in `CsnpInput` or `CsnpResult`. A score is for a species code, as the legacy service's was.
- Common names such as "Human". The source has none.

## Decisions

1. **`SPECIES_NAMES` is the literal, and `SPECIES_CODES` is derived from it:** `SPECIES_CODES = frozenset(SPECIES_NAMES)`.
   - Its value and type don't change, so the API's import and the database test keep working, and the database test then covers the names' codes too.
   - *Alternative:* two literals and a test that they agree. Rejected: the 85 codes would be written twice.
   - *Alternative:* read the names from a file in the data folder at run time. Rejected for the same reason the codes are a literal: the API checks species without the data.
2. **Read-only:** a `types.MappingProxyType` over a `dict`, typed `Mapping[str, str]`.
   - Like the `frozenset`, it is module state shared by every caller in a process, so no caller may change it for the others (spec, Read-only).
   - *Alternative:* a plain `dict`. Rejected: one caller could change it for every other.
   - *Alternative:* a tuple of pairs. Rejected: no lookup by code.
   - *Alternative:* a third-party frozen mapping. Rejected: a new dependency for what the standard library already does.
3. **Names exactly as the list writes them,** split at the first hyphen as `handleCsnpOrgs` does. That includes `Synechocystis` with no strain, and older names such as `Canis familiaris` (proposal, Open Questions).
4. **Code order,** as `codes.py` already sorts. The old site's own order came from a rank in a database we don't have. The spec promises no order, so the frontend can sort as it likes.
5. **A checksum ties the names to the old site's list.**
   - During apply, compute the sha256 of the list's 85 entries, `CODE-Name`, one per line, in the list's order, from `OrganismConstants.java`. Pin it in a unit test that builds the same text from `SPECIES_NAMES`.
   - Any change to a name, or a code, then fails in CI, and whoever changes a name on purpose updates the checksum and says why.
   - If the list's order isn't code order, the test sorts both the same way, and the Notes say so.
   - *Alternative:* a test that reads `OrganismConstants.java` when `../panther-workspace` is there, and skips otherwise. Rejected: it would always skip in CI, and `CLAUDE.md` says not to assume where that checkout is.
   - *Alternative:* spot checks only. Kept for the spec's scenarios, but they'd miss a typo in any other name.

## Risks / Trade-offs

- [Production may have shown other names for some codes] → The list is the only source in `panther-workspace` (proposal, Open Questions). A later change can replace a name, and its review then updates the checksum.
- [Users see some older taxonomic names] → Kept to match the old site. Updating them is the science owner's call.
- [Callers come to rely on code order] → The spec promises none, and the docstring says the order is the codes'.

## Migration Plan

None: the change only adds. Rolling it back means reverting the change, as long as nothing imports `SPECIES_NAMES` by then.
