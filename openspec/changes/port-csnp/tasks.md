# Tasks

Test-first: for each task that adds code, write its tests, run them and see them fail for the right reason, then write the code. Paths under `engine/` are relative to `engine/src/panther_engine/` unless they start with `tests/`.

## 1. The Input Error and the Shared Docs

- [x] 1.1 Do `add-job-input-errors` task 1.1 (`core/errors.py`, `InputError` with `__reduce__`, and `tests/test_errors.py` with its three scenarios through a real `spawn` pool), and tick it in that change's `tasks.md`. Verify that its three tests pass, and that `docker compose run --rm engine` passes
- [x] 1.2 Do `add-job-input-errors` task 1.2 (when to raise `InputError`, the message rules, single-item problems belong in the result), in `docs/testing/engine.md`, and tick it there. Verify `npx markdownlint-cli2` passes
- [x] 1.3 In `docs/parity/divergences.md`:
  - add row 8 for `csnp`: a query `blastp` can't read (exit status 1). The reference gives every substitution "Not scored: No PANTHER family for input sequence"; the Python raises `InputError` (a `422`). "Approved by" is "Engine developer", dated when they approve the pull request. Task 7.2 fills in which inputs trigger it;
  - in the note under the table, say that `SCORE-7` and `SCORE-8` don't arise in the service, which scores one protein, so one family, per call, as the CGI did. Row 3 stays a proposal for batch use.

  Verify `npx markdownlint-cli2` passes
- [x] 1.4 In `docs/design/tech-stack.md`:
  - **Engine condition 3:** the `csnp` reference image takes the scripts from a developer's checkout through `git archive cebb5ab`, because `pantherdb/cSNP_analysis` is private (engine developer, 2026-10-29);
  - **Open Questions, All services:** making the original repositories public (`cSNP_analysis` and `pantherScoring` are private), to consider eventually; and the licence (PSEP 1.01 is GPLv2, and this repository has none);
  - **the Status line:** the revision.

  Verify `npx markdownlint-cli2` passes and `grep -n 'cloned when the image is built' docs/design/tech-stack.md` finds nothing left that contradicts it

## 2. Running Tools With Input

- [x] 2.1 Give `core/process.py`'s `run_tool()` a keyword-only `input` (text sent to stdin) and `cwd` (the working folder). Nothing else about it changes. Verify `tests/test_process.py`:
  - text with shell metacharacters and newlines reaches a fake program's stdin unchanged;
  - the program runs in `cwd`;
  - the existing no-shell test still passes

## 3. The Sample With the BLAST Database

- [x] 3.1 Give `csnp/sample.py`'s `build` and `panther-engine csnp sample build` a `--blast-archive`, checked against the pin in spec §7.1 (`2cf4428c…`). It copies `blast/blast.phr`, `.pin` and `.psq` to `csnp/9/blast/` and records the archive in the manifest (design.md, decision 8). Verify `tests/test_csnp_sample.py`, with a fixture BLAST archive built in `tmp_path`:
  - two builds are byte-identical;
  - a BLAST archive with the wrong sha256 exits non-zero, naming both checksums, and leaves no tarball
- [x] 3.2 Build `csnp-sample-2.tar.gz` from the pinned archives, with the same 15 families, and write `csnp/sample.json`. Verify:
  - a second build is byte-identical;
  - each BLAST file's sha256 equals the one inside `PANTHER9.blast.tar.gz`;
  - `uv build --wheel` includes `sample.json`.

  Record the compressed and unpacked sizes in the Notes
- [x] 3.3 Add to `tests/test_csnp_sample_data.py` a test marked `tools("blastdbcmd")` and `data("csnp")`: `blastdbcmd -info` on the sample's database reports 570,173 sequences. The marker takes any program on `PATH`; `core/tools.py`'s `TOOLS`, which the API reads, doesn't change. Verify it passes in the engine image with the sample from `fetch --from` the local tarball
- [x] 3.4 Publish `gh release create csnp-sample-2 csnp-sample-2.tar.gz --prerelease`, with notes linking the survey doc. The engine developer approves publishing first: the asset is public, and the BLAST database is part of the public PSEP 1.01 release. Then fetch into an empty `.data/`. Verify:
  - the fetch downloads and verifies;
  - a second fetch downloads nothing;
  - `gh release view csnp-sample-2` shows the asset with the manifest's size;
  - the repository's latest release is unchanged
