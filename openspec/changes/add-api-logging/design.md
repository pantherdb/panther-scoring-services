# Design

## Context

See proposal.md, Why. The requirements are in this change's `api-service` and `scoring-jobs` deltas.

This change relies on these decisions, and doesn't change them:

- **[tech-stack.md](../../../docs/design/tech-stack.md),** API recommendation 1: jobs run in a pool of `spawn` worker processes, and their state lives on the event loop.
- **[hosting.md](../../../docs/design/hosting.md),** What the Server Provides: the image runs with Docker, and the API's logs are one of the ways to see that it's up.

What the code does today (fastapi 0.162.0, fastapi-cli 0.0.32, uvicorn 0.54.0):

- **`fastapi run`** starts Uvicorn with Uvicorn's `LOGGING_CONFIG` when standard output isn't a terminal, as in the image, and with fastapi-cli's Rich config when it is, as in development. Both configure only the `uvicorn`, `uvicorn.error` and `uvicorn.access` loggers, with `disable_existing_loggers: False` and no `root` key. The access log goes to standard output, everything else to standard error.
- **The root logger has no handler,** so `panther_api`'s records reach Python's last-resort handler, which writes `WARNING` and above, with no timestamp or logger name.
- **Uvicorn's access record** has `args` of `(client_addr, method, path, http_version, status_code)`, and the message `'%s - "%s %s HTTP/%s" %d'`. A protocol decides whether to log access when a connection opens, from `access_logger.hasHandlers()`, which counts ancestors' handlers when the logger propagates.
- **`JobRecord`** already keeps `created_at`, `started_at` and `finished_at`, so a job's wait and run times need no new state.
- **The engine doesn't log,** and its `InputError` messages are fixed text (`csnp/blast.py`), with no user data.

## Goals / Non-Goals

**Goals:**

- One place, `panther_api/logs.py`, that sets up the log, called once per app start.
- The same lines in the image and natively, so what a developer sees is what the server writes.
- A new service can't be added without saying what its submission line shows.

**Non-Goals:**

- Uvicorn's first lines, before the lifespan runs ("Started server process", "Waiting for application startup."), keep Uvicorn's format. See decision 1.
- A line when the API shuts down with jobs still queued. Uvicorn's shutdown lines already show the restart; a count of lost jobs can come later if it's missed.

## Decisions

### 1. Set up the log in the lifespan, on the root logger

`configure_logging(level)` runs first in the lifespan, after the settings are read:

- It puts one handler on the root logger, writing to standard error with the format below, and sets the root's level.
- For `uvicorn`, `uvicorn.error` and `uvicorn.access`, it removes their handlers, sets them to propagate, and sets their level, so their records go through the root's handler too.
- It adds the access filter (decision 3) to `uvicorn.access` when the level isn't `DEBUG`.
- It's idempotent: it replaces the handler and filter it added before, found by their own classes, so each test's app start doesn't stack another. It leaves other handlers on the root alone, so pytest's `caplog` keeps working.

The root, not `panther_api`'s logger, so warnings from libraries, such as asyncio's "Task exception was never retrieved", get the same format.

Alternatives:

- **Uvicorn's `--log-config`.** It would format Uvicorn's first lines too, but `fastapi run` doesn't take it; the image would have to run `uvicorn` directly, and the level would come from a file or Uvicorn's own `--log-level`, not from the API's settings with their validation.
- **At import time, in `main.py`.** It runs before the settings are read, so it can't use `PANTHER_API_LOG_LEVEL`. `fastapi run` also applies Uvicorn's config after importing the app. Uvicorn doesn't touch the root logger, so the root handler would survive, but Uvicorn's own loggers would be reset to their handlers.

### 2. Plain text, with a UTC timestamp

```text
2026-11-04T17:02:54.611Z INFO panther_api.jobs.runner: Job 9c1e… csnp, HUMAN, 347 residues, 3 substitutions: succeeded, waited 0.0 s, ran 41.2 s
2026-11-04T17:03:10.002Z INFO uvicorn.access: 172.18.0.1:51234 - "POST /api/v1/jobs HTTP/1.1" 422
```

- **UTC,** written with a `Z`, since the server's time zone is unknown and job times in the API are UTC.
- **Plain text, not JSON.** The log is read with `docker logs` and `grep` for now. JSON can replace the formatter later without touching any `logger` call.
- **Standard error for everything,** the access log included, so the two can't interleave out of order through separate buffers.
- In development, this replaces fastapi-cli's coloured Rich output. One format everywhere is worth more than the colour.

### 3. Leave routine requests out of the access log

