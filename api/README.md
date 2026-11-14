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
| `GET /api/v1/versions` | The API, engine, external tool and data versions, read once at startup |
| `POST /api/v1/jobs` | Starts a job (`{"service": ..., "input": {...}}`). Returns `202`, the job, and its path in `Location` |
| `GET /api/v1/jobs/{job_id}` | The job: `queued`, `running`, `succeeded` with its `result`, or `failed` with an `error` |
| `GET /api/v1/csnp/species` | The 85 species a `csnp` job's `species` may name, each `{"code", "name"}`, such as `{"code": "HUMAN", "name": "Homo sapiens"}`, in the engine's order. Read from the engine, so it needs no data; cacheable for an hour |
| `/api/v1/docs`, `/api/v1/openapi.json` | The interactive docs and the schema |

Every error is an RFC 9457 problem-details body (`application/problem+json`).

Two limits protect a public API: a request body over 16 MiB gets a `413` before it's parsed, and a job that would wait behind 50 others gets a `503` with `Retry-After`. Both are settings. A frontend on another origin, such as GitHub Pages, needs `PANTHER_API_CORS_ORIGINS`, empty by default, which adds no CORS. At startup, the API logs an error for each service whose data is missing, `csnp` or `refmap`, and starts anyway.

The log goes to standard error, one line per record with a UTC timestamp, at the level `PANTHER_API_LOG_LEVEL` sets, `INFO` by default. Each job gets one line when it finishes, with its size, status and times, never what was submitted. Health checks, successful polls and accepted submissions are left out of the request log below `DEBUG`.

Jobs run in a pool of worker processes and are kept in memory, so a restart loses them. The finished jobs' results share a memory budget, `PANTHER_API_RESULTS_BUDGET_MIB`; over it, the largest expire first. There are three:

- **`csnp`** (`{"sequence", "substitutions", "species"}`) scores coding SNPs in one protein with the engine's PANTHER-PSEP port. It needs `blastp` and the cSNP data, in the folder `PANTHER_DATA_DIR` names; the compose `api` service mounts `.data/` there. A sequence the engine can't read fails the job with a `422` and the engine's message; any other error fails it with a generic `500`.
- **`refmap`** (`{"organism", "ids"}`) maps up to 100,000 protein IDs to PANTHER IDs for one organism, with the engine's port of `map_panther.pl`. It needs the refmap data in the same folder. `GET /api/v1/refmap/organisms` lists the organisms it maps for. Its result is kept as the JSON its worker made.
- **`tools`**, built in, reports the external tools' versions from a worker.

A fourth, **`hmmscore`** (`{"sequence"}`), scores one protein against PANTHER's HMM library. Its request is validated, its residues checked against `PANTHER_API_HMMSCORE_MAX_RESIDUES` (10,000 by default), but a valid one gets a `501` problem, "HMM scoring isn't available yet.", and no job, until the engine's port of `scoreAlignXml.cgi` is wired in (`openspec/changes/add-hmmscore-job/`). At most `PANTHER_API_HMMSCORE_MAX_RUNNING` hmmscore jobs will run at once, 1 by default.

To try them, and to get the data sample, see "Try the Jobs by Hand" in [docs/testing/api.md](../docs/testing/api.md). The settings (`PANTHER_API_*`) are listed there too. `GET /api/v1/versions` and every job also name the PANTHER release each service's data comes from: PANTHER 9 for `csnp`.

## Layout

```text
src/panther_api/
  main.py        create_app(): the /api/v1 router, the error handlers, CORS, the body limit, and the
                 startup that reads the settings, sets up the log, reads the versions, checks
                 each service's data, and starts the job runner
  prefix.py      API_PREFIX, /api/v1
  settings.py    the PANTHER_API_* settings, read once at startup
  logs.py        the log's format and level, for the API's records and Uvicorn's, and the
                 filter that leaves routine requests out of the access log
  limits.py      the middleware that refuses a body over the limit with a 413
  cors.py        CORS for the origins in PANTHER_API_CORS_ORIGINS, or none
  problems.py    problem-details errors, and how the schema documents them. A 422 lists at
                 most the first 100 field errors
  versions.py    the Versions model, read from the engine
  jobs/          the job models, the in-memory store, the worker-pool runner, and work.py:
                 what the workers run. A scoring service joins by adding its request,
                 result and case there; one not ported yet also gets a row in UNAVAILABLE,
                 for its 501. fields.py holds the input shapes more than one service checks
  openapi.py     writes openapi.json: uv run python -m panther_api.openapi
  routers/       one module per area; each is one include_router line in create_app(). csnp.py
                 holds cSNP's species list, and refmap.py refmap's organism list
tests/           pytest with FastAPI's TestClient; conftest.py fakes the engine's tool report,
                 and job_helpers.py the work that runs in the workers. test_csnp_scoring.py
                 runs real csnp jobs where blastp and the data sample are there, and
                 test_refmap_data.py real refmap jobs where the refmap data is (markers.py)
openapi.json     the committed schema; a test fails when it's out of date
```

## Working on It

- **Before a pull request,** from `api/`: `uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest`.
- **After any change to a route or model,** regenerate the schema with `uv run python -m panther_api.openapi`, and commit `openapi.json` in the same pull request.
- **Never echo submitted values in an error.** Some Pydantic messages quote the input; `union_tag_invalid`, for an unknown `service`, does. `problems.py` rewrites the ones found so far. Test each new request model with a distinctive invalid value, and check that it isn't in the body.
- **Plan changes in [`openspec/`](../openspec/).** No new dependency without a proposal.

## More

- [CLAUDE.md](CLAUDE.md): the API's rules and traps, for anyone, or any assistant, changing it.
- [docs/testing/api.md](../docs/testing/api.md): every command, and how the tests are set up.
- [docs/design/api-stack.md](../docs/design/api-stack.md): the tooling (Accepted). [docs/design/tech-stack.md](../docs/design/tech-stack.md): the API's architecture, such as jobs and worker processes (Proposed).
- [openspec/specs/api-service/spec.md](../openspec/specs/api-service/spec.md): the behaviour every endpoint shares.
