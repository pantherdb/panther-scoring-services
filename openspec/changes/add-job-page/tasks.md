# Tasks

Test-first: each group writes its tests from the spec scenarios, runs them and sees them fail for the right reason, records the red run in the Notes, then implements.

## 1. The Wire Module

- [x] 1.1 Write `tests/app/api/wire.test.ts`: `fromWireJob` renames every field, turns the ISO timestamps into epoch milliseconds, keeps `null` timestamps `null`, and passes `result`, `error` and `versions` through unchanged. Run it and verify it fails because `@/app/api/wire` doesn't exist yet, and nothing else. Record the red run in the Notes.
- [x] 1.2 Implement `src/app/api/wire.ts` as design.md describes, with its types as aliases of `schema.d.ts`. Verify the test from 1.1 passes, `npm run type-check` and `npm run lint` pass, and no API type is written by hand.

## 2. Mocked Jobs

- [x] 2.1 Add `src/mocks/data/jobs.ts` (the job bodies, only type and relative imports), `src/mocks/jobs.ts` (the per-job store with `createJob`, `pollJob` and `resetJobs`), the `POST /api/v1/jobs` and `GET /api/v1/jobs/:id` handlers in `src/mocks/handlers.ts`, and a `resetJobs()` call after each test in `tests/setup.ts`. Verify `npm test`, `npm run type-check` and `npm run lint` pass, with no UI changed yet.

## 3. The Job Page

