# Tasks

## 1. Prerequisites and Shared Docs

- [x] 1.1 Download `https://data.pantherdb.org/ftp/hmm_scoring/19.0/PANTHER19.0_hmmscoring.tgz` once, outside the repository, with `curl -fL -C - -o …` so an interrupted download resumes. Record in the Notes:
  - where it is;
  - the time it took;
  - its sha256 from `shasum -a 256`.

  Verify that its size is 18,494,793,691 bytes, and that `gzip -t` passes
- [x] 1.2 In `CLAUDE.md`, record the engine developer's answers of 2026-11-09.
  - **The gotcha "Two copies of the HMM scoring CGIs that differ too":** replace "Which copies run in production needs team verification" with:
    - the site's copies are from the HMMER2 era (`use Algs::Hmmer`, `./PANTHER7.2`, `-B ./blastall`), so they can't have served PANTHER 19;
    - production ran `pantherScoring`'s `scoreAlignXml.cgi`;
    - `alignOnTheFly.cgi` isn't used any more.
  - **The `hmmscore` section's data line:** the data is `PANTHER19.0_hmmscoring.tgz`. The FASTA file with a DBM index was only for `alignOnTheFly.cgi`'s `seqId` lookup. `binHmm` had its own folder in production only to put the big files on another volume.
  - **The `alignOnTheFly.cgi` row:** add "not used any more".

  Verify that `grep -n -E 'Which copies run|DBM index' CLAUDE.md` finds only the corrected text, and that `npx markdownlint-cli2` passes
- [x] 1.3 In `docs/design/tech-stack.md`, record the same answers:
  - **The `hmmscore` section's Data line,** as in 1.2.
  - **The `hmmscore` open questions:**
    - "Production CGIs": answered as in 1.2;
    - "Library modes": answered from the code. Only prod is used: `scoreAlignXml.cgi:63` builds the library as `"prod"`, and `pantherScore.pl`'s `-P` defaults to prod.
  - **The Shared Concerns data table:**
    - a `/data/hmmscore/<version>/` row: the HMM library from `PANTHER19.0_hmmscoring.tgz`, pinned by `engine/src/panther_engine/hmmscore/data.json` (`add-hmmscore-survey-and-sample`);
    - drop `hmmscore` from the `/data/panther/<version>/` row's users, as `port-refmap` did for refmap.
  - **The Status line:** the revision.

  Verify that `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass
- [x] 1.4 In `CONTRIBUTING.md`'s Spec Layout, add `hmmscore-data`: "The hmmscore data: reading the PANTHER 19 HMM library's `names.tab` and models, the library survey, the pinned library with fetching and verifying it, and the data sample". Verify `npx markdownlint-cli2` passes
- [x] 1.5 Write hmmscore's copy of the site's example, `engine/tests/golden/hmmscore/example/apoe.fasta` (design.md, decision 10). It holds the HMM scoring help page's ten lines as written (`tips_exampleHmmScoreInput_content.jsp`), under `>sequence`. Start `engine/tests/golden/hmmscore/README.md` with where the file comes from. Verify that:
  - its residues are the 317 of cSNP's `example/apoe.fasta`;
  - `npx markdownlint-cli2` passes

## 2. Shared Helpers in core/

- [x] 2.1 Move these to a new `core/archive.py` (design.md, decision 8):
  - `open_stream`, `member_lines` and their read size, from `csnp/survey.py`;
  - `write_tarball` and `unpack`, from `csnp/sample.py`. `unpack` takes the top folder its members must be under.

  Update the imports in `csnp/survey.py`, `csnp/sample.py` and `csnp/full.py`. Move the tests that exercise only these helpers to `tests/test_archive.py`. Verify that:
  - `git grep -n -E 'def (open_stream|member_lines|write_tarball|unpack)'` finds only `core/archive.py`;
  - `uv run ruff check`, `uv run ruff format --check` and `uv run basedpyright` pass;
  - `PANTHER_REQUIRE_DATA=1 uv run pytest` passes with the cSNP sample and refmap data fetched
- [x] 2.2 Add `open_https(url)` to `core/download.py`, and rewrite `download()` on top of it (design.md, decision 8). Verify that `tests/test_download.py` covers:
  - a streamed read;
  - the refusal of an `http://` URL;
  - the refusal of a redirect to `http://`.

## 3. Readers

- [x] 3.1 Add fixtures under `engine/tests/fixtures/hmmscore/`:
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
- [x] 3.2 Add `hmmscore/library.py` (design.md, decisions 1 and 3): the member kinds by path below the prefix, the `names.tab` reader, the HMM text reader and `LibraryFormatError`. Verify that `tests/test_hmmscore_library.py` covers:
  - every scenario of "Reading names.tab" and "Reading HMM files";
  - every member kind, an unexpected member, and a path with `..`
- [x] 3.3 Add `hmmscore/legacy.py`: `getHmmNames`'s key and `runHmmscan`'s model ID, each with a comment citing its lines in `pantherScore.pl` at `89ea0ae` (code unchanged since `d7b28ee`). Verify that `tests/test_hmmscore_legacy.py` covers:
  - every scenario of "The legacy readings";
  - agreement with the strict reader on every line of the clean fixture `names.tab`

## 4. Library Survey

- [x] 4.1 Add `hmmscore/survey.py` (design.md, decision 3):
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
- [x] 4.2 Add `hmmscore/cli.py` with `panther-engine hmmscore survey TARBALL [--json FILE]`, and register it in `cli.py`. Verify that `tests/test_hmmscore_cli.py` covers the "Survey a tarball", "Nothing written" and "Unreadable tarball" scenarios, a truncated gzip and a plain text file among them. Also verify that `uv run panther-engine hmmscore survey --help` lists the options

