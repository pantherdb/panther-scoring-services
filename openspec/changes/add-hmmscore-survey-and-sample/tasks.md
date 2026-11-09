# Tasks

## 1. Prerequisites and Shared Docs

- [ ] 1.1 Download `https://data.pantherdb.org/ftp/hmm_scoring/19.0/PANTHER19.0_hmmscoring.tgz` once, outside the repository, with `curl -fL -C - -o …` so an interrupted download resumes. Record in the Notes:
  - where it is;
  - the time it took;
  - its sha256 from `shasum -a 256`.

  Verify that its size is 18,494,793,691 bytes, and that `gzip -t` passes
- [ ] 1.2 In `CLAUDE.md`, record the engine developer's answers of 2026-11-09.
  - **The gotcha "Two copies of the HMM scoring CGIs that differ too":** replace "Which copies run in production needs team verification" with:
    - the site's copies are from the HMMER2 era (`use Algs::Hmmer`, `./PANTHER7.2`, `-B ./blastall`), so they can't have served PANTHER 19;
    - production ran `pantherScoring`'s `scoreAlignXml.cgi`;
    - `alignOnTheFly.cgi` isn't used any more.
  - **The `hmmscore` section's data line:** the data is `PANTHER19.0_hmmscoring.tgz`. The FASTA file with a DBM index was only for `alignOnTheFly.cgi`'s `seqId` lookup. `binHmm` had its own folder in production only to put the big files on another volume.
  - **The `alignOnTheFly.cgi` row:** add "not used any more".

  Verify that `grep -n -E 'Which copies run|DBM index' CLAUDE.md` finds only the corrected text, and that `npx markdownlint-cli2` passes
- [ ] 1.3 In `docs/design/tech-stack.md`, record the same answers:
  - **The `hmmscore` section's Data line,** as in 1.2.
  - **The `hmmscore` open questions:**
    - "Production CGIs": answered as in 1.2;
    - "Library modes": answered from the code. Only prod is used: `scoreAlignXml.cgi:63` builds the library as `"prod"`, and `pantherScore.pl`'s `-P` defaults to prod.
  - **The Shared Concerns data table:**
    - a `/data/hmmscore/<version>/` row: the HMM library from `PANTHER19.0_hmmscoring.tgz`, pinned by `engine/src/panther_engine/hmmscore/data.json` (`add-hmmscore-survey-and-sample`);
    - drop `hmmscore` from the `/data/panther/<version>/` row's users, as `port-refmap` did for refmap.
  - **The Status line:** the revision.

  Verify that `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass
- [ ] 1.4 In `CONTRIBUTING.md`'s Spec Layout, add `hmmscore-data`: "The hmmscore data: reading the PANTHER 19 HMM library's `names.tab` and models, the library survey, the pinned library with fetching and verifying it, and the data sample". Verify `npx markdownlint-cli2` passes

## 2. Shared Helpers in core/

- [ ] 2.1 Move these to a new `core/archive.py` (design.md, decision 8):
  - `open_stream`, `member_lines` and their read size, from `csnp/survey.py`;
  - `write_tarball` and `unpack`, from `csnp/sample.py`. `unpack` takes the top folder its members must be under.

  Update the imports in `csnp/survey.py`, `csnp/sample.py` and `csnp/full.py`. Move the tests that exercise only these helpers to `tests/test_archive.py`. Verify that:
  - `git grep -n -E 'def (open_stream|member_lines|write_tarball|unpack)'` finds only `core/archive.py`;
  - `uv run ruff check`, `uv run ruff format --check` and `uv run basedpyright` pass;
  - `PANTHER_REQUIRE_DATA=1 uv run pytest` passes with the cSNP sample and refmap data fetched
- [ ] 2.2 Add `open_https(url)` to `core/download.py`, and rewrite `download()` on top of it (design.md, decision 8). Verify that `tests/test_download.py` covers:
  - a streamed read;
  - the refusal of an `http://` URL;
  - the refusal of a redirect to `http://`.

## 3. Readers

