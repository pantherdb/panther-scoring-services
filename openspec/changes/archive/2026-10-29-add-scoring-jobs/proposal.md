# Proposal

**Area:** api. Outside `api/`, it changes only docs: `docs/testing/api.md`, `docs/testing/README.md` and `CONTRIBUTING.md`.

## Why

Scoring takes seconds to minutes, so every service runs as a job: `POST /api/v1/jobs` starts one and `GET /api/v1/jobs/{id}` polls it ([tech-stack.md](../../../docs/design/tech-stack.md), API recommendation 1). The first ported service needs those endpoints, the worker processes behind them and the job contract the frontend polls. Building them now, with no scoring logic, settles the lifecycle, the worker pool and the contract on their own. A built-in `tools` job, which reports the external tools' versions from a worker process, lets the engine developer try the whole path by hand before any service exists.

## What Changes

- **New endpoint: `POST /api/v1/jobs`.** The body is `{"service": ..., "input": {...}}`. `service` selects the input model, so the body is a union tagged by `service`, and the frontend gets one generated type that it narrows by `service`. It answers `202 Accepted` with a `Location` header pointing at the job, and the job. An unknown `service` or an invalid `input` gets the existing `422` validation problem.
- **New endpoint: `GET /api/v1/jobs/{id}`.** It returns the job. An unknown or expired id gets `404` as problem details.
- **The job:** `id` (a random UUID4), `service`, `status` (`queued`, `running`, `succeeded` or `failed`), `created_at`, `started_at`, `finished_at`, `result` (typed per service, `null` until the job succeeds), `error` (problem details, `null` unless it failed) and `versions` (the `Versions` model from `connect-api-to-engine`).
- **One job type for now, `tools`:** `{"service": "tools", "input": {}}` runs the engine's tool report in a worker process. Its result lists each tool's name and version, never its path. Each scoring service adds its own member to the union when it's ported.
- **Workers:** a process pool, started with `spawn`, created and shut down with the app. A job that raises is `failed` with a generic error that reveals nothing internal. A worker that dies fails its job, and the pool is replaced so later jobs still run.
- **Storage:** in memory, in the API process. A finished job expires after a set time, 24 hours by default, and every job is lost when the API restarts.
- **The first settings,** read from environment variables prefixed `PANTHER_API_`: the number of worker processes and the expiry time. This adds the one new dependency, `pydantic-settings`, pinned exactly at 2.16.2, as [api-stack.md](../../../docs/design/api-stack.md) planned ("Added with the first setting").
- **Docs:**
  - `docs/testing/api.md`: the settings, how the job tests work, and a "Try the jobs by hand" section for the engine developer: start the API in the image, submit a `tools` job and poll it, with `/api/v1/docs` or `curl`.
  - `docs/testing/README.md`: the API row of the Kinds of Test table mentions the job lifecycle as planned ("later the job lifecycle"); it becomes current.
  - `CONTRIBUTING.md`: the `scoring-jobs` row in Spec Layout gains the job shape and the worker behaviour.

Not in this change:

- **Any scoring service.** Each joins the union with its own change.
- **A limit on queued jobs, and the largest accepted input.** Both are open questions in tech-stack.md (Input size).
- **Cancelling a job, a Redis-backed queue, and authentication.**

## Capabilities

### New Capabilities

- `scoring-jobs`: the job lifecycle behind `POST /api/v1/jobs` and `GET /api/v1/jobs/{id}`: the request and job shapes, statuses, failures, worker processes, expiry, configuration, and the built-in `tools` job.

### Modified Capabilities

None. The new endpoints follow `api-service`'s existing requirements (the `/api/v1` prefix, problem details, the committed schema) without changing them.

## Impact

- **Code:** a new `panther_api.jobs` package and `routers/jobs.py`; a settings module; the lifespan in `create_app()` also starts and stops the worker pool; new tests; a regenerated `api/openapi.json`. `problems.py` stops one validation message from quoting the submitted value: an unknown `service` was echoed back, against `api-service`'s existing requirement *(found during apply)*.
- **Dependencies:** `pydantic-settings==2.16.2` in `api/pyproject.toml`. `fastapi[standard]` already locked it at 2.16.2, so `api/uv.lock` gains only the direct requirement and no package *(found during apply, 2026-10-29)*. No other dependency.
- **API contract:** two new operations and new schema components (the `tools` request, input, result and job; `JobStatus`). The frontend developer reviews them, and they are the shapes the frontend's `/jobs/:id` page polls. The frontend has no `api:types` script yet, so it has no generated types to update.
- **Engine:** no changes. The `tools` job's worker function lives in `api/` and calls the engine's existing `report_tools()`.
- **Image and compose:** no changes. The defaults suit the compose `api` service, so it needs no environment variables.
- **Parity with each service's reference:** not affected. There's no scoring logic and no divergence.

## Open Questions

Each needs team verification.

- **Limit on queued jobs and largest accepted input** (tech-stack.md, Input size). Today any number of jobs can wait in memory. The answer decides when a real queue is needed, and each service sets its own input limit when it's ported.
- **Does `refmap` go through jobs,** or get a synchronous endpoint (tech-stack.md, Jobs vs synchronous)? The endpoints here don't depend on the answer.
- **Does the site poll jobs, or wait on a synchronous call** (tech-stack.md, API recommendation 2)? It's the API developer's decision, needed before the site's first service moves to `/api/v1`.
- **The default pool size.** It's 2 workers, a placeholder until a service's memory use is measured; tech-stack.md says to size it by memory as well as CPU. Each deployment sets it.
- **Should the `tools` job stay once scoring services exist?** It's useful as a smoke test of a deployed pool. The working default is that it stays.
