# Tasks

## 1. Prerequisites and Shared Docs

- [x] 1.1 Check the local inputs against legacy behaviour spec §7.1 with `shasum -a 256`: `PAML_RST.tar.gz` (`6791f433…`), the PSEP 1.01 release's `PANTHER9.blast.tar.gz` (`2cf4428c…`) and `cSNP_analysis/species_pthr8_time.nhx` (`23b035c2…`). Verify all three match, and record where each one is on this machine in the Notes
- [x] 1.2 Record the new service priority, decided 2026-10-29: `csnp` 1, `refmap` 2, `hmmscore` 3, `treegrafter` 4.
  - In `CLAUDE.md`'s Project table and `docs/design/tech-stack.md`'s Scope table, put the rows in that order, with the new numbers. Say in each that it was revised on 2026-10-29.
  - Change the first line of the context in `openspec/config.yaml` to the same order.
  - Add the revision to `tech-stack.md`'s Status line.

  Verify that `grep -rn -i priorit CLAUDE.md frontend/CLAUDE.md docs/ openspec/config.yaml` shows no other order, and that `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass
- [x] 1.3 Record where `PAML_RST.tar.gz` came from: it was tarballed from the production server before that was shut down, so it is production's library build (engine developer, 2026-10-29). This answers legacy behaviour spec §8, question 4. The spec is in `panther-workspace`, which is read-only, so record the answer here.
  - In `CLAUDE.md`'s `csnp` section, replace the **Production** bullet, which says the library build can't be checked.
  - In `tech-stack.md`, narrow the `csnp` open question "Production CGI and library build" to the CGI copy, which is still unknown. Add the origin to the Data bullet about the developer copy of the PAML library, and the revision to the Status line.

  Verify that `grep -n -E 'library build|unrecorded' CLAUDE.md docs/design/tech-stack.md` finds nothing still saying the build is unknown, and that `npx markdownlint-cli2` passes
- [x] 1.4 Record the rule for legacy code and docs that disagree, decided by the engine developer on 2026-10-29. The rule: follow the code, so M1 reproduces what ran in production, and log the docs' version to revisit after the service is live on production.
  - **The rule itself:** add it beside the "needs team verification" rule in `CLAUDE.md`, in `CONTRIBUTING.md`'s Review Rules, and in the context in `openspec/config.yaml`.
  - **cSNP's thresholds and pDel bounds** (`SCORE-5`, `SCORE-6`): the port keeps 180 / 380 Mya and `age < bound`.
    - In `tech-stack.md`, rewrite Engine condition 7 and the `csnp` open question "Thresholds and pDel" to say so, and mark `SCORE-6` as kept for M1 in condition 6. Name `thomaspd` as the science owner in the Review table, and add the revision to the Status line.
    - In `CLAUDE.md`'s thresholds gotcha, replace "Which is correct needs team verification before porting".
    - In `openspec/config.yaml`, replace "including the csnp 180/380 vs 200/450 Mya thresholds".
  - **`docs/parity/divergences.md`:**
    - add proposed row 7 for the thresholds (`SCORE-5`): 180 / 380 Mya in the code; 200 / 450 Mya in the help page and thomaspd's 2021 ticket;
    - mark rows 4 and 7 as deferred until cSNP is live on production;
    - take the thresholds out of the "Still open" note.

  Verify that `grep -n -E 'before porting|unresolved' CLAUDE.md docs/design/tech-stack.md openspec/config.yaml` finds nothing left about the thresholds, and that `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass

## 2. Data Folder and Checksum Manifests

- [x] 2.1 Add `core/data.py`: the data folder from an explicit path or `PANTHER_DATA_DIR`, and a service's folder under it (`csnp/9/`), with an error that names the variable when neither is given. Verify `tests/test_data.py` covers both "Data folder" scenarios
- [x] 2.2 Add `core/manifest.py`: read a manifest of relative paths and sha256 checksums, hash files in chunks, and verify a folder against it, returning the missing files and the differing ones. Verify `tests/test_manifest.py` covers the three "Data checked against a checksum manifest" scenarios, and that a manifest path that is absolute or contains `..` is rejected

## 3. Library Readers

