# Tasks

Test-first: each group writes its tests from the spec scenarios, runs them and sees them fail for the right reason, records the red run in the Notes, then implements.

## 1. The Wire Module

- [x] 1.1 Extend `tests/app/api/wire.test.ts`: `fromWireJob` converts a `csnp` job, keeping its `result` (family, scores, `null` age and pDel) unchanged; `isValidationProblem` accepts a `422` body and refuses others; `inputErrors` puts each error's `msg` on the field its `loc` names, prefixes a list item's with its place counted from 1, and keeps an error with any other `loc` under `other`. Run it and verify it fails because the `csnp` job doesn't type-check as a `WireJob` and the helpers don't exist, and the existing tests still pass. Record the red run in the Notes.
- [x] 1.2 Make `WireJob`, `JobRequest` and `Job` unions in `src/app/api/wire.ts`, with `fromWireJob` switching on `service`, and add `ValidationProblem`, `isValidationProblem` and `inputErrors`, as design.md describes. Add the `csnp` case to `JobResult` (rendering nothing yet) and `SERVICE_TITLES`, so `tsc` passes. Verify the tests from 1.1 and every other Vitest test pass, and `npm run type-check` and `npm run lint` pass, with no API type written by hand.

## 2. Mocked cSNP Jobs

- [x] 2.1 Add `csnpResult` (commented as mock data, family `PTHR00000`, a "Not scored: …" row with `null` age and pDel), `csnpJob(id, status)` and `csnpUnavailable` to `src/mocks/data/jobs.ts`, keeping it to type and relative imports; make `src/mocks/jobs.ts` remember each job's service, with `createJob()` still defaulting to `tools`; and let the mocked `POST` accept `csnp`. Verify `npm test`, `npm run type-check` and `npm run lint` pass, with no UI changed yet.

## 3. cSNP Results on the Job Page

- [x] 3.1 Extend `tests/features/jobs/JobPage.test.tsx` from the spec's "cSNP results on the job page": a succeeded `csnp` job shows its title, family, each score's four values in order, and the job's versions (A scored job); the not-scored row shows its substitution and message with empty age and pDel (A substitution that wasn't scored); a `null` family says there's no PANTHER family and still shows the scores (No family). Run it and verify the new tests fail because no family or score table is shown, and the `tools` tests still pass. Record the red run in the Notes.
- [x] 3.2 Implement `src/features/jobs/CsnpScores.tsx` and render it from `JobResult`, as design.md describes. Verify the tests from 3.1 and every other Vitest test pass with no warnings, and `npm run format:check`, `npm run lint` and `npm run type-check` pass.

## 4. The cSNP Form's Logic

- [x] 4.1 Write `tests/features/csnp/substitutions.test.ts` (the spec's "Spaces, tabs and new lines" and "Other separators are part of a token", plus empty and whitespace-only text), `tests/features/csnp/checks.test.ts` (each row of design.md's checks table, with an accepted value beside each rejected one, the spec's "A valid input is sent" values accepted, and no message containing the value checked) and `tests/features/csnp/draft.test.ts` (editing a field clears its errors and the form's, the example replaces every value and clears every error, `checked` and `rejected` set errors). Run them and verify they fail only because the modules don't exist. Record the red run in the Notes.
- [x] 4.2 Implement `src/features/csnp/substitutions.ts`, `checks.ts`, `draft.ts` and `example.ts`, as design.md describes. Verify the tests from 4.1 pass, and `npm run lint` and `npm run type-check` pass.

## 5. The cSNP Page and Submitting