- [x] 3.5 In `docs/testing/engine.md`:
  - the sample now holds the BLAST database;
  - the full data's layout, adding `tar -xzf PANTHER9.blast.tar.gz -C <root>/csnp/9/`;
  - publishing a sample with `--blast-archive`.

  In `docs/design/tech-stack.md`'s Data bullet, give `csnp-sample-2`'s size. Verify `npx markdownlint-cli2` passes, and the commands run as written

## 4. The Reference Image and the Goldens

- [x] 4.1 Create `tests/golden/csnp/`:
  - `release/`: `HUMAN`, `sample.input` and `sample.fasta`, copied from the PSEP 1.01 release;
  - `spec/`: §7.3's output, and §7.5's input and output, transcribed from the legacy behaviour spec. `e10`'s input line and output keep their `\r`;
  - a `README.md` giving each file's source and sha256, the release's copyright statement, and how to regenerate.

  Verify:
  - `HUMAN` and `sample.input` match the sha256 in spec §7.1;
  - after `git add`, `git ls-files --eol tests/golden/csnp/` shows the `e10` files stored with their CRLF;
  - `npx markdownlint-cli2` passes
- [x] 4.2 Add the `csnp-reference` stage to the root `Dockerfile` (design.md, decision 9): Debian's `perl`, the three scripts from the named context `csnp-reference-scripts`, and `sha256sum --check --strict` against their pins. Verify:
  - it builds from a `git archive cebb5ab` of the local `cSNP_analysis` checkout;
  - with one byte of `PANTHER_PSEP1.01.pl` changed, the build fails, naming the file;
  - `docker buildx build --target engine` and `--target api` build without the context;
  - `docker run --rm <api image> sh -c 'dpkg -l perl; ls /opt/csnp-reference'` finds neither Debian's `perl` package nor the scripts. The image keeps Debian's Essential `perl-base`, from the Python base image (engine developer, 2026-10-30)
- [x] 4.3 Add `csnp/parity.py`'s Perl runner and `panther-engine csnp parity reference`. Each run gets a fresh working folder linking the data folder's species tree, and calls `perl` through `run_tool()`. Run the self-check in the image:
  - steps 2 and 3 on `release/` must reproduce `spec/`'s §7.3 output byte for byte;
  - §7.5's input (step 2 with `-s NA`) must reproduce its output.

  Save step 2's snpParse output for both as goldens in `generated/`. Record the Perl version in the Notes. Verify both comparisons are byte-identical
- [x] 4.4 Add `panther-engine csnp parity cases` (design.md, decision 10): step-3 cases per family, grouped by gene, and step-2 cases (listed and seeded alignments, ties, species substrings). Verify `tests/test_csnp_parity.py`, without data, on the fixture family:
  - the same seed gives identical cases;
  - a different seed gives different ones;
  - the cases include a wrong wild type, a position past the end, both sequence ends, a "no family" row and an unmapped row
- [x] 4.5 In the image, generate cases for the 15 sample families (default 5 genes × 8 positions) and the step-2 cases, run them through `parity reference`, and commit both under `generated/`. Verify:
  - a second run gives identical files;
  - the families' walks reach nodes of every event kind the sample has (`0>1`, `1>0`, `0>0`, `Ev=UNK`, a taxon missing from the species tree). Record which in `docs/parity/inputs.md`
- [x] 4.6 Write `docs/parity/golden-setup.md` (the `git archive` and `docker buildx build --build-context` commands, the self-check, regenerating the goldens, the staging run on the full library) and `docs/parity/inputs.md` (each input, by kind, and why it's in the set; how §7.5's cases map to the service). Mark both as existing in `docs/parity/README.md`'s What Goes Here. Verify `npx markdownlint-cli2` passes, and the commands in `golden-setup.md` run as written

## 5. Step 2: The Best Hit and the Mapping

- [x] 5.1 Write `tests/test_csnp_hits.py` on synthetic BLAST lines (design.md, decision 4), and see it fail:
  - the species filter matches anywhere in the line, case-sensitively;
  - the ranking, with ties broken byte by byte;
  - `pident` recomputed to 2 decimals, and a line whose recomputed value doesn't round to its own fails;
  - the first line per `qseqid`;
  - family and `ANinfo` from `sseqid`;
  - `MAP-4` (position at `qstart`; `AB-CD` against `ABXCD`);
  - `010` echoed as written but mapped as 10;
  - no hit.

  Then write `csnp/hits.py`. Verify the tests pass