- [x] 3.1 Add the hand-written fixture family under `engine/tests/fixtures/csnp/`, consistent with spec §3.5: three leaves, a root and one internal node, with a `.paml` of two sites, a `.rst` with its branch list and tree on the 12th and 15th lines and a sequence section, and an `.orig.tree` with its NHX line and gene lines. Add one broken copy for each error the readers must catch: no root, a bad probability, CRLF, an empty `.rst`, the branch list off its line, and a node without `Ev`. Add a species tree with one `NXH` node. In `.gitattributes`, replace the placeholder comment with `engine/tests/fixtures/csnp/** -text` and `engine/tests/golden/** -text`. Verify `git ls-files --eol engine/tests/fixtures/csnp/` shows the CRLF copy stored as `i/crlf` after `git add`
- [x] 3.2 Add `LibraryFormatError` and `csnp/paml.py`. It reads the header (node numbers, AN labels, parents, root) and one site's residues and probabilities, line by line, without holding the file. The site-row patterns are module-level compiled patterns, for the survey to reuse. Verify `tests/test_csnp_paml.py` covers the three `.paml` scenarios, and the "Bad probability" and "CRLF line endings" scenarios
- [x] 3.3 Add `csnp/rst.py`. It reads the 12th line as (parent, child) pairs, the 15th line's node numbers in order, and the sequences between `List of extant and reconstructed sequences` and `Overall`. Verify `tests/test_csnp_rst.py` covers the four `.rst` scenarios
- [x] 3.4 Add `csnp/orig_tree.py` and `csnp/species.py`. Verify `tests/test_csnp_orig_tree.py` and `tests/test_csnp_species.py` cover the `.orig.tree` and species-tree scenarios, including "Node without an event" and "Misspelt tag"
- [x] 3.5 In `CONTRIBUTING.md`'s Spec Layout, add `csnp-data` ("The cSNP data: reading the PAML_RST library and the species tree, the library survey, and the data sample"), and limit `psep-engine`'s row to scoring. Verify `npx markdownlint-cli2` passes from the repo root

## 4. Library Survey

- [x] 4.1 Add `csnp/legacy.py`: the Perl's readings in design.md's table. Each has a comment citing its line in `PANTHER_PSEP1.01.pl` at `cebb5ab` and its quirk ID. Verify `tests/test_csnp_legacy.py` shows each reading agreeing with the strict reader on the clean fixture family. It must also show each one differing on a fixture made to trigger it: a colliding label, a stray `Node<k>` in a parent cell, a malformed branch token, an `Ev` the pattern misses, a gene identifier that is a prefix of another, and a trailing `\r`
- [x] 4.2 Add `csnp/survey.py`, as design.md's decision 2 describes:
  - one streaming pass over a gzipped tar, with the sha256 of the compressed bytes from the same pass;
  - the checks in the spec's survey requirements;
  - a report giving each check's count and up to five examples, smallest family first;
  - members matched by file name, so the sample tarball can be surveyed too.

  Verify `tests/test_csnp_survey.py`. It builds archives in `tmp_path` from the fixtures: the clean family, a family missing its `.rst`, a split part with no base, the broken copies, and every family's files in shuffled order. It must cover the scenarios of "Survey of files and parsing", "Survey of agreement between a family's files", "Survey of the legacy readings" and "Survey of events and taxa"
- [x] 4.3 Add the survey's optional BLAST input. It reads the headers of `blast/blast.fasta` from `PANTHER9.blast.tar.gz` as a stream, and runs the checks in "Survey of the BLAST database against the library". Verify both of its scenarios with a small BLAST archive built in `tmp_path`
- [x] 4.4 Add `csnp/cli.py` with `panther-engine csnp survey ARCHIVE [--species FILE] [--blast-archive FILE] [--json FILE]`, and register it in `cli.py`. Verify `tests/test_csnp_cli.py` covers these scenarios:
  - "Survey an archive";
  - "Nothing written": nothing but the JSON report appears in the working folder or `tmp_path`;
  - "Unreadable archive": a truncated gzip, and a plain text file.

  Also verify that `uv run panther-engine csnp survey --help` lists the options

## 5. Sample Tooling

