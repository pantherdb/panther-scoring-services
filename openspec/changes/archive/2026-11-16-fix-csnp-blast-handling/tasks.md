# Tasks

## 1. No Usage Reports (ENG-1)

- [x] 1.1 In `core/process.py`, make `run_tool` pass the caller's environment with `BLAST_USAGE_REPORT=false` set over it (design.md, decision 1). Add tests to `tests/test_process.py`, with the `make_tool` fixture and a tool that prints its environment. With the caller's `BLAST_USAGE_REPORT=true`, the tool sees `false`, and another variable reaches it unchanged (spec, A caller asks for reports). Verify that both tests fail before the change and pass after, and that `uv run pytest tests/test_process.py` passes natively
- [x] 1.2 Add `BLAST_USAGE_REPORT=false` to the `Dockerfile`'s `tools` stage `ENV`, and say in `docs/testing/engine.md` that BLAST+'s usage reports are off and where. Verify:
  - `docker compose run --rm --build engine printenv BLAST_USAGE_REPORT` and the same for `api` both print `false` (spec, In the images);
  - `panther-engine tools` in the engine image, with `--add-host www.ncbi.nlm.nih.gov:10.255.255.1`, finishes in under 2 s, where it took about 11 s before the change (spec, NCBI unreachable). Record both times in the Notes;
  - `npx markdownlint-cli2` passes.

## 2. BLAST+ 2.17.0's Identity Formula (CSNP-1)

- [x] 2.1 In the engine image, align the eight tie pairs of the spec's "Ties from BLAST+ itself" with `blastp -subject` and the legacy `-outfmt`: ungapped, with the mismatches spread inside the sequence (design.md, decision 3). Verify that each line has the intended length and identity count, and that its written identity is `n / L × 100`, not `100 × n / L`, to three decimals. Commit the 201/320 line as `tests/fixtures/csnp/identity-tie.csv`, and record the eight written identities in the Notes
- [x] 2.2 Write the tests first (design.md, decision 3):
  - in `tests/test_csnp_hits.py`, the fixture line is read with no error and ranked at `62.81` (spec, A tie at three decimals);
  - a `tools("blastp")` test that builds the eight pairs from a fixed seed, aligns them, and reads every line through step 2 (spec, Ties from BLAST+ itself).

  Verify that both fail against today's formula, with `BlastError`. The existing `test_an_identity_that_disagrees_with_the_counts_is_an_error` stays as it is (spec, A line that contradicts itself)
- [x] 2.3 Change the formula to `(length - mismatch - gaps) / length * 100` in `hits.two_decimals` and `parity.blast_line`, with their docstrings and the error message (design.md, decision 2). Verify that:
  - 2.2's tests and the rest of `tests/test_csnp_hits.py` pass natively, and the `tools` test passes in the engine image;
  - `parity cases` rewrites the generated cases byte for byte: `git status` shows nothing under `tests/golden/`;
  - `parity check` reports no difference;
  - the golden tests pass with `PANTHER_REQUIRE_DATA=1`.
- [x] 2.4 Search the docs and the code comments for the old formula (`100 *`, `100 ×`) and for the claim that it was checked on every line, and correct each outside `openspec/changes/archive/`. Verify that the search finds none, and that `npx markdownlint-cli2` passes

## 3. Missing cSNP Data (CSNP-3, the Check)

- [x] 3.1 Add `MissingDataError` to `core/data.py`, and the data check to `panther_engine.csnp`, exported (design.md, decision 4). Call it in `score()` after the input checks and the early return for no substitutions, and before `blast.search`. Update `score()`'s docstring. Verify, natively, with tests in `tests/test_csnp_scoring.py` that make `blast.search` fail if it's called:
  - a folder with only `csnp/9/blast/` names `PAML_RST` and `species_pthr8_time.nhx`, and nothing is searched (spec, Only the BLAST database);
  - an empty `PAML_RST/` is named (spec, An empty library folder);
  - an empty folder names all three (spec, No data at all);
  - the error isn't an `InputError`, and comes back from a worker process with its type and message.

  Update `test_a_data_folder_without_the_database_is_a_failure_not_an_input_error` to expect `MissingDataError`, and check that `test_no_substitutions_give_no_family_and_nothing_is_searched` passes unchanged
