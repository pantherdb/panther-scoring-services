# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **Jobs, a pool of processes started with `spawn`, sized by memory as well as CPU, and a later move to a Redis-backed queue without changing the contract:** [docs/design/tech-stack.md](../../../docs/design/tech-stack.md), API recommendation 1. So is **"Engine code never runs on the event loop"**.
- **pydantic-settings, added with the first setting; no other new dependency without a proposal; strict types with named ignores; the `S` rules:** [docs/design/api-stack.md](../../../docs/design/api-stack.md).
- **The app factory, the `/api/v1` router and problem details:** [openspec/changes/archive/2026-10-28-scaffold-api/design.md](../archive/2026-10-28-scaffold-api/design.md).
- **The `Versions` model, read once in the lifespan, and the autouse fake for the engine's tool report:** [openspec/changes/connect-api-to-engine/design.md](../connect-api-to-engine/design.md).
- **How the frontend consumes jobs:** it polls `GET /jobs/{id}` with RTK Query's `pollingInterval`, stops when the job finishes or fails, and shows results at `/jobs/:id` ([frontend/CLAUDE.md](../../../frontend/CLAUDE.md), State and Data and cSNP-Specific Rules).

Decided before this change was written (2026-10-29), and not reopened here: the two endpoints and their status codes, one endpoint with a request union tagged by `service`, the job's fields, random UUID4 ids, the built-in `tools` job, a `ProcessPoolExecutor` with an explicit `spawn` context created in the lifespan, in-memory storage with a 24-hour default expiry, pydantic-settings with prefixed environment variables, and test-first apply.

What exists now: `create_app()` has a lifespan that stores `read_versions()` on `app.state.versions`. `problems.py` turns `HTTPException` into problem details and gives every unexpected error a generic 500. The test `client` fixture runs the lifespan, and the autouse `fake_tools` fixture patches `panther_api.versions.report_tools`.

The behaviour is in [specs/scoring-jobs/spec.md](specs/scoring-jobs/spec.md).

## Goals / Non-Goals

**Goals:**

- A scoring service joins by adding a request member, a result model and a worker function. Nothing in the store, the runner or the router changes.
- The tests run real worker processes under `spawn` on every platform, and still never run the real external tools.

**Non-Goals:**

- Measuring how many workers a service needs. The default is a placeholder (proposal, Open Questions).
- Progress reporting inside a running job.
- Persisting jobs, or sharing them between API processes. With more than one API process (`fastapi run --workers N`), a job is only visible on the process that created it. The image runs one process; the move to Redis is what lifts this.

## Decisions

### Layout

```text
api/src/panther_api/
  settings.py          Settings (pydantic-settings, prefix PANTHER_API_)
  main.py              the lifespan also reads the settings and starts and stops the JobRunner
  jobs/
    __init__.py
    tools.py           ToolsInput, ToolsResult, run_tools(): the tools job's work
    work.py            the request union (JobRequest), the result union (JobResult) and run_job()
    models.py          JobStatus and the response models (ToolsJob; Job)
    store.py           JobRecord and JobStore: in memory, with expiry; utcnow()
    runner.py          JobRunner: the process pool, queueing, failures, pool replacement
  routers/jobs.py      POST /jobs, GET /jobs/{job_id}
api/tests/
  job_helpers.py       module-level job functions the tests run in worker processes
  test_jobs.py         the endpoints and lifecycle, through TestClient and a real pool
  test_job_store.py    expiry, without a pool
  test_settings.py
  clock.py             a clock that moves only when a test moves it (added during apply)
```

- **What a worker imports is kept light.** A worker unpickles the request and calls `run_job`, so it imports `work.py` and `tools.py`, which need only pydantic, the engine and `versions.py`. The response models, which need `problems.py` and so FastAPI, stay in `models.py`, which no worker imports.

### The contract

The request body:

```json
{ "service": "tools", "input": {} }
```

The job, as both endpoints return it:

```json
{
  "id": "6f1c0f0e-8a51-4c43-9d36-1c7f1f5f2a90",
  "service": "tools",
  "status": "succeeded",
  "created_at": "2026-10-29T18:00:00.120000Z",
  "started_at": "2026-10-29T18:00:00.121000Z",
  "finished_at": "2026-10-29T18:00:01.480000Z",
  "result": {
    "tools": [
      { "name": "blastp", "version": "2.17.0" },
      { "name": "hmmscan", "version": "3.4" },
      { "name": "hmmsearch", "version": "3.4" },
      { "name": "epa-ng", "version": "0.3.8" }
    ]
  },
  "error": null,
  "versions": { "api": "0.1.0", "engine": "0.1.0", "tools": ["…the versions report…"] }
}
```