- [x] 5.1 Add `build` to `csnp/sample.py` (design.md's decision 5) and `panther-engine csnp sample build`. The archive's expected sha256 defaults to the pin in §7.1 and can be overridden, so the tests don't need the real archive. Verify `tests/test_csnp_sample.py`:
  - two builds from a fixture archive are byte-identical;
  - an archive with the wrong sha256 exits non-zero naming both checksums, and leaves no tarball;
  - the tarball's members are sorted, owned by 0 and dated 0
- [x] 5.2 Add `fetch` and `verify` (design.md's decision 6) and their subcommands. `--from FILE` takes a local tarball. `--data-dir` defaults to `PANTHER_DATA_DIR`. Verify with `--from` and a test manifest that the tests cover the five "Fetching the sample" scenarios, "Changed file", and the refusal of an `http://` URL. A failed fetch must leave the data folder as it was. The download itself is checked by CI's fetch (8.2)
- [x] 5.3 Add the `data` marker to `tests/conftest.py` (design.md's decision 8). `PANTHER_DATA_DIR` falls back to the repository's `.data/`. Add `.data/.gitkeep`, with `/.data/*` and `!/.data/.gitkeep` in `.gitignore`. Verify:
  - `tests/test_data_marker.py`, with pytester as `test_tools_marker.py` does, covers the "Without the data" and "Data required but missing" scenarios;
  - `git status --ignored` shows a file put in `.data/` as ignored, and `.gitkeep` as tracked
- [x] 5.4 Write the Test Data section of `docs/testing/engine.md`:
  - fetching the sample, natively and through compose (`--user "$(id -u):$(id -g)"`, mounted writable at another path);
  - the `data` marker, `PANTHER_DATA_DIR` and `PANTHER_REQUIRE_DATA`;
  - using the full library instead;
  - publishing a new sample: build, `gh release create … --latest=false`, commit the manifest.

  Verify `npx markdownlint-cli2` passes. Tasks 7.3 and 8.1 run the commands as written

## 6. Survey of the Pinned Library

- [x] 6.1 From `engine/`, run `uv run panther-engine csnp survey <PAML_RST.tar.gz> --species <species tree> --blast-archive <PANTHER9.blast.tar.gz> --json <scratch>/survey.json`. Verify it reads both archives to the end, and reports the PAML archive's sha256 as in §7.1. Record the run time and peak memory in the Notes (`/usr/bin/time -l` on macOS, `-v` on Linux)
- [x] 6.2 Compare the results with the figures in the legacy behaviour spec and the parity review:

  | Check | Expected |
  | ----- | -------- |
  | Families | 8,607 |
  | Split parts with no base family (`DATA-1`) | 1,887 parts, covering 410 families |
  | Known broken files (`DATA-1`) | 4 |
  | Start column (`SCORE-2`) | 117,389 of 676,233 leaves, in 6,897 of 8,605 families |
  | Speciation nodes aged as duplications (`DATA-3`) | 40,506; plus 1,977 `Ev=0>0` nodes and 319 without `Ev` |
  | BLAST entries (`DATA-2`) | 474,535 found; 95,638 with no `.paml` |

  Verify that every figure matches, or that each difference is traced to its cause and explained. A bug in a reader or in `legacy.py` is fixed with a failing test first, and the survey is run again
- [x] 6.3 Choose the sample: the four named families; for each non-zero check, the smallest family that shows it; and the family with the largest `.paml`, for size. Write `docs/parity/csnp-library-survey.md`, and add it to the What Goes Here table in `docs/parity/README.md`. The doc gives:
  - the date and the engine commit;
  - the inputs, where each came from (the PAML archive from the production server, the BLAST archive and the species tree from the PSEP 1.01 release), their checksums, and the command;
  - each check's result, beside the review's figure;
  - the chosen families, with the check each one stands for;
  - what it means for the port: which legacy readings differ, and so must be matched or logged as divergences.

  Verify that `npx markdownlint-cli2` passes, and that every non-zero check in the report has a family in the table

## 7. The Sample

- [x] 7.1 Run `uv run panther-engine csnp sample build` with the chosen families, the species tree and the PSEP copyright statement. It writes `csnp-sample-1.tar.gz`, and the manifest to `engine/src/panther_engine/csnp/sample.json`. Verify:
  - a second build is byte-identical;
  - the `PTHR10366` and `PTHR15126` checksums start with the digits in §7.1, and the species tree's matches;
  - `uv build --wheel` includes `sample.json`.

  Record the tarball's size, compressed and unpacked, in the Notes
- [x] 7.2 Add `tests/test_csnp_sample_data.py`, marked `data("csnp")`. It checks that:
  - the sample matches the manifest;
  - every sample family reads with the strict readers, and the four known broken files raise the expected errors;
  - in `PTHR10366`, AN 911's (Q9H2F3, `del28`) leaf column is 1238 and the legacy start column is 1380 (`SCORE-2`, spec §6);
  - surveying the sample, tarred up in `tmp_path`, finds every check that was non-zero for the full library ("Every variant").

  Verify it passes, with none skipped, against the sample unpacked by `fetch --from` the local tarball
- [x] 7.3 Publish with `gh release create csnp-sample-1 csnp-sample-1.tar.gz --latest=false`, with notes linking the survey doc. Then fetch into an empty `.data/` with `uv run panther-engine csnp sample fetch --data-dir ../.data` from `engine/`. Verify:
  - the fetch downloads and verifies;
  - a second fetch downloads nothing;
  - `gh release view csnp-sample-1` shows the asset, with the manifest's size;
  - the repository's latest release is unchanged
- [x] 7.4 In `docs/design/tech-stack.md`'s Data bullet ("How the sample is stored … is the engine developer's decision"), record the decision: a public release asset, decided and approved for publishing by the engine developer on 2026-10-29, unpacked under `PANTHER_DATA_DIR` at `csnp/9/`, with a link to `docs/testing/engine.md`. Verify `npx markdownlint-cli2` passes

## 8. Compose and CI

- [x] 8.1 In `compose.yaml`'s `engine` service, mount `./.data` read-only at `/data` and set `PANTHER_DATA_DIR=/data`. Leave the `api` service as it is: it needs the mount only once it runs cSNP jobs. Verify the "Sample fetched" scenario:
  - with the sample in `.data/`, `docker compose run --rm engine` passes with no data test skipped;
  - `git status --ignored .data` shows nothing new;
  - with `.data/csnp` moved aside, the data tests skip, naming `PANTHER_DATA_DIR`;
  - the compose fetch command in `engine.md` works as written
- [x] 8.2 In the `engine` job of `.github/workflows/ci.yml`:
  - restore `.data/csnp` with `actions/cache`, pinned to a commit SHA with its version in a comment, keyed on the manifest's hash (design.md's decision 9);
  - run `uv run panther-engine csnp sample fetch --data-dir ../.data`;
  - run `pytest` with `PANTHER_REQUIRE_DATA=1`.

  Verify that actionlint (`uvx --from actionlint-py actionlint`) reports no errors, and that the job's steps pass, in order, from a copy of only the files git would commit
- [x] 8.3 In the `engine-image` job:
  - restore the same cache;
  - fetch inside the built image, with `.data` mounted writable and `--user "$(id -u):$(id -g)"`;
  - run the tests with `.data` mounted read-only at `/data`, `PANTHER_DATA_DIR=/data` and `PANTHER_REQUIRE_DATA=1`.

  Verify that actionlint reports no errors, and that the steps pass locally with `docker buildx build --target engine --load` and `docker run`
- [x] 8.4 In `docs/testing/README.md`, add the sample fetch and `PANTHER_REQUIRE_DATA` to the `engine` and `engine-image` rows of What CI Runs, and the `data` marker to the Engine row of Kinds of Test. Verify that the commands named match `ci.yml`, and that `npx markdownlint-cli2` passes

## 9. Final Check

- [x] 9.1 From a clean clone of the branch, run the checks:
  - after `uv run panther-engine csnp sample fetch --data-dir ../.data` in `engine/`: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run basedpyright && PANTHER_REQUIRE_DATA=1 uv run pytest` passes, with only the `tools` tests skipped;
  - from the root, `docker compose run --rm engine` passes with nothing skipped;
  - from `api/`, which imports the engine: `uv sync --locked && uv run pytest` passes, and `uv lock --check` reports no change;
  - `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass

## Workflow follow-up

- The proposal and its implementation are reviewed together, in one pull request from `feat/add-csnp-survey-and-sample`. That was the engine developer's choice on 2026-10-29, instead of approving the proposal before any code is written.
  - All three developers approve it, because it changes `CLAUDE.md`, `tech-stack.md` and `openspec/config.yaml`.
  - The API developer also reviews the changes to `compose.yaml` and `ci.yml`, which the API's service shares.
- The pull request is over the 400-line norm. Its description says why (proposal, Impact, Size), and walks through the work in task order.
- When that pull request is opened, confirm on it that:
  - the `api` and `api-image` jobs, which an engine change also runs, pass;
  - the `engine` job and both `engine-image` legs fetch the sample, with a cache miss on the first run and a hit on a re-run;
  - no data test is skipped in any of them (check the logs, not just the result).
- After the implementation merges, archive with `/opsx:archive`. That creates `openspec/specs/csnp-data/spec.md` and adds the new requirements to `engine-core`.
- Next change for cSNP: the parity harness. That means the Perl reference image (Engine condition 3) and the spec §7 goldens in `engine/tests/golden/csnp/`, run against the sample. Step 3 keeps the code's thresholds and pDel bounds (`SCORE-5`, `SCORE-6`; task 1.4).
- Before step 3 is ported, agree the engine's cSNP interface with the API developer, in a change of its own. That covers the `score` function and its input and result types, the data version and the list of species codes. The API developer's questions of 2026-10-29 are the starting point. `InputError` is already settled by `add-job-input-errors`, and its task group 1 lands with the `csnp` port. None of `csnp`'s legacy conditions raises it.
- After cSNP is live on production, open an issue for the science owner, thomaspd, on divergence rows 4 and 7: the pDel bounds and the thresholds. Ask which values are correct, and whether pDel should include its bounds.

## Notes

### Next action

None: the change is merged (#21, `234d650`) and archived (2026-10-29).

- The **Run** line of `docs/parity/csnp-library-survey.md` names the merge commit.
- #21's CI confirmed the Workflow follow-up (run 40997521102, its only attempt):
  - the `api` and `api-image` jobs passed;
  - the `engine` job missed the cache, fetched and checked the sample, and saved the cache. Its 220 tests passed, with only the `tools` test skipped, as expected natively;
  - both `engine-image` legs hit that cache, and passed 221 tests with none skipped.

  The cache hit came from the same run, not from a re-run, which wasn't needed.
- Next for cSNP: `port-csnp`, not yet proposed. It ports the three steps behind `score()`, the interface agreed on #19, with the parity harness and the Perl reference image.

### Decisions during apply

- **Two variants in `PTHR10366` are part of the strict `.paml` shape** (engine developer, 2026-10-29). The golden family has 2,941 unreconstructed cells (a NUL residue with a `-nan` probability, always as a pair) and 812 internal columns labelled `Node<k>` with no AN. They read as no residue and NaN, and as AN None. Either half of the pair alone, or a leaf column without an AN, is still a format error. The spec delta and design.md record them, and the survey counts both.
- **One unmatched `)` before the `;` is part of the strict `.orig.tree` shape** (engine developer, 2026-10-29). 135 split parts, `PTHR23125_2` among them, end their tree line that way; each parses strictly without it, and the Perl's patterns never see it. The BLAST database has 801 entries in those families. The survey counts them under `extra-parenthesis`.
- **`.rst` sequence lists have no `Overall` line** in the library's files; the list runs to the end of the file, as the Perl's flip-flop does. The spec delta says so.
- **The BLAST database has two header shapes:** `GENE:PTHR…:SF…`, and `GENE:AN<n>:PTHR…`. Step 2 takes the second field as the family, so for the second shape it looks for a family `AN<n>`, finds no `.paml`, and never scores the entry. The survey reads them the same way, and counts them under `blast-not-a-family`.
- **Split names nest:** `PTHR10024_1_1`. The family pattern allows any number of `_N` parts, and a split part's base is the `PTHRnnnnn` before the first.
- **`csnp-sample-1` is a pre-release** (engine developer, 2026-10-29). Created with `--latest=false` as task 7.3 says, GitHub still made it Latest, being the repository's only release. `gh release edit csnp-sample-1 --prerelease` undid that: `/releases/latest` is 404 again, as before. `docs/testing/engine.md` now publishes with `--prerelease`.
- **Ruff doesn't report `S202`** for `extractall(…, filter="data")`, so `unpack` has no `noqa` for it, unlike design.md's decision 6 expected. `S310` has its `noqa`.

### Inputs on this machine

Checked with `shasum -a 256` on 2026-10-29 (task 1.1). All three match legacy behaviour spec §7.1. Paths are relative to the parent folder of this repo:

| Input | Path | sha256 |
| ----- | ---- | ------ |
| `PAML_RST.tar.gz` | `panther_build/PAML_RST.tar.gz` | `6791f43325afdae3a1872c7655d103f9cdd98d5dbf6695a1187bb30985a869c5` |
| `PANTHER9.blast.tar.gz` | `PANTHER_PSEP1.01/PANTHER9.blast.tar.gz` (the PSEP 1.01 release) | `2cf4428c97b99c4bce3705a80dc7f55c17779e54a0bcae9ddb7d75a67b40dcc9` |
| `species_pthr8_time.nhx` | `panther-workspace/legacy/cSNP_analysis/species_pthr8_time.nhx`; the release's `PANTHER_PSEP1.01/scripts/` copy is identical | `23b035c293337966bd766628dd721c0a264230a49e4763188c607e301623d1e9` |

The copyright statement is at the top of `PANTHER_PSEP1.01/README.txt`.

### Survey run

`uv run panther-engine csnp survey` on `PAML_RST.tar.gz`, with the species tree and the BLAST archive, on 2026-10-29 (task 6.1), on an Apple Silicon Mac:

- **Run time:** 395 s (`/usr/bin/time -l`: 394.61 real, 360.84 user, 26.58 sys).
- **Peak memory:** 277 MB maximum resident set size. The BLAST headers, held by family until each family's `.orig.tree` arrives, are most of it.
- **Read to the end:** 25,821 members, 2,350,213,383 bytes of archive, sha256 `6791f433…` as in spec §7.1. All 570,174 BLAST headers.

The results, and how each differs from the review's figure, are in `docs/parity/csnp-library-survey.md`.

### The sample

`csnp-sample-1.tar.gz`, built on 2026-10-29 (task 7.1) from the 15 families in `docs/parity/csnp-library-survey.md`:

- **Compressed:** 26,000,104 bytes, sha256 `6b8fb633a9dafe255345aa58ca3e2e5ecaa2231de38c11a8aa043179b98c10d0`.
- **Unpacked:** 259,519,715 bytes in 47 files: 45 library files, the species tree and the copyright statement. `PTHR11695.paml` is 136 MB of it.
- **The build** reads the whole archive once, in about 85 s. Two builds gave the same bytes.

### Blockers

None yet.

### Failed approaches

- **The first full survey ran at about 80 MB of archive a minute (2026-10-29), so about 30 minutes in all.** `open_stream` passed `bufsize=1 MiB` to `tarfile.open`. In stream mode, each small read of a member then slices tarfile's decompressed buffer, about 8 MB, so line-by-line reading copied it over and over: 11.3 s against 0.34 s for the same 105 MB. Fixed by keeping tarfile's default buffer and reading members in 1 MiB chunks, split into lines by hand (`member_lines`). Don't raise `bufsize` again.
- **The first `.rst` sequence pattern rejected 844 files (2026-10-29).** It allowed no space after the last block. PAML writes a space after every full block of 10, so a sequence whose length is a multiple of 10 ends with one. Found by the full survey, traced with a one-off scan of every sequence line, and fixed test-first; the pattern now matches PAML's layout exactly.
- **The first survey report kept only five rejected files per check.** The spec asks for every rejected file with its error, so the report now lists them all (`rejected`).
- **`io.TextIOWrapper` over a stream-mode tar member fails:** it calls `seekable()`, which tarfile's `_Stream` lacks. Lines are decoded one by one instead.

### Lessons learned

- **Run the strict readers on the whole library before trusting a format description.** Spec §3.5 missed three variants and the `.rst` line layout. The survey's rejections, plus a short one-off scan to group them by cause, found each in minutes. Keep the survey able to list every rejection, not just examples.
- **Don't pass a large `bufsize` to `tarfile.open` in stream mode.** Read members in large chunks instead. This applies to any streaming tar reader in the engine.
- **`gh release create --latest=false` doesn't stop the repository's only release from becoming Latest.** Publish data assets with `--prerelease`.
- **Check figures against an independent count.** Every difference from the review traced to a definition, such as families whose `.paml` reads against families with a root, or to a reader bug. None was left unexplained.