- [x] 5.2 Add golden tests: step 2 on `release/HUMAN` and `sample.input` (species `HUMAN`), on §7.5's input (`NA`), and on the generated step-2 cases, each byte-identical to its golden snpParse. Verify they pass; they need no data

## 6. Step 3: Trace-Back, Ages, Message and pDel

- [x] 6.1 Add `read_sites(lines, name, sites)` to `csnp/paml.py`: several sites in one pass, stopping after the last one needed. Verify `tests/test_csnp_paml.py`: each site equals `read_site`'s, and a site past the end is reported as absent, not an error
- [x] 6.2 Write `tests/test_csnp_psep.py` on hand-written fixture families, and see it fail. Extend `tests/fixtures/csnp/` where needed, with a duplication, a `0>0` node, an `Ev=UNK` root and a taxon missing from the species tree. It covers:
  - the order of checks (`SCORE-1`), including a family with no sequence list giving "Invalid substitution" without reading its `.paml`;
  - `getCorrectnum`'s column;
  - the start column (`SCORE-2`);
  - the walk, with a NaN cell, and a start column of `None`;
  - each age rule in design.md decision 5, and the cap;
  - message and pDel at every bound: 24/25, 84/85, 90/91, 98/99, 198/199, 398/399, 698/699, 798/799, 898/899, 1298/1299, 1598/1599, 3998/3999, and 179/180 and 379/380 for the message;
  - the empty age.

  Then write `csnp/psep.py`. Verify the tests pass
- [x] 6.3 Add `panther-engine csnp parity check`, and golden tests marked `data("csnp")`:
  - steps 2 and 3 from `release/` give `spec/`'s §7.3 output byte for byte;
  - §7.5's input gives its output;
  - every family's generated step-3 cases give their golden output;
  - the broken families give "Invalid substitution".

  Verify they pass with `PANTHER_REQUIRE_DATA=1`, none skipped, and that a golden row changed by hand fails, naming the case
- [x] 6.4 Time step 3 in the image for 10 substitutions in `PTHR11695` (the largest `.paml`) and in `PTHR10366`, and record both in the Notes. Above about 10 s, note a follow-up for an index (design.md, Risks). Verify the times are recorded

## 7. Step 1 and `score()`

- [x] 7.1 Write `tests/test_csnp_blast.py` with `make_tool` fake `blastp` programs that record their arguments and stdin, and see it fail:
  - the arguments and the `>P0001` query are the legacy's (design.md, decision 3);
  - exit 0 returns the lines;
  - exit 1 raises `InputError`, whose message contains none of the fake's stderr;
  - exit 2, a timeout and a missing `blastp` raise `BlastError`, which isn't an `InputError`.

  Then write `csnp/blast.py`. Verify the tests pass
- [x] 7.2 In the image, against the sample's database, find which inputs the API accepts (printable ASCII, no whitespace) make `blastp` 2.17.0 exit with status 1. Try all digits, all punctuation and a lone residue. Write the `InputError` message for them, and complete divergence row 8. Add a test marked `tools("blastp")` and `data("csnp")` with one such input. Record what exits with 1, and what doesn't, in the Notes. Verify the test passes
- [x] 7.3 Write `csnp/codes.py`'s `SPECIES_CODES` from the database's species, and a test marked `tools("blastdbcmd")` and `data("csnp")` that the sample database's species are exactly these 85 codes. If `blastdbcmd` can't list them, follow design.md's fallback and say so in the Notes. Verify it passes
- [x] 7.4 Write `csnp/scoring.py`:
  - the frozen dataclasses `CsnpInput`, `CsnpResult` and `SubstitutionScore`, with the fields agreed on #19;
  - `score()` (design.md, decision 6);
  - the exports in `csnp/__init__.py`.

  Test first, in `tests/test_csnp_scoring.py`:
  - `ValueError` for an unknown species, a bad token or a bad sequence, with nothing searched;
  - the family cut: `PTHR23125_2`, `AN12345`, empty;
  - the conversion of result records, including the empty age.

  Then, marked `tools("blastp")` and `data("csnp")`:
  - §7.3 as three calls;
  - "Order of calls";
  - `A010E`;
  - two proteins scored at the same time in a `spawn` pool.

  Verify they pass in the image
