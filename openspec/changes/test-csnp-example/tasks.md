# Tasks

## 1. The API's Real-Job Test

- [x] 1.1 In `api/tests/test_csnp_scoring.py`, read the example from `engine/tests/golden/csnp/example/` by path: the sequence as `apoe.fasta`'s residue lines without its header, as the form's example has it, and the rows from `apoe.input` and `apoe.out`, as `expected_scores()` reads spec §7.3's. Add a test that submits it for `HUMAN` and checks that the job succeeds with family `PTHR18976` and `apoe.out`'s four rows, in order. Verify that `ruff check`, `ruff format --check`, `basedpyright` and `pytest` pass natively, where the real-job tests skip
- [x] 1.2 Run the API's tests in the API image with the tools and data, as `docs/testing/api.md` says, with `PANTHER_REQUIRE_TOOLS=1` and `PANTHER_REQUIRE_DATA=1`. Verify that they all pass, the new one among them, and record the counts in the Notes

## 2. The Browser Test

- [ ] 2.1 In `frontend/e2e/csnp.spec.ts`, add an `@api` test that opens the form, chooses **Use an example**, checks that the form holds `apoe.fasta`'s residue lines and `apoe.input`'s substitutions, submits it, and checks that the job succeeds with `PTHR18976` and the four rows of `apoe.out`, read by path. Verify that `format:check`, `lint`, `type-check` and `npm test` pass
- [ ] 2.2 Run the e2e tests in mock mode, then in api mode against the API image on another port, with the data sample, through `API_PROXY_TARGET`. Verify that they all pass, the new test among them, and record the counts in the Notes

## 3. Docs and Final Check

- [ ] 3.1 Update `docs/testing/api.md` ("Tests With the Tools and Data": what the tests submit, and the number of real jobs) and `docs/testing/frontend.md` (the api mode's needs, and the `@api` cSNP specs that create a job). Verify that `npx markdownlint-cli2` and `npx openspec validate --all` pass

## Notes

### Next action

Task 2.1.

### Blockers

None.

### Progress

- **The data (2026-11-06):** `.data/` in the main checkout holds `csnp-sample-3`; `panther-engine csnp sample verify` in the API image says every file matches the manifest. The worktree's own `.data/` is empty, so every run below mounts the main checkout's, read-only.
- **Task 1.1:** natively, `ruff check`, `ruff format --check` and `basedpyright` (0 errors) pass, and `pytest` gives 339 passed, 7 skipped: the real-job tests, without `blastp`.
- **Task 1.2:** in the API image built from this branch, with `PANTHER_REQUIRE_TOOLS=1` and `PANTHER_REQUIRE_DATA=1`: 346 passed, none skipped (8 min 18 s, with the frontend's tests running beside it). `tests/test_csnp_scoring.py` alone: 7 passed in 3 min 47 s. The API's rows for the example are exactly `apoe.out`'s: family `PTHR18976`; L46P 91, probably benign, 0.19; C130R 6, probably benign, 0.02; R163C 220, possibly damaging, 0.50; R176C 220, possibly damaging, 0.50.

### Failed approaches

None.

### Lessons learned

None yet.
