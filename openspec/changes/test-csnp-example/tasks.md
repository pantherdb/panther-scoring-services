# Tasks

## 1. The API's Real-Job Test

- [x] 1.1 In `api/tests/test_csnp_scoring.py`, read the example from `engine/tests/golden/csnp/example/` by path: the sequence as `apoe.fasta`'s residue lines without its header, as the form's example has it, and the rows from `apoe.input` and `apoe.out`, as `expected_scores()` reads spec §7.3's. Add a test that submits it for `HUMAN` and checks that the job succeeds with family `PTHR18976` and `apoe.out`'s four rows, in order. Verify that `ruff check`, `ruff format --check`, `basedpyright` and `pytest` pass natively, where the real-job tests skip
- [x] 1.2 Run the API's tests with the API image's tools and data, as `docs/testing/api.md` says, with `PANTHER_REQUIRE_TOOLS=1` and `PANTHER_REQUIRE_DATA=1`. Verify that they all pass, the new one among them, and record the counts in the Notes

## 2. The Browser Test

- [x] 2.1 In `frontend/e2e/csnp.spec.ts`, add an `@api` test that opens the form, chooses **Use an example**, checks that the form holds `apoe.fasta`'s residue lines and `apoe.input`'s substitutions, submits it, and checks that the job succeeds with `PTHR18976` and the four rows of `apoe.out`, read by path. Verify that `format:check`, `lint`, `type-check` and `npm test` pass
- [x] 2.2 Run the e2e tests in mock mode, then in api mode against the API image on another port, with the data sample, through `API_PROXY_TARGET`. Verify that they all pass, the new test among them, and record the counts in the Notes
- [x] 2.3 In `frontend/tests/features/csnp/draft.test.ts`, check "the example" against `apoe.fasta` and `apoe.input`, read by path, in full, so CI's `frontend` job catches a changed residue anywhere in `example.ts` (review of #65). In the browser spec, check the score rows with one helper, `expectScoreRows`. Verify that `format:check`, `lint`, `type-check`, `npm test` and the e2e tests in mock mode pass

## 3. Docs and Final Check

- [x] 3.1 Update `docs/testing/api.md` ("Tests With the Tools and Data": what the tests submit, and the number of real jobs) and `docs/testing/frontend.md` (the api mode's needs, and the `@api` cSNP specs that create a job). Verify that `npx markdownlint-cli2` and `npx openspec validate --all` pass
- [x] 3.2 CI: the `api-image` job, on amd64 only, runs `tests/test_csnp_scoring.py` with the tools, Python and data of the API image it built, with the tools and data required, so a change that breaks the example fails CI (#38). Docs: `docs/testing/api.md` and `docs/testing/README.md`. Verify in the pull request's CI log that the seven tests run and pass, not skip

## Notes

### Next action

Every task is done. The pull request's review, then archive with `/opsx:archive`.

### Blockers

None.

### Progress

- **The data (2026-11-06):** `.data/` in the main checkout holds `csnp-sample-3`; `panther-engine csnp sample verify` in the API image says every file matches the manifest. The worktree's own `.data/` is empty, so every run below mounts the main checkout's, read-only.
- **The example agrees with the golden:** `frontend/src/features/csnp/example.ts` has `apoe.fasta`'s ten residue lines, without its header, 317 residues, and `apoe.input`'s four substitutions, `L46P`, `C130R`, `R163C` and `R176C`. The browser test checks this in the form.
- **Task 1.1:** natively, `ruff check`, `ruff format --check` and `basedpyright` (0 errors) pass, and `pytest` gives 339 passed, 7 skipped: the real-job tests, without `blastp`.
- **Task 1.2:** in the API image built from this branch, with `PANTHER_REQUIRE_TOOLS=1` and `PANTHER_REQUIRE_DATA=1`: 346 passed, none skipped (8 min 18 s, with the frontend's tests running beside it). `tests/test_csnp_scoring.py` alone: 7 passed in 3 min 47 s. The API's rows for the example are exactly `apoe.out`'s: family `PTHR18976`; L46P 91, probably benign, 0.19; C130R 6, probably benign, 0.02; R163C 220, possibly damaging, 0.50; R176C 220, possibly damaging, 0.50.
- **Task 2.1:** `format:check`, `lint` and `type-check` pass; `npm test` gives 372 passed in 30 files, under Node 24.22.0.
- **Task 2.2:** mock mode, 40 passed. Api mode, against the API image on port 8001 (`API_PROXY_TARGET=http://localhost:8001`), with the sample: 48 passed, the new test on both projects among them. The container was stopped afterwards.
- **Task 3.1:** `npx markdownlint-cli2` (179 files, no issues) and `npx openspec validate --all --no-interactive` pass.
- **Task 3.2:** the pull request's CI run: `api-image (amd64)` collected 7 tests in `tests/test_csnp_scoring.py`, and all 7 passed in 40.26 s, none skipped. The step took under a minute, `uv sync` included; task 1.2's 3 min 47 s was a local run.
- **Review (dustine32, #65):** `draft.test.ts`'s "the example" test now reads `apoe.fasta` and `apoe.input` by path and compares the whole sequence and the substitutions with `example.ts`, so CI's `frontend` job catches a changed residue anywhere; before, only the `@api` browser test, which CI doesn't run, compared them in full. The CI step has `timeout-minutes: 10`, runs after the `API logs` step, and the docs say it runs the checkout's code with the image's tools, not the packages the image ships. The browser spec's score-row check is one helper, `expectScoreRows`.
- **Task 2.3:** `format:check`, `lint` and `type-check` pass; `npm test` gives 373 passed in 30 files, and the new test fails when a residue in the middle of `example.ts` is changed. Mock mode, 40 passed. The `@api` specs that use the helper weren't run again in api mode: they type-check, and the helper checks the same cells as before.

### Failed approaches

None.

### Lessons learned

- **Tests that need the tools don't run in CI's `api` job:** it has no `blastp`, so they skip. `engine-image` already runs `engine/tests/test_csnp_scoring.py::test_the_forms_example_gives_the_references_scores` with `blastp` and the sample, on both architectures, so an engine change that broke the example already failed CI. What the `api-image` step (3.2) adds is the API between the form and the engine: its input handling, the job and the worker. Without it, an API change that broke the example's scores would have passed CI.
- **The example in the form is checked in CI by the frontend's unit test,** which compares `example.ts` with `apoe.fasta` and `apoe.input` in full. The API's and the engine's tests read the golden files, not `example.ts`, and the `@api` browser test runs only by hand.
