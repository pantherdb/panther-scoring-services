# Proposal

**Area:** cross-cutting: the API's tests and the frontend's tests, a step in CI's `api-image` job, and their testing docs. No code in `api/src/` or `frontend/src/` changes, and nothing in `engine/`.

## Why

The scoring form's example, human APOE with `L46P`, `C130R`, `R163C` and `R176C`, is the first thing most users score. Since `add-apoe-to-csnp-sample` (#36), the data sample `csnp-sample-3` holds its family, `PTHR18976`, and the legacy Perl's output for it is a golden in `engine/tests/golden/csnp/example/`. The engine's tests check the port against it, but the API's and the frontend's tests still score only the release sample's proteins. #36's review agreed that both should score the example too (#38).

## What Changes

- **The API's real-job tests** (`api/tests/test_csnp_scoring.py`, marked `tools("blastp")` and `data("csnp")`): a new test submits the form's example, as the form sends it, and checks that the job succeeds with family `PTHR18976` and `apoe.out`'s four rows, in order. The sequence is `apoe.fasta`'s residue lines without its header, as the form's example has it, and the substitutions are `apoe.input`'s. The golden is read from the engine's test folder by path, not copied, as the existing tests read spec §7.3's.
- **The api-mode browser test** (`frontend/e2e/csnp.spec.ts`, tagged `@api`): a new test chooses **Use an example**, checks that the form then holds `apoe.fasta`'s residue lines and `apoe.input`'s substitutions, submits it, and checks that the job page shows `PTHR18976` and the four rows of `apoe.out`. It reads the golden by path, as the existing `@api` test reads `sample.fasta`.
- **CI:** the `api-image` job runs the API's real-job tests in the image it builds, on amd64 only, with the tools and data required, so a change that breaks the example fails CI. Before, CI's `api` job skipped them without `blastp`, and only one protein was scored there, with `curl` and `jq`. It adds about four minutes to that job.
- **Docs:** `docs/testing/api.md`, `docs/testing/frontend.md` and `docs/testing/README.md` say what the new tests check, the number of real jobs, and where CI runs them.

Not in this change:

- **The browser test in CI.** CI runs the e2e tests in mock mode only, so the new `@api` test runs by hand, as the other `@api` specs do.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None: the change adds tests of existing behaviour, so it has no spec deltas (`skip_specs: true`).

## Impact

- **Code:** tests only, in `api/tests/` and `frontend/e2e/`.
- **API contract:** not affected.
- **Dependencies:** none.
- **Parity with the reference:** not affected, and no divergence row is needed. The tests compare the API's and the website's results with the reference's own output, `apoe.out`.
- **Running them:** the API test needs `blastp` and the data sample, so it runs in the API image (`docs/testing/api.md`, "Tests With the Tools and Data"). The browser test needs an API with both, in api or site mode. Each adds one real job, of a few seconds.

## Open Questions

None. CI runs the new API test (task 3.2); the browser test runs in api mode only, by hand, as the other `@api` specs do.
