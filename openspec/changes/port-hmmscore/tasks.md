# Tasks

Work test-first: write each group's tests, see them fail, then make them pass. Paths in `engine/` are relative to `engine/src/panther_engine/` unless they start with `engine/`. The engine's checks run in the engine image (`docker compose run --rm engine`), with the data sample in `.data/`.

## 1. Shared Pieces and Docs

- [x] 1.1 In `docs/parity/divergences.md`:
  - add row 13, hmmscore's tied best hits (`HMMSCORE-1`). The reference showed one of the tied IDs in hash order; the port reports the subfamily before its family, then the lowest PANTHER ID (design.md, decision 3). Fill in "Approved by" with "Engine developer" and the date once they approve this change's pull request;
  - add `HMMSCORE-11` to the "Not listed" paragraph.

  Verify `npx markdownlint-cli2` passes.
- [x] 1.2 In `docs/parity/hmmscore-legacy-behaviour.md`:
  - `HMMSCORE-1`'s parity call is now row 13;
  - `HMMSCORE-5` notes that the bound is inclusive (`>` at 338), so an E-value of exactly 1e-3 is kept;
  - add `HMMSCORE-11`: the CGI ignores `hmmsearch`'s status and never deletes its `.aln` (140 to 160). Never replicated;
  - note that `-c` is parsed and never used (84);
  - Golden Inputs points at `inputs.md`.

  In `docs/parity/README.md`, line 7 names the reference as `scoreAlignXml.cgi` and the `pantherScore.pl` it runs. In `docs/design/tech-stack.md`, add an hmmscore bullet beside `csnp`'s and `refmap`'s under the reference container: the image, HMMER 3.1b2, and amd64 only. Verify `npx markdownlint-cli2` passes.
- [x] 1.3 Add `core/hmmer.py`, with `hmmscan` and `hmmsearch` over `run_tool` (design.md, decision 5). Write `engine/tests/test_core_hmmer.py` first, with `make_tool` fakes:
  - each tool gets its arguments as a list, with `--cpu`, and no shell;
  - the table or report lands in the given file byte for byte;
  - a non-zero status is returned, not raised;
  - `subprocess.TimeoutExpired` passes through.

  Verify `pytest engine/tests/test_core_hmmer.py` passes.

## 2. Scoring

- [x] 2.1 Write `engine/tests/test_hmmscore_scoring.py` from the spec's scenarios, with hand-written tables and a saved `hmmsearch` report under `engine/tests/fixtures/hmmscore/tables/`. Cover:
  - the columns read, and the IDs `PTHR18976.SF2.pir` and `PTHR34093..pir`;
  - score before E-value, and the cutoff at `0.001` and at `0.0011`;
  - a table with no rows;
  - ties: the subfamily before its family, and `SF2` before `SF10` before another family;
  - the alignment's first and last lines;
  - "No name".

  Verify they fail for want of the code.
- [x] 2.2 Add `hmmscore/scoring.py` (design.md, decisions 1 to 4): the dataclasses, `DATA_VERSION`, `HmmscoreError`, `check_data()` and `score()`. Export them from `hmmscore/__init__.py`. Add tests:
  - `ValueError` for `mkvl`, `*` and an empty sequence, with no tool run;
  - a 10,001-letter sequence is accepted;
  - `check_data()` names a missing `globals/binHmm.h3p`;
  - the time limit raises `InputError` with decision 4's message, kills the fake tool and removes the folder;
  - a non-zero `hmmscan` or `hmmsearch`, or a missing model file, raises `HmmscoreError`;
  - `DATA_VERSION` is `"19"` with `PANTHER_DATA_DIR` unset.

  Verify 2.1's tests and these pass.
- [x] 2.3 Add end-to-end tests with the real tools:
  - `tools("hmmscan", "hmmsearch")` on the fixture library, `PTHR99999`: a consensus of one of its models gets that model's ID;
  - with `data("hmmscore")` on the sample:
    - APOE gets `PTHR18976:SF2` at `439.0`, with its `names.tab` name, and an alignment naming `sequence`;
    - APOE at `--cpu` 0 and 2 gives identical results;
    - two proteins scored at once each give their result alone.

  Verify they pass in the engine image.

## 3. The Command Line

