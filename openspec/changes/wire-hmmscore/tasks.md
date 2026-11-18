# Tasks

Start once #81 (`port-hmmscore`) and #82 (`add-hmmscore-form`'s archive) have merged, from `main` with both.

## 1. API: hmmscore jobs run

- [ ] 1.1 `work.py`: `JobOptions` (`hmmscore_cpu`, `hmmscore_time_limit_seconds`); `run_job(request, options)`. `JobRunner` takes `options` and submits them with every job; `main.py`'s lifespan builds them from the settings (design.md, decision 2). `tests/job_helpers.py`'s stand-ins take the second argument. Verify every existing job, runner and store test passes unchanged in what it checks
- [ ] 1.2 `jobs/hmmscore.py`: `run_hmmscore(request, *, cpu, timeout)` imports `panther_engine.hmmscore` lazily, calls `score()` with the sequence, `cpu` and `timeout`, and builds `HmmscoreResult` and `HmmHit` field for field (decision 1). `run_job`'s hmmscore case calls it with the options. `UNAVAILABLE` loses its row, keeping the mechanism; the module docstrings and `HmmscoreJobRequest`'s drop the `501`. Verify in `tests/test_jobs.py`, with the engine's `score` replaced in-process: the options reach it; a hit and a `null` hit map field for field; a valid request gets `202` and a job; `run_job`'s refusing test goes (spec, hmmscore job scores with the engine; hmmscore job time limit and threads)
- [ ] 1.3 How a job fails, through stand-ins in `job_helpers.py`: the engine's `InputError` with the time limit's message fails the job with `422` and that `detail`; `HmmscoreError` with a path in its message, and `ValueError`, fail it with the generic `500`, and the job holds neither. Verify in `tests/test_jobs.py`, each beside a success, and in `tests/test_job_logs.py` that the time limit's line is the fixed input-error outcome (spec, hmmscore job time limit and threads; A failing job reveals nothing internal)
- [ ] 1.4 The `501` tests go: the `assert_unavailable` cases become `202` cases where they test the residue limit and the characters; the residue limit's `422`s stay as they are. `tests/test_openapi.py`: no `501` on `POST /api/v1/jobs`, without reloading the router (decision 1). Verify both files pass
- [ ] 1.5 Startup: `main.DATA_CHECKS` gains hmmscore (decision 4). Verify in the startup tests: the cSNP and refmap data without the hmmscore data logs only the hmmscore error, and health is 200; with the hmmscore sample's parts, no hmmscore error (spec, Startup check of the hmmscore data)
- [ ] 1.6 Versions: `read_versions()` lists hmmscore's `DATA_VERSION` after refmap's (decision 5). Verify in `tests/test_versions.py` and `tests/test_jobs.py`: the report lists all three in order; an `hmmscore` job's `versions.data` is hmmscore's alone (spec, Versions report; Job shape)
- [ ] 1.7 `settings.py`: the time limit's and `--cpu`'s descriptions and docstrings drop "takes effect once hmmscore is wired in". Verify `tests/test_settings.py`
- [ ] 1.8 Regenerate `api/openapi.json` with `uv run python -m panther_api.openapi`: the `501` goes, nothing else changes. Verify `tests/test_openapi.py` passes, and `git diff --ignore-cr-at-eol api/openapi.json` shows only the `501` and the descriptions

## 2. API: with the tools and the data sample

- [ ] 2.1 `hmmscore` joins `tests/markers.py`'s `DATA_MANIFESTS`, with `panther_engine.hmmscore.sample.MANIFEST`. A new `tests/test_hmmscore_scoring.py`, marked `tools("hmmscan", "hmmsearch")` and `data("hmmscore")`, runs real jobs through the API for `apoe`, `no-hit` and `tie-pthr35774`, reading the inputs and the expected hits from `engine/tests/golden/hmmscore/parity/` read-only; and calls `run_hmmscore` in-process with a timeout of a millisecond for the `422` (decision 7). Verify they pass in the API image with the sample (`docs/testing/api.md`, "Tests With the Tools and Data"), and skip natively on Windows (spec, hmmscore job scores with the engine: The form's example, No hit, Tied best hits)
- [ ] 2.2 CI's `api-image` job, both architectures: restore `.data/hmmscore` from the cache the engine jobs fill, `panther-engine hmmscore sample fetch` with the image's CLI, run `tests/test_hmmscore_scoring.py` with `PANTHER_REQUIRE_TOOLS=1` and `PANTHER_REQUIRE_DATA=1`, and score APOE through the running API with `curl`, checking `PTHR18976:SF2`, "APOLIPOPROTEIN E" and `versions.data`. The "Start the API" step already mounts `.data/`. Verify in the pull request's CI logs that the tests run, not skip, on both legs
- [ ] 2.3 API checks: `uv run ruff check`, `ruff format --check`, `basedpyright` and `pytest` pass natively, and the image's tests pass with the cSNP, refmap and hmmscore data

## 3. Frontend