## 5. Survey of the Pinned Tarball

- [x] 5.1 From `engine/`, run `uv run panther-engine hmmscore survey <tarball> --json <scratch>/survey.json` under `/usr/bin/time -l`. Verify that:
  - it reads to the end;
  - it reports task 1.1's sha256 and size.

  Record the run time and peak memory in the Notes
- [x] 5.2 Compare the results with what is expected (design.md, Context):

  | Check | Expected |
  | ----- | -------- |
  | Models in `books/` | 15,683 family and 128,012 subfamily models (the README) |
  | `names.tab` | 143,695 lines, all in the two shapes, none keyed differently by `getHmmNames` |
  | One-subfamily families | 5,450, each subfamily's file a copy of the family's named `PTHRnnnnn.orig.30.pir` |
  | `binHmm` | every model has its model file; count and repeated names as found |
  | Pressed files | format 3/f |
  | Members | nothing unexpected |

  Verify that every figure matches, or that each difference is traced to its cause and explained. A bug in a reader is fixed with a failing test first, then the survey is run again. Record anything that changes the design under Decisions during apply, and update design.md to match
- [x] 5.3 Start `docs/parity/hmmscore-library-survey.md`, and add it to the What Goes Here table in `docs/parity/README.md`. It holds:
  - the date and the engine commit;
  - the tarball's URL, size and sha256, and the command;
  - each check's result, beside what was expected.

  Verify that `npx markdownlint-cli2` passes

## 6. The Pinned Library

- [x] 6.1 Add `data manifest` to `hmmscore/data.py`, and `panther-engine hmmscore data manifest TARBALL --url URL` (design.md, decision 4). Verify that `tests/test_hmmscore_data.py` covers:
  - the "Reproducible" and "Unexpected member" scenarios of "Pinning the library";
  - a member outside the prefix;
  - a model file that doesn't read

  all on built tarballs
- [x] 6.2 Add `data fetch` and `data verify` with `--data-dir`, plus `--tarball FILE` for fetch (design.md, decision 5). Verify, on built tarballs with their pins passed in and `open_https` replaced by a stub that serves them, that the tests cover:
  - every scenario of "Fetching the library", "Verifying the library" and "Data layout";
  - "Already fetched" with a stub that fails if called;
  - a failed fetch leaving the data folder as it was
- [x] 6.3 Run `uv run panther-engine hmmscore data manifest <tarball> --url https://data.pantherdb.org/ftp/hmm_scoring/19.0/PANTHER19.0_hmmscoring.tgz`, and commit `hmmscore/data.json`. Verify that:
  - a second run gives the same bytes;
  - the pin's sha256 is task 1.1's;
  - its model count is the survey's;
  - `uv build --wheel` includes `data.json`
- [x] 6.4 Fetch the full library into a folder outside the repository with `data fetch --tarball <tarball> --data-dir <folder>`, then run `data verify`. Record in the Notes and the survey doc:
  - the time;
  - the peak memory;
  - the bytes kept.

  Verify that:
  - `shasum -a 256 -c books.sha256` in `<folder>/hmmscore/19/` reports every line OK;
  - no `cluster.pir` or `tree.tree` was written;
  - a second fetch downloads nothing
- [x] 6.5 Once, fetch from the URL itself into an empty folder, with no `--tarball`. It takes about 50 minutes at the 6 MB/s measured here, so run it in the background. Verify that it ends with the same files as task 6.4, and record the time in the Notes
- [x] 6.6 Write the "hmmscore Full Library" section of `docs/testing/engine.md`:
  - fetching it, and the disk and time it takes, with the tarball's 18.5 GB wherever it's downloaded first;
  - `--tarball` for a download made with `curl -C -`;
  - a server whose container can't reach `data.pantherdb.org`, such as the hosting server behind its TLS-inspecting proxy (design.md, decision 3):
    - the host downloads the tarball;
    - `fetch` runs in the image, with the tarball's folder mounted read-only, as `docs/deployment/runbook-server.md` does for refmap's data.

    Give that command, so the runbook can start from it;
  - `data verify`, and checking by hand with `shasum -a 256 -c books.sha256`, or `sha256sum -c` on Linux;
  - why the pin is `data.json` plus `books.sha256`;
  - pinning a new release with `data manifest`.

  Verify that `npx markdownlint-cli2` passes, and that tasks 6.3 and 6.4 ran the commands as written

## 7. Checks and Measurements on the Full Library

- [x] 7.1 If the tarball has no flat `binHmm`, write `binHmm.h3m` out as text with `hmmconvert` in the engine image. Then compare each model, without its format line, with its model file in `books/`. Record the result in the survey doc; with a flat `binHmm`, record that the survey's text comparison covered it. Verify that every model is accounted for: identical, or listed with how it differs
- [x] 7.2 The press check (design.md, decision 6), on amd64:
  1. Press the shipped models with HMMER 3.4's `hmmpress` into a scratch folder.
  2. Compare the four pressed files with the shipped ones, byte for byte.
  3. If they differ, compare `hmmscan`'s tables, without their `#` lines, for the example and `test.fasta` against both sets.

  Record in the survey doc which ran, and where. Verify that either the files are identical, or the tables are. If neither is, record the decision on pressing at fetch under Decisions during apply before going on