- [ ] 3.1 Add fixtures under `engine/tests/fixtures/hmmscore/`:
  - **Tiny real models,** built with the pinned `hmmbuild` from three-sequence alignments in the engine image: a family, two subfamilies, and a subfamily that is the family's copy, named `PTHR99999.orig.30.pir`. A short README there says how to rebuild them.
  - **A `names.tab` for them.**
  - **Broken copies:**
    - a line without a tab;
    - a repeated key;
    - a key without `.mod`;
    - CRLF line ends;
    - two models in one model file;
    - a model cut off before `//`;
    - a model without `NAME`.

  Add `engine/tests/fixtures/hmmscore/** -text` to `.gitattributes`. Verify that `git ls-files --eol engine/tests/fixtures/hmmscore/` shows the CRLF copy stored as `i/crlf`
- [ ] 3.2 Add `hmmscore/library.py` (design.md, decisions 1 and 3): the member kinds by path below the prefix, the `names.tab` reader, the HMM text reader and `LibraryFormatError`. Verify that `tests/test_hmmscore_library.py` covers:
  - every scenario of "Reading names.tab" and "Reading HMM files";
  - every member kind, an unexpected member, and a path with `..`
- [ ] 3.3 Add `hmmscore/legacy.py`: `getHmmNames`'s key and `runHmmscan`'s model ID, each with a comment citing its lines in `pantherScore.pl` at `89ea0ae` (code unchanged since `d7b28ee`). Verify that `tests/test_hmmscore_legacy.py` covers:
  - every scenario of "The legacy readings";
  - agreement with the strict reader on every line of the clean fixture `names.tab`

## 4. Library Survey

- [ ] 4.1 Add `hmmscore/survey.py` (design.md, decision 3):
  - one streamed pass, with the tarball's sha256 and size from the same pass;
  - the checks in the spec's survey requirements;
  - a report of each check's count and up to five examples, smallest first, as text and JSON;
  - `binHmm`'s model list from the flat file, or else from `binHmm.h3i`.

  Verify that `tests/test_hmmscore_survey.py` covers every scenario of these requirements, on tarballs built in `tmp_path` from the fixtures:
  - "Survey of the tarball's members";
  - "Survey of names and models";
  - "Survey of one-subfamily families";
  - "Survey of binHmm", once with a flat `binHmm` and once with only its pressed files;
  - "Survey of the pressed files".

  The pressed files are made once by the pinned `hmmpress` and committed as fixtures; the README of task 3.1 says how
- [ ] 4.2 Add `hmmscore/cli.py` with `panther-engine hmmscore survey TARBALL [--json FILE]`, and register it in `cli.py`. Verify that `tests/test_hmmscore_cli.py` covers the "Survey a tarball", "Nothing written" and "Unreadable tarball" scenarios, a truncated gzip and a plain text file among them. Also verify that `uv run panther-engine hmmscore survey --help` lists the options

## 5. Survey of the Pinned Tarball

- [ ] 5.1 From `engine/`, run `uv run panther-engine hmmscore survey <tarball> --json <scratch>/survey.json` under `/usr/bin/time -l`. Verify that:
  - it reads to the end;
  - it reports task 1.1's sha256 and size.

  Record the run time and peak memory in the Notes
- [ ] 5.2 Compare the results with what is expected (design.md, Context):

  | Check | Expected |
  | ----- | -------- |
  | Models in `books/` | 15,683 family and 128,012 subfamily models (the README) |
  | `names.tab` | 143,695 lines, all in the two shapes, none keyed differently by `getHmmNames` |
  | One-subfamily families | 5,450, each subfamily's file a copy of the family's named `PTHRnnnnn.orig.30.pir` |
  | `binHmm` | every model has its model file; count and repeated names as found |
  | Pressed files | format 3/f |
  | Members | nothing unexpected |

  Verify that every figure matches, or that each difference is traced to its cause and explained. A bug in a reader is fixed with a failing test first, then the survey is run again. Record anything that changes the design under Decisions during apply, and update design.md to match
- [ ] 5.3 Start `docs/parity/hmmscore-library-survey.md`, and add it to the What Goes Here table in `docs/parity/README.md`. It holds:
  - the date and the engine commit;
  - the tarball's URL, size and sha256, and the command;
  - each check's result, beside what was expected.

  Verify that `npx markdownlint-cli2` passes

## 6. The Pinned Library

- [ ] 6.1 Add `data manifest` to `hmmscore/data.py`, and `panther-engine hmmscore data manifest TARBALL --url URL` (design.md, decision 4). Verify that `tests/test_hmmscore_data.py` covers:
  - the "Reproducible" and "Unexpected member" scenarios of "Pinning the library";
  - a member outside the prefix;
  - a model file that doesn't read

  all on built tarballs
