# Tasks

Test-first: each group writes its tests from the spec scenarios, runs them and sees them fail for the right reason, records the red run in the Notes, then implements.

## 1. The Splitter

- [x] 1.1 In `tests/features/csnp/substitutions.test.ts`, keep "Spaces, tabs and new lines", and replace the test that keeps commas in a token with the spec's "Commas" (`L46P,C130R`; `L46P, C130R,,R163C\n`), plus mixed separators, repeated commas, a leading and a trailing comma, commas with spaces and tabs, and text of only commas and spaces; and "Other separators are part of a token" (`L46P;C130R`, and `;`, `|` and `+` kept). Run it and verify the comma tests fail because the commas stay in the tokens, while the whitespace and other-separator tests pass. Record the red run in the Notes.
- [x] 1.2 Split at `/[\s,]+/` in `src/features/csnp/substitutions.ts`, and update its comment, as design.md describes. Verify the tests from 1.1 pass, and that `tests/features/csnp/checks.test.ts` still passes unchanged (its comma tokens test the check, not the splitter).

## 2. The Form

- [x] 2.1 In `tests/features/csnp/CsnpPage.test.tsx`, add a test that pastes `L4P,c13r` with a valid sequence and species, submits, and sees the request's `substitutions` as `["L4P", "c13r"]` and the job opened; keep the existing whitespace-separated submit test beside it. Add a test that the substitutions box's description mentions commas. Run them and verify the comma test fails because the form rejects `L4P,c13r` as one malformed token and sends nothing, and the description test fails on the old wording. Record the red run in the Notes.
- [x] 2.2 After 1.2, change the help text in `src/features/csnp/CsnpForm.tsx` to "separated by spaces, commas or new lines". Verify the tests from 2.1 and every other Vitest test pass, and `npm run format:check`, `npm run lint` and `npm run type-check` pass.

## 3. Docs and Final Check

- [x] 3.1 In `docs/manual-qa/02-csnp-form.md`, add a TC 2.2 step that pastes `L46P, C130R,R163C` and submits it as three substitutions. Check `docs/testing/frontend.md` for a separator to update (none expected). Walk the new step in a browser on the mock build, or say in the Notes that only the Vitest test checks it.
- [x] 3.2 Final check: in `frontend/`, `npm run api:types:check`, `format:check`, `lint`, `type-check`, `npm test`, `npm run build` and `npm run test:e2e` pass; from the root, `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass, and this change is valid with `--strict`, so the RENAMED and MODIFIED delta applies to `openspec/specs/scoring-ui/spec.md`.

## Workflow follow-up

- **Review:** the frontend developer approves the code and the `scoring-ui` delta. The engine developer answers the proposal's open question on a divergence row.
- **After the implementation merges,** archive with `/opsx:archive`. `add-mock-data-banner` adds other `scoring-ui` requirements; either can be archived first.

## Notes

### Next action

Every task is done (2026-10-29). Next: the pull request and its review, together with `add-mock-data-banner` in one commit.

### Blockers

None.

### Failed approaches

- **A QA step that read the split from the mock results (3.1, 2026-10-29).** The first draft said the job page's table would show three rows for `L46P, C130R,R163C`. The mocked `csnp` job always succeeds with the example's four rows, whatever was sent, so the step now checks only that the form accepts the input and opens a job, and says why.

### Lessons learned

- **The splitter red run (1.1).** 10 of 21 tests failed, every one with a comma: the commas stayed in the tokens (`["L46P,C130R"]` for `L46P,C130R`; `[","]` for `,`). The 11 others passed: whitespace, a single token, `;`, `|`, `+`, `.` and `/` kept, tokens as typed, and blank text. Green after 1.2. `checks.test.ts` passes unchanged.
- **The form red run (2.1).** 2 of 26 tests failed: the comma test stayed at `/csnp` instead of opening `/jobs/{id}`, since `L4P,c13r` was one malformed token; the description test failed on "separated by spaces or new lines". The new `L46P;C130R` row ("a semicolon, which does not separate substitutions") passed before and after, as a guard should. Green after 2.2: 185 tests in 14 files.
- **The rename applies (3.2).** Both changes were archived in a scratch copy of `openspec/`: this one reported "1 modified, 1 renamed", and the merged spec has "cSNP substitutions split on whitespace and commas" with its "Commas" scenario.
- **Walked in a browser (3.1, 2026-10-29).** Chromium driven by Playwright against the `build:e2e` build: the help text reads "separated by spaces, commas or new lines"; `L46P, C130R,R163C` was sent as `["L46P","C130R","R163C"]` and opened a job; `L46P;C130R` stayed at `/csnp` with "Substitution 1 (L46P;C130R): use the form L46P, a residue, its position, a residue."
- **Final check (3.2, 2026-10-29).** In `frontend/`: `api:types:check`, `format:check`, `lint`, `type-check`, `npm test` (185), `build`, `test:e2e` (20 passed) and `test:e2e:api` (24 passed, against an API on port 8001). From the root: `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass, and this change is valid with `--strict`.
