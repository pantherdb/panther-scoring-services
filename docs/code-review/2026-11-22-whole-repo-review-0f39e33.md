# Whole-Repository Review at `0f39e33`, 2026-11-22

**Reviewed:** the code. That's `engine/` (`core/`, `csnp`, `hmmscore`, `refmap` and the `treegrafter` stub), `api/` and `frontend/`; the root `Dockerfile` and `compose.yaml`; and the frontend's image and nginx template. GitHub process (rulesets, CODEOWNERS, the pull request workflow and Dependabot) was out of scope. The docs and specs were read only to check the code against them.

**Commit:** `0f39e33`, on `chore/archive-add-hmmscore-form`. That's `main` after #81 (`port-hmmscore`), plus one commit archiving `add-refmap-classification`. The last whole-repository review was at `64174c9` on 2026-10-30. The 167 commits since then brought:

- refmap's engine, data, wiring and classification endpoint;
- hmmscore's job contract, form and engine port;
- the API limits, logging and CORS;
- the deploy work.

`main` has since gained #82 and #83 (`wire-hmmscore`), and HMM scoring is deployed on the server (#68). Neither pull request was reviewed here. "After `0f39e33`" says which findings they change.

**Reviewer:** tmushayahama.

**How it was checked:** one pass per area:

- the engine's `core/` and `csnp`, against the Perl at `cebb5ab`;
- the engine's `hmmscore` and `refmap`, against `pantherScoring` and `RefProteomeMapper`;
- the API;
- the frontend;
- the images.

Every finding of Medium severity was then read again against the code at `0f39e33`, and each finding says how it was checked:

- **reproduced:** run, with the result given;
- **traced:** the code path read end to end;
- **suspected:** plausible, not confirmed.

No code was changed. Experiments ran in a scratch folder outside the repository. Images ran with `.data/` mounted read-only, and `../panther-workspace` was only read.

## Summary

- **No finding is High.** Nothing found makes `hmmscore` or `refmap` give a wrong scientific result for any input the API sends. Both match their Perl closely, and every deliberate difference found has a row in `divergences.md`. cSNP's steps 2 and 3 still match the Perl line for line. One input case is silently mishandled: a stray character in the sequence (CSNP-101).
- **The main risks are operational:**
  - data tooling that can silently swap or half-replace a library (HMM-1, HMM-2, REFMAP-1);
  - a job store whose memory and per-submit cost grow with traffic (API-101);
  - a site deployed under a path calls its API at the wrong address (FE-101).
- **Native Windows is broken in two places**, though developers run the suites there:
  - `import panther_engine.cli` fails on `import resource` (HMM-3);
  - one API test always fails (API-107).

  CI runs on Linux and passes.
- **hmmscore was ported but not wired at `0f39e33`.** The API answered `501`. #83 has since wired it, and it now runs on the server, so HMM-1 is a live risk there.
- **The earlier review's Medium findings are nearly all fixed.** Of the nine in scope, eight are fixed. CSNP-2, the species filter, still waits on the science owner. Most of its Low findings still hold. "Earlier Findings" has the status of each.
- **Full-library parity for cSNP isn't proven yet.** `docs/parity/` has no dated report of the staging run.

## Checks Run

| Check | Where | Result |
| --- | --- | --- |
| Engine: ruff, format, basedpyright, pytest | `panther-engine` image built from `0f39e33`, with `.data/` (csnp and hmmscore samples, refmap data) | Clean; **1503 passed** in 75 minutes |
| Engine: `import panther_engine.cli` | Native, Windows | **Fails**: `ModuleNotFoundError: No module named 'resource'` (HMM-3) |
| API: ruff, format, basedpyright, pytest | Native, Windows | Clean; 516 passed, 8 skipped, **1 failed** (API-107) |
| API: `openapi.json` against the code | Native | The same, once line endings are ignored |
| API: live jobs, load and large bodies | `panther-api` image on port 8001, with `.data/` | Used for API-101, API-104 and API-105 |
| Frontend: type-check, lint, unit tests | Native | Clean; 36 files, 552 tests |
| Frontend: `schema.d.ts` against `openapi.json` | Regenerated into scratch | Byte-identical |
| Frontend against API input rules | 6,025 generated sequences through both `checkSequence` and the API's models | **0 disagreements** |

Playwright wasn't run: it writes `dist/` and report folders into the working copy.

## Findings

IDs continue from the earlier review's. The new engine findings are `HMM-n` and `REFMAP-n`, with `CSNP-101` and `CORE-101` on; the API's are `API-101` on and the frontend's `FE-101` on.

### Medium

#### CSNP-101. BLAST+ silently drops characters it ignores, so positions count residues only, and divergence row 8 says these sequences are refused

- **Where:**
  - `engine/src/panther_engine/csnp/blast.py:112-119` ignores `blastp`'s standard error whenever it exits 0;
  - `csnp/scoring.py:24` (`SEQUENCE = [!-~]+`) accepts any printable character;
  - `docs/parity/divergences.md` row 8.
- **What's wrong:**
  - BLAST+ 2.17.0 drops any character other than a letter or `*` from a query of normal length, such as `- . ~ _ + ? ( ! > < @` and digits. It exits 0 and only warns on stderr: `FASTA-Reader: Ignoring invalid residues at position(s): On line 2: 21`. The engine throws that warning away.
  - The positions mapped after that count residues only, not the characters submitted.
  - Row 8 says sequences "with `.`, `~`, `?` or brackets" are refused with a `422`. That's true only when BLAST+ judges the whole sequence implausible, as for `MKVL.`. The same characters inside a 317-residue protein are dropped without a word.
- **What could go wrong:** the user is never told that BLAST+ ignored part of the input, and which numbering they meant is ambiguous:
  - A user who counts the stray character gets the neighbouring residue's score. Take the form's APOE example with a `.` added at position 21. `L70A`, meant as character 70 (residue 69), comes back scored as residue 70: age 91 and pDel 0.19, instead of 176 and 0.27.
  - Wherever two adjacent residues are the same, the wild-type check can't catch the shift. APOE has 16 such pairs after position 21, and in 8 of them the two positions score differently: `A117` gives 361, "possibly damaging", while 118 gives 176, "probably benign".
  - Elsewhere the shift shows only as "Invalid substitution", which hides the real cause.
  - A user counting UniProt residues gets the right answer.

  hmmscore refuses the same characters (row 12), so the two services treat one input differently.
- **Parity:** the legacy site didn't check characters either (`CsnpScoreForm.java` removed only whitespace), so production very likely did the same. Which BLAST+ production ran needs team verification.
- **Checked:** reproduced in the engine image with the data sample. BLAST+ reported `qend` 317 for the 318-character sequence. The code path and row 8 were then read at `0f39e33`.
- **Fix:**
  - in `search()`, turn the "Ignoring invalid residues" warning into an `InputError` that names the positions;
  - or refuse anything but letters and `*` before searching, as the API's rule;
  - either way, correct row 8 and log the change as a divergence row.

#### HMM-1. `hmmscore sample fetch` into a folder holding the full library replaces its globals, and every search then runs against 14 families

- **Where:**
  - `engine/src/panther_engine/hmmscore/sample.py:362-389`;
  - `check_data` in `hmmscore/scoring.py:172`.
