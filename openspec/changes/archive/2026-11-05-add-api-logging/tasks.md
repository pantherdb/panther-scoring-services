# Tasks

## 1. The Level Setting

- [x] 1.1 Add `log_level` to `settings.py`: `DEBUG`, `INFO`, `WARNING` or `ERROR`, upper-cased before validation, `INFO` by default (design.md, decision 6). Verify with `tests/test_settings.py`: the default is `INFO`, `debug` reads as `DEBUG`, and `LOUD` and `CRITICAL` are refused (spec, Log level from the environment: Default level; Invalid level)

## 2. The Format and the Access Filter

- [x] 2.1 Add `panther_api/logs.py` with `configure_logging(level)`: one root handler on standard error with the UTC format, Uvicorn's loggers routed through it, idempotent (design.md, decisions 1 and 2). Call it first in the lifespan, after the settings are read. Verify with a new `tests/test_logs.py`:
  - a record from `panther_api` is written as one line matching `^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z INFO panther_api\.\S+:` and then the message (spec, A message from the API);
  - `GET /api/v1/versions` writes a `uvicorn.access` line in the same format with the path and `200` (spec, A request);
  - at `WARNING`, an `INFO` record and the request line aren't written, and a `WARNING` is (spec, A higher level);
  - starting the app twice leaves one handler of ours on the root.
- [x] 2.2 Add the access filter to `logs.py`, on `uvicorn.access` below `DEBUG` only (design.md, decision 3). Verify in `tests/test_logs.py`, against a real Uvicorn server (`tests/serving.py`), with a kept case beside each dropped one:
  - a poll of an existing job writes no request line, a poll of an unknown id writes one with `404` (spec, A successful poll; A poll for an unknown job);
  - `GET /api/v1/health` writes none (spec, A health check);
  - a valid submission writes no request line, an invalid one writes one with `422` (spec, An accepted submission; A refused submission);
  - at `DEBUG`, the submission, the poll and the health check each write one (spec, Every request at DEBUG);
  - a record whose `args` isn't Uvicorn's 5-tuple passes the filter.

## 3. The Job Lines

- [x] 3.1 Add `log_summary()` to `CsnpInput`, `RefmapInput` and `ToolsInput` (design.md, decision 5). Verify with unit tests in `tests/test_csnp_input.py` and `tests/test_refmap_input.py` that a summary holds the code and the sizes and none of the submitted residues, substitutions or IDs, and that `uv run basedpyright` passes on `request.input.log_summary()` (spec, The size of a job's input)
- [x] 3.2 In `JobRunner`, log the submission at `DEBUG` and the queue-full refusal in `submit()`, and replace `_run()`'s three failure lines with one finish line per job (design.md, decision 4). Verify with `caplog` in a new `tests/test_job_logs.py`, patching `run_job` with functions from `tests/job_helpers.py`:
  - a `tools` job logs one `INFO` line with `succeeded`, a wait and a run time, and at `INFO` nothing else (spec, A job that succeeds; Not at INFO);
  - at `DEBUG`, a submission line comes before it (spec, Submitted at DEBUG);
  - a job raising `InputError` logs one `INFO` line with `422` and the message, and no traceback (spec, A job that fails on its input);
  - a job raising another exception logs one `ERROR` line with `500` (spec, A job that fails unexpectedly);
  - a worker that dies logs one `ERROR` line saying the worker stopped (spec, A worker dies);
  - a `422`, a `501` (`refmap`) and a `503` log no submission line, and the `503` logs one `WARNING` with the service and the cap (spec, A request that creates no job; Queue full).
- [x] 3.3 Add the table of recent errors to the runner, timed by the jobs' own `finished_at` (design.md, decision 7). Verify in `tests/test_job_logs.py`: two jobs failing with the same error, the first line has the traceback and the second none and names the first job; a different message gets its own traceback; past ten minutes on the clock, the traceback is logged again and later repeats name the new job (spec, An unexpected error's traceback is logged once in ten minutes)
- [x] 3.4 Run a real `csnp` job with a distinctive sequence and substitutions, and assert the captured log has its line with `HUMAN`, the length and the count, and neither the sequence nor any substitution. In `tests/test_csnp_scoring.py`, marked `tools` and `data` like its neighbours; run it in the API image by the testing doc's command. Also assert a `422` request with a distinctive value leaves no trace of it in the log, in `tests/test_logs.py` (spec, No user data in the log; A cSNP job's size)
- [x] 3.5 Document the job lines in `api/CLAUDE.md`, "Jobs": the runner logs them, and each service's input has a `log_summary()`. Add the rule "Never log a submitted value" beside "Never echo a submitted value in an error". Verify with `npx markdownlint-cli2`

## 4. Docs

- [x] 4.1 In `docs/testing/api.md`: `PANTHER_API_LOG_LEVEL` in the settings table, and a Logs section with the format, what's logged at each level, what's left out of the access log, the traceback-once rule, how to read it (`docker compose logs api`, `docker logs`), and Docker's size cap as a server setting. Replace the notes that an input error doesn't appear. Update `api/README.md` if it lists the settings. Verify with `npx markdownlint-cli2`, and by running the API natively and in the image and checking the section's example lines match

## 5. Final Check

- [x] 5.1 In `api/`: `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run basedpyright`, `uv run pytest`, and `uv run python -m panther_api.openapi` leaves `openapi.json` unchanged. At the root: `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive`. All pass
- [x] 5.2 Build the API image and run it on port 8001 with `MSYS_NO_PATHCONV=1 docker run` (not the compose project). Submit the cSNP example, poll it to the end, and check `docker logs`: Uvicorn's startup lines, then the job's one line in the new format, and no poll or `202` lines

