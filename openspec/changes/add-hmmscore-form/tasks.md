# Tasks

## 1. The Wire Module, Mocks and Shared Code

- [ ] 1.1 Add the `hmmscore` job and request to `frontend/src/app/api/wire.ts`, with no type written by hand, `HMMSCORE_FIELDS` to `src/app/formFields.ts`, and `hmmscore` to `KEPT_FIELDS` in `src/features/jobs/keptInput.ts`. Add `hmmscoreJob(id, status)` with a made-up hit and a 200-character-wide alignment, both marked as mock data, to `src/mocks/data/jobs.ts`, and let the mocked `POST` accept `hmmscore`.
- [ ] 1.2 Give `startJob` in `src/features/jobs/jobsApi.ts` a `transformErrorResponse` that adds `Retry-After`'s seconds. Move the submit-failure classification to `src/components/submitProblem.ts` and the alert to `src/components/SubmitAlert.tsx`, and use them in `useSubmitCsnp` and `useSubmitRefmap`, showing `unavailable` and `busy` as `failed` (design.md, decision 3). Delete the two feature `SubmitAlert.tsx` files.
- [ ] 1.3 Move `checkSequence` to `src/components/sequence.ts`, with each service's rules and the limits as exported constants, and the APOE sequence to `src/components/apoe.ts`; use both in the cSNP form (design.md, decisions 1 and 2).
- [ ] 1.4 Head every job in `JobDetails` with `service(job.service).title`, keeping a title for `tools` only, and check a job every second for 30 seconds, then every 5 seconds (design.md, decisions 4 and 5).
- [ ] 1.5 Tests: extend `tests/app/api/wire.test.ts` (`fromWireJob` keeps an `hmmscore` hit, and a `null` hit; `inputErrors` puts an hmmscore `422` on `sequence`, and anything else under `other`), `tests/mocks/jobs.test.ts` (a mocked `hmmscore` job succeeds with the mock hit) and `tests/features/jobs/keptInput.test.ts` (`isEditable('hmmscore')`). Move `checkSequence`'s cases from `tests/features/csnp/checks.test.ts` to `tests/components/sequence.test.ts`, and add hmmscore's: each rule, an accepted value beside each rejected one, 10,000 letters and one more, 10,000 letters and a final `*`. Add `tests/components/submitProblem.test.ts` (a `501` and a `503` with and without problem details, `Retry-After` present, missing or not a number) and the polling interval's case. Verify `npm test -- --run` passes.

## 2. The HMM Scoring Form

- [ ] 2.1 Implement `src/features/hmmscore/` (`HmmscorePage.tsx` with the notice while `comingSoon`, `HmmscoreForm.tsx`, `useSubmitHmmscore.ts`, `checks.ts`, `index.ts`), add `/hmmscore` to `src/app/router.tsx` with `errorElement: <ErrorPage />` in place of its coming-soon page, and give HMM scoring an `action` in `src/app/services.ts`, keeping `comingSoon: true`. Verify `npm run type-check` and `lint` pass.
- [ ] 2.2 Write `tests/features/hmmscore/HmmscorePage.test.tsx` from the spec scenarios: open from the home page and from the tab; the notice; the example; the client checks, sending nothing; a valid sequence and `"mkvbjouxz*\n"` sent as typed; disabled in flight; a `422` on `sequence` naming the server's limit, and on no field, and editing clearing it; the `501` with and without problem details, the busy `503`, a `500`, a network error, each followed by a successful submit; "Edit and resubmit" fills the box. Update `tests/features/home/HomePage.test.tsx` and the service tab tests for HMM scoring's form, and move `tests/components/ComingSoonPage.test.tsx`'s `/hmmscore` cases (12, 27) to `/treegrafter`. Verify `npm test -- --run` passes.

## 3. hmmscore Results on the Job Page