- **What's wrong:** the sample goes into the same `hmmscore/19/` as the full library. Unlike cSNP's sample, it isn't a byte-identical subset: its `globals/names.tab` and `globals/binHmm.h3{f,i,m,p}` are its own (`hmmscore/sample.json`). On a folder holding the full library:
  1. `verify(root, files)` fails on those five files;
  2. `fetch` downloads the sample and `os.replace`s them over the full library's;
  3. `check_data()` still passes, because it only checks that files exist;
  4. every later `hmmscan` runs against about 450 models.
- **What could go wrong:** most proteins get "No hit" or a wrong family, with no error and nothing in the log. The trigger is one documented command run on a server whose `PANTHER_DATA_DIR` holds production data. Since #68, the server holds the full library. Recovering means streaming the 18.5 GB tarball again.
- **Checked:** reproduced with the engine's own `sample.fetch`, a stand-in manifest and a stand-in tarball. Afterwards `names.tab` and `binHmm.h3m` were the sample's, a full-library-only book was still there, and `check_data()` passed. The paths were confirmed against `sample.json` at `0f39e33`.
- **Fix:**
  - refuse when the full library's `books.sha256` is present;
  - or keep the sample under its own version folder;
  - or have `check_data()` compare `names.tab`'s size with the pin it expects.

#### HMM-2. An interrupted `hmmscore data fetch` leaves up to 67 GB staged, and its moves aren't atomic

- **Where:**
  - `engine/src/panther_engine/hmmscore/data.py:335` (staging) and `:359` (the move loop);
  - the CLI help, which promises the fetch "writes nothing under hmmscore/19/ if anything fails".
- **What's wrong:**
  - The staging folder `.hmmscore-fetch-*` sits in the data root. `TemporaryDirectory` cleans it up only on a Python exception:
    - SIGHUP, from an SSH session dropping during a multi-hour stream, ends the process with no cleanup;
    - so does SIGTERM, from `docker stop`.
  - The staged copy then stays, and no later fetch removes it, so the next attempt needs another 67 GB.
  - The files then move one `os.replace` at a time. A permission error or an `EXDEV` part-way through leaves two releases mixed. `EXDEV` happens with `globals/` on another volume, as legacy production had `binHmm`.
- **Checked:** traced. The move loop is the same pattern as ENG-6, which the earlier review reproduced for cSNP.
- **Fix:**
  - remove stale `.hmmscore-fetch-*` folders when a fetch starts;
  - turn SIGTERM and SIGHUP into `SystemExit` while fetching;
  - stage beside `hmmscore/19/` and swap the whole folder in with one rename.

#### HMM-3. `import resource` breaks every `panther-engine` command and 12 test modules on native Windows

- **Where:** `engine/src/panther_engine/hmmscore/cli.py:7`, imported at import time by `engine/src/panther_engine/cli.py:9`.
- **What's wrong:** `resource` is POSIX-only. So natively on Windows:
  - `panther-engine csnp …` fails, and so do `refmap …` and `hmmscore …`;
  - `pytest` can't collect 12 modules, among them `test_refmap_*` and `test_csnp_cli`.

  This undoes the care refmap's tooling takes to keep file names Windows-safe. `docs/testing/engine.md` documents native `uv run pytest`, and the team develops on Windows. The API is unaffected: it imports `panther_engine.hmmscore`, not its CLI.
- **Two Windows-only test failures nearby:**
  - `test_hmmscore_scoring.py`'s 12 fake-tool tests fail instead of skipping, because `shutil.which` doesn't find fakes with no extension;
  - `test_refmap_mapping.py:212` writes its fixture with `write_text`, which gives CRLF. The port then keeps the `\r`, as it should (refmap row 10), and the assertion fails.
- **Checked:** reproduced. `uv run python -c "import panther_engine.cli"` in `engine/` gives `ModuleNotFoundError: No module named 'resource'`.
- **Fix:**
  - import `resource` inside `peak_memory_mib()`;
  - write the test fixtures with `write_bytes` or `newline=""`;
  - skip the fake-tool tests on Windows.

#### API-101. The job store's memory, and the time each submit takes, grow with the number of jobs, and the results budget doesn't bound either for small jobs

This extends API-8.

- **Where:**
  - `api/src/panther_api/jobs/store.py:88-89`, where `add` checks every stored job for expiry on each submit;
  - `store.py:122-145`, where `_finished_with` sorts every finished job when the budget is exceeded.
- **What's wrong:**
  - The budget counts each result's JSON: 80 bytes for a one-ID refmap result.
  - The record behind it, a `JobRecord` with its own `Versions` and result, is about 1.2 KB. So 200,000 finished one-ID jobs count as only 15 MiB of the 256 MiB budget, and nothing expires them for 24 hours.
  - Each accepted `POST` then scans all of them on the event loop.
- **What could go wrong:** one client with 8 threads got 5 refmap jobs a second accepted on the live image: about 430,000 a day. Within a day that's about 520 MB of records and about 0.4 s of blocked event loop on every submit, which delays every poll and health check.
- **Checked:** reproduced. In process, 200,000 finished jobs take about 1.2 KB each, and `add()` then takes 201 ms; the cost is linear in the number of jobs. The rate was measured on the live image.
- **Fix:**
  - keep jobs in creation order, and drop expired ones from the front, so a sweep stops at the first unexpired job;
  - count a fixed per-job overhead, about 2 KB, in the budget, or cap the number of jobs kept.

#### FE-101. Under a path, the `web` image's site calls the API at the root of the origin, so every API call fails

- **Where:** `frontend/src/app/apiBaseUrl.ts:9-12`; `docs/deployment/runbook-server.md`, "A path such as `/scoring/`".
- **What's wrong:**
  - The runbook's path setup builds with `BASE_PATH=/scoring/`, and has the server's front end forward only `location /scoring/ { proxy_pass …/; }`.
  - `apiBaseUrl()` ignores the base path. With `VITE_API_BASE_URL` empty, the app calls `/api/v1/…` at the origin's root, and the front end never forwards that.
- **What could go wrong:** following the runbook gives a site where:
  - the footer says the versions are unavailable;
  - the species and organism lists fall back to the typed-code box;
  - every submit says the job couldn't be started;
  - the API docs link is dead.
- **Checked:** traced through `apiBaseUrl.ts` and the runbook.
- **Fix:** default the base to `${import.meta.env.BASE_URL}api/v1`, or have the runbook build with `--build-arg VITE_API_BASE_URL=/scoring`. `apiBaseUrl` already accepts a value that's only a path.

#### FE-102. A CSV file, or a second column separated by spaces, is read as IDs

- **Where:** `frontend/src/features/refmap/ids.ts:14` (`SEPARATORS = /[\s,]+/`); `IdsField.tsx:56` accepts `.csv` and `text/csv`.
- **What's wrong:** only a tab ends the first column; every comma and space splits an ID. Loading `gene,log2fc\nP04217,1.5\nP01023,-0.2` sends six IDs: `gene`, `log2fc`, `P04217`, `1.5`, `P01023` and `-0.2`. The file picker invites exactly that file.
- **What could go wrong:** the results report six IDs, half with no PANTHER family, and the header and values go into the TSV download. A user with a real gene list gets a result padded with noise, with no warning.
- **Checked:** reproduced with `splitIds`. This follows `scoring-ui` ("split … at every run of whitespace and commas"), so fixing it needs a spec change first.
- **Fix:** for a `.csv` file, read the first comma-separated column, or warn when a line gives more than one ID. Otherwise drop `.csv` from `accept`.