## 6. Review on #58

- [x] 6.1 Key the recent errors by the exception's type and where it was raised, not its message (design.md, decision 7). Verify in `tests/test_job_logs.py`: a message that varies from one place is the same error, and fail()'s message raised from another place is another (spec, A message that varies; A different error)
- [x] 6.2 Replace a broken pool before logging the dead worker's line, and log the submission at the end of `submit()`, only when `DEBUG` is on (decision 4). Verify that the existing dead-worker and submission tests pass
- [x] 6.3 Log a job that fails on its input with a fixed outcome, without the engine's message (decision 4). Verify in `tests/test_job_logs.py` and `tests/test_jobs.py` that the job has the message and the log doesn't (spec, A job that fails on its input)
- [x] 6.4 Log refused submissions at most once a minute, counting the rest (`_Refusals`, decision 4). Verify with the `Clock` in `tests/test_job_logs.py`: three refusals in a minute, then one more, give two lines, the second counting three (spec, A client retrying against a full queue)
- [x] 6.5 In the access filter, drop only a successful health check, keep the `202`, build the paths from `API_PREFIX` (moved to `prefix.py`), and leave Uvicorn's access logger alone when `--no-access-log` turned it off (decision 3). Verify with the filter's table in `tests/test_logs.py`, the `202` line with the client's address against a real Uvicorn server, and `serve(access_log=False)` writing no request line (spec, A failed health check; An accepted submission; The request log turned off)
- [x] 6.6 Start every test from the settings' defaults: an autouse fixture in `conftest.py` removes every exported `PANTHER_API_*`. Verify by running the suite with `PANTHER_API_LOG_LEVEL=WARNING` exported. Also: `conftest` uses `logs.UVICORN_LOGGERS`, `_seconds()` tests `is not None`, and one `tests/polling.py` replaces the polling helpers of `test_jobs.py`, `test_csnp_scoring.py` and `test_job_logs.py`
- [x] 6.7 Update `docs/testing/api.md`, Logs, `api/CLAUDE.md`, `api/README.md`'s layout, the proposal, the design and both spec deltas. Final check as in 5.1, the suite in the API image as in 3.4, and the image's log as in 5.2

## Notes

### Next action

The pull request, #58, is open and in review. The engine developer's review (2026-11-05) is answered by section 6. Next: their approval, then merge and archive. Don't open another pull request for this change.

### Blockers

None.

### Failed approaches

- **Checking the log with `fastapi run` started from a helper script (2026-11-04):** the helper ran under another Python (3.11) than the API's venv (3.13), and the child inherited its environment, so the venv's interpreter loaded the wrong standard library ("SRE module mismatch"). Checked in the image instead (5.2).

### Lessons learned

- **`TestClient` calls the app directly, without Uvicorn,** so it never produces an access log. The access-log tests serve the app with a real `uvicorn.Server` in a thread, on port 0 (`tests/serving.py`).
- **Once an app has started, the root logger is at `INFO`,** so `caplog` also captures `httpx2`'s request lines, which contain job ids. Select records by logger name, and match a job's line by its start, `Job <id>` and a space: a repeat's line names the earlier job too.
- **pytest adds and removes its own handlers on the root around each phase,** so the `restore_logging` fixture removes only the handler the app added, instead of restoring the root's handler list.
- **A handler that keeps `sys.stderr` from when it was made** can write to a stream a test's capture has closed. `_Handler` looks up `sys.stderr` on each record.
- **In the image, fastapi-cli prints its own banner before Uvicorn starts.** It isn't a logger, so it keeps its format, as do Uvicorn's first two lines.

- **Review on #58 (2026-11-05).** The first version keyed repeated errors by message, which misses `blastp`'s time-limit message, since the limit scales with the sequence, and merges different bugs with a generic message. It also logged the dead worker before replacing the pool, logged the submission between storing the job and starting it, put the engine's input-error message in the log, dropped failed health checks and the `202` with the client's address, turned `--no-access-log` back on, and let an exported `PANTHER_API_LOG_LEVEL` fail 11 tests. All fixed in section 6.
- **Uvicorn writes access lines whenever `uvicorn.access` has a handler, its ancestors' included** (`h11_impl.py`, `self.access_log = self.access_logger.hasHandlers()`). `--no-access-log` works only by leaving it with none and not propagating.
- **A worker's exception reaches the parent with the worker's traceback as text,** chained as its `__cause__` (`_RemoteTraceback`). Its frames are read from that text.
- **Final check, after the review (6.7, 2026-11-05).** `ruff check`, `ruff format --check`, `basedpyright`, and `pytest` (339 passed, 6 skipped without the tools; the same with `PANTHER_API_LOG_LEVEL=WARNING` exported) pass natively; `openapi.json` is unchanged. In the API image, all 345 pass. The image's log shows the `202` line with the client's address and the job's line, and no health or successful poll lines.

### Open questions

- **Engine error messages that quote the input,** such as the BLAST-line previews in `csnp/hits.py`, which carry the aligned query. They reach the log in a traceback. The engine developer offered to forbid it in the engine's error contract (#58); it's engine-side, not this change.

- **Log retention on the server:** a log collector, or Docker's `max-size` and `max-file` for the `api` container. For the engine developer, with #34. It doesn't change this change's code; `docs/testing/api.md`, Logs, gives the options.
