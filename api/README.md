# api

The HTTP API for PANTHER's four scoring services (`hmmscore`, `refmap`, `csnp`, `treegrafter`): one FastAPI app, `panther_api`. It imports the engine in [`engine/`](../engine/) as a library, never over HTTP. Its OpenAPI schema is the contract with [`frontend/`](../frontend/README.md) and with the PANTHER website.

## Quick Start

Natively, from `api/`, with uv 0.13.6 or later (`uv self update` if yours is older):

```sh
uv sync                                # .venv from uv.lock, with the dev tools
uv run fastapi dev --port 8000         # dev server with reload
```

Then open <http://localhost:8000/api/v1/docs>. The external tools (BLAST+, HMMER, EPA-ng) are only in the image, so natively `/api/v1/versions` shows each tool's version as `null`.

With the pinned tools, as it's deployed, from the repository root:

```sh
docker compose up --build api          # serves on localhost:8000; no reload
```

## What It Serves

Everything is under `/api/v1`. The current, complete list is the schema in [`openapi.json`](openapi.json), or the interactive docs at `/api/v1/docs`.

| Path | What it returns |
| ---- | --------------- |
| `GET /api/v1/health` | `{"status": "ok"}` while the process can serve requests |
| `GET /api/v1/versions` | The API, engine and external tool versions, read once at startup |
| `POST /api/v1/jobs` | Starts a job (`{"service": ..., "input": {...}}`). Returns `202`, the job, and its path in `Location` |
| `GET /api/v1/jobs/{job_id}` | The job: `queued`, `running`, `succeeded` with its `result`, or `failed` with an `error` |
| `/api/v1/docs`, `/api/v1/openapi.json` | The interactive docs and the schema |

Every error is an RFC 9457 problem-details body (`application/problem+json`).

Jobs run in a pool of worker processes and are kept in memory, so a restart loses them. Until the first scoring service is ported, the only job is the built-in `tools` job, which reports the external tools' versions from a worker. To try it, see "Try the Jobs by Hand" in [docs/testing/api.md](../docs/testing/api.md). The settings (`PANTHER_API_*`) are listed there too.

## Layout

```text
src/panther_api/
  main.py        create_app(): the /api/v1 router, the error handlers, and the startup that reads
                 the settings and versions and starts the job runner
  settings.py    the PANTHER_API_* settings, read once at startup
  problems.py    problem-details errors, and how the schema documents them
  versions.py    the Versions model, read from the engine
  jobs/          the job models, the in-memory store, the worker-pool runner, and work.py:
                 what the workers run. A scoring service joins by adding its request,
                 result and case there
  openapi.py     writes openapi.json: uv run python -m panther_api.openapi
  routers/       one module per area; each is one include_router line in create_app()
tests/           pytest with FastAPI's TestClient; conftest.py fakes the engine's tool report,
                 and job_helpers.py the work that runs in the workers
openapi.json     the committed schema; a test fails when it's out of date
```

## Working on It

- **Before a pull request,** from `api/`: `uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest`.
- **After any change to a route or model,** regenerate the schema with `uv run python -m panther_api.openapi`, and commit `openapi.json` in the same pull request.
- **Never echo submitted values in an error.** Some Pydantic messages quote the input; `union_tag_invalid`, for an unknown `service`, does. `problems.py` rewrites the ones found so far. Test each new request model with a distinctive invalid value, and check that it isn't in the body.
- **Plan changes in [`openspec/`](../openspec/).** No new dependency without a proposal.

## More

- [docs/testing/api.md](../docs/testing/api.md): every command, and how the tests are set up.
- [docs/design/api-stack.md](../docs/design/api-stack.md): the tooling (Accepted). [docs/design/tech-stack.md](../docs/design/tech-stack.md): the API's architecture, such as jobs and worker processes (Proposed).
- [openspec/specs/api-service/spec.md](../openspec/specs/api-service/spec.md): the behaviour every endpoint shares.
