# Tasks

## 1. API: refmap jobs run

- [x] 1.1 `jobs/refmap.py`: the organism validator checks `ORGANISM_CODES` after the shape, with the message naming `ENDPU` and the organism list (design.md, decision 2); the module docstring and `RefmapInput`'s docstring drop `HUMAN`. Verify in `tests/test_refmap_input.py`: `ENDPU`, `ARAVE` and `ECO57` accepted; `HUMAN`, `ECOLI` and `ZZZZZ` rejected on `organism` without the value; every code in `ORGANISM_CODES` accepted (spec, refmap organism is an organism code)
- [x] 1.2 `RefmapResult` gains `organism`, before `mappings`; `run_refmap` calls the engine's `map_ids` in the worker and maps its result field for field (decision 1). `run_job`'s refmap case calls it; `UNAVAILABLE` loses its row, keeping the mechanism. Verify in `tests/test_jobs.py`: a valid request gets 202 and a job, no 501 is left in the schema, and the engine's `ValueError` or `MissingDataError` fails the job with the generic 500
- [ ] 1.3 A test fixture writes a made-up data folder: `refmap/19/panther_classification/ENDPU` from `engine/tests/golden/refmap/out/test_geneList.out`, in a temporary `PANTHER_DATA_DIR` (decision 8). Verify with job tests against it: the example's six IDs map to the golden's values; `U1G4Q5`, `P04217`, `U1G4Q5` give three mappings in order; a `refmap` and a `csnp` job don't mix (spec, refmap job maps with the engine)
- [ ] 1.4 Startup: one check per service, `csnp` and `refmap`, each logging its own error (decision 6). Verify in the startup tests: cSNP data without refmap data logs only the refmap error, and health is 200 (spec, Startup check of the refmap data)
- [x] 1.5 `GET /api/v1/refmap/organisms` in a new `routers/refmap.py`: code, name and gene counts from the engine, in its order, cached for an hour (decision 3). Verify in a new `tests/test_refmap_organisms.py`: 1,533 entries, ENDPU's name and counts, the header, no data needed, and the schema's entry (spec, refmap organism list)

## 2. API: large lists and large results

- [ ] 2.1 Spike, recorded in Notes: how one list validator on `ids` raises the first 100 errors at their item `loc`s and passes the total to the problem handler (decision 5). Measure 100,000 empty IDs against 100,000 valid IDs for an unknown organism, before and after
- [ ] 2.2 Replace the per-item `ids` validator with the list validator, keeping each item's `pattern`, `minLength` and `maxLength` in the schema. Verify: the existing `ids` 422 tests pass unchanged; `api/openapi.json` is unchanged for `ids`; the timing test of 100,000 empty IDs is within twice the valid list's (spec, Validation errors list the failing fields)
- [ ] 2.3 Keep a finished refmap result as JSON bytes built in the worker, and drop a finished job's request IDs, keeping its log summary (decision 4). `get_job` returns the stored bytes inside the job's JSON. Verify in `tests/test_jobs.py` and `tests/test_job_store.py`: a polled 100,000-ID job validates against `JOB_ADAPTER` and equals the engine's mappings in order; `csnp` and `tools` jobs poll as before; the job's log line still has its organism and ID count (spec, refmap job shape)
- [ ] 2.4 The results budget: `PANTHER_API_RESULTS_BUDGET_MIB`, 256 by default, at least 1; each finished job's result counted by its JSON size; over the budget, the oldest finished jobs expire first, and a result larger than the budget is still kept (design.md, decision 4). Verify in `tests/test_job_store.py` and `tests/test_settings.py`: the scenarios Over the results budget and A result larger than the budget, the default, and 0 refused (spec, Jobs expire; Configuration from the environment). `docs/testing/api.md`'s settings table gains it
- [ ] 2.5 Regenerate `api/openapi.json` with `uv run python -m panther_api.openapi`: `organism` in the refmap result, the organism list, no 501. Verify `tests/test_openapi.py` passes

## 3. API: with the real data

- [ ] 3.1 `refmap` joins the API's `DATA_MANIFESTS` (`tests/markers.py`), and tests marked `data("refmap")` run the example job against the release, and a 100,000-ID job, recording its size in memory and its poll time in Notes. Verify they pass with the data (`uv run panther-engine refmap data fetch --data-dir ../.data`, from `engine/`) and skip without it
- [ ] 3.2 CI: the `api-image` job restores the refmap data from the cache the engine jobs fill, and mounts it, so the data tests run there. Verify in the pull request's CI logs that they run, not skip
- [ ] 3.3 API checks: `uv run ruff check`, `ruff format --check`, `basedpyright` and `pytest` pass natively, and the image's tests pass with both data sets