- [ ] 3.1 Regenerate the types (`npm run api:types`): the `501` goes from `schema.d.ts`. Verify `npm run api:types:check` and `type-check`
- [ ] 3.2 `services.ts`: HMM scoring's `comingSoon` is `false`, and its comment goes. `HmmscorePage.tsx` loses `NotAvailableNotice`. Verify in `tests/layout/AppHeader.test.tsx`, `tests/features/home/HomePage.test.tsx` and `tests/features/hmmscore/HmmscorePage.test.tsx`: only TreeGrafter is marked; `/hmmscore` has no badge and no notice (spec, Services that aren't available yet; The home page shows every service)
- [ ] 3.3 The `501` path goes: `submitProblem`'s `unavailable`, `SubmitAlert`'s text for it, and their tests (decision 6). Verify in `tests/components/submitProblem.test.ts` and `HmmscorePage.test.tsx`: a `501` with problem details is "couldn't be started", one without is "can't be reached", each with the sequence kept, beside a `202` that opens the job; cSNP's and refmap's submit failure tests pass unchanged (spec, hmmscore submit failures)
- [ ] 3.4 Mocks: `versions.ts` lists hmmscore's PANTHER 19; the comments that say the real API answers `501` go (`handlers.ts`, `jobs.ts`). Verify in `tests/features/jobs/HmmscoreHit.test.tsx` or `JobPage.test.tsx` that a mocked `hmmscore` job's page shows PANTHER 19 (spec, hmmscore results on the job page)
- [ ] 3.5 e2e: the untagged spec in `e2e/hmmscore.spec.ts` drops the notice and keeps the empty form's check; `e2e/shell.spec.ts` checks only TreeGrafter is marked. The `@api` spec that expected the `501` becomes one that scores the example against a real API with the hmmscore data sample, and checks the hit's PANTHER ID `PTHR18976:SF2` and its name, not its E-value, waiting up to 60 s (decision 7). The `@api` `422` spec stays. Verify with `npm run test:e2e` in mock mode, and in api mode against an API run with `docker run` on another port, such as 8001, with `.data/` mounted
- [ ] 3.6 Frontend checks: `format:check`, `lint`, `type-check`, `npm test -- --run` and `npm run test:e2e`, desktop and mobile

## 4. Docs

- [ ] 4.1 `docs/testing/api.md`: the hmmscore section shows a real job with the example on the data sample, how to fetch the sample, and the time limit's `422`; the `501` goes; the settings table and its note drop "takes effect when hmmscore's scoring is wired in"; the links to `add-hmmscore-job` point to its archive. `api/README.md`: hmmscore runs. `compose.yaml`: the `api` service's comment names the hmmscore sample (design.md, decision 8)
- [ ] 4.2 `docs/testing/frontend.md`: the hmmscore mocks and specs without the `501`, and the `@api` spec's real hit. `docs/manual-qa/04-hmmscore-form.md`: no notice or mark; the real API scores the example, and the job page shows `PTHR18976:SF2`, its alignment and PANTHER 19, replacing the "not available yet" step
- [ ] 4.3 `docs/deployment/runbook-server.md`: the full library under `hmmscore/19/`, downloaded on the host and passed to `panther-engine hmmscore data fetch --tarball`; the four settings, with the engine developer setting the server's values (#68). Checked against `engine/src/panther_engine/hmmscore/cli.py`'s options, and with no memory figure for the server
- [ ] 4.4 `api/CLAUDE.md`: "Adding a Service" says hmmscore has been through all four steps, and how the settings reach the worker (`JobOptions`). `frontend/CLAUDE.md` if a convention changed. Final check, from the root: `npx markdownlint-cli2`, `npx openspec validate --all` and `npx openspec validate wire-hmmscore --strict`

## Workflow follow-up

- **Review:** the API developer and the frontend developer approve; the engine developer reviews the use of `panther_engine.hmmscore` and the server's data step.
- **On the server:** the engine developer fetches the full library and sets the four hmmscore settings before or with the deploy (#68).
- **After the implementation merges,** archive with `/opsx:archive`.

## Notes

### Next action

Review the proposal in its pull request. Once #81 and #82 have merged and the proposal is approved, rebase on `main` and start at 1.1.

### Blockers

- **#81 (`port-hmmscore`) isn't merged.** The engine's `score()`, `check_data()`, `DATA_VERSION` and `HmmscoreError` are on its branch only, so nothing here can import them yet.
- **#82 (`add-hmmscore-form`'s archive) isn't merged.** The `scoring-ui` requirements this change modifies and removes are in `openspec/specs/` only once it is; until then, archiving this change would fail.

### Failed approaches

None yet.

### Lessons learned

- **The engine's interface fits the plan, with one addition.** `score()` is `add-hmmscore-job`'s decision 4 as proposed. Beside `InputError`, `HmmscoreError` and `ValueError`, it can raise `LibraryFormatError` for a broken `names.tab`, `MissingDataError`, and `DataFolderError` when `PANTHER_DATA_DIR` isn't set; all three are the generic `500` (proposal draft, 2026-11-17).
- **`run_job` takes only the request,** and a `spawn` worker has no settings, so the time limit and `--cpu` need a way in: `JobOptions` (design.md, decision 2).