- [ ] 6.2 Add `data fetch` and `data verify` with `--data-dir`, plus `--tarball FILE` for fetch (design.md, decision 5). Verify, on built tarballs with their pins passed in and `open_https` replaced by a stub that serves them, that the tests cover:
  - every scenario of "Fetching the library", "Verifying the library" and "Data layout";
  - "Already fetched" with a stub that fails if called;
  - a failed fetch leaving the data folder as it was
- [ ] 6.3 Run `uv run panther-engine hmmscore data manifest <tarball> --url https://data.pantherdb.org/ftp/hmm_scoring/19.0/PANTHER19.0_hmmscoring.tgz`, and commit `hmmscore/data.json`. Verify that:
  - a second run gives the same bytes;
  - the pin's sha256 is task 1.1's;
  - its model count is the survey's;
  - `uv build --wheel` includes `data.json`
- [ ] 6.4 Fetch the full library into a folder outside the repository with `data fetch --tarball <tarball> --data-dir <folder>`, then run `data verify`. Record in the Notes and the survey doc:
  - the time;
  - the peak memory;
  - the bytes kept.

  Verify that:
  - `shasum -a 256 -c books.sha256` in `<folder>/hmmscore/19/` reports every line OK;
  - no `cluster.pir` or `tree.tree` was written;
  - a second fetch downloads nothing
- [ ] 6.5 Once, fetch from the URL itself into an empty folder, with no `--tarball`. It takes about 50 minutes at the 6 MB/s measured here, so run it in the background. Verify that it ends with the same files as task 6.4, and record the time in the Notes
- [ ] 6.6 Write the "hmmscore Full Library" section of `docs/testing/engine.md`:
  - fetching it, and the disk and time it takes;
  - `--tarball` for a download made with `curl -C -`;
  - `data verify`, and checking by hand with `shasum -a 256 -c books.sha256`, or `sha256sum -c` on Linux;
  - why the pin is `data.json` plus `books.sha256`;
  - pinning a new release with `data manifest`.

  Verify that `npx markdownlint-cli2` passes, and that tasks 6.3 and 6.4 ran the commands as written

## 7. Checks and Measurements on the Full Library

- [ ] 7.1 If the tarball has no flat `binHmm`, write `binHmm.h3m` out as text with `hmmconvert` in the engine image. Then compare each model, without its format line, with its model file in `books/`. Record the result in the survey doc; with a flat `binHmm`, record that the survey's text comparison covered it. Verify that every model is accounted for: identical, or listed with how it differs
- [ ] 7.2 The press check (design.md, decision 6), on amd64:
  1. Press the shipped models with HMMER 3.4's `hmmpress` into a scratch folder.
  2. Compare the four pressed files with the shipped ones, byte for byte.
  3. If they differ, compare `hmmscan`'s tables, without their `#` lines, for the example and `test.fasta` against both sets.

  Record in the survey doc which ran, and where. Verify that either the files are identical, or the tables are. If neither is, record the decision on pressing at fetch under Decisions during apply before going on
- [ ] 7.3 The `hmmscan` measurements of design.md, decision 9, in the engine image against the fetched library:
  - the example (`engine/tests/golden/csnp/example/apoe.fasta`, named `sequence`);
  - each sequence of `test.fasta`, with its URL and sha256 recorded (`https://data.pantherdb.org/ftp/hmm_scoring/19.0/pantherScore2.2/test.fasta`);
  - a sequence of about 5,000 residues;
  - one of 50,000 residues.

  For each: the cache cold and warm, the default `--cpu` and `--cpu 1`, and peak memory. Record the numbers, the machine and the architecture in the survey doc, and keep the example's and `test.fasta`'s tables for task 7.4. Verify that the doc gives, for each query, the time and memory needed, and the RAM needed to keep `binHmm.h3f` cached
- [ ] 7.4 Choose the sample's families (design.md, decision 7):
  - from task 7.3's tables, the families of the example's and `test.fasta`'s hits that pass 1e-3, up to ten for each sequence;
  - from the survey, the smallest family showing each non-zero family- or model-level check;
  - a one-subfamily family, and a family with many subfamilies.

  Record them in the survey doc, each with the reason it's in, and each sequence's best-scoring model on the full library. Verify that every non-zero family- or model-level check has a family in the table

