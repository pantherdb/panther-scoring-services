# Proposal

**Area:** cross-cutting: `api/` and `frontend/`, with their docs, tests and CI, and three small tasks in `engine/` for the engine developer (tasks.md, group 0): a timeout error of the engine's own, bounding a tool whose worker dies, and an `__all__` for `hmmscore.parity`. The engine developer also reviews how the API calls `panther_engine.hmmscore`, and the server's data step.

**Depends on:**

- **`port-hmmscore` (#81), merged on 2026-11-17 (`c74a30b`):** the engine's `score()`, `check_data()`, `DATA_VERSION` and `HmmscoreError`, the goldens, and divergence row 13. Its archive puts `hmmscore-engine` in `openspec/specs/`, which this change's `hmmscore-engine` delta modifies.
- **`add-hmmscore-form`'s archive (#82), still open:** it moves the form's requirements into `openspec/specs/scoring-ui/spec.md`, which this change's `scoring-ui` delta modifies and removes from.

## Why

The engine scores a protein against PANTHER 19's HMM library since `port-hmmscore` (#81), with every golden case matching the Perl on the data sample and on the full library. But the API still answers every valid `hmmscore` request with `501`, and the form says HMM scoring isn't available yet. This change wires the two together, so HMM scoring works end to end, as `wire-refmap` did for ID mapping.

## What Changes

- **`hmmscore` jobs run.** A valid request gets `202` and a job that calls the engine's `score()` in a worker, as `csnp` jobs call theirs. The `501` goes, with the whole mechanism behind it: `UNAVAILABLE`, `Unavailable`, the router's `501` branch, the schema's `501` and `run_job`'s refusing case. **BREAKING** for a client that relied on the `501`; none does but the form, which changes here. `add-treegrafter-job` brings a `501` back if it needs one.
- **The settings take effect.** Each job's time limit grows with its length, from a new `PANTHER_API_HMMSCORE_MIN_TIME_LIMIT_SECONDS` (120 by default) for the shortest sequence to `PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS` (720) at 10,000 residues, the most the API ever takes: APOE's 317 residues get 139 s. The length is divided by that fixed 10,000, not by `PANTHER_API_HMMSCORE_MAX_RESIDUES`, so a server that lowers the residue limit doesn't lengthen anyone's time limit. The limit goes to `score()` as its `timeout`, and `PANTHER_API_HMMSCORE_CPU` (0) as its `cpu`, which `score()` passes to both `hmmscan` and `hmmsearch`. A short query that hangs then frees the one running slot in about two minutes, not twelve. The residue limit and the running cap already act (`add-hmmscore-job`).
- **How a job fails:**
  - past the time limit, the engine raises a timeout error of its own (group 0), no longer its input error: a short query reaches its limit only on a busy server, so the time limit isn't the input's fault. The job fails with status `503` and the API's `detail`, "The search took longer than this service allows. The server may be busy: try again later, or with a shorter sequence.";
  - a tool that fails (`HmmscoreError`), a broken `names.tab` (`LibraryFormatError`), missing data (`MissingDataError`) or an unset `PANTHER_DATA_DIR` (`DataFolderError`) fails it with the generic `500`;
  - the engine's `ValueError` can't happen for a request the API accepted, and is the generic `500` too.
- **A search tool doesn't outlive its worker.** When a worker dies, its `hmmscan`, `hmmsearch` or `blastp` is killed too, on Linux (group 0), so it can't run on, unlimited, beside the next job.
- **The startup check covers hmmscore's data,** logging an error, without stopping, when the folder lacks a file every search needs, as for cSNP and refmap.
- **Versions:** `GET /api/v1/versions` lists hmmscore's data, PANTHER 19, beside cSNP's and refmap's, and an `hmmscore` job names only its own. HMMER's version is already in the report, as `hmmscan` and `hmmsearch`.
- **The data:** `<PANTHER_DATA_DIR>/hmmscore/19/`. Developers and CI use the data sample, `hmmscore-sample-1` (33 MB); the hosting server needs the full library (67 GB), fetched with `panther-engine hmmscore data fetch`.
- **The form:** HMM scoring is no longer "coming soon", so its tab, its home page card and its page lose the mark, and the page loses its notice. The `501` path goes from the form: a `501` from the API gets "couldn't be started", as any other error. A job past its time limit shows its `detail` on the job page, as any failed job does.
- **Docs:** `docs/testing/api.md` and `docs/testing/frontend.md` move from the `501` to real jobs on the data sample; `docs/manual-qa/04-hmmscore-form.md` scores the example against the real API; `docs/deployment/runbook-server.md` gains the library's fetch; `docs/parity/divergences.md` gains row 14, approved.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-jobs`: a valid `hmmscore` request starts a job that scores with the engine, within a time limit that grows with its length, and with the configured thread count for both tools ("hmmscore not available yet" is removed); a job past its time limit fails with a `503`; the startup check covers the hmmscore data; an `hmmscore` job's versions name PANTHER 19; the submission log's scenario no longer names a `501`.
- `api-service`: the versions report lists hmmscore's PANTHER 19 data.
- `scoring-ui`: HMM scoring is no longer coming soon; the notice and the `501` requirements are removed ("HMM scoring form says it isn't available yet", "HMM scoring not yet available"); "hmmscore submit failures" stays, without the `501`; the job page shows an `hmmscore` job's data version, and the `detail` of one past its time limit.
- `hmmscore-engine`: past the time limit, the engine raises its own timeout error, not its input error.
- `engine-core`: an external tool doesn't outlive the process that started it.

## Parity

The scoring doesn't change. The API passes the normalised sequence to `score()` unchanged, and returns its hit field for field. The engine's goldens prove the scoring (#81): 15 cases on the data sample in CI, and the same 15 on the full library.

It ships three approved rows in `docs/parity/divergences.md`:

- **Row 11, the residue limit:** at most 10,000 residues, the product owner's, 2026-11-12.
- **Row 12, the sequences the API refuses:** with a `422`, the engine developer's, 2026-11-16.
- **Row 13, tied best hits:** the subfamily first, then the lowest ID, the engine developer's, approved on #81, 2026-11-17.

It needs one new row, which must be approved before the code ships:

- **Row 14, hmmscore's time limit by length, approved by the engine developer on 2026-11-18 (#83).** A job past its limit fails, where the reference would have answered, however long it took. The limit runs from 120 s for the shortest sequence to 720 s at 10,000 residues. On the survey's and #68's timings, at `--cpu 0` on Endeavour, it's about 10 times APOE's 13 s (139 s), 4 times Q14204's cold 93 s (399 s at 4,646 residues), and 3 times `titin-10000`'s 231 s (720 s). Those times are Endeavour's, not the server's.

## Impact

- **API:** `api/src/panther_api/jobs/` (`hmmscore.py`, `work.py`, `runner.py`, `models.py`), `routers/jobs.py`, `main.py`'s startup checks, `versions.py`, `settings.py`, `api/openapi.json`, `api/CLAUDE.md` and `api/README.md`, and tests, including real-data ones marked `tools("hmmscan", "hmmsearch")` and `data("hmmscore")`.
- **Engine (group 0, the engine developer's):** `hmmscore/scoring.py` and `hmmscore/__init__.py` (the timeout error), `core/process.py` (`run_tool`), `hmmscore/parity.py` (`__all__`), and their tests.
- **Frontend:** `src/app/services.ts`, `src/features/hmmscore/`, `src/components/` (the `unavailable` submit problem), `src/mocks/`, `src/app/api/schema.d.ts` (regenerated: no `501`), unit tests, and the e2e specs.
- **CI:** the `api-image` job fetches the hmmscore data sample from the cache the engine jobs fill, runs the API's hmmscore data tests, and scores the example through the running API.
- **compose:** `.data/` is already mounted; its comments name the hmmscore sample beside the cSNP and refmap data.
- **Docs:** `docs/parity/divergences.md` gains row 14, approved.
- **The hosting server** needs the full library under its `PANTHER_DATA_DIR`, 67 GB, and its own values for the hmmscore settings. Until the library is there, `hmmscore` jobs fail with the generic `500` and the API logs why at startup.
- **`csnp` jobs:** their `blastp` dies with its worker too (decision 9), with the same results.
- **Unchanged:** the `refmap` and `tools` jobs, the `csnp` jobs' results, the hmmscore input rules, the residue limit, the running cap, and the scoring.

## Open Questions

- **The hosting server's memory for long queries.** At the 10,000-residue limit, `titin-10000` peaked at 6.0 GiB at `--cpu 0` on the full library (#68). Whether the server can run a titin-like query, with what swap and in what time, is for the deploy to measure there. The engine developer sets the server's values for the hmmscore settings (#68), and a lower residue limit, if needed, goes into row 11.
- **Whether the running cap's default of 1 stays.** It was set before any full-library timing, since each search reads all of `binHmm.h3f`. With the server's measurements, the team may raise it, or keep 1 and set the server's own value.
- **Out of scope, noted:** separate waiting limits and `Retry-After` times per job type (#80). Today a backlog of `hmmscore` jobs fills the shared waiting cap, and the `503`'s `Retry-After` asks for 30 s, about a cSNP job. `add-hmmscore-job`'s Risks left both to the wiring; #80 now holds them.
