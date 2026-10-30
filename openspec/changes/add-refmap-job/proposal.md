# Proposal

**Area:** cross-cutting. The code is in `api/`, plus the regenerated `frontend/src/app/api/schema.d.ts`. Nothing in `engine/` changes, but design.md proposes the engine's `refmap` interface, so the engine developer approves it, and the frontend developer reviews the contract (CONTRIBUTING.md, Review Rules).

## Why

`refmap` is the second service to port. As for cSNP (#19, `add-csnp-job`), agreeing the contract first lets the frontend and the website build against the real request, result and `422`s, and lets the engine developer port `map_panther.pl` against a fixed interface. The legacy service had no written contract at all: what it accepts and returns is only in two 50-line Perl scripts and the website's Java, so this change also records it, with evidence, in [docs/parity/refmap-legacy-behaviour.md](../../../docs/parity/refmap-legacy-behaviour.md).

## What Changes

- **A `refmap` job request** joins the request union: `{"service": "refmap", "input": {"organism": "HUMAN", "ids": ["P04217", "P01023"]}}`.
  - `organism`: required, 1 to 5 upper-case letters or digits, the shape of a UniProt species mnemonic, as cSNP's `species` is. Membership in the engine's organism list is checked once the engine exports one, as cSNP's was (#24).
  - `ids`: a list of 1 to 100,000 identifiers, each 1 to 64 printable ASCII characters without whitespace. Not trimmed, not upper-cased and not de-duplicated: the legacy lookup is exact and case-sensitive, and returns one row per input line.
- **A `refmap` job** joins the job union. Its `result` is `{"mappings": [{"id": string, "panther_id": string | null}]}`: one mapping per submitted ID, in order, duplicates included. `panther_id` is the PANTHER ID the classification file gives, such as `PTHR10078:SF1` (the website help's example), or `null` where the legacy printed `NOHIT`.
- **Not available yet:** a valid `refmap` request gets `501 Not Implemented` as problem details, "refmap ID mapping isn't available yet.", and no job is created. The `501` is documented in the OpenAPI schema. `run_job` has a `refmap` case that raises `NotImplementedError`, as `csnp`'s did before #26. The change that wires the engine in removes all three.
- **No mapping is made up anywhere,** in the code or the tests: nothing returns a PANTHER ID until the engine does.
- **A job, not a synchronous endpoint.** The API's rule is to score through jobs, and tech-stack.md leaves `refmap` open. design.md recommends a job, with the reasons and the synchronous alternative, as a decision for the engine and API developers.
- **The engine interface, proposed:** `panther_engine.refmap.map_ids(RefmapInput) -> RefmapResult`, frozen dataclasses, the input already validated by the API, and `ORGANISM_CODES` exported for the API's membership check (design.md, decision 3).
- **Contract files:** `api/openapi.json` and `frontend/src/app/api/schema.d.ts` regenerated. Nothing else in `frontend/` changes: its job types (`src/app/api/wire.ts`) list each service by hand, and no `refmap` job can exist while the `501` stands. They gain `refmap` with the refmap form, a later change.
- **Docs:** `api/README.md` and `docs/testing/api.md` (the `refmap` job and its `501`). `docs/parity/refmap-legacy-behaviour.md`: the legacy service as the code runs it, with quirk IDs (`REFMAP-1`, …), what the website called and how it used the answers, the data, and the proposed golden inputs. `docs/parity/README.md` lists it.

No new dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-input`: new requirements for a refmap input's `organism` and `ids`.
- `scoring-jobs`: new requirements for the `refmap` job request, the `refmap` job's shape, and the `501` while mapping isn't available. Only ADDED requirements, so it doesn't conflict with `wire-csnp-scoring`, which removes cSNP's `501` requirement from the same capability, or with `add-job-input-errors`. Any of them can archive first.

## Impact

- **API:** a new `api/src/panther_api/jobs/refmap.py` (the input with its validation, and the result); `jobs/work.py` (the request and result unions, and a `run_job` case that refuses to run); `jobs/models.py` (`RefmapJob`); `routers/jobs.py` (the `501`, documented in the schema); tests.
- **API contract:** new schema components `RefmapJobRequest`, `RefmapInput`, `RefmapJob`, `RefmapResult` and `IdMapping`, and a `501` response on `POST /api/v1/jobs`. Existing shapes don't change.
- **Frontend:** only the regenerated `schema.d.ts`. `npm run type-check` passes without other changes.
- **Engine:** no code changes, and no import of `panther_engine.refmap`, which is an empty module today. The engine developer reviews the proposed interface in design.md before porting.
- **Parity with the reference:** this change maps nothing, so no output changes and no divergence row is needed. Its validation must not reject any input the legacy would have mapped: design.md lists each rule with its legacy evidence. The rules that are new, where the legacy had no limit (64 characters per ID, no whitespace in an ID) or silently mishandled the input (an unknown organism mapped everything to `NOHIT`), are listed below.

## Open Questions

For the engine developer (needs team verification where the legacy code doesn't settle it):

- **The organism key.** The website sent the organism's long name from the `stats` file, which is also the classification file's name (`index.jsp` 1343, `genericMapping.cgi` 41). The code reads it as `Genus_species_CODE` and shows the last `_` part as the short name (`MapOrganism.java` 33 to 49). The contract takes that code. Is it always a unique UniProt mnemonic of 1 to 5 upper-case letters or digits? If not, `organism` takes the long name instead, with a shape check that keeps it out of any path.
- **The classification files.** Their source (no `panther_build` code or doc names `panther_classification/`), count (the help says 800+ and 900+, the Phase 1 user guide 1,533), size, columns beyond the first two, line endings (`REFMAP-3`), and whether any ID repeats in a file (`REFMAP-2`). And whether the PANTHER 19 copy behind `mapping19` still exists, for the goldens.
- **The engine's organism list:** a literal in code, as `SPECIES_CODES` is, or read from the data's `stats` file at startup? design.md, decision 3.
- **The data layout:** `refmap/19/` under `PANTHER_DATA_DIR`, as `core/data.py` lays out each service, or the shared `/data/panther/<version>/` root tech-stack.md's Shared Concerns describe for the current release?
- **The limits:** 100,000 IDs follows the website's line limit; 64 characters per ID and no whitespace are new. Fine from the engine side?
- **Keep or fix:** each quirk in the legacy behaviour doc marked **Decide**. The contract assumes **Match** for all of them, as M1 follows the code.

For the team:

- **Jobs or synchronous** for `refmap` (tech-stack.md, Open Questions): design.md, decision 1, recommends a job.
- **`map_panther_cls` and `map_panther_stats`.** The website also fetched each organism's whole classification file, as the reference list for its enrichment tests, and the `stats` list of organisms with gene counts. Neither maps IDs. The organism list becomes an endpoint once the engine exports it (follow-up). What replaces the whole-file download, and is it part of these four services at all?
- **Columns after the ID.** The legacy echoed every column after the ID back after the PANTHER ID, and the website's enrichment test read its expression value from there (`REFMAP-5`). The contract takes IDs only and returns one mapping per ID in order, so a client re-attaches its own columns by position. Does the website's port to the JSON API agree?
- **Was `genericMapping.cgi` reachable from outside the website's server?** Its `organism` goes unchecked into a two-argument `open`, which reads any file or runs a command (`REFMAP-8`). The site's settings point at `localhost`, with a public host commented out. The port never repeats it either way.