A `logging.Filter` on `uvicorn.access` drops a record for `GET /api/v1/health`; for `GET /api/v1/jobs/{id}` with a 2xx status; and for `POST /api/v1/jobs` with `202`. It reads the record's `args` tuple, ignores a query string, and keeps any record whose `args` isn't the 5-tuple it expects, so a change in Uvicorn's record logs too much, not too little.

- **A 404 poll stays:** a client polling an expired or wrong id is worth seeing. So does a `422`, `413`, `501` or `503` submission.
- **An accepted submission goes:** its job's finish line says more.
- **Health checks go,** since a proxy or Docker health check may call it every few seconds.
- **At `DEBUG` nothing is dropped,** for following one client's polls.

Alternative: **an access log middleware of our own,** with Uvicorn's turned off. It would control the line fully, but duplicates what Uvicorn does, and `fastapi run` would need `--no-access-log`, which it doesn't take.

### 4. The runner writes the job lines

`JobRunner` logs, so every route that submits a job gets them:

- **Finished,** once, at the end of `_run()`, from the job's own timestamps, with `request.input.log_summary()`: `INFO` for a success or an `InputError`, `ERROR` for anything else, with the traceback when decision 7 says so. This replaces the three failure lines `_run()` has now, so each job has exactly one line at `INFO`.
- **Submitted,** in `submit()` after the job is stored, at `DEBUG`: the id, the service and the summary.
- **Refused,** in `submit()` before raising `QueueFullError`: `WARNING`, with the service, the number of unfinished jobs and the cap. The router doesn't log it again.

One line per job, written at the end, means a job that never finishes leaves no line at `INFO`. Jobs only stop finishing if workers hang, and then the queue-full warnings show it; `DEBUG` shows each submission while that's looked into.

The job id is in the log, as it is today. Anyone who can read the log can fetch that job's result while it's kept; the log is for the people who run the server.

### 5. Each service's input says what it logs

Each input model gets `log_summary() -> str`: `CsnpInput` gives the species, the sequence's length and the number of substitutions; `RefmapInput` the organism and the number of IDs; `ToolsInput` an empty string. Because `JobRequest` is a union, basedpyright fails `request.input.log_summary()` if a new service's input lacks the method.

`refmap` jobs aren't created yet (`501`), so its summary is written now but only logged once its wiring lands (#40).

Alternative: **a `match` on the request in the runner.** It puts every service's fields in one place away from the models, and a missing case passes the type check.

### 6. The level is a setting like the others

`Settings.log_level`, a `Literal["DEBUG", "INFO", "WARNING", "ERROR"]` with a before-validator that upper-cases a string, so `debug` works and `LOUD` stops the API. `CRITICAL` isn't offered: the API logs nothing at that level, so it would silence the log.

### 7. A repeated error's traceback once in ten minutes

`jobs/runner.py` keeps a small table of the unexpected errors seen recently, keyed by the exception's type and message. For a job that fails unexpectedly:

- **A new key, or one first seen more than ten minutes ago:** the finish line has the traceback (`exc_info`), and the table records this job's id, the time and a count of 1.
- **A key seen within ten minutes:** the line has no traceback, and ends "same error as job 9c1e…, seen 12 times since 17:02:13Z".
- Entries older than ten minutes are dropped whenever one is added, so the table stays small.

A dead worker is keyed like any other error, by `BrokenProcessPool` and its message.

The table lives on the event loop, like the rest of the runner's state, so needs no lock. Its times are the jobs' own `finished_at`, from `store.utcnow`, so a test steps past ten minutes with the `Clock` it already patches there.

Alternatives:

- **A filter on the handler that drops repeated records.** It would hide the job's line itself, not only its traceback, and lose which job failed.
- **Never log tracebacks, only messages.** The first one is what someone debugging needs.

## Risks / Trade-offs

- **[A future log line includes user data]** → `api/CLAUDE.md` gets the rule, next to "Never echo a submitted value in an error", and a test runs a job with distinctive values and asserts none is in the captured log.
- **[A Uvicorn upgrade changes the access record]** → the filter keeps records it doesn't recognise, and the tests of the access log serve the app with a real Uvicorn server (`TestClient` bypasses Uvicorn), so they fail if Uvicorn's record changes and nothing is dropped.
- **[The log grows without bound on the server]** → Docker's `json-file` driver keeps everything by default. Rotation (`max-size`, `max-file`) is a server setting, raised as an open question in the proposal for #34.
- **[Tests start the app many times]** → `configure_logging` replaces its own handler and filter instead of adding more (decision 1).
