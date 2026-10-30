# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **The engine is a library the API imports,** never the other way round: [docs/design/tech-stack.md](../../../docs/design/tech-stack.md), Engine condition 1.
- **How jobs run and fail:** a `spawn` process pool, with job state changed only on the event loop, and an unexpected error giving a generic `500` problem: [openspec/specs/scoring-jobs/spec.md](../../specs/scoring-jobs/spec.md) and the archived [add-scoring-jobs design](../archive/2026-10-29-add-scoring-jobs/design.md).
- **Errors as problem details, with `type` `about:blank`** until the frontend needs to tell errors apart by more than status: [docs/design/api-stack.md](../../../docs/design/api-stack.md).

What exists now:

- **`JobRunner._run`** (`api/src/panther_api/jobs/runner.py`) catches `BrokenProcessPool`, then `Exception`. Both fail the job with a fixed `500` detail, and the log gets the exception with its traceback.
- **A worker's exception reaches the API process pickled.** `concurrent.futures` re-raises it there, with the worker's traceback chained as its cause.
- **`engine/` has no exception types of its own.**

The behaviour is in [specs/engine-core/spec.md](specs/engine-core/spec.md) and [specs/scoring-jobs/spec.md](specs/scoring-jobs/spec.md).

## Goals / Non-Goals

**Goals:**

- Every service reports a problem with the whole input the same way, and the user reads a message that says what to fix.
- An input error never makes a bug look like a user mistake, and a bug never shows its message.

**Non-Goals:**

- Problems with single items, such as one unmappable substitution or one ID with no family. They belong in each service's result.
- Machine-readable error codes, or the field an error is about. See the proposal's Open Questions.
- Validating input before a job starts. Request validation stays the `422` the API returns at submit time. This change covers what only the engine can find out, such as an organism its data doesn't have.

## Decisions

### The exception lives in the engine

`panther_engine.core.errors.InputError(Exception)`, raised with one argument, the message.

- *Alternative:* the API defines the exception and the engine imports it. Rejected: the engine is a library with no dependency on the API.
- *Alternative:* duck typing, so that any exception with a `user_message` attribute counts. Rejected: an implicit contract the type checker can't see, and any library's exception could match by accident.
- **Subclasses per service** (for example `UnknownOrganism(InputError)`) are allowed, and the API catches them through the base class.

### It survives the trip between processes

An exception is pickled as its class and its `args`. `InputError(message)` keeps the message in `args`, so it arrives intact.

- **A subclass whose constructor takes other arguments must keep `args` reconstructible,** or define `__reduce__`. The engine's tests check the base class, round-tripped with `pickle` and through a real `spawn` worker. The docstring warns about subclasses.

### The job's error: status 422, the message as `detail`

`runner.py` catches `InputError` between `BrokenProcessPool` and `Exception`. It fails the job with `Problem(status=422, title="Unprocessable Content", detail=str(exc))`.

- **Why 422:** the request was valid and accepted (`202`), but its content can't be processed. The API already uses 422 for content it can't process at submit time, so the frontend reads one status: 422 means the user can fix it, and 500 means it's our fault. *Alternative:* 400. Rejected: it means a malformed request, which this isn't.
- **`type` stays `about:blank`.** The status already tells the two apart.
- **The message is shown as given, without truncating or rewriting it.** The engine's contract is what makes it safe: written for users, with no paths, tool output or internal identifiers. The API adds nothing from the exception's cause or traceback.

### Logging

An input error is the user's mistake, not a fault. It's logged at `INFO` with the job id and message, without a traceback, so it doesn't look like a failure in the logs. Unexpected errors keep `logger.exception`.

### Testing across the process boundary

The API's tests already run real `spawn` workers with module-level helpers (`api/tests/job_helpers.py`). A new helper raises `InputError`, so the test covers the pickling path as well as the runner's handling, not a stand-in for it.

## Risks / Trade-offs

- **[A service raises `InputError` with an unsafe message]** → The contract is in the docstring and the spec. Each service's tests check its own messages. The API can't tell a safe message from an unsafe one, so review is the guard.
- **[A bug is reported as an input error]** → Only explicit `raise InputError(...)` in the engine counts. Nothing converts other exceptions into it.
- **[A subclass doesn't pickle]** → `concurrent.futures` would then raise a pickling error in place of the subclass, and the job fails with the generic `500`. The safe direction. The docstring tells subclass authors to keep `args` reconstructible.
- **[Group 2 waits on group 1]** → Group 1 is one small module and its tests. The engine developer adds it with the first port, `csnp` (decided 2026-10-29); group 2 follows in the API change that adds the `csnp` job.

## Migration Plan

Nothing to migrate. No service raises `InputError` yet, so behaviour changes only when a port starts raising it.