## 8. The Sample

- [ ] 8.1 Add `build` to `hmmscore/sample.py`, and `panther-engine hmmscore sample build TARBALL --families FILE --tag TAG` (design.md, decisions 6 and 7). It checks the tarball against the pin, checks `hmmpress`'s version, and runs `hmmpress` on the relative name `binHmm` inside its temporary folder. Verify that `tests/test_hmmscore_sample.py` covers:
  - "Wrong tarball";
  - "Wrong HMMER", with a fake `hmmpress` from `make_tool`;
  - the tarball's members sorted, owned by 0 and dated 0, on a built tarball;
  - "Reproducible", marked `tools("hmmpress")`, run in the image
- [ ] 8.2 Add `fetch` and `verify` to `hmmscore/sample.py`, with their subcommands, `--from FILE` and `--data-dir`. Verify that the tests cover every scenario of "Fetching the sample" and "Verifying the sample", and the refusal of an `http://` URL. A failed fetch must leave the data folder as it was
- [ ] 8.3 In `tests/conftest.py`, add `DATA_MANIFESTS["hmmscore"]` and the `hmmscore_data` fixture (design.md, decision 10). Verify that a test marked `data("hmmscore")`:
  - is skipped, naming the data and `PANTHER_DATA_DIR`, when the sample isn't there;
  - fails with `PANTHER_REQUIRE_DATA=1`
- [ ] 8.4 In the engine image, run `panther-engine hmmscore sample build` on the tarball with task 7.4's families and `--tag hmmscore-sample-1`. It writes `hmmscore-sample-1.tar.gz` and `src/panther_engine/hmmscore/sample.json`. Verify that:
  - a second build is byte-identical;
  - each model file's sha256 in `sample.json` is its line in task 6.4's `books.sha256`, and the README's is the pin's;
  - `uv build --wheel` includes `sample.json`.

  Record the tarball's size, compressed and unpacked, in the Notes
- [ ] 8.5 Add `tests/test_hmmscore_sample_data.py`, marked `data("hmmscore")`. It checks that:
  - the sample matches its manifest;
  - its README's sha256 is `data.json`'s;
  - every `names.tab` line and model file reads strictly;
  - surveying the sample, tarred up in `tmp_path`, finds every family- or model-level check that was non-zero for the full library ("Every variant").

  Verify that it passes, with none skipped, against the sample unpacked by `fetch --from` the local tarball
- [ ] 8.6 Add the committed table `engine/tests/golden/hmmscore/sample-hmmscan/apoe.domtblout`: `hmmscan --domtblout` for the example, named `sequence`, against the sample, without the `#` lines. Add tests marked `tools("hmmscan")` and `data("hmmscore")` that check:
  - the table equals it ("The sample's pressed files on both architectures");
  - its highest-scoring model is task 7.4's full-library best ("The example's best hit").

  Verify that both pass in the engine image on arm64 and on amd64
- [ ] 8.7 With the engine developer's approval to publish recorded in the Notes, run `gh release create hmmscore-sample-1 hmmscore-sample-1.tar.gz --prerelease --title "hmmscore data sample 1" --notes "See docs/parity/hmmscore-library-survey.md"`. Then fetch into an empty `.data/` with `uv run panther-engine hmmscore sample fetch --data-dir ../.data`. Verify that:
  - the fetch downloads and verifies;
  - a second fetch downloads nothing;
  - `gh release view hmmscore-sample-1` shows the asset at the manifest's size;
  - the repository's Latest release is unchanged
- [ ] 8.8 Write the hmmscore parts of `docs/testing/engine.md`:
  - "The hmmscore Data Sample": fetching it natively and through compose;
  - "Publishing a New hmmscore Sample": build in the image, `gh release create … --prerelease`, commit the manifest;
  - the `hmmscore_data` fixture in "Tests That Need the Data".

  Also add the sample to `tech-stack.md`'s Data bullets, linking `engine.md`. Verify that `npx markdownlint-cli2` passes, and that task 8.7 ran the commands as written

## 9. CI

- [ ] 9.1 In the `engine` job of `.github/workflows/ci.yml`:
  - restore `.data/hmmscore` with `actions/cache`, pinned to the same commit SHA as the other cache steps, with the key `hmmscore-sample-${{ hashFiles('engine/src/panther_engine/hmmscore/sample.json') }}`;
  - run `uv run panther-engine hmmscore sample fetch --data-dir ../.data`.

  Verify that actionlint (`uvx --from actionlint-py actionlint`) reports no errors