- [x] 7.3 The `hmmscan` measurements of design.md, decision 9, in the engine image against the fetched library:
  - the example, task 1.5's `engine/tests/golden/hmmscore/example/apoe.fasta`;
  - each sequence of `test.fasta`, with its URL and sha256 recorded (`https://data.pantherdb.org/ftp/hmm_scoring/19.0/pantherScore2.2/test.fasta`);
  - a sequence of about 5,000 residues;
  - one of 50,000 residues, the website's limit.

  For each: the cache cold and warm, at `--cpu 0` (the default), `--cpu 2` and `--cpu 4`, and peak memory. Then run two and three copies of the example, and of the 5,000-residue query, at once, warm, at `--cpu 0`. Record the numbers, the machine and the architecture in the survey doc, and keep the example's and `test.fasta`'s tables for task 7.4. Verify that:
  - each query's tables are the same at every `--cpu`;
  - the doc gives each query's time and memory, alone and at once;
  - the doc says what a server needs (design.md, decision 9):
    - the RAM to keep `binHmm.h3f` cached;
    - the disk for the kept files, plus the tarball while fetching;
    - the time at 50,000 residues
- [x] 7.4 Choose the sample's families (design.md, decision 7):
  - from task 7.3's tables, the families of the example's and `test.fasta`'s hits that pass 1e-3, up to ten for each sequence;
  - from the survey, the smallest family showing each non-zero family- or model-level check;
  - a one-subfamily family, a family with many subfamilies, and a family with a `PTHRnnnnn..pir` model.

  Record them in the survey doc, each with the reason it's in, and each sequence's best-scoring model on the full library. Verify that every non-zero family- or model-level check has a family in the table

## 8. The Sample

- [x] 8.1 Add `build` to `hmmscore/sample.py`, and `panther-engine hmmscore sample build TARBALL --families FILE --tag TAG` (design.md, decisions 6 and 7). It checks the tarball against the pin, and the version of `hmmpress`. Without a flat `binHmm`, it cuts the chosen families' records out of `binHmm.h3m`, presses them as they are, and checks that the sample's `binHmm.h3m` is those records, byte for byte (Notes, Decisions during apply). It runs `hmmpress` on the relative name `binHmm` inside its temporary folder. Verify that `tests/test_hmmscore_sample.py` covers:
  - "Wrong tarball";
  - "Wrong HMMER", with a fake `hmmpress` from `make_tool`;
  - "The models as shipped", with a fake `hmmpress` that changes them, and marked `tools("hmmpress")` in the image;
  - the tarball's members sorted, owned by 0 and dated 0, on a built tarball;
  - "Reproducible", marked `tools("hmmpress")`, run in the image
- [x] 8.2 Add `fetch` and `verify` to `hmmscore/sample.py`, with their subcommands, `--from FILE` and `--data-dir`. Verify that the tests cover every scenario of "Fetching the sample" and "Verifying the sample", and the refusal of an `http://` URL. A failed fetch must leave the data folder as it was
- [x] 8.3 In `tests/conftest.py`, add `DATA_MANIFESTS["hmmscore"]` and the `hmmscore_data` fixture (design.md, decision 10). Verify that a test marked `data("hmmscore")`:
  - is skipped, naming the data and `PANTHER_DATA_DIR`, when the sample isn't there;
  - fails with `PANTHER_REQUIRE_DATA=1`
- [x] 8.4 In the engine image, run `panther-engine hmmscore sample build` on the tarball with task 7.4's families and `--tag hmmscore-sample-1`. It writes `hmmscore-sample-1.tar.gz` and `src/panther_engine/hmmscore/sample.json`. Verify that:
  - a second build is byte-identical;
  - each model file's sha256 in `sample.json` is its line in task 6.4's `books.sha256`, and the README's is the pin's;
  - `uv build --wheel` includes `sample.json`.

  Record the tarball's size, compressed and unpacked, in the Notes
- [x] 8.5 Add `tests/test_hmmscore_sample_data.py`, marked `data("hmmscore")`. It checks that:
  - the sample matches its manifest;
  - its README's sha256 is `data.json`'s;
  - every `names.tab` line and model file reads strictly;
  - surveying the sample, tarred up in `tmp_path`, finds every family- or model-level check that was non-zero for the full library ("Every variant").

  Verify that it passes, with none skipped, against the sample unpacked by `fetch --from` the local tarball
- [x] 8.6 Add the committed tables `engine/tests/golden/hmmscore/sample-hmmscan/amd64/apoe.domtblout` and `sample-hmmscan/arm64/apoe.domtblout`: `hmmscan --domtblout` for task 1.5's example against the sample, in the engine image on each architecture, without the `#` lines (Notes, Decisions during apply). In `golden/hmmscore/README.md`, say how they're made, why there are two, and that both are regenerated when the sample or HMMER changes. Add tests marked `tools("hmmscan")` and `data("hmmscore")` that check:
  - the table equals its architecture's ("The sample's pressed files on both architectures");
  - its highest-scoring model is task 7.4's full-library best ("The example's best hit").

  Verify that both pass in the engine image on arm64 and on amd64
- [x] 8.7 With the engine developer's approval to publish recorded in the Notes, run `gh release create hmmscore-sample-1 hmmscore-sample-1.tar.gz --prerelease --title "hmmscore data sample 1" --notes "See docs/parity/hmmscore-library-survey.md"`. Then fetch into an empty `.data/` with `uv run panther-engine hmmscore sample fetch --data-dir ../.data`. Verify that:
  - the fetch downloads and verifies;
  - a second fetch downloads nothing;
  - `gh release view hmmscore-sample-1` shows the asset at the manifest's size;
  - the repository's Latest release is unchanged
