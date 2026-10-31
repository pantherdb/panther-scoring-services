# api/

The FastAPI app, `panther_api`, for the four scoring services. [README.md](README.md) is the overview: what it serves, and its layout. [docs/testing/api.md](../docs/testing/api.md) has every command and how the tests are set up. This file holds the rules and the traps; the project-wide rules in [../CLAUDE.md](../CLAUDE.md) still apply.

## Before Claiming Anything Works

From `api/`:

```bash
uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest
uv run python -m panther_api.openapi    # after any change to a route, a model or an error
```

If the schema changed, also run `npm run api:types` in `frontend/` and commit `src/app/api/schema.d.ts`. CI's `frontend` job fails when it doesn't match `api/openapi.json`.

## The Contract

- **The OpenAPI schema is the contract** with the frontend and the PANTHER website. Commit `openapi.json` in the same pull request as the change that alters it; `tests/test_openapi.py` fails when they differ.
  - On Windows, the export writes CRLF line endings. If `git diff --ignore-cr-at-eol` shows nothing, restore the file with `git checkout`.
  - The schema should carry the rules the API enforces, such as a `pattern`, so clients learn them before a `422`. Put a rule a custom validator enforces into the schema with `Field(json_schema_extra=...)`.
- **The behaviour is specified in `openspec/specs/`:**
  - `api-service`: what every endpoint shares;
  - `scoring-jobs`: jobs;
  - `scoring-input`: each service's input rules.

  A change in behaviour starts as an OpenSpec change, and its tests follow the spec's scenarios.
- **Every error is RFC 9457 problem details** (`problems.py`). The details:
  - A `422` lists each failing field by its `loc`, with a message written for a person; `problems.py` drops Pydantic's "Value error, " prefix.
  - **Never echo a submitted value in an error.** Some Pydantic messages quote the input; `problems.py` rewrites the ones found so far. Test every new request model with a distinctive invalid value, and assert it isn't in the body.
- **Everything is a job.** `POST /api/v1/jobs` starts one, and `GET /api/v1/jobs/{id}` polls it. Don't add a synchronous scoring endpoint without a team decision; whether `refmap` gets one is an open question (#30).

## Jobs

- **The work runs in `spawn` worker processes** (`jobs/runner.py`):
  - A worker imports `jobs/work.py` afresh, and gets everything from `run_job`'s argument.
  - Keep that module, and everything it imports, free of import-time state, and keep its imports light: no FastAPI.
- **Only the event loop touches a job.** The handlers are `async def` and never run work themselves.
- **Validate and normalise in the request model,** before a job starts. Follow the legacy website's clean-up, as `scoring-input` records it, so the engine gets what the legacy scripts got.
- **Check a code against the engine's list, not only its shape,** before a request can reach the engine. cSNP's `species` is checked against `panther_engine.csnp.SPECIES_CODES`. This is how the API avoids the legacy command injection (`CGI-5`).
- **How a job fails:**
  - When the engine raises `panther_engine.core.errors.InputError`, the input as a whole can't be processed. The job fails with a `422`, and the engine's message as `detail`; the engine writes that message for the user.
  - Any other exception fails the job with the generic `500` detail, and its details go only to the log.
  - A problem with one item, such as one substitution that can't be mapped, isn't an error: it belongs in the result.
- **Jobs are kept in memory** until they expire (`PANTHER_API_JOB_EXPIRY_SECONDS`), so a restart loses them. Mind the size of what a job keeps: a result of 100,000 items is tens of megabytes.

## The Engine

- **The engine is a library.** Import it; never call it over HTTP. Import only what a module exports in `__all__`, such as `panther_engine.csnp`'s `score`, `CsnpInput`, `SPECIES_CODES` and `DATA_VERSION`.
- **`engine/` belongs to the engine developer.** When the API needs something the engine doesn't export, ask in the pull request or in an OpenSpec change, as `DATA_VERSION` was asked for on #26.
- **The API's models mirror the engine's frozen dataclasses,** field for field, and an adapter converts between them in the worker (`run_csnp()` in `jobs/csnp.py`).

## Adding a Service

The order that worked for `csnp`:

1. **The contract,** against a stand-in (#19):
   - the request and result models in `jobs/<service>.py`;
   - the request in `work.py`'s `JobRequest` union, and the result in `JobResult`;
   - a job model in `models.py`;
   - a valid request answered with a `501` and no job until the port exists.
2. **The form,** against the contract (#20).
3. **The port and its parity goldens,** in the engine (#24).
4. **Wiring:** the `501` goes, `run_job` calls the engine, and the code check against the engine's list lands in the same change (#26).

`refmap` is at step 1 (#30), and the open work is tracked in #46.

## Tests

The setup is in [docs/testing/api.md](../docs/testing/api.md), "Tests (pytest)". The traps:

- **A monkeypatch never reaches a worker process.** To change what a job does, patch `panther_api.jobs.runner.run_job` with a module-level function from `tests/job_helpers.py`.
- **`tests/` has no `__init__.py`.** Import shared helpers by their bare name (`from job_helpers import ...`); a test can't import from `conftest.py`.
- **`TestClient` is built on `httpx2`, not `httpx`,** so type a response as `httpx2.Response`.
- **The autouse `fake_tools` fixture** fakes the engine's tool report, so tests pass with or without the tools installed.
- **Real jobs** (`tests/test_csnp_scoring.py`) are marked `tools` and `data`, and skipped where `blastp` or the data sample is missing, as natively on Windows. Run them in the API image, by the command in the testing doc.
- **Keep a success test beside every failure test.** A test that expects an error also passes when everything fails for another reason.

## Running It With Docker

- **The data:** the compose `api` service reads the cSNP data from `.data/`. Fetch the sample there first; [docs/testing/engine.md](../docs/testing/engine.md), "The cSNP Data Sample", says how.
- **In Git Bash, start a `docker run` line with `MSYS_NO_PATHCONV=1`.** Otherwise Git Bash rewrites container paths such as `/data` into Windows paths, and every `csnp` job fails with the generic error.
- **Check that the image was loaded.** If `docker build` warns that the result stays in the build cache, `docker run` starts an older image. Build with `docker buildx build --load`.
- **Don't disturb a developer's running API.** An agent, or a script, testing the image should run it with `docker run` on another port, such as 8001. Never `docker compose down`, `stop` or `up` the repository's project, which may be serving the developer's frontend on port 8000.

## Workflow

- **Plan in `openspec/`.** The change's artifacts and its code go in one pull request. Keep the Notes at the end of `tasks.md` current.
- **Open every pull request against `main`.** CI runs only on pull requests into `main`, and one based on another pull request's branch merges into that branch, not `main`.
- **Record each deliberate difference from the legacy service** as a row in `docs/parity/divergences.md`, before it ships.