- [ ] 3.1 Implement `src/features/jobs/HmmscoreHit.tsx` and `AlignmentText.tsx`, render them from `JobResult`, and add the next step to `JobNextSteps` (design.md, decision 4).
- [ ] 3.2 Write `tests/features/jobs/HmmscoreHit.test.tsx`: the PANTHER ID and its link (encoded, `target`, `rel`, the accessible name), the name, the E-value and score as given, the alignment's spaces and line breaks kept, its box focusable and named, no hit, no hit or alignment while running, the versions, the heading from `services.ts`; and the next step's link to an empty form. Verify `npm test -- --run` passes.

## 4. End to End and Docs

- [ ] 4.1 Add `e2e/hmmscore.spec.ts`: untagged, the notice and the empty form's error; `@mock`, the example from the home page to the mocked hit and alignment, and at mobile width the alignment box scrolls sideways and the page doesn't; `@api`, the real `501` shown as not available yet with the sequence kept, and a `422` shown on the sequence field. Point `e2e/shell.spec.ts`'s coming-soon test (79) at `/treegrafter`, and add `/hmmscore` to `e2e/mock-data.spec.ts`'s no-banner check. Verify `npm run test:e2e` passes, and `test:e2e:api` against the API image on port 8001 (never 8000), then stop the container.
- [ ] 4.2 Add `docs/manual-qa/04-hmmscore-form.md`, following its README (`TC n.m`, a checkbox per visible step, Pass / Fail and Notes). Update `docs/testing/frontend.md`: mocked `hmmscore` jobs, `hmmscoreJob`, serving the `501` and a busy `503`, and the hmmscore e2e spec. Verify `npx markdownlint-cli2` passes.

## 5. Final Check

- [ ] 5.1 In `frontend/`: `npm run api:types:check`, `format:check`, `lint`, `type-check`, `npm test -- --run` and `npm run test:e2e`. From the root: `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive` and `npx openspec validate add-hmmscore-form --strict --no-interactive`. All pass; record the results in Notes.

## Workflow follow-up

- Open a pull request against `main`. The frontend developer approves the code, the `scoring-ui` delta and design.md's decisions; the engine developer reviews the `add-hmmscore-job` amendment.
- After this merges, archive with `/opsx:archive`. The wiring change turns HMM scoring's "coming soon" off, which removes the notice, and REMOVES "HMM scoring not yet available" and "HMM scoring form says it isn't available yet". "hmmscore submit failures" stays.
- Later ideas, not planned: an endpoint for the server's residue limit; a busy message on the cSNP and refmap forms; saying on the job page why an hmmscore job is queued.

## Notes

### Next action

Split out of `add-hmmscore-job` on 2026-11-11, at the engine developer's request on #70, and in its own pull request, #71. Both reviews of #71 are addressed (Lessons learned). Next: the frontend developer approves the plan; code starts once the Blockers clear.

### Blockers

- **`add-hmmscore-job` applied and merged:** the form reads its regenerated `schema.d.ts`, `api:types:check` needs its components, and `test:e2e:api` needs its `501`.
- **The refused-sequences row approved:** the divergence `add-hmmscore-job` adds for the sequences the API refuses where the reference answered no hit, which this form's checks ship. The engine developer is asked to approve it.

### Failed approaches

None yet.

### Lessons learned

- **The legacy page's "score" was the E-value,** and its sentence about the cutoff is backwards (`HMMSCORE-3`, `HMMSCORE-4`). The new page shows the API's fields by their real names, and no threshold.
- **The product owner set hmmscore's residue limit at 10,000 on 2026-11-12** (`add-hmmscore-job`, #70), in place of the website's 50,000. The form checks 10,000, the most the setting allows. The server-limit scenario is 5,000, since 20,001 residues would fail the form's own check first.
- **#71's reviews, 2026-11-12 and 13:** a character set can't express "one `*`, last"; "Edit and resubmit" reads `KEPT_FIELDS`, not only `formFields.ts`; moving a function moves its tests and breaks those that pinned the old page; a temporary `501` requirement stays apart from the lasting failures, as `wire-refmap` learned; a status alone doesn't prove the API answered; new-tab links and scroll boxes follow the existing accessibility rules; a full queue needs its own message; a final `*` isn't a residue, in the API too.
- **Name a divergence by what it covers, not its row number,** until the row is on `main`: rows are numbered when a change is applied.