- [x] 8.8 Write the hmmscore parts of `docs/testing/engine.md`:
  - "The hmmscore Data Sample": fetching it natively and through compose;
  - "Publishing a New hmmscore Sample": build in the image, `gh release create … --prerelease`, commit the manifest;
  - the `hmmscore_data` fixture in "Tests That Need the Data".

  Also add the sample to `tech-stack.md`'s Data bullets, linking `engine.md`. Verify that `npx markdownlint-cli2` passes, and that task 8.7 ran the commands as written

## 9. CI

- [x] 9.1 In the `engine` job of `.github/workflows/ci.yml`:
  - restore `.data/hmmscore` with `actions/cache`, pinned to the same commit SHA as the other cache steps, with the key `hmmscore-sample-${{ hashFiles('engine/src/panther_engine/hmmscore/sample.json') }}`;
  - run `uv run panther-engine hmmscore sample fetch --data-dir ../.data`.

  Verify that actionlint (`uvx --from actionlint-py actionlint`) reports no errors
- [x] 9.2 In the `engine-image` job:
  - restore the same cache;
  - fetch inside the built image, with `.data` mounted writable at `/fetch` and `--user "$(id -u):$(id -g)"`;
  - add nothing else, since the existing test step already mounts `.data` read-only with data required.

  Verify that actionlint reports no errors, and that the steps pass locally with `docker buildx build --target engine --load` and `docker run`
- [x] 9.3 In `docs/testing/README.md`, add the hmmscore sample fetch to the `engine` and `engine-image` rows of What CI Runs. Verify that the commands named match `ci.yml`, and that `npx markdownlint-cli2` passes

## 10. HMMER 3.1b2 Against 3.4

- [x] 10.1 Run the comparison of design.md, decision 9, on the sample. Use Bioconda's `hmmer=3.1b2` in a throwaway `linux/amd64` container, and HMMER 3.4 in the engine image. Each presses its own copy of the sample's models, its `binHmm.h3m` copied as `binHmm`. Compare:
  - `hmmscan`'s tables for the example and `test.fasta`, without their `#` lines;
  - each best hit's `hmmsearch` alignment, from "Domain annotation for each sequence" to "Internal pipeline statistics summary:".

  If an amd64 machine with the full library is at hand, repeat the tables with the shipped pressed files. Verify that the survey doc records, for each comparison, identical or each difference
- [x] 10.2 Finish `docs/parity/hmmscore-library-survey.md`:
  - the measurements;
  - the press check;
  - the comparison;
  - the sample's families;
  - what the findings mean for `port-hmmscore`:
    - the legacy readings to match;
    - how the one-subfamily copies are reported;
    - any HMMER difference to propose as a divergence row;
    - whether the hosting server has what a server needs (task 7.3), from its memory and free disk, read on the server.

  In `tech-stack.md`'s Pinning Tool Versions, add a HMMER note: production most likely ran 3.1b2 (engine developer, 2026-11-09), 3.4 reads the shipped format, and the comparison's result, with a link to the survey doc. Verify that `npx markdownlint-cli2` passes

## 11. Final Check

- [x] 11.1 From a clean clone of the branch, with the three data sets fetched into `.data/`, run these checks:
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
  - the staging run on the full library;
  - the longest query hmmscore accepts, and the hosting server's memory. The server has 7 GiB, and `titin-50000`, at the website's limit, needed 21 GiB at `--cpu 0` (survey doc, "What It Means for port-hmmscore"). It's decided with the API developer, before hmmscore is deployed there.

  It proposes these divergence rows:
  - a fixed rule for tied best hits;
  - an input error for a sequence `hmmscan` can't read;
  - trimming before the header is removed;
  - any difference task 10.1 finds.
- **Before the port's scoring,** agree the engine's hmmscore interface with the API developer, in a change of its own. It includes hmmscore's `DATA_VERSION`, `"19"`, for the per-service `versions.data` that #64 added, as `refmap` exports its own.

## Notes

### Next action

Every task is done. Next, open the implementation's pull request, once the engine developer asks for it, and check CI on it as Workflow follow-up says.

The hosting server's memory is too small for hmmscore at the website's 50,000 residues (task 10.2). That's for `port-hmmscore` to settle with the API developer (Workflow follow-up), not this change.

### Commits

The engine developer asked for the commits on 2026-11-10. They're on `feat/add-hmmscore-survey-and-sample-apply`, one for each layer, and each passes the engine's checks on its own, from a `git archive` of it:

| Commit | What | Tasks |
| ------ | ---- | ----- |
| `8338a1e` | The tarball helpers in `core/archive.py`, and `open_https` | 2.1, 2.2 |
| `72012f7` | The readers, the legacy readings and `hmmscore survey`, with the fixtures | 3.1 to 3.3, 4.1, 4.2 |
| `b560b8e` | The pin, `data.json`, and `hmmscore data manifest`, `fetch` and `verify` | 6.1 to 6.3 |
| `b1a6db6` | The sample, `sample.json`, the `hmmscore` data marker and the committed tables | 1.5, 8.1 to 8.6 |
| `739caad` | CI | 9.1 to 9.3 |
| `d5dff79` | The docs, the survey doc naming the engine commits | 1.1 to 1.4, 5.3, 6.6, 7.1 to 7.4, 8.8, 10.1, 10.2 |
| `bff0575` | This change's artifacts and notes | |
| The next one | Task 11.1 ticked, with its results below | 11.1 |

