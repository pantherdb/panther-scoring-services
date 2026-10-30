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
- `POST http://localhost:8000/api/v1/jobs` starts a job, and `GET http://localhost:8000/api/v1/jobs/{id}` polls it. See [Try the Jobs by Hand](#try-the-jobs-by-hand).

## Settings

The API reads its settings from environment variables when it starts. An invalid value stops it from starting, with an error naming the variable.

| Variable | Default | Valid | What it sets |
| -------- | ------- | ----- | ------------ |
| `PANTHER_API_JOB_WORKERS` | `2` | an integer ≥ 1 | Worker processes that run jobs. Jobs beyond that wait as `queued` |
| `PANTHER_API_JOB_EXPIRY_SECONDS` | `86400` (24 hours) | an integer ≥ 1 | How long a finished job is kept. After that, polling it gets a 404 |

Set one for the native dev server with, for example, `PANTHER_API_JOB_WORKERS=1 uv run fastapi dev --port 8000`, and for the image with `docker run -e PANTHER_API_JOB_WORKERS=1 …`. The compose `api` service sets none, so it uses the defaults. Jobs are kept in memory, and are lost when the API restarts.

## Running the API in the Image

The root `Dockerfile`'s `api` stage serves the API with the engine and the pinned external tools, as it will be deployed. Run it from the repository root, not `api/`:

```sh
docker compose up --build api          # build the image and serve on localhost:8000; Ctrl+C stops it
docker compose down                    # remove the container
```

- **It's for the frontend to call,** through its dev proxy, with the real tools: `/api/v1/versions` then reports each tool's pinned version. It has no source mount and no reload, so rerun with `--build` after changing `api/` or `engine/`. Develop the API itself with the native dev server above.
- **Both use port 8000.** Run one at a time.
- **Name the service.** A bare `docker compose up` also runs the `engine` service's checks.
- **To wait for it in a script,** use `curl --retry 30 --retry-all-errors --retry-delay 1 localhost:8000/api/v1/health`. Docker's port proxy accepts the connection before the app listens, so the first requests get an empty reply, not a refused connection, and `--retry-connrefused` doesn't retry them. CI's `api-image` job waits this way.

## Try the Jobs by Hand

Until the first scoring service is ported, the only job is `tools`: a worker process runs the engine's tool report and returns each tool's version. It checks that the API, the worker pool, the engine and the tools work together. Start the API in the image, so the tools are there, from the repository root:

```sh
docker compose up --build api
```

**From the docs page:** open `http://localhost:8000/api/v1/docs`.

1. Open **POST /api/v1/jobs**, choose **Try it out**, set the body to `{"service": "tools", "input": {}}`, and choose **Execute**. The response is `202`, with a `location` header and the job, `queued` or `running`. Copy its `id`.
2. Open **GET /api/v1/jobs/{job_id}**, choose **Try it out**, paste the `id`, and choose **Execute**. Repeat until `status` is `succeeded`, a second or two after the first job, which starts a worker.

**With curl,** in a second terminal (a POSIX shell; on Windows, the WSL2 shell):

```sh
curl -si localhost:8000/api/v1/jobs -H 'Content-Type: application/json' -d '{"service": "tools", "input": {}}'
curl -s localhost:8000/api/v1/jobs/<id>      # the id from the job, or the path from its location header
```

A finished job looks like this:

```json
{
  "id": "c56f34dc-cf36-429d-83d9-dcac03e46957",
  "service": "tools",
  "status": "succeeded",
  "created_at": "2026-10-30T00:32:00.020522Z",
  "started_at": "2026-10-30T00:32:00.021159Z",
  "finished_at": "2026-10-30T00:32:01.540021Z",
  "result": {
    "tools": [
      { "name": "blastp", "version": "2.17.0" },
      { "name": "hmmscan", "version": "3.4" },
      { "name": "hmmsearch", "version": "3.4" },
      { "name": "epa-ng", "version": "0.3.8" }
    ]
  },
  "error": null,
  "versions": { "api": "0.1.0", "engine": "0.1.0", "tools": ["… as GET /api/v1/versions …"] }
}
```

What else to try:

- **The worker processes:** `docker compose top api` lists the API's process and, once a job has run, a worker started by `multiprocessing` (`spawn`).
- **Errors:** an unknown `service`, or an `input` with a field it doesn't take, gets a `422` problem listing the field. `GET /api/v1/jobs/not-a-real-id` gets a `404` problem.
- **Natively:** the same steps work against `uv run fastapi dev --port 8000` in `api/`, but every tool's `version` is `null`, because the tools are only in the image.

### The cSNP Job: Validated, Not Scored Yet

The `csnp` job's contract is in place, but the engine's cSNP scoring isn't. The API validates a `csnp` request as it will when scoring lands, then answers a valid one with `501` and creates no job. The rules are in `openspec/specs/scoring-input/` (until `add-csnp-job` is archived, `openspec/changes/add-csnp-job/specs/scoring-input/spec.md`).

A valid request gets `501`:

```sh
curl -si localhost:8000/api/v1/jobs -H 'Content-Type: application/json' \
  -d '{"service": "csnp", "input": {"sequence": ">sp|P02649|APOE_HUMAN\nMKVLWAALLVTFLAGCQAKV", "substitutions": ["L4P", "C130R"], "species": "HUMAN"}}'
```

```json
{ "type": "about:blank", "title": "Not Implemented", "status": 501, "detail": "cSNP scoring isn't available yet." }
```

An invalid one gets the `422` validation problem, which names each failing field and never repeats its value. Here `species` isn't a species code and `substitutions` is empty:

```sh
curl -si localhost:8000/api/v1/jobs -H 'Content-Type: application/json' \
  -d '{"service": "csnp", "input": {"sequence": "MKVLWAALLV", "substitutions": [], "species": "human; id"}}'
```

```json
{
  "type": "about:blank",
  "title": "Unprocessable Content",
  "status": 422,
  "detail": "Request validation failed",
  "errors": [
    { "loc": ["body", "csnp", "input", "substitutions"], "msg": "List should have at least 1 item after validation, not 0", "type": "too_short" },
    { "loc": ["body", "csnp", "input", "species"], "msg": "Value error, The species must be a PANTHER species code of 1 to 5 upper-case letters or digits, such as HUMAN.", "type": "value_error" }
  ]
}
```

The `tools` job runs as before.

`docker compose down` stops the API, and its jobs with it.

## The OpenAPI Schema

`api/openapi.json` is the frontend ↔ api contract: the frontend generates its TypeScript types from it. It must always match what the app serves, and `tests/test_openapi.py` fails when it doesn't.

After any change to a route, a request or response model, or an error response, regenerate it and commit it in the same pull request:

```sh
uv run python -m panther_api.openapi
```

On Windows, the export writes CRLF line endings. Git stores the file with LF (`.gitattributes`), and the test reads it in text mode, so git's "CRLF will be replaced by LF" warning is harmless.

## Tests (pytest)

Tests live in `tests/` and call the app through FastAPI's `TestClient`, so no server needs to be running and no test data is needed.

- **The `client` fixture** in `tests/conftest.py` gives a client for a fresh app.
- **`TestClient` is built on `httpx2`, not `httpx`** (Starlette 1.x). Type a test's responses as `httpx2.Response`; `httpx.Response` fails the type check. `fastapi[standard]` installs both.
- **To test with a throwaway route**, build the app with `create_app(router)` from `panther_api.main`: the router is included under `/api/v1`, like the app's own.
- **No test runs the external tools.** The app reads the tool versions once when it starts, through the engine's `report_tools()`. The autouse `fake_tools` fixture in `tests/conftest.py` replaces it with a report of all four tools at made-up paths, so tests give the same results with or without the tools installed. To test another report, patch `panther_api.versions.report_tools` again in the test, then build the app with `TestClient(create_app())`: the `client` fixture's app has already read the fake. The `api-image` CI job checks the real tools.
- **Share test helpers through their own module,** such as `tests/job_helpers.py`, imported by its bare name (`from job_helpers import ...`). `tests/` has no `__init__.py`, so a test can't import from `conftest.py`.
- **A monkeypatch never reaches a worker process.** Jobs run in `spawn` workers, which import every module afresh. To change what a job does, patch `panther_api.jobs.runner.run_job` with a module-level function from `tests/job_helpers.py`. The pool pickles it by reference, and the workers find it because they inherit the test process's `sys.path`. Anything else a worker needs goes in an environment variable set before the first job, since workers start when the first job is submitted.

Run one file, or one test by name:

```sh
uv run pytest tests/test_health.py
uv run pytest -k "outside_the_prefix"
```
