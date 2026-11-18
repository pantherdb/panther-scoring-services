# Proposal

**Area:** cross-cutting: `api/` and `frontend/`, with their docs, tests and CI. Nothing in `engine/` changes; the engine developer reviews how the API calls `panther_engine.hmmscore`, and the server's data step.

**Depends on:**

- **`port-hmmscore` (#81) merged:** the engine's `score()`, `check_data()`, `DATA_VERSION` and `HmmscoreError`, and divergence row 13. This change imports them.
- **`add-hmmscore-form`'s archive (#82) merged:** it moves the form's requirements into `openspec/specs/scoring-ui/spec.md`, which this change's `scoring-ui` delta modifies and removes from.

## Why

The engine scores a protein against PANTHER 19's HMM library since `port-hmmscore` (#81), with every golden case matching the Perl on the data sample and on the full library. But the API still answers every valid `hmmscore` request with `501`, and the form says HMM scoring isn't available yet. This change wires the two together, so HMM scoring works end to end, as `wire-refmap` did for ID mapping.

## What Changes

- **`hmmscore` jobs run.** A valid request gets `202` and a job that calls the engine's `score()` in a worker, as `csnp` jobs call theirs. The `501`, its row in `UNAVAILABLE`, `run_job`'s refusing case and their tests go, and the `501` leaves the schema. **BREAKING** for a client that relied on the `501`; none does but the form, which changes here.
- **The settings take effect.** Each job's time limit grows with its length, from a new `PANTHER_API_HMMSCORE_MIN_TIME_LIMIT_SECONDS` (120 by default) for the shortest sequence to `PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS` (720) at the residue limit: APOE's 317 residues get 139 s. It goes to `score()` as its `timeout`, and `PANTHER_API_HMMSCORE_CPU` (0) as its `cpu`. A short query that hangs then frees the one running slot in about two minutes, not twelve. The residue limit and the running cap already act (`add-hmmscore-job`).
- **How a job fails:**
  - past the time limit, the engine raises its input error, so the job fails with a `422` whose `detail` is "The search took longer than this service allows. Try a shorter sequence.";
  - a tool that fails (`HmmscoreError`), a broken `names.tab` (`LibraryFormatError`), missing data (`MissingDataError`) or an unset `PANTHER_DATA_DIR` (`DataFolderError`) fails it with the generic `500`;
  - the engine's `ValueError` can't happen for a request the API accepted, and is the generic `500` too.
- **The startup check covers hmmscore's data,** logging an error, without stopping, when the folder lacks a file every search needs, as for cSNP and refmap.
- **Versions:** `GET /api/v1/versions` lists hmmscore's data, PANTHER 19, beside cSNP's and refmap's, and an `hmmscore` job names only its own. HMMER's version is already in the report, as `hmmscan` and `hmmsearch`.
- **The data:** `<PANTHER_DATA_DIR>/hmmscore/19/`. Developers and CI use the data sample, `hmmscore-sample-1` (33 MB); the hosting server needs the full library (67 GB), fetched with `panther-engine hmmscore data fetch`.
- **The form:** HMM scoring is no longer "coming soon", so its tab, its home page card and its page lose the mark, and the page loses its notice. The `501` path goes from the form: a `501` from the API gets "couldn't be started", as any other error.
- **Docs:** `docs/testing/api.md` and `docs/testing/frontend.md` move from the `501` to real jobs on the data sample; `docs/manual-qa/04-hmmscore-form.md` scores the example against the real API; `docs/deployment/runbook-server.md` gains the library's fetch.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-jobs`: a valid `hmmscore` request starts a job that scores with the engine, within a time limit that grows with its length and the configured thread count ("hmmscore not available yet" is removed); the startup check covers the hmmscore data; an `hmmscore` job's versions name PANTHER 19.
- `api-service`: the versions report lists hmmscore's PANTHER 19 data.
- `scoring-ui`: HMM scoring is no longer coming soon; the notice and the `501` requirements are removed ("HMM scoring form says it isn't available yet", "HMM scoring not yet available"); "hmmscore submit failures" stays, without the `501`; the job page shows an `hmmscore` job's data version.

## Parity

This change doesn't affect parity. The API passes the normalised sequence to `score()` unchanged, and returns its hit field for field. The engine's goldens prove the scoring (#81): 15 cases on the data sample in CI, and the same 15 on the full library.

It needs no new divergence. It ships three rows, all approved in `docs/parity/divergences.md`:

- **Row 11:** at most 10,000 residues, the product owner's, 2026-11-12.
- **Row 12:** the sequences the API refuses with a `422`, the engine developer's, 2026-11-16.
- **Row 13:** tied best hits, the subfamily first, then the lowest ID, the engine developer's, approved on #81, 2026-11-17.

The time limit isn't a row: a job past it fails where the reference would have answered, but the 720 s default covers the residue limit. `titin-10000` took about 231 s on the full library at `--cpu 0` (#68), the longest query the API accepts.

## Impact

- **API:** `api/src/panther_api/jobs/` (`hmmscore.py`, `work.py`, `runner.py`), `routers/jobs.py`, `main.py`'s startup checks, `versions.py`, `settings.py`'s descriptions, `api/openapi.json`, `api/CLAUDE.md` and `api/README.md`, and tests, including real-data ones marked `tools("hmmscan", "hmmsearch")` and `data("hmmscore")`.
- **Frontend:** `src/app/services.ts`, `src/features/hmmscore/`, `src/components/` (the `unavailable` submit problem), `src/mocks/`, `src/app/api/schema.d.ts` (regenerated: no `501`), unit tests, and the e2e specs.
- **CI:** the `api-image` job fetches the hmmscore data sample from the cache the engine jobs fill, runs the API's hmmscore data tests, and scores the example through the running API.
- **compose:** `.data/` is already mounted; its comments name the hmmscore sample beside the cSNP and refmap data.
- **The hosting server** needs the full library under its `PANTHER_DATA_DIR`, 67 GB, and its own values for the four settings. Until the library is there, `hmmscore` jobs fail with the generic `500` and the API logs why at startup.
- **Unchanged:** `engine/`, the `csnp`, `refmap` and `tools` jobs, the hmmscore input rules, and the residue limit and running cap.

## Open Questions

- **The hosting server's memory for long queries.** At the 10,000-residue limit, `titin-10000` peaked at 6.0 GiB at `--cpu 0` on the full library (#68). Whether the server can run a titin-like query, with what swap and in what time, is for the deploy to measure there. The engine developer sets the server's values for the four settings (#68), and a lower residue limit, if needed, goes into row 11.
- **Whether the running cap's default of 1 stays.** It was set before any full-library timing, since each search reads all of `binHmm.h3f`. With the server's measurements, the team may raise it, or keep 1 and set the server's own value.
- **Out of scope, noted:** separate waiting limits and `Retry-After` times per job type (#80). Today a backlog of `hmmscore` jobs fills the shared waiting cap, and the `503` asks for 30 s, about a cSNP job. `add-hmmscore-job`'s Risks left both to the wiring; #80 now holds them.