- **`hmmscore/cli.py` grew with the commits:** `72012f7`'s has only `survey`, and `b560b8e`'s adds `data`. Each version is the final file with the later commands' blocks left out. Only the module's docstring and `panther-engine --help`'s line for `hmmscore` were written for it, to name the commands it has.
- **The survey's code, at `72012f7`, is unchanged since.** Run again on 2026-11-10 with the engine at `b1a6db6`, it gave yesterday's report, byte for byte (task 5.3).
- **The final check (task 11.1),** on 2026-11-10, from `git clone --branch feat/add-hmmscore-survey-and-sample-apply` at `bff0575`, with the three data sets fetched into its `.data/` in 29 s. Everything passed:
  - in `engine/`: ruff, the formatter and basedpyright; `PANTHER_REQUIRE_DATA=1 uv run pytest`: 1,272 passed, and the 35 skipped are all `tools` tests (BLAST+ and EPA-ng aren't installed natively, and this Mac's HMMER is 3.1b2);
  - `docker compose run --rm --build engine`, with `PANTHER_REQUIRE_DATA=1` and `PANTHER_REQUIRE_TOOLS=1`, so any skip would fail: 1,307 passed;
  - in `api/`: 393 passed, and the 7 skipped are `blastp`'s;
  - `npx markdownlint-cli2`, and `npx openspec validate --all --no-interactive`: 15 passed.
- **Left out:** six files in the working tree that aren't this change's. They're `docs/code-review/2026-10-30-whole-repo-review.md`, `docs/code-review/2026-11-02-refmap-form.md` and the four `panther-api-*.tar.gz` at the root.

### Approvals

- **Publishing the sample** as a public release asset of this repository: approved by the engine developer on 2026-11-09 (task 8.7). The sample carries the library's README, whose copyright statement must go with each copy. Confirmed for the built `hmmscore-sample-1` on 2026-11-10, and published that day.

### Decisions during apply

- **The moved helpers' errors (task 2.1).** `core/archive.py` raises its own `ArchiveError`. cSNP's fetch turns it back into a `SampleError`, and its survey into a `SurveyError`, so cSNP's commands and messages don't change. No cSNP test exercised only the helpers (they go through `build` and `fetch`), so `tests/test_archive.py` tests them directly, and cSNP's tests stay where they were.
- **The survey's prefix (task 4.1).** It's PANTHER 19's, `PREFIX` in `hmmscore/survey.py`, as the spec's command has no `--prefix`. The tests tar their libraries under it.
- **`names-legacy-key` (task 4.1)** counts every line `getHmmNames` keys other than by the strict reader's ID, including the lines the strict reader rejects. On a line the strict reader accepts, the two keys can't differ, so the check is only non-zero alongside `names-rejected`.
- **The `tools` marker and HMMER's version (task 8.1).** The engine developer's machine has HMMER 3.1b2 in `/usr/local/bin`, so tests marked `tools("hmmpress")` or `tools("hmmscan")` would run natively against it, and fail. `tests/conftest.py` now counts an HMMER program as missing unless its `-h` names the image's 3.4, `hmmscore/sample.py`'s `HMMER_VERSION`: the test is skipped, "needs hmmpress 3.4, found HMMER 3.1b2 at …", or fails under `PANTHER_REQUIRE_TOOLS=1`. `test_tools_marker.py` covers it. Other tools are unchanged.
- **The readers of the pressed index and the names (task 8.1).** `index_names`, `pressed_format`, `family_of` and `path_of` moved from `survey.py` to `library.py`, as the sample's build needs them too.
- **`data manifest --prefix` (task 6.1).** It defaults to PANTHER 19's prefix. A new release gives its own, as design decision 4 expects.
- **binHmm holds models no model file holds (task 5.2).** The tarball has no flat `binHmm`. Its index lists 144,361 models against 143,693 model files, with 6,118 names that no model file holds:
  - in each of the 5,450 one-subfamily families, the subfamily's own model, `PTHRnnnnn.SFn.pir`, whose model file is a copy of the family's;
  - in 668 families, a second family-level model named `PTHRnnnnn..pir`.

  No check reported them, so the survey gained `binhmm-not-in-books`, test first. Its second run reports all 6,118 and is otherwise the same as the first. Examples, cut from `binHmm.h3m` and converted by 3.4's `hmmconvert`:
  - `PTHR35774.SF1.pir` and `PTHR35774.orig.30.pir` are the same 34 positions and 39 sequences, built half an hour apart, and differ in 12 emission scores in the fifth decimal;
  - `PTHR34093..pir` is a model of one sequence, 269 positions, with a model mask; the family's own is 511 positions from 37 sequences.
