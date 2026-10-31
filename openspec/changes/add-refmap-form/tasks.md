# Tasks

## 1. The Wire Module and Shared Helpers

- [x] 1.1 Add the `refmap` job and request to `src/app/api/wire.ts` (`WireJob`, `JobRequest`, `Job`, `fromWireJob`, and the `RefmapInput`, `RefmapResult` and `IdMapping` aliases), with no type written by hand. Move the helpers that read a failed request's status and body from `useSubmitCsnp.ts` to `src/app/api/errors.ts` (`errorStatus`, `errorData`), and import them in `useSubmitCsnp.ts`.
- [x] 1.2 Extend `tests/app/api/wire.test.ts`: `fromWireJob` keeps a `refmap` job's mappings, `null` and repeats included, unchanged; `inputErrors` puts a refmap `422`'s errors on `ids` (with the item) and `organism`, and anything else under `other`.

## 2. Mocked refmap Jobs

- [x] 2.1 Add `refmapResult(ids)` (commented as mock data: deterministic per ID, about a third with no PANTHER ID, the rest `PTHR00000:SF<n>`) and `refmapJob(id, status, ids)` to `src/mocks/data/jobs.ts`, keeping it to type and relative imports. Make `src/mocks/jobs.ts` remember a job's IDs (`createJob('refmap', ids)`), and the mocked `POST` accept `refmap` and pass on `input.ids`.
- [x] 2.2 Add `tests/mocks/jobs.test.ts`: a mocked `refmap` job succeeds with one mapping per submitted ID, in order; the example's IDs give a mix of made-up PANTHER IDs and none, the same each time.

## 3. The refmap Form's Logic

