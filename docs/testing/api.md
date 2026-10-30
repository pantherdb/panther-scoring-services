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
- **It reads the data folder,** `.data/` at the repository root, mounted read-only at `/data` with `PANTHER_DATA_DIR=/data`, as the `engine` service does. `csnp` jobs need the cSNP data sample there: see [The Data Sample](#the-data-sample).
- **Both use port 8000.** Run one at a time.
- **Name the service.** A bare `docker compose up` also runs the `engine` service's checks.
- **To wait for it in a script,** use `curl --retry 30 --retry-all-errors --retry-delay 1 localhost:8000/api/v1/health`. Docker's port proxy accepts the connection before the app listens, so the first requests get an empty reply, not a refused connection, and `--retry-connrefused` doesn't retry them. CI's `api-image` job waits this way.

## Try the Jobs by Hand

There are two jobs: the built-in `tools` job, and `csnp`, which scores coding SNPs ([below](#the-csnp-job)). In a `tools` job, a worker process runs the engine's tool report and returns each tool's version. It checks that the API, the worker pool, the engine and the tools work together. Start the API in the image, so the tools are there, from the repository root:

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
  "versions": { "api": "0.1.0", "engine": "0.1.0", "tools": ["… as GET /api/v1/versions …"], "data": [{ "service": "csnp", "panther": "9" }] }
}
```

`versions.data` names the PANTHER release each service's data comes from: cSNP's frozen PANTHER 9 data. It's the release the engine reads, read from the engine at startup, not a check that the data is there.

What else to try:

- **The worker processes:** `docker compose top api` lists the API's process and, once a job has run, a worker started by `multiprocessing` (`spawn`).
- **Errors:** an unknown `service`, or an `input` with a field it doesn't take, gets a `422` problem listing the field. `GET /api/v1/jobs/not-a-real-id` gets a `404` problem.
- **Natively:** the same steps work against `uv run fastapi dev --port 8000` in `api/`, but every tool's `version` is `null`, because the tools are only in the image.

### The cSNP Job

A `csnp` job scores one protein's substitutions with the engine's PANTHER-PSEP port: a worker runs `blastp` and reads the cSNP data. The input rules are in `openspec/specs/scoring-input/`.

#### The Data Sample

The API reads the cSNP data from `PANTHER_DATA_DIR`, which its workers inherit. The compose `api` service mounts `.data/` there, so fetch the cSNP data sample into `.data/` once (157 MB; running it again downloads nothing), from `engine/`:

```sh
uv run panther-engine csnp sample fetch --data-dir ../.data
```

[engine.md](engine.md#the-csnp-data-sample) says what the sample holds, and how to fetch it through compose instead. Then start the API with `docker compose up --build api`. Without the sample, every `csnp` job fails with the generic `500` described below.

The sample holds 15 of the library's families, but the whole PANTHER9 BLAST database. So a protein whose family isn't in the sample still gets its family, and each substitution gets "Not scored: No PANTHER family for input sequence", as the legacy service said for a family without its library files. The form's example, human APOE, is such a protein: against the sample, its job succeeds with family `PTHR18976` and four of those rows. Use a protein of the sample's families instead, such as the release sample's P26439 below.

#### A Job That Succeeds

The first protein of the release sample, P26439 (family `PTHR10366`), with three of its substitutions. From the repository root:

```sh
sequence=$(sed -n 2p engine/tests/golden/csnp/release/sample.fasta)
curl -si localhost:8000/api/v1/jobs -H 'Content-Type: application/json' \
  -d "{\"service\": \"csnp\", \"input\": {\"sequence\": \"$sequence\", \"substitutions\": [\"A10E\", \"G15D\", \"S213G\"], \"species\": \"HUMAN\"}}"
curl -s localhost:8000/api/v1/jobs/<id>
```

The job takes a few seconds; the first one also starts a worker. Its `result` holds the scores the legacy service gave, as the engine's goldens record them (spec §7.3):

```json
{
  "family": "PTHR10366",
  "scores": [
    { "substitution": "A10E", "age": 220, "message": "possibly damaging", "pdel": "0.50" },
    { "substitution": "G15D", "age": 4200, "message": "probably damaging", "pdel": "0.95" },
    { "substitution": "S213G", "age": 91, "message": "probably benign", "pdel": "0.19" }
  ]
}
```

A substitution that can't be scored is still a row, such as `M1V` with "Not scored: Invalid substitution" and a `null` `age` and `pdel`. A species with no hit, such as `PLAF7` for this protein, gives a `null` `family`.

#### A Job That Fails

A request the API accepts can still fail in its worker, in one of two ways:

- **An input error: `422`.** The engine found a problem with the input as a whole that only it can find, and says what to fix. For `csnp`, that's a sequence `blastp` can't read, such as `1234567890` (divergence 8 in [docs/parity/divergences.md](../parity/divergences.md)). The job's `detail` is the engine's message, as it is:

  ```json
  {
    "status": "failed",
    "result": null,
    "error": {
      "type": "about:blank",
      "title": "Unprocessable Content",
      "status": 422,
      "detail": "The sequence can't be read as a protein sequence. Use one-letter residue codes, such as MKVL."
    }
  }
  ```

- **Anything else: `500`.** A bug, missing data or a `blastp` failure. The job says only "The job hit an unexpected error and could not complete.", and the API's log has the exception with its traceback (`docker compose logs api`). To see one, run a second container without the data, on another port, and submit the P26439 job above to port 8001:

  ```sh
  docker compose run --rm -p 8001:8000 -e PANTHER_DATA_DIR=/nowhere api
  ```

An input error is logged at `INFO`, without a traceback. Uvicorn's logging shows only its own loggers, so it doesn't appear in `docker compose logs api` as the image is configured now.

#### Requests That Are Refused

An invalid request gets the `422` validation problem, which names each failing field and never repeats its value, and no job is created. A `species` must also be one of the 85 species in cSNP's data (`panther_engine.csnp.SPECIES_CODES`): `ZZZZZ` gets "cSNP scoring has no sequences for this species. …" on `species`. Here `species` isn't a species code and `substitutions` is empty:

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
    { "loc": ["body", "csnp", "input", "species"], "msg": "The species must be a PANTHER species code of 1 to 5 upper-case letters or digits, such as HUMAN.", "type": "value_error" }
  ]
}
```

`docker compose down` stops the API, and its jobs with it.

## The OpenAPI Schema

`api/openapi.json` is the frontend ↔ api contract: the frontend generates its TypeScript types from it. It must always match what the app serves, and `tests/test_openapi.py` fails when it doesn't.

After any change to a route, a request or response model, or an error response, regenerate it and commit it in the same pull request:

```sh
uv run python -m panther_api.openapi
```

On Windows, the export writes CRLF line endings. Git stores the file with LF (`.gitattributes`), and the test reads it in text mode, so git's "CRLF will be replaced by LF" warning is harmless.

## Tests (pytest)

Tests live in `tests/` and call the app through FastAPI's `TestClient`, so no server needs to be running. Only the tests in `tests/test_csnp_scoring.py` need the tools and data; see [Tests With the Tools and Data](#tests-with-the-tools-and-data).

- **The `client` fixture** in `tests/conftest.py` gives a client for a fresh app.
- **`TestClient` is built on `httpx2`, not `httpx`** (Starlette 1.x). Type a test's responses as `httpx2.Response`; `httpx.Response` fails the type check. `fastapi[standard]` installs both.
- **To test with a throwaway route**, build the app with `create_app(router)` from `panther_api.main`: the router is included under `/api/v1`, like the app's own.
- **No test runs the external tools,** except those marked `tools` (below). The app reads the tool versions once when it starts, through the engine's `report_tools()`. The autouse `fake_tools` fixture in `tests/conftest.py` replaces it with a report of all four tools at made-up paths, so tests give the same results with or without the tools installed. To test another report, patch `panther_api.versions.report_tools` again in the test, then build the app with `TestClient(create_app())`: the `client` fixture's app has already read the fake. The `api-image` CI job checks the real tools.
- **Share test helpers through their own module,** such as `tests/job_helpers.py`, imported by its bare name (`from job_helpers import ...`). `tests/` has no `__init__.py`, so a test can't import from `conftest.py`.
- **A monkeypatch never reaches a worker process.** Jobs run in `spawn` workers, which import every module afresh. To change what a job does, patch `panther_api.jobs.runner.run_job` with a module-level function from `tests/job_helpers.py`. The pool pickles it by reference, and the workers find it because they inherit the test process's `sys.path`. Anything else a worker needs goes in an environment variable set before the first job, since workers start when the first job is submitted. `score_with_a_fake_engine` in `tests/job_helpers.py` runs the real `run_job` with the engine's `score()` replaced in the worker, so a `csnp` job succeeds without BLAST+ or data.

Run one file, or one test by name:

```sh
uv run pytest tests/test_health.py
uv run pytest -k "outside_the_prefix"
```

### Tests With the Tools and Data

`tests/test_csnp_scoring.py` runs real `csnp` jobs end to end: the API, a `spawn` worker, the engine, `blastp` and the cSNP data sample. It submits the release sample's three proteins with their substitutions, and checks each job's scores against the engine's goldens (`engine/tests/golden/csnp/`, spec §7.3). It also checks a species with no hit and a sequence `blastp` can't read.

Its tests are marked as the engine's are, `tools("blastp")` and `data("csnp")` (`tests/markers.py`):

- **Where `blastp` or the sample is missing,** they're skipped with the reason, as natively on Windows and in CI's `api` job. CI's `api-image` job runs a real `csnp` job against the image instead.
- **With `PANTHER_REQUIRE_TOOLS=1` and `PANTHER_REQUIRE_DATA=1`,** missing tools or data fail them.
- **The data folder is `PANTHER_DATA_DIR`,** or `.data/` at the repository root.

To run the whole suite with them, in the API image, which has `blastp` and uv but not the dev tools: from the repository root, with the sample in `.data/`:

```sh
docker build --target api -t panther-api .
docker run --rm -v "$PWD/api:/src/api:ro" -v "$PWD/engine:/src/engine:ro" -v "$PWD/.data:/data:ro" \
  -e PANTHER_DATA_DIR=/data -e PANTHER_REQUIRE_TOOLS=1 -e PANTHER_REQUIRE_DATA=1 \
  -e UV_PROJECT_ENVIRONMENT=/tmp/venv -e UV_CACHE_DIR=/tmp/uv-cache -e PYTHONDONTWRITEBYTECODE=1 \
  -w /src/api panther-api sh -c 'uv sync --locked -q && uv run --no-sync pytest -p no:cacheprovider'
```

It installs the dev tools into the container's `/tmp`, and writes nothing to the mounts. The five real jobs take about a minute and a half.

In Git Bash, start the `docker run` line with `MSYS_NO_PATHCONV=1`. Otherwise Git Bash rewrites container paths such as `/data` into Windows paths, and every `csnp` job fails with the generic error.