- [x] 5.1 Write `tests/features/csnp/CsnpPage.test.tsx` and `tests/features/home/HomePage.test.tsx` from the spec scenarios: the home page links to `/csnp`, which shows the empty boxes and `HUMAN` (Open the form from the home page); the example fills all three (Use the example); an empty form shows three field errors and sends nothing (Empty form); two sequences, too long and a bad species each show their field's error and send nothing; a valid input sends the expected body and opens `/jobs/{id}` with the `csnp` title (A valid input is sent, The API accepts the request); the button is disabled in flight (While submitting); a `422` on `species`, on substitution 3, and on `organism` (The API rejects the species, The API rejects one substitution, An error on no field), and editing clears a field's error (Correcting a field); the `501` (The API answers 501) and a `500` (The API answers 500), each followed by a successful submit. Run them and verify they fail because `/csnp` shows the not-found page and the home page has no link, not because of an import, type or setup error. Record the red run in the Notes.
- [x] 5.2 Write `e2e/csnp.spec.ts`: the untagged empty-form test, and the `@mock` flow from `/` to a succeeded job with the mock family, rows and versions, with no sideways scroll. Run `npm run test:e2e` and verify both fail on desktop and mobile because there's no link or form. Record the red run in the Notes.
- [x] 5.3 Implement `src/features/csnp/` (`CsnpPage.tsx`, `CsnpForm.tsx`, `useSubmitCsnp.ts`, `index.ts`), export `useStartJobMutation` from `src/features/jobs/index.ts`, add `csnp` to `src/app/router.tsx`, and add the link to `HomePage`, as design.md describes. Verify the tests from 5.1 and every other Vitest test pass with no warnings, `npm run test:e2e` passes on both projects, and `npm run format:check`, `npm run lint`, `npm run type-check` and `npm run build` pass. Check that each guard is a real guard: with the client checks disabled, the "sends nothing" tests fail; with the button's `disabled` forced off, "While submitting" fails.

## 6. Against the Real API

- [x] 6.1 Add the `@api` tests to `e2e/csnp.spec.ts`: the example gets the real `501`, shown as not available yet, with the input kept and the URL unchanged; a request whose species is rewritten in flight gets the real `422`, shown on the species field; and a direct `POST` gets a `422` whose `loc` is `["body", "csnp", "input", "species"]`. From the repo root, `docker compose up --build -d api`, then `npm run test:e2e:api` in `frontend/` passes on both projects, including the existing tests; then `docker compose down`. Record the result in the Notes.

## 7. Docs and Final Check

