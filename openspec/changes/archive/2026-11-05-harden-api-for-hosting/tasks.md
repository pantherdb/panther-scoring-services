# Tasks

## 1. Settings

- [x] 1.1 Add `max_queued_jobs` (default 50, ≥ 0) and `max_body_bytes` (default 16 MiB, ≥ 1) to `settings.py`, and keep the settings on `app.state.settings` in the lifespan. Verify with `tests/test_settings.py`: the defaults, the environment overriding them, and `-1`, `many`, `0` and `16MB` refused (spec, Configuration from the environment)

## 2. The Body Limit (API-1)

- [x] 2.1 Add `limits.BodyLimit`, a pure ASGI middleware, and add it in `create_app()` (design.md, decisions 1 and 2). Verify with `tests/test_limits.py`:
  - a `Content-Length` one byte over is a `413` problem without the body's text, and no job (spec, Over the limit by its length);
  - a chunked body over the limit is a `413` (spec, Over the limit without a length);
  - the middleware alone, given 1,000 chunks against a limit of 2.5 chunks, reads 3 and never calls the app (spec, Streamed past the limit);
  - a body of exactly the limit is a `202` (spec, At the limit), and a body of 16 MiB + 1 under the defaults is a `413`;
  - 100,000 escaped 64-character IDs, about 13.1 MB, get `refmap`'s `501` (spec, The largest valid request).
- [x] 2.2 Document the `413` for every operation with a body, in `problems.document_problems()`. Verify with `test_the_schema_documents_the_413_and_the_503` (spec, In the schema)

## 3. The Cap on Waiting Jobs (API-2)

- [x] 3.1 Count unfinished jobs in `JobRunner`, and raise `QueueFullError` from `submit()` before storing anything when the workers plus the cap are already unfinished. Answer it in `routers/jobs.py` with a `503`, `Retry-After: 30` and fixed text, and document it in `_CREATE_RESPONSES` (design.md, decision 3). Verify with `tests/test_limits.py`:
  - with 1 worker and a cap of 2, the fourth job is a `503` problem with `Retry-After` and no `Location`, the store still holds 3, and an invalid request is still a `422` (spec, Past the cap; An invalid request past the cap);
  - after the gate opens and the jobs finish, the next is a `202` and succeeds (spec, After the queue drains);
  - 2 workers and a cap of 0: `202`, `202`, `503` (spec, Free workers);
  - 1 worker, a cap of 0, three failing jobs in turn: each a `202` (spec, Finished jobs free their place);
  - the schema documents the `503` with `Retry-After` (spec, In the schema).

## 4. The Startup Data Check

- [x] 4.1 Call `panther_engine.csnp.check_data()` in the lifespan, off the event loop, and log any exception at `ERROR` without stopping (design.md, decision 4). Verify with `tests/test_limits.py`: an empty data folder and an unset `PANTHER_DATA_DIR` each log one error and `/health` answers `200`; a passing check logs nothing (spec, Startup check of the cSNP data). Verify by hand that the line shows in uvicorn's output

## 5. Contract and Docs

- [x] 5.1 Regenerate `api/openapi.json` with `uv run python -m panther_api.openapi`, and `frontend/src/app/api/schema.d.ts` with `npm run api:types`. Verify that `tests/test_openapi.py`, `npm run api:types:check` and `npm run type-check` pass
- [x] 5.2 Update `docs/testing/api.md` (the settings, the startup log line, and a Limits section with how to see each response), `api/README.md` and `api/CLAUDE.md`. Verify with `npx markdownlint-cli2`, and by running the Limits section's commands against a native server

## 6. Final Check

- [x] 6.1 In `api/`: `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run basedpyright`, `uv run pytest`. In `frontend/`: `npm run api:types:check`, `npm run type-check`. At the root: `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive`. All pass

## Notes

### Next action

Review: open the pull request against `main` with this change's artifacts and code, for the API owner's approval. Then archive.

### Blockers

None.

### Failed approaches

- **Adding `Problem` to `models_json_schema` in `document_problems()` (2026-11-02),** to reference it from the `413`: it re-emitted the `Problem` component with its keys in another order, a noisy schema diff. `Problem` is already in the components through the `default` response, so the `413` references it without that.

### Lessons learned

- **Starlette 1.10 ships `RequestBodyLimitMiddleware`** (`FastAPI(max_body_size=...)`). It wasn't used: its limit is fixed when the app is built, before the lifespan reads the settings, and its fallback `413` is plain text (design.md, decision 1).
- **`TestClient` sends a request body as one message,** whatever its chunks. A test of the middleware's counting across chunks has to call it as an ASGI app with its own `receive`, as `run_body_limit()` does.
- **A job is `queued` for a loop turn even when a worker is free,** so a cap counted by status would refuse back-to-back submissions that would run at once.
- **An `ERROR` from `panther_api` reaches the console** under uvicorn through Python's last-resort handler, though uvicorn configures only its own loggers. An `INFO` doesn't.

### Follow-ups

- **#34:** a per-client rate limit at the proxy, a slow-body timeout there, and recording both limits in the deploy runbook.
- **`refmap`'s wiring (#40):** with its largest requests, 50 waiting jobs hold about 600 MB. Look at the cap again then.