- **The sample's binHmm (tasks 5.2 and 8.1; engine developer, 2026-11-09).** Design decision 6's fallback for a tarball without a flat `binHmm`, the model files in the index's order, can't give those 6,118 models. So `sample build` cuts the chosen families' records out of `binHmm.h3m`, at the index's offsets, as the tarball streams past. Until 2026-11-10 it converted them to text with the pinned `hmmconvert`, and pressed that; now it presses the records themselves (below). On the two families above, the converted text of each model that has a model file is that file byte for byte, apart from the format line, which is 3.4's.
- **The disk.** Fetched, the library keeps 67,062,857,219 bytes: `globals/` (34.7 GB) and the model files (32.4 GB). `cluster.pir` and `tree.tree` (9.8 GB) stay out. The press check needs about 48 GB besides, and task 6.5's fetch another 67 GB in an empty folder: more than this Mac's 105 GB free, with the tarball and one fetched copy.
- **The full-library tasks run on CARC's Endeavour (engine developer, 2026-11-09).** Tasks 6.4, 6.5, 7.1, 7.2 and 7.3, and 10.1's optional full-library step, run as two Slurm jobs that the engine developer submits, in `/scratch2/debert/panther-scoring-services/`. They're amd64, as 7.2 asks, and have the room. The jobs and their README are in `hmm_scoring/carc/` beside this repository. They run the engine image built for amd64, through Apptainer, with the working tree's `engine/` mounted, and record each step's wall time and peak memory with `os.wait4`. A "cold" run follows `posix_fadvise(DONTNEED)` on the pressed files, as far as a user without root can go.
- **The full library keeps its shipped pressed files, and fetch never presses (task 7.2; engine developer, 2026-11-10).** The press check found that HMMER 3.4 can't reproduce them. Pressing `hmmconvert`'s text of `binHmm.h3m` changed `.h3f`, `.h3m` and `.h3p`; only `.h3i` was the same. `hmmscan`'s tables then moved for a few hits near a cutoff: on `test.fasta`, PTHR24235.SF9 went from 53.6 to 54.0 bits as its envelope changed. On amd64, 3.1b2 and 3.4 give exactly the shipped files' tables, so keeping them keeps production's numbers. Design decision 6 already said so; this settles its "decided before `port-hmmscore`".
- **The sample presses the records cut from `binHmm.h3m` as they are (engine developer, 2026-11-10).** It replaces the `hmmconvert` step of "The sample's binHmm" above.
  - **Why:** 3.4 reads a text model's probabilities in single precision, `expf(-1.0 * atof(tok1))` (`src/p7_hmmfile.c`), so the text round trip changes about 1 probability in 1,000 by one unit in the last place.
  - **What it gives:** 3.4's `hmmpress` reads the records as a binary model file. On the first 25,000 models, it gives back the shipped `.h3m` and `.h3f` byte for byte, on amd64 and arm64. Only `.h3p` differs, as it does from any 3.4 press.
  - **The build now:** it no longer needs `hmmconvert`. It checks that the sample's `binHmm.h3m` is the cut records, byte for byte, and ships no flat `binHmm`, as the library has none.
  - **Nothing needs the flat file:** the legacy Perl gives `hmmscan` only the path `globals/binHmm` (`pantherScore.pl` 377), and HMMER opens `binHmm.h3m` when `binHmm` is absent.

  Test first, as in `tests/test_hmmscore_sample.py`: a fake `hmmpress` that copies its input to the `.h3m`, as the real one does, and a build that refuses a press that changes the records.
- **A committed sample table for each architecture (engine developer, 2026-11-10).** 3.4's `hmmscan` computes a few numbers differently on arm64 than on amd64, from the same pressed files. On the first 25,000 shipped models:
  - 2 of the example's 36 domains differ in the last digit: 13.1 against 13.2 bits, and a bias of 0.8 against 0.7;
  - `test.fasta`'s PTHR24235.SF9 domain moves its envelope.

  So the spec's single table can't pass on both `engine-image` legs. Task 8.6 commits `sample-hmmscan/amd64/apoe.domtblout` and `sample-hmmscan/arm64/apoe.domtblout`, each checked exactly on its own architecture. For `hmmscore-sample-1` the two are the same 11 lines: the domains that differ by architecture on the full library aren't in the sample.
- **`data manifest` writes `data.json` as any new file (task 9.2).** It wrote it through `tempfile.mkstemp`, so 0600 whatever the umask. Git records it as 644, so a clone is fine. But an image built from the working tree copied the 0600, and `docker run --user` couldn't read it. Now `write_file` opens a uniquely named partial file with `"xb"`, so the umask sets the mode. Test first: `test_the_manifest_is_as_readable_as_any_new_file`. refmap's `data manifest` (`refmap/data.py`, `port-refmap`) has the same `mkstemp`, and its `organisms.json` stops `panther-engine` from importing at all in such an image. That's outside this change, so it's left as it is, for the engine developer. The three local files were set to 644 by hand, which git doesn't see.
- **The sample is built on amd64 (task 8.4).** Production ran on amd64, and there 3.4's press of the records gives back the shipped `.h3f` byte for byte; on arm64 it differed in 2 bytes of the first 25,000 models'. The build ran in the amd64 engine image under Docker's emulation on this Mac.
- **The sample's families (task 7.4)** are in the survey doc: the example's one family; `test.fasta`'s ten with the highest-scoring best models, of the 56 with a hit that passes 1e-3; and one family each for `name-without-model` (PTHR24068), the one-subfamily checks (PTHR35774) and a `..pir` model (PTHR34093). Ten for `test.fasta` keeps the tarball at 33 MB, against cSNP's 157 MB.

### Inputs on this machine

Paths are relative to the parent folder of this repository.

| Input | Path | sha256 |
| ----- | ---- | ------ |
| `PANTHER19.0_hmmscoring.tgz`, 18,494,793,691 bytes | `hmm_scoring/19.0/PANTHER19.0_hmmscoring.tgz` | `77b3a9eae1d4d1baeaf345368b861f2474893711f0187a9767397a1a1d0e87c8` |

