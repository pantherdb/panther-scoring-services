# Design

## Context

See proposal.md, Why. The findings, with how each was reproduced, are API-1 and API-2 in [the review at `64174c9`](../../../docs/code-review/2026-10-30-whole-repo-review-64174c9.md).

This change relies on these decisions, and doesn't change them:

- **[tech-stack.md](../../../docs/design/tech-stack.md),** API recommendation 1: jobs run in a pool of `spawn` worker processes, and are kept in memory.
- **[hosting.md](../../../docs/design/hosting.md),** A Public API: running jobs are bounded by the workers, waiting ones aren't, and the options are a cap in the API, a rate limit at the front end, or both. This change adds the cap; the rate limit stays with #34.

What the code does today:

- **The body:** FastAPI reads a JSON body with Starlette's `Request.body()`, which joins every chunk in memory, then decodes it. The request models' limits, such as `refmap`'s 100,000 IDs, run after that. Neither the app nor `fastapi run` limits the size.
- **The jobs:** `JobRunner.submit()` stores the job and starts an asyncio task, which waits on a semaphore of one slot per worker. Nothing bounds how many tasks wait.
- **The settings** are read once, in the lifespan, so an invalid one stops the API before it takes a request (`scoring-jobs`, Configuration from the environment).
- **The data check:** `origin/main` has `panther_engine.csnp.check_data()`, exported in `__all__` (#53). It raises `DataFolderError` when `PANTHER_DATA_DIR` isn't set, and `MissingDataError`, naming the folder and each missing part, when the data is incomplete. `score()` calls it before every search.

## Goals / Non-Goals

**Goals:**

- No valid request is refused by the body limit.
- No job is stored when a submission is refused.
- Every new error is problem details, with fixed text, echoing nothing from the request.

**Non-Goals:**

- A per-client limit. The API sees the proxy's address, not the client's, and #34 decides the proxy.
- A readiness endpoint. The data check only logs.
- Changing how a `csnp` job fails without data: still the generic `500`.

## Decisions

1. **A pure ASGI middleware that reads the body itself, `limits.BodyLimit`.**
   - A `Content-Length` over the limit is refused before anything is read.
   - Otherwise the middleware reads the body, counting, and refuses it as soon as the count passes the limit. A body within the limit is handed to the app as the same messages, then the server's own `receive` takes over, so a later disconnect still arrives.
   - Holding up to the limit in the middleware costs nothing extra: FastAPI holds the whole body anyway.
   - The `413` is sent by the middleware itself, as problem details: title "Content Too Large", and detail "The request body is larger than the API accepts, 16,777,216 bytes." It names the limit, which is configuration, and nothing from the request.
   - It applies to every request, so a body on a route that never reads one is refused too.
   - *Alternative:* Starlette 1.10's `RequestBodyLimitMiddleware`, or `FastAPI(max_body_size=...)`. Rejected:
     - its limit is fixed when the app is built, but the settings are read in the lifespan, so an invalid value would stop the import, not the startup;
     - it refuses by raising an `HTTPException` from `receive`, so whether the client gets our problem details or its plain-text fallback depends on how FastAPI's body parsing re-raises it.
   - *Alternative:* `BaseHTTPMiddleware`. Rejected: it can't refuse a streamed body before the app reads it.
   - *Alternative:* only at the proxy. Rejected: the API would still be unprotected natively and behind any proxy that isn't configured, and the review asks for both.
2. **The limit is 16 MiB, `PANTHER_API_MAX_BODY_BYTES`, read in the lifespan and kept on `app.state.settings`.**
   - The largest valid request is `refmap`'s: 100,000 IDs of 64 printable characters. If each is `"` or `\`, JSON escapes it as two, so the body is about 13.1 MB. A test sends exactly that, and it gets `refmap`'s `501`, not a `413`.
   - A `csnp` request is far smaller: 50,000 residues and its substitutions.
   - The middleware reads the limit from `app.state.settings` on each request. Where the lifespan hasn't run, as for a test client used without `with`, it uses the default.
   - The setting must be at least 1.
3. **A cap on waiting jobs, `PANTHER_API_MAX_QUEUED_JOBS`, 50 by default, checked in `JobRunner.submit()`.**
   - **What's counted:** the runner counts jobs submitted and not yet finished. A new job is refused when that count is already the workers plus the cap. So up to `workers` jobs run, and up to `cap` wait.
   - **Why not count `queued` jobs:** a job becomes `running` only when its task next gets the event loop. Two jobs submitted back to back while two workers are free would both still be `queued`, and the second would count as waiting.
   - **Refused:** `QueueFullError`, before the store is touched, so no job is stored. The router answers `503` with `Retry-After: 30` and the detail "Too many jobs are waiting to run. Try again later."
   - **Order:** a request is validated first, so an invalid one is still a `422`, and a valid `refmap` one still a `501`.
   - **The count goes down** in the task's done callback, on the event loop, however the job ended: succeeded, failed, a dead worker, or cancelled at shutdown.
   - **`0` is allowed:** no job waits, and a submission is refused while every worker is busy.
   - **Why 50:**
     - **Waiting time.** A `csnp` job of an ordinary protein takes seconds: the five real jobs in `tests/test_csnp_scoring.py` take about a minute and a half together, a worker start included. With the default two workers, 50 jobs of 5 to 10 s each wait about 2 to 4 minutes at the back of the queue. Much longer than that, a user is better told to come back.
     - **Memory.** A waiting `csnp` job holds its input, under 1 MB, so 50 hold under 50 MB. When `refmap` is wired in, one of its largest requests holds about 12 MB as Python strings, so 50 of them would hold about 600 MB. That's bounded, where today nothing is; `refmap`'s wiring (#40) should look at it again.
     - **Ordinary use isn't refused.** The forms submit one job at a time, so only a client scripting many submissions reaches the cap.
     - It's a setting, so #34 can change it for the server's cores and traffic.
   - **`Retry-After` is fixed at 30 s,** about one `csnp` job's time. It's a constant, not a setting: a client should retry, and the exact number isn't critical.
   - *Alternative:* `429`. Rejected: the cap is on the server's total, not on one client's rate, and RFC 9110 gives `503` with `Retry-After` for a temporary overload.
4. **The startup check logs and carries on.** The lifespan calls `panther_engine.csnp.check_data()` off the event loop. Any exception it raises is logged at `ERROR`, with the engine's message, which names the folder and what's missing, or that `PANTHER_DATA_DIR` isn't set. The API starts either way.
   - **Why not refuse to start:** a developer runs the API natively without the data (`api/README.md`), and only `csnp` jobs need it. The `tools` job, the species list and the frontend's work all run without it.
   - **The log line shows** in `docker compose logs api`: uvicorn configures only its own loggers, so Python's last-resort handler writes an `ERROR` from `panther_api` to standard error.
   - **Each `csnp` job still checks,** in the engine, so data that arrives after startup works, and data that goes missing fails the job with the generic `500`, as now.
   - *Alternative:* report the check in `GET /api/v1/versions` or a readiness endpoint. Rejected here: it's new contract, and #34 hasn't asked for one.

## Risks / Trade-offs

- **A slow client holds the middleware** while it sends up to 16 MiB. That's no worse than today, where Starlette waits the same way; a slow-body timeout belongs at the proxy.
- **The cap is per process.** The API runs one process (hosting.md), so it's the server's total.
- **A burst can be refused while workers are idle,** if the cap is 0 and the jobs are submitted faster than earlier ones finish. With the default of 50, that needs 52 unfinished jobs.

## Migration Plan

None: both settings have defaults, and no request that worked before is refused, except one over 16 MiB or past the cap.
