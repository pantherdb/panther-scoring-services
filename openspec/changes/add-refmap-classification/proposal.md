# Proposal

## Why

PANTHER's overrepresentation analysis can use a whole reference proteome as its reference list. For that, the website reads the organism's whole classification file from data.pantherdb.org (`generic_mapping/panther_classification/<long name>`, its `map_panther_cls` property, in `RefProteomeMapping.retrieveMappingsForOrganism`, called by `GeneListAnalysisAction` and `SelectFilesListsServlet`). The website is moving its mapping calls to this API, and that URL can't be used. The API has no replacement: a `refmap` job maps only the IDs it's sent, and the website doesn't know an organism's IDs; `GET /api/v1/refmap/organisms` gives gene counts, not genes. The data is already in the API's data folder, the same files a `refmap` job reads. This is #72.

**Area:** api. Nothing in `engine/` changes; `frontend/` only regenerates its schema types.

## What Changes

- **`GET /api/v1/refmap/organisms/{code}/classification`** answers `200` with every gene in the organism's classification file and its PANTHER ID, as JSON in the shape of a `refmap` job's result (`RefmapResult`, `{"organism", "mappings": [{"id", "panther_id"}]}`): one mapping per line, in the file's order, repeated IDs included, each line read as the engine reads it for a job; `NOHIT`, or a line with no tab, is `null`. Each request reads the file and builds its response; nothing is kept in memory, and no cache header is sent.
- **A code refmap doesn't map for is a `404`** problem, checked against the engine's `ORGANISM_CODES` before any path is built from it, so no request can name another file.
- **A listed organism whose file is missing fails with the generic `500`,** as a `refmap` job does, without the path.
- **The schema** gains the route; `api/openapi.json` and the frontend's `schema.d.ts` are regenerated. The frontend doesn't call it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `api-service`: the organism classification endpoint.

## Parity

This change doesn't affect the parity of `refmap` jobs; it adds no divergence. The endpoint replaces a static file, not a legacy program: written back as `<id>`, a tab and the PANTHER ID or `NOHIT`, one a line, its mappings are the published file byte for byte, for every one of the 1,533 organisms (tested against the real data).

## Impact

- **API:** `api/src/panther_api/routers/refmap.py`, `api/openapi.json`, a new `api/tests/test_refmap_classification.py`, and a real-data test in `api/tests/test_refmap_data.py`.
- **Frontend:** `src/app/api/schema.d.ts`, regenerated.
- **Docs:** `docs/testing/api.md`.
- **The PANTHER website** (pantherSite, outside this repository) switches `retrieveMappingsForOrganism` to this endpoint once it's deployed, through `scoring_api_base`; its `map_panther_cls` property is then unused.
- **Unchanged:** `engine/`, the jobs and their input rules, and the server's data.

## Open Questions

- **Response size:** the largest organism, ARAVE, has 246,021 genes, 10.6 MB of JSON (1.4 MB gzipped), built per request in about 0.3 s and not kept. Whether the team server wants it compressed (nginx `gzip` for `application/json`) needs team verification; the website calls it once per analysis against a whole proteome.
