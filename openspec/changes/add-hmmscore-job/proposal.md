# Proposal

**Area:** cross-cutting. The code is in `api/` and `frontend/`, with their docs and tests. Nothing in `engine/` changes, but design.md proposes the engine's `hmmscore` interface, so the engine developer approves it, and the frontend and API developers review the contract (CONTRIBUTING.md, Review Rules).

**Depends on:**

- **#67** (`add-hmmscore-survey-and-sample`, applied on `feat/add-hmmscore-survey-and-sample-apply`). This change links to its [library survey](../../../docs/parity/hmmscore-library-survey.md), which `main` doesn't have yet. #67 merges first.
- **`wire-refmap`**, archived first. This change modifies three requirements that `wire-refmap` also modifies (`scoring-jobs`' "Configuration from the environment", and `scoring-ui`'s "Services that aren't available yet" and "The home page shows every service"). Its text here starts from `wire-refmap`'s.

## Why

`hmmscore` is the third service to port. Issue #42 asks for its contract before the port, as cSNP (#19) and refmap (#30) had theirs. Agreeing it now lets the frontend build the form and results against the real request, result and `422`s, and lets the engine developer port `scoreAlignXml.cgi` against a fixed interface.

The survey also showed that a long query needs far more time and memory than a typical protein: 21 GiB and about 20 minutes at the website's 50,000 residues. Issue #68 asks for a residue limit, a job time limit, a cap on hmmscore jobs running at once and `hmmscan`'s thread count, before hmmscore is served. They are part of the contract, so they come here, as settings the server sets.

## What Changes

