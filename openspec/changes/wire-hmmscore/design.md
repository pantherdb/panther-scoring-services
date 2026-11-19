# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **The engine is a library; scoring goes through jobs; the website moves to the JSON API:** [docs/design/tech-stack.md](../../../docs/design/tech-stack.md). Workers are `spawn` processes (API recommendation 1).
- **What the API serves and where, and what the server holds:** [docs/design/api-stack.md](../../../docs/design/api-stack.md) and [docs/design/hosting.md](../../../docs/design/hosting.md).
- **The contract, the input rules, the settings and the running cap:** the archived [add-hmmscore-job](../archive/2026-11-16-add-hmmscore-job/design.md), decisions 2 (the result), 3 (the rules), 4 (the engine interface), 5 (the settings and their defaults), 6 (the running cap) and 7 (the residue limit in the router). Its Migration Plan lists this change's work.
- **The form and the results:** the archived `add-hmmscore-form` (#79, archived in #82), whose Risks say this change removes the `501` requirement and the notice, and keeps the submit failures.
- **The pattern:** the archived [wire-refmap](../archive/2026-11-10-wire-refmap/design.md): decision 1 (the job calls the engine in the worker), decision 6 (one startup check per service), decision 9 (each job names its own service's data), and how it removed refmap's `501`.
- **The engine's scoring:** [port-hmmscore](../port-hmmscore/design.md), decision 4 (the time limit, threads and failures) and decision 7 (the goldens).

**What exists:**

- **The engine** (`port-hmmscore`, #81, merged): `panther_engine.hmmscore` exports `DATA_VERSION` (`"19"`), the frozen dataclasses `HmmscoreInput(sequence)`, `HmmHit(panther_id, name, evalue, score, alignment)` and `HmmscoreResult(hit)`, `score(request, *, data_dir=None, cpu=0, timeout=None)`, `check_data(data_dir=None)` and `HmmscoreError`. It's decision 4 of `add-hmmscore-job`, unchanged. `score()` raises, in order:
  - `ValueError` for a sequence that isn't upper-case letters, `.`, `_`, `~` and `*` with a letter, which the API never sends;
  - `DataFolderError` when `PANTHER_DATA_DIR` isn't set, and `MissingDataError` when the folder lacks `globals/names.tab`, the four pressed `binHmm` files or `books/` (`check_data`);
  - today, `InputError("The search took longer than this service allows. Try a shorter sequence.")` once the whole search passes `timeout`, after killing the running tool; group 0 replaces it with a timeout error of the engine's own (decision 3);
  - `HmmscoreError` for a tool that exits non-zero, can't run or writes nothing readable, or a missing model file;
  - `LibraryFormatError` (`hmmscore.library`) for a broken `names.tab`.

  `cpu` goes to both `hmmscan` and `hmmsearch` as `--cpu`. `core/process.py`'s `run_tool` runs each tool with `subprocess.run`, in the worker's own session. `hmmscore.parity` reads the goldens (`read_cases`, `Case.sequence`, `expected_result`), and has no `__all__`.
- **The API** (`add-hmmscore-job`, #76): `jobs/hmmscore.py`'s request and result models, which mirror the engine's dataclasses field for field; the residue limit in the router; the running cap in `JobRunner`; the four settings, two of which, the time limit and `--cpu`, nothing reads yet; `UNAVAILABLE`'s row, the router's `501` branch and its schema entry, and `run_job`'s case that raises `NotImplementedError`.
- **The form** (`add-hmmscore-form`, #79): the form, the checks, the results and the alignment, built against the contract; `services.ts` keeps HMM scoring's `comingSoon: true`, which shows the badge and the notice; `submitProblem`'s `unavailable` shows the `501`.

## Goals / Non-Goals

**Goals:**

- A valid `hmmscore` request scores with the engine, end to end, in the API and the form.
- The time limit and the thread count reach `score()`, from the API's settings, and a job past its limit is told to try again later.
- No tool outlives the worker that started it.
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
- **Exceptions pass through,** and the runner sorts them:

  | Raised | The job |
  | ------ | ------- |
  | The engine's timeout error (decision 3) | `failed`, `503`, the API's time limit `detail` |
  | `HmmscoreError`, `LibraryFormatError`, `MissingDataError`, `DataFolderError` | `failed`, `500`, the generic `detail`; the message goes to the log |
  | `ValueError` | The same. It can't happen for a request the API accepted, so reaching it is a bug, and a `500` is right |

  Nothing about a `500`'s exception reaches the job, so a data path or a tool's standard error stays in the log.
- **The engine module is imported at module level,** as `jobs/csnp.py` and `jobs/refmap.py` import theirs. The API process imports it anyway, for the startup check (decision 4).
- **The `501` mechanism goes, on both sides.** No service answers `501` once hmmscore runs, so the API drops `UNAVAILABLE`, `Unavailable`, the router's `501` branch and the `if UNAVAILABLE:` block that documents it, and the frontend drops `unavailable` (decision 6). `add-treegrafter-job` brings a `501` back, with its own requirement, if its contract comes before its engine. The test that no `501` is documented becomes a plain check of the schema, with no router to reload.

### 2. The settings reach the worker as the job's options

A worker is a `spawn` process: it imports `work.py` afresh, and gets everything from `run_job`'s arguments (`api/CLAUDE.md`, "Jobs"). The settings are read once, in the lifespan. So:

- **`work.py` gains `JobOptions`,** a frozen dataclass of what the work needs from the settings: `hmmscore_cpu`, `hmmscore_time_limit_seconds` and `hmmscore_min_time_limit_seconds`. `run_job(request, options)` passes them to `run_hmmscore`; the other cases ignore them.
- **`JobRunner` takes `options`** when it's built, from the settings in `main.py`'s lifespan, and submits `run_job(request, options)` for every job. A test that builds a `JobRunner` passes its own.
- **Every caller of `run_job` changes with it:**
  - the pure stand-ins in `tests/job_helpers.py` take the second argument and ignore it;
  - `score_with_a_fake_engine` (`job_helpers.py` 125) isn't a pure stand-in: it calls the real `run_job`, so it passes the options on, or the cSNP tests that use it fail with the generic `500`;
  - the direct calls in `tests/test_jobs.py` (118, 585 and 890) and `tests/test_refmap_jobs.py` (135) pass options.

*Alternatives:*

- **The worker reads the settings itself,** from the environment it inherits. Rejected: it validates them a second time, in another place, and a test that builds `Settings` directly wouldn't reach it.
- **A pool initializer** that stores the options in the worker. Rejected: state set up in the worker, beside the rule that it gets everything from `run_job`'s arguments, and a pool replaced after a dead worker must be given them again.
- **The options inside `HmmscoreJobRequest`.** Rejected: the request is the contract, and these aren't the client's to set.

### 3. The time limit

- **It counts from when `score()` starts,** in the worker, not from the job's submission. A job waiting for the running cap or a worker doesn't use it up. `hmmscan` gets what's left of it, then `hmmsearch` what's left after that (port-hmmscore, decision 4).
- **It grows with the sequence's length.** A job's limit is `floor + (ceiling − floor) × residues ÷ 10,000`, rounded to the nearest second. The ceiling is `PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS` (720), and the floor is a new `PANTHER_API_HMMSCORE_MIN_TIME_LIMIT_SECONDS` (120). With the defaults, APOE's 317 residues get 139 s, Q14204's 4,646 residues 399 s, 5,000 residues 420 s, and 10,000 the full 720 s. A search's time grows with its length: APOE took 13 s and `titin-10000` 231 s on the full library (#68). So a short query that runs far longer than it should, on an overloaded server, is stopped in about two minutes, not twelve, and frees the one running slot for the jobs waiting behind it.
- **It divides by 10,000, the most the API ever takes,** `settings.HMMSCORE_MAX_RESIDUES`, the residue setting's upper bound, not the setting itself. A search's time depends on its length, not on the server's residue limit: if the deploy lowers `PANTHER_API_HMMSCORE_MAX_RESIDUES` to 5,000 for memory, APOE keeps 139 s and a 5,000-residue query 420 s, rather than 158 s and the full 720 s.
- **The floor** covers what every search costs whatever its length: `hmmscan` reads all of `binHmm.h3f`, 4.9 GB, which is slower when the server can't keep it cached. Settings validation requires the floor to be at least 1 and at most the ceiling; equal values give every job the same limit.
- **720 s stands as the ceiling.** `titin-10000`'s 231 s is under the 240 s estimate the default was scaled from. A slower server may need other values; those are the server's (#68), set once the deploy has measured a short and a long query there.
- **It's divergence row 14, proposed.** A job past its limit fails where the reference would have answered. On Endeavour's timings at `--cpu 0`, the limits are about 10 times APOE's, 4 times Q14204's cold run and 3 times `titin-10000`'s. The engine developer approves the row before the code ships.

**Past the limit:**

- **The engine raises a timeout error of its own** (task 0.1), not its input error. A long query can reach its limit because it's long, but a short one reaches it only when the server is busy: swapping, or reading `binHmm.h3f` uncached. So the time limit isn't the input's fault. The exception's name is the engine developer's; `panther_engine.hmmscore` exports it, and it crosses from the worker to the API process with its type, as an input error does (`engine-core`, "Input errors").
- **The job fails with status `503`,** the server unable to finish it now, and the API's `detail`: "The search took longer than this service allows. The server may be busy: try again later, or with a shorter sequence." The API owns the message, with the status, so the engine no longer needs to export `TIME_LIMIT_MESSAGE`, and the API's tests import the API's own constant. The job page shows the `detail` as for any failed job.
- **The log line** is a `WARNING`, the runner's own outcome for this case, without a traceback: "failed 503, past its time limit of 139 s", in the usual finish line, which has the job's residues (`log_summary()`) and how long it ran. The runner works out the limit from the request it holds and the options, as `run_hmmscore` did, so the line needs nothing from the exception.
- *Alternative:* keep the input error and its `422`. Rejected: it tells the submitter of a short query to shorten it, which can't help, and the log records a busy server as bad input.

### 4. Startup: hmmscore's data check

`main.DATA_CHECKS` gains `("hmmscore", "hmmscore", panther_engine.hmmscore)`, after `csnp` and `refmap`. Its check is a few `stat`s, no file read, in the threadpool beside the others. Missing data logs "hmmscore jobs will fail until the hmmscore data is in place: …", with the engine's message, and the API still starts. The checks stay independent: missing hmmscore data doesn't stop `csnp` or `refmap` jobs, nor the reverse.

- **The data sample passes the check.** It holds the same parts as the full library (`names.tab`, the pressed `binHmm` files, `books/`), so a developer's `.data/` with the sample logs no error. The check doesn't tell the sample from the library: `hmmscore data verify` does.
- **The startup tests count each service's line,** so they change: in `tests/test_limits.py`, `csnp, refmap = main_records(caplog)` (295), the three `[record] = main_records(caplog)` tests (312, 332, 346), the unset folder's `== ["csnp", "refmap"]` (364) and `test_complete_data_logs_nothing` (382). Each gets a third, hmmscore, record unless its fixture provides the hmmscore sample's parts.

### 5. Versions

`versions.read_versions()` lists `DataVersion(service="hmmscore", panther=DATA_VERSION)` after refmap's, in the order the services were ported. `Versions.for_service` already gives each job its own, so an `hmmscore` job's `versions.data` is `[{"service": "hmmscore", "panther": "19"}]`. HMMER's version is already in the report, as the `hmmscan` and `hmmsearch` tools, and in every job's `versions.tools`.

### 6. The form

- **`services.ts`:** HMM scoring's `comingSoon` becomes `false`. Its tab and its home page card lose the mark, and its page loses the badge and the notice, which read the flag.
- **The notice goes** with its requirement: `NotAvailableNotice` in `HmmscorePage.tsx`, and the tests that looked for it. The page keeps reading the flag for the badge, as the home page and the tabs do.
- **The `501` path goes:** `submitProblem`'s `unavailable`, `SubmitAlert`'s text for it, and their tests, as the API's `UNAVAILABLE` goes (decision 1). A `501` with problem details is `failed`, "couldn't be started", as for refmap since `wire-refmap`. A `501` without problem details still came from something in between, and stays `unreachable` (`isUnreachable`). `SubmitAlert`'s `limited` keeps showing `busy` as `failed` for cSNP and refmap, until #80.
- **A job past its time limit:** the job page shows its `503` `detail` and no result, as "Failed job shows its error" requires of any failed job. The job's `error.status` is data in a `200` poll, not the poll's status, so it isn't read as an unreachable API. A unit test covers it.
- **The mocks:** the versions list hmmscore's PANTHER 19, so a mocked `hmmscore` job's page shows it. The mocked hit stays the made-up `PTHR00000:SF1`. The comments that say the real API answers `501` go.
- **The types:** `npm run api:types` drops the `501` from `schema.d.ts`; nothing else in the contract changes.

### 7. Tests and data

- **Without the data or the tools** (CI's `api` job, Windows natively): the job's options reach `run_hmmscore` (decision 2), with the time limit by length; `run_hmmscore` maps the engine's result field for field, with the engine's `score` replaced in-process; the engine's timeout error fails the job with a `503` and the API's `detail`, through a stand-in `run_job` in `job_helpers.py`; `HmmscoreError` and `ValueError` fail it with the generic `500`, without their messages; a valid request gets `202`; the schema has no `501`; the startup check logs hmmscore's error alone; the versions report and a job's versions.
- **With the tools and the data sample** (marked `tools("hmmscan", "hmmsearch")` and `data("hmmscore")`), a new `tests/test_hmmscore_scoring.py` runs real jobs through the API:
  - the form's example, APOE: `PTHR18976:SF2`, "APOLIPOPROTEIN E", score `439.0` and the alignment, as the golden gives them;
  - `no-hit`: `{"hit": null}`;
  - `tie-pthr35774`: `PTHR35774:SF1` (row 13);
  - a time limit too short to finish: the engine's timeout error. It calls `run_hmmscore` in-process with a timeout of a millisecond, since the setting is whole seconds.
- **The goldens come through the engine:** `panther_engine.hmmscore.parity`'s `read_cases`, `Case.sequence` and `expected_result`, which apply row 13's pick, the "No name" rule and the sample's arm64 copies. Reading the files directly is easy to get wrong: `tie-pthr35774`'s `cgi.xml` has the CGI's hash-order pick, `PTHR35774`. `parity.py` gets an `__all__` with them (task 0.3), as `api/CLAUDE.md` asks before the API imports a module.
- **Only the image's HMMER:** `tests/markers.py`'s `tools()` checks only that the programs are on `PATH`. For `hmmscan` and `hmmsearch`, it also skips, or fails where tools are required, when the version found isn't the image's, as the engine's `conftest.py` (`other_hmmer`) does, reusing `hmmer_version` and `HMMER_VERSION` from `panther_engine.hmmscore.sample`. A developer with HMMER 3.1b2 or 3.3 on `PATH` then gets skips, not failures: 3.1b2 can't read the sample's presses, and other versions can differ from the goldens. `hmmscore` joins `DATA_MANIFESTS`, with the sample's manifest.
- **CI's `api-image` job,** on both architectures, restores the hmmscore sample from the cache the engine jobs fill, fetches it with the image's CLI, which checks it, runs `tests/test_hmmscore_scoring.py` with the tools and data required, and scores APOE through the running API with `curl`, as it does a cSNP protein. The image has HMMER 3.4.
- **The frontend:**
  - unit tests: no badge or notice on `/hmmscore`, the tabs and the home page marking only TreeGrafter, a `501` with problem details shown as "couldn't be started", the job page showing an `hmmscore` job's PANTHER 19, and a job past its time limit showing its `detail`;
  - the `@api` e2e spec submits the example against a real API with the data sample, and checks the hit's PANTHER ID and name. Not its E-value, which depends on the library: `2.2e-133` on the sample, `7e-131` on the full library. It replaces the spec that expected the `501`. The spec that rewrites the request in flight to get the real `422` stays.

### 8. The data, in compose, the docs and on the server

- **compose:** the `api` service already mounts `.data/` at `/data`; its comment names the hmmscore sample, fetched with `panther-engine hmmscore sample fetch --data-dir ../.data`, beside the cSNP and refmap data. Without it, every `hmmscore` job fails with the generic error.
- **`docs/testing/api.md`:** the hmmscore section shows a real job with the example on the data sample. It shows no time limit example: on the sample a search finishes within a second, the setting's least, so a job would succeed. It says the tests cover the time limit. The settings table drops "takes effect when hmmscore's scoring is wired in"; the `501` goes; the links to `add-hmmscore-job` point to its archive.
- **`docs/deployment/runbook-server.md`:** the full library under `hmmscore/19/`, 67 GB, downloaded on the host and passed to `panther-engine hmmscore data fetch --tarball`, as the refmap data is, since the container doesn't trust the server's proxy's CA; and the hmmscore settings, whose values the engine developer sets from measuring there (#68). It names no memory figure for the server.
- **`docs/parity/divergences.md`:** row 14, proposed, with its approver blank (decision 3).

### 9. A tool doesn't outlive its worker

`run_tool` starts each tool with `subprocess.run`, in the worker's session. When the worker dies, from the out-of-memory killer's `SIGKILL` or the signal a broken pool sends its other workers, nothing reaches the tool. It's orphaned: it runs to the end with no time limit, up to 6 GiB for `titin-10000`; its temporary folder is never removed; and since `JobRunner._run` releases the hmmscore cap when the pool breaks, the replacement pool starts the next hmmscore job beside it, two large searches under the memory pressure that broke the pool.

So `run_tool` makes sure a tool dies with the process that started it (task 0.2). The mechanism is the engine developer's choice:

- **`PR_SET_PDEATHSIG`:** on Linux, the child asks the kernel for `SIGKILL` when its parent dies, through `prctl` in a `preexec_fn`, and checks its parent is still there afterwards, in case it died first. It needs nothing from the API. A worker runs its tasks on its main thread, the one the signal follows.
- **A session per tool:** `start_new_session=True`, and the runner kills the dead worker's tools' sessions when it replaces the pool. It also covers a worker that outlives a broken pool, but the API needs a way to find those sessions, from the engine.

Either way, a test starts a long-running tool from a child process, kills the child, and checks that the tool is gone. Elsewhere than Linux, where only developers run the API, the first does nothing.

## Risks / Trade-offs

- **[A long query needs more memory than the server has]** → At `--cpu 0`, `titin-10000` peaked at 6.0 GiB on the full library (#68). If the server can't give a job that much, `hmmscan` is killed, and the job fails with the generic `500`, or it swaps and runs past its time limit, and fails with the `503` and the advice to try again later or with a shorter sequence. Other jobs keep running. The engine developer measures it there with the deploy, and sets a lower residue limit if needed, recorded in row 11 (open question).
- **[The kernel kills the worker, not the tool]** → If the out-of-memory killer picks the worker process instead of `hmmscan`, the pool breaks, and the job running beside it fails too, as `scoring-jobs`' "Recover from a dead worker" allows. The tool dies with its worker (decision 9), so it can't run on beside the next hmmscore job, and the cap of 1 holds. What's left is its temporary folder, the query and a partial table, in the system's temporary directory. The pool is replaced, and later jobs run.
- **[A busy server fails short queries]** → A job past its limit fails with the `503`, whose `detail` says the server may be busy. The log line gives its residues, its limit and its run time, so a run of short jobs failing says the server is overloaded, not that the input is bad. The server's values for the floor and the ceiling come from measuring there (#68).
- **[A backlog of hmmscore jobs refuses other services]** → The waiting cap is shared, and the submit `503`'s `Retry-After` is 30 s, sized for cSNP. With the defaults, 50 waiting `hmmscore` jobs, each up to 720 s, refuse a `csnp` job that would wait. #80 proposes a waiting limit and a `Retry-After` per job type; until then, the busy message asks the user to try again in about 30 seconds.
- **[A restart waits for a running search]** → On shutdown, `JobRunner.close()` waits for running jobs, and an `hmmscore` job may run for minutes. Docker stops the container after its grace period; jobs don't survive a restart either way (`scoring-jobs`, "Jobs expire").
- **[The sample isn't the library]** → The API's tests, CI and the `@api` spec score against the sample, where E-values differ from the full library's. They check the sample's own goldens, and the `@api` spec checks only the ID and the name. The engine's full-library goldens (#81) prove the scoring on the real library.
- **[The data isn't on the server]** → `hmmscore` jobs fail with the generic `500`, and the startup log says why. The runbook has the fetch; doing it is the engine developer's.

## Migration Plan

Deploy order: the library on the server, then the API and the site together. The API without the library still starts, and only `hmmscore` jobs fail. Rollback is reverting the change and regenerating the frontend's types: the `501` and the "coming soon" mark come back together. Group 0's engine changes can ship first: until the API calls `score()`, nothing sees the timeout error, and `run_tool`'s change applies to every service's tools.
