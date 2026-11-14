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
- `http://localhost:8000/api/v1/csnp/species` returns the species a `csnp` job accepts, with their names. See [The Species List](#the-species-list).
- `http://localhost:8000/api/v1/refmap/organisms` returns the organisms a `refmap` job maps for, with their names and gene counts. See [The Organism List](#the-organism-list).
- `http://localhost:8000/api/v1/docs` is the interactive documentation.
- `http://localhost:8000/api/v1/openapi.json` is the schema.
- `POST http://localhost:8000/api/v1/jobs` starts a job, and `GET http://localhost:8000/api/v1/jobs/{id}` polls it. See [Try the Jobs by Hand](#try-the-jobs-by-hand).

## Settings

The API reads its settings from environment variables when it starts. An invalid value stops it from starting, with an error naming the variable.

| Variable | Default | Valid | What it sets |
| -------- | ------- | ----- | ------------ |
| `PANTHER_API_JOB_WORKERS` | `2` | an integer ≥ 1 | Worker processes that run jobs. Jobs beyond that wait as `queued` |
| `PANTHER_API_JOB_EXPIRY_SECONDS` | `86400` (24 hours) | an integer ≥ 1 | How long a finished job is kept. After that, polling it gets a 404 |
| `PANTHER_API_RESULTS_BUDGET_MIB` | `256` | an integer ≥ 1 | The memory the finished jobs' results may take, in MiB, each counted by the size of its JSON. When a finishing job takes them over it, the largest results expire first, the oldest first among equal sizes, before their time; failed jobs free nothing, so they stay. A result larger than the budget on its own is still kept, after every other result. See [Limits](#limits) |
| `PANTHER_API_MAX_QUEUED_JOBS` | `50` | an integer ≥ 0 | Jobs that may wait, for a worker or for their service's cap on running jobs. Past that, a submission that would wait gets a `503` and no job is created. See [Limits](#limits) |
| `PANTHER_API_MAX_BODY_BYTES` | `16777216` (16 MiB) | an integer ≥ 1 | The largest request body accepted. A larger one gets a `413`. See [Limits](#limits) |
| `PANTHER_API_CORS_ORIGINS` | empty | comma-separated origins, such as `https://pantherdb.github.io`: a scheme and host, with no path, `*` or trailing `/` | The browser origins allowed to call the API from another site. Empty adds no CORS headers. See [CORS](#cors) |
| `PANTHER_API_LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING` or `ERROR`, in any case | The lowest level logged. See [Logs](#logs) |
| `PANTHER_API_HMMSCORE_MAX_RESIDUES` | `10000` | an integer from 1 to 10,000 | The most residues an `hmmscore` sequence may have, counting every position `hmmscan` reads but a final `*`. A longer one gets a `422` naming the limit. 10,000 is the product owner's limit, and the most allowed ([divergence 11](../parity/divergences.md)) |
| `PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS` | `720` | an integer ≥ 1 | How long one `hmmscore` job may run. Takes effect when hmmscore's scoring is wired in |
| `PANTHER_API_HMMSCORE_MAX_RUNNING` | `1` | an integer ≥ 1 | `hmmscore` jobs that may run at once. More wait as `queued`, without holding a worker, so other services' jobs still run. They count toward `PANTHER_API_MAX_QUEUED_JOBS` |
| `PANTHER_API_HMMSCORE_CPU` | `0` | an integer ≥ 0 | `hmmscan`'s `--cpu` for each `hmmscore` job. Takes effect when hmmscore's scoring is wired in |

Set one for the native dev server with, for example, `PANTHER_API_JOB_WORKERS=1 uv run fastapi dev --port 8000`, and for the image with `docker run -e PANTHER_API_JOB_WORKERS=1 …`. The compose `api` service sets none, so it uses the defaults. Jobs are kept in memory, and are lost when the API restarts.

The four `hmmscore` settings' defaults are starting points: the server sets its own once they're measured there with the full library (#68). The time limit's 720 s is scaled from the [library survey](../parity/hmmscore-library-survey.md)'s times, since no 10,000-residue query was measured (`add-hmmscore-job`, design.md, decision 5). Until hmmscore's scoring is wired in, a valid `hmmscore` request gets a `501` ([The hmmscore Job](#the-hmmscore-job)), so only the residue limit acts yet. The running cap is in the job runner, ready for the first `hmmscore` job; the time limit and `--cpu` take effect with the wiring.

At startup, the API checks each service's data with the engine's `check_data()`: the cSNP data and the refmap data. If `PANTHER_DATA_DIR` isn't set, or the folder lacks part of a service's data, it logs an error for that service, such as `csnp jobs will fail until the cSNP data is in place: the cSNP data folder … lacks: …` or `refmap jobs will fail until the refmap data is in place: the refmap data folder … lacks 1,534 of 1,534 files: …`, and starts anyway: everything but that service's jobs works without it. The checks are independent, so one service's missing data doesn't stop the other's jobs. Natively without the data, expect both lines.

### CORS

A frontend on another origin, such as the GitHub Pages site, needs `PANTHER_API_CORS_ORIGINS` set to its origin. Set, a request or preflight from a listed origin gets `Access-Control-Allow-Origin`, with `GET`, `POST` and `Content-Type` allowed and `Location` and `Retry-After` exposed; other origins get none, and no credentials are ever allowed. A `413` carries the headers too. To see it:

```bash
PANTHER_API_CORS_ORIGINS=https://pantherdb.github.io uv run fastapi dev --port 8000
curl -si -X OPTIONS http://localhost:8000/api/v1/jobs -H 'Origin: https://pantherdb.github.io' -H 'Access-Control-Request-Method: POST' | grep -i access-control
```

### Limits

Three limits protect the API's memory and its queue. The first two answer with problem details, in fixed text that never repeats the request:

- **A body over `PANTHER_API_MAX_BODY_BYTES` gets a `413`,** "The request body is larger than the API accepts, 16,777,216 bytes.", before it's parsed. A `Content-Length` over the limit is refused without reading the body; a body without one is refused as soon as it passes the limit. The default fits the largest valid request, a `refmap` job of 100,000 IDs of 64 characters, about 13 MB of JSON.
- **A job that would wait past `PANTHER_API_MAX_QUEUED_JOBS` gets a `503`,** "Too many jobs are waiting to run. Try again later.", with `Retry-After: 30`, and no job is created. Up to `PANTHER_API_JOB_WORKERS` jobs run, and up to the cap wait. A job waiting for its service's cap on running jobs, such as a second `hmmscore` job with `PANTHER_API_HMMSCORE_MAX_RUNNING` at 1, counts as waiting, though a worker is free; a job that runs at once on the free worker is never refused. So with the defaults, 51 `hmmscore` jobs are taken, 1 running and 50 waiting, and a `csnp` job still runs beside them. A request is validated first, so an invalid one is still a `422`.
- **The finished jobs' results fit in `PANTHER_API_RESULTS_BUDGET_MIB`.** Each result is counted by the size of its JSON when its job finishes: about 4 MB for a `refmap` job of 100,000 IDs, a few kilobytes for a `csnp` job. A failed job counts nothing, and stays until its time. When a finishing job takes the total over the budget, the largest results expire first, the oldest first among equal sizes, before their 24 hours, so a burst of large jobs expires its own results rather than everyone's small ones. Polling an expired job gets the `404` any expired job gets. The default, 256 MiB, holds about 50 of the largest `refmap` jobs; the server sets the value that suits it. A `refmap` result is kept as the JSON its worker made, and a poll returns those bytes as they are.

To see the `503`, start the dev server with one worker and no waiting allowed, then submit two `tools` jobs at once:

```sh
PANTHER_API_JOB_WORKERS=1 PANTHER_API_MAX_QUEUED_JOBS=0 uv run fastapi dev --port 8000
for i in 1 2; do curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/v1/jobs -H 'Content-Type: application/json' -d '{"service": "tools", "input": {}}'; done
```

The first gets `202`; the second gets `503` if it arrives while the first is still running, as it does while the first job starts the worker. To see the `413`, send a body over the limit with `PANTHER_API_MAX_BODY_BYTES=100`.

### Logs

The API writes its log to standard error, one line per record: a UTC timestamp, the level, the logger, and the message. Its own lines and Uvicorn's request lines share the format, from the time the app has started; Uvicorn's first two lines, before that, keep Uvicorn's format. Read it with `docker compose logs api`, or `docker logs <container>`. A job's run, at `INFO`:

```text
2026-11-04T17:02:13.415Z INFO uvicorn.access: 172.18.0.1:51230 - "POST /api/v1/jobs HTTP/1.1" 202
2026-11-04T17:02:54.611Z INFO panther_api.jobs.runner: Job 9c1e2f4a-… csnp, HUMAN, 347 residues, 3 substitutions: succeeded, waited 0.0 s, ran 41.2 s
2026-11-04T17:03:10.002Z INFO uvicorn.access: 172.18.0.1:51234 - "POST /api/v1/jobs HTTP/1.1" 422
```

What each level writes:

| Level | What's logged |
| ----- | ------------- |
| `DEBUG` | Everything below, plus a line when each job is submitted, and every request |
| `INFO` | One line per job when it finishes, with its service, the size of its input, its status, its wait and its run time. Every request except the routine ones below |
| `WARNING` | Submissions refused because the queue is full, with the number of jobs and the cap, at most once a minute |
| `ERROR` | A job that failed unexpectedly or whose worker died, and a startup without a service's data |

- **Routine requests are left out below `DEBUG`:** a health check (`GET /api/v1/health`) or a poll (`GET /api/v1/jobs/{id}`) answered with a 2xx. A failed health check, a poll that gets a `404`, and every submission are logged. A submission's line is the only one at `INFO` with the client's address.
- **The client's address is the one the API sees:** behind a proxy, the proxy's, unless Uvicorn trusts the proxy's forwarded headers. `fastapi run` trusts them from `127.0.0.1` only; set `FORWARDED_ALLOW_IPS` to the proxy's address to trust it. That's the server's setting (#34).
- **Uvicorn's `--no-access-log` is respected:** if Uvicorn starts without an access log, the API leaves it off.
- **An unexpected error's traceback is logged once in ten minutes.** While every job fails the same way, such as while the data is missing, the first job's line has the traceback, and each repeat ends `(same error as job <id>, seen <n> times since <time>)`. An error is the same when its type and the place it was raised are, whatever its message: a time limit's message names the limit, which differs from job to job.
- **Refusals at most once a minute.** While the queue stays full, the first refused submission is logged, and the next line, a minute or more later, counts the ones since: `Refused 37 jobs since <time>, the last a csnp job: …`.
- **No submitted values.** A job's line gives sizes and the species or organism code, never a sequence, a substitution or an ID. A rejected value isn't logged either, nor is the engine's message for an input error: the line says `failed 422, the engine couldn't process the input`, and the job has the message. A traceback has the exception's message as the engine raised it; keeping submitted values out of those is the engine's rule.
- **How much:** about 200 bytes a job at `INFO`. `DEBUG` adds a line for every poll, about one a second for each job a browser is waiting on; use it to look into something, then set it back.
- **Its size on a server:** Docker keeps a container's log until the container is removed. Cap it with the `json-file` driver's options, such as `--log-opt max-size=10m --log-opt max-file=5` on `docker run`, or `logging:` in a compose file. That's the server's setting, not the API's.

## Running the API in the Image

The root `Dockerfile`'s `api` stage serves the API with the engine and the pinned external tools, as it will be deployed. Run it from the repository root, not `api/`:

```sh
docker compose up --build api          # build the image and serve on localhost:8000; Ctrl+C stops it
docker compose down                    # remove the container
```

- **It's for the frontend to call,** through its dev proxy, with the real tools: `/api/v1/versions` then reports each tool's pinned version. It has no source mount and no reload, so rerun with `--build` after changing `api/` or `engine/`. Develop the API itself with the native dev server above.
- **It reads the data folder,** `.data/` at the repository root, mounted read-only at `/data` with `PANTHER_DATA_DIR=/data`, as the `engine` service does. `csnp` jobs need the cSNP data sample there, and `refmap` jobs the refmap data: see [The Data Sample](#the-data-sample) and [The refmap Data](#the-refmap-data).
- **Both use port 8000.** Run one at a time.
- **Name the service.** A bare `docker compose up` also runs the `engine` service's checks.
- **To wait for it in a script,** use `curl --retry 30 --retry-all-errors --retry-delay 1 localhost:8000/api/v1/health`. Docker's port proxy accepts the connection before the app listens, so the first requests get an empty reply, not a refused connection, and `--retry-connrefused` doesn't retry them. CI's `api-image` job waits this way.

## Try the Jobs by Hand

There are three jobs: the built-in `tools` job, `csnp`, which scores coding SNPs ([below](#the-csnp-job)), and `refmap`, which maps protein IDs to PANTHER IDs ([The refmap Job](#the-refmap-job)). An `hmmscore` request is validated, then refused with a `501` until its scoring is ported ([The hmmscore Job](#the-hmmscore-job)). In a `tools` job, a worker process runs the engine's tool report and returns each tool's version. It checks that the API, the worker pool, the engine and the tools work together. Start the API in the image, so the tools are there, from the repository root:

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
  "versions": { "api": "0.1.0", "engine": "0.1.0", "tools": ["… as GET /api/v1/versions …"], "data": [] }
}
```

`GET /api/v1/versions` lists, in `data`, the PANTHER release each service's data comes from: cSNP's frozen PANTHER 9 data and refmap's PANTHER 19. It's the release the engine reads, read from the engine at startup, not a check that the data is there. A job's `versions.data` has only its own service's entry, such as `[{ "service": "refmap", "panther": "19" }]` for a `refmap` job, and a `tools` job, which reads no data, has none.

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

The sample holds 16 of the library's families, but the whole PANTHER9 BLAST database. So a protein whose family isn't in the sample still gets its family, and each substitution gets "Not scored: No PANTHER family for input sequence", as the legacy service said for a family without its library files. Use a protein of the sample's families, such as the release sample's P26439 below, or the form's example, human APOE (`PTHR18976`), whose scores from the legacy scripts are in `engine/tests/golden/csnp/example/apoe.out`.

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

- **Anything else: `500`.** A bug, missing data or a `blastp` failure. The job says only "The job hit an unexpected error and could not complete.", and the API's log has the job's line with the exception's traceback (`docker compose logs api`). To see one, run a second container without the data, on another port, and submit the P26439 job above to port 8001:

  ```sh
  docker compose run --rm -p 8001:8000 -e PANTHER_DATA_DIR=/nowhere api
  ```

Both are logged as the job's one line ([Logs](#logs)): an input error at `INFO`, as `failed 422, the engine couldn't process the input`, without the engine's message or a traceback; anything else at `ERROR`, with the traceback the first time in ten minutes.

#### The Species List

`GET /api/v1/csnp/species` lists the 85 species a `csnp` job's `species` may name, with their scientific names, in the engine's order (`panther_engine.csnp.SPECIES_NAMES`). The form's species dropdown reads it. It needs no data, so it works natively too:

```sh
curl -si localhost:8000/api/v1/csnp/species
```

It starts like this, and goes on for 83 more, `{"code": "HUMAN", "name": "Homo sapiens"}` among them:

```json
[
  { "code": "ANOCA", "name": "Anolis carolinensis" },
  { "code": "ANOGA", "name": "Anopheles gambiae" },
  "…"
]
```

The response has `Cache-Control: public, max-age=3600`: the list changes only with a new image. The request's `species` stays a plain string in the schema, with no enum; the API checks it against the same codes (`add-csnp-species-list`, design.md, decision 2).

#### Requests That Are Refused

An invalid request gets the `422` validation problem, which names each failing field and never repeats its value, and no job is created. A `species` must also be one of the 85 species in cSNP's data (`panther_engine.csnp.SPECIES_CODES`, the codes [the species list](#the-species-list) gives): `ZZZZZ` gets "cSNP scoring has no sequences for this species. …" on `species`. Here `species` isn't a species code and `substitutions` is empty:

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

### The refmap Job

A `refmap` job maps protein IDs, such as UniProt accessions, to PANTHER IDs for one organism, with the engine's port of `map_panther.pl`: a worker reads the organism's classification file. Its contract and input rules are in `openspec/specs/scoring-jobs/` and `openspec/specs/scoring-input/`.

#### The refmap Data

The API reads the refmap data, PANTHER 19's generic mapping release, from `PANTHER_DATA_DIR`, under `refmap/19/`: one classification file per organism, and `stats`, 1,534 files, 523 MB. The compose `api` service mounts `.data/` there, so fetch the data into `.data/` once, from `engine/`. It downloads 157 MB; run again, it downloads nothing and checks the files:

```sh
uv run panther-engine refmap data fetch --data-dir ../.data
uv run panther-engine refmap data verify --data-dir ../.data    # checks every file against the manifest
```

Without it, every `refmap` job fails with the generic `500`, and the API logs why at startup ([Settings](#settings)).

#### The Organism List

`GET /api/v1/refmap/organisms` lists the 1,533 organisms a `refmap` job's `organism` may name, in the engine's order (by code), each with its name and its gene counts: the genes in its classification file, and how many of them have a PANTHER ID. The form's organism selector reads it. It needs no data, so it works natively too:

```sh
curl -si localhost:8000/api/v1/refmap/organisms
```

ENDPU's entry is among them:

```json
{ "code": "ENDPU", "name": "Endocarpon pusillum", "genes": 9228, "genes_with_panther_id": 7665 }
```

The response has `Cache-Control: public, max-age=3600`: the list changes only with a new image. PANTHER's own 143 genomes, such as `HUMAN`, aren't in the generic mapping data, so they aren't listed (#52).

#### A Job That Maps

The form's example, six IDs from the release's own test list for the lichen *Endocarpon pusillum*, from the repository root:

```sh
curl -si localhost:8000/api/v1/jobs -H 'Content-Type: application/json' \
  -d '{"service": "refmap", "input": {"organism": "ENDPU", "ids": ["U1G4Q5", "U1GCA1", "U1HRR6", "U1GLV9", "U1GJ40", "U1HQ27"]}}'
curl -s localhost:8000/api/v1/jobs/<id>
```

The job takes under a second once a worker has started. Its `result` names the organism, and gives one mapping per ID, in the order submitted, as `map_panther.pl` gives them (`engine/tests/golden/refmap/out/test_geneList.out`): three subfamilies, two families, and an ID with no PANTHER ID, whose `panther_id` is `null` where the legacy service said `NOHIT`:

```json
{
  "organism": "ENDPU",
  "mappings": [
    { "id": "U1G4Q5", "panther_id": "PTHR11360:SF130" },
    { "id": "U1GCA1", "panther_id": "PTHR21058:SF0" },
    { "id": "U1HRR6", "panther_id": "PTHR42765:SF2" },
    { "id": "U1GLV9", "panther_id": "PTHR28011" },
    { "id": "U1GJ40", "panther_id": "PTHR13401" },
    { "id": "U1HQ27", "panther_id": null }
  ]
}
```

Each ID is looked up exactly as given, not trimmed or upper-cased, and a repeated ID gets a mapping each time. An ID the organism doesn't have is a `null` mapping, not an error. A job of 100,000 IDs runs in about 3 seconds, and its result is kept as about 4 MB of JSON, within the results budget ([Limits](#limits)).

#### Requests That Are Refused (refmap)

An invalid request gets the `422` validation problem, without the submitted values, and no job is created. `organism` must be one of the codes [the organism list](#the-organism-list) gives (`panther_engine.refmap.ORGANISM_CODES`): `HUMAN`, though of the right shape, gets "The organism must be the code of an organism refmap maps for, such as ENDPU." on `organism`. Each of `ids` must be 1 to 64 printable ASCII characters with no whitespace, and there can be up to 100,000.

A `422` lists at most the first 100 failing fields, for any service; when there are more, its `detail` says how many there were in all, such as "Request validation failed: 100,000 fields are invalid, and the first 100 are listed." A list of 100,000 bad IDs is checked in one pass, so its `422` takes about as long as a valid list's (#41). Here the organism is `HUMAN` and the second ID holds two:

```sh
curl -si localhost:8000/api/v1/jobs -H 'Content-Type: application/json' \
  -d '{"service": "refmap", "input": {"organism": "HUMAN", "ids": ["P04217", "P04217 P01023"]}}'
```

```json
{
  "type": "about:blank",
  "title": "Unprocessable Content",
  "status": 422,
  "detail": "Request validation failed",
  "errors": [
    { "loc": ["body", "refmap", "input", "organism"], "msg": "The organism must be the code of an organism refmap maps for, such as ENDPU.", "type": "value_error" },
    { "loc": ["body", "refmap", "input", "ids", 1], "msg": "Each ID must be 1 to 64 printable ASCII characters, with no spaces, such as P04217.", "type": "value_error" }
  ]
}
```

### The hmmscore Job

An `hmmscore` job will score one protein against PANTHER's HMM library, with the engine's port of `scoreAlignXml.cgi`. Its contract is settled (`openspec/changes/add-hmmscore-job/`) and its input rules are in `openspec/changes/add-hmmscore-job/specs/scoring-input/spec.md` until the change is archived, but the engine doesn't score yet. So a valid request gets a `501` problem, and no job is created. It needs no data, so it works natively too:

```sh
curl -si localhost:8000/api/v1/jobs -H 'Content-Type: application/json' \
  -d '{"service": "hmmscore", "input": {"sequence": ">sp|P02649|APOE_HUMAN\nMKVLWAALLVTFLAGCQAKV"}}'
```

```json
{
  "type": "about:blank",
  "title": "Not Implemented",
  "status": 501,
  "detail": "HMM scoring isn't available yet."
}
```

An invalid request still gets the `422` validation problem first, without the submitted sequence. The sequence is normalised as a `csnp` one is: trimmed, one FASTA header removed, whitespace removed and upper-cased. Then it may hold only letters, `.`, `_`, `~` and `*`, which HMMER 3.1b2 and 3.4 score alike, and at least one letter; one with none gets "The sequence has no residues." Anything else, such as `-` or a digit, is refused ([divergence 12](../parity/divergences.md)). It may have at most `PANTHER_API_HMMSCORE_MAX_RESIDUES` residues, 10,000 by default, counting every character but a final `*`; a longer one gets "The sequence has more than 10,000 residues." Here the sequence has a digit:

```sh
curl -si localhost:8000/api/v1/jobs -H 'Content-Type: application/json' \
  -d '{"service": "hmmscore", "input": {"sequence": "MKVLWAALLV1TFLAGCQAKV"}}'
```

```json
{
  "type": "about:blank",
  "title": "Unprocessable Content",
  "status": 422,
  "detail": "Request validation failed",
  "errors": [
    { "loc": ["body", "hmmscore", "input", "sequence"], "msg": "The sequence must be one-letter residue codes, the letters A to Z, and may also hold . _ ~ and *. Remove any -, digit, other punctuation or other character.", "type": "value_error" }
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

Tests live in `tests/` and call the app through FastAPI's `TestClient`, so no server needs to be running. Only the tests in `tests/test_csnp_scoring.py` and `tests/test_refmap_data.py` need the tools or data; see [Tests With the Tools and Data](#tests-with-the-tools-and-data).

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

`tests/test_csnp_scoring.py` runs real `csnp` jobs end to end: the API, a `spawn` worker, the engine, `blastp` and the cSNP data sample. It submits the release sample's three proteins with their substitutions, and checks each job's scores against the engine's goldens (`engine/tests/golden/csnp/`, spec §7.3). It submits the form's example, human APOE, as the form sends it, and checks its four scores against the legacy scripts' (`example/apoe.out`). It also checks a species with no hit and a sequence `blastp` can't read.

`tests/test_refmap_data.py` runs real `refmap` jobs against the refmap data: the form's example, checked against `map_panther.pl`'s golden, and a job of 100,000 of ARAVE's own IDs, checked against the engine, whose kept result must stay under 8 MB and whose poll must take under 2 seconds. It needs no tools. `tests/test_refmap_jobs.py` runs the same kind of jobs everywhere, against a made-up data folder holding only ENDPU's file, written from the golden.

Their tests are marked as the engine's are, `tools("blastp")`, `data("csnp")` and `data("refmap")` (`tests/markers.py`):

- **Where `blastp` or the data is missing,** they're skipped with the reason, as natively on Windows and in CI's `api` job. CI's `api-image` job runs the `refmap` data tests in the image on both architectures. On amd64, it also runs the real `csnp` jobs with the image's tools and data, with both set, so a change that breaks the example or a sample protein fails CI. It runs the command below, so it tests the checkout's `api/` and `engine/`, not the packages the image ships.
- **With `PANTHER_REQUIRE_TOOLS=1` and `PANTHER_REQUIRE_DATA=1`,** missing tools or data fail them.
- **The data folder is `PANTHER_DATA_DIR`,** or `.data/` at the repository root.

To run the whole suite with them, with the API image's tools, which has `blastp` and uv but not the dev tools: from the repository root, with the cSNP sample and the refmap data in `.data/`:

```sh
docker build --target api -t panther-api .
docker run --rm -v "$PWD/api:/src/api:ro" -v "$PWD/engine:/src/engine:ro" -v "$PWD/.data:/data:ro" \
  -e PANTHER_DATA_DIR=/data -e PANTHER_REQUIRE_TOOLS=1 -e PANTHER_REQUIRE_DATA=1 \
  -e UV_PROJECT_ENVIRONMENT=/tmp/venv -e UV_CACHE_DIR=/tmp/uv-cache -e PYTHONDONTWRITEBYTECODE=1 \
  -w /src/api panther-api sh -c 'uv sync --locked -q && uv run --no-sync pytest -p no:cacheprovider'
```

It installs the dev tools into the container's `/tmp`, and writes nothing to the mounts. The seven real `csnp` jobs took under a minute on CI, `uv sync` included, and about four minutes on a laptop; the `refmap` ones take a few seconds.

In Git Bash, start the `docker run` line with `MSYS_NO_PATHCONV=1`. Otherwise Git Bash rewrites container paths such as `/data` into Windows paths, and every `csnp` job fails with the generic error.