- [x] 3.2 Add a `data` test showing that a folder that passes the check still gives "Not scored: No PANTHER family for input sequence" for a family without a `.paml`: step 3 on a record whose family isn't in the sample (spec, A family the library doesn't have). Verify that it passes natively with the sample, and that every existing test in `tests/test_csnp_scoring.py` and `tests/test_csnp_psep.py` passes with `PANTHER_REQUIRE_DATA=1`

## 4. BLAST+ Time Limit (CSNP-4)

- [x] 4.1 In the engine image, with group 1 done, time `panther-engine csnp score` three times each on titin (Q8WZ42 from UniProt, 34,350 residues) and on a 50,000-residue query: titin, then its first 15,650 residues. Record the machine, the image's architecture and each time in the Notes. Then set the per-residue rate so each query's limit is at least 2.5 times its slowest time, with a base of 60 s (design.md, decision 5)
- [x] 4.2 In `csnp/blast.py`, replace `TIMEOUT` with a limit of `(base + rate × residues) × scale`, the scale read from `PANTHER_CSNP_BLAST_TIME_SCALE` on each call. `search()` uses it unless the `timeout` keyword is given. Verify with unit tests, natively:
  - titin's limit is at least 2.5 times its slowest time in 4.1 (spec, Titin);
  - 400 residues get at least 60 s and under 2 minutes (spec, An ordinary protein);
  - a scale of `2` doubles the limit (spec, A slower machine);
  - `0`, `-1`, `fast`, `inf` and `nan` each fail before `blastp` runs, naming the variable (spec, An invalid scale);
  - the existing `test_a_search_past_its_time_limit_is_a_blast_error` still passes (spec, Past the limit).
- [x] 4.3 Document the limit, its measurements and `PANTHER_CSNP_BLAST_TIME_SCALE` in `docs/testing/engine.md`, and the variable in `engine/README.md`. Verify:
  - the Titin test's number is the one engine.md records;
  - `uv run ruff format --check` passes, since it formats the README's Python blocks;
  - `npx markdownlint-cli2` passes.

## 5. Exit Status 1 and Data Folder Paths (CSNP-5, CSNP-6)

- [x] 5.1 In `blast.search`, treat exit status 1 as an input error only when standard error has a `BLAST query error:` line (design.md, decision 9). Write the tests first, in `tests/test_csnp_blast.py` with the `blastp` fixture:
  - status 1 with 2.17.0's usage text and `Error: Unknown argument: "bogus_option"` is a `BlastError` whose message includes that line (spec, An argument BLAST+ rejects);
  - status 1 with nothing on standard error is a `BlastError` (spec, Status 1 with nothing on standard error);
  - `test_exit_status_1_is_an_input_error_without_the_tools_output` passes unchanged (spec, Unreadable query).

  Add a `tools("blastp")` test that runs the real BLAST+ with `OPTIONS` patched to `-best_hit_overhang 0.9`, and gets a `BlastError` naming `best_hit_overhang`. Verify that:
  - the new tests fail before the change;
  - they and every test in the file pass natively after it;
  - `test_a_query_blastp_cant_read_is_an_input_error` passes in the engine image;
  - neither divergence row 8 nor `docs/testing/engine.md` says that every status 1 is the input's fault;
  - `npx markdownlint-cli2` passes.
