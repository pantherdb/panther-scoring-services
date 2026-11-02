# Proposal

**Area:** api. Everything changed is in `api/`, its docs, and the generated `frontend/src/app/api/schema.d.ts` if the schema's types change. No engine or frontend code changes.

## Why

The API is about to go public ([hosting.md](../../../docs/design/hosting.md), #34). The whole-repository review at `64174c9` ([the review](../../../docs/code-review/2026-10-30-whole-repo-review-64174c9.md)) found two Medium faults that a public deployment would hit:

- **API-1:** the input limits are Pydantic checks, which run after Starlette has read the whole body and decoded its JSON. One 200 MB request took the process from 78 MB to about 1 GB before its 422. A few at once can exhaust the container's memory, and every job in the in-memory store goes with it.
- **API-2:** nothing limits how many jobs can wait. 1,000 submissions were all accepted with 202, behind one worker. One client can delay everyone's jobs by tens of minutes, and each waiting job holds its input in memory.

PR #53 also added `panther_engine.csnp.check_data()`, which raises when the cSNP data folder is missing pieces. Today the API finds that out only when a `csnp` job fails with a 500.

## What Changes

- **A request body limit (API-1):** a middleware refuses a body over `PANTHER_API_MAX_BODY_BYTES`, 16 MiB by default, both by its `Content-Length`, before reading it, and by counting the bytes as they arrive, so a body without a length is refused as soon as it passes the limit. The answer is a `413` problem with fixed text that echoes nothing. The default fits the largest valid request: `refmap`'s 100,000 IDs of up to 64 characters are about 13 MB of JSON when every character is escaped.
- **A cap on waiting jobs (API-2):** `PANTHER_API_MAX_QUEUED_JOBS`, 50 by default, caps the jobs that wait for a worker. Past it, `POST /api/v1/jobs` answers a `503` problem with `Retry-After`, and stores no job. Running jobs are already bounded by `PANTHER_API_JOB_WORKERS`.
- **A startup check of the cSNP data:** the lifespan calls `check_data()` and, if the data is missing or incomplete, logs an error naming what's missing. The API still starts.
- **The schema:** `POST /api/v1/jobs` documents the `413` and the `503`, with its `Retry-After` header.
- **Docs:** `docs/testing/api.md` (the two settings, and the new responses), `api/README.md` and `api/CLAUDE.md`.

Not in this change:

- **A per-client rate limit.** That belongs at the proxy in front of the API ([hosting.md](../../../docs/design/hosting.md), A Public API), and is #34's call.
- **The deployment runbook.** The review asks for the body limit to be recorded there; the runbook belongs to #34, and doesn't exist yet. The limit is in `docs/testing/api.md`'s settings table, for it to link.
- **The Low API findings** (API-3 to API-6) and the nits. None is part of the two fixes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `api-service`: a new requirement, a request body limit answered with `413`.
- `scoring-jobs`:
  - a new requirement, a cap on waiting jobs answered with `503` and `Retry-After`;
  - a new requirement, the startup check of the cSNP data;
  - "Configuration from the environment" is modified to list the two new settings.

## Impact

- **Code:** a new `api/src/panther_api/limits.py` (the middleware); `settings.py`, `main.py` (the middleware, the settings on `app.state`, the data check), `jobs/runner.py` (the cap), `routers/jobs.py` (the `503`) and `problems.py` (the `413` in the schema).
- **API contract:** `openapi.json` gains the `413` and `503` responses on `POST /api/v1/jobs`, and a sentence in its description. No request or response model changes. The frontend's generated `schema.d.ts` gains the two responses, and no frontend code needs to change.
- **Behaviour:** a request over 16 MiB, which no valid request is, now gets a `413` where it got a `422`. A submission past the cap gets a `503` where it got a `202`. The forms show any submit failure that isn't a `422` or an unreachable API as fixed text, "The job couldn't be started. Try again in a moment." (`frontend/src/features/*/SubmitAlert.tsx`), which fits both.
- **Tests:** `api/tests/test_limits.py` and `test_settings.py`.
- **Dependencies:** none.
- **Parity with the reference:** not affected. Neither limit changes what a job computes, and no valid request is refused by the body limit. The legacy CGIs had neither limit; the website capped a cSNP sequence at 50,000 residues, which the API's `scoring-input` rules already do. No divergence row is needed.

## Open Questions

Each needs team verification:

- **The cap's default, 50,** is set from the jobs we measured, not from production traffic (design.md, decision 3). #34 may change it with the setting once the server's job times are known.
- **Whether the forms should say more for a `503`,** such as using its `Retry-After`. Today they show the fixed "Try again in a moment." That's the frontend developer's call.