- **The download (task 1.1):** `curl -fL -C - -o …` on 2026-11-09, 3,055 s (51 minutes), about 6.1 MB/s, in one piece: no resume was needed.
- **Passes over the local copy,** natively on an Apple Silicon Mac with 10 cores, on 2026-11-09, the two at once:
  - the survey (task 5.1): 240 s, 431 MB at its peak (`/usr/bin/time -l`), 318,761 members read to the end, with task 1.1's sha256 and size;
  - `data manifest` (task 6.3's first run): 239 s, 363 MB.
- **The measurement queries (task 7.3),** fetched on 2026-11-09:
  - `https://data.pantherdb.org/ftp/hmm_scoring/19.0/pantherScore2.2/test.fasta`, one sequence, `>test`, 381 residues, sha256 `097bbf0c629a0b7aaa00c73c5368d11b9a5ba689412f4051ab5b353e03db2499`;
  - about 5,000 residues: human DYNC1H1, UniProt Q14204, 4,646 residues, `https://rest.uniprot.org/uniprotkb/Q14204.fasta`, sha256 `39c4c48c73e21f0207c64336bbb1cf9c8844a105d897038b4162e418a0c89c80`;
  - 50,000 residues, as for cSNP's BLAST+ timing (`docs/testing/engine.md`): titin, UniProt Q8WZ42 (34,350 residues; its FASTA's sha256 is `2bb79b409b2540249a432bd638215e5a789e69116eaf1ea0d15e48304e5c80f2`), then its first 15,650 residues, as `>titin-50000` in lines of 60, sha256 `157165b96b2b91a69dd45720ef5ef50f3ceb84712e7e860e43bf8ae7c7954f91`.

### The sample, `hmmscore-sample-1`

Built on 2026-11-10 (task 8.4), in 5 minutes 43 seconds, in the amd64 engine image under Docker's emulation on this Mac. From the repository root, with the families in `hmm_scoring/sample/families.txt`:

```sh
docker run --rm --platform linux/amd64 --user "$(id -u):$(id -g)" -v "$PWD/engine:/work/engine" \
  -v "$PWD/../hmm_scoring/19.0:/library:ro" -v "$PWD/../hmm_scoring/sample:/out" panther-engine:amd64 \
  panther-engine hmmscore sample build /library/PANTHER19.0_hmmscoring.tgz \
  --families /out/families.txt --tag hmmscore-sample-1 --out /out/hmmscore-sample-1.tar.gz
```

- **The tarball:** `hmm_scoring/sample/hmmscore-sample-1.tar.gz`, 33,247,636 bytes, sha256 `b75302f64a476a868b67e857e707b094a0f8abfa090a27b8830a42c8f58c4e43`. A second build, into `hmm_scoring/sample/second/`, gave the same bytes, and the same `sample.json`.
- **Unpacked:** 134,680,343 bytes in 460 files: 454 model files (64,380,364 bytes), `names.tab` (455 lines), the README, and the four pressed files (70,270,278 bytes) of 456 models.
- **Checked:** each model file's sha256 is its line in `books.sha256`, rebuilt from the tarball with the engine's `hash_library` and `books_list`: 13,866,910 bytes, whose sha256 is the pin's, so it's task 6.4's file. The README's sha256 is the pin's. `uv build --wheel` includes `sample.json`.
- **Fetched** into `.data/` with `sample fetch --from` that tarball, in 2 s; a second fetch did nothing. Tasks 8.5's and 8.6's tests pass against it, natively and in the image on both architectures, with data and tools required.
- **Published** on 2026-11-10 (task 8.7): `https://github.com/pantherdb/panther-scoring-services/releases/tag/hmmscore-sample-1`, a pre-release on `main`, its asset at the manifest's 33,247,636 bytes. The command was 8.7's, run from `hmm_scoring/sample/` with `--repo pantherdb/panther-scoring-services`, as that folder is outside the repository. The repository still has no Latest release (`/releases/latest` is 404, as before).
- **Fetched from the release** into an empty scratch folder, rather than an empty `.data/`, which holds the other data sets: downloaded and checked in 3.6 s; a second fetch did nothing, and `sample verify` found every file. `.data/` already matched it.

### HMMER 3.1b2 on the sample (task 10.1)

On 2026-11-10, Bioconda's `quay.io/biocontainers/hmmer:3.1b2--3`, pinned by digest `sha256:e7b1a7a131b7acd6546a6a77cfffc3007fc80f74f7b40b5c660fe29fda122158`, ran under Docker's emulated amd64 on this Mac, beside the amd64 engine image.

- **The results:** each pressed its own copy of the sample's `binHmm.h3m`, and their `hmmscan` tables for the example and `test.fasta` are identical, without the `#` lines. So are their `hmmsearch` alignments for each best hit's model file. Their presses differ only in 4,653 bytes of `.h3p`, and 3.4's is the sample's, byte for byte.
- **The shipped `.h3p`:** 3.1b2's press of the first 25,000 models' records gives the shipped `.h3m`, `.h3f` and `.h3i`, but not the shipped `.h3p`. It differs in 5,462,372 bytes, as 3.4's does in 5,185,856. Neither version can give the sample production's `.h3p`.

### The hosting server (task 10.2)

Read there by the engine developer on 2026-11-10, with `nproc; free -g; df -h panther-data/`:

- **CPUs:** 2.
- **Memory:** 7 GiB in all: 1 used, 2 free and 3 in the page cache, so 5 available. Swap is 7 GiB, unused.
- **Disk:** `panther-data/` is on `/home` (`/dev/mapper/rhel-home`): 222 GiB, 33 GiB used, 189 GiB free.

So the disk holds the full library at its peak, and the memory can't run `titin-50000`. The survey doc's "What It Means for port-hmmscore" has the comparison, and Workflow follow-up's `port-hmmscore` bullet the decision it needs.

### The runs on Endeavour

