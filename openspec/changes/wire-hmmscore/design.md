# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **The engine is a library; scoring goes through jobs; the website moves to the JSON API:** [docs/design/tech-stack.md](../../../docs/design/tech-stack.md). Workers are `spawn` processes (API recommendation 1).
- **What the API serves and where, and what the server holds:** [docs/design/api-stack.md](../../../docs/design/api-stack.md) and [docs/design/hosting.md](../../../docs/design/hosting.md).
- **The contract, the input rules, the settings and the running cap:** the archived [add-hmmscore-job](../archive/2026-11-16-add-hmmscore-job/design.md), decisions 2 (the result), 3 (the rules), 4 (the engine interface), 5 (the settings and their defaults), 6 (the running cap) and 7 (the residue limit in the router). Its Migration Plan lists this change's work.
- **The form and the results:** the archived `add-hmmscore-form` (#79, archived in #82), whose Risks say this change removes the `501` requirement and the notice, and keeps the submit failures.
- **The pattern:** the archived [wire-refmap](../archive/2026-11-10-wire-refmap/design.md): decision 1 (the job calls the engine in the worker), decision 6 (one startup check per service), decision 9 (each job names its own service's data), and how it removed refmap's `501`.

**What exists:**

- **The engine** (`port-hmmscore`, #81): `panther_engine.hmmscore` exports `DATA_VERSION` (`"19"`), the frozen dataclasses `HmmscoreInput(sequence)`, `HmmHit(panther_id, name, evalue, score, alignment)` and `HmmscoreResult(hit)`, `score(request, *, data_dir=None, cpu=0, timeout=None)`, `check_data(data_dir=None)` and `HmmscoreError`. It's decision 4 of `add-hmmscore-job`, unchanged. `score()` raises, in order:
  - `ValueError` for a sequence that isn't upper-case letters, `.`, `_`, `~` and `*` with a letter, which the API never sends;
  - `DataFolderError` when `PANTHER_DATA_DIR` isn't set, and `MissingDataError` when the folder lacks `globals/names.tab`, the four pressed `binHmm` files or `books/` (`check_data`);
  - `InputError("The search took longer than this service allows. Try a shorter sequence.")` once the whole search passes `timeout`, after killing the running tool;
  - `HmmscoreError` for a tool that exits non-zero, can't run or writes nothing readable, or a missing model file;
  - `LibraryFormatError` (`hmmscore.library`) for a broken `names.tab`.
- **The API** (`add-hmmscore-job`, #76): `jobs/hmmscore.py`'s request and result models, which mirror the engine's dataclasses field for field; the residue limit in the router; the running cap in `JobRunner`; the four settings, two of which, the time limit and `--cpu`, nothing reads yet; `UNAVAILABLE`'s row, and `run_job`'s case that raises `NotImplementedError`.
- **The form** (`add-hmmscore-form`, #79): the form, the checks, the results and the alignment, built against the contract; `services.ts` keeps HMM scoring's `comingSoon: true`, which shows the badge and the notice.

## Goals / Non-Goals

**Goals:**

- A valid `hmmscore` request scores with the engine, end to end, in the API and the form.
- The time limit and the thread count reach `score()`, from the API's settings.
- An `hmmscore` job traces to PANTHER 19, and the startup log says when the library is missing.
- The real API's answer for the form's example is tested in CI, against the data sample.

**Non-Goals:**

- Changing the input rules, the residue limit, the running cap or the scoring: the contract and the engine's parity stand.
- The server's values for the settings (#68), which the engine developer sets with the deploy.
- Waiting limits and `Retry-After` times per job type (#80).
- The website's port to the JSON API.

## Decisions

### 1. The job calls `score()` in the worker, as `csnp` does

`jobs/hmmscore.py` gains `run_hmmscore(request, *, cpu, timeout)`, called from `run_job`'s hmmscore case in the worker. It passes the normalised sequence to `panther_engine.hmmscore.score()` unchanged, with `cpu` and `timeout`, and builds `HmmscoreResult` and `HmmHit` from the engine's result, field for field, as `run_csnp` does.

- **The result stays a model.** It's one hit with an alignment of a few kilobytes, about 50 KB for `titin-10000`'s. A `SerializedResult`, as refmap's, buys nothing at that size. The results budget still counts it by its JSON size.
- **Exceptions pass through,** and the runner sorts them as it does today:

  | Raised | The job |
  | ------ | ------- |
  | `InputError`, past the time limit | `failed`, `422`, its message as `detail` |
  | `HmmscoreError`, `LibraryFormatError`, `MissingDataError`, `DataFolderError` | `failed`, `500`, the generic `detail`; the message goes to the log |
  | `ValueError` | The same. It can't happen for a request the API accepted, so reaching it is a bug, and a `500` is right |

  Nothing about a `500`'s exception reaches the job, so a data path or a tool's standard error stays in the log.
- **The engine module is imported lazily** inside `run_hmmscore`, as `run_refmap` does, so a process imports `hmmscore.library` and `core.hmmer` only where it scores. `main.py` imports it for the startup check (decision 4).
- **`UNAVAILABLE` keeps its mechanism** with no rows, as `wire-refmap` left it, for `treegrafter`'s contract. With no row, the router never answers `501`, and the schema drops it. The test that no `501` is documented once every service runs no longer needs to reload the router with the table emptied.

### 2. The settings reach the worker as the job's options

A worker is a `spawn` process: it imports `work.py` afresh, and gets everything from `run_job`'s arguments (`api/CLAUDE.md`, "Jobs"). The settings are read once, in the lifespan. So:

- **`work.py` gains `JobOptions`,** a frozen dataclass of what the work needs from the settings: `hmmscore_cpu` and `hmmscore_time_limit_seconds`. `run_job(request, options)` passes them to `run_hmmscore`; the other cases ignore them.
- **`JobRunner` takes `options`** when it's built, from the settings in `main.py`'s lifespan, and submits `run_job(request, options)` for every job. A test that builds a `JobRunner` passes its own.
- **The test helpers** in `tests/job_helpers.py`, which stand in for `run_job`, take the second argument and ignore it.

*Alternatives:*

- **The worker reads the settings itself,** from the environment it inherits. Rejected: it validates them a second time, in another place, and a test that builds `Settings` directly wouldn't reach it.
- **A pool initializer** that stores the options in the worker. Rejected: state set up in the worker, beside the rule that it gets everything from `run_job`'s arguments, and a pool replaced after a dead worker must be given them again.
- **The options inside `HmmscoreJobRequest`.** Rejected: the request is the contract, and these aren't the client's to set.

### 3. The time limit

- **It counts from when `score()` starts,** in the worker, not from the job's submission. A job waiting for the running cap or a worker doesn't use it up. `hmmscan` gets what's left of it, then `hmmsearch` what's left after that (port-hmmscore, decision 4).
- **Past it, the job fails with a `422`,** and the engine's message, "The search took longer than this service allows. Try a shorter sequence.", is its `detail`, as `scoring-jobs`' "Input errors reach the user" requires. The submitter can shorten the sequence, so it's an input error, unlike cSNP's BLAST limit (`add-hmmscore-job`, decision 4). The job page shows the `detail` as for any failed job.
- **The log line** is the runner's fixed outcome for an input error, "failed 422, the engine couldn't process the input", with the job's residues and its time, which says how long it ran.
- **It grows with the sequence's length.** A job's limit is `floor + (ceiling − floor) × residues ÷ the residue limit`, rounded to the nearest second, where the ceiling is `PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS` (720), the floor is a new `PANTHER_API_HMMSCORE_MIN_TIME_LIMIT_SECONDS` (120), and the residue limit is `PANTHER_API_HMMSCORE_MAX_RESIDUES` (10,000). With the defaults, APOE's 317 residues get 139 s, 5,000 residues 420 s, and 10,000 the full 720 s. A search's time grows with its length: APOE took 13 s and `titin-10000` 231 s on the full library (#68). So a short query that runs far longer than it should, on an overloaded server, is stopped in about two minutes, not twelve, and frees the one running slot for the jobs waiting behind it.
- **The floor** covers what every search costs whatever its length: `hmmscan` reads all of `binHmm.h3f`, 4.9 GB, which is slower when the server can't keep it cached. Settings validation requires the floor to be at least 1 and at most the ceiling; equal values give every job the same limit, as before this change.
- **720 s stands as the ceiling.** `titin-10000`'s 231 s is under the 240 s estimate the default was scaled from. A slower server may need other values; those are the server's (#68), set once the deploy has measured a short and a long query there.

### 4. Startup: hmmscore's data check

`main.DATA_CHECKS` gains `("hmmscore", "hmmscore", panther_engine.hmmscore)`, after `csnp` and `refmap`. Its check is a few `stat`s, no file read, in the threadpool beside the others. Missing data logs "hmmscore jobs will fail until the hmmscore data is in place: …", with the engine's message, and the API still starts. The checks stay independent: missing hmmscore data doesn't stop `csnp` or `refmap` jobs, nor the reverse.

- **The data sample passes the check.** It holds the same parts as the full library (`names.tab`, the pressed `binHmm` files, `books/`), so a developer's `.data/` with the sample logs no error. The check doesn't tell the sample from the library: `hmmscore data verify` does.

### 5. Versions

`versions.read_versions()` lists `DataVersion(service="hmmscore", panther=DATA_VERSION)` after refmap's, in the order the services were ported. `Versions.for_service` already gives each job its own, so an `hmmscore` job's `versions.data` is `[{"service": "hmmscore", "panther": "19"}]`. HMMER's version is already in the report, as the `hmmscan` and `hmmsearch` tools, and in every job's `versions.tools`.

### 6. The form

- **`services.ts`:** HMM scoring's `comingSoon` becomes `false`. Its tab and its home page card lose the mark, and its page loses the badge and the notice, which read the flag.
- **The notice goes** with its requirement: `NotAvailableNotice` in `HmmscorePage.tsx`, and the tests that looked for it. The page keeps reading the flag for the badge, as the home page and the tabs do.
- **The `501` path goes:** `submitProblem`'s `unavailable`, `SubmitAlert`'s text for it, and their tests. No service answers `501` now, so a `501` with problem details is `failed`, "couldn't be started", as for refmap since `wire-refmap`. A `501` without problem details still came from something in between, and stays `unreachable` (`isUnreachable`). `SubmitAlert`'s `limited` keeps showing `busy` as `failed` for cSNP and refmap, until #80.
- **The mocks:** the versions list hmmscore's PANTHER 19, so a mocked `hmmscore` job's page shows it. The mocked hit stays the made-up `PTHR00000:SF1`. The comments that say the real API answers `501` go.
- **The types:** `npm run api:types` drops the `501` from `schema.d.ts`; nothing else in the contract changes.

*Alternative:* keep `unavailable` for `treegrafter`'s contract later. Rejected for now: it's dead code until then, and `add-treegrafter-job`, if it has a `501`, can bring it back with its own requirement.

### 7. Tests and data

- **Without the data or the tools** (CI's `api` job, Windows natively): the job's options reach `run_hmmscore` (decision 2); `run_hmmscore` maps the engine's result field for field, with the engine's `score` replaced in-process; the time limit's `InputError` fails the job with a `422` and its message, through a stand-in `run_job` in `job_helpers.py`; `HmmscoreError` and `ValueError` fail it with the generic `500`, without their messages; a valid request gets `202`; the schema has no `501`; the startup check logs hmmscore's error alone; the versions report and a job's versions.
- **With the tools and the data sample** (marked `tools("hmmscan", "hmmsearch")` and `data("hmmscore")`), a new `tests/test_hmmscore_scoring.py` runs real jobs through the API:
  - the form's example, APOE: `PTHR18976:SF2`, "APOLIPOPROTEIN E", score `439.0`, E-value `2.2e-133`, and the alignment of the engine's sample golden;
  - `no-hit`: `{"hit": null}`;
  - `tie-pthr35774`: `PTHR35774:SF1` (row 13);
  - a time limit too short to finish: the `422` and its message. It calls `run_hmmscore` in-process with a timeout of a millisecond, since the setting is whole seconds.

  The inputs and the expected hits come from the engine's goldens, `engine/tests/golden/hmmscore/parity/`, read-only. `hmmscore` joins `tests/markers.py`'s `DATA_MANIFESTS`, with the sample's manifest.
- **CI's `api-image` job,** on both architectures, restores the hmmscore sample from the cache the engine jobs fill, fetches it with the image's CLI, which checks it, runs `tests/test_hmmscore_scoring.py` with the data required, and scores APOE through the running API with `curl`, as it does a cSNP protein. The sample's cases gave their amd64 results on arm64 too (#81). The image has HMMER 3.4.
- **The frontend:**
  - unit tests: no badge or notice on `/hmmscore`, the tabs and the home page marking only TreeGrafter, a `501` with problem details shown as "couldn't be started", and the job page showing an `hmmscore` job's PANTHER 19;
  - the `@api` e2e spec submits the example against a real API with the data sample, and checks the hit's PANTHER ID and name. Not its E-value, which depends on the library: `2.2e-133` on the sample, `7e-131` on the full library. It replaces the spec that expected the `501`. The spec that rewrites the request in flight to get the real `422` stays.

### 8. The data, in compose, the docs and on the server

- **compose:** the `api` service already mounts `.data/` at `/data`; its comment names the hmmscore sample, fetched with `panther-engine hmmscore sample fetch --data-dir ../.data`, beside the cSNP and refmap data. Without it, every `hmmscore` job fails with the generic error.
- **`docs/testing/api.md`:** the hmmscore section shows a real job with the example on the data sample, and the time limit's failure; the settings table drops "takes effect when hmmscore's scoring is wired in"; the `501` goes; the links to `add-hmmscore-job` point to its archive.
- **`docs/deployment/runbook-server.md`:** the full library under `hmmscore/19/`, 67 GB, downloaded on the host and passed to `panther-engine hmmscore data fetch --tarball`, as the refmap data is, since the container doesn't trust the server's proxy's CA; and the four settings, whose values the engine developer sets from measuring there (#68). It names no memory figure for the server.

## Risks / Trade-offs

- **[The message after a short query's time limit]** → "Try a shorter sequence" fits a long query. A short one reaches its limit only when the server is overloaded, where trying again later is the better advice. The message is the engine's; this change keeps it, and the runner's log line, with the residues and the limit, shows which case it was.
- **[A long query needs more memory than the server has]** → At `--cpu 0`, `titin-10000` peaked at 6.0 GiB on the full library (#68). If the server can't give a job that much, `hmmscan` is killed, and the job fails with the generic `500`, or it swaps and runs past the time limit, and fails with the `422`. Other jobs keep running. The engine developer measures it there with the deploy, and sets a lower residue limit if needed, recorded in row 11 (open question).
- **[The kernel kills the worker, not the tool]** → If the out-of-memory killer picks the worker process instead of `hmmscan`, the pool breaks, and the job running beside it fails too, as `scoring-jobs`' "Recover from a dead worker" allows. The pool is replaced, and later jobs run.
- **[A backlog of hmmscore jobs refuses other services]** → The waiting cap is shared, and the `503`'s `Retry-After` is 30 s, sized for cSNP. With the defaults, 50 waiting `hmmscore` jobs, each up to 720 s, refuse a `csnp` job that would wait. #80 proposes a waiting limit and a `Retry-After` per job type; until then, the busy message asks the user to try again in about 30 seconds.
- **[A restart waits for a running search]** → On shutdown, `JobRunner.close()` waits for running jobs, and an `hmmscore` job may run for minutes. Docker stops the container after its grace period; jobs don't survive a restart either way (`scoring-jobs`, "Jobs expire").
- **[The sample isn't the library]** → The API's tests, CI and the `@api` spec score against the sample, where E-values differ from the full library's. They check the sample's own goldens, and the `@api` spec checks only the ID and the name. The engine's full-library goldens (#81) prove the scoring on the real library.
- **[The data isn't on the server]** → `hmmscore` jobs fail with the generic `500`, and the startup log says why. The runbook has the fetch; doing it is the engine developer's.

## Migration Plan

Deploy order: the library on the server, then the API and the site together. The API without the library still starts, and only `hmmscore` jobs fail. Rollback is reverting the change and regenerating the frontend's types: the `501` and the "coming soon" mark come back together.
