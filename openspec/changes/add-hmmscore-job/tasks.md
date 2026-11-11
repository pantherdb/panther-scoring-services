# Tasks

## 1. The Legacy Service, Recorded

- [ ] 1.1 Read `pantherScoring/` (`scoreAlignXml.cgi`, `pantherScore.pl`) and the website's callers (`SequenceSearchAction.java`, `SequenceSearchForm.java`, `HMMScoreXMLParser.java`, `HMMHitBean.java`, `PantherScore.java`, `hmmScoreResults.jsp`, `sequenceSearchForm.jsp`, `tips_exampleHmmScoreInput_content.jsp`, `extra.properties.example`), read-only. Write `docs/parity/hmmscore-legacy-behaviour.md`, following `docs/parity/README.md`: what the CGI ran and returned, what the site sent and showed, the quirks `HMMSCORE-1` to `HMMSCORE-9` with file, line and a parity call (design.md, decision 9), and the proposed golden inputs. Link to the survey for the library and `pantherScore.pl`'s readings rather than repeating them. List the doc in `docs/parity/README.md`. Verify `npx markdownlint-cli2` passes.
- [ ] 1.2 Add proposed row 11 to `docs/parity/divergences.md`, with no approver: a sequence longer than the configured residue limit, 5,000 by default, is a `422`, where the site scored up to 50,000; and the new rules (trimming, upper-casing, printable ASCII, 1,000,000 characters). Add a footer line for `HMMSCORE-` IDs. Verify `npx markdownlint-cli2` passes.

## 2. The hmmscore Input and Result Models

- [ ] 2.1 Move cSNP's sequence normalising from `api/src/panther_api/jobs/csnp.py` to `jobs/fields.py`, with each service's messages passed in, so `csnp.py` keeps its messages unchanged. Verify `uv run pytest tests/test_csnp_input.py` passes unchanged.
- [ ] 2.2 Add `api/src/panther_api/jobs/hmmscore.py`: `HmmscoreInput` with the rules in design.md, decision 3, and `log_summary()` giving the residues; `HmmHit` and `HmmscoreResult`, every field required, nullable where the proposed engine dataclass is (decision 4). It imports only pydantic and `fields.py`. Verify `uv run basedpyright` passes.
- [ ] 2.3 Write `api/tests/test_hmmscore_input.py` for every scenario of `scoring-input`'s hmmscore requirements on `HmmscoreInput`: FASTA and plain sequences normalised; lower case and spaces; a header alone; two `>`; non-ASCII and a control character; 50,000 residues accepted and 50,001 rejected; 1,000,001 characters rejected; no sequence; an extra field. Each rejection asserts its `loc`, and that no message contains a distinctive part of the sequence. Verify they pass.

## 3. The Settings

