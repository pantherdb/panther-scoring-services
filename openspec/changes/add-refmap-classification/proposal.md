# Proposal

## Why

PANTHER's overrepresentation analysis can use a whole reference proteome as its reference list. For that, the website reads the organism's whole classification file from data.pantherdb.org (`generic_mapping/panther_classification/<long name>`, its `map_panther_cls` property, in `RefProteomeMapping.retrieveMappingsForOrganism`, called by `GeneListAnalysisAction` and `SelectFilesListsServlet`). The website is moving its mapping calls to this API, and that URL can't be used. The API has no replacement: a `refmap` job maps only the IDs it's sent, and the website doesn't know an organism's IDs; `GET /api/v1/refmap/organisms` gives gene counts, not genes. The data is already in the API's data folder, the same files a `refmap` job reads. This is #72.

**Area:** cross-cutting: `api/` and `engine/`. The engine gains an exported reader of a whole classification file, shared with `map_ids`, and a command that builds each organism's response ahead of time; the engine developer reviews both (review of #73). `frontend/` only regenerates its schema types.

## What Changes

- **`GET /api/v1/refmap/organisms/{code}/classification`** answers `200` with every gene in the organism's classification file and its PANTHER ID, as JSON in the shape of a `refmap` job's result (`RefmapResult`, `{"organism", "mappings": [{"id", "panther_id"}]}`): one mapping per line, in the file's order; `NOHIT`, or a line with no tab, is `null`. A repeated ID appears once for each of its lines, where a job gives the last line's value each time.
- **The response is built ahead of time, not per request.** `panther-engine refmap data build-json` writes each organism's JSON, gzipped, to `refmap/19/classification_json/<code>.json.gz` (176 MB for the 1,533 organisms, about a minute). It's run where the data is, such as the HPC system, and the folder copied to the server's data folder. The API sends the file from disk a piece at a time: as it is, with `Content-Encoding: gzip`, to a client that accepts gzip, and decompressed as it's sent to any other. Nothing is built or kept in memory, and no `Cache-Control` or `ETag` is sent.
- **The engine reads the file once for both callers.** `classification_mappings(code)` yields every line as an `IdMapping`, with the line and field rules `map_ids` uses, from one shared reader (`classification_lines`), so a change to how a line is read reaches jobs and this endpoint alike. It, `classification_json_file` and `check_classification_json` are exported.
- **A code refmap doesn't map for is a `404`** problem, checked against the engine's `ORGANISM_CODES` before any path is built from it, so no request can name another file. Its problem is in the schema; no `422` is listed, since none can happen.
- **A listed organism whose JSON is missing fails with the generic `500`,** without the path, logged at most once in ten minutes. The startup check logs which files are missing, once the refmap data itself is in place.
- **The schema** gains the route; `api/openapi.json` and the frontend's `schema.d.ts` are regenerated. The frontend doesn't call it.

## Why Not a Job

`api/CLAUDE.md` asks for a team decision before a synchronous scoring endpoint, and leaves open whether `refmap` gets one (`add-refmap-job`). This isn't one: nothing is submitted or computed per request. It's reference data, like `GET /refmap/organisms`: the same bytes for every request until the data changes, sent from a file built ahead of time. Mapping a client's IDs stays a job, and the open question about a synchronous `refmap` is unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `api-service`: the organism classification endpoint.
- `refmap-engine`: reading an organism's whole classification file, shared with `map_ids`.
- `refmap-data`: building the classification JSON.

## Parity

This change doesn't affect the parity of `refmap` jobs; it adds no divergence. `map_ids` reads lines through the shared reader with the same rules, and its tests and goldens pass unchanged. The endpoint replaces a static file, not a legacy program: written back with the engine's `render`, one a line, `classification_mappings` gives the published file byte for byte, for every one of the 1,533 organisms (engine release tests).

## Impact

- **Engine:** `refmap/mapping.py` (`classification_lines`, `classification_mappings`, `classification_json_file`, `check_classification_json`; `read_classification` uses the shared reader), `refmap/data.py` (`build_classification_json`), `refmap/cli.py` (`refmap data build-json`), `refmap/__init__.py`'s exports, a new `tests/test_refmap_classification.py`, and release tests in `tests/test_refmap_release_data.py`.
- **API:** `routers/refmap.py`, `main.py`'s startup check, `problems.py` (`NO_VALIDATION_PROBLEM`), `jobs/refmap.py`'s `RefmapResult` description, `api/openapi.json`, `tests/test_refmap_classification.py`, `tests/test_refmap_data.py` and `tests/test_limits.py`.
- **Frontend:** `src/app/api/schema.d.ts`, regenerated.
- **Docs and CI:** `docs/testing/api.md`, `docs/testing/engine.md`, `docs/deployment/runbook-server.md`, and the comment on CI's refmap data tests.
- **The server** needs `refmap/19/classification_json/` beside the refmap data, built with `build-json`, before the endpoint answers.
- **The PANTHER website** (pantherSite, outside this repository) switches `retrieveMappingsForOrganism` to this endpoint once it's deployed, through `scoring_api_base`; its `map_panther_cls` property is then unused.
- **Unchanged:** the jobs and their input rules, `refmap data fetch` and the manifest.

## Open Questions

- **Building on the server's data:** the JSON is built from the same pinned release wherever it's built, so building it on the HPC system and copying it is equivalent; whether the deploy steps should also check it (`check_classification_json`) before switching the website needs team verification.