- [ ] 9.2 In the `engine-image` job:
  - restore the same cache;
  - fetch inside the built image, with `.data` mounted writable at `/fetch` and `--user "$(id -u):$(id -g)"`;
  - add nothing else, since the existing test step already mounts `.data` read-only with data required.

  Verify that actionlint reports no errors, and that the steps pass locally with `docker buildx build --target engine --load` and `docker run`
- [ ] 9.3 In `docs/testing/README.md`, add the hmmscore sample fetch to the `engine` and `engine-image` rows of What CI Runs. Verify that the commands named match `ci.yml`, and that `npx markdownlint-cli2` passes

## 10. HMMER 3.1b2 Against 3.4

- [ ] 10.1 Run the comparison of design.md, decision 9, on the sample. Use Bioconda's `hmmer=3.1b2` in a throwaway `linux/amd64` container, and HMMER 3.4 in the engine image. Each presses its own copy of the sample's `binHmm`. Compare:
  - `hmmscan`'s tables for the example and `test.fasta`, without their `#` lines;
  - each best hit's `hmmsearch` alignment, from "Domain annotation for each sequence" to "Internal pipeline statistics summary:".

  If an amd64 machine with the full library is at hand, repeat the tables with the shipped pressed files. Verify that the survey doc records, for each comparison, identical or each difference
- [ ] 10.2 Finish `docs/parity/hmmscore-library-survey.md`:
  - the measurements;
  - the press check;
  - the comparison;
  - the sample's families;
  - what the findings mean for `port-hmmscore`:
    - the legacy readings to match;
    - how the one-subfamily copies are reported;
    - any HMMER difference to propose as a divergence row.

  In `tech-stack.md`'s Pinning Tool Versions, add a HMMER note: production most likely ran 3.1b2 (engine developer, 2026-11-09), 3.4 reads the shipped format, and the comparison's result, with a link to the survey doc. Verify that `npx markdownlint-cli2` passes

## 11. Final Check

- [ ] 11.1 From a clean clone of the branch, with the three data sets fetched into `.data/`, run these checks:
  - in `engine/`: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run basedpyright && PANTHER_REQUIRE_DATA=1 uv run pytest` passes, with only the `tools` tests skipped;
  - from the root, `docker compose run --rm engine` passes with nothing skipped;
  - from `api/`, which imports the engine, `uv sync --locked && uv run pytest` passes;
  - `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass

## Workflow follow-up

- **Review first.** Open a pull request with this change's artifacts, as CLAUDE.md's Development Workflow says. All three developers approve it, because it changes `CLAUDE.md`, `tech-stack.md` and `ci.yml`. The API developer reviews the CI changes, which the API's jobs share.
- **When the implementation's pull request is open,** confirm on it that:
  - the `engine` job and both `engine-image` legs fetch the hmmscore sample, missing the cache on the first run and hitting it on a re-run;
  - no data test is skipped in any of them (check the logs, not just the result);
  - the committed-table test passes on both `engine-image` legs;
  - the `api` and `api-image` jobs, which an engine change also runs, pass.
- **After it merges,** archive with `/opsx:archive`. That creates `openspec/specs/hmmscore-data/spec.md`.
- **Next for hmmscore: `port-hmmscore`.** It covers:
  - the Perl reference image, built from `pantherScoring` at `89ea0ae` and run through `scoreAlignXml.cgi`;
  - the goldens, on the sample;
  - `score()`;
  - `check_data()`;
  - the staging run on the full library.

  It proposes these divergence rows:
  - a fixed rule for tied best hits;
  - an input error for a sequence `hmmscan` can't read;
  - trimming before the header is removed;
  - any difference task 10.1 finds.
- **Before the port's scoring,** agree the engine's hmmscore interface with the API developer, in a change of its own.

## Notes

### Next action

Task 1.1: download the tarball.

### Approvals

- **Publishing the sample** as a public release asset of this repository: approved by the engine developer on 2026-11-09 (task 8.7). The sample carries the library's README, whose copyright statement must go with each copy.

### Decisions during apply

None yet.

### Inputs on this machine

None recorded yet (task 1.1).

### Blockers

None.

### Failed approaches

None yet.

### Lessons learned

None yet.
