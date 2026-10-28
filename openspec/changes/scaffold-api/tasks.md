# Tasks

## 1. Prerequisites

- [ ] 1.1 Confirm `docs/design/api-stack.md` is Accepted ([#7](https://github.com/pantherdb/panther-scoring-services/issues/7)) and that this change's proposal and design still match it; verify its status line says Accepted and every choice in design.md's Tooling configuration appears in it. If review changed a choice, update design.md before going on
- [ ] 1.2 Update the local uv to the version CI will pin (`uv self update`); verify `uv --version` prints that version, and record it in the Notes

## 2. Project and Tooling

- [ ] 2.1 Create the uv project in `api/` with `uv init --package` (distribution `panther-api`, package `panther_api`, `uv_build` backend), `.python-version` set to `3.13`, `fastapi[standard-no-fastapi-cloud-cli]` pinned exactly, and a `dev` dependency group with `ruff`, `basedpyright` and `pytest` pinned exactly; set `required-version` in `[tool.uv]`; remove `api/.gitkeep`; add `.venv/`, `__pycache__/`, `.pytest_cache/` and `.ruff_cache/` to the root `.gitignore`. Verify `uv sync` writes `api/uv.lock`, `uv run python --version` prints 3.13, and `git status` shows no virtualenv or cache files
- [ ] 2.2 Add `[tool.ruff]` (target `py313`, line length 100, rules `E W F I UP B SIM RUF S FAST`, `S101` ignored under `tests/`), `[tool.basedpyright]` (strict, `src` and `tests`, Python 3.13) and `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `-ra --strict-markers`) to `api/pyproject.toml`. Verify `uv run ruff check`, `uv run ruff format --check` and `uv run basedpyright` pass; a scratch `subprocess.run(cmd, shell=True)` in `src/` is reported as `S602` (then removed); and the basedpyright VS Code extension reports the same error as the CLI for a scratch type error. Record in the Notes which config section both of them read

## 3. App Factory and Health Check

- [ ] 3.1 Add `src/panther_api/main.py` (`create_app()` with the `/api/v1` router, `openapi_url="/api/v1/openapi.json"`, `docs_url="/api/v1/docs"`, ReDoc off; `app = create_app()`) and `routers/health.py` (`GET /health` returning `{"status": "ok"}` through a response model); verify `tests/test_health.py` passes, covering the spec's "Healthy process" and "Endpoint under the prefix" scenarios, and that `GET /health` returns 404
- [ ] 3.2 Start the dev server on port 8000 with `uv run fastapi dev`, falling back to the command line or `uvicorn` as design.md says; verify `curl -i localhost:8000/api/v1/health` returns 200 with `{"status":"ok"}` and that `/api/v1/docs` loads in a browser. Record the working command in the Notes
- [ ] 3.3 Write `docs/testing/api.md`, following `docs/testing/README.md`: the uv version needed and `uv self update`, `uv sync`, the dev server command from 3.2, each check (`ruff check`, `ruff format --check`, `basedpyright`, `pytest`), and how to run a single test; verify every command in it runs as written from `api/`

## 4. Problem Details

- [ ] 4.1 Add `src/panther_api/problems.py`: the `Problem` and `ValidationProblem` models and the three handlers from design.md (Starlette's `HTTPException`, `RequestValidationError`, `Exception`), registered in `create_app()`; verify `tests/test_problems.py` passes and covers the spec's scenarios: unknown path and path outside the prefix (404), `POST /api/v1/health` (405 with `Allow: GET`), invalid input on a test-only route (422, one `errors` item with `loc`, `msg`, `type`; a distinctive submitted value absent from the body), and an unhandled exception on a test-only route (500 with a generic `detail`; the exception message and a path in it absent from the body, using `raise_server_exceptions=False`). Every case also checks the `application/problem+json` content type and that `status` matches the HTTP status
- [ ] 4.2 Declare `Problem` as the `default` and `500` responses on the `/api/v1` router, and override `app.openapi()` so every 422 response points at `ValidationProblem` and the `HTTPValidationError` and `ValidationError` components are removed; verify in `tests/test_openapi.py` that the schema lists `GET /api/v1/health`, defines `Problem`, that a test-only route with a body documents its 422 with `ValidationProblem`, and that no `HTTPValidationError` remains anywhere in the schema. Also verify `/api/v1/docs` returns 200 HTML that references `/api/v1/openapi.json`

## 5. Committed OpenAPI Schema

- [ ] 5.1 Add `src/panther_api/openapi.py` (run as `python -m panther_api.openapi`; writes `api/openapi.json` with two-space indentation and a trailing newline), generate and commit `api/openapi.json`, and add the test to `tests/test_openapi.py` that compares it with a fresh export and fails naming the regenerate command. Verify: change the health route's summary and the test fails with that message; regenerate and it passes; revert both. Add the regenerate command to `docs/testing/api.md`
- [ ] 5.2 Add `api/openapi.json linguist-generated=true` to `.gitattributes`, with a comment naming the command that generates it; verify `git check-attr linguist-generated api/openapi.json` prints `set`

## 6. Spec Layout

- [ ] 6.1 Add an `api-service` row to the Spec Layout table in `CONTRIBUTING.md` ("Behaviour every API endpoint shares: the `/api/v1` prefix, the health check, problem-details errors and the published OpenAPI schema"); verify `npx markdownlint-cli2` passes from the repo root

## 7. CI

- [ ] 7.1 Fill the `api` slot in `.github/workflows/ci.yml` as design.md describes: an `api` filter in `changes` (with a comment that `engine/**` joins it once the API depends on the engine), an `api` job in `api/` running `astral-sh/setup-uv` (pinned to a commit SHA with the version in a comment, uv version set, cache keyed on `api/uv.lock`), `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright` and `pytest`, and `api` added to `ci-passed`'s `needs`. Add the `api` row to the What CI Runs table in `docs/testing/README.md` and update its sentence about missing jobs. Verify on the draft pull request that the `api` job runs, passes and is listed under `ci-passed`
- [ ] 7.2 On the same pull request, check whether the `dependency-review` job lists the Python packages from `api/uv.lock`; record the result in the Notes. If it does, add to `allow-licenses` only the licences the job actually rejects, and verify the job passes. If it doesn't, raise a follow-up issue for dependency submission (design.md, Risks) and link it in the Notes

## 8. Final Check

- [ ] 8.1 From a clean clone of the branch, in `api/`: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest` all pass
- [ ] 8.2 With the API's dev server running on port 8000, run the frontend with `npm run dev:api` in `frontend/`; verify `curl -i localhost:5173/api/v1/health` returns 200 with `{"status":"ok"}` through the Vite proxy, and `localhost:5173/api/v1/docs` loads
- [ ] 8.3 From the repo root, `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass

## Workflow follow-up

- Open a pull request with these artifacts. The API developer approves; the frontend developer reviews the error format and the `openapi.json` workflow, which become the frontend ↔ api contract. Apply starts only after that and after `api-stack.md` is Accepted.
- After the implementation merges, archive with `/opsx:archive` so `openspec/specs/api-service/spec.md` is created.
- The frontend developer adds the `api:types` script that generates `frontend/src/app/api/schema.d.ts` from `api/openapi.json`, as a frontend change.

## Notes

### Next action

`docs/design/api-stack.md` is drafted as Proposed on the `docs/api-stack` branch (2026-10-28), with `tech-stack.md` and `docs/design/README.md` updated. Open its pull request ("Closes #7") and get it Accepted. In parallel, commit these artifacts on `feat/scaffold-api` (not `main`, and not the docs branch) and open a pull request for review. Then start with 1.1.

### Blockers

- `docs/design/api-stack.md` is Proposed, not Accepted (#7). Apply waits for it.

### Failed approaches

None yet.

### Lessons learned

None yet.
