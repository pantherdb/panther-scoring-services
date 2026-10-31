# Tasks

## 1. The Sample

- [x] 1.1 Write `families.txt` from `sample.json`'s 15 families plus `PTHR18976`, and build `csnp-sample-3` twice from the pinned archives, as `docs/testing/engine.md`'s Publishing a New Sample says (design.md, decision 1). Verify that the two tarballs are byte-identical, that `sample.json` lists 16 families, and that `PTHR18976`'s three files have the same sha256 as in `PAML_RST.tar.gz` (spec, The form's example family). Record the tarball's size, unpacked size and sha256 in the Notes
- [x] 1.2 Fetch the new tarball into an empty folder with `sample fetch --from`, and run the existing tests against it in the engine image with `PANTHER_REQUIRE_DATA=1`. Verify that they all pass unchanged, so no existing golden depends on the sample's family list
- [x] 1.3 Update `docs/testing/engine.md` (the tag and the sizes), `engine/README.md`'s Quick Start (the sample's size), and the survey's sample table in `docs/parity/csnp-library-survey.md` (`PTHR18976`, standing for the form's example, and the sentence above the table). Verify that `npx markdownlint-cli2` passes

## 2. Generated Cases for `PTHR18976`

- [x] 2.1 Regenerate the generated cases and run the Perl on every family, with `golden-setup.md`'s commands, against the new sample (design.md, decision 2). Verify that `git status` shows only `step3/PTHR18976.snpparse`, `step3/PTHR18976.out` and the new family in `cases.json`, and that `parity check` reports no differences. Record the family's case count and the kinds of node its walks stop at in the Notes
- [x] 2.2 Update `docs/parity/inputs.md`, Generated Step-3 Cases: the case and family counts, and the Kinds of Node table, from `parity check`'s report. Verify that the numbers match the report and that `npx markdownlint-cli2` passes

## 3. The Form's Example

- [x] 3.1 Write `engine/tests/golden/csnp/example/apoe.fasta` from the legacy help page (`tips_exampleCsnpInput_content.jsp`), and `example/apoe.input` with the four SNP lines as `score()` gives them to step 2 (design.md, decision 3). Write `blast/APOE.csv` in the engine image with `golden-setup.md`'s step-1 command, extended to the example. Verify that `APOE.csv`'s best hit for `HUMAN` is `APOE_HUMAN` (`P02649`) in `PTHR18976`
- [x] 3.2 In the reference image, run the self-check, then the Perl's steps 2 and 3 on the example, writing `example/apoe.snpparse` and `example/apoe.out` (design.md, decision 4). Verify that the self-check finds no difference. Compare `apoe.out` with the port's result in proposal.md, and record both in the Notes; if they differ, follow design.md, decision 6
- [x] 3.3 Add the three tests of design.md, decision 5. Verify that the `data` test passes natively, that all three pass in the engine image, and that the `data` test fails, naming the case, with one field of `apoe.out` changed by hand; then restore the file
- [x] 3.4 Document the example: `golden/csnp/README.md` (an `example/` table, and `blast/APOE.csv` with its sha256 in the step-1 table), `docs/parity/inputs.md` (a section for the form's example, and the step-1 golden's protein count), and `docs/parity/golden-setup.md` (the command from 3.2, and the step-1 command covering the example). Verify that the documented commands give the committed files byte for byte, and that `npx markdownlint-cli2` passes

## 4. Publish and Final Check

- [x] 4.1 With the engine developer's go-ahead, publish `csnp-sample-3` as a pre-release, as engine.md says. Verify that a fetch into an empty folder downloads and checks it, that a second fetch downloads nothing, and that the repository still has no Latest release
- [x] 4.2 From a copy of the files git would commit, with the sample fetched from the release, verify that everything passes, and record the counts in the Notes:
  - in `engine/`: `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright` and `PANTHER_REQUIRE_DATA=1 uv run pytest`;
  - `docker compose run --rm --build engine`, which runs the example's step-1 and end-to-end tests with `blastp`;
  - in `api/`, which imports the engine: `uv sync --locked` and `uv run pytest`;
  - `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive`.
