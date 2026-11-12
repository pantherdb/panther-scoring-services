# Tasks

## 1. API

- [x] 1.1 `routers/refmap.py`: `GET /refmap/organisms/{code}/classification` returns `RefmapResult`'s JSON built by `classification_json` in the threadpool, with no cache header; a code that doesn't match the pattern or isn't in `ORGANISM_CODES` is a 404 before any path is built; a missing file raises `MissingDataError` (design.md, decisions 1 to 4). Verify in a new `tests/test_refmap_classification.py`: mappings in the file's order with `NOHIT`, a repeated ID, a line with no tab and a third field; the content type and no `Cache-Control`; 404 problems for `NOPE1`, `endpu`, `ENDPUX`, `..`, `%2E%2E` and `ENDP%2F`; the generic 500 without the path for a listed organism without its file; the schema's entry (spec, refmap organism classification)
- [x] 1.2 Regenerate `api/openapi.json` with `uv run python -m panther_api.openapi`. Verify `tests/test_openapi.py` passes
- [x] 1.3 With the real data: a test marked `data("refmap")` in `tests/test_refmap_data.py` fetches every organism's classification, rebuilds its file from the mappings and compares the bytes and `stats`'s counts. Verify it passes with the data and skips without it (spec, The published file, rebuilt)
- [x] 1.4 API checks: `uv run ruff check`, `ruff format --check`, `basedpyright` and `pytest`

## 2. Frontend

- [x] 2.1 Regenerate the types (`npm run api:types`). Verify `npm run api:types:check`, `format:check` and `type-check`

## 3. Docs

- [x] 3.1 `docs/testing/api.md`: the endpoint in the list of URLs, and a section after The Organism List. Final check: from the root, `npx markdownlint-cli2`, `npx openspec validate --all` and `npx openspec validate add-refmap-classification --strict` pass

## Workflow follow-up

- **Review:** the engine developer reviews the reading of the classification file outside `read_classification` (design.md, decision 2); #72 closes with the merge.
- **On the server:** nothing new; the refmap data is already there for jobs. The PANTHER website's switch is deployed after this one.
- **After the implementation merges,** archive with `/opsx:archive`.

## Notes

### Next action

Every task is done. Open the pull request for #72 when the user asks.

### Blockers

None.

### Failed approaches

None.

### Lessons learned

- **The real files rebuild exactly (2026-11-12):** all 1,533 organisms' files are two fields a line, with no line lacking a tab or with a third field, so `<id>`, a tab and the PANTHER ID or `NOHIT` gives each file back byte for byte; the test takes about 35 s for 523 MB.
- **Sizes and times (2026-11-12),** through the app: ENDPU 9,228 mappings, 394 KB, 10 ms; ABSGL 14,825, 685 KB, 13 ms; ARAVE 246,021, 10.6 MB (1.4 MB gzipped), 277 ms.