- [x] 7.1 Add `docs/manual-qa/02-csnp-form.md`, following its README (`TC n.m`, a checkbox per visible step, Pass / Fail and Notes): in mock mode (`npm run dev`), open the form from the home page, use the example, try the client checks, submit, and read the results and versions; against the compose API (`npm run dev:api`), see the `501` with the input kept, and a server error on a field. Verify each step in a browser, or say in the Notes which were checked only by the e2e tests.
- [x] 7.2 Update `docs/testing/frontend.md` where running the tests changed (mocked `csnp` jobs; serving the `501` with `server.use`). Verify every command it names runs as written from `frontend/`.
- [x] 7.3 Final check:
  - in `frontend/`: `npm run api:types:check`, `npm run format:check`, `npm run lint`, `npm run type-check`, `npm test`, `npm run build` and `npm run test:e2e` pass;
  - the api-mode run from 6.1 passes against the final source;
  - from the root: `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass.

## 8. The Substitution Form Rule (PR #19, 2026-10-30)

- [x] 8.1 Flip the tests for the rule change: in `tests/features/csnp/checks.test.ts`, tokens that aren't `[A-Z][0-9]+[A-Z]` once upper-cased (`XYZ`, `G129`, `G12|`, `A10*`, `L46P,C130R`, …) are rejected and named by place and as typed, at most ten, while `G99999R` and lower case are accepted; in `draft.test.ts`, an API error on a substitution names the token from the `sent` list; in `CsnpPage.test.tsx`, malformed tokens show on the substitutions field and send nothing, the valid inputs use well-formed tokens, and a `422` on substitution 3 names `G12V`. Update the `scoring-ui` delta, proposal and design to match. Verify the new tests fail with the form check removed (a mutant) and with the sent token not looked up, and pass with them. Record it in the Notes.
- [x] 8.2 Rerun the final check from 7.3 against the final source, including the api-mode run, and walk the new manual QA steps in TC 2.2 in a browser.

## Workflow follow-up

- **Review:** the frontend developer approves the code, the `scoring-ui` delta, and the reducer in place of `useForm` (design.md, "The draft"). The API developer reviews how the `422`'s `loc` is read and the proposal's species-list question. The engine developer answers the proposal's questions on commas and the PANTHER 9 note, with add-csnp-job's.
- **Merge after PR #19** (`add-csnp-job`), on which this branch is based. Once this commit is on top of PR #19's updated branch (with the API's substitution rule), rerun `npm run api:types:check` and the api-mode e2e run, and consider an `@api` test that sends a malformed token past the client checks (as the species test does) and sees it named on the substitutions field. Not done here: the API at `9b34dbe` still keeps such tokens.
- **When the API's `501` is removed** (the port's API change), the same pull request, or a frontend one right after it, removes the `unavailable` outcome, its Vitest test, the `@api` `501` test and `csnpUnavailable`, and makes the `@api` test submit the example and wait for `succeeded`.
- **After the implementation merges,** archive with `/opsx:archive`, after `add-csnp-job`, which creates `scoring-input`.

## Notes

### Next action

Every task is done (2026-10-30). PR #19 merged, and the commit was put on top of `main` at `fa87c1e`, which has the API's substitution rule. There, every frontend check passes: `api:types:check`, format, lint, type-check, build, 140 Vitest tests, and 18 mock-mode e2e. The api-mode e2e passes (22) against `docker compose up --build api` built from that `main`. Next: the pull request and its review.

### Blockers

None for this change. PR #19 must merge first; its substitution rule (2026-10-30) isn't in `9b34dbe`, so the api-mode run here was against an API that still keeps malformed tokens. No api-mode test sends one.

### Failed approaches

- **Shell edits of tracked files (2026-10-29).** A heredoc that appended tests, and a `for` loop of `sed` edits, were refused by the worktree's command guard as too complex to verify. The same edits were made with the file tools, or with one plain `sed`.
- **`Table.ScrollContainer` for the score table (3.2, 2026-10-29).** Mantine's scroll container is a `ScrollArea`, which needs `ResizeObserver`; jsdom has none, so every `csnp` result test crashed the route ("ResizeObserver is not defined"). A Tailwind `overflow-x-auto` wrapper does the same job with no polyfill in `tests/setup.ts`.

### Lessons learned

- **The wire red run (1.1).** At run time, the 9 new `isValidationProblem` and `inputErrors` tests failed with "is not a function", and the `csnp` job test passed, since `fromWireJob` copied its fields through. `npm run type-check` was the real red for it: "Type '"csnp"' is not assignable to type '"tools"'" and "Property 'tools' is missing", in the test's `WireJob`. Green after 1.2: 42 tests in 7 files, and `tsc` clean.
- **`inputErrors` returns the item index, not text (1.1).** The first draft of the test expected "Substitution 3: …" from `wire.ts`. Naming a token's place is the cSNP form's wording, so `wire.ts` returns `{msg, item}` and the draft reducer words it.
- **The job page red run (3.1).** Four of the five new tests failed: no `PTHR00000`, no table named "Scores", no "No PANTHER family", no "PANTHER family" line. The fifth, "no score table while running", passed, as a guard should. The `tools` tests still passed.
- **`getByText` reads an element's own text (3.2).** With the family label in one `span` and the id in another, `getByText(/panther family/i)` found the label's `span`, which doesn't contain the id. The label is now the paragraph's own text, with the id in a child `span`.
- **The logic red run (4.1).** All three files failed only with "Failed to resolve import "@/features/csnp/…"". Green after 4.2: 60 tests in the three files, 107 in all.
- **Prettier rewrites the escape for U+0020 to a literal space** in a regex character class, and `no-control-regex` flags `\u0000` and `\u000b`. `\v` isn't flagged; the trim regex has a line-level disable with its reason.
- **The page red run (5.1).** In `CsnpPage.test.tsx` and `HomePage.test.tsx`, 20 of 21 tests failed because `/csnp` showed the not-found page: "Unable to find a label with the text of: /protein sequence/i" (and `/species/i`), or no "Score coding SNPs" link, "Use an example" or "Score substitutions" button. The one that passed, "keeps the scoring tools check", is the guard beside the new link test. The files type-checked and linted first.
- **The e2e red run (5.2).** In mock mode, both new tests failed on desktop and mobile after 30 s: the empty-form test waiting for the species label, the `@mock` flow waiting for the "Score coding SNPs" link.
- **Mantine's `Textarea autosize` crashes under jsdom (5.3, 2026-10-29).** It uses `react-textarea-autosize`, which listens on `document.fonts`: "Cannot read properties of undefined (reading 'addEventListener')", and the route rendered React Router's error page. Fixed rows with vertical resizing need no polyfill.
- **Green (5.3).** `npm test`: 128 tests in 12 files, no warnings. `npm run test:e2e`: 18 passed. `build` passes. The guards are real: with `checkDraft`'s result replaced by `{}`, the 7 "sends nothing" tests and "clears a field's error" failed; with the button's `loading` and `disabled` forced to `false`, "is disabled while the request is in flight" failed. Both mutants were reverted.
- **A test bug caught by the client checks (5.3).** "clears the API's error … and opens the job" first typed `2` after `HUMAN`; `HUMAN2` is six characters, so the client check stopped the resubmit. The test now types `RAT`.
- **Screenshots (5.3).** Of the production-like builds on desktop and Pixel 7: the home link, the three field errors, the mock results, and the `501` alert. With the table at a minimum width, the pDel column was off screen on the phone; without it, the columns wrap and all four fit.
- **api mode (6.1, 2026-10-29).** `docker compose up --build -d api` from this worktree; `/api/v1/health` answered `ok`. `npm run test:e2e:api`: 22 passed, including the three new `@api` tests on both projects. The real `422` reached the form through the `page.route` rewrite, and its `msg` ("Value error, The species must be a PANTHER species code …") was the species field's description.
- **The manual QA checklist (7.1).** TC 2.1, TC 2.2 and TC 2.4 were walked in Chromium driven by Playwright against a production build proxied to the compose API (the same `/api` proxy as `npm run dev:api`); every step showed what the checklist says. TC 2.3 is the `@mock` e2e test plus the screenshots. TC 2.5's `curl` command was run as written: `422`, errors at `substitutions` and `species`, no `human; id`.
- **The rule change (8.1, 2026-10-30).** The coordinator's message arrived after 7.3 had passed. The form check was written before its tests were flipped, so the red run is by mutants: with the token pattern replaced by `/^.*$/`, 11 tests failed (8 "rejects a token that is not a substitution", the naming and ten-token tests, and the page test); with the sent token looked up at the wrong index, the reducer's and the page's naming tests failed (2). Both reverted; then 140 tests pass.
- **Final check (8.2, 2026-10-30).** In `frontend/`: `api:types:check`, `format:check`, `lint`, `type-check`, `npm test` (140 tests in 12 files), `build`, `test:e2e` (18 passed) and `test:e2e:api` (22 passed, against the compose API at `9b34dbe`); then `docker compose down`. The new TC 2.2 steps were walked in a browser against the mock build: `XYZ` and `G12|` were named as substitutions 5 and 6, and `l46p` was accepted. From the root: `npx markdownlint-cli2` (72 files, 0 issues) and `npx openspec validate --all --no-interactive` (8 items) pass, and `add-csnp-form` is valid with `--strict`.