## 4. Frontend

- [ ] 4.1 Regenerate the types (`npm run api:types`); `wire.ts` gains the refmap result's `organism` and the organism list's entry. Verify `npm run api:types:check` and `type-check`
- [ ] 4.2 A shared `CodeListField` in `src/components/`, from `SpeciesField`'s three states, with its texts as props, `limit` for long lists and options sorted by name (decision 7). cSNP's form uses it for species. Verify the cSNP form's unit and e2e tests pass unchanged, and new tests of the field's three states
- [ ] 4.3 The refmap form: `getRefmapOrganisms` and `useRefmapOrganisms`, the organism selector with its fallback, the check against the list once loaded, and the ENDPU example. Verify in `tests/features/refmap/`: the selector's options, search by `pusill` and `eco57`, the code sent, the loading and failed states, the retry keeping `ENDPU`, `HUMAN` rejected once the list has loaded, and the example (spec, refmap form; refmap form checks the input before sending; refmap organism list unavailable)
- [ ] 4.4 Remove the 501 path: `useSubmitRefmap`'s `unavailable`, its alert and its tests; a 501 now gets "couldn't be started". Verify the submit failure tests (spec, refmap submit failures)
- [ ] 4.5 The job page says "Mapped against Endocarpon pusillum (ENDPU)", or the code without the list. Verify in `tests/features/jobs/` (spec, refmap results on the job page)
- [ ] 4.6 `services.ts`: refmap's `comingSoon` is `false`. Verify the header and home page tests: only HMM scoring and TreeGrafter are marked (spec, Services that aren't available yet; The home page shows every service)
- [ ] 4.7 Mocks: a short real organism list, and the example's IDs mapped to the golden's values (decision 7). Verify the mocked e2e refmap spec: choose the organism, use the example, submit, and read the six mappings and the organism on the job page
- [ ] 4.8 The `@api` refmap spec submits the example against a real API with the data and checks its six mappings, replacing the spec that expected the 501. Verify it passes with `npm run test:e2e` in api mode, against an API run with `docker run` on another port
- [ ] 4.9 Frontend checks: `format:check`, `lint`, `type-check`, `npm test -- --run` and `npm run test:e2e`, desktop and mobile

## 5. Docs

- [ ] 5.1 `docs/testing/api.md`: the refmap section shows a real job with `ENDPU`, the organism list, the `organism` error for `HUMAN`, and how to fetch the refmap data; the 501 goes. `docs/testing/frontend.md`: the refmap mocks and `@api` spec. Verify with `npx markdownlint-cli2`
- [ ] 5.2 `docs/manual-qa/03-refmap-form.md`: the selector, the ENDPU example, a real job's results and the organism on the job page, replacing the 501 step. `docs/deployment/runbook-server.md`: the refmap data under `PANTHER_DATA_DIR`, fetched with `panther-engine refmap data fetch`
- [ ] 5.3 `api/CLAUDE.md` and `frontend/CLAUDE.md`: a line each where a convention changed (the stored JSON result; the shared code field). Final check: from the root, `npx markdownlint-cli2`, `npx openspec validate --all` and `npx openspec validate wire-refmap --strict` pass

## Workflow follow-up

- **Review:** the engine developer reviews the use of `panther_engine.refmap` and the server's data step; #40 and #41 close with the merge.
- **On the server:** the engine developer fetches the refmap data before or with the deploy.
- **After the implementation merges,** archive with `/opsx:archive`.

## Notes

### Next action

The contract is in (1.1, 1.2, 1.5, 2026-11-06): the organism check, the result's `organism`, `run_refmap`, the organism list, no 501, and the regenerated `openapi.json` and `schema.d.ts`. The rest runs in parallel: the API (1.3, 1.4, 2, 3) and the frontend (4). The plan's review (#64) goes on alongside.

### Blockers

None. #63 is merged.

### Failed approaches

None yet.

### Lessons learned

- **The tests' autouse fixture fakes every job's work** with the tools report, so a test of a real refmap job must put `run_job` back (`monkeypatch.setattr("panther_api.jobs.runner.run_job", run_job)`). Polling a refmap job whose result is the fake tools report gets a 500 from the response's validation.