- [x] 3.1 Implement `src/features/refmap/ids.ts` (`splitIds`, `shownId`), `checks.ts`, `draft.ts`, `example.ts` and `idsFile.ts`, as design.md decisions 1 to 3, 8 and 9 describe.
- [x] 3.2 Add `tests/features/refmap/ids.test.ts` (line breaks, spaces and commas, the first column only and its count, IDs kept as typed, Unicode spaces, blank text, 100,000 lines staying fast; `shownId`), `checks.test.ts` (each rule with an accepted value beside each rejected one, exactly 100,000 and 100,001 IDs, naming by place, line and as typed, ten then a count, 100,000 IDs checked fast, no message quoting the organism), `draft.test.ts` (editing, the example, a refused file, `checked`, `rejected` naming an ID from the sent split, the request's input) and `idsFile.test.ts` (a file read, exactly 10 MB read, larger refused, unreadable refused).

## 4. The refmap Page and Submitting

- [x] 4.1 Implement `src/features/refmap/` (`RefmapPage.tsx`, `RefmapForm.tsx`, `IdsField.tsx`, `useSubmitRefmap.ts`, `SubmitAlert.tsx`, `index.ts`), add `/refmap` to `src/app/router.tsx`, and add the "Protein ID mapping" section and link to `HomePage`, as design.md decisions 2, 4, 7 and 8 describe.
- [x] 4.2 Add `tests/features/refmap/RefmapPage.test.tsx` from the spec scenarios: open from the home page; the example; the descriptions; the count and the lines with columns; loading a file (and submitting it), replacing the box, and refusing one over 10 MB; the client checks for each field, sending nothing; a valid input sent as split and trimmed, 100,000 IDs sent; disabled in flight; a `422` on `organism`, on ID 3 (named by place, line and as sent) and on no field, and editing clearing it; the `501`, a `500`, a network error and the dev proxy's empty `500`, each followed by a successful submit. Extend `tests/features/home/HomePage.test.tsx` with the new link.

## 5. refmap Results on the Job Page

- [x] 5.1 Implement `src/features/jobs/RefmapMappings.tsx`, `MappingsTable.tsx` and `mappingsFile.ts`, render them from `JobResult`, and title the job "Protein ID mapping" in `JobDetails`, as design.md decisions 5 and 6 describe.
- [x] 5.2 Add `tests/features/jobs/RefmapMappings.test.tsx` (the title, the summary, the rows in order with "No PANTHER ID", the versions, one ID, no mappings, no table while running; 100 rows a page and moving between pages; 100,000 mappings to the last page; the download's name, type and every line) and `tests/features/jobs/mappingsFile.test.ts` (the TSV's header, lines and empty `panther_id`, no mappings, 100,000 mappings quickly, the file name).

## 6. End to End

- [x] 6.1 Add `e2e/refmap.spec.ts`: untagged, the empty form's errors; `@mock`, the example from the home page to the mocked mappings, summary, versions and the downloaded file, and a file of 100,000 IDs loaded, mapped and paged to the last page; `@api`, the real `501` shown as not available yet with the input kept, the real `422` named on the IDs field through a `page.route` rewrite, and a direct `POST` whose `422` `loc`s name `organism` and `ids[1]` without echoing them. Add `/refmap` to `e2e/mock-data.spec.ts`'s no-banner check, and let `e2e/shell.spec.ts` accept more than one section heading on the home page.
- [x] 6.2 Run `npm run test:e2e` (mock mode, both projects), and `test:e2e:api` against #30's API image built from this worktree (`docker build --target api -t panther-api:refmap-form .`, run on port 8001), then stop the container.

## 7. Docs and Final Check

- [x] 7.1 Add `docs/manual-qa/03-refmap-form.md`, following its README (`TC n.m`, a checkbox per visible step, Pass / Fail and Notes). Update `docs/testing/frontend.md`: mocked `refmap` jobs, `refmapJob`, serving the `501`, slow 100-row pages under jsdom, and the refmap e2e specs.
- [x] 7.2 Final check: in `frontend/`, `npm run api:types:check`, `format:check`, `lint`, `type-check`, `npm test` and `npm run test:e2e` pass, and the api-mode run from 6.2; from the root, `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive` and `npx openspec validate add-refmap-form --strict --no-interactive` pass.

## Workflow follow-up

- **Review:** the frontend developer approves the code, the `scoring-ui` delta, and design.md's decisions on splitting (1), file loading (2), pagination (5) and the download format (6). The engine developer answers the proposal's questions on `HUMAN` as a refmap organism and on `\r` in PANTHER IDs; the API developer the one on the organism in the result.
- **Merge after PR #30** (`add-refmap-job`), on which this branch is based. If #30 changes before it merges, rerun `npm run api:types:check` and the api-mode e2e run.
- **When the API's `501` for `refmap` is removed** (the wiring change), the same pull request, or a frontend one right after it, removes the `unavailable` outcome from `useSubmitRefmap` and `SubmitAlert`, its Vitest test, and the `@api` `501` test, which becomes a test that submits the example and waits for a succeeded job.
- **When the engine exports its organism list,** the organism box becomes a searchable selector, as cSNP's species did (#24, #31), in its own change.
- **After the implementation merges,** archive with `/opsx:archive`, after `add-refmap-job`.

## Notes

### Next action

Every task is done (2026-10-30) and committed locally on the agent's branch, from `origin/feat/refmap-job` at `efd4fe3`. Next: the coordinator reviews the commit and opens the pull request; the engine, API and frontend developers answer the proposal's Open Questions.

### Blockers

None for this change. PR #30 must merge first.

### Failed approaches

- **Editing two files with one inline Python script from the shell (1.1, 2026-10-30)** was refused by the agent's worktree guard as too complex to check. The same edits were made with the file tools.
- **Reading each row's cells by role in the results tests (5.2, 2026-10-30).** With a page of 100 rows, `within(row).getAllByRole('cell')` for every row took about 4 s a test under jsdom, and the pagination test timed out at 5 s when the whole suite ran in parallel. The rows are still found by role; their cells are read with `row.cells`, and the large-result tests allow 20 s.
- **Finding the job page by its heading right after submitting (4.2, 2026-10-30).** The form page's heading reads the same, "Protein ID mapping", so `findByRole('heading')` matched the form's, which then left the page. The test waits for the job's status first.

### Lessons learned

- **A second section on the home page broke `e2e/shell.spec.ts`,** which expected exactly one `h2` in `<main>` (strict mode). It now takes the first, as `mock-data.spec.ts` already did.
- **Prettier writes `�` in a test's regex as the literal character.** Harmless, but searching the test for the escape finds nothing.
- **The csnp `@api` spec that scores P26439 needs the cSNP data sample** even though this change doesn't touch cSNP. Against the container with no data mount, as briefed, `test:e2e:api` had 34 passed and that spec failed on both projects. With the main checkout's `.data/` mounted read-only (`-v .data:/data:ro -e PANTHER_DATA_DIR=/data`, as `compose.yaml` mounts it), all 36 passed.
- **Counts (7.2, 2026-10-30):** `npm test`, 291 tests in 23 files; `test:e2e`, 28 passed; `test:e2e:api`, 36 passed against `panther-api:refmap-form` on port 8001 with the data sample. The `refmap` `501` and both `422`s came from the real API. Screenshots of the mock build at desktop and Pixel 7 width (home, form errors, 250 mappings) showed no sideways scroll, and the pagination controls fit a phone.
- **The manual QA checklist (7.1)** was checked by the e2e tests and the screenshots, not walked step by step in a browser.