#### FE-5. When the job id changes on a mounted job page, the previous job's result shows under the new address

From the earlier review; it still holds and is raised from Low.

- **Where:** `frontend/src/features/jobs/JobPage.tsx:12` reads `data` from `useJob(id)`; the route doesn't key the page by id.
- **What's wrong:** going from `/jobs/A` to `/jobs/B` shows A's heading and table while B loads. Both ways in reproduce it: the browser's history menu and a link between jobs.
- **What could go wrong:** the user sees A's scores, mappings or hit as B's. The same stale data leaves `MappingsTable` on a stale page and points "Edit and resubmit" at A.
- **Checked:** reproduced.
- **Fix:** key the job page by id in the router, or use `currentData` instead of `data`.

### Low

#### Low: Engine Core and cSNP

##### CSNP-102. `csnp score` ends in a traceback when the data folder is incomplete

- **Where:** `engine/src/panther_engine/csnp/cli.py:495-502`. Its handlers don't catch `MissingDataError`, which is new in `core/data.py:34`. `run_parity` (`cli.py:545`) catches neither that nor `LibraryFormatError`.
- **What could go wrong:** the check an operator runs after a deploy prints a full traceback instead of the message. The message is good: it lists exactly which files are missing.
- **Checked:** reproduced. `panther-engine csnp score q.fasta A10E --species HUMAN --data-dir /scratch/empty` ends in `MissingDataError: … lacks: blast/blast.phr, …, PAML_RST/, species_pthr8_time.nhx`.
- **Fix:** add `MissingDataError` and `LibraryFormatError` to the handlers.

##### CORE-101. One service's import failure takes down every command

- **Where:** `engine/src/panther_engine/cli.py:7-10` imports every service's CLI when the module loads, and so does `engine/tests/conftest.py`.
- **What's wrong:** this is why HMM-3 breaks more than hmmscore. One platform-specific import in one service takes down every command (`--version` and `csnp score` among them) and pytest's collection for every service. Natively on Windows, pytest reports 12 collection errors, then "Interrupted", and runs no test.
- **Checked:** reproduced.
- **Fix:** import each service's CLI module inside its branch of `main()`.

##### CORE-102. `run_tool` resolves `stdout` and the arguments against different folders

- **Where:** `engine/src/panther_engine/core/process.py:44`; `core/hmmer.py:40` and `:58`.
- **What's wrong:**
  - A relative `stdout` path is opened against the Python process's working folder.
  - A relative path in `args`, such as hmmscan's `--domtblout`, is resolved by the tool against `cwd`. With `cwd=` set, one call can scatter its output across two folders. This is the core-level cause of HMM-5.
  - The `stdout` file is created or truncated before the program starts, so a failed start leaves an empty report behind.
- **Checked:** traced.
- **Fix:** refuse or absolutize relative paths in `run_tool`, and open `stdout` only once the program has started.

#### Low: hmmscore and refmap

##### HMM-4. The survey exits 0 on a tarball cut at a member boundary, and `data manifest` pins one

- **Where:** `hmmscore/survey.py:210` (`survey`, reading `r|gz`); `hmmscore/data.py:179` (`manifest`).
- **What's wrong:** a stream read stops quietly at a missing header after offset 0, and the gzip CRC isn't checked. `hmmscore-data`'s "Unreadable tarball" scenario requires a non-zero exit for a tarball that ends early. This repeats ENG-5.
- **Checked:** reproduced on a 4-member tarball cut before its third header:
  - the survey printed "Members: 2" and exited 0;
  - `data manifest` wrote a pin with no books and no pressed files, and exited 0.

  `data fetch`, `sample build` and refmap's fetch are safe, because they compare a pinned sha256.
- **Fix:** require the end-of-archive blocks, or the README's member counts, and have `manifest` require `names.tab` and the four pressed files.

##### HMM-5. With a relative data folder, `check_data()` passes and every search fails

- **Where:** `hmmscore/scoring.py:125`, `:136` and `:153`; `core/data.py:17-31` returns the folder as given.
- **What's wrong:** `hmmscan` and `hmmsearch` run with `cwd=` the temporary work folder, but the database and model paths stay relative to the caller's directory.
- **Checked:** reproduced in the image. From `/`, `--data-dir data` and `PANTHER_DATA_DIR=data` both fail with `HMM file data/hmmscore/19/globals/binHmm not found`, while `check_data()` passes. Through the API, every hmmscore job would fail with a `500`.
- **Fix:** make `data_root` return `Path(folder).absolute()`, which fixes every service at once.

##### HMM-6. CLI mistakes still end in a traceback

This repeats ENG-8.

- **Where:** `hmmscore/cli.py:525`, where the `survey --json` file is written outside the `try`; `read_families`, whose `UnicodeDecodeError` isn't caught.
- **Checked:** reproduced:
  - `hmmscore survey whole.tgz --json /nonexistent/survey.json` gives a `FileNotFoundError` traceback *after* the whole survey, which is 240 s on the real tarball, and the survey is lost;
  - `sample build --families` with a Latin-1 file gives a traceback.
- **Fix:** write the JSON inside the `try`, and catch `ValueError` in `run_sample`.

##### HMM-7. `score()` documents fewer exceptions than it raises

- **Where:** the `score` docstring, `hmmscore/scoring.py:103-121`.
- **What's wrong:** it leaves out two exceptions:
  - `DataFolderError`, when no folder is given and `PANTHER_DATA_DIR` is unset;
  - bare `OSError`, from the temporary folder and from reading the table, the report and `names.tab`.
- **Why it matters:** the coming API wiring will map errors from this list. Today every non-`InputError` is a `500`, so the effect is small.
- **Checked:** traced.
- **Fix:** document both, or wrap the reads in `HmmscoreError`.

##### HMM-8. Every hit re-reads and re-parses all of `names.tab`, and one bad line fails every search

- **Where:** `hmmscore/scoring.py:321-325` (`name_of`).
- **What's wrong:** PANTHER 19's `names.tab` has 143,695 lines and 7.6 MB.
- **Checked:** measured. A synthetic 8 MB file took 0.86 s per call natively, about 7% of APOE's 13 s on the full library. The pinned file parses cleanly, so nothing fails today.
- **Fix:** cache the parsed names per process, keyed by path and mtime.

##### HMM-9. `hmmscore score` scores sequences the API refuses

This repeats ENG-4.

- **Where:** `core/fasta.py:26` upper-cases before any character check. The API checks first.
- **Checked:** reproduced:
  - `MKVﬀL` becomes `MKVFFL`;
  - `MKVıL` becomes `MKVIL`;
  - `mkvß` becomes `MKVSS`.

  Each is a `422` from the API.
- **Fix:** check the API's characters (ASCII letters and `._~*`) before `upper()`.

##### HMM-10. No memory cap, and a killed worker leaves `hmmscan` running

- **Where:** `core/process.py`, as hmmscore uses it; `api/src/panther_api/jobs/runner.py:253` (`_run`).
- **What's wrong:**
  - `titin-10000` peaks at about 6 GiB through the port. On the server it fit only with swap's help, one job at a time (#68). Nothing bounds memory.
  - If the OOM killer picks the Python worker rather than `hmmscan`, the pool breaks and its other jobs fail (API-3). The orphaned `hmmscan` runs on, and its temporary folder stays.
