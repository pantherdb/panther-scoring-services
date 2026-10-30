# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **How the engine joins the API:** an editable path dependency, resolved into `api/uv.lock`, with drift from `engine/uv.lock` as an accepted risk: [docs/design/api-stack.md](../../../docs/design/api-stack.md), Project Layout.
- **The engine is a library the API imports,** and engine code never runs on the event loop: [docs/design/tech-stack.md](../../../docs/design/tech-stack.md), API recommendation 1 and Engine condition 1.
- **Versions in every response** (API recommendation 3), and **one image for the API plus the engine** with the pinned tools (Shared Concerns, Containers): tech-stack.md.
- **The root `Dockerfile`'s stages and pins, and the compose conventions:** [openspec/changes/archive/2026-10-29-scaffold-engine/design.md](../archive/2026-10-29-scaffold-engine/design.md). Its `tools` stage was built so this change could add an `api` stage on top.
- **The app factory, the `/api/v1` router and problem details:** [openspec/changes/archive/2026-10-28-scaffold-api/design.md](../archive/2026-10-28-scaffold-api/design.md).

What exists now:

- **The engine:** `panther_engine.__version__`, and `panther_engine.core.tools.report_tools()`, which returns a `ToolReport` (name, path, version) for each tool in a fixed order. When a tool isn't on `PATH`, it reports no path and starts nothing.
- **The API:** `create_app(*routers)` builds the app, with no lifespan yet. The test `client` fixture uses `TestClient` as a context manager, so a lifespan runs in every test. `python -m panther_api.openapi` calls `create_app().openapi()` and never starts the app.
- **The frontend's dev proxy** sends `/api` to `http://localhost:8000` (`frontend/vite.config.ts`).

The behaviour is in [specs/api-service/spec.md](specs/api-service/spec.md).

## Goals / Non-Goals

**Goals:**

- The jobs change, and each service after it, can import the engine and use the `Versions` model without changing the dependency setup, the image or CI again.
- On a machine without the tools, the API's tests are exactly as deterministic as they are on one that has them.

**Non-Goals:**

- A slimmed or hardened production image (worker count, proxy headers, health checks in the image). The `api` stage serves the API correctly; deployment tunes it.
- Reporting the PANTHER data version.
- A compose setup for API development with reload. Developing the API stays native.

## Decisions

### Layout

```text
api/
  pyproject.toml             + panther-engine, with [tool.uv.sources] path = "../engine", editable
  uv.lock                    + the engine, as a path source
  openapi.json               regenerated: /api/v1/versions, Versions, ToolVersion
  src/panther_api/
    main.py                  create_app() gains a lifespan that reads the versions once
    versions.py              Versions and ToolVersion models; read_versions()
    routers/versions.py      GET /versions
  tests/
    conftest.py              + an autouse fake for the engine's tool report
    test_versions.py
Dockerfile                   + the `api` stage, on top of `tools`
.dockerignore                + api/
compose.yaml                 + the `api` service
.github/workflows/ci.yml     api filter, api-image job, ci-passed
```

- **The models go in `versions.py`, not in the router.** The jobs change will put `Versions` in every job result, and it should be able to import the model without importing a router.

### The response shape

```json
{
  "api": "0.1.0",
  "engine": "0.1.0",
  "tools": [
    { "name": "blastp", "version": "2.17.0" },
    { "name": "hmmscan", "version": "3.4" },
    { "name": "hmmsearch", "version": "3.4" },
    { "name": "epa-ng", "version": "0.3.8" }
  ]
}
```