- [x] 7.5 Commit `tests/golden/csnp/blast/`, the BLAST+ 2.17.0 output for the three `sample.fasta` proteins against the sample's database. Add a test (`tools`, `data`) that the output equals it, and that each protein's best hit equals its first row in `release/HUMAN` in subject id, starts and aligned sequences. Replace tech-stack.md's "cSNP's BLAST step has no golden yet" with where it is. Verify the test passes and `npx markdownlint-cli2` passes

## 8. The Command Line and the Testing Docs

- [x] 8.1 Add `panther-engine csnp score FASTA --species CODE SUBSTITUTION...`, with `--data-dir` and `--json`. It normalises one FASTA record as the API does (header, whitespace, upper case), refuses more than one, and prints the family and each score. Verify `tests/test_csnp_cli.py`:
  - P26439 with `A10E` and `G15D` prints `PTHR10366` and §7.3's two rows (`tools`, `data`);
  - a two-record file exits non-zero and scores nothing;
  - `--help` lists the options
- [x] 8.2 In `docs/testing/engine.md`, add scoring from the command line, the parity golden tests, and `parity check`. Point to `docs/parity/golden-setup.md` for the reference image. In `docs/testing/README.md`, add the parity tests to the Engine row of Kinds of Test. Verify `npx markdownlint-cli2` passes, and the commands run as written

## 9. Final Check

- [x] 9.1 From a copy of the files git would commit:
  - in `engine/`, after `uv run panther-engine csnp sample fetch --data-dir ../.data`: `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright` and `PANTHER_REQUIRE_DATA=1 uv run pytest` pass, with only the `tools` tests skipped;
  - from the root: `docker compose run --rm engine` passes with nothing skipped;
  - in `api/`, which imports the engine: `uv sync --locked` and `uv run pytest` pass, and `uv lock --check` reports no change;
  - `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass

## Workflow follow-up

- **One pull request** for the proposal and the implementation, the engine developer's choice (proposal, Size).
  - All three developers approve it, because it changes `tech-stack.md`, `divergences.md` and the root `Dockerfile`.
  - The engine developer's approval also signs off divergence row 8. Date the row then.
  - On the pull request, confirm in the logs, not just the results:
    - the `engine` job fetches `csnp-sample-2` on a cache miss;
    - both `engine-image` legs run the `tools` and `data` tests with none skipped;
    - the `api` jobs pass.
- **The API developer wires the engine in,** in their own change:
  - remove the `501`;
  - add the adapter;
  - `add-job-input-errors` group 2;
  - check species membership against `SPECIES_CODES`;
  - give the `api` compose service the data mount and `PANTHER_DATA_DIR`.

  The frontend developer removes the `501` branch and its mock, and regenerates the types.
- **Staging,** before production:
  - provision the full data, checked against a manifest;
  - run `parity cases`, `parity reference` and `parity check` on the full library: that's M1's acceptance;
  - record the result in `docs/parity/`.
- **After the merge,** archive with `/opsx:archive`. That creates `openspec/specs/psep-engine/spec.md` (delete its `.gitkeep`), and updates `csnp-data`.
- **After cSNP is live on production,** open an issue for the science owner on rows 2, 3, 4, 5 and 7.

## Notes

### Next action

Every task is done. Open the pull request (Workflow follow-up): all three developers approve it, and the engine developer's approval dates divergence row 8. On the pull request, check CI's logs as listed there.

### Blockers

None. The engine developer decided the three that came up in apply (2026-10-30):

- **Task 3.4:** publish `csnp-sample-2`. Published as a pre-release; the repository still has no Latest release.
- **Task 4.2, Perl in the `api` image:** accept Debian's Essential `perl-base`, which comes with the Python base image and which `dpkg` won't remove. The check, the spec's Reference image requirement, design.md decision 9, the proposal, `tech-stack.md` and `golden-setup.md` now say the image has neither the scripts nor Debian's `perl` package.
- **BLAST+'s exit status 3:** a sequence that starts with `!`, `#` or `;` is read as a FASTA comment, so BLAST+ finds no sequence and exits with 3, an engine error. `blast.search()` raises the same `InputError` before running `blastp`. Divergence row 8, design.md decision 3, the spec and the proposal say so, and `tests/test_csnp_blast.py` and `tests/test_csnp_scoring.py` test it.

### Progress

