# Proposal

**Area:** cross-cutting. The data sample, its manifest, the parity goldens and their docs are all the engine's. But #26, merged while this change was under way, says in five places that the example isn't in the sample: in the API's and the frontend's test docs, the manual QA and a frontend e2e spec's comment. This change corrects them, so all three developers review it (design.md, decision 8). `docs/design/tech-stack.md` doesn't change (decision 7).

## Why

The scoring form's example is the legacy site's: human APOE, with `L46P`, `C130R`, `R163C` and `R176C` (`tips_exampleCsnpInput_content.jsp`). Its family, `PTHR18976`, isn't among the data sample's 15, so in development and CI the example's job succeeds with every substitution "Not scored: No PANTHER family for input sequence". tmushayahama asked on #26 whether the sample should gain it, and the engine developer said yes (2026-10-30).

`PTHR18976` is in the full PAML_RST library, and isn't one of its seven broken families. Against a copy of the sample with its three files added, the port scores the example L46P 91 / 0.19, C130R 6 / 0.02, R163C 220 / 0.50 and R176C 220 / 0.50. The Perl, in the reference image, gives exactly the same (tasks.md, Notes).

## What Changes

- **A new sample, `csnp-sample-3`:** the 15 families of `csnp-sample-2`, plus `PTHR18976` (1.9 MB unpacked), built from the pinned archives with `sample build` and published as a pre-release. `sample.json` pins it. `csnp-sample-2` stays published, for older commits.
- **Generated parity cases for `PTHR18976`,** from the same seed, through the Perl in the reference image. Each family's cases have their own seed, so the other families' cases and outputs don't change.
- **A Perl golden for the form's example itself,** since the generated cases may never reach APOE or its four positions:
  - the step-1 golden: BLAST+ 2.17.0's output for the example against the sample's database, beside the three release proteins';
  - the example's SNP lines, as `score()` gives them to step 2, and the Perl's step-2 and step-3 output for them, from the reference image;
  - tests that the port's steps 2 and 3 give that output, and that `score()` gives it end to end.
- **Docs:** the sample's tag and size in `docs/testing/engine.md`; the family in the survey's sample table; the example in `docs/parity/inputs.md`, `golden-setup.md` and the golden files' README.
- **`main`'s statements that the example isn't in the sample,** all from #26 (design.md, decision 8):
  - `docs/testing/api.md` and `docs/testing/frontend.md` say its family isn't among the sample's 15;
  - the manual QA's TC 2.4 counts 15 families, and expects the example's four rows to be "Not scored: No PANTHER family for input sequence";
  - a comment in `frontend/e2e/csnp.spec.ts` says so too.

  Each now says the sample holds 16 families and scores the example, and TC 2.4 expects its four scores. No test's code changes.
- **Also on this branch:** a new `engine/README.md`, an overview of the engine like `api/README.md` and `frontend/README.md`, which the root `README.md` now links to instead of `docs/testing/engine.md`. It's documentation only, and no part of this change; it rides along to avoid a `no-spec` pull request (engine developer, 2026-10-30).

Not in this change:

- **The API's and the frontend's tests.** Once this merges, their real-job and e2e tests can score the form's example and check it against the new golden, as they do P26439 against §7.3. That's their developers' call; only their docs' statements above change.
- **Any other family.** The sample stays one family per survey check, the spec's four, and now the form's example.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `csnp-data`: Data sample contents must include `PTHR18976`, the family of the form's example.
- `psep-engine`: Parity with the reference adds the reference's output for the form's example to the goldens.

## Impact

- **Data:** a new GitHub pre-release, `csnp-sample-3`. Publishing it needs write access, and the engine developer's go-ahead at that step. CI's cache is keyed on `sample.json`, so the next run of each job that uses the sample (`engine`, `engine-image` and `api-image`) fetches it once.
- **Code:** none in `src/`, apart from `csnp/sample.json`. The goldens and tests are under `engine/tests/`.
- **Other areas:** docs, the manual QA and one comment in a frontend e2e spec; no API or frontend code. The comment makes CI's `frontend` job run too.
- **Tests:** a data test of steps 2 and 3 on the example; tests marked `tools` and `data` for its step 1 and for `score()` end to end, which run in CI's `engine-image` job.
- **API contract:** not affected.
- **Dependencies:** none.
- **Parity with the reference:** not affected, and no divergence row is needed. The change adds goldens made by the reference; the port must match them exactly.
- **Size:** about 650 changed lines, over the 400-line norm: about 260 are this change's artifacts, 132 the two READMEs, 110 goldens made by BLAST+ and the Perl, 136 the manifest, the tests and the engine's docs, and 10 the corrections in the API's and the frontend's areas.

## Open Questions

Each needs team verification:

- **The example's scores** (answered by task 3.2): the Perl's output is exactly the port's.
- **What production gave for the example.** Production ran this library build, so the reference image's output should be what users saw, but nothing recorded from production can confirm it.