- **The request is a discriminated union on `service`** (`Annotated[ToolsJobRequest, Field(discriminator="service")]`, written as a union of one). Pydantic accepts a one-member tagged union, and the schema is already `oneOf` with a `discriminator` mapping. When `csnp` adds `CsnpJobRequest`, the schema gains a member and the generated TypeScript type gains a branch. Nothing that exists changes shape.
  - An unknown `service` fails with pydantic's `union_tag_invalid` at `["body"]`, and an invalid `input` at `["body", "tools", "input", …]`. Both go through the existing 422 handler.
  - **Pydantic's `union_tag_invalid` message quotes the tag it was given** (`Input tag 'nope' found using 'service' …`), which would echo the submitted value, against `api-service`'s requirement. `problems.py` rebuilds that one message from its context without the tag; it still lists the expected tags. *(Decided during apply, 2026-10-29: found by hand against the image, and a test now covers it.)*
  - **Each input model forbids extra fields,** so a mistyped field is a 422 instead of being silently ignored.
  - *Alternative:* one endpoint per service (`POST /jobs/tools`). Rejected in the brief: the frontend would get one type per service and a growing list of routes.
- **The job is a union on `service` too:** `ToolsJob` has `service: "tools"` and `result: ToolsResult | null`. The frontend then narrows the result by `service`, the same way as the request. Each member is built from the same fields.
- **The job doesn't echo its input.** Inputs will be sequences and substitution lists; the client has them already, and leaving them out keeps every poll small.
- **`result` and `error` are required and nullable** (no default), as `ToolVersion.version` is: the generated type is `T | null`, not optional.
- **`status` is a `StrEnum`,** so the schema has a named `JobStatus` component the frontend can switch on.
- **Timestamps are timezone-aware UTC,** serialized with a `Z`.
- **`versions` is `app.state.versions`,** copied onto the job when it's created. The image fixes the versions, so the ones read at startup are the ones the worker runs with.
- **`Location` is a path,** `/api/v1/jobs/{id}`, built with `app.url_path_for`. RFC 9110 allows a relative reference, and a path stays right behind the frontend's dev proxy and any reverse proxy, where an absolute URL could name the wrong host. The 202 response documents the header in the schema.
- **`GET /jobs/{job_id}` takes the id as a string,** not a `UUID`. An id that isn't a UUID can't be a job's, so it gets the same 404 as an unknown one instead of a 422: a mistyped `/jobs/:id` link shows "not found" in the frontend, like an expired one. The 404's `detail` is fixed text and doesn't repeat the id.
  - `problems.py` documents a 422 for every operation with parameters, so the schema lists one for this `GET` although a string id can't fail validation. Harmless, and left as it is.

### Ids

`uuid.uuid4()`, which reads the operating system's random source. There is no endpoint that lists jobs. Anyone who has a job's id can read it: the id is the only secret, as in a shared link. The legacy CGI let concurrent users read each other's BLAST hits (`CGI-6`); here each job's state lives under its own unguessable key, and once services run files, each job gets its own work directory from `core/` (CLAUDE.md, Working Rules).

### Running a job

```text
POST ─► JobStore.add (queued) ─► asyncio task ─► wait for a free slot ─► running
     ─► pool.submit(run_job, request) ─► await asyncio.wrap_future(…) ─► succeeded | failed
```

- **The API keeps its own queue, and hands the pool at most one job per worker.** Each job gets an asyncio task that waits on an `asyncio.Semaphore` sized to the worker count, then marks the job `running`, records `started_at` and submits it.
  - **Why:** a `ProcessPoolExecutor` future doesn't say when a worker actually starts it. It reports "running" when the item enters the pool's internal call queue, which holds more items than there are workers. With the semaphore, a submitted job always has an idle worker, so `running` and `started_at` are true to within a process start.
  - **It also protects queued jobs.** When a worker dies, the pool fails every item it holds. Queued jobs are still waiting on the semaphore, outside the pool, so they run on the replacement (see below).
  - *Alternative:* submit straight to the pool and report `running` from `future.running()`. Rejected for the two reasons above.
  - *Alternative:* a worker callback through a `multiprocessing.Manager` queue to report the start. Rejected: another process and another channel, for what the semaphore gives for free.
