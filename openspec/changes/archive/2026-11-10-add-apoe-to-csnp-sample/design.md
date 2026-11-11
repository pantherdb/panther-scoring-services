# Design

## Context

See proposal.md, Why.

- **The sample** is a public release asset, pinned by `engine/src/panther_engine/csnp/sample.json` ([tech-stack.md](../../../docs/design/tech-stack.md#shared-concerns), Shared Concerns, Data). [engine.md](../../../docs/testing/engine.md#publishing-a-new-sample) has the steps for publishing a new one: choose the families, `sample build`, `gh release create --prerelease`, fetch into an empty folder, commit the manifest.
- **The parity goldens** come from the reference image, `csnp-reference` ([tech-stack.md](../../../docs/design/tech-stack.md#engine-engine-agree-with-conditions), Engine condition 3). [golden-setup.md](../../../docs/parity/golden-setup.md) has the commands. `parity cases` seeds each family's random generator with `"<seed>:<family>"`, and the step-2 runs with `"<seed>:step2"`.
- **`score()`** gives step 2 one SNP line per substitution, `SNP_<n>|P0001|<position>|<WT>;<MUT>`, after BLAST+ has searched the query as `P0001`.
- **`PTHR18976` in the archive:** `.paml` 1,709,004 bytes, `.rst` 168,189, `.orig.tree` 7,605. `APOE_HUMAN` (`UniProtKB=P02649`) is a leaf of its tree.

## Goals / Non-Goals

**Goals:**

- The form's example scores against the sample, and the Perl confirms its four results exactly.
- Every existing golden stays byte for byte as it is.

**Non-Goals:**

- Changing the generator, its seed or its sizes.
- Changing the API's or the frontend's tests. In their areas, only statements the new sample makes wrong change (decision 8).

## Decisions

1. **Build `csnp-sample-3` by the documented steps,** from the same pinned archives, with the families list `sample.json` gives plus `PTHR18976`. Build it twice and compare, as for `csnp-sample-2`. Publish it as a pre-release; `csnp-sample-2` stays, since older commits pin it.
2. **Regenerate all the generated cases, and run the Perl on all of them,** by golden-setup's commands, not just on the new family.
   - Since each family has its own seed, the only changes must be `PTHR18976`'s two new files and its entry in `cases.json`. Anything else in the diff means the generator isn't stable per family: stop, and record it in the Notes.
   - Running every family again costs about 5 minutes, and confirms once more that the Perl's output is the same from run to run.
   - *Alternative:* `parity cases --family PTHR18976` and `parity reference --family PTHR18976` only. Rejected: it would leave `cases.json` to be edited by hand, and checks nothing about the other families.
3. **The example's goldens:**
   - `example/apoe.fasta`: the legacy help page's sequence (`tips_exampleCsnpInput_content.jsp`), its ten lines as written, under `>APOE`.
   - `example/apoe.input`: the four SNP lines exactly as `score()` gives them to step 2.
   - `example/apoe.snpparse` and `example/apoe.out`: the Perl's step-2 and step-3 output.
   - `blast/APOE.csv`: the step-1 golden, beside the three release proteins'.
   - *Alternative:* a step-2 run in `generated/`. Rejected: `generated/` is rewritten from the seed, and the example is a fixed input.
   - *Alternative:* `release/` or `spec/`. Rejected: those are copied unchanged from the 2016 release, or transcribed from the legacy spec.
4. **The Perl's output for the example comes from a short command in the reference image,** written into golden-setup.md as the step-1 golden's is. It runs the self-check first, and stops if that finds any difference, then `Reference.step2` and `Reference.step3`.
   - *Alternative:* a `parity example` subcommand, or a step of `parity reference`. Rejected: it's one fixed input, and `parity reference` also serves the staging run, which mustn't write into the committed goldens.
5. **Three tests:**
   - `test_csnp_golden.py`, marked `data`: the port's steps 2 and 3 on `blast/APOE.csv` and `example/apoe.input` give `apoe.snpparse` and `apoe.out`. It needs no `blastp`, so it runs in CI's `engine` job too.
   - `test_csnp_golden.py`, marked `tools("blastp")` and `data`: step 1 on `apoe.fasta` gives `blast/APOE.csv`. It's its own test, because the release proteins' test also compares with the `HUMAN` fixture, which doesn't have APOE.
   - `test_csnp_scoring.py`, marked `tools("blastp")` and `data`: `score()` on the example gives family `PTHR18976` and the scores in `apoe.out`, read with `to_score`, as the §7.3 test does (spec, The form's example).
6. **If the Perl and the port differ on the example,** it's a porting bug: fix it in this change, with the case in the Notes. The reference defines M1. If the fix reaches beyond step 2 or 3's handling of this input, stop and ask.
7. **`docs/design/tech-stack.md` doesn't change.** Its sentence on the sample describes `csnp-sample-1` and `csnp-sample-2` as history, and says `sample.json` pins the current sample, which stays true; [engine.md](../../../docs/testing/engine.md#the-csnp-data-sample) names the current sample.
8. **Correct the statements on `main` that the new sample makes wrong, in this change.** #26 merged while this change was under way, and says in five places that the example isn't in the sample: `docs/testing/api.md`, `docs/testing/frontend.md`, the manual QA's TC 2.4 (twice) and a comment in `frontend/e2e/csnp.spec.ts`. They'd be wrong from the moment this merges, and TC 2.4 would fail for a tester.
   - Each edit changes only the fact: the sample holds 16 families and scores the example. TC 2.4 expects the four scores the real API gives it, which are `apoe.out`'s.
   - No test's code changes, so whether the API's and the frontend's tests score the example stays their developers' call.
   - It makes the change cross-cutting, so all three developers review it.
   - *Alternative:* list them in the pull request for their owners to fix after the merge. Rejected by the engine developer (2026-10-30): `main`'s docs and manual QA would be wrong until then.

## Risks / Trade-offs

- [Publishing a release can't be quietly undone: manifests that pin it would fail to fetch if it changed] → It's a new tag, built twice to the same bytes, and published only with the engine developer's go-ahead at that task.
- [The example's best hit could differ between arm64 and amd64] → The step-1 tests run on both CI legs, as the release proteins' do.
- [Everyone's `.data` and CI's cache fetch the sample again] → Once, and it's about the same size as `csnp-sample-2`.

## Migration Plan

- **Developers:** run `panther-engine csnp sample fetch` again. The folder no longer matches the manifest, so it downloads `csnp-sample-3`, checks every file, and moves them into place. The other families' files are the same bytes as before.
- **CI:** the cache key changes with `sample.json`, so each job that uses the sample, `engine`, `engine-image` and `api-image`, fetches it once.
- **Rollback:** revert the commit. `csnp-sample-2` is still published, and its manifest comes back with the revert.