- [ ] 3.1 Add `hmmscore_max_residues` (5,000, 1 to 50,000), `hmmscore_time_limit_seconds` (300, at least 1), `hmmscore_max_running` (1, at least 1) and `hmmscore_cpu` (0, at least 0) to `api/src/panther_api/settings.py`, each with a description and a comment pointing at design.md, decision 5. Pass the residue limit to the router and the running cap to `JobRunner`; keep the other two on the app's state for the wiring.
- [ ] 3.2 Extend `api/tests/test_settings.py`: the four defaults; each set from its variable; 0 and 50,001 residues, a time limit of 0, a running cap of 0 and `--cpu` -1 each stop the app from starting. Verify they pass.
- [ ] 3.3 In `docs/testing/api.md`, list the four variables with the others, their defaults as placeholders the server sets (#68), and that the time limit and `--cpu` take effect with the wiring. Verify `npx markdownlint-cli2` passes.

## 4. The hmmscore Job in the API

- [ ] 4.1 Add `HmmscoreJobRequest` to `JobRequest` and `HmmscoreResult` to `JobResult` in `jobs/work.py`, with hmmscore's row in `UNAVAILABLE` ("HMM scoring isn't available yet.", until the engine scores it) and a comment on what the wiring adds with its removal, and `run_job`'s `hmmscore` case raising `NotImplementedError`; `HmmscoreJob` in `jobs/models.py`. In `routers/jobs.py`, check the configured residue limit after the model and before the `501`, raising a `RequestValidationError` at `["body", "hmmscore", "input", "sequence"]` (design.md, decision 7). Verify the existing tests still pass.
- [ ] 4.2 Add the running cap to `jobs/runner.py`: a semaphore per capped service, taken before the worker slot (design.md, decision 6). Verify the existing runner tests still pass.
- [ ] 4.3 Write the API tests in `api/tests/test_jobs.py`: two `>` (422 at its `loc`, the residues not in the body, no job); no sequence; an extra field; 5,000 residues get the `501` and 5,001 the `422` naming 5,000; with the limit set to 20,000, 20,000 get the `501`; a valid request gets the `501` problem with no `Location` and no job; a `tools` job succeeds after it; `run_job` with an `hmmscore` request raises `NotImplementedError`. On a `JobRunner` with a stand-in `run_job` from `tests/job_helpers.py`: the running cap's three scenarios. In `test_job_logs.py`, an hmmscore job's line gives its residues and not the sequence. Verify they pass.

## 5. The Contract Files

- [ ] 5.1 Regenerate `api/openapi.json` (`uv run python -m panther_api.openapi`, from `api/`). Update `api/tests/test_openapi.py`: both unions list `hmmscore` fourth with its mapping; `HmmscoreJobRequest` and `HmmscoreInput` (required, no extra properties, the `maxLength`); `HmmscoreResult` and `HmmHit` (required fields, `hit` and `name` nullable); the `501` documented, naming `hmmscore`. Verify `uv run pytest` passes, including `test_committed_schema_is_current`.
- [ ] 5.2 Regenerate the frontend's types: `npm run api:types`, from `frontend/`. Verify `npm run api:types:check` and `type-check` pass.
- [ ] 5.3 In `docs/testing/api.md`, add "The hmmscore Job" to "Try the Jobs by Hand": a valid request and its `501`, a sequence over the limit and its `422`, with `curl`, and the bodies the API returns. In `api/README.md`, add a line for `hmmscore` and its `501`. In `api/CLAUDE.md`, "Adding a Service", say `hmmscore` has its contract. Verify `npx markdownlint-cli2` passes.

## 6. The Wire Module and Mocks

- [ ] 6.1 Add the `hmmscore` job and request to `frontend/src/app/api/wire.ts`, with no type written by hand, and `HMMSCORE_FIELDS` to `src/app/formFields.ts`. Add `hmmscoreJob(id, status)` with a made-up hit marked as mock data to `src/mocks/data/jobs.ts`, and let the mocked `POST` accept `hmmscore`.
- [ ] 6.2 Extend `tests/app/api/wire.test.ts` (`fromWireJob` keeps an `hmmscore` hit, and a `null` hit; `inputErrors` puts an hmmscore `422` on `sequence`, and anything else under `other`) and `tests/mocks/jobs.test.ts` (a mocked `hmmscore` job succeeds with the mock hit). Verify `npm test -- --run` passes.

## 7. The HMM Scoring Form

- [ ] 7.1 Move `checkSequence` from `src/features/csnp/checks.ts` to `src/components/sequence.ts`, with the limit as an argument, and import it in the cSNP form; share the APOE example sequence (design.md, decision 10). Verify cSNP's tests pass unchanged.
- [ ] 7.2 Implement `src/features/hmmscore/` (`HmmscorePage.tsx`, `HmmscoreForm.tsx`, `useSubmitHmmscore.ts`, `SubmitAlert.tsx`, `example.ts`, `index.ts`), add `/hmmscore` to `src/app/router.tsx` with `errorElement: <ErrorPage />` in place of its coming-soon page, and give HMM scoring an `action` in `src/app/services.ts`, keeping `comingSoon: true`. Verify `npm run type-check` and `lint` pass.
- [ ] 7.3 Write `tests/components/sequence.test.ts` (each rule, with an accepted value beside each rejected one, at 50,000 and 50,001 residues) and `tests/features/hmmscore/HmmscorePage.test.tsx` from the spec scenarios: open from the home page and from the tab; the example; the client checks, sending nothing; a valid sequence sent as typed; disabled in flight; a `422` on `sequence` naming the server's limit, and on no field, and editing clearing it; the `501`, a `500`, a network error, each followed by a successful submit; "Edit and resubmit" fills the box. Update `tests/features/home/HomePage.test.tsx` and the service tab tests for HMM scoring's form. Verify `npm test -- --run` passes.

## 8. hmmscore Results on the Job Page

- [ ] 8.1 Implement `src/features/jobs/HmmscoreHit.tsx` and `AlignmentText.tsx`, render them from `JobResult`, title the job "HMM scoring" in `JobDetails`, and add its next step to `JobNextSteps` (design.md, decision 10).
- [ ] 8.2 Write `tests/features/jobs/HmmscoreHit.test.tsx`: the PANTHER ID and its link, the name, `null` name, the E-value and score as given, the alignment's spaces and line breaks kept, no hit, no hit or alignment while running, the versions; and the next step's link to an empty form. Verify `npm test -- --run` passes.

## 9. End to End and Frontend Docs

- [ ] 9.1 Add `e2e/hmmscore.spec.ts`: untagged, the empty form's error; `@mock`, the example from the home page to the mocked hit and alignment, and at mobile width the alignment box scrolls sideways and the page doesn't; `@api`, the real `501` shown as not available yet with the sequence kept, and a direct `POST` of 5,001 residues whose `422` names `sequence` without echoing it. Add `/hmmscore` to `e2e/mock-data.spec.ts`'s no-banner check. Verify `npm run test:e2e` passes, and `test:e2e:api` against this worktree's API image on port 8001 (never 8000), then stop the container.
- [ ] 9.2 Add `docs/manual-qa/04-hmmscore-form.md`, following its README (`TC n.m`, a checkbox per visible step, Pass / Fail and Notes). Update `docs/testing/frontend.md`: mocked `hmmscore` jobs, `hmmscoreJob`, serving the `501`, and the hmmscore e2e spec. Verify `npx markdownlint-cli2` passes.

## 10. Final Check

- [ ] 10.1 In `api/`: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest`. In `frontend/`: `npm run api:types:check`, `format:check`, `lint`, `type-check`, `npm test -- --run` and `npm run test:e2e`. From the root: `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive`, `npx openspec validate add-hmmscore-job --strict --no-interactive` and `docker build --target api .`. All pass; record the results in Notes.

## Workflow follow-up

- **Merge order:** #67 (`add-hmmscore-survey-and-sample`) merges first, since design.md links its survey doc. `wire-refmap` archives first, since this change's MODIFIED requirements start from its text.
- Open a pull request against `main` with these artifacts. Reviewers:
  - the API developer approves the API side and the settings;
  - the frontend developer reviews the contract and approves the form and results;
  - **the engine developer reviews the proposed interface** (design.md, decision 4) and the input rules against `docs/parity/hmmscore-legacy-behaviour.md`, answers the proposal's Open Questions, ties first, and approves or rejects divergence row 11. Their approval closes the contract part of #42.
- **The engine developer's port** (`port-hmmscore`, a change of its own) adds `panther_engine.hmmscore.score`, its dataclasses, `DATA_VERSION`, `check_data()`, a reference image and the goldens.
- **The wiring change removes the `501`:** it deletes hmmscore's `UNAVAILABLE` row, which takes the `501` and its schema entry with it; replaces `run_job`'s case with an adapter to `score()`, passing the time limit and `--cpu`; adds the data check at startup and the data version; REMOVES "hmmscore not available yet" from `scoring-jobs` and adds the time limit's behaviour; and turns HMM scoring's "coming soon" off.
- **The server's values** for the four settings are measured on the server with the full library in place, and set there (#68).
- After this merges, archive with `/opsx:archive`.

## Notes

### Next action

The artifacts are drafted for review (2026-11-10). Next: open the pull request once #67 merges, and get the engine developer's answers to the proposal's Open Questions, ties first. Code starts after the area owners approve.

### Blockers

- #67 must merge first: design.md and the proposal link to `docs/parity/hmmscore-library-survey.md`, which is only on `feat/add-hmmscore-survey-and-sample-apply` today.
- `wire-refmap` must archive before this change does: both modify the same three requirements.
- None for the work itself. The engine's `score()` blocks the wiring, not this change.

### Failed approaches

None yet.

### Lessons learned

- **The CGI's XML is thinner than the site's page.** `scoreAlignXml.cgi` returned only the HMM ID, the E-value and the alignment. The family name came from the website's own database, and the page's "score" was the E-value. The contract keeps those three, and marks `name` and `score` as new.
- **The HMM scoring form wasn't cSNP's form.** `SequenceSearchForm` didn't trim or upper-case, unlike `CsnpScoreForm`. The contract uses cSNP's rules, and records the difference.
- **`getBestHit` can return ties, and the CGI showed whichever came first in Perl's hash order.** That makes the legacy's reported hit unstable for exact ties, which the one-subfamily families make likely. It's an open question, not something the contract can settle.
- **A setting read at startup can't go in the committed schema,** so the configured residue limit is checked in the router, with the same `422` shape, and the schema only describes it.