Two Slurm jobs, 6921723 (`full-library.sbatch`) and 6921729 (`measure.sbatch`), from 05:08 to 16:41 UTC on 2026-11-10. Both ran on the node `b11-19.hpc.usc.edu`: AMD EPYC 7513, 64 CPUs, 503 GB of memory. The folder was on `/scratch2`, a shared BeeGFS file system. Their logs and outputs are in `hmm_scoring/carc-results/`.

| Step | Task | Wall time | CPU time | Peak memory | Result |
| ---- | ---- | --------- | -------- | ----------- | ------ |
| `curl -C -` of the tarball | 1.1 | 226 s | | | The pinned sha256 |
| `data fetch --tarball` | 6.4 | 875 s | 304 s | 330 MiB | 67,076,724,129 bytes in `hmmscore/19/` |
| `data verify` | 6.4 | 5,778 s | 111 s | 98 MiB | 0 missing and 0 differing, of 143,700 listed files |
| `sha256sum --check books.sha256` | 6.4 | | | | All 143,693 lines OK |
| `data fetch`, the folder already there | 6.4 | 5,933 s | 113 s | 98 MiB | "nothing to fetch" |
| `data fetch` from the URL, into an empty folder | 6.5 | 1,134 s | 352 s | 331 MiB | The same files at the same sizes as 6.4's |
| `data verify` of that folder | 6.5 | 5,916 s | 114 s | 98 MiB | Every file matches the pin |
| `hmmconvert` of `binHmm.h3m`, compared with the model files | 7.1 | 9,186 s | 693 s | 236 MiB | `hmmconvert-check.txt` and `.tsv` |
| `hmmconvert` of `binHmm.h3m` | 7.2 | 449 s | 420 s | 16 MiB | |
| `hmmpress` of that text | 7.2 | 395 s | 340 s | 38 MiB | `.h3f`, `.h3m` and `.h3p` differ from the shipped files; `.h3i` is the same |

- **The bytes:** the 67,076,724,129 bytes are the 67,062,857,219 kept from the tarball, and `books.sha256`'s 13,866,910. No `cluster.pir` or `tree.tree` was written.
- **Reading the folder is slow on BeeGFS:** each check of it took about 96 minutes, with under 2 minutes of CPU. The fetches, which write as they stream, took 15 and 19 minutes.
- **The `hmmscan` runs (task 7.3),** with the cache cold and warm, at `--cpu` 0, 2 and 4, then two and three at once. They're in the survey doc. Each query's tables were the same at every setting.
- **HMMER 3.1b2 (task 10.1's full-library step):** built from source in the job, sha256 `dd16edf4…` for `hmmer-3.1b2.tar.gz`. Its `hmmscan` tables for the example and `test.fasta`, on the shipped pressed files, are 3.4's, apart from the `#` lines.

### CI, checked locally (tasks 9.1 and 9.2)

- **actionlint** passed on both jobs' steps. The session's permission check refused `uvx --from actionlint-py actionlint`, as it downloads and runs a package, so the engine developer ran it by hand on 2026-11-09, with no output. `ci.yml` hasn't changed since.
- **Task 9.2's steps** ran on 2026-11-10, after the sample was published, in an image built with `docker buildx build --target engine --load -t panther-engine:ci .` on arm64. All passed:
  - the hmmscore fetch into an empty folder downloaded and checked the sample, as on a cache miss;
  - the fetch into `.data/` did nothing, as on a hit;
  - the test step passed 1,307 tests, with none skipped.

### Blockers

None. Tasks 5.3 and 11.1 wait for the engine developer's commit (Next action).

### Failed approaches

- **Pressing `hmmconvert`'s text for the sample (task 8.1, replaced on 2026-11-10).** It changed some of the library's probabilities by one unit in the last place, so the sample's models weren't production's (Decisions during apply).

### Lessons learned

- **`hmmpress` refuses a repeated model name.** HMMER 3.4 exits 1 and writes no pressed files: Easel's SSI writer stops at "primary keys not unique" (`easel/esl_ssi.c`), though the message comes out garbled. So a pressed `binHmm` can't hold a family's model and its byte-for-byte copy under one name.
- **Byte order of the pressed files.** `.h3f`, `.h3m` and `.h3p` start with a magic number in the machine's byte order, little-endian on amd64 and arm64 (`fwrite` of a `uint32_t`). The `.h3i` index is big-endian, as Easel writes SSI files.
- **`git grep` skips untracked files.** Task 2.1's check needs `git grep --untracked` until the new module is added.
- **basedpyright flags `@contextmanager` on a function typed `-> Iterator[…]`** as deprecated. Type it `-> Generator[…]`, as `api/tests/serving.py` does.
- **HMMER 3.4 can't round-trip a binary model through text.** It reads text probabilities with `expf` on a single-precision argument, while the shipped `.h3m` holds other floats, one unit in the last place away for about 1 in 1,000. Press binary records to keep them. This Mac's 3.1b2, an arm64 build, doesn't reproduce them from text either.
- **`hmmscan`'s numbers depend on the architecture.** The same pressed files give a few last-digit differences on arm64 and amd64, and a domain near a cutoff can move its envelope. Production's numbers are amd64's.
- **Docker's emulated amd64 on Apple Silicon gives real amd64's numbers.** Its `hmmscan` matched Endeavour's on all 417 domains they shared. Its `hmmpress` of the text also differed from the shipped files at the same first bytes as Endeavour's. So amd64 tables can be made on this Mac with `--platform linux/amd64`.
- **Compare `hmmscan` tables of different databases on bit scores, not E-values.** E-values scale with the number of models searched, and so does which weak domains are reported. Match each of the larger database's domains, by its score, bias and coordinates, among the smaller one's.