- [x] 3.1 Add `panther-engine hmmscore score [FILE|-] [--cpu N] [--timeout S] [--json] [--usage]` to `hmmscore/cli.py`:
  - it reads one FASTA record, and normalises it as the API does: one header and whitespace removed, upper-cased;
  - it prints the hit or "No hit";
  - `--usage` adds the wall time and the tools' peak memory;
  - errors follow the CLI's convention: `panther-engine hmmscore score: <message>` on standard error, and exit 1.

  Extend `engine/tests/test_hmmscore_cli.py` with the spec's three scenarios. Verify they pass.
- [x] 3.2 In `docs/testing/engine.md`, document `hmmscore score`, and add hmmscore's rows to "Parity Tests". Verify `npx markdownlint-cli2` passes.

## 4. The Reference Image and the Goldens

- [x] 4.1 Add the `hmmer-3.1b2` and `hmmscore-reference` stages to the root `Dockerfile` (design.md, decision 6):
  - the Bioconda digest;
  - the tools copied to `/opt/hmmer-3.1b2/bin/`, and a build-time `hmmscan -h` check for 3.1b2;
  - Debian's `perl` and `libyaml-libyaml-perl`;
  - the `hmmscore-reference-scripts` context, with every file sha256-pinned.

  Verify:
  - it builds with `--platform linux/amd64` and the context from `git archive 89ea0ae`;
  - a changed `pantherScore.pl` fails the build, naming it;
  - `docker buildx build --target api` holds no `pantherScore.pl`, no `/opt/hmmer-3.1b2` and no `perl` package.

  If the Bioconda tools don't run there, build 3.1b2 from the survey's tarball instead, and record why in Notes.
- [x] 4.2 Write `engine/tests/golden/hmmscore/parity/cases.json` and `inputs/` (design.md, decision 7), with each input's source and sha256 in the goldens' README:
  - make the consensus inputs with 3.4's `hmmemit -c`, and record the command;
  - pick `no-hit` and `over-cutoff` by running `hmmscan` on the sample, and record their tables;
  - search the sample's models for an `HMMSCORE-5` case, and record what was found.

  Verify `cases.json` lists every input file, and every input holds only what the API sends.
- [x] 4.3 Add `panther-engine hmmscore parity reference` (design.md, decision 6):
  - the 3.1b2 presses of a data folder;
  - for each case, the CGI's `config.yaml`, the CGI posted `sequence=<posted>`, `pantherScore.pl -D B -n`, and `hmmsearch` for each tied ID;
  - one case at a time, into a temporary folder, then moved into place;
  - the self-check first.

  Unit-test the config, the environment and the arguments without Perl. Verify the self-check passes in the image on the sample.
- [x] 4.4 Run `parity reference` on the sample, in the image, on amd64. Commit `parity/sample/`, with each file's sha256 in the README. Verify that `tie-pthr35774`'s `best.tsv` lists both PTHR35774 and `PTHR35774:SF1`, and that `cgi.xml` for `no-hit` is `<scores>\n</scores>\n`.
- [ ] 4.5 Add `panther-engine hmmscore parity check` and `engine/tests/test_hmmscore_parity.py`, using `tools(…)` and `data("hmmscore")` (design.md, decisions 7 and 8):
  - every sample case gives its expected result;
  - a hand-changed golden E-value fails, naming the case;
  - the cross-checks hold for `cgi.xml`.

  Run it on both `engine-image` legs. Add `sample-arm64/` copies only for cases whose arm64 result differs, and list what differs in the README. Verify CI's `engine-image` legs pass.
- [x] 4.6 In `docs/parity/golden-setup.md`, add an `hmmscore` section: building the image from a checkout, running `parity reference` and `parity check`, the self-check and regenerating. In `docs/parity/inputs.md`, add an `hmmscore` section: each case and why. Verify `npx markdownlint-cli2` passes.

## 5. The Staging Run on the Full Library

- [ ] 5.1 On an amd64 machine with the full library verified (`panther-engine hmmscore data verify`), run `parity reference` with the full library, and commit `parity/full/`. Then run `parity check --goldens full`. Record the machine, the date and the result in `inputs.md`. For any difference: fix the port if it's the port's fault, or propose a row. Verify `parity check --goldens full` exits 0.
- [ ] 5.2 In fresh processes on the same machine, time `titin-10000` and APOE with `panther-engine hmmscore score --usage --cpu 0`. Add the wall time and peak memory to the survey doc's timing section, and comment them on #68. If `titin-10000` takes more than 240 s, propose a new time limit default there (design.md, decision 9). Verify both numbers are in the doc.

