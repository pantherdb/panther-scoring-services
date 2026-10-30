# Tasks

## 1. API: Score cSNP Jobs With the Engine

- [x] 1.1 In `api/src/panther_api/jobs/csnp.py`, add `run_csnp()`, the adapter of design.md decision 1, and call it from `run_job`'s `csnp` case in `jobs/work.py`. Keep `work.py` free of import-time state. Verify with tests in `api/tests/test_jobs.py`: the adapter with a fake `score()` (the engine input it builds, the result it returns, a `null` family, the engine's errors passed on); `run_job` runs the `csnp` case; and a `csnp` job succeeds with the fake engine's scores through a real `spawn` worker (`score_with_a_fake_engine` in `tests/job_helpers.py`).
- [x] 1.2 Remove the `501`: the check in `routers/jobs.py`, `CSNP_UNAVAILABLE`, and the `501` entry in the create route's OpenAPI responses. Update the docstrings that mention it. Verify that `tests/test_openapi.py` checks no `501` is documented, and the `501` tests are gone.
- [x] 1.3 Add the species membership check of design.md decision 3. Verify with `tests/test_csnp_input.py` (every one of `SPECIES_CODES` is accepted; `ZZZZZ`, `XENLA`, `SALSA` and `9PRIM` are rejected with one error that doesn't repeat them) and `tests/test_jobs.py` (`XYZZY` gets a `422` at `["body", "csnp", "input", "species"]`, without the value, and no job).
- [x] 1.4 Add `DataVersion` and `Versions.data` (design.md decision 4), read from `panther_engine.csnp.DATA_VERSION` (task 1.7). Verify with `tests/test_versions.py` (the body's `data`, the value `"9"`, and that it needs no `PANTHER_DATA_DIR`) and `tests/test_openapi.py` (the schema's `DataVersion`).
- [x] 1.5 Add the `tools` and `data` markers to `api/pyproject.toml` and `tests/markers.py`, and `tests/test_csnp_scoring.py` (design.md decision 6). Verify that natively they're reported as skipped, and that in the API image, with the data sample and `PANTHER_REQUIRE_TOOLS=1` and `PANTHER_REQUIRE_DATA=1`, the whole suite passes with none skipped.
- [x] 1.6 Regenerate `api/openapi.json` with `uv run python -m panther_api.openapi`. Verify in `api/`: `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run basedpyright` and `uv run pytest` pass.
- [x] 1.7 At the engine developer's request on #26, export `DATA_VERSION` from `panther_engine.csnp`: `from panther_engine.csnp.scoring import VERSION as DATA_VERSION`, listed in `__all__`. Make `versions.py` and `tests/test_versions.py` import it from there. Verify that `tests/test_versions.py` passes (the value `"9"`, with no `PANTHER_DATA_DIR`), and that `uv run ruff check`, `ruff format --check` and `basedpyright` pass in `engine/` and `api/`.

## 2. API: Input Errors in Failed Jobs

`add-job-input-errors` groups 2 and 3, done here; tick them there too.

- [x] 2.1 In `jobs/runner.py`, catch `InputError` between `BrokenProcessPool` and `Exception`, and fail the job with `Problem(status=422, title="Unprocessable Content", detail=str(exc))`, logged at `INFO` without a traceback. Verify with tests in `tests/test_jobs.py`, through real workers, with `raise_input_error` and `input_error_for_csnp` in `tests/job_helpers.py`: "Unprocessable input" (the exact problem, no traceback, the `INFO` record without `exc_info`), "Other jobs keep running", and that any other error is still the generic `500`. The real `csnp` case, `1234567890`, is in `tests/test_csnp_scoring.py`.

## 3. Root: compose and CI

- [x] 3.1 In `compose.yaml`, give the `api` service `./.data:/data:ro` and `PANTHER_DATA_DIR=/data`. Verify by running the image the same way (`docker run -p 8001:8000 -v <data>:/data:ro -e PANTHER_DATA_DIR=/data`): a `csnp` job for P26439 succeeds.
- [x] 3.2 In `.github/workflows/ci.yml`, make `api-image` fetch the cSNP sample with the engine jobs' cache key and fetch step, start the image with it mounted, and check a real `csnp` job's family, scores and data version with `jq`. Verify the job's script against the local image in a container with `curl` and `jq`, since the developer's machine has no `jq`.

## 4. Frontend

- [x] 4.1 Run `npm run api:types`. Remove the `'unavailable'` `SubmitProblem`, its alert, `csnpUnavailable` and the `501` tests; a `501` is now any failure to start, and a test says so. Verify `npm run api:types:check`, `format:check`, `lint`, `type-check` and `npm test -- --run` pass.
- [x] 4.2 Show `versions.data` in `VersionList`, after the tools, as "`<service> data`" and "`PANTHER <panther>`"; add `data` to the mocked versions. Verify with tests: the footer shows the data the API reports, not a fixed release; a `csnp` job's page shows the job's own data version.
- [x] 4.3 Replace the api-mode e2e `501` test with one that submits P26439 with `A10E G15D S213G`, waits for the job to succeed, and checks the spec §7.3 rows and the data version. Add the data versions to the e2e version checks. Verify `npm run test:e2e` (mock mode) and `API_PROXY_TARGET=http://localhost:8001 npm run test:e2e:api` against the API image with the data sample.

## 5. Docs

- [x] 5.1 Update `docs/testing/api.md`: the data sample, a `csnp` job by hand, a failed job's `422` and `500`, request validation including the species, and the tests with the tools and data. Also `docs/testing/README.md` (the API tests and `api-image`), `api/README.md`, `docs/testing/frontend.md` (api mode needs the sample; the `@api` specs), `frontend/README.md`, and `docs/manual-qa/02-csnp-form.md` (TC 2.4 scores for real, with what APOE gives against the sample; TC 2.5's species). Verify `npx markdownlint-cli2` passes, and that nothing outside `engine/` and `openspec/changes/archive/` still says cSNP scoring isn't available.

