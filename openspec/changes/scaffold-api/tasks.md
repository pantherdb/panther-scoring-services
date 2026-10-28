# Tasks

## 1. Prerequisites

- [x] 1.1 Confirm `docs/design/api-stack.md` is Accepted ([#7](https://github.com/pantherdb/panther-scoring-services/issues/7)) and that this change's proposal and design still match it; verify its status line says Accepted and every choice in design.md's Tooling configuration appears in it. If review changed a choice, update design.md before going on
- [x] 1.2 Update the local uv to the version CI will pin (`uv self update`); verify `uv --version` prints that version, and record it in the Notes

## 2. Project and Tooling

- [x] 2.1 Create the uv project in `api/` with `uv init --package` (distribution `panther-api`, package `panther_api`, `uv_build` backend), `.python-version` set to `3.13`, `fastapi[standard-no-fastapi-cloud-cli]` pinned exactly, and a `dev` dependency group with `ruff`, `basedpyright` and `pytest` pinned exactly; set `required-version` in `[tool.uv]`; remove `api/.gitkeep`; add `.venv/`, `__pycache__/`, `.pytest_cache/` and `.ruff_cache/` to the root `.gitignore`. Verify `uv sync` writes `api/uv.lock`, `uv run python --version` prints 3.13, and `git status` shows no virtualenv or cache files
- [x] 2.2 Add `[tool.ruff]` (target `py313`, line length 100, rules `E W F I UP B SIM RUF S FAST`, `S101` ignored under `tests/`), `[tool.basedpyright]` (strict, `src` and `tests`, Python 3.13) and `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `-ra --strict-markers`) to `api/pyproject.toml`. Verify `uv run ruff check`, `uv run ruff format --check` and `uv run basedpyright` pass; a scratch `subprocess.run(cmd, shell=True)` in `src/` is reported as `S602` (then removed); and the basedpyright VS Code extension reports the same error as the CLI for a scratch type error. Record in the Notes which config section both of them read

## 3. App Factory and Health Check

- [x] 3.1 Add `src/panther_api/main.py` (`create_app()` with the `/api/v1` router, `openapi_url="/api/v1/openapi.json"`, `docs_url="/api/v1/docs"`, ReDoc off; `app = create_app()`) and `routers/health.py` (`GET /health` returning `{"status": "ok"}` through a response model); verify `tests/test_health.py` passes, covering the spec's "Healthy process" and "Endpoint under the prefix" scenarios, and that `GET /health` returns 404
- [x] 3.2 Start the dev server on port 8000 with `uv run fastapi dev`, falling back to the command line or `uvicorn` as design.md says; verify `curl -i localhost:8000/api/v1/health` returns 200 with `{"status":"ok"}` and that `/api/v1/docs` loads in a browser. Record the working command in the Notes
- [x] 3.3 Write `docs/testing/api.md`, following `docs/testing/README.md`: the uv version needed and `uv self update`, `uv sync`, the dev server command from 3.2, each check (`ruff check`, `ruff format --check`, `basedpyright`, `pytest`), and how to run a single test; verify every command in it runs as written from `api/`

## 4. Problem Details

- [x] 4.1 Add `src/panther_api/problems.py`: the `Problem` and `ValidationProblem` models and the three handlers from design.md (Starlette's `HTTPException`, `RequestValidationError`, `Exception`), registered in `create_app()`; verify `tests/test_problems.py` passes and covers the spec's scenarios: unknown path and path outside the prefix (404), `POST /api/v1/health` (405 with `Allow: GET`), invalid input on a test-only route (422, one `errors` item with `loc`, `msg`, `type`; a distinctive submitted value absent from the body), and an unhandled exception on a test-only route (500 with a generic `detail`; the exception message and a path in it absent from the body, using `raise_server_exceptions=False`). Every case also checks the `application/problem+json` content type and that `status` matches the HTTP status
- [x] 4.2 Declare `Problem` as the `default` and `500` responses on the `/api/v1` router, and override `app.openapi()` so every 422 response points at `ValidationProblem` and the `HTTPValidationError` and `ValidationError` components are removed; verify in `tests/test_openapi.py` that the schema lists `GET /api/v1/health`, defines `Problem`, that a test-only route with a body documents its 422 with `ValidationProblem`, and that no `HTTPValidationError` remains anywhere in the schema. Also verify `/api/v1/docs` returns 200 HTML that references `/api/v1/openapi.json`

## 5. Committed OpenAPI Schema

- [x] 5.1 Add `src/panther_api/openapi.py` (run as `python -m panther_api.openapi`; writes `api/openapi.json` with two-space indentation and a trailing newline), generate and commit `api/openapi.json`, and add the test to `tests/test_openapi.py` that compares it with a fresh export and fails naming the regenerate command. Verify: change the health route's summary and the test fails with that message; regenerate and it passes; revert both. Add the regenerate command to `docs/testing/api.md`
- [x] 5.2 Add `api/openapi.json linguist-generated=true` to `.gitattributes`, with a comment naming the command that generates it; verify `git check-attr linguist-generated api/openapi.json` prints `set`

## 6. Spec Layout

- [x] 6.1 Add an `api-service` row to the Spec Layout table in `CONTRIBUTING.md` ("Behaviour every API endpoint shares: the `/api/v1` prefix, the health check, problem-details errors and the published OpenAPI schema"); verify `npx markdownlint-cli2` passes from the repo root

## 7. CI

- [x] 7.1 Fill the `api` slot in `.github/workflows/ci.yml` as design.md describes: an `api` filter in `changes` (with a comment that `engine/**` joins it once the API depends on the engine), an `api` job in `api/` running `astral-sh/setup-uv` (pinned to a commit SHA with the version in a comment, uv version set, cache keyed on `api/uv.lock`), `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright` and `pytest`, and `api` added to `ci-passed`'s `needs`. Add the `api` row to the What CI Runs table in `docs/testing/README.md` and update its sentence about missing jobs. Verify locally, without a pull request: actionlint (`uvx --from actionlint-py actionlint`) reports no errors in `ci.yml`, and the `api` job's steps, run in order from a copy of only the files git would commit, all pass
- [x] 7.2 Without a pull request: find out from GitHub's documentation whether the dependency graph, which `dependency-review` reads, supports `uv.lock`, and record the answer and its source in the Notes. Check the licence of every package in `api/uv.lock` against `dependency-review`'s `allow-licenses`, and add only licences that are missing, each named in the Notes. If the graph doesn't read `uv.lock`, record dependency submission (design.md, Risks) in the Notes as a follow-up; open no issue without the API developer's go-ahead

## 8. Final Check

- [x] 8.1 From a clean clone of the branch, in `api/`: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest` all pass
- [x] 8.2 With the API's dev server running on port 8000, run the frontend with `npm run dev:api` in `frontend/`; verify `curl -i localhost:5173/api/v1/health` returns 200 with `{"status":"ok"}` through the Vite proxy, and `localhost:5173/api/v1/docs` loads
- [x] 8.3 From the repo root, `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass

## Workflow follow-up

- Open a pull request with these artifacts. The API developer approves; the frontend developer reviews the error format and the `openapi.json` workflow, which become the frontend ↔ api contract. Apply starts only after that and after `api-stack.md` is Accepted.
- When a pull request for the implementation is opened (`main` accepts changes only through one), confirm on it that the `api` job runs and passes under `ci-passed`, and what `dependency-review` reports for `api/uv.lock`. Not tracked here: the API developer chose to finish this change without a pull request (2026-10-28).
- After the implementation merges, archive with `/opsx:archive` so `openspec/specs/api-service/spec.md` is created.
- The frontend developer adds the `api:types` script that generates `frontend/src/app/api/schema.d.ts` from `api/openapi.json`, as a frontend change.

## Notes

### Next action

All tasks are done (2026-10-28). 7.1 and 7.2 were first verified locally (tasks reworded 2026-10-28, when the API developer chose to finish before opening a pull request). The implementation is now in #11.

On #11's first run, the `api` job passed on GitHub, but `dependency-review` failed on two licences (see Lessons learned, 7.2). Fixed by exempting the two packages by name. Next: confirm `ci-passed` is green on #11 and get the reviews. After it merges, archive.

### Blockers

None.

### Failed approaches

- **Stopping background dev servers by pattern (3.2, 8.2, 2026-10-28).** `pkill -f` and `pgrep -f` with the server's command line also matched the shell running them, which then killed itself (exit 144). Killing the process group saved from `$!` didn't stop the servers either. What worked: kill by PID, then check that the ports are free with `curl`, using a command that doesn't contain the pattern.
- **`raw_detail: object = exc.detail` (4.1).** Pyright narrows a declared `object` back to `str` on assignment, so the `isinstance` check was still "unnecessary". `cast(object, exc.detail)` keeps it `object`.

### Lessons learned

- **uv 0.13.6 (1.2).** Updated from 0.9.17 with `uv self update 0.13.6`. CI pins the same version, and `required-version = ">=0.13.6"` in `api/pyproject.toml` stops an older uv.
- **basedpyright reads `[tool.basedpyright]` (2.2).** Changing `typeCheckingMode` there changes the CLI's result (strict: 0 warnings on a scratch file; recommended: 5). The VS Code basedpyright extension, with Pylance off, reports the same scratch error as the CLI (checked by the API developer, 2026-10-28).
- **`fastapi dev` finds the app from `[tool.fastapi] entrypoint` (3.2).** `uv run fastapi dev --port 8000` works from `api/` with `entrypoint = "panther_api.main:app"`.
- **Starlette 1.x's `TestClient` is built on `httpx2`, not `httpx` (4.1).** `fastapi[standard]` installs both. Annotate test responses as `httpx2.Response`; `httpx.Response` fails the type check. Worth adding to `docs/testing/api.md` at archive.
- **FastAPI skips its own 422 when a route declares `default` (4.2).** So `HTTPValidationError` is never generated, and the schema override only adds `ValidationProblem` 422s and moves error bodies to `application/problem+json`. design.md was updated to match.
- **Starlette types `HTTPException.detail` as `str`; FastAPI's subclass accepts any value (4.1).** The handler falls back to the title for a non-string detail.
- **FastAPI's default 422 echoes the submitted value (4.1).** With the handlers switched off, `test_validation_error_does_not_echo_the_value` fails. That's what the handler protects.
- **Ruff `S105` flags test constants named like secrets (4.1).** `SECRET_PATH` was renamed `INTERNAL_PATH`.
- **markdownlint's `**/*.md` glob reaches `api/.venv/` (3.3).** Packages install Markdown licence files there. Added `**/.venv/**` to the ignores in `.markdownlint-cli2.jsonc`, beside `node_modules`. This was outside the task list.
- **`git check-attr` prints `true`, not `set`,** for an attribute written `=true` (5.2).
- **8.2 needs the frontend's dependencies:** `npm ci` in `frontend/` first.
- **CI checked locally (7.1).** actionlint 1.7.12 (`uvx --from actionlint-py actionlint`) reports no errors in `ci.yml`. The `api` job's five steps, run in order from a copy of only the files git would commit, all pass. `setup-uv` is v10.3.3, pinned to `68559e99cc807c1eb7e9238fd43a15bba460eec2`. GitHub itself has not run the job yet: see Workflow follow-up.
- **The dependency graph does read `uv.lock` (7.2, corrected 2026-10-28).** GitHub's [supported ecosystems](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/dependency-graph-supported-package-ecosystems) page lists no uv entry, and the local check concluded from that that `dependency-review` couldn't see Python packages. That was wrong: on #11 it reported packages from `api/uv.lock` by name. The docs page is behind; trust the job's output over it. No dependency submission is needed.
- **Package metadata and GitHub's licence scanner can disagree (7.2).** Locally, all 62 locked packages had allowed licences in their own metadata. On #11, GitHub's scanner rejected two:
  - `protobuf` as `BSD-3-Clause AND LicenseRef-scancode-protobuf`. The extra reference is protobuf's note that code generated from your `.proto` files is yours.
  - `typing-extensions` as `Python-2.0 AND GPL-1.0-or-later AND …`. The PSF licence's history section mentions the GPL, but the package is PSF-2.0.

  Both are exempted by name with `allow-dependencies-licenses` in `ci.yml`, with a comment on each, rather than adding `GPL-1.0-or-later` to `allow-licenses` for every package. Advisories still apply to them. The API developer approved this. A local licence check can't stand in for the job: check the job's output.
- **`fastapi[standard-no-fastapi-cloud-cli]` pulls in OpenTelemetry (7.2).** It installs `opentelemetry-sdk` and the OTLP HTTP exporter, which bring in `protobuf`, `googleapis-common-protos` and `requests`. FastAPI exports nothing unless `FASTAPI_OTEL_AUTO_CONFIGURE=true` and an `OTEL_EXPORTER_OTLP_*` endpoint are set (`fastapi/telemetry/_runtime.py`). If telemetry is ever turned on, its `logs` setting records exception messages and stack traces, so whatever collector it sends to sees what our 500 handler keeps out of responses. Dropping these packages would mean not using the `standard` extra, which is a change to `api-stack.md`.
