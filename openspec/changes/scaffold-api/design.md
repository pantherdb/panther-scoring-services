# Design

## Context

`api/` holds only `.gitkeep`. This change relies on these decisions and doesn't repeat them:

- The API stack (FastAPI, uv, Python 3.13, Ruff, basedpyright, pytest, RFC 9457, the committed `openapi.json`), and why `api/` is its own uv project rather than a workspace shared with `engine/`: [docs/design/api-stack.md](../../../docs/design/api-stack.md), to be written and Accepted under [#7](https://github.com/pantherdb/panther-scoring-services/issues/7) before apply starts.
- One app for all four services, scoring through jobs, compatibility endpoints, and the engine as a library that `api/` imports: [docs/design/tech-stack.md](../../../docs/design/tech-stack.md).
- The frontend calls a relative `/api/v1` and proxies `/api` to `http://localhost:8000` in dev and preview. There's no CORS: [openspec/changes/archive/2026-10-28-scaffold-frontend/design.md](../archive/2026-10-28-scaffold-frontend/design.md).

The behaviour is in [specs/api-service/spec.md](specs/api-service/spec.md).

Locally, uv is 0.9.17 and the latest is 0.13.6. pyenv provides Python 3.11, so uv downloads 3.13 itself.

## Goals / Non-Goals

**Goals:**

- The first service endpoint and the jobs change add their routers, models and tests without editing the app factory, the error handlers or the test setup.
- `uv sync --locked`, then `ruff check`, `ruff format --check`, `basedpyright` and `pytest`, all pass from a clean clone, locally and in CI.
- The frontend can generate types from `api/openapi.json` without running the API.

**Non-Goals:**

- No settings module, logging configuration, middleware, auth or rate limiting. Each arrives with the change that needs it.
- No Dockerfile or production server configuration.
- No custom problem `type` URIs. Every problem uses `about:blank`, as RFC 9457 allows, until the frontend needs to tell errors apart by more than status.

## Decisions

### Layout

```text
api/
  pyproject.toml          project, dependency groups, [tool.ruff], [tool.basedpyright], [tool.pytest.ini_options]
  uv.lock
  .python-version         3.13
  openapi.json            generated, committed
  src/panther_api/
    __init__.py
    main.py               create_app(); app = create_app()
    problems.py           Problem model, exception handlers, responses for the schema
    openapi.py            the schema export: python -m panther_api.openapi
    routers/
      __init__.py
      health.py           GET /health -> {"status": "ok"}
  tests/
    conftest.py           client fixtures
    test_health.py
    test_problems.py      404, 405, 422, 500 (test-only routes)
    test_openapi.py       served schema, docs page, committed file is current
```

- **`src/` layout, built with `uv_build`** (what `uv init --package` sets up). Tests then import the installed package, not the working directory, so a missing `__init__.py` or a file left out of the package fails in tests too, not only in deployment.
- **One router per area under `routers/`.** Each service and the jobs change add a module and one `include_router` line in `create_app()`. *Alternative:* one module per service with its routes, models and engine calls together. Deferred: with only `health.py` there's nothing to choose between, and the first service change can reorganize if its routes outgrow one file.

### App factory, prefix, and where the docs live

`create_app()` builds a new `FastAPI` each time, and `main.py` also exposes `app = create_app()` for the server. Tests call `create_app()` so they can add throwaway routes (for the 422 and 500 cases) without touching the real app.

The `/api/v1` prefix is set once, on an `APIRouter` that every area's router is included into. The schema and docs URLs are set on the app to `/api/v1/openapi.json` and `/api/v1/docs`, and ReDoc is turned off. The frontend's proxy only forwards `/api`, so FastAPI's default `/docs` and `/openapi.json` would be unreachable through it, and a deployed site would also have to route them separately.

*Alternative:* `root_path="/api/v1"`. Rejected: `root_path` is for a proxy that strips the prefix. Here nothing strips it, so the paths would be wrong in the schema.

### Problem details

`problems.py` holds three handlers, registered by `create_app()`:

| Handler for | Status | `detail` | Notes |
| ----------- | ------ | -------- | ----- |
| Starlette's `HTTPException` (FastAPI's subclasses it) | the exception's | the exception's `detail` | Keeps the exception's headers, so `405` keeps `Allow` |
| `RequestValidationError` | 422 | "Request validation failed" | `errors`: each of FastAPI's errors reduced to `loc`, `msg`, `type`. `input`, `ctx` and `url` are dropped, so submitted values are never echoed |
| `Exception` | 500 | a fixed, generic sentence | The exception and traceback are logged, never returned |

Every problem has `type: "about:blank"` and `title` set to the HTTP reason phrase for its status, as RFC 9457 specifies for `about:blank`. The responses use `JSONResponse` with `media_type="application/problem+json"`.

**Handlers for the base class.** The `HTTPException` handler is registered for Starlette's class, not FastAPI's. Starlette's router raises its own `HTTPException` for unknown paths and wrong methods; a handler on FastAPI's subclass would miss them.

**The schema.** `Problem` is a Pydantic model; `ValidationProblem` extends it with `errors`. They reach the schema in two ways:

- **The `/api/v1` router** declares `default` and `500` responses with `Problem`, so every route under it documents its errors.
- **The 422 response.** FastAPI adds its own `HTTPValidationError` 422 to every route with parameters or a body, unless the route already declares a `422`, `4XX` or `default` response. The router's `default` response therefore stops it. The app is a `FastAPI` subclass whose `openapi()` post-processes the generated schema (`document_problems` in `problems.py`):
  - it adds a 422 with `ValidationProblem` to every operation that has parameters or a request body;
  - it moves every error response's body from `application/json` to `application/problem+json`, since FastAPI lists a response `model` under `application/json`;
  - it adds `ValidationProblem` and `FieldError` to the components.

  The health route has no parameters, so its 422 only shows once the first route with input arrives. A test-only route in `test_openapi.py` checks it now. *(Updated during apply, 2026-10-28: the plan was to rewrite FastAPI's `HTTPValidationError` 422s and delete their components. Declaring `default` means they're never generated.)*
- *Alternative:* a custom `APIRoute` class that changes how FastAPI documents 422. Rejected: it reaches into FastAPI internals that change between releases. Post-processing the generated schema uses only its output.

### The committed schema and its check

- **Export:** `python -m panther_api.openapi` writes `create_app().openapi()` to `api/openapi.json` as JSON with two-space indentation, keys in FastAPI's order, and a trailing newline. Nothing in the schema depends on the environment (no server URLs, no hostnames), so the file is the same on every machine.
- **Check:** `tests/test_openapi.py` compares the committed file with a fresh export, and on a mismatch fails with the command to regenerate it. Because the check is a pytest test, CI's `pytest` step covers it and the CI job needs no extra step.
- **Marked as generated** in `.gitattributes`, so GitHub collapses it in diffs as it does `frontend/src/app/api/schema.d.ts`. The diff stays one click away, for the frontend developer reviewing a contract change.
- *Alternative:* the frontend fetches the schema from a running API. Rejected: the frontend's CI would then need the API running, and contract changes wouldn't show up in the API's pull requests.

### Tooling configuration

Everything goes in `api/pyproject.toml`; there are no separate config files.

- **Dependencies:** `fastapi[standard-no-fastapi-cloud-cli]` at runtime. The `standard` extra also pulls in `fastapi-cloud-cli` and its dependencies, which we don't use. The dev dependency group (`[dependency-groups] dev`) holds `ruff`, `basedpyright` and `pytest`. The `httpx` that `TestClient` needs comes with the `standard` extras. All versions are pinned exactly, as the frontend pins its npm packages.
- **Ruff:** target `py313`, line length 100. Rules: `E`, `W`, `F`, `I`, `UP`, `B`, `SIM`, `RUF`, `S` and `FAST`. Tests ignore `S101` (`assert`). The `S` rules (`S602`, `S604`, `S605` and the rest of the subprocess family) are what enforce CLAUDE.md's "never pass request data through a shell" once the API or engine runs tools.
- **basedpyright:** `typeCheckingMode = "strict"`, over `src` and `tests`, Python 3.13. Strict rather than `all`: `all` adds rules such as `reportAny` that fire on FastAPI's own signatures.
- **pytest:** `testpaths = ["tests"]`, and `-ra --strict-markers`.
- **uv:** `required-version` in `[tool.uv]` makes everyone use a uv that writes the same `uv.lock` format. CI pins the same uv version. Developers update with `uv self update`.

### Running it

The dev server is `uv run fastapi dev` on port 8000, matching the frontend proxy's default. Whether the `fastapi` CLI finds `panther_api.main:app` from a `[tool.fastapi]` entrypoint setting, or needs the path on the command line, is checked during apply. `docs/testing/api.md` records the command that works. Without `dev`, it's `uv run fastapi run`.

### CI

Filling the slot in `.github/workflows/ci.yml`:

- **`changes`:** an `api` filter on `api/**` and `.github/workflows/ci.yml`. Once `api/` depends on `engine/`, the filter also needs `engine/**`; a comment says so.
- **The `api` job** runs in `api/`:
  - `astral-sh/setup-uv`, pinned to a commit SHA with the uv version set and its cache keyed on `api/uv.lock`
  - `uv sync --locked`: fails if `uv.lock` is out of date with `pyproject.toml`
  - `uv run ruff check`, `uv run ruff format --check`, `uv run basedpyright`, `uv run pytest`

  `setup-uv` installs the Python version named in `.python-version`.
- **`ci-passed`:** `needs` gains `api`.

Dependabot already updates the `setup-uv` SHA (it covers GitHub Actions). Python packages are left out of Dependabot, as npm packages are.

## Risks / Trade-offs

- **[Dependency review may not read `uv.lock`]** → Check on the pull request whether the `dependency-review` job lists the Python packages. If it doesn't, record it in the Notes and raise a follow-up. One option is the `uv` dependency submission action, which reports the lock to GitHub's dependency graph. The licence allow-list may also need Python licences such as `MIT AND Python-2.0`; add only what the job actually reports.
- **[Starlette's error middleware re-raises after the 500 handler]** → This is expected: the handler's response is still sent, and the server logs the exception. Tests for the 500 case use `TestClient(app, raise_server_exceptions=False)`, or the test would see the exception instead of the response.
- **[The schema relies on FastAPI skipping its own 422 when `default` is declared]** → `test_openapi.py` asserts that no `HTTPValidationError` or `ValidationError` appears anywhere in the schema. A FastAPI upgrade that changes the rule fails that test instead of silently changing the contract.
- **[The `fastapi` CLI can't find the app]** → Fall back to `uv run uvicorn panther_api.main:app --reload --port 8000`, and record which command works in the Notes and `docs/testing/api.md`.
- **[A strict type checker on FastAPI code produces noise]** → Fix it in our code first. Use a targeted `# pyright: ignore[rule]` with a reason only for library typing gaps, and list each one in the Notes.
- **[A developer's uv is older than `required-version`]** → uv refuses to run and says why. `docs/testing/api.md` tells them to run `uv self update`.