## 6. Final Check

- [ ] 6.1 Run the engine's checks in the image, with tools and data required: `ruff check`, `ruff format --check`, `basedpyright` and `pytest`. From the root, run `npx markdownlint-cli2`, `npx openspec validate port-hmmscore --strict --no-interactive` and `npx openspec validate --all --no-interactive`. Verify all pass, and record the results in Notes. Verify CI is green on the pull request, both `engine-image` legs included.

## Workflow follow-up

- Open a pull request against `main`. The engine developer approves it, and with it row 13. The API developer checks that `score()` is decision 4's interface, unchanged.
- Archive `add-hmmscore-survey-and-sample` first, so `hmmscore-data` is in `openspec/specs/`, then archive this change with `/opsx:archive`.
- Next, the wiring change:
  - remove `UNAVAILABLE`'s hmmscore row and the `501`;
  - call `score()` with `hmmscore_time_limit_seconds` and `hmmscore_cpu`;
  - add `check_data()` and `DATA_VERSION` to the API's startup checks and versions;
  - turn off HMM scoring's "coming soon" mark.
- #68: the hosting server's four values, measured there with the full library, come with the deploy, with the API developer.

## Notes

### Next action

Applied on 2026-11-16, at the developer's request, before the proposal had a review pull request of its own; `port-refmap` likewise shipped its proposal and code in one (#63). Groups 1 to 4 are done locally, apart from 4.5's CI check. Next:

1. Open the pull request against `main`, with the artifacts and the code. The engine developer approves row 13 there; fill in its "Approved by" and date then (1.1).
2. Watch both `engine-image` legs run `tests/test_hmmscore_parity.py`, then tick 4.5. Both passed locally: the reference image on emulated amd64 (162 hmmscore tests, `parity check` 15 of 15) and the engine image on arm64 (the whole suite, `parity check` 15 of 15).
3. Group 5 on an amd64 machine with the full library (Blockers), then 6.1's CI check.

### Checks (6.1), 2026-11-16

- **The engine image, arm64,** `PANTHER_REQUIRE_DATA=1`: `ruff check` and `ruff format --check` clean, `basedpyright` 0 errors, `pytest` 1,499 passed, none skipped.
- **The reference image, emulated amd64:** the hmmscore tests, 162 passed; `parity check` 15 of 15.
- **From the root:** `npx markdownlint-cli2` 0 issues; `openspec validate port-hmmscore --strict` valid; `openspec validate --all` 17 passed.
- **Not yet:** CI on the pull request, with both `engine-image` legs.

### Blockers

- **For group 5:** an amd64 machine with the full library (about 67 GB) and room for the reference image. The survey used the Endeavour node.
- **4.5 and 6.1** need CI on the pull request.

### Decisions made while applying

design.md and the spec record them since `/opsx:update` on 2026-11-16: `cgi.xml` without its `Content-type` header, the reports' file names without `:`, the cross-check taking any tied line, the runners returning the finished process, `run_tool`'s two options, `core/fasta.py`, "No name" for an empty name, Perl's whitespace in the table, `--usage` on standard error, and the 15th case, `best-over-cutoff`.

### Failed approaches

None.

### Lessons learned

- **Measure HMMER on amd64.** A Mac build of 3.1b2 for CPUs without SSE (`impl_dummy`) split hits at `.`, `_`, `~`, `-` and an inner `*`, and production's builds didn't (#76, 2026-11-13). The reference image is amd64 only for that reason.
- **From port-refmap:** capture a reference's output with `run_tool(stdout=…)`, since text-mode capture rewrites CR. And Perl's `split` into scalars keeps a trailing empty field.
- **The query's name is part of the output:** `hmmsearch`'s report says `>> sequence`, so the port names the query as the CGI did.
- **The Bioconda 3.1b2 tools run on the engine's Debian** as they are: no fallback build was needed (4.1).
- **`hmmsearch`'s reports end with the run's CPU time,** so the goldens are never the same bytes twice. Only the alignment section is compared.
- **An `HMMSCORE-5` case is rare:** one in 110,991 windows of the sample's consensus sequences, APOE and `test.fasta`. Score and E-value only invert between models of different lengths, and here by 0.1 bit across 1e-3.
- **Python's `float()` strips whitespace,** `\xa0` included, where Perl's numeric reading of such a string is 0. It only matters for a table HMMER never writes.