- **`tools` is a list, in the engine's order,** not an object keyed by name. Each entry can then gain fields later, such as the package name ("BLAST+"), without changing the shape.
- **`version` is required and can be `null`** (`str | None` with no default). The generated TypeScript type is then `version: string | null`, and the frontend has to handle a missing tool.
- **The data version is left out until it exists.** Adding a `data` field later is an added, optional property, so clients built against this version keep working.
- **The API declares its own Pydantic models,** and `read_versions()` copies only the name and version out of each `ToolReport`. That keeps the path out of the response, as the spec requires.
  - *Alternative:* return the engine's `ToolReport` dataclass directly. Rejected: the response would carry the path, and an engine refactor would silently change the public contract.
  - The general rule for the API and engine types used by service inputs and results is left to the jobs change. Here the type is small enough that copying it is the clear choice.

### Read once, in the lifespan

`create_app()` gains a lifespan:

- It calls `read_versions()` through `fastapi.concurrency.run_in_threadpool` and stores the result on `app.state.versions`.
- The route returns `app.state.versions`.

This follows "engine code never runs on the event loop" even at startup. The tools' version commands are subprocesses, and the thread keeps them off the loop.

**If the report itself raises,** `read_versions()` logs the exception and lists every tool in the engine's `TOOLS` with a `null` version. A tool whose output can't be decoded, for example, then can't stop the API from starting, and the health check keeps its "no dependency on the tools" requirement. *(Added during apply, 2026-10-29.)*

*Alternatives:*

- **Read on each request.** Rejected: every request would start four subprocesses, and the spec forbids it.
- **A module-level `functools.cache`.** Rejected: the cache would be shared by every app the tests build, so a test with a missing tool would see whatever an earlier test cached.
- **A lifespan on the versions router.** Rejected: an app-level lifespan doesn't depend on how a FastAPI version merges router lifespans, and the jobs change's worker pool will need the app-level one anyway.

The schema export doesn't start the app, so regenerating `openapi.json` never runs the tools.

### Tests without the real tools

- **An autouse fixture in `tests/conftest.py`** replaces `panther_api.versions.report_tools` with a fake that returns all four tools with fixed versions and made-up paths. Every test, and the existing `client` fixture, then sees the same versions, whether the machine has the tools or not.
- **Per-test overrides:** a test for the missing-tool scenario swaps in a report without `epa-ng`. A counting fake proves the report runs once at startup, however many requests follow. The made-up paths let the "no file paths" scenario check that they don't appear in the body.
- **The real `report_tools()` is never called in the API's tests.** The `api-image` CI job checks the real call, in the image with the tools.
- *Alternative:* a `create_app(versions=...)` parameter. Rejected: it changes the factory's signature for tests only, and the patch point (`panther_api.versions.report_tools`) stays one well-known name.

### The `api` image stage

On top of `tools`, beside `engine`:

| Step | Why |
| ---- | --- |
| `/opt/venv` and `/work` owned by `panther`, `UV_PROJECT_ENVIRONMENT=/opt/venv`, `/opt/venv/bin` on `PATH` | The same conventions as the `engine` stage |
| Copy `api/pyproject.toml`, `api/uv.lock`, `api/.python-version` and `engine/pyproject.toml`; then `uv sync --locked --no-dev --no-cache --no-install-project --no-install-package panther-engine` | The dependency layer. It changes only when a lock or a `pyproject.toml` changes. uv reads the engine's `pyproject.toml` to check the lock, but installs nothing from its source yet |
| Copy `engine/pyproject.toml`, `engine/src/` and `api/`; then `uv sync --locked --no-dev --no-cache --no-editable` | Installs the API and the engine as regular packages. The image runs what it was built from, and nothing mounted over `/work` can change that |
| `WORKDIR /work/api`, `EXPOSE 8000`, `CMD ["fastapi", "run", "--port", "8000"]` | `fastapi run` finds the app through `[tool.fastapi]` in `api/pyproject.toml`, as the dev server does. It listens on `0.0.0.0` |

- **Not on top of the `engine` stage.** That stage installs the engine's dev group, sets `PANTHER_REQUIRE_TOOLS` for its tests, and installs editable. The API needs none of these. Both stages build on `tools`, so the tool pins exist once.
- **The engine's tests, `tools-env/` and lock aren't copied.** Building the engine package needs only its `pyproject.toml` and `src/`.