- [x] 4.3 Move the branch onto `main`, which gained #26, #28, #31 and #32 while this change was under way, and correct the statements there that the new sample makes wrong: `docs/testing/api.md`, `docs/testing/frontend.md`, the manual QA's TC 2.4 and a comment in `frontend/e2e/csnp.spec.ts` (design.md, decision 8). Verify that:
  - nothing else names the sample's 15 families, or says the example isn't in it;
  - the real API, with `csnp-sample-3`, scores the form's example as TC 2.4 now says;
  - 4.2's checks pass again from a copy of the files git would commit, plus the API's tests in the API image with the tools and data, and the frontend's `type-check`, `lint` and `test`. Record the counts in the Notes.

## Workflow follow-up

- Open the pull request against `main`. Its CI is the first run on GitHub's runners with `csnp-sample-3`.
- After the merge, tell the API and frontend developers that the form's example now scores against the sample, with a Perl golden to check it against.
- Archive with `/opsx:archive`.

## Notes

### Next action

Every task is done, and `csnp-sample-3` is published. Open the pull request against `main`, for all three developers to review (design.md, decision 8). Its CI is the first run with `csnp-sample-3` on GitHub's runners.

### Blockers

None.

### Progress

- **`PTHR18976` in the library (2026-10-30):** `PAML_RST.tar.gz` (sha256 `6791f433…`) holds `PTHR18976.paml` (1,709,004 bytes), `.rst` (168,189) and `.orig.tree` (7,605). `APOE_HUMAN` (`P02649`) is a leaf of its tree.
- **The port on the example (2026-10-30),** in the engine image, against a copy of `csnp-sample-2` with those three files added: family `PTHR18976`; L46P 91, probably benign, 0.19; C130R 6, probably benign, 0.02; R163C 220, possibly damaging, 0.50; R176C 220, possibly damaging, 0.50. Against `csnp-sample-2` alone, every substitution is "Not scored: No PANTHER family for input sequence".

- **`csnp-sample-3` (task 1.1, 2026-10-30):** built twice from the pinned archives, about 1.6 minutes each; the tarballs and manifests are byte-identical. sha256 `a580b37d267643698a5da5e8828918038f1358b1d8ebdab01cdf2ea9a3b267a4`. 156,764,767 bytes (157 MB), 154 KB more than `csnp-sample-2`; unpacked 624,177,858 bytes (624 MB), exactly `PTHR18976`'s three files more. `sample.json` lists 16 families and 53 files, and its pins for the source archives, the BLAST database and the species tree didn't change. The tarball is in the session's scratchpad until 4.1 publishes it.
- **The existing tests on `csnp-sample-3` (task 1.2):** `fetch --from` the tarball into an empty folder checks every file, and `verify` passes; then into `.data/`, which went from 15 families to 16. In the engine image with `PANTHER_REQUIRE_DATA=1` and `PANTHER_REQUIRE_TOOLS=1`: 413 passed, none skipped. That's 3 more than before, from the sample-data tests parametrized over the manifest's families. No existing golden depends on the family list.
- **Generated cases (task 2.1):**
  - **The reference image** was rebuilt from this branch; the three scripts passed their sha256 checks.
  - **`parity cases`** wrote 16 families and 4 step-2 runs. Every existing input came back byte for byte.
  - **`parity reference`** passed the self-check, then ran every case in 7.4 minutes. Every existing output came back byte for byte; the diff is `PTHR18976.snpparse`, `PTHR18976.out` and its line in `cases.json`. 648 step-3 cases now, 42 of them `PTHR18976`'s.
  - **`parity check`:** 0 differences in every run and family. The walks now stop at `0>1` 224 (visited 258), `Ev=1>0, not read` 63 (99), `Ev=0>0, not read` 16 (29), `Ev=UNK, not read` 7 (7), missing taxon 24 (82), leaf 0 (295). `PTHR18976` adds 12, 12 and 6 stops to the first, second and fifth.