- **Completion is handled on the event loop.** `asyncio.wrap_future` turns the pool's future, which completes on the pool's manager thread, into an asyncio future that is resolved through `loop.call_soon_threadsafe`. Every change to a job's state happens in the job's own task, on the loop. No lock is needed, and no other thread touches a `JobRecord`.
- **Tasks are kept in a set** until they finish, so the event loop's weak reference can't let one be garbage-collected mid-job.
- **The pool is created in the lifespan** with `ProcessPoolExecutor(max_workers=settings.job_workers, mp_context=multiprocessing.get_context("spawn"))`. It starts processes only when jobs arrive, so an app that never runs a job starts none, and the existing tests pay nothing.
- **At shutdown,** the runner cancels the tasks still waiting for a slot, then shuts the pool down with `cancel_futures=True` and `wait=True`, in a thread (`run_in_threadpool`). Running jobs finish first; see Risks.

### Spawn-safe work

- **`run_job(request)` is the one function submitted,** a module-level function in `work.py`. It dispatches on the request's type with a `match` (one case per service) and calls the service's own module-level function, `run_tools(input)` for now. Everything it needs comes from its argument. It relies on no global state set up in the parent, which `spawn` wouldn't carry over: a fresh interpreter imports the module, unpickles the request, and calls it.
- **Requests and results are pydantic models,** which pickle by reference to their importable classes.
- **`run_tools`** calls `panther_engine.core.tools.report_tools()` and copies each tool's name and version into `ToolVersion`, as `read_versions()` does, so the path never leaves the worker.
- **The tools job's work lives in `api/`,** not in the engine, because the engine is another developer's area and `report_tools()` already does the work. Each scoring service's work function will call the engine's typed interface for that service.

### Failures

| What happened | Job status | `error` |
| ------------- | ---------- | ------- |
| The work raised any exception | `failed` | `{"title": "Internal Server Error", "status": 500, "detail": "The job hit an unexpected error and could not complete."}` |
| The worker process died (`BrokenProcessPool`) | `failed` | `{"title": "Internal Server Error", "status": 500, "detail": "The worker running the job stopped unexpectedly."}` |

- **Nothing from the exception reaches the job,** as with `problems.py`'s 500: not the message, not the traceback, not a path. The runner logs it with `logger.exception`, which includes the worker's traceback, because `concurrent.futures` chains it as the exception's cause.
- **A service error a user can act on,** such as a sequence the engine can't score, will need its own `detail`. That's left to the first service: it adds an exception type the runner maps to a 4xx-style problem. Until then every failure is generic.
- **A dead worker:** `ProcessPoolExecutor` marks the whole pool broken and fails every item it holds, so jobs running in other workers of the same pool fail with it (the spec allows this). The runner then replaces the pool, unless another task already has: it compares the broken executor with the current one, which is safe because every task runs on the same loop. The old pool is shut down without waiting. Jobs still waiting for a slot then run on the new pool.
- **A worker that dies while idle** breaks the pool without failing a job. The next `submit` raises `BrokenProcessPool`, and that job takes the same path: it fails, and the pool is replaced. See Risks.

### Expiry: on access, and a sweep on each submit

- **On access:** `JobStore.get` treats a job whose `finished_at` plus the expiry is in the past as gone, deletes it, and returns nothing. The 404 is then exact at the boundary, however rarely the sweep runs.
- **A sweep on each submit:** `JobStore.add` first deletes every expired job. Memory grows only when a job is submitted, so sweeping there bounds it as well as a timer would, without a background task to start, stop and test. A job nobody polls again is freed by the next submission.
- **Expiry counts from `finished_at`,** and an unfinished job never expires. Counting from `created_at` could delete a job a client is still waiting on, if the queue were long.
- *Alternatives:* only on access. Rejected: jobs nobody polls again would never be freed. Only a periodic sweep: rejected, because a job would answer 200 for up to one interval after it expired, and it needs a background task.
- **The sweep is linear in the number of stored jobs.** That's every job of the last 24 hours. Until there's a limit on queued jobs (proposal, Open Questions), it's small enough; a store keyed by expiry time can replace it if not.
- **The clock is `store.utcnow()`,** a module-level function that every timestamp comes from. Tests patch it to move time forward instead of sleeping.