- **Checked:** suspected; traced.
- **Fix:**
  - set `RLIMIT_AS` for the HMMER runners, or a cgroup memory limit at deploy;
  - start the tools in their own process group, and kill the group.

##### REFMAP-1. `refmap data fetch` isn't atomic, though its docstring says nothing is written if it fails

This repeats ENG-6.

- **Where:** the claim is at `refmap/data.py:12-15`; the code at `refmap/data.py:336-356`.
- **What's wrong:** the same pattern as HMM-2, at refmap's size:
  - files move one `os.replace` at a time;
  - a killed fetch leaves `.refmap-fetch-*` behind, holding the tarball and its unpacked copy.
- **Checked:** traced.
- **Fix:** the same as HMM-2.

##### REFMAP-2. The classification JSON can go stale with nothing noticing

- **Where:** `refmap/data.py:364-409` (`build-json`); `refmap/mapping.py:187-202` (`check_classification_json`).
- **What's wrong:**
  - `build-json` builds from whatever file is there, without checking it against `data.json`.
  - The JSON records no digest of its source, and the check only looks for the files.
  - `--missing-only` keeps old files, and, by the spec, `fetch` never rebuilds them.
- **What could go wrong:** after a re-fetch or a file replaced by hand, `GET …/classification` and refmap jobs can disagree, with nothing logged.
- **Checked:** traced.
- **Fix:** write the source's sha256 beside or into each JSON, and compare it with `data.json` in the check.

#### Low: API

##### API-102. A refused CORS preflight is a `400 text/plain`, not problem details

- **Where:** `api/src/panther_api/cors.py:43`, which uses Starlette's `CORSMiddleware`; `api/tests/test_cors.py` checks only the status.
- **What's wrong:** an `OPTIONS` request gets a plain-text `400` in each of these cases:
  - from an unlisted origin: `Disallowed CORS origin`;
  - from a listed origin asking for `DELETE`: `Disallowed CORS method`;
  - with an extra request header: `Disallowed CORS headers`.

  `api-service` says every 4xx has an RFC 9457 body.
- **Checked:** reproduced.
- **Fix:** rewrite the preflight rejection as a problem response, or exempt preflights in the spec.

##### API-103. An unexpected `500` carries no CORS headers

- **Where:** `api/src/panther_api/problems.py:111` registers the `Exception` handler, which Starlette runs in `ServerErrorMiddleware`, outside the middleware `main.py:123-124` adds.
- **What's wrong:** a cross-origin frontend sees a CORS failure instead of the problem body. API-7 and `_job_json`'s `ValueError` both lead here.
- **Checked:** reproduced. A route raising `RuntimeError`, called from a listed origin, gave a `500` with no `Access-Control-Allow-Origin`. A `404` and a `413` from the same origin carry it.
- **Fix:** turn unexpected exceptions into the problem `500` in a middleware inside `Cors`.

##### API-104. Every refused submission writes an access-log line, and a burst's refusal count is never logged

- **Where:** `api/src/panther_api/logs.py:79` keeps every non-2xx `POST`, as `api-service` requires; `jobs/runner.py:127-155` (`_Refusals`).
- **What's wrong:**
  - A client retrying in a loop fills the log with access lines anyway. The rate-limited refusal warning exists to prevent exactly that.
  - The warning reports a count only when another refusal arrives a minute later, so a burst followed by quiet is never counted.
- **Checked:** reproduced. 20 s of one client gave 4,754 `POST … 503` access lines and one refusal warning. The other 4,753 refusals were never counted.
- **Fix:**
  - leave `503`s out of the access log, and put the client address in the warning (an `api-service` change);
  - write the pending count when the interval ends and at shutdown.

##### API-105. Large valid refmap requests block the event loop for 0.3 to 0.5 s each

- **Where:** FastAPI decodes and validates the body on the loop before `create_job` (`routers/jobs.py:128`) runs.
- **What's wrong:** nothing bounds how many large bodies are decoded at once.
- **Checked:** reproduced:
  - four 10 MB, 100,000-ID requests took 0.5 to 0.8 s each;
  - the slowest health check went from 156 ms to 475 ms, and the container from 187 to 334 MiB;
  - polling the finished job returned 12.4 MB, uncompressed.
- **Fix:** a semaphore in `BodyLimit` for bodies over a few MB, or a per-client limit at the proxy; gzip large job responses (see also FE-103).

##### API-106. A corrupt classification file is served as a `200` with a truncated or corrupt body

- **Where:** `api/src/panther_api/routers/refmap.py:141-144` (`_gunzipped_chunks`) and `:204-208`.
- **What's wrong:**
  - Without gzip, decompression fails after the headers have gone, so the client gets a `200` and broken JSON.
  - With gzip, the corrupt file goes out as it is.
- **Checked:** reproduced. A half-truncated `ARAVE.json.gz` gave a `200` with 1,310,720 bytes, ending mid-record.
- **Fix:** check the gzip's integrity in `check_classification_json` or `refmap data verify` (see REFMAP-2), or read to the end before the first chunk goes.

##### API-107. One test always fails on native Windows

- **Where:** `api/tests/test_refmap_classification.py`, `test_a_file_replaced_after_opening_is_sent_as_it_was`.
- **What's wrong:** Windows refuses to rename over an open file (`WinError 5`), so the route answers `500`.
- **Checked:** reproduced: 1 failed, 21 passed. CI passes on Linux.
- **Fix:** `pytest.mark.skipif(os.name == "nt", ...)`, with the reason.

##### API-108. No deadline on a running job at the API level

- **Where:** `api/src/panther_api/jobs/runner.py:253` (`_run`).
- **What's wrong:** a worker whose engine call never returns holds its slot until the API restarts. ENG-3 is one way in; HMM-10 is another. With two such jobs, every later job queues and then gets a `503`, while `/health` stays `200`.
- **Checked:** suspected; traced.
- **Fix:** a backstop per service, a margin over its engine time limit (`asyncio.wait_for`), that fails the job and replaces the pool.

#### Low: Frontend

##### FE-103. The `web` image serves everything uncompressed

- **Where:** `frontend/nginx/default.conf.template`. There's no `gzip`, and the base image's `nginx.conf` has it commented out.
- **What could go wrong:** a first load is about 886 kB instead of about 240 kB. The JS bundle is 624 kB, 200 kB gzipped; the CSS 262 kB, 39 kB gzipped. A 100,000-ID refmap result, 5 to 11 MB of JSON, also goes through uncompressed.
- **Checked:** reproduced: the config read, and the sizes measured.
- **Fix:** `gzip on; gzip_proxied any; gzip_types application/javascript text/css application/json application/problem+json;`.

##### FE-104. No security headers

- **Where:** `frontend/nginx/default.conf.template:41-52`.
- **What's wrong:** there's no `X-Content-Type-Options`, `frame-ancestors` or `X-Frame-Options`, `Referrer-Policy` or CSP, so the site can be framed and its submit buttons clickjacked.
- **Checked:** traced.
- **Fix:**
  - add the headers with `always`;
  - repeat them in each `location`, because a `location` with its own `add_header` drops the server-level ones;
  - give a CSP `style-src 'unsafe-inline'` for Mantine.

##### FE-105. Back after "Edit and resubmit" refills the earlier job's input, not the one just submitted

