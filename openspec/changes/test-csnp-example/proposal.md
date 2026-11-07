# Proposal

**Area:** cross-cutting: the API's tests and the frontend's tests, and their testing docs. No code in `api/src/` or `frontend/src/` changes, and nothing in `engine/`.

## Why

The scoring form's example, human APOE with `L46P`, `C130R`, `R163C` and `R176C`, is the first thing most users score. Since `add-apoe-to-csnp-sample` (#36), the data sample `csnp-sample-3` holds its family, `PTHR18976`, and the legacy Perl's output for it is a golden in `engine/tests/golden/csnp/example/`. The engine's tests check the port against it, but the API's and the frontend's tests still score only the release sample's proteins. #36's review agreed that both should score the example too (#38).

## What Changes

- **The API's real-job tests** (`api/tests/test_csnp_scoring.py`, marked `tools("blastp")` and `data("csnp")`): a new test submits the form's example, as the form sends it, and checks that the job succeeds with family `PTHR18976` and `apoe.out`'s four rows, in order. The sequence is `apoe.fasta`'s residue lines without its header, as the form's example has it, and the substitutions are `apoe.input`'s. The golden is read from the engine's test folder by path, not copied, as the existing tests read spec §7.3's.
- **The api-mode browser test** (`frontend/e2e/csnp.spec.ts`, tagged `@api`): a new test chooses **Use an example**, checks that the form then holds `apoe.fasta`'s residue lines and `apoe.input`'s substitutions, submits it, and checks that the job page shows `PTHR18976` and the four rows of `apoe.out`. It reads the golden by path, as the existing `@api` test reads `sample.fasta`.
- **Docs:** `docs/testing/api.md` and `docs/testing/frontend.md` say what the new tests check, and the number of real jobs.

Not in this change:

- **CI.** CI's `api` job skips the real-job tests, since it has no `blastp`, and CI runs the e2e tests in mock mode only, so neither new test runs in CI as it stands. CI's `api-image` job scores P26439 with `curl` and `jq`; scoring the example there too is an open question below.

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

- **Should CI score the example?** Neither new test runs in CI as it stands (Not in this change). CI's `api-image` job could score the example beside P26439, or run the API image's real-job tests. That touches `.github/`, which all three developers own, so it needs team verification.