- [x] 3.1 Move `VersionList` from `src/features/versions/` to `src/components/`, typed with the schema's `Versions`, and import it from there in `AppVersions`. Verify `npm test` passes unchanged, and `grep` finds no import of `features/versions/` outside that folder except through its `index.ts`.
- [x] 3.2 Write `tests/features/jobs/JobPage.test.tsx` from the spec scenarios: loading first, then the job (Open a job's page); `queued` → `running` → `succeeded` without a reload (A job moves forward); no further requests once `succeeded` or `failed` (Checking stops when the job finishes); the tools result in order and the job's versions (A tools job succeeded); a `null` tool version (A tool is missing from the result); a failed job's `detail` and no result (A job failed); 404 with a link home and no further requests (Unknown or malformed id, No further checks); 500 with no status, result or build details, then "Try again" (The request fails, Try again). Run it and verify every test fails because `/jobs/:id` shows the not-found page, not because of an import, type or setup error. Record the red run in the Notes.
- [x] 3.3 Write the untagged e2e test in `e2e/jobs.spec.ts`: opening `/jobs/not-a-job` says the job wasn't found, links home, and shows no build details. Run `npm run test:e2e` and verify it fails on both projects because the generic not-found page is shown instead. Record the red run in the Notes.
- [x] 3.4 Implement design.md's endpoints, polling, page states and route: `src/features/jobs/` (`jobsApi.ts`, `useJob.ts`, `JobPage.tsx`, `JobDetails.tsx`, `JobStatus.tsx`, `JobResult.tsx`, `ToolsResult.tsx`, `index.ts`) and `jobs/:id` in `src/app/router.tsx`. Verify the tests from 3.2 and every other Vitest test pass with no warnings, the e2e test from 3.3 passes on both projects, and `npm run format:check`, `npm run lint` and `npm run type-check` pass.

## 4. The Home Page Action and the Title

- [x] 4.1 Write `tests/features/jobs/StartToolsCheck.test.tsx` from the spec scenarios: choosing the action starts a `tools` job and shows `/jobs/{id}` (Start a tools check); the action is disabled while the request is in flight (While starting); a failed start shows an alert with no build details, stays at `/`, and the action can be chosen again (Starting fails). Change `tests/layout/AppLayout.test.tsx` to expect "PANTHER Scoring". Run them and verify each fails because there's no action or the title is the old one. Record the red run in the Notes.
- [x] 4.2 Add to `e2e/jobs.spec.ts`: a `@mock` test that starts the check from `/`, sees `queued`, `running` and `succeeded` in turn, then the mocked tools and the job's versions, with no sideways scroll on the job page; and an `@api` test that starts a check, waits for `succeeded`, checks the tools against `GET /api/v1/versions`, and reloads to see the same result. Run `npm run test:e2e` and verify the `@mock` test fails on both projects because there's no action on the home page. Record the red run in the Notes.
- [x] 4.3 Implement `StartToolsCheck` in `src/features/jobs/`, export it from `index.ts`, render it on `HomePage`, and change the title in `src/layout/AppLayout.tsx` and `index.html`. Verify every Vitest test passes with no warnings, `npm run test:e2e` passes on both projects, and `npm run format:check`, `npm run lint`, `npm run type-check` and `npm run build` pass.
- [x] 4.4 Verify api mode against the real API, from the repo root: `docker compose up --build -d api`, then `npm run test:e2e:api` in `frontend/` passes on both projects, including the `@api` job test; then `docker compose down`.

## 5. Docs and Final Check

- [x] 5.1 Add a manual QA checklist in `docs/manual-qa/`, following its README (`NN-<area>.md`, test cases `TC n.m`, a checkbox per visible step, Pass / Fail and Notes): start the API with compose, run the frontend against it, start the tools check, watch the statuses, read the result and versions, reload, then open a bad job id. Verify every step by following it in a browser against the compose API, or, where that isn't possible, say in the Notes which steps were checked only by the e2e tests.
- [x] 5.2 Update `docs/testing/frontend.md` where running the tests changed (the mocked jobs and their reset; overriding a job's state with `server.use`). Verify every command it names runs as written from `frontend/`.
- [x] 5.3 Final check:
  - in `frontend/`: `npm run api:types:check`, `npm run format:check`, `npm run lint`, `npm run type-check`, `npm test`, `npm run build` and `npm run test:e2e` pass;
  - the api-mode run from 4.4 passes;
  - from the root: `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass.

## Workflow follow-up

- **Review:** the frontend developer approves the code, the `scoring-ui` delta and the placeholder action. The API developer reviews how the contract is consumed (the job's id rather than `Location`, polling every second) and the proposal's open questions on polling and failures.
- **The engine developer** follows the manual QA checklist against the compose API.
- **After the implementation merges,** archive with `/opsx:archive`, after `add-api-types`, whose `scoring-ui` delta sits beside this one.

## Notes

### Next action

Every task is done (2026-10-29), and the change is committed on its own branch. Next: open the pull request for review (Workflow follow-up), and settle the proposal's open questions there.

### Blockers

None.

### Failed approaches

- **One compound shell command per mutation check (2026-10-29).** A command that backed up `useJob.ts`, edited it, ran Vitest and showed the diff was refused by the worktree's command guard as too complex to verify. Split into plain commands, with the edit reverted by a second `sed`.
- **Stopping a background server by its task (2026-10-29).** Stopping the background `npm run preview` or `npm run dev:api` task left its `node` child listening on 4173 or 5173, so the next e2e run would fail on a taken port. Find it with `Get-NetTCPConnection -LocalPort <port>` and stop that process.

### Lessons learned

- **The wire red run (1.1, 2026-10-29).** `tests/app/api/wire.test.ts` failed only with "Failed to resolve import "@/app/api/wire"": the module didn't exist. Green after 1.2 (4 tests). `Date.parse` takes the API's microsecond timestamps (`00:32:00.020522Z`) and keeps the milliseconds, in Node and the browser.
- **The mock texts match the API's (2.1).** The 404 and failed-job `detail`s in `src/mocks/data/jobs.ts` are copied from `api/src/panther_api/routers/jobs.py` and `jobs/runner.py`, so mock mode reads like the real API.
- **The job page red run (3.2).** All 11 tests in `tests/features/jobs/JobPage.test.tsx` failed because `/jobs/:id` showed the generic not-found page: "Unable to find role="status"", "Unable to find role="alert"", "Unable to find role="heading" and name `/job not found/i`", or no "Loading the job" text. The file type-checked and linted first.
- **The e2e red run (3.3).** In mock mode, the untagged bad-id test failed on desktop and mobile: the heading "Job not found" resolved to no element, because the generic "Page not found" was shown.
- **Green (3.4).** `npm test`: 28 tests in 6 files, with no warnings. `npm run test:e2e`: 12 passed. With real timers, the four tests that wait for polls take about 1.5 to 2 s each; fake timers weren't needed.
- **The polling tests can fail (3.4).** With `pollingInterval` forced to 1 s whatever the job's state, the two "stops checking" tests and the not-found test failed (3 of 11), so they guard the stop rule.
- **RTK Query's flags after an error.** While a refetch after an error is in flight, the entry is `pending`: `isError` is false, and `isLoading` is false too, because the last result was an error. The page picks "loading" by the absence of data, not by `isLoading`.
- **The home action red run (4.1).** In `tests/features/jobs/StartToolsCheck.test.tsx`, all four tests failed with "Unable to find an accessible element with the role "button" and name `/check the scoring tools/i`". The updated `AppLayout` title test failed on "PANTHER cSNP Scoring". The other `AppLayout` test passed, as it should.
- **The e2e flow red run (4.2).** In mock mode, the `@mock` flow test failed on desktop and mobile after 30 s, waiting for the "Check the scoring tools" button. The other 12 runs passed. The spec imports `src/mocks/data/jobs.ts`, which imports `./versions` relatively, so Playwright resolves it without the `@/` alias.
- **Green (4.3).** `npm test`: 32 tests in 7 files, no warnings. `npm run test:e2e`: 14 passed. `npm run build` passes. With the button's `loading` and `disabled` forced to `false`, "is disabled while the job is being started" fails, so it guards the rule.
- **api mode (4.4).** After `docker compose up --build -d api`, `POST /api/v1/jobs` answered 202 with `location: /api/v1/jobs/{id}` and a `queued` job, and `GET /api/v1/jobs/not-a-job` answered 404. `npm run test:e2e:api`: 14 passed, including the `@api` job test (about 2.5 s per project) and its reload. Screenshots of the production build against that API, on desktop and mobile, showed the home section, `Running`, then `Succeeded` with "Ran for 0.3 s", the four tools and the versions. Then `docker compose down`.
- **The manual QA checklist (5.1).** `docs/manual-qa/01-tools-check.md`. Checked in a real browser (Chromium driven by Playwright): TC 1.1, TC 1.2 and the reload in TC 1.3 against the compose API, through `npm run preview`, which has the same `/api` proxy as `npm run dev:api`; TC 1.4 by the e2e tests in mock and api modes; TC 1.5's two failure messages with `npm run dev:api` and no API running. Not checked by hand: the last two steps of TC 1.5 (restart the API, then "Try again" shows "Job not found"), which follow from the API keeping jobs in memory (`scoring-jobs`, "Jobs expire").
- **The testing doc (5.2).** `docs/testing/frontend.md` now says how the mocked jobs move, how to override them, that the job page polls with real timers, and that a reload in mock mode forgets the job. Its two example Vitest commands still run as written.
- **Final check (5.3).** In `frontend/`: `api:types:check`, `format:check`, `lint`, `type-check`, `npm test` (32 tests in 7 files), `build` and `test:e2e` (14) pass; the production build contains no mock code. The api-mode run from 4.4 (14 passed) was against the final source: only docs changed after it. From the root: `npx markdownlint-cli2` (56 files, 0 issues) and `npx openspec validate --all --no-interactive` (8 items) pass.
