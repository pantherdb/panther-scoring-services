# Proposal

## Why

The engine maps protein IDs since #63 (`port-refmap`), with full parity against `map_panther.pl`, but the API still answers every valid `refmap` request with `501`, and the form is marked "coming soon". This change wires the two together, so protein ID mapping works end to end. It's #40, with #41 folded in, since both change how a `refmap` request is validated.

**Area:** cross-cutting: `api/` and `frontend/`, with their docs and tests. Nothing in `engine/` changes; the engine developer reviews how the API calls it.

## What Changes

- **`refmap` jobs run.** A valid request gets `202` and a job that calls the engine's `map_ids` in a worker, as `csnp` jobs call `score`. The `501`, its row in `UNAVAILABLE` and `run_job`'s refusing case go, and the `501` leaves the schema. **BREAKING** for a client that relied on the `501`; none does but the form, which changes here.
- **`organism` must be an organism refmap maps for**, one of the engine's 1,533 `ORGANISM_CODES`, not only the shape of one. `HUMAN`, `MOUSE` and `ECOLI` are now rejected with a `422`: PANTHER's own 143 genomes aren't in the generic mapping data (#52). The messages' example becomes `ENDPU`.
- **The result names its organism:** `{"organism", "mappings"}`, as the engine's `RefmapResult` does.
- **`GET /api/v1/refmap/organisms`** lists every organism with its code, name and gene counts, from the engine, with no data needed, cacheable for an hour, as `GET /api/v1/csnp/species` does.
- **The startup check covers refmap's data,** logging an error, without stopping, when the folder lacks a file, as for cSNP.
- **A large result is kept compactly, within a budget.** 100,000 mappings take about 59 MB as models; the job keeps them for 24 hours. The result is kept serialised instead, about a tenth of that, and each poll stops re-serialising it. The finished jobs' results share a memory budget, 256 MiB by default: over it, the largest results expire first, so a burst of large jobs doesn't expire everyone's smaller ones.
- **A request with 100,000 bad IDs answers its `422` in about the time a valid one takes** (#41), about 0.2 s instead of 1.1 s on the event loop, with the same body: the first 100 errors at their `loc`s, and the total in `detail`.
- **The form:** a searchable organism selector fed by the new endpoint, as cSNP's species selector is, with a box to type a code when the list can't load; the example becomes six IDs from the data's own ENDPU test list; the "not available yet" path goes; ID mapping is no longer "coming soon".
- **The job page says which organism** the IDs were mapped against.
- **Docs:** the `refmap` sections of `docs/testing/api.md` and `docs/testing/frontend.md`, and `docs/manual-qa/03-refmap-form.md`, move from the `501` and `HUMAN` to real jobs and `ENDPU`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-jobs`: a valid `refmap` request starts a job that maps with the engine (the "not available yet" requirement is removed); the result carries `organism`; the startup check covers the refmap data; finished jobs' results share a configurable memory budget; a job's versions name only its own service's data.
- `scoring-input`: a refmap `organism` must be one of the engine's organisms.
- `api-service`: the organism list endpoint; a large invalid list gets its `422` as fast as a valid one; the versions report names refmap's PANTHER 19 data beside cSNP's PANTHER 9.
- `scoring-ui`: the organism selector and its fallback, the ENDPU example, the organism on the job page, the submit failures without the `501`, and ID mapping no longer coming soon.

## Parity

This change doesn't affect parity: the API passes the organism and the IDs to `map_ids` unchanged, and returns its mappings in order. The engine's goldens and its full run (#63) prove the mapping. The divergences it relies on, rows 9 and 10 in `docs/parity/divergences.md`, are approved (#52). A missing classification file (row 9) fails the job with the generic `500`, as the engine's `MissingDataError` does for any service.

## Impact

- **API:** `api/src/panther_api/jobs/` (`refmap.py`, `work.py`, `store.py`, `fields.py`), `routers/jobs.py`, a new `routers/refmap.py`, `main.py`'s startup check, `api/openapi.json`, and tests, including real-data ones marked `data("refmap")`.
- **Frontend:** `src/features/refmap/`, `src/features/jobs/` (the organism on the job page), `src/app/services.ts`, `src/app/api/` (the regenerated types, `wire.ts`, the organism list endpoint), `src/mocks/`, unit and e2e tests.
- **CI:** the API's real-data tests need the refmap data, cached as the engine's jobs cache it.
- **The team server** needs the refmap data, 523 MB, under its `PANTHER_DATA_DIR`, fetched with `panther-engine refmap data fetch`. Until it's there, `refmap` jobs fail with the generic `500` and the API logs why at startup.
- **Unchanged:** `engine/`, the `csnp` and `tools` jobs, and the input rules for `ids`.

## Open Questions

- **The results budget on the team server:** 256 MiB is a starting default; the engine developer, who runs the server, sets the value that suits it.
- **The gene counts in the organism list** serve the website's enrichment tests, which read them from `stats` before (`ORGANISM_GENES`). Whether the website's port wants them from this endpoint needs team verification; they cost nothing to include.