- **`csnp-sample-2` (task 3.2, 2026-10-29):** built twice from the pinned archives, byte-identical, sha256 `87506a64…`. Compressed 156,610,658 bytes (157 MB); unpacked 622,293,060 bytes (622 MB), against 26 MB and 260 MB for `csnp-sample-1`. Each build took about 1.5 minutes on an M-series Mac. The three BLAST files' sha256 match the ones inside `PANTHER9.blast.tar.gz`, and the wheel holds `sample.json`.
- **`blastdbcmd -info` (task 3.3):** 570,173 sequences, in the engine image, with the sample fetched `--from` the local tarball.
- **The reference image (task 4.3):** Perl 5.40.1, Debian's `perl` `5.40.1-6+deb13u1`, on aarch64. Its self-check reproduces spec §7.3 and §7.5 byte for byte. The self-check takes about 40 s, and the whole generated set about 5 minutes.
- **Parity (tasks 4.5, 6.3):** 296 step-2 cases and 606 step-3 cases in the 15 sample families: the port matches the Perl byte for byte, with no differences. Generating the cases takes 8 s, and `parity check` 2 s.
- **What makes `blastp` 2.17.0 exit with 1 (task 7.2),** against the sample's database, with the query on stdin: all digits (`1234567890`, `12`, `1.5`), a lone `-` or `~`, `......`, `()`, `[]`, `{}`, `<>`, `*()`, any one of `%&^@$?=_/+:|`, and letters followed by `.` or `!` (`MKVL.`, `MKVL!`, `MKV.`). The message says "BLAST query error: CFastaReader: Near line 2, there's a line that doesn't look like plausible data".
- **What doesn't (task 7.2):** a lone residue (`M`, `B`, `U`, `X`, `*`), `MKV`, `ZZZZ`, `JJJJ`, `OOOO`, `MK*V` and `MKV*` exit with 0 and no hit. A digit among letters (`MKV1`, `1M`, `M!`) and hyphens (`MKV-`, `M-K`) are dropped with a warning, and exit with 0. Exit 3: a sequence starting with `!`, `#` or `;` (Blockers).
- **Step-1 golden (task 7.5):** the same bytes from BLAST+ 2.17.0 on amd64, run under emulation from the `Dockerfile`'s `blast` stage, as on arm64.
- **End to end (task 7.4):** in the engine image, `score()` reproduces spec §7.3 for the three proteins, one call each, through BLAST+ 2.17.0. `tests/test_csnp_scoring.py` takes about 70 s there.
- **Final check (task 9.1), 2026-10-30,** from a copy of the files git would commit: in `engine/`, `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright` and `PANTHER_REQUIRE_DATA=1 uv run pytest` pass, 381 passed and only the 18 `tools` tests skipped; `docker compose run --rm --build engine` passes, 399 passed, none skipped; in `api/`, `uv sync --locked`, `uv run pytest` (147 passed) and `uv lock --check` pass; `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass. Run again after 3.4, from a fresh copy, with `sample fetch` downloading the published sample: 387 passed natively with only the 19 `tools` tests skipped, 406 passed in compose with none skipped, and the rest as before.
- **Order of work:** steps 2 and 3 (groups 5 and 6) were written before the case generator (4.4), which uses step 3's tree to choose genes and positions whose walks stop at each kind of node.

### Failed approaches

- **Node kinds by the event the Perl reads (task 4.5).** The first generated set never stopped at a `0>0` node. In the sample's data, every duplication and every `0>0` node is written without `S=`, so the Perl's pattern reads no event for them and ages them as duplications. Lumping them as "event not read" hid them from the generator. Kinds now carry the `Ev` value (`Ev=1>0, not read`, `Ev=0>0, not read`), and the set was regenerated.

### Lessons learned

- **Spec §4.4's "`0>0` with a known taxon" doesn't occur in the sample.** Real `0>0` nodes have no `S=`, so they're aged as duplications. The fixture family `PTHR00004` has one with `S=`, and the Perl gives it an empty age (`getYear` falls through), as design.md decision 5 says.
- **A family without a sequence list inherits `$nth` in a batch.** Alone, as in a one-protein call, it gives "Invalid substitution". After another family's record in the same Perl process, it can be scored from column 0 ("0,probably benign,0.02"). The port keeps `$nth` per call, so it would raise `LibraryFormatError` there instead. That only happens in a batch spanning families, which the service never runs.