- **An `hmmscore` job request** joins the request union: `{"service": "hmmscore", "input": {"sequence": "MKVLWAALLV..."}}`. One protein per job, as `scoreAlignXml.cgi` scored one (design.md, decision 1).
- **The sequence follows cSNP's rules** in `scoring-input`: trimmed, one FASTA header line removed, whitespace removed, letters upper-cased; rejected when empty, when it holds more than one `>`, or when it has a character outside printable ASCII. The website's form for HMM scoring did the same, except that it didn't trim or upper-case (design.md, decision 3).
- **A residue limit for hmmscore,** below the website's 50,000: `PANTHER_API_HMMSCORE_MAX_RESIDUES`, 5,000 by default. A longer sequence is a `422` on `sequence`.
- **An `hmmscore` job** joins the job union. Its `result` is `{"hit": null}` when no model passes the cutoff, or `{"hit": {"panther_id", "name", "evalue", "score", "alignment"}}`. `panther_id`, `evalue` and `alignment` are what the CGI's XML carried. `name` replaces the website's own database lookup, and `score`, the best hit's bit score, is new: `pantherScore.pl` computed it, and the CGI dropped it (design.md, decision 2).
- **Not available yet:** a valid `hmmscore` request gets `501 Not Implemented` as problem details, "HMM scoring isn't available yet.", and no job is created. Validation comes first. The `501` is documented in the OpenAPI schema while `UNAVAILABLE` has a row. `run_job` has an `hmmscore` case that raises `NotImplementedError`. The wiring change removes all three.
- **Four new settings,** read at startup and checked like the API's others, so an invalid value stops the API:

  | Variable | Default | What it sets |
  | -------- | ------- | ------------ |
  | `PANTHER_API_HMMSCORE_MAX_RESIDUES` | 5,000 | The longest sequence hmmscore takes, 1 to 50,000 |
  | `PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS` | 300 | How long one hmmscore job may run |
  | `PANTHER_API_HMMSCORE_MAX_RUNNING` | 1 | hmmscore jobs running at once; more wait, `queued` |
  | `PANTHER_API_HMMSCORE_CPU` | 0 | `hmmscan`'s `--cpu` |

  The defaults are placeholders, reasoned from the survey's measurements (design.md, decision 5). The server sets its own, once they're measured there (#68). This change enforces the residue limit and the running cap. The time limit and `--cpu` reach the engine with the wiring.
- **The frontend:** an HMM scoring page at `/hmmscore`, with a sequence box, a "Use an example" action that fills in the help page's human APOE, client checks that mirror the rules, `422`s on the field, the `501` in fixed text, and the job page's hmmscore result: the PANTHER ID and name, the E-value, the bit score and the alignment. HMM scoring's tab and home page card open the form; both keep the "coming soon" mark until the wiring.
- **Contract files:** `api/openapi.json` and `frontend/src/app/api/schema.d.ts` regenerated together. The wire module's unions gain `hmmscore`.
- **Docs:** `docs/parity/hmmscore-legacy-behaviour.md`, the legacy service as the code runs it, with quirk IDs (`HMMSCORE-1`, …), listed in `docs/parity/README.md`; proposed divergence row 11 for the residue limit; `api/README.md`, `docs/testing/api.md` (the job, its `501` and the settings), `docs/testing/frontend.md`, and a manual QA checklist, `docs/manual-qa/04-hmmscore-form.md`.

No new dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-input`: new requirements for an hmmscore input's `sequence`: its normalising, and when it's rejected, the configured residue limit included.
- `scoring-jobs`: new requirements for the `hmmscore` job request, its shape, its `501` while scoring isn't available, and the cap on hmmscore jobs running at once. "Configuration from the environment" and "The size of a job's input" are MODIFIED for the new settings and hmmscore's size in the log.
- `scoring-ui`: new requirements for the hmmscore form, its checks, its `422`s, its `501` and other failures, opening its job, and its results. "Services that aren't available yet", "The home page shows every service" and "The next step from a job's page" are MODIFIED, so HMM scoring opens its form.

`api-service` doesn't change: the largest valid hmmscore request, about 1 MB, is far under the 16 MiB body limit, and its `422`s use the existing shape.

## Impact

- **API:** a new `api/src/panther_api/jobs/hmmscore.py` (the input, its validation, the result); `jobs/fields.py` (cSNP's sequence normalising, shared); `jobs/work.py` (the unions, the `UNAVAILABLE` row, a `run_job` case that refuses to run); `jobs/models.py` (`HmmscoreJob`); `jobs/runner.py` (the running cap); `routers/jobs.py` (the configured residue limit, as a `422`); `settings.py`; tests.
- **API contract:** new schema components `HmmscoreJobRequest`, `HmmscoreInput`, `HmmscoreJob`, `HmmscoreResult` and `HmmHit`, and the `501` on `POST /api/v1/jobs` again, naming `hmmscore`. Existing shapes don't change.
- **Frontend:** a new `src/features/hmmscore/`; `src/features/jobs/` (the hmmscore result and title, the next step); `src/app/services.ts`, `router.tsx`, `formFields.ts` and `api/wire.ts`; the sequence check shared with cSNP; `src/mocks/`; tests in `tests/` and `e2e/`.
- **Engine:** no code changes, and no import of `panther_engine.hmmscore` beyond what exists. The engine developer reviews the proposed interface (design.md, decision 4) before porting (`port-hmmscore`).
- **Parity with the reference:** this change scores nothing, so no output changes. Its contract carries every field the CGI's XML carried, unchanged. Two rules answer differently from the website: a sequence over the residue limit is a `422` where the site took up to 50,000, proposed divergence row 11, which may not ship without an approver; and trimming and upper-casing, which the HMM scoring form didn't do, change no score, since HMMER reads either case alike (needs team verification against the port's goldens).
- **Size:** over the 400-line norm, as `add-refmap-job` and `add-refmap-form` together were. The task groups make reviewable commits; it splits into the API contract and the form if a reviewer prefers.

## Open Questions

For the engine developer (needs team verification where the legacy code doesn't settle it):

- **Tied best hits (`HMMSCORE-1`).** `getBestHit` returns every model with the best score and E-value, as printed, and `pantherScore.pl` prints them in Perl's hash order. The CGI reports the first line, so which tied model the site showed could change from one run to the next. The survey found that in the 5,450 one-subfamily families, the family and subfamily models differ by rounding in the fifth decimal, so they can tie as printed. The contract returns one hit. Which one should the port report: a fixed rule (for example the family before its subfamily), or all ties? Either is a proposed divergence row for `port-hmmscore`.
- **`name`:** from `names.tab`, which #67 records is in sync with the PANTHER database the website read names from. Is `null` right for an ID `names.tab` lacks? The survey found a `names.tab` line for every model file, so it shouldn't arise.
- **`evalue` and `score` as strings,** as `hmmscan` printed them, since `getBestHit` compares them as printed and the site showed the E-value's text. Or numbers?
- **A sequence `hmmscan` can't read,** such as one with a digit. The CGI died and the site showed its error page. The contract accepts printable ASCII, as cSNP's does, and expects the engine to raise `InputError`, a `422` in the job, as cSNP's port did for `blastp` (divergence 8). Or should the API accept only letters, `*` and `-`?
- **The time limit's failure:** design.md, decision 5 proposes the engine raises `InputError` with a fixed message when a job runs past the limit, so the user is told to try a shorter sequence, instead of the generic `500`.
- **Upper-casing:** HMMER reads lower-case residues as upper-case, so the hit and the alignment should be the same either way. The port's goldens confirm it.

For the team:

- **The defaults** (design.md, decision 5) are placeholders. The server's values come from measuring there with the full library in place (#68).
- **The website's port to the JSON API** (`panther-site-java` moving off `score_cgi`): it reads `panther_id`, `evalue` and `alignment` where it read `<id>`, `<eval>` and `<align>`, and can drop its own name lookup.
- **The relatedness label.** The site showed an icon from the E-value: closely related below 1e-23, related below 1e-11, distantly related below 1e-3 (`PantherScore.getImageLink`). The contract returns the E-value only. Should the form's results show that label, and should the API compute it?
- **The residue limit before submitting.** The form checks the website's 50,000; a sequence over the server's own limit is told by the API's `422`. Showing the server's limit on the form needs an endpoint (design.md, decision 7).