### The compose `api` service

```yaml
api:
  build:
    context: .
    target: api
  ports:
    - "8000:8000"
```

- **No mount and no command override.** `docker compose up --build api` builds the image and serves it. The frontend's dev proxy reaches it at its default target with no setting changed.
- **The documented command names the service.** Without the name, `docker compose up` would also run the `engine` service's checks.
- **Port 8000 is shared with the native dev server.** Run one at a time; `docs/testing/api.md` says so.

### CI

- **The `api` filter** gains `engine/**`, `Dockerfile`, `.dockerignore` and `compose.yaml`. The API's checks and its image both depend on them. This replaces the filter's "once api/ depends on engine/" comment.
- **The `api` job** doesn't change. `uv sync --locked` in `api/` installs the engine from `../engine`, which the checkout already contains.
- **A new `api-image` job,** on the same filter, with the same architecture matrix as `engine-image`:
  - It builds the `api` target with `docker/build-push-action`, pinned to the SHA `engine-image` uses, and loads it.
  - **The build cache:** it reads the `engine-<arch>` cache scope, so the tool stages come from cache, and writes its own `api-<arch>` scope. Apply chooses the cache mode so that the tool stages aren't stored twice, and records the cache size in the Notes.
  - It runs the image detached on port 8000. It waits for `/api/v1/health` with `curl --retry`. Then it checks `/api/v1/versions` with `jq`: four tools, each with a non-null version. If a step fails, it prints the container's logs.
- **Why a separate job,** instead of a step in `engine-image`: the two run on different paths. A change to `api/` alone must build the API image and not rerun the engine's suite.
- **Why `api-image` checks for non-null versions, not exact ones:** `engine-image` already asserts the exact pinned versions on the same `tools` stage. Repeating them in `ci.yml` would be a third copy of each pin to keep in step. The exact versions in the spec's "Versions in the image" scenario are checked by hand during apply.
- **`ci-passed`** needs `api-image`.

## Risks / Trade-offs

- **[basedpyright doesn't resolve the editable engine]** uv's editable install is a `.pth` file pointing at `engine/src`. Check during apply that `uv run basedpyright` in `api/` sees `panther_engine`'s types; the engine ships `py.typed`. If it doesn't, add `../engine/src` to `extraPaths` with a comment saying why, and record it in the Notes.
- **[`uv sync --locked` in the dependency layer needs more of the engine than its `pyproject.toml`]** If uv wants the source to check the lock, apply finds out. Either copy the engine before the first sync and accept a less useful layer cache (the engine has no dependencies of its own yet), or adjust the flags. Record which in the Notes.
- **[`fastapi run` doesn't find the app in the image]** Fall back to `uvicorn panther_api.main:app --host 0.0.0.0 --port 8000`, and record it in the Notes.
- **[A hanging tool delays startup]** `report_tools()` gives each tool 30 s, so the worst case is about two minutes before the API serves. The tools are pinned and answer in milliseconds. The CI job's health wait would show a hang as a timeout, not as a silent pass.
- **[The engine's lock and the API's lock drift]** This risk is accepted in api-stack.md. Today the engine has no runtime dependencies, so the two can't drift yet. It becomes real with the engine's first runtime dependency.
- **[`dependency-review` flags `panther-engine`]** `api/uv.lock` now lists the engine as a path source. It isn't on PyPI and has no licence metadata, and the review may report it as unknown. Check its log on the pull request. If it fails there, exempt `pkg:pypi/panther-engine` by purl in `allow-dependencies-licenses`, with a comment saying it's this repository's own package. Never widen `allow-licenses` for it.
- **[Two image jobs per architecture make CI slower]** The `api` stage reuses the cached tool stages, so a cached run builds only the Python layers. Record the first and a cached build time in the Notes.

## Migration Plan

Nothing to migrate. The endpoint and image are new, and nothing calls them yet. Rollback is reverting the pull request.