## 6. Final Check

- [x] 6.1 From the files git would commit:
  - in `api/`: `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright` and `pytest` pass;
  - in `frontend/`: `api:types:check`, `format:check`, `lint`, `type-check`, `npm test -- --run`, `npm run test:e2e`, and api-mode e2e against the image with the data sample pass;
  - from the root: `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive` and `docker build --target api .` pass, and the engine image's checks pass as `docker compose run --rm engine` runs them.

## Workflow follow-up

- Open a pull request with the change and its implementation. All three developers approve: it changes `compose.yaml` and `ci.yml`, the schema (frontend and API developers) and how the API reads the engine (API and engine developers).
- On the pull request, confirm in `api-image`'s log, on both architectures, that the sample is fetched or restored, and that the `csnp` job's `jq` check prints `true`.
- The engine developer answers the open questions on the data version and the APOE example.
- After merge, archive `add-job-input-errors` first, then this change, with `/opsx:archive`.

## Notes

### Next action

Every task is done. The pull request is #26. The engine developer answered both open questions there (2026-10-30), and asked for the `DATA_VERSION` export in this change (task 1.7). Next: the engine developer's review of that export, and the three approvals.

### Blockers

None.

### Failed approaches

- **Editing Python with a script's `Path.write_text` (2026-10-30).** On Windows it writes CRLF line endings. Use the Edit tool, or write with `newline=""`.
- **Shell heredocs for TypeScript with `\n` in a string (2026-10-30).** Git Bash's heredoc turned `'\n'` into a real line break and broke a test file. Use the Edit tool for anything with a backslash.

### Lessons learned

- **The data sample has the whole BLAST database but 15 families.** A protein of another family gets its family, and every substitution "Not scored: No PANTHER family for input sequence". The form's APOE example is one (`PTHR18976`), so development and CI use the release sample's proteins.
- **`blastp` without its database exits with status 2,** a `BlastError`, so the API without data fails `csnp` jobs with the generic `500`, not an input error. Status 1 is the only input error.
- **The runner's `INFO` log doesn't reach `docker logs`.** Uvicorn configures only its own loggers; `logger.exception` still shows, through Python's last-resort handler.
- **API tests can run in the API image** with `api/` and `engine/` mounted read-only and `UV_PROJECT_ENVIRONMENT=/tmp/venv`: `uv sync --locked` installs the dev tools in the container, and nothing is written to the mounts.