### Settings

`panther_api.settings.Settings`, a `BaseSettings` with `env_prefix="PANTHER_API_"`:

| Setting | Environment variable | Default | Valid |
| ------- | -------------------- | ------- | ----- |
| `job_workers` | `PANTHER_API_JOB_WORKERS` | `2` | an integer ≥ 1 |
| `job_expiry_seconds` | `PANTHER_API_JOB_EXPIRY_SECONDS` | `86400` (24 hours) | an integer ≥ 1 |

- **Read in the lifespan, first,** with `Settings()`. An invalid value raises a validation error before the app takes a request, so a mistyped setting stops the API instead of being ignored. The schema export never starts the app, so it reads no settings.
- **No `.env` file.** Configuration comes from the environment only; compose and deployment set it there.
- **Seconds, as an integer,** rather than a `timedelta` parsed from ISO 8601: `PANTHER_API_JOB_EXPIRY_SECONDS=3600` needs no explanation.
- **The compose `api` service sets neither.** The defaults suit a developer machine.

### Tests

- **The patch point is `panther_api.jobs.runner.run_job`.** The runner looks the name up when it submits, so a test replaces what the workers run by patching it in the parent, and the pool pickles the replacement by reference.
- **Replacement functions live in `tests/job_helpers.py`,** at module level. Under `spawn` a worker must import the function by name: pytest puts `tests/` on `sys.path`, and `multiprocessing` passes the parent's `sys.path` to each worker it starts, so `job_helpers` imports there too. A function defined inside a test, or in a test module, wouldn't be importable that way.
- **The autouse `fake_tools` fixture also patches `run_job`** with a helper that returns the four fake tool versions, so no worker runs the real tools. `run_job` and `run_tools` themselves are tested in the test process, with `report_tools` patched. The image check in tasks covers the real tools through a real worker.
- **A monkeypatch in the parent never reaches a worker.** The helpers that need parameters read them from environment variables, which a worker inherits when it starts. The blocking helper waits for a file named in `PANTHER_TEST_JOB_GATE`, so a test can hold a job in `running` and then release it.
- **A dying worker** is a helper that calls `os._exit`, which ends the process without the pool's own exception handling.
- **Tests poll with a deadline,** as the frontend does, instead of sleeping a fixed time. A worker's first start under `spawn` takes about a second.

## Risks / Trade-offs

- **[Shutdown waits for running jobs]** `wait=True` lets running jobs finish before the API exits, although their results are lost with the store. A long job delays a restart by its own length. Python 3.13's `ProcessPoolExecutor` has no public way to stop a busy worker (`terminate_workers()` arrives in 3.14), and killing the workers through private attributes is fragile. Accepted until jobs take minutes; then a deployment sets a graceful-shutdown timeout, or the move to Redis changes the model.
- **[A worker dying fails the jobs beside it]** A crash in one worker fails every job running in that pool. Workers die only on a crash or an out-of-memory kill, and jobs still queued are kept. The client sees `failed` and can resubmit.
- **[An idle worker's death fails the next job]** That job never ran, but fails. Retrying the submission once on the new pool would hide it; it isn't done now, because there's no reliable way to test it without reaching into the pool's private state. Revisit if it's seen in practice.
- **[Unbounded queue]** Any number of jobs can wait in memory. Bounded by the open question on queue limits and input size; until a scoring service exists, the only job is the tiny `tools` job.
- **[Spawn start-up cost]** Each worker's first job pays for a fresh interpreter importing pydantic and the engine, about a second. Workers are reused afterwards.
- **[Jobs on one API process only]** See Non-Goals. The image runs one process.
- **[pydantic-settings pulls in a new transitive dependency]** It didn't: `fastapi[standard]` had already locked pydantic-settings 2.16.2, so `uv.lock` gains only the direct requirement (checked during apply). `dependency-review` still checks the licence.

## Migration Plan

Nothing to migrate: the endpoints are new, and nothing calls them yet. Rollback is reverting the pull request. When a Redis-backed queue replaces the in-memory store and pool, the endpoints, request and job shapes stay; only `store.py` and `runner.py` change.
