# Proposal

**Area:** cross-cutting: engine (task group 1, by the engine developer) and api (task group 2).

## Why

Today any error in a job's work ends the job with "The job hit an unexpected error and could not complete." That's right for bugs, but not when the user's input is the problem and only the engine can tell, so the API couldn't reject it when the job was submitted. The user then can't tell what to fix. Every service port will hit this, so settle one way to report input problems before the first port, rather than once per service.

## What Changes

- **Engine:** a new exception, `panther_engine.core.errors.InputError`. A service raises it when the input as a whole can't be processed. Its message is written for the person who submitted the job: no file paths, tool output or internal identifiers. It keeps its type and message when it travels from a worker process back to the API.
- **API:** when a job's work raises `InputError`, the job ends `failed` with a problem-details `error` whose `status` is `422` and whose `detail` is the error's message. Every other exception is handled as now: a generic `500` detail, with the message only in the log.
- **A problem with one item isn't an `InputError`.** Examples: one substitution that can't be mapped, or one ID with no family. Those belong in the result, and the job succeeds, as the legacy services report "Invalid substitution" per SNP and `NOHIT` per ID.
- **No change to the API contract.** The job's `error` is the same `Problem` schema; only its `status` and `detail` differ for input errors. The frontend's job page already shows `detail`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `engine-core`: a new requirement for input errors that are safe to show and survive the trip between processes.
- `scoring-jobs`: "A failing job reveals nothing internal" now excludes input errors. A new requirement says how an input error reaches the user.

## Impact

- **Engine (engine developer):** `engine/src/panther_engine/core/errors.py` and its tests.
- **API:** `api/src/panther_api/jobs/runner.py`, `api/tests/`, and `docs/testing/api.md`. `api/openapi.json` doesn't change.
- **Frontend:** nothing to change. A failed job's `detail` is already what the job page shows.
- **Parity with each service's reference:** not affected by this change. Each port decides which legacy conditions are input errors, and its golden files show whether the legacy service reported them as errors. Needs team verification per service.
- **Order:** the API side imports `InputError`, so task group 1 lands before group 2. The engine developer adds `InputError` with the first port, `csnp` (2026-10-29), so group 2 waits for it.

## Open Questions

Each needs team verification.

- **A code beside the message?** Should `InputError` also carry a short machine-readable code (for example `unknown_organism`), or the input field it's about, so the frontend can highlight the field? Not needed for the first port; it can be added without breaking anything.
- **Which legacy conditions are input errors,** for `refmap`, `hmmscore` and `treegrafter`. Each port's proposal lists them.

Answered by the engine developer on 2026-10-29:

- **The name and place:** `panther_engine.core.errors.InputError`, as proposed. It arrives with the first port, `csnp`.
- **`csnp` has no input errors among its legacy conditions.** "No family hit" and "invalid substitution" are per-substitution results, as in the legacy service ("Not scored: No PANTHER family for input sequence", "Not scored: Invalid substitution"), and parity keeps them that way. An unknown species is rejected before the job starts: the engine exports the species codes it accepts, and the API validates against them.
- **A broken data file isn't the user's fault,** so it stays a generic failure.