- **The example (tasks 3.1 and 3.2):**
  - **Step 1:** `blast/APOE.csv` has two hits. The best for `HUMAN` is `P02649` in `PTHR18976:SF2`, at 100% over all 317 residues.
  - **The Perl,** in the reference image, after a clean self-check, in 74 s: step 2 maps each position to itself on `APOE_HUMAN`, and step 3 gives L46P 91, probably benign, 0.19; C130R 6, probably benign, 0.02; R163C 220, possibly damaging, 0.50; R176C 220, possibly damaging, 0.50. Exactly the port's result above, so design.md's decision 6 wasn't needed.
  - **The tests (task 3.3):** natively the `data` test passes and the two `blastp` tests skip; in the engine image all three pass. With C130R's pDel changed to `0.03` in `apoe.out`, the `data` test fails with "example, case SNP_2 (line 2)"; the restored file passes.
  - **The docs (task 3.4):** golden-setup.md's two commands, run as written, give every `blast/*.csv` and `example/` file byte for byte.
- **Published (task 4.1), 2026-10-30,** with the engine developer's go-ahead: [`csnp-sample-3`](https://github.com/pantherdb/panther-scoring-services/releases/tag/csnp-sample-3), a pre-release with one asset of 156,764,767 bytes. A fetch from it into an empty folder took 16 s and checked every file; a second downloads nothing. The repository still has no Latest release.
- **Final check (task 4.2), 2026-10-30,** from `git checkout-index` of the staged files, with the sample fetched from the published release:
  - in `engine/`: `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright` and `PANTHER_REQUIRE_DATA=1 uv run pytest` pass; 396 passed, and only the 21 `tools` tests skipped. That's 5 more passed than #27's CI (`PTHR18976`'s three sample-data tests and its generated cases, and the example's `data` test), and 2 more skipped (the example's `blastp` tests);
  - `docker compose run --rm --build engine`, with `PANTHER_REQUIRE_DATA=1` and `PANTHER_REQUIRE_TOOLS=1`, passes: 417 passed, none skipped, 7 more than before;
  - in `api/`: `uv sync --locked`, `uv run pytest` (147 passed) and `uv lock --check` pass;
  - `npx markdownlint-cli2` (109 files, no issues) and `npx openspec validate --all --no-interactive` (13 passed) pass.
- **Onto `main` (task 4.3), 2026-10-30:**
  - **The move:** the branch was still at `ce48464`, with the change staged and nothing committed. It fast-forwarded to `1fca4dd` (#26, #28, #31 and #32), and the staged change merged with no conflict.
  - **The five statements,** all from #26: `docs/testing/api.md`'s and `docs/testing/frontend.md`'s, TC 2.4's family count and its expected rows for the example, and the comment in `frontend/e2e/csnp.spec.ts`. A search for "15" near "families", and for the example being missing from the sample, finds nothing else outside the archive, the goldens and `tech-stack.md`'s history (decision 7).
  - **The real API** (`docker compose up --build api`, with `.data` holding `csnp-sample-3`): the form's example, as `frontend/src/features/csnp/example.ts` has it, the same 317 residues as `apoe.fasta`, succeeds with family `PTHR18976` and exactly `apoe.out`'s four scores.
  - **The checks,** from `git checkout-index` of the staged files, with the sample fetched from the release. In `engine/`: 396 passed, 21 skipped. The engine image: 417 passed, none skipped. In `api/`: 172 passed, the 5 real-job tests skipped without `blastp`; `uv lock --check` passes. The API image, with the tools and data: 177 passed, none skipped. markdownlint (121 files) and `openspec validate` (9 passed) pass.
  - **The frontend:** `type-check` and `lint` pass, and `npm test` gives 205 passed under Node 25. This machine has no Node 24, the version `.nvmrc` pins, and under Node 20 Vitest can't load `undici`.

### Failed approaches

- **Task 1.2's first image run (2026-10-30)** stopped at `ruff format --check`, before any test: `engine/README.md`'s Python example lined up its trailing comments with extra spaces. Fixed with `uv run ruff format README.md`, which changed only those two lines.

### Lessons learned

- **`ruff format --check` in `engine/` formats Python code blocks in Markdown,** such as `engine/README.md`'s, so a README can fail CI's `engine` job. Run `uv run ruff format` after editing one.
