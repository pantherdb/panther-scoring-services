# Tasks

## 1. The Wire Module and Mocks

- [ ] 1.1 Add the `hmmscore` job and request to `frontend/src/app/api/wire.ts`, with no type written by hand, and `HMMSCORE_FIELDS` to `src/app/formFields.ts`. Add `hmmscoreJob(id, status)` with a made-up hit marked as mock data to `src/mocks/data/jobs.ts`, and let the mocked `POST` accept `hmmscore`.
- [ ] 1.2 Extend `tests/app/api/wire.test.ts` (`fromWireJob` keeps an `hmmscore` hit, and a `null` hit; `inputErrors` puts an hmmscore `422` on `sequence`, and anything else under `other`) and `tests/mocks/jobs.test.ts` (a mocked `hmmscore` job succeeds with the mock hit). Verify `npm test -- --run` passes.

## 2. The HMM Scoring Form

- [ ] 2.1 Move `checkSequence` from `src/features/csnp/checks.ts` to `src/components/sequence.ts`, with the limit and the characters accepted as arguments, and import it in the cSNP form; share the APOE example sequence (design.md, decisions 1 and 2). Verify cSNP's tests pass unchanged.
- [ ] 2.2 Implement `src/features/hmmscore/` (`HmmscorePage.tsx`, `HmmscoreForm.tsx`, `useSubmitHmmscore.ts`, `SubmitAlert.tsx`, `example.ts`, `index.ts`), add `/hmmscore` to `src/app/router.tsx` with `errorElement: <ErrorPage />` in place of its coming-soon page, and give HMM scoring an `action` in `src/app/services.ts`, keeping `comingSoon: true`. Verify `npm run type-check` and `lint` pass.
- [ ] 2.3 Write `tests/components/sequence.test.ts` (each rule, with an accepted value beside each rejected one, at the most residues allowed and one more) and `tests/features/hmmscore/HmmscorePage.test.tsx` from the spec scenarios: open from the home page and from the tab; the example; the client checks, sending nothing; a valid sequence sent as typed; disabled in flight; a `422` on `sequence` naming the server's limit, and on no field, and editing clearing it; the `501`, a `500`, a network error, each followed by a successful submit; "Edit and resubmit" fills the box. Update `tests/features/home/HomePage.test.tsx` and the service tab tests for HMM scoring's form. Verify `npm test -- --run` passes.

## 3. hmmscore Results on the Job Page

- [ ] 3.1 Implement `src/features/jobs/HmmscoreHit.tsx` and `AlignmentText.tsx`, render them from `JobResult`, title the job "HMM scoring" in `JobDetails`, and add its next step to `JobNextSteps` (design.md, decision 3).
- [ ] 3.2 Write `tests/features/jobs/HmmscoreHit.test.tsx`: the PANTHER ID and its link, the name, a `null` name, the E-value and score as given, the alignment's spaces and line breaks kept, no hit, no hit or alignment while running, the versions; and the next step's link to an empty form. Verify `npm test -- --run` passes.

## 4. End to End and Docs

- [ ] 4.1 Add `e2e/hmmscore.spec.ts`: untagged, the empty form's error; `@mock`, the example from the home page to the mocked hit and alignment, and at mobile width the alignment box scrolls sideways and the page doesn't; `@api`, the real `501` shown as not available yet with the sequence kept, and a `422` shown on the sequence field. Add `/hmmscore` to `e2e/mock-data.spec.ts`'s no-banner check. Verify `npm run test:e2e` passes, and `test:e2e:api` against the API image on port 8001 (never 8000), then stop the container.
- [ ] 4.2 Add `docs/manual-qa/04-hmmscore-form.md`, following its README (`TC n.m`, a checkbox per visible step, Pass / Fail and Notes). Update `docs/testing/frontend.md`: mocked `hmmscore` jobs, `hmmscoreJob`, serving the `501`, and the hmmscore e2e spec. Verify `npx markdownlint-cli2` passes.

## 5. Final Check

- [ ] 5.1 In `frontend/`: `npm run api:types:check`, `format:check`, `lint`, `type-check`, `npm test -- --run` and `npm run test:e2e`. From the root: `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive` and `npx openspec validate add-hmmscore-form --strict --no-interactive`. All pass; record the results in Notes.

## Workflow follow-up

- **Merge order:** `add-hmmscore-job` first. `wire-refmap` archives before this change does.
- Open a pull request against `main`. The frontend developer approves the code, the `scoring-ui` delta and design.md's decisions.
- After this merges, archive with `/opsx:archive`. The wiring change turns HMM scoring's "coming soon" off and removes the `501` path.

## Notes

### Next action

Split out of `add-hmmscore-job` on 2026-11-11, at the engine developer's request on #70, to bring that pull request under the 400-line norm. Whether this change goes in its own pull request is still to decide. Code starts after `add-hmmscore-job`'s contract is approved.

### Blockers

- `add-hmmscore-job` must merge first: the form reads its generated types.
- `wire-refmap` must archive first: both modify the same two `scoring-ui` requirements.

### Failed approaches

None yet.

### Lessons learned

- **The legacy page's "score" was the E-value,** and its sentence about the cutoff is backwards (`HMMSCORE-3`, `HMMSCORE-4`). The new page shows the API's fields by their real names, and no threshold.
