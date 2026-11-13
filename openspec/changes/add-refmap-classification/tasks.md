# Tasks

## 1. Engine

- [x] 1.1 `refmap/mapping.py`: `classification_lines`, the shared line reader, used by `read_classification`; `classification_mappings`, `classification_json_file` and `check_classification_json`, exported from `panther_engine.refmap` (design.md, decision 2). Verify in a new `tests/test_refmap_classification.py`: every line in order with NOHIT, a repeated ID, a `\r`, no tab, an empty value, a third field and a Latin-1 byte; agreement with `read_classification`; empty lines and files; unlisted organisms refused before reading; a missing file; no data folder; and that `tests/test_refmap_mapping.py` passes unchanged (spec, refmap-engine: An organism's whole classification)
- [x] 1.2 `refmap/data.py`: `build_classification_json`, streamed in batches into gzip, moved into place, mode 0644, with no name or time in the header; `refmap/cli.py`: `refmap data build-json`, with `--organisms` and `--missing-only` (decision 4). Verify: every mapping, a file longer than a batch, the same bytes twice, mode and no partial file, `--missing-only`, a missing source, and the command's output and error (spec, refmap-data: Building the classification JSON)
- [x] 1.3 Release tests in `tests/test_refmap_release_data.py`: every organism's mappings, written back with `render`, are its file, with `stats`'s counts; the JSON built for ENDPU, ABSGL and ARAVE holds their mappings. Verify with the data (about 30 s)
- [x] 1.4 Engine checks: `uv run ruff check`, `ruff format --check`, `basedpyright` and `pytest`

## 2. API

- [x] 2.1 `routers/refmap.py`: the route checks `ORGANISM_CODES`, then streams `classification_json_file`'s bytes, gzipped or decompressed by `Accept-Encoding`, with `Vary` and no cache headers; the 404's `Problem` model; `NO_VALIDATION_PROBLEM` in `problems.py`, so no 422 is listed; a missing file or data folder answers the generic 500, logged at most once in ten minutes (decisions 3 to 6). `RefmapResult`'s description covers both uses. Verify in `tests/test_refmap_classification.py`: gzipped with its length, plain, no cache headers, `Accept-Encoding` parsing, 404s that reach the route and build no path, the 500 logged once, no data folder, and the schema's 200, 404 and no 422 (spec, api-service)
- [x] 2.2 `main.py`: once the refmap data is in place, the startup check logs missing classification JSON. Verify in `tests/test_limits.py`: the new line alone when only the JSON is missing, and the other startup tests with it patched (spec, The startup check)
- [x] 2.3 With the real data: `tests/test_refmap_data.py` fetches every organism's classification, gzipped, and one plain, and compares them with `classification_mappings`; skipped without the JSON. Verify with the data and the JSON built (about 50 s)
- [x] 2.4 Regenerate `api/openapi.json`. API checks: `uv run ruff check`, `ruff format --check`, `basedpyright` and `pytest`

## 3. Frontend

- [x] 3.1 Regenerate the types (`npm run api:types`). Verify `npm run api:types:check`, `format:check` and `type-check`

## 4. Docs

- [x] 4.1 `docs/testing/api.md`: the endpoint, building the JSON, gzip, the startup line and the real-data test; `docs/testing/engine.md`: `build-json`; `docs/deployment/runbook-server.md`: building it on the HPC system and copying it; the comment on CI's refmap data tests. Final check: from the root, `npx markdownlint-cli2`, `npx openspec validate --all` and `npx openspec validate add-refmap-classification --strict` pass

## Workflow follow-up

- **Review:** the engine developer reviews the engine's new reader and `build-json` (#73); #72 closes with the merge.
- **On the server:** build the classification JSON (HPC) and copy `classification_json/` beside the refmap data, before the PANTHER website's switch is deployed.
- **After the implementation merges,** archive with `/opsx:archive`.

## Notes

### Next action

The review of #73 is answered (2026-11-13). Waiting for the engine developer's re-review.

### Blockers

None.

### Failed approaches

- **Building each response per request (2026-11-12).** Correct, but the review of #73 measured about 106 MB and 0.3 to 0.6 s of CPU per ARAVE request, with nothing limiting how many run at once; replaced by the JSON built ahead of time (design.md, decision 4).

### Lessons learned

- **The real files rebuild exactly (2026-11-12):** all 1,533 organisms' files are two fields a line, with no line lacking a tab or with a third field, so `render` gives each file back byte for byte.
- **Sizes (2026-11-13):** the JSON for all 1,533 organisms is 176 MB gzipped, built in 53 s; ARAVE 10.6 MB of JSON, 1.5 MB gzipped; ENDPU 394 KB, 66 KB.
- **`tempfile.mkstemp` makes a file readable by its owner only;** a file the API reads as another user needs its mode set before it's moved into place.
- **Starlette's `FileResponse` adds `ETag` and `Last-Modified`;** a response that mustn't carry them is streamed instead.
- **httpx normalises `..` out of a URL, and an encoded `/` matches no route,** so a test of a route's own 404 asserts its detail, which the router's unmatched-route 404 doesn't have.
