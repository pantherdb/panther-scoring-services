# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **The engine is a library the API imports,** with no HTTP between them: [docs/design/tech-stack.md](../../../docs/design/tech-stack.md), "Engine (`engine/`)" and "API (`api/`)".
- **Jobs run in a `spawn` process pool,** and a failing job reveals nothing internal: the archived [add-scoring-jobs design](../archive/2026-10-29-add-scoring-jobs/design.md) and `openspec/specs/scoring-jobs/`.
- **The `csnp` job's request and result, and the engine's interface,** agreed on #19: the archived [add-csnp-job design](../archive/2026-10-29-add-csnp-job/design.md) and [port-csnp's design](../port-csnp/design.md). `score(CsnpInput) -> CsnpResult`, frozen dataclasses, one protein per call, the input already normalised by the API.
- **Input errors:** [add-job-input-errors' design](../add-job-input-errors/design.md). This change implements its groups 2 and 3, as that change planned.
- **Errors as problem details:** [docs/design/api-stack.md](../../../docs/design/api-stack.md).

What exists now:

- The API validates a `csnp` request, then answers `501`; `run_job`'s `csnp` case raises `NotImplementedError`.
- The engine exports `score`, `CsnpInput`, `CsnpResult`, `SubstitutionScore` and `SPECIES_CODES` from `panther_engine.csnp`. `score()` reads its data folder from `PANTHER_DATA_DIR`. It raises `ValueError` for input the API would reject, `InputError` when `blastp` can't read the sequence, `BlastError` for any other BLAST+ failure, and `DataFolderError` when `PANTHER_DATA_DIR` isn't set.
- The engine keeps cSNP's data version as `panther_engine.csnp.scoring.VERSION = "9"`, the `csnp/9/` in the data folder. It isn't in `__all__`.

The behaviour is in the spec deltas under `specs/`.

## Goals / Non-Goals

**Goals:**

- A `csnp` job's result is the engine's, field for field, with nothing computed or rewritten in the API.
- A cSNP score names the data behind it.
- The API and the UI keep working when the data isn't installed: only `csnp` jobs fail, with the generic `500`.

**Non-Goals:**

- Changing the engine. Where it's in the way, the proposal lists an open question.
- Checking at startup that the data is installed. A missing data folder fails each `csnp` job, not the API: the `tools` job and the health check still work, and the deployment runbook checks the data (tech-stack.md, "Shared Concerns").
- A species list in the form, or the species in the schema. See the proposal's Open Questions.

## Decisions

### 1. The adapter lives with the `csnp` models

`run_csnp(CsnpInput) -> CsnpResult` in `api/src/panther_api/jobs/csnp.py`, beside the API's models, as `run_tools` sits in `tools.py`. It builds the engine's `CsnpInput` (the substitutions as a tuple), calls `score()`, and copies the engine's result into the API's `CsnpResult` (lists). `run_job`'s `csnp` case calls it.

- It calls `score()` through the module, `panther_engine.csnp.score`, looked up at call time, so a test can replace it in the test process, or in a worker through a helper.
- It catches nothing. The runner decides what an exception means: `InputError` is a `422`, anything else a `500`. The engine's `ValueError` can't happen for a request that passed validation, since the API checks the same rules first; if one did, it's a bug, so the generic `500` is right.
- *Alternative:* the API's models are the engine's dataclasses. Rejected: the API's models carry the validation and the schema, and the engine stays free of Pydantic and FastAPI (#19).

### 2. No new setting for the data

The engine reads `PANTHER_DATA_DIR`. A `spawn` worker gets a copy of the API process's environment when it starts, so setting the variable for the API process is enough. compose sets it for the `api` service, with `.data/` mounted read-only at `/data`, as for the `engine` service.

- *Alternative:* a `PANTHER_API_DATA_DIR` setting that the adapter passes as `score(..., data_dir=...)`. Rejected: two names for one folder, and the engine's own error message names `PANTHER_DATA_DIR`.

### 3. The species check runs in the request model

A second `AfterValidator` on `species`, after the shape check, checks membership in `SPECIES_CODES`. Pydantic runs it only when the shape check passed, so a species gets one error. The message doesn't repeat the value, and `problems.py` already strips "Value error, ".

- It runs at submit time, so an unknown species is a `422` with no job, and never reaches the engine, which would raise `ValueError` for it.
- `SPECIES_CODES` is a literal in the engine, so the check needs no data folder.
- *Alternative:* an enum in the schema. Rejected for now: 85 values in every client's types, and Pydantic's message for a failed enum lists them all. It's an open question for the frontend.

### 4. The data version goes in `Versions`

`Versions` gains `data: list[DataVersion]`, where `DataVersion` is `{service: str, panther: str}`, the PANTHER release a service's data comes from. The API fills it once at startup from the engine, `[{"service": "csnp", "panther": "9"}]`, so `GET /api/v1/versions` and every job report it.

- **Why `Versions`:** it's already "the versions behind every answer", read once at startup, copied into every job, and shown by one shared UI component. A job's versions then say "PANTHER 9" with no change to the job models. The next services add an entry each: PANTHER 19 for `hmmscore`, `refmap` and `treegrafter`.
- **Why a list of `{service, panther}`:** like `tools`, a list keeps an order and an entry per service, and the frontend renders each without knowing the services. The field is named `panther`, not `version`, because the value is a PANTHER release; the UI shows it as "PANTHER 9" without writing the 9.
- **It's what the engine reads, not what's installed.** The data folder may be missing, or hold the full library or the sample; the release is the same. The deployment's data check is separate.
- *Alternative:* a field on the `csnp` job only, such as `CsnpJob.data_version`. Rejected: a second place for versions, and every future service would add its own. Its one advantage, that a `tools` job wouldn't name cSNP's data, doesn't matter: the versions are the service's, not the job's.
- *Alternative:* in the result, beside `family`. Rejected: the result mirrors the engine's `CsnpResult`.
- **How it's read:** `from panther_engine.csnp.scoring import VERSION`, the one import from outside `panther_engine.csnp.__all__`. The proposal asks the engine developer to export it or name another way.

### 5. Input errors, as add-job-input-errors designed

The runner catches `InputError` between `BrokenProcessPool` and `Exception`, logs it at `INFO` with the job id and message and no traceback, and fails the job with `Problem(status=422, title="Unprocessable Content", detail=str(exc))`. Its design has the reasons.

### 6. Real end-to-end tests, marked as the engine's

`api/tests/test_csnp_scoring.py` runs real `csnp` jobs: the app, a `spawn` worker, the real `run_job`, the engine, `blastp` and the data sample. It submits the release sample's three proteins and checks each result against `engine/tests/golden/csnp/spec/sample.out`, and checks a species with no hit and an unreadable sequence.

- **Markers:** `tools("blastp")` and `data("csnp")`, with the engine's semantics: skipped where missing, failed where `PANTHER_REQUIRE_TOOLS=1` or `PANTHER_REQUIRE_DATA=1`. `tests/markers.py` applies them; it checks the sample against the engine's manifest, `panther_engine.csnp.sample.MANIFEST`, for presence only.
- **Where they run:** in the API image, with `api/` and `engine/` mounted and the dev tools installed into the container (docs/testing/api.md). Natively on Windows and in CI's `api` job, `blastp` is missing and they skip.
- **CI** checks the same path in `api-image`, with `curl` and `jq` against the running image, not with pytest: the image has no dev tools, and that job already starts it.
- *Alternative:* run them in CI's `api-image` job with pytest. Rejected for now: it needs the dev tools in the job, and the `jq` check covers the deployed path. It can be added if the two drift.

### 7. The frontend

- **The 501 goes.** `'unavailable'` leaves `SubmitProblem`, and its alert leaves `SubmitAlert`. A 501 is now any other failure to start, and a test says so.
- **`VersionList` shows each `data` entry after the tools,** as "`<service> data`" and "`PANTHER <panther>`". The footer and the job page share it, so the job page shows the job's own data version.
- **The api-mode e2e test** submits P26439 with three substitutions and checks the spec §7.3 rows. The form's example, APOE, isn't in the sample (proposal, Open Questions).
- **Mock mode** is unchanged: the mocked versions gain `data`, and the mocked `csnp` job still succeeds with mock data.

## Risks / Trade-offs

- **[The data isn't installed]** → Every `csnp` job fails with the generic `500`; the log says why (`DataFolderError`, or `BlastError` naming the missing database). The docs say to fetch the sample first. A startup check is left to the deployment runbook.
- **[An engine `ValueError` reaches the user as a `500`]** → Only if the API's validation and the engine's checks disagree. The API's rules are the stricter or equal ones, and the end-to-end tests run real requests through both.
- **[`VERSION` moves or is renamed in the engine]** → The API's import fails at startup, loudly, and a test checks the value. The open question asks for a public name.
- **[The API's tests read the engine's goldens and sample manifest]** → They depend on the engine's test files and `sample` module. Both are pinned with the engine in this repository, and a change to either shows in the API's tests in the same pull request.
- **[An input error's log line isn't visible]** → Uvicorn shows only its own loggers, so the `INFO` line doesn't reach the container log. The job carries the message; logging configuration is for the deployment runbook.

## Migration Plan

- Merge with all three approvals. The API and the frontend must deploy together: a frontend without the `data` field still renders the versions, but a frontend that expects it fails on an older API's versions.
- Before running the API, fetch the cSNP data into its data folder. Staging and production use the full library, in the same layout (docs/testing/engine.md, "Using the Full Library").
- Archive `add-job-input-errors` first, then this change.
- Rollback: revert the commit. The `501` returns, and nothing persisted changes: jobs live in memory.
