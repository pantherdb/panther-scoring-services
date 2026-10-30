# Tasks

Test-first: for each task, write its tests, run them and see them fail for the right reason, then write the code. Record each red run in the Notes.

## 1. Engine: the Input Error (engine developer)

- [ ] 1.1 Add `engine/src/panther_engine/core/errors.py` with `InputError(Exception)`, raised with one message. Its docstring states the contract:
  - written for the person who submitted the input;
  - no file paths, tool output or internal identifiers;
  - only for problems with the input as a whole, since single-item problems belong in the result;

  `InputError` defines `__reduce__`, rebuilding through a module-level `_rebuild(cls, message, state)` that doesn't call the subclass's `__init__` (design.md, "It survives the trip between processes"). Verify that `engine/tests/test_errors.py` covers the spec's three scenarios:
  - "Copied between processes": a `pickle` round trip keeps the type and message;
  - "Raised in a worker process": a module-level function raising it in a `spawn` `ProcessPoolExecutor` reaches the parent as `InputError` with the same message;
  - "A subclass with its own constructor": a subclass whose `__init__` takes other arguments (for example `(family, species)`) arrives through a real `spawn` worker with its type, message and attributes, while another job running in the same pool succeeds.

  Also verify that `docker compose run --rm engine` passes.
- [ ] 1.2 Tell service authors how to use it, in the engine's docs (the engine README or `docs/testing/engine.md`, the engine developer's choice): when to raise it, the message rules, and that single-item problems go in the result. Verify `npx markdownlint-cli2` passes.

## 2. API: Input Errors in Failed Jobs

- [ ] 2.1 Once 1.1 is on the branch, write these tests in `api/tests/test_jobs.py`, with a module-level helper in `tests/job_helpers.py` that raises `InputError("Unknown organism.")` in a real worker:
  - the spec's "Unprocessable input" (the job is `failed`, `result` null, the `error` has status 422 and exactly that `detail`, and the body has no traceback);
  - "Other jobs keep running";
  - the existing "The work raises" test still passes unchanged.

  Run them and verify the new ones fail first, with status 500 and the generic detail.
- [ ] 2.2 In `jobs/runner.py`, catch `InputError` between `BrokenProcessPool` and `Exception`, and fail the job with `Problem(status=422, title="Unprocessable Content", detail=str(exc))`. Log it at `INFO` with the job id and message, without a traceback. Verify:
  - 2.1's tests pass;
  - `uv run python -m panther_api.openapi` leaves `api/openapi.json` unchanged (`git diff --exit-code api/openapi.json`);
  - `uv run ruff check`, `uv run ruff format --check`, `uv run basedpyright` and `uv run pytest` pass in `api/`.
- [ ] 2.3 In `docs/testing/api.md`, under "Try the Jobs by Hand", show what a failed job looks like for an input error (422, the engine's message) and for an unexpected error (500, the generic detail). Verify `npx markdownlint-cli2` passes.

## 3. Final Check

- [ ] 3.1 From a copy of the files git would commit:
  - in `api/`: `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright` and `pytest` pass;
  - from the root: `docker compose run --rm engine` passes, and `docker compose up --build -d api` still runs a `tools` job to `succeeded` (then `docker compose down`);
  - `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass.

## Workflow follow-up

- Open a pull request with these artifacts. The engine developer approves the contract and owns group 1. The API developer approves group 2.
- The engine developer adds group 1 with the first port, `csnp` (decided 2026-10-29). Group 2 starts after that, with the API change that adds the `csnp` job.
- After the implementation merges, archive with `/opsx:archive`.
- **Each service port** lists, in its own proposal, which legacy conditions become `InputError` and which are single-item results.

## Notes

### Next action

The artifacts are in #17, for the engine developer's review. Group 1 arrives with the `csnp` port (engine developer); then group 2.

### Blockers

- Group 2 needs `InputError` from group 1, which comes with the `csnp` port.

### Failed approaches

None yet.

### Lessons learned

- **The engine developer's answers (2026-10-29).** `InputError` keeps its proposed name and module, and arrives with the `csnp` port. In `csnp`, "no family hit" and "invalid substitution" are per-substitution results, not input errors, so the example message in the spec and tasks is now "Unknown organism.", as in the `engine-core` scenario. A broken data file stays a generic failure.
- **Subclasses across processes (engine developer's review on #17, 2026-10-30).** Unpickling an exception calls `cls(*exc.args)`, so a subclass with its own constructor came back garbled, or broke the pool and every running job. The design had called that failure "the safe direction"; it wasn't. The base class now defines `__reduce__`, and task 1.1 tests a subclass through a real worker.