- **Where:** `frontend/src/features/jobs/useEditedInput.ts:34`.
- **What's wrong:** from job A, "Edit and resubmit", change `K2E` to `V3L` and submit job B, then press Back. The form remounts from `history.state.editJob = A`, so it shows `K2E` as "Filled in from your earlier job". The edit just submitted is gone.
- **Checked:** reproduced.
- **Fix:** before navigating to job B, replace the form's history entry with `editState(B)`.

##### FE-106. A UTF-16 text file is decoded as UTF-8, so every ID is refused, with garbled names

- **Where:** `frontend/src/features/refmap/idsFile.ts:17` (`file.text()`).
- **What's wrong:** Excel's "Unicode Text" export is UTF-16LE with a BOM. `P04217\r\nP01023` becomes five "IDs" full of U+FFFD and NUL characters.
- **Checked:** reproduced.
- **Fix:** sniff the BOM and decode with `TextDecoder('utf-16le')` or `'utf-16be'`.

##### FE-107. The TSV download writes formula-like IDs raw

- **Where:** `frontend/src/features/jobs/mappingsFile.ts:11-12`.
- **What's wrong:** an ID such as `=HYPERLINK("http://x.example/")` is printable ASCII with no whitespace, so the API accepts it, and it's written as it is.
- **What could go wrong:** job links can be shared, so someone can send a job crafted through the API. The victim downloads the TSV, opens it in Excel, and the formula runs.
- **Checked:** reproduced (`mappingsTsv`'s output).
- **Fix:** prefix `'` to cells starting with `=`, `+`, `-`, `@`, a tab or a CR.

##### FE-108. hmmscore's switch to slower polling compares the API's clock with the browser's

- **Where:** `frontend/src/features/jobs/useJob.ts:33`.
- **What's wrong:** the wait is the job's `createdAt` plus 30 s, minus `Date.now()`. On a device whose clock is 5 minutes slow, the page polls every second for 5.5 minutes: about 330 requests instead of about 60. The comment at line 27 acknowledges the clocks differ.
- **Checked:** traced.
- **Fix:** time the 30 s from when the page first saw the job.

##### FE-109. On GitHub Pages, kept inputs share an origin with every other site the organisation publishes

- **Where:** `frontend/src/features/jobs/keptInput.ts:23` (`panther-scoring:input:`).
- **What's wrong:** `<org>.github.io` is one origin for all of that organisation's project pages. Any of them, opened in the same browser, can read the kept sequences and ID lists, up to 1 MB each.
- **Checked:** traced.
- **Fix:** use a custom domain, or accept it and say so in `runbook-pages.md`.

#### Low: Images

##### IMG-1. Earlier image findings that still hold

- **REPO-4:** `Dockerfile:262` runs `fastapi run` without pinning one worker. The job store is in memory, so a second worker would answer polls for the other's jobs with `404`.
- **REPO-5:** `compose.yaml:49` publishes the API on every interface.
- **REPO-6:** the API image's runtime user owns the installed code, and uv is in the runtime image (`Dockerfile:98`, `:244-259`).
- **No health check:** neither the API image nor compose has a `HEALTHCHECK`, and `web`'s `depends_on: api` waits only for the container to start.
- **Checked:** traced.

### Nits

- **CORE-103** (`core/manifest.py:68-78`): a manifest path with a Windows drive passes the check. `relative_path("C:/Windows/x")` is accepted, and `Path("D:/data") / it` gives `C:\Windows\x`. It matters only natively on Windows, with a hostile manifest, which would be a reviewed commit. Reproduced.
- **CSNP-103** (`csnp/library.py:44`): `open_lines` uses `newline=""`, which splits at a lone CR as well as at LF, while Perl splits at LF only. It's safe today: the survey found no CR in the library.

- **HMM-11** (`core/hmmer.py:41`): `hmmscan`'s stdout goes to `/dev/null`, and HMMER prints its option errors there. So `hmmscore score --cpu -1` reports `hmmscan exited with status 1:`, with nothing after it. Reproduced.
- **REFMAP-3** (`refmap/data.py:290`): `write_together` leaves `data.json` and `organisms.json` at `mkstemp`'s 0600. `build-json` (`:403`) and hmmscore's `write_file` fix that; this writer doesn't. Harmless in the images.
- **API-109** (`routers/refmap.py:112-119`): `accepts_gzip` treats `gzip;Q=0` and `gzip;q=0.0000` as accepting gzip. Reproduced.
- **API-110** (`store.py:116`): `uuid.UUID()` accepts other spellings, so one job answers at several URLs: no hyphens, upper case, `urn:uuid:…` and `{…}`. Harmless. Reproduced.
- **API-111** (`settings.py:41`): `PANTHER_API_CORS_ORIGINS` accepts an upper-case host or a default port, such as `https://PantherDB.github.io` or `…:443`. Neither ever equals a browser's `Origin`, so CORS silently does nothing.
- **API-112** (`main.py:84`): the lifespan's docstring says running jobs "finish first" on shutdown, but their tasks are cancelled and their results dropped while the pool drains. Traced.
- **FE-110** (`refmap/ids.ts:52-55`): `shownId` cuts an ID at 24 characters, so a bad character past the cut, or why a 65-character ID fails, isn't visible.
- **FE-111** (`CsnpForm.tsx:92`, `RefmapForm.tsx:90`, `HmmscoreForm.tsx:78`): `key={message}` gives duplicate keys when a `422` has two identical messages.
- **FE-112** (`mappingsFile.ts`): revoking the blob URL on a 0 ms timer is known to cancel downloads in some browsers. Suspected.

## Earlier Findings at `0f39e33`

The earlier review's findings in the areas reviewed. "Holds" means still true at `0f39e33`.

### Engine Core and cSNP

| Earlier | Status | Note |
| --- | --- | --- |
| CSNP-1: one BLAST+ tie line fails the job | Fixed | `identity()` uses BLAST+'s order; a real 2.17.0 tie and pairs from real BLAST+ runs are tested |
| CSNP-2: any species but the best match's gets "No PANTHER family" | Holds | The species filter sees only what `-best_hit_*` left. It's the science owner's call, and no open change tracks it. See also `MAP-2` under "Gaps" |
| CSNP-3: a missing library gives answers, not an error | Fixed | `check_data()` raises `MissingDataError`; `full.json` and `csnp data verify` check the data. The CLI's traceback is CSNP-102 |
| CSNP-4: titin's BLAST+ headroom | Fixed | 60 s plus 21 ms a residue, scaled by `PANTHER_CSNP_BLAST_TIME_SCALE`: 2.85 times titin's time |
| CSNP-5: every exit status 1 blamed on the sequence | Fixed | Only with a `BLAST query error:` line; the last lines of stderr go to the log |
| CSNP-6: a data folder path with a space | Fixed | `blastp` runs in the database's folder; a space and a `"` are tested |
| CSNP-7: paths no test reaches | Partly holds | Still untested: `age()`'s cycle guard (`psep.py:219`), `search()`'s `OSError` branch, and a gene missing from the `.orig.tree` |
| CSNP-8: `FamilyTree.path` has no cycle guard | Holds | `psep.py:192-200` |
| CSNP-9: `scoring` reaches `legacy` through `hits` | Holds | `scoring.py:98` |
| CSNP-10: the `.rst` is held three times | Holds | `psep.py:148-149` and `read_rst`. `PTHR11695.rst` is 15 MB |
| CSNP-11: `score()`'s documented errors | Changed | Now names `MissingDataError`, `BlastError` and `LibraryFormatError`, but not `OSError` or `DataFolderError` |
| ENG-1: every `blastp` contacts NCBI | Fixed | `run_tool`'s fixed environment, and `BLAST_USAGE_REPORT=false` in the image |
| ENG-2: `run_tool` rewrites output | Changed | Documented, and `stdout=Path` is byte-exact. Captured text still turns CR into LF |
| ENG-3: a timeout kills only the tool | Holds | A grandchild wrote its marker 1.5 s after a 0.3 s timeout |
| ENG-4: the CLI normalises unlike the API | Holds, moved | Now in `core/fasta.py:20-26`, shared with hmmscore (HMM-9). `MKßVﬀı` becomes `MKSSVFFI`. No 50,000-residue limit in the CLI |
| ENG-5: a partial archive exits 0 | Holds | A tarball cut at its fourth header gives "Families: 1" and no error, and a bad gzip CRC passes. The new tests cut inside a member only |
| ENG-6: `sample fetch` isn't atomic | Holds | `sample.py:270-273` replaces files one by one, against what `cli.py:167`, `sample.py:14` and `engine.md` promise. Stale `.csnp-sample-*` folders stay |
| ENG-7: fetch trusts the manifest and server | Holds | `asset.bytes` unused, `asset.name` unchecked (`sample.py:252`), redirects followed before the https check (`download.py:36-39`), no size bound on `unpack` |
| ENG-8: CLI tracebacks | Holds | `survey --json` writes outside the `try` (`cli.py:611`); `--genes -1` and `--positions 3` reach a negative `rng.sample` (`parity.py:400`, `:470`); CSNP-102 adds one more |
| ENG-9: tests ignore the `.data/` fallback | Holds | `test_csnp_scoring.py:75`, `:320` and `:372` call `score()` without a data folder |
| ENG-10: `parity cases` takes every `.paml` | Holds | `parity.py:269`; `fetch` never removes files a newer manifest drops |
| ENG-11: untested core behaviour | Partly holds | Still untested: a wrong species sha256, a bad family name, a README without its copyright line, an unreadable manifest, the runner's kill, stdin and output size |
| ENG-12 to ENG-17, ENG-19, ENG-21, ENG-22 | Hold | Unchanged. ENG-16 now measured: 200 MB of tool output held in memory |
| ENG-18: a build can leave folders behind | Changed | Archives unpack into a temporary folder; only a newly created `out.parent` can stay (`sample.py:121`) |
| ENG-20: `data("…")` raises `KeyError` | Changed | refmap and hmmscore are keys now; another name still raises `KeyError` |
| Core, for the next three services | Partly done | Done: `core/archive`, `open_https`, `HashingReader`, `core/hmmer`, a single-protein `core/fasta`, `MissingDataError`, an `environment` parameter. Missing: stdin, a process-group kill and an output cap in the runner; per-job work folders; pinned tool versions in core; one picklable error base; a generic fetch and parity harness; multi-record FASTA |

### hmmscore and refmap Against the Engine's Earlier Findings

The earlier review predates these services, so this table says whether their own code repeats the generic findings.

| Earlier | hmmscore | refmap | Note |
| --- | --- | --- | --- |
| ENG-2: `run_tool` rewrites output | No | No | HMMER's table and report, and `map_panther.pl`'s output, go to files byte for byte |
| ENG-3: a timeout kills only the tool | Not applicable | Not applicable | HMMER uses threads, not child processes; HMM-10 covers a killed worker |
| ENG-4: the CLI normalises unlike the API | **Yes** (HMM-9) | No | refmap takes IDs exactly as given |
| ENG-5: a partial archive exits 0 | **Yes** (HMM-4) | Mitigated | refmap's cross-check against `stats` fails a short build; every fetch checks a pinned sha256 |
| ENG-6: fetch isn't atomic | **Yes** (HMM-2, and `sample fetch`) | **Yes** (REFMAP-1) | |
| ENG-7: fetch trusts the manifest and server | **Partly** | **Partly** | `sample fetch` doesn't check `asset.name` or use `asset.bytes`, and unpacks unlisted members (`sample.py:368`, `:377`). `data fetch` never uses member names as paths. No download has a size cap, and `open_https` checks only the final URL's scheme |
| ENG-8: CLI tracebacks | **Yes** (HMM-6) | No | |
| ENG-9: the `.data/` fallback | Fixed | Fixed | `conftest.data_folder()` |

### API

| Earlier | Status | Note |
| --- | --- | --- |
| API-1: the body is read before a size limit | Fixed | `BodyLimit`: a 20 MB body gets a `413` |
| API-2: nothing limits waiting jobs | Fixed | The waiting cap gave 4,754 `503`s under load |
| API-3: a job submitted just after a worker dies fails | Holds | `runner.py:264-265`: `BrokenProcessPool` from `pool.submit` fails the job without resubmitting it |
| API-4: a `422` echoes a field name in full | Holds | A 50,028-character unknown key is echoed in a 50,243-byte `422` |
| API-5: unpinned Swagger UI from a CDN | Holds | `swagger-ui-dist@5` from jsDelivr, no SRI |
| API-6: the docs' OAuth redirect is outside `/api/v1` | Holds | `GET /docs/oauth2-redirect` gives `200` |
| API-7: a large expiry passes the startup check | Holds | With `80000000000000`, the API starts; the next poll and `POST` get `500`s |
| API-8: the store's memory and work grow | Changed | The request is no longer kept, and refmap results are stored as bytes. The sweep remains: API-101 |
| API-9: operators can't see input errors or the queue | Mostly fixed | Each job's log line has its wait and run times, and a worker death is logged. Queue depth shows only in refusal lines |
| API-10: unknown fields are accepted | Holds | A `202` with an extra `"priority"` |
| API-11: the schema lacks some patterns | Holds | `CsnpInput.species` has no `pattern` or `maxLength`; substitutions have no `pattern` |
| API-12: `GET /jobs/{id}` documents a `422` | Holds | `NO_VALIDATION_PROBLEM` now exists, so it's a one-line fix |
| API-13: `Location` ignores `root_path` | Holds | With `root_path=/scoring`, `Location` is still `/api/v1/jobs/…` |
| API-14: the core modules have no `__all__` | Holds | The API now also imports `core.data.DataFolderError` |
| API-15: no test pins the `405` for `GET /jobs` | Holds | |
| REPO-3: CI skips the real-job tests | Changed | `api-image` now runs them with the tools and data. A csnp "data missing" test through the real `run_job` is still missing |

### Frontend

| Earlier | Status | Note |
| --- | --- | --- |
| FE-1: a rendering error shows the developer screen | Fixed | Every route has an `errorElement` |
| FE-2: contrast | Fixed | `cssVariablesResolver` maps the error and dimmed colours |
| FE-3: a quadratic trim | Fixed | 1M characters in 4 ms |
| FE-4: an unknown service or status polls forever | Holds | "Loading the job…" and a poll every second. `wire.ts:84-92` has no default case, and `WireJob` is a hand-listed union |
| FE-5: a changed job id shows the previous result | Holds; raised to Medium | See above |
| FE-6: leaving the form still moves to the job | Holds | `await navigate` in `useSubmitCsnp.ts:27`, `useSubmitRefmap.ts:28`, `useSubmitHmmscore.ts:32` and `StartToolsCheck.tsx:17` |
| FE-7: a species typed while the list is unavailable | Fixed | |
| FE-8: one failed poll ends live updates; no timeout | Holds | Likelier now that hmmscore jobs can run 720 s. Needs `scoring-ui` changed first |
| FE-9: errors and page changes aren't announced | Changed | API failures are announced (`role="alert"`). Field errors aren't announced or focused, and every page has the same `<title>` |
| FE-10: input lost on Back or reload | Changed | "Edit and resubmit" was added; a fresh form still empties (see FE-105) |
| FE-11: the pages link nowhere | Fixed | |
| FE-12: test gaps | Changed | `check:no-mocks` gates the builds. No StrictMode in `tests/utils/render.tsx`; the e2e "must not scroll" check (`csnp.spec.ts:125`) asserts nothing; nothing tests FE-4, FE-5 or FE-6 |
| FE-13: the raw limit counts UTF-16 units | Fixed | |
| FE-14: JavaScript's `\s` | Holds | `substitutions.ts:9`, now copied into `refmap/ids.ts:14` |
| FE-15: a stale manual QA step | Holds | `02-csnp-form.md:133` |
| FE-16: `await startMocking()` has no catch | Holds | `main.tsx:31` |
| FE-17: duplicate `Versions` type | Holds | `versionsApi.ts` re-declares it |

Two improvements the earlier review suggested still apply:

- **A 4xx without problem details means "not the API":** a front end's HTML `413` still says "Try again in a moment" (`errors.ts:28`).
- **Clear the submit alert:** hmmscore clears it, but cSNP and refmap keep an "unreachable" alert after an edit (`useSubmitCsnp.ts:22`, `useSubmitRefmap.ts:23`).

## Gaps

### hmmscore Wiring and Data

- **The wiring:** done after `0f39e33`, in #83.
- **`port-hmmscore` is merged but not archived,** so `openspec/specs/` has no hmmscore engine spec. #87 archives it, with `wire-hmmscore`.
- **Memory:** #68 is closed. The deploy runs one hmmscore job at a time, and the longest query fit only with swap's help. There's still no memory cap in the engine or the deploy (HMM-10).
- **Parity breadth:** 15 cases on the full library, all matching; refmap was checked on 23.1 million IDs. A sampled run of a few hundred UniProt proteins through the reference would cover where differences hide: the 5,279 one-subfamily families prone to ties, and the 839 `HMMSCORE-9` models.
- **arm64:** HMMER 3.4's NEON build changes some last digits (the survey, "hmmscan on arm64"). If the host isn't amd64, that's a divergence with no row.

### API Readiness and Drift

- **Readiness:** nothing a client or an orchestrator can see shows missing data. `/health` is liveness only, and `versions.data` lists each release whether it's installed or not, both by the spec. Without the data, every csnp or refmap job fails with a `500`.
- **Contract drift:** API-11 and API-12, and two responses only `default` documents:
  - the `404` for `GET /jobs/{job_id}`;
  - the `400` for a body that can't be parsed.
- **Spec drift:**
  - `api-service`'s "Errors as problem details" (API-102), "Versioned base path" (API-6) and "Submitted values are not echoed" (API-4);
  - `scoring-jobs`' "invalid value MUST stop the API" (API-7), "release the memory" (API-101) and "jobs submitted afterwards run normally" (API-3).

### Frontend Mocks and Types

- **The mocks validate nothing,** so the `422` locations in unit tests are hand-written. At `0f39e33`, the mock also answered an hmmscore `POST` with a `202` where the API answered `501`; #83 removed the `501`.
- **Hand-written unions:** `WireJob` and `JobRequest` (`wire.ts`), and a third copy in `mocks/jobs.ts`, are hand-listed. If they were derived from the generated `paths` types, a new service would fail `tsc` (FE-4).

### cSNP Parity and Science

- **Full-library parity isn't proven.** `docs/parity/` has no dated `parity check` report, and "The Staging Run on the Full Library" in `golden-setup.md` is still to do.
- **Check the flip-flop before that run.**
  - Perl's `getCorrectnum` flip-flop stays on after a `last` inside the sequence list, so a record's second and later SNPs scan from the top of the file. The port resets it per record.
  - The two are the same only if no line before "List of extant…" contains `AN<n>`. None of the 16 sample `.rst` files has one.
  - The survey doesn't check this. Add it to the survey before the full run.
- **Which BLAST+ production ran needs team verification.** `MAP-1` ranks at 2 decimals, assuming the legacy BLAST+ wrote 2. From 2021 the legacy README installs Debian's `ncbi-blast+`. If that version already wrote 3, ranking at 2 is a divergence with no row.
- **`MAP-2` is reproduced faithfully, but nobody has logged it as a science question.**
  - The species filter is a substring match on the whole line. 37 of the 85 species codes are spelled only with amino-acid letters (`RAT`, `PIG`, `CHICK`, `DANRE`, …), so a line passes whenever its aligned sequences happen to spell the code.
  - `RAT` is also inside `ARATH`, so species `RAT` keeps every Arabidopsis hit.

  This belongs with CSNP-2, for the science owner.
- **Age 0 now shows where the old site showed nothing.** `snpScore.cgi` printed the age only when it was truthy, so it showed 0 and an empty age alike, as blank. The port returns `0` and `None`. It's harmless, but no divergence row or doc records it.
- **Legacy reference docs are missing.** CLAUDE.md's "read these first" for csnp names `.specs/2026-10-28-legacy-behavior-spec.md` and `docs/2026-10-28-parity-review.md` in `legacy/cSNP_analysis`. Neither is in any commit of the local checkout at `cebb5ab`, so a reviewer can't read the quirk catalogue the repo cites. Where they live needs team verification.

### Missing Tests

- **Engine:**
  - a stray character inside a long cSNP query (CSNP-101);
  - the paths still listed under CSNP-7 and ENG-11;
  - a sample fetch over a full library;
  - a relative data folder;
  - the survey on a tarball that ends early;
  - a broken `names.tab` through `score()`;
  - importing the CLI on Windows.

  Also, `conftest`'s `data("hmmscore")` checks against the *sample* manifest. A full-library folder passes it, then fails the sample's expectations, such as its E-values, which depend on the number of models.
- **API:**
  - an unknown key that mustn't be echoed (API-4);
  - the CORS rejection's body, and CORS headers on a `500`;
  - a huge expiry setting;
  - a submit onto a broken pool;
  - csnp with missing data through the real `run_job`;
  - a corrupt classification file;
  - the store's sweep at scale.
- **Frontend:**
  - an unknown service or status (FE-4);
  - the id changing on a mounted job page (FE-5);
  - navigating after leaving the form (FE-6);
  - StrictMode;
  - cSNP and refmap clearing their alert;
  - CSV, UTF-16 and space-separated files;
  - Back after a resubmit.

## Checked and Found Sound

- **hmmscore against `pantherScore.pl` and `scoreAlignXml.cgi`:**
  - **The table:** columns read like Perl's (target 0, full-sequence E-value 6, score 7), split on whitespace as Perl does.
  - **The best hit:** the highest score, then the smallest E-value, compared as numbers and kept as printed. The 1e-3 cutoff is inclusive and applies to the best hit only (`HMMSCORE-5`). The tied set is exactly Perl's, and `pick` implements row 13. The model id and path match `FamLibEntry_prod`.
  - **The alignment and query:** the alignment window matches the CGI, and the query is named and written as the CGI wrote it.
  - **Running HMMER:** argument lists, no shell, absolute programs. Each call gets its own work folder, removed afterwards. One time limit spans both tools. A non-zero exit or a missing table is an error, never "No hit".
  - **The data fetch:** member names are never used as paths; links, `..` and unknown members are refused. Every model is checked through `books.sha256` before anything moves, and `books.sha256` is itself hash-checked.
- **refmap against `map_panther.pl`:**
  - **Parsing:** Perl's `split` semantics (an implicit limit of 3, keeping a trailing empty field). The `\r` is kept, the last line wins, and the lookup is exact and case-sensitive.
  - **The result:** `NOHIT` gives `None`. Input order and repeats are kept.
  - **Safety:** the organism is checked against the list before any path is built, and fetched file names come from the list, with Windows device names refused.
- **The API:**
  - **Input:** every character check is ASCII-only, across full-width letters, zero-width characters, NBSP, NUL, the dotless i, the Kelvin sign, ligatures and lone surrogates. CRLF FASTA and a header after a blank line are handled.
  - **Errors:** nothing is echoed for odd `service` types, a non-object `input`, invalid JSON or form-encoded bodies. A `text/plain` cross-origin `POST` gets a `422`, so a CORS simple request can't start a job.
  - **refmap's list:** an over-long list is refused fast: 100,001 empty strings in 0.075 s.
  - **csnp through a real worker:** position 0, leading zeros, a 30-digit position, a position past the end and a repeated token all give per-row results, never a `500`.
  - **The engine contract:** the API's models mirror the engine's dataclasses, the engine's errors pickle across processes, and no engine path the API calls raises `SystemExit`.
  - **Jobs:** the waiting and running-cap arithmetic is right, only the event loop touches a job, and expired and evicted jobs both give a `404` problem.
  - **The log:** the access log URL-quotes paths, so a path can't inject a line.
- **The frontend:**
  - no `dangerouslySetInnerHTML`; API text is rendered as text;
  - polling stops on success, `404` and error, and unsubscribes on unmount;
  - `Retry-After` is read, and exposed through CORS;
  - each `422` location lands on its field;
  - kept input survives storage that throws or is full;
  - huge inputs are fast: 100,000 IDs split in 121 ms, a 1M-character sequence checked in 4 to 6 ms;
  - nginx runs as non-root, with the SPA fallback, immutable `/assets/` and the 17 MB body limit.
- **The images:** base images and downloads pinned by digest and sha256, the reference stages checking every legacy script's sha256, and `.gitattributes` keeping the fixtures and goldens byte for byte.

- **cSNP against the Perl at `cebb5ab`:**
  - **Step 1:**
    - the legacy options;
    - the query on stdin as `>P0001\n<seq>`, with no final LF;
    - no shell and no temporary file;
    - usage reports off.
  - **Step 2 against `parse_blastp.pl`:**
    - `sort -t, -k1,1 -k3nr,3` in C order, with ties broken on the whole line;
    - `grep` matching anywhere in the line;
    - the first line per query as the best hit;
    - Perl's `split` dropping trailing empty fields;
    - `getCorrectPosition`, including `MAP-4`.
  - **Step 3 against `PANTHER_PSEP1.01.pl`:**
    - the order of the checks;
    - the last header match (`SCORE-2`);
    - the walk's strict `> 0.99`;
    - `getYear`'s children taken from 1..`$i`, and the 4,200 cap;
    - 180/380 and `age < bound` (rows 4 and 7 deferred, code followed);
    - `.rst` lines 12 and 15 (`SCORE-9`);
    - the `.rst` tree nodes paired with the `.orig.tree` ANs, where the survey shows 0 differences.
  - **The script pins:** the legacy scripts' sha256s match the Dockerfile's pins.
- **Engine core:**
  - **`run_tool`:** an absolute program, an argument list, no shell, and the environment set in the documented order.
  - **`unpack`:** refuses links, absolute paths, `..` and anything outside the top folder, then applies tarfile's `data` filter.
  - **Downloads:** `write_tarball` is reproducible, and `open_https` refuses non-https URLs before any request.
  - **Errors across workers:** `InputError`, `LibraryFormatError`, `MissingDataError` and `BlastError` cross a worker process intact.

## After `0f39e33`

These merged afterwards and weren't reviewed: #82, which archives two changes, and #83, which wires hmmscore. Read against `main` at `82a2940`, they change these findings:

| Finding | At `82a2940` |
| --- | --- |
| hmmscore not wired (Summary, Gaps) | Fixed: jobs score with the engine, with the time limit and threads from the settings, the startup check and the versions entry. The `501` is gone |
| The hmmscore mock answering `202` against the API's `501` | Fixed with the `501` |
| HMM-10 | Partly fixed: on Linux, `run_tool`'s `die_with_parent` kills `hmmscan`, `hmmsearch` and `blastp` when their worker dies, and compose's `api` runs an init process to reap them. Memory is still uncapped |
| HMM-7 | Changed: the time limit now raises `TimeLimitError`, which the docstring names, and the API turns it into a `503`. `DataFolderError` and `OSError` are still undocumented |
| API-108 | Changed: hmmscore's time limit now reaches the engine. There's still no backstop in the API for a call that never returns |
| IMG-1 | Changed: compose's `api` has `init: true`. Still no health check |
| HMM-1 | Now live: the server holds the full library (#68) |
| HMM-3, HMM-5, CORE-102 | Hold: `hmmscore/cli.py` still imports `resource` at the top, and the paths are still relative |

Two pull requests were open when this was written: #86, the deploy's record, and #87, archiving `port-hmmscore` and `wire-hmmscore`.

## Follow-ups

None of these has an OpenSpec change yet. Each needs one, or a line in an existing change, before code is written.

- **The science owner:**
  - CSNP-101: refuse or report the characters BLAST+ ignores, and correct row 8;
  - CSNP-2 and `MAP-2`: the species filter.
- **Engine (the engine developer):**
  - HMM-1, HMM-2, REFMAP-1 and ENG-6: one change to the fetch tooling, covering the guards, stale staging and a single rename;
  - HMM-3 with CORE-101: a small fix, and urgent for anyone running the engine natively on Windows;
  - CSNP-102: a small fix;
  - the flip-flop check in the survey, before the full-library parity run;
  - HMM-5 with CORE-102: absolute paths in `core/data.py` and `run_tool`;
  - HMM-10: a memory cap for the HMMER runs.
- **API, left over from `wire-hmmscore`:**
  - the `score()` exceptions still undocumented (HMM-7);
  - a backstop deadline per job (API-108);
  - readiness.
- **API, in a separate hardening change:**
  - API-101's store;
  - API-102 to API-104 and API-106;
  - API-107 can go in any API change.
- **Frontend, in a hosting change or `deploy-frontend-to-pages`:**
  - FE-101, together with its runbook;
  - FE-103 and FE-104, in nginx.
- **Frontend, in a jobs-page change:**
  - FE-4, FE-5 and FE-6, with their tests;
  - FE-105 and FE-108.
- **Frontend, needing `scoring-ui` changed first:** FE-102 and FE-8.
- **Frontend, small changes:** FE-106, FE-107 and FE-109.
- **Nits:** no change needed. Fix them alongside nearby work.
