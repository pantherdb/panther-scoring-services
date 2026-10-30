# Tasks

Every task that adds behaviour is test-first: write the tests for its scenarios, run them and see them fail for the right reason, then implement. Record each red run (the tests, and why they failed) in Notes.

## 1. Settings

- [x] 1.1 Add `pydantic-settings==2.16.2` to `dependencies` in `api/pyproject.toml` and run `uv lock`. Verify:
  - `uv sync --locked` passes;
  - `api/uv.lock`'s diff adds `pydantic-settings` and nothing that wasn't already locked (record what it pulls in);
  - the existing checks and tests still pass.
- [x] 1.2 Test-first, `tests/test_settings.py`: the defaults (2 workers, 86400 seconds), each `PANTHER_API_` variable overriding its default, and `PANTHER_API_JOB_WORKERS=0` and a non-integer expiry rejected. Then add `src/panther_api/settings.py` as design.md describes. Verify the tests pass.

## 2. The Tools Job's Work

- [x] 2.1 Test-first, in `tests/test_jobs.py`, in the test process with `panther_api.jobs.tools.report_tools` patched: `run_tools()` lists the tools in the engine's order, gives `null` for a missing tool, and has none of the fake's paths in its JSON; `run_job()` with a `tools` request returns that result. Then add `jobs/tools.py` and `jobs/work.py`. Verify the tests pass, and that `run_job` and `run_tools` pickle by reference (`pickle.loads(pickle.dumps(run_job)) is run_job`).

## 3. Job Store

- [x] 3.1 Test-first, `tests/test_job_store.py`, with `store.utcnow` patched: a new job is `queued` with a UUID4 id and `created_at`; ids differ; an unknown id isn't found; a finished job is found just before `finished_at` plus the expiry and not after it ("Before expiry", "After expiry"); an unfinished job never expires; adding a job sweeps out expired ones. Then add `src/panther_api/jobs/store.py` (`JobRecord`, `JobStore`, `utcnow`). Verify the tests pass.

## 4. Endpoints and Worker Pool

- [x] 4.1 Test-first, `tests/test_jobs.py`, through `TestClient` and a real `spawn` pool, with `tests/job_helpers.py` and the autouse fixture patching `panther_api.jobs.runner.run_job`. Cover "Submit a tools job" (202, `Location`, status), "Unknown service", "Invalid input", "Missing input" (422, no job created), "Two jobs" (UUID4, different), "Poll until done" (statuses only move forward), "A finished job" (timestamps ordered, `result` set, `error` null, `versions` equal to `GET /versions`), and "Unknown id" (a random UUID and `not-a-uuid`: 404 problem details). Then add `jobs/models.py`, `jobs/runner.py`, `routers/jobs.py`, and start and stop the runner in the lifespan. Verify the tests pass, and the existing ones still do.
- [x] 4.2 Test-first: "More jobs than workers" (`PANTHER_API_JOB_WORKERS=1`, a job held by the gate helper, a second job `queued` until the first is released, then both `succeeded`) and "Requests while a job runs" (`/health` answers 200 while the gate holds a job). Verify they pass.
- [x] 4.3 Test-first: "The work raises" (`failed`, `null` result, a 500 problem `error`, and neither the message nor the path anywhere in the job), and another job submitted afterwards still succeeds. Verify they pass.
- [x] 4.4 Test-first: "A worker dies" (the helper exits its process; that job is `failed` with a problem `error`; a job submitted afterwards `succeeded`). Verify it passes.
- [x] 4.5 Test-first: expiry through the API, with `store.utcnow` patched: a finished job answers 200 just before its expiry and 404 after it. Also "Invalid setting": building the app with `PANTHER_API_JOB_WORKERS=0` fails at startup. Verify they pass.
- [x] 4.6 Regenerate `api/openapi.json` with `uv run python -m panther_api.openapi`. Add tests to `tests/test_openapi.py` and verify they pass: `POST /api/v1/jobs`'s body is a `oneOf` with a `discriminator` on `service`; its 202 response documents `Location`; `GET /api/v1/jobs/{job_id}` documents its 404 through the `default` problem response; `JobStatus` is a component; `ToolsJob.result` and `ToolsJob.error` are required and nullable. `test_committed_schema_is_current` passes. The frontend has no `api:types` script yet, so there are no generated types to regenerate; record that in Notes.