- [x] 5.2 Run `blastp` with its working folder set to the data folder's `blast/`, and `-db blast` (design.md, decision 10). When there's no `blast/` folder, `search()` raises `BlastError` naming it. Write the tests first:
  - `tools("blastp")` and `data("csnp")` tests that link the sample's `csnp/9` under a folder whose path has a space, and under one whose path has a `"`, and score the form's example. Each gives `PTHR18976` and `apoe.out`'s scores (spec, A space in the path; A double quote in the path);
  - a unit test that a data folder without `blast/` is a `BlastError` naming it.

  The `blastp` fixture's tests need a `blast/` folder in their data folder. `test_blastp_gets_the_legacy_options_and_the_query_on_stdin` now expects `-db blast` and the working folder. Verify that:
  - the path tests fail before the change, with exit status 2;
  - after it, every test in `tests/test_csnp_blast.py` and `tests/test_csnp_scoring.py` passes natively, and in the engine image with `PANTHER_REQUIRE_DATA=1` and `PANTHER_REQUIRE_TOOLS=1`;
  - the step-1 golden test still gives `blast/*.csv` byte for byte.

## 6. The Full Data Manifest (CSNP-3, the Manifest)

- [x] 6.1 Add `csnp/full.py` and `panther-engine csnp data manifest`: stream each archive through sha256 without unpacking, check each input against its pin, and write the manifest in `sample.json`'s format (design.md, decisions 6 to 8). Test it on small built inputs, as `tests/test_csnp_sample.py`'s `inputs` fixture builds them, with the pins passed in. Verify these tests pass natively:
  - two builds are byte for byte the same (spec, Reproducible);
  - the manifest lists the library members, the three BLAST files, the species tree and the copyright statement, and not `blast.fasta` (spec, What it lists);
  - an archive with the wrong sha256 writes nothing, and the error names both checksums (spec, An archive that isn't pinned).
- [x] 6.2 Build `engine/src/panther_engine/csnp/full.json` from `../panther_build/PAML_RST.tar.gz`, `../PANTHER_PSEP1.01/PANTHER9.blast.tar.gz`, the species tree and `../PANTHER_PSEP1.01/README.txt`, twice. Add its `linguist-generated` line to `.gitattributes`. Verify:
  - the two builds are byte for byte the same;
  - `git check-attr linguist-generated` reports it as set;
  - a native test, needing no data, finds every file in `sample.json` in `full.json` with the same sha256 (spec, It agrees with the sample).

  Record the build time, the file count, the size and the sha256 in the Notes
- [x] 6.3 Add `panther-engine csnp data verify`, reusing `core.manifest.verify` against `full.json`. It prints the two counts and the first 20 paths of each, and exits 1 if either count isn't 0. Test it against a small manifest, passed in, natively. Verify that:
  - a deleted file and a truncated file are both named (spec, A copy that stopped halfway);
  - a folder missing 30 files reports 30, and names 20 (spec, Only the sample);
  - an unlisted extra file is ignored (spec, Files it doesn't list);
  - a matching folder exits 0.
- [x] 6.4 Install the full data in a scratch folder, as `docs/testing/engine.md`'s "Using the Full Library" says; it needs 19.9 GB free. Run `csnp data verify` on it, natively and in the engine image. Then delete one `.paml` and truncate one `.rst`, and check that `verify` names both. Restore the two from the archive, and check that it passes again. Also:
  - score P26439 and the form's example against the full data in the engine image, and check that they give spec §7.3's rows and `apoe.out`;
  - add the `verify` step, and how long it takes, to engine.md's "Using the Full Library".

  Verify that the documented commands run as written, and that `npx markdownlint-cli2` passes. Record the times in the Notes, then delete the scratch folder

## 7. Final Check

- [x] 7.1 From a copy of the files git would commit (`git checkout-index` of the staged files), with the sample in `.data/`, verify that everything passes, and record the counts in the Notes:
  - in `engine/`: `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright` and `PANTHER_REQUIRE_DATA=1 uv run pytest`;
  - `docker compose run --rm --build engine`, with `PANTHER_REQUIRE_DATA=1` and `PANTHER_REQUIRE_TOOLS=1`;
  - in `api/`: `uv sync --locked` and `uv run pytest`, including the committed OpenAPI schema test, which shows the contract didn't change. Then the API's tests in the API image, with the tools and the sample;
  - `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive`.

## Workflow follow-up

- Open the pull request against `main`. It's an engine change, but tell the API developer three things:
  - `MissingDataError` fails a job with a 500, and the log says why;
  - a `blastp` exit status 1 that isn't a query error is now a 500, not a 422;
  - `PANTHER_CSNP_BLAST_TIME_SCALE` exists.
- For #34: the deploy runbook runs `panther-engine csnp data verify` before the API takes traffic. It also times titin on the server, and sets the scale if titin takes more than 40% of its limit there.
- Suggested follow-ups, each its own change:
  - CSNP-7 to CSNP-11, apart from CSNP-7's real tie line, which group 2 covers;
  - `harden-engine-tooling` (ENG-2, ENG-3, ENG-16);
  - `harden-images`;
  - an API readiness check that calls the data check.
- Archive with `/opsx:archive`.

## Notes

### Next action

Every task is done (2026-11-02). The pull request from `fix/csnp-blast-handling` is open against `main`. It holds this change, its code, and the review it answers, `docs/code-review/2026-10-30-whole-repo-review-64174c9.md`, whose follow-ups now link here.

1. Watch its CI: the first run of the 11 new `tools` tests on GitHub's runners, on both architectures. Record anything that fails only there.
2. After the review and the merge, do the workflow follow-up below.

The earlier draft review, which the 64174c9 one supersedes, and the refmap form's review stay untracked; neither is part of this change.

### Progress

- **No usage reports (tasks 1.1 and 1.2, 2026-11-02):**
  - `test_process.py`'s two new tests failed before the change (the tool saw `true`, and nothing), and pass after: 9 passed.
  - After rebuilding, `printenv BLAST_USAGE_REPORT` prints `false` in both the `engine` and the `api` image.
  - With `--add-host www.ncbi.nlm.nih.gov:10.255.255.1`, on this Apple Silicon Mac, arm64 image, times include starting the container (0.24 s on its own):
    - before, `blastp -version` took 14.50 s and 10.42 s;
    - after, `panther-engine tools`, which runs all four tools, took 1.02 s, and 0.66 s with `-e BLAST_USAGE_REPORT=true`, so `run_tool` overrides the caller. `blastp -version` by hand took 0.28 s.
- **Tie lines from BLAST+ 2.17.0 (task 2.1, 2026-11-02),** in the rebuilt engine image. Each pair is a seeded random sequence (`random.Random("tie:<n>/<L>")`), and the subject has `L − n` substitutions spread evenly between the 8th residue from each end. `blastp -subject` with the legacy `-outfmt` and options gave one full-length, ungapped line per pair, with the intended counts, first time. Written identities:

  | Pair | Written | `n / L × 100` | `100 × n / L` |
  | ---- | ------- | ------------- | ------------- |
  | 161/320 | 50.313 | 50.313 | 50.312 |
  | 199/320 | 62.187 | 62.187 | 62.188 |
  | 201/320 | 62.813 | 62.813 | 62.812 |
  | 402/640 | 62.813 | 62.813 | 62.812 |
  | 603/960 | 62.813 | 62.813 | 62.812 |
  | 804/1280 | 62.813 | 62.813 | 62.812 |
  | 1005/1600 | 62.813 | 62.813 | 62.812 |
  | 1021/1600 | 63.813 | 63.813 | 63.812 |

  The 201/320 line is `tests/fixtures/csnp/identity-tie.csv`, 699 bytes.
- **The formula (tasks 2.2 to 2.4, 2026-11-02):**
  - Before the change, the fixture test failed natively, and in the engine image all nine tie tests failed with `BlastError: the identity 62.813 isn't 100 * (length - mismatch - gaps) / length = 62.81250`, and the same for the other pairs.
  - The change: `hits.identity(identities, length)` computes `identities / length * 100`. Both `two_decimals` and `parity.blast_line` use it.
  - After it:
    - natively, `test_csnp_hits.py` and `test_csnp_parity.py` give 35 passed, with the 8 `tools` tests skipped;
    - in the engine image, with `PANTHER_REQUIRE_DATA=1` and `PANTHER_REQUIRE_TOOLS=1`, those two files and `test_csnp_golden.py` give 77 passed, none skipped.
  - `parity cases` into an empty scratch folder wrote 25 files, each byte for byte the committed one in `generated/`. Writing into scratch kept `generated/`'s reference outputs, which a regeneration in place deletes.
  - `parity check` reports 0 differences for the self-check, every step-2 run and every family. The golden tests natively give 30 passed, with 4 skipped for `blastp`.
  - The search of task 2.4 found the old formula only in `docs/code-review/`'s two whole-repository reviews. Those are dated records of the finding, so they stay as they are. No other doc or comment states it.
- **The data check (tasks 3.1 and 3.2, 2026-11-02):**
  - **The code:** `MissingDataError` is in `core/data.py`. `check_data(data_dir=None)` is in `csnp/scoring.py`, exported from `panther_engine.csnp`. `score()` calls it after the input checks and the early return for no substitutions, just before `blast.search`.
  - **Red first:** with a stub `check_data`, the five new failing-folder tests failed and the complete-folder test passed. The new tests are: only the database, an empty library, an empty folder, a missing database, and the error crossing a spawned worker.
  - **One existing test then failed:** `test_score_raises_the_input_error_for_a_sequence_blast_reads_as_a_comment`. It scores `;MKVL` with an empty data folder, and got `MissingDataError`, because the comment check was inside `blast.search`.
    - Design decision 4 puts the data check after the input checks, so the comment check is now `blast.refuse_comment()`. `score()` calls it before `check_data`, and `search()` still calls it for direct callers.
    - The test passes unchanged.
  - **The library test:** `test_a_family_the_library_doesnt_have_still_isnt_scored` (task 3.2) runs step 3 on the sample for `PTHR99999`. It passed at once, as a guard should: the behaviour isn't new.
  - **The checks:** `test_a_data_folder_without_the_database_is_a_failure_not_an_input_error` now expects `MissingDataError`. It no longer needs `blastp`, so it runs natively.
    - Natively, with `PANTHER_REQUIRE_DATA=1`, `test_csnp_scoring.py` and `test_csnp_psep.py` give 83 passed, with 12 skipped for `blastp` and `blastdbcmd`.
    - In the engine image, with both variables set, those two files and `test_csnp_blast.py` give 111 passed, none skipped.
- **The time limit (tasks 4.1 to 4.3, 2026-11-02):**
  - **The setup:** an Apple M1 Pro, with Docker Desktop's VM at 10 CPUs and 11.7 GiB, and the arm64 `panther-scoring-services-engine` image. Titin is Q8WZ42 from UniProt, 34,350 residues; the long query is titin then its first 15,650 residues, 50,000 in all. Each search was timed through `blast.search` with `timeout=3600`, one at a time, against the sample's database:
    - titin: 274.6, 273.9 and 267.2 s, each 9 lines;
    - 50,000 residues: 427.1, 436.9 and 424.0 s, each 15 lines.
  - **The rate:** 2.5 times the slowest needs 686.5 s for titin and 1,092.25 s for the long query. The provisional 20 ms a residue gave the long query 1,060 s, too little; 21 ms gives 781.4 s and 1,110 s.
  - **The tests,** written before the code, failed first on the missing `time_limit`. Then:
    - with 20 ms, the new 50,000-residue test failed, and with 21 ms it passes;
    - natively, the 14 limit and scale tests pass;
    - the only failures left in `test_csnp_blast.py` are 5.2's two, waiting for their change.
  - **The docs:** "The BLAST+ Time Limit" in `docs/testing/engine.md` has the timing command. Run on 400 of titin's residues, it printed `400 residues: 5.6 s`. `engine/README.md` quotes 781 s for titin.
- **Exit status 1 and data folder paths (tasks 5.1 and 5.2, 2026-11-02):**
  - **5.1:** `tests/fixtures/csnp/blastp-unknown-argument.stderr` is what BLAST+ 2.17.0 wrote for `-bogus_option`: 34 lines, ending in the two `Error:` lines. The fake-`blastp` tests for it and for an empty standard error failed first, with `InputError`. After the change, they and the whole file pass natively. In the engine image, the real `-best_hit_overhang 0.9` test gives a `BlastError` naming the argument, and `test_a_query_blastp_cant_read_is_an_input_error` still passes. Neither divergence row 8 nor `docs/testing/engine.md` says that every status 1 is the input's fault, so no doc changed.
  - **5.2, before the change:** in the engine image, both path tests (`my data`, and `a "quoted" folder`) failed with `blastp exited with status 2: BLAST Database error: No alias or index file found for protein database [.../my]`, and `[.../a]`.
  - **5.2, the change:** `search()` runs `blastp` in `<data>/blast` with `-db blast`, and raises `BlastError("no BLAST database folder: …")` without it. The `blastp` fixture now makes `tmp_path/blast`, and `RECORD` writes the working folder too.
  - **5.2, after it:** natively, `test_csnp_blast.py` and `test_csnp_scoring.py` give 61 passed, with 15 skipped for the tools. In the engine image, with both variables set, those two files and `test_csnp_golden.py`, which holds the step-1 goldens, give 110 passed, none skipped.
- **The manifest commands (tasks 6.1 and 6.3, 2026-11-02),** done while task 4.1's timings ran, natively, so Docker stayed free for them:
  - **The code:** `csnp/full.py` has `build()` and `hash_members()`, and `full.MANIFEST` is `full.json`. The CLI's `csnp data manifest` and `csnp data verify` are in `csnp/cli.py`. `verify` reuses `sample.verify_folder` with `full.json`.
  - **The manifest tests,** in `tests/test_csnp_full.py`, failed first: there was no `csnp data` command.
    - In the first run, the fixture's `PAML_RST/` entry became a 0-byte regular file, since `make_tar` writes every member as a file. The builder rightly refused it as "not a relative path". The fixture now leaves it out; the real archive's folder entry is skipped as a non-file.
    - Ruff's `S101` rejected two `assert`s; `core.manifest.checksums` gives the typed `files` instead.
  - **`verify` came before its tests,** written with `manifest` in 6.1. So its tests (6.3) passed at once. To show they can fail, `verify` was broken twice and restored byte for byte:
    - without the 20-path cap, `..._reports_30_and_names_20` failed;
    - exiting 0 on mismatches, the deleted-and-truncated test and the 30-file test failed.
  - **Result:** natively, 14 of the file's 15 tests pass. `test_verify_uses_the_engines_full_manifest_by_default` waits for `full.json` (task 6.2).
- **`full.json` (task 6.2, 2026-11-02):**
  - **The build:** natively, from `engine/`, with the four inputs at the paths task 6.2 names. Each build took 31.1 s and 31.7 s, and the two are byte for byte the same.
  - **The file:** 25,826 files, which is 8,607 each of `.paml`, `.rst` and `.orig.tree`, the three database files, the species tree and the copyright statement. 2,786,534 bytes and 25,842 lines, sha256 `b53d8c3eb4fc7a685407c27bfe25dbba6d23a17566d26cf8168ca864e8050c21`.
  - **The tests:** `test_the_full_manifest_lists_every_sample_file_with_the_same_sha256` and `..._pins_the_same_sources_as_the_sample` pass, and so does the default-manifest test from 6.3: 17 passed.
  - **Showing the agreement test can fail:**
    - The first mutation prefixed a `0` to `PTHR10366.paml`'s sha256. The test failed on the malformed 65-character digest, not on the mismatch, so it proved nothing.
    - Changing one hex digit instead failed it with both digests shown.
    - `full.json` was restored from the second build, byte for byte.
  - **`.gitattributes`:** marks `full.json` `linguist-generated`, and `git check-attr` reports it set.
- **The full library (task 6.4, 2026-11-02),** in the session's scratchpad, by engine.md's steps with only the folder changed:
  - **Install:** 43 s in all, 19 GB. The unpacking took 29 s; the `sample fetch` that adds the copyright statement downloaded `csnp-sample-3` from GitHub.
  - **`csnp data verify`:** "0 missing and 0 differing, of 25,826 listed files" and exit 0, in 21.3 s natively. In the engine image, with the folder bind-mounted on macOS, 68.4 s.
  - **A broken copy:** with `PAML_RST/PTHR15921.paml` deleted and `PTHR23097_1.rst` truncated to 1,000 bytes, it printed "1 missing and 1 differing", named both, and exited 1. After both were extracted again from the archive, it passed.
  - **Scoring:** in the engine image, with `PANTHER_DATA_DIR` naming the full data, 6 tests passed: the three spec §7.3 proteins, the form's example against `apoe.out`, and both odd-path tests. `csnp score` printed P26439's rows as engine.md shows them.
  - **Docs:** engine.md's "Using the Full Library" now ends with `csnp data verify`, and gives the times and the rebuild check. The rebuild check, run as written, gave the same bytes. `git diff --exit-code` proves nothing until `full.json` is committed, since git doesn't diff an untracked file, so it was compared with 6.2's second build too.
  - **Cleanup:** the scratch copy is deleted.
  - **Disk:** free space read 71 GB afterwards, against 95 GB before the install. That wasn't the copy: the scratchpad is 2.9 MB. macOS holds OS-update snapshots (`com.apple.os.update-MSUPrepareUpdate`), and Docker has 7 stopped containers using 4.4 GB, left alone.
- **The final check (task 7.1, 2026-11-02),** from `git checkout-index -a` of the 28 staged files into the session's scratchpad. The three untracked `docs/code-review/` notes aren't part of this change, so they're left out. The copy got an APFS clone of `.data/csnp`.
  - **`engine/`, natively:** `uv sync --locked`, `ruff check`, `ruff format --check` and `basedpyright` pass. `PANTHER_REQUIRE_DATA=1 uv run pytest` gives 439 passed, 31 skipped for `blastp`, `blastdbcmd` or `epa-ng`. Against #36's 396 and 21, that's 43 more passed and 10 more skipped: 11 new `tools` tests, and one test that no longer needs `blastp`.
  - **`docker compose run --rm --build engine`,** with both variables set: 470 passed, none skipped. #36 had 417.
  - **`api/`, natively:** `uv sync --locked`, `uv lock --check`, `ruff check`, `ruff format --check` and `basedpyright` pass. `uv run pytest` gives 245 passed, with the 5 real jobs skipped for `blastp`.
  - **The API image,** with the tools and the sample, by `docs/testing/api.md`'s command: 250 passed. That includes the committed OpenAPI schema test, so the contract didn't change. Nothing under `api/` or `frontend/` changed.
  - **`npx markdownlint-cli2`:** 140 files, no issues. **`npx openspec validate --all --no-interactive`:** 10 passed. Its two warnings are about long requirements in the main `scoring-ui` spec, not this change.
  - **Size:** about 1,180 changed lines without `full.json` and the artifacts, over the 400-line norm. proposal.md's Impact, Size, says why it isn't split.

### Blockers

None. Task 6.4 needs 19.9 GB free; this machine had 101 GB free on 2026-11-02.

### Failed approaches

- **The provisional time-limit rate (2026-11-02):** 20 ms a residue gave the 50,000-residue query 1,060 s, under 2.5 times its slowest search, 436.9 s. Searching isn't quite linear: titin took about 8.0 ms a residue, the long query 8.7. It's now 21 ms.
- **A symlink for the copy's data (task 7.1, 2026-11-02):** `git checkout-index` writes the tracked `.data/.gitkeep`, so the copy already had a `.data` folder, and `ln -s` put the link inside it. The engine image then saw an empty data folder, and 101 tests failed with `PANTHER_REQUIRE_DATA=1`. Fixed by cloning `.data/csnp` into the copy with `cp -Rc`. A symlink as a bind-mount source isn't needed then.
- **A mutation that broke the format (task 6.2):** prefixing a digit to a sha256 in `full.json` made it 65 characters long, so the test failed on the malformed manifest, not on the mismatch it's meant to catch. Change one digit instead.

### Lessons learned

- **Measured while planning (2026-11-02),** with the system Python on this machine:
  - Up to length 10,000, `n / L × 100` and `100 × n / L` give different three-decimal strings at 31 lengths, all multiples of 320, for 1,343 identity counts. They give different two-decimal strings at 62 lengths, all multiples of 160, for 1,318 counts. The first is 23/160: 14.37 against 14.38.
  - Under `n / L × 100`, none of the goldens' 109 BLAST lines changes its written identity or its two-decimal value. That covers 9 files: the four step-1 goldens, `release/HUMAN` and the generated step-2 `.blast` files.
- **BLAST+ 2.17.0's failures (2026-11-02),** in `panther-scoring-services-engine:latest`, against the sample:
  - a query the FASTA reader rejects (`1234567890`, `MK(VL`) exits 1, with one line: `BLAST query error: CFastaReader: Near line 2, there's a line that doesn't look like plausible data, but it's not marked as defline or comment.`;
  - an unknown argument (`-bogus_option`) or a value out of range (`-best_hit_overhang 0.9`) exits 1 too. It writes the usage text, then two `Error:` lines naming the argument;
  - an unknown `-outfmt` field (`10 qseqid nosuchfield`) exits 0 and writes nothing to standard error. Step 2's 15-field check is what catches it;
  - a missing database exits 2, with `BLAST Database error: No alias or index file found …`.
- **`-db` and paths (2026-11-02),** searching for APOE with the legacy options:
  - an absolute path with a space exits 2, naming only the part before the space;
  - the path in double quotes inside the argument works, but not when the path has a `"`;
  - run in the database's folder with `-db blast`, it works with a space and with a `"`, and with `BLASTDB=/nonexistent`. Its output is exactly `blast/APOE.csv`;
  - in a folder without the database, BLAST+ falls back to `BLASTDB` and searches the database found there.
- **Learned while applying (2026-11-02).** Each of these may belong in `CLAUDE.md` or `docs/` at archive:
  - **The final check's copy needs the sample cloned, not linked.** `.data/.gitkeep` is tracked, so `git checkout-index -a` makes `.data/` a real folder in the copy. `cp -Rc .data/csnp <copy>/.data/` clones it on APFS, and compose's bind mount sees it. Every change's final check does this.
  - **Check that `parity cases` is stable without regenerating in place.** golden-setup.md's regeneration deletes `generated/step2` and `step3`, the Perl's outputs included. Writing the cases into an empty scratch folder and comparing each file is enough when only the generator changed.
  - **Time long searches in the built image,** with `docker run`, not `docker compose run`. compose mounts the working copy, so editing the engine mid-run would change what's timed. Keep other Docker work off the machine meanwhile.
  - **Input errors come before data checks.** A check of the server's data that runs before an input check turns the user's mistake into a 500, as `;MKVL` with no data did. That's why `blast.refuse_comment()` runs before `check_data()`.
  - **`python3` in `engine/` is pyenv's shim,** and `.python-version` asks for a 3.13 that pyenv may not have. Use `uv run python`, or `/usr/bin/python3` for a helper script outside the project.
