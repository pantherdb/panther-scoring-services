# API Tests

How to run the API, its checks and its tests. Run every command from `api/`. The stack is in [docs/design/api-stack.md](../design/api-stack.md).

## Setup

uv `0.13.6` or later. `pyproject.toml` sets `required-version`, so an older uv refuses to run and says why; update it with:

```sh
uv self update
```

Then install the project. uv downloads Python 3.13 itself if it isn't on the machine:

```sh
uv sync                                # creates .venv from uv.lock, with the dev group
```

In VS Code, install the basedpyright extension and turn off Pylance, so the editor reports the same type errors as CI.

## Before Claiming Anything Works

```sh
uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest
```

## Commands

| Command | What it does |
| ------- | ------------ |
| `uv run fastapi dev --port 8000` | Dev server with reload on port 8000, where the frontend's `/api` proxy sends requests. It finds the app through `[tool.fastapi]` in `pyproject.toml` |
| `uv run ruff check` | Lint, including the `S` security rules |
| `uv run ruff format` / `ruff format --check` | Format files, or only report |
| `uv run basedpyright` | Type check `src/` and `tests/`, strict |
| `uv run pytest` | All tests |
| `uv run python -m panther_api.openapi` | Regenerate `api/openapi.json` from the app |

With the dev server running:

- `http://localhost:8000/api/v1/health` returns `{"status":"ok"}`.
- `http://localhost:8000/api/v1/versions` returns the API, engine and tool versions. Run natively, every tool's `version` is `null`, because the external tools are only in the image.
- `http://localhost:8000/api/v1/docs` is the interactive documentation.
- `http://localhost:8000/api/v1/openapi.json` is the schema.

## Running the API in the Image

The root `Dockerfile`'s `api` stage serves the API with the engine and the pinned external tools, as it will be deployed. Run it from the repository root, not `api/`:

```sh
docker compose up --build api          # build the image and serve on localhost:8000; Ctrl+C stops it
docker compose down                    # remove the container
```

- **It's for the frontend to call,** through its dev proxy, with the real tools: `/api/v1/versions` then reports each tool's pinned version. It has no source mount and no reload, so rerun with `--build` after changing `api/` or `engine/`. Develop the API itself with the native dev server above.
- **Both use port 8000.** Run one at a time.
- **Name the service.** A bare `docker compose up` also runs the `engine` service's checks.

## The OpenAPI Schema

`api/openapi.json` is the frontend ↔ api contract: the frontend generates its TypeScript types from it. It must always match what the app serves, and `tests/test_openapi.py` fails when it doesn't.

After any change to a route, a request or response model, or an error response, regenerate it and commit it in the same pull request:

```sh
uv run python -m panther_api.openapi
```

## Tests (pytest)

Tests live in `tests/` and call the app through FastAPI's `TestClient`, so no server needs to be running and no test data is needed.

- **The `client` fixture** in `tests/conftest.py` gives a client for a fresh app.
- **`TestClient` is built on `httpx2`, not `httpx`** (Starlette 1.x). Type a test's responses as `httpx2.Response`; `httpx.Response` fails the type check. `fastapi[standard]` installs both.
- **To test with a throwaway route**, build the app with `create_app(router)` from `panther_api.main`: the router is included under `/api/v1`, like the app's own.
- **No test runs the external tools.** The app reads the tool versions once when it starts, through the engine's `report_tools()`. The autouse `fake_tools` fixture in `tests/conftest.py` replaces it with a report of all four tools at made-up paths, so tests give the same results with or without the tools installed. To test another report, patch `panther_api.versions.report_tools` again in the test, then build the app with `TestClient(create_app())`: the `client` fixture's app has already read the fake. The `api-image` CI job checks the real tools.

Run one file, or one test by name:

```sh
uv run pytest tests/test_health.py
uv run pytest -k "outside_the_prefix"
```