## 5. Docs

- [x] 5.1 In `docs/testing/api.md`: a Settings table (the two variables, defaults, valid values); the job endpoints in the dev-server list; in Tests, how the job tests work (`job_helpers.py`, the `run_job` patch point, the gate, why a monkeypatch doesn't reach a worker); and a "Try the Jobs by Hand" section for the engine developer: start the API in the image with `docker compose up --build api`, then submit a `tools` job and poll it from `/api/v1/docs` and with `curl`. Verify every command as written, against the `api` image on port 8001 (port 8000 belongs to the other agent's work on this machine), and say so in Notes.
- [x] 5.2 Update the API row of `docs/testing/README.md`'s Kinds of Test table (the job lifecycle is now tested) and the `scoring-jobs` row of `CONTRIBUTING.md`'s Spec Layout. Verify `npx markdownlint-cli2` passes.

## 6. Final Check

- [x] 6.1 Build the `api` image (`docker buildx build --target api --load -t panther-api:jobs .`), run it on port 8001, submit a `tools` job and poll it until it `succeeded` with `blastp` 2.17.0, `hmmscan` 3.4, `hmmsearch` 3.4 and `epa-ng` 0.3.8 and no paths ("Tools in the image"). Check the container's processes show the spawned worker.
- [x] 6.2 In `api/`: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest`. From the root: `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive`. All pass.

## Workflow follow-up

- **No separate artifact-review pull request.** The team decided (2026-10-29) to review this change's artifacts and its implementation together in #16, from `feat/api`, as for `connect-api-to-engine`. Reviewers there:
  - the API developer approves;
  - the frontend developer reviews the contract: the two operations, `ToolsJobRequest`, `ToolsInput`, `ToolsJob`, `ToolsResult` and `JobStatus`;
  - the engine developer tries the jobs by hand, following `docs/testing/api.md`.
- **On #16,** confirm `api` and `api-image` pass under `ci-passed`, and that `dependency-review` lists `pydantic-settings` with an allowed licence.
- **Settle the proposal's open questions in review,** or carry them to the first service's change.
- **After it merges,** archive with `/opsx:archive`, which creates `openspec/specs/scoring-jobs/spec.md`. Archive `connect-api-to-engine` first: both changes are on `feat/api`.

## Notes

### Next action

Every task is done (2026-10-29), and committed on the agent branch for `feat/api` (#16). Next: push to `feat/api`, then confirm on #16 that `api`, `api-image` and `dependency-review` pass (Workflow follow-up), and that the engine developer can try the jobs by hand from `docs/testing/api.md`.

### Blockers

None.

### Failed approaches

- **The first image build (6.1, 2026-10-29)** failed before starting: Docker's `desktop-linux` context file was locked by another process (the frontend agent, working in parallel). Rerunning the same command worked.

### Lessons learned

- **Artifacts and code in one pull request (2026-10-29).** As for `connect-api-to-engine`, the team chose to skip the separate artifact-review pull request: this change's artifacts and implementation are reviewed together in #16. The branch for this work was moved to `feat/api` at `b604087` before the change was created.
- **Red runs, test-first (2026-10-29).**
  - **1.2:** `test_settings.py` failed to collect: `No module named 'panther_api.settings'`.
  - **2.1** (the tools job's work, then group 3): `test_jobs.py` failed to collect: `No module named 'panther_api.jobs'`.
  - **3.1:** `test_job_store.py` failed to collect: `No module named 'panther_api.jobs.models'`.
  - **4.1:** first a collection error (no `panther_api.jobs.runner`). With the runner and models added but no route, 10 tests failed, each because `POST /api/v1/jobs` answered 404. The two unknown-id tests passed at once, because any unknown path is already a 404 problem; they guard the route that came next.
  - **4.2:** `test_a_job_waits_queued_while_the_only_worker_is_busy` failed with "job still running": without the slot semaphore, the second job was marked `running` while the only worker was busy. `test_the_api_answers_while_a_job_runs` passed at once: the handlers never block.
  - **4.3:** both tests failed with "job still running": the work's exception escaped the job's task ("Task exception was never retrieved"), so the job never finished.
  - **4.4:** `test_a_dead_worker_fails_its_job_and_later_jobs_run` failed on the detail (the generic message, not the worker one), and `test_a_dead_worker_leaves_the_queued_jobs_alone` failed because the queued job ran on the broken pool and failed.
  - **4.5:** the three tests passed on their first run, because the behaviour already existed below the API: expiry in the store (3.1), `Settings()` in the lifespan and its default of 2 workers (4.1). To show they can fail, two mutants were run and reverted: without the expiry check in `JobStore.get`, the expiry test failed; with a default of 1 worker, `test_two_workers_by_default` failed ("job still queued").
  - **4.6:** the five new schema tests passed on their first run (the contract was built in 4.1); `test_committed_schema_is_current` was the red one until the schema was regenerated.
  - **After 6.1:** `test_an_unknown_service_is_not_echoed` failed: the 422 body contained the submitted `service` (see below).
- **pydantic-settings was already locked (1.1).** `fastapi[standard]` depends on it, and `api/uv.lock` already had 2.16.2, the newest 2.16.x. The direct pin added only the requirement lines to the lock, and no package. proposal.md and design.md record it.
- **The task groups were reordered (2.1, 3.1).** The store holds the request type, so the tools job's work (`work.py`) came first: group 2 is now the work and group 3 the store.
- **An unknown `service` was echoed in the 422 (found against the image, 6.1).** Pydantic's `union_tag_invalid` message quotes the tag (`Input tag 'nope' found using 'service' …`), against `api-service`'s "never echo submitted values". The 4.1 test used a distinctive value only in another case, so it missed this. `problems.py` now rebuilds that message without the tag; a test sends a distinctive `service` and checks it isn't in the body. Any future tagged union, and any pydantic message that quotes its input, needs the same care.
- **Spawn under pytest works without set-up (4.1).** Workers import the replacement functions from `tests/job_helpers.py` by name, because `multiprocessing` passes the parent's `sys.path`, which pytest's prepend import mode has given `tests/`, to each worker. basedpyright resolves `from job_helpers import …` in tests without configuration. The whole suite (74 tests, 27 of them for jobs) runs in about 7 s on Windows, including real worker processes.
- **A monkeypatch never reaches a worker.** Tests patch `panther_api.jobs.runner.run_job` in the parent, and the pool pickles the replacement by reference. The gate helper gets its file path from `PANTHER_TEST_JOB_GATE`, which a worker inherits when it starts. Workers start lazily, on the first job, so the variable must be set before the first submit.
- **The job is `queued` in the 202 response, natively and in the image.** Its task hasn't run yet when the handler returns; it is `running` within a millisecond. The spec allows either.
- **The OpenAPI schema (4.6).** The request and the job are `oneOf` with a `discriminator`, even with one member. FastAPI titles the 202's inline union `Response Create Job Api V1 Jobs Post`; it's a title, not a component, and was left. The `GET` lists a 422 that can't happen (design.md). The frontend has no `api:types` script yet, so there are no generated types to regenerate.
- **Native check (2026-10-29).** `uv run fastapi dev --port 8001`: a `tools` job went `queued` to `succeeded` in about 0.4 s, with every version `null` (no tools natively). `not-a-uuid` got the 404 problem. Stopping the server left no Python processes behind.
- **The image (6.1, port 8001, amd64).** `docker buildx build --target api --load -t panther-api:jobs .`, then `docker run --rm -d -p 8001:8000 --name panther-api-jobs panther-api:jobs`. A `tools` job `succeeded` about 1.5 s after it was submitted (the first worker's start), with `blastp` 2.17.0, `hmmscan` 3.4, `hmmsearch` 3.4 and `epa-ng` 0.3.8 and no paths. `docker top` showed `fastapi run`, multiprocessing's `resource_tracker`, and one `spawn_main` worker. The unknown-service and extra-field 422s and the `not-a-real-id` 404 answered as documented. `docker stop` took under a second.
- **How the docs were checked (5.1).** Port 8000 belonged to the frontend agent on this machine, so `docker compose up --build api` wasn't run. The same `api` target was built and run with `docker run` on port 8001, and every `curl` in "Try the Jobs by Hand" ran against it with the port changed. `docker top` stood in for `docker compose top api`. The `/api/v1/docs` steps weren't clicked through in a browser; the schema tests cover what the page is built from.
