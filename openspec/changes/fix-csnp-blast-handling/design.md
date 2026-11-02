# Design

## Context

See proposal.md, Why. The findings, with how each was reproduced, are in [the review at `64174c9`](../../../docs/code-review/2026-10-30-whole-repo-review-64174c9.md): ENG-1, CSNP-1 and CSNP-3 to CSNP-6.

This change relies on these decisions, and doesn't change them:

- **[tech-stack.md](../../../docs/design/tech-stack.md):**
  - Shared Concerns, Data: the full library stays off developer machines and CI, which use the sample;
  - Environments: every deploy checks the data against a pinned checksum manifest;
  - Pinning Tool Versions: BLAST+ 2.17.0, and `pident`'s three decimals.
- **[hosting.md](../../../docs/design/hosting.md):** the server mounts the full cSNP data read-only and names it with `PANTHER_DATA_DIR`, and each running job uses one worker process.

What the code does today:

- **`core/process.py`'s `run_tool`** is the one place the engine starts a subprocess. The child inherits the caller's whole environment. `core/tools.py` (`panther-engine tools`, and the API's startup through `report_tools()`) and `csnp/blast.py` both start `blastp` through it.
- **`csnp/hits.py`'s `two_decimals`** computes `100 * (length - mismatch - gaps) / length`. It raises `BlastError` unless that rounds to BLAST+'s three-decimal value, and returns it to two decimals for ranking (`MAP-1`). `csnp/parity.py`'s `blast_line` builds generated lines with the same formula.
  - The archived `port-csnp` design says the formula was checked to round to 2.17.0's value "on every line". That was every line of the goldens, none of which is at a tie. This change's tests replace that claim; the archive isn't edited.
  - Python's float arithmetic is IEEE double, as BLAST+'s C++ is, so the same operations in the same order give the same value.
- **`score()`** reaches the data only through `blastp`'s `-db` and step 3. Step 3 treats a family without a `.paml` as "No PANTHER family", as the Perl's `-e` does, and thousands of families legitimately have none.
- **`csnp/blast.py`'s `search()`** passes the database as an absolute path, `-db <data>/blast/blast`. It turns every exit status 1 into `InputError`, and drops BLAST+'s standard error. For any other status, its `BlastError` keeps the last three lines of standard error. The API logs a `BlastError` with its traceback, but an `InputError` with only its message, at INFO (`jobs/runner.py`).
- **`blast.TIMEOUT`** is a fixed 300 s. The API has no per-job limit of its own, and its worker processes inherit its environment.
- **`core/manifest.py`** reads, checks and verifies manifests whose `files` member maps relative paths to sha256. `sample.json` is one. The survey streams the PAML_RST archive through sha256 without unpacking it.

## Goals / Non-Goals

**Goals:**

- No change to any golden, generated case or `parity check` result.
- No change to the API's code or its OpenAPI schema. The api ↔ engine interface stays as agreed on #19.
- Each fix has a test that fails without it.

**Non-Goals:**

- An explicit environment for every tool. This change only adds one variable to what's inherited.
- An API readiness endpoint. The data check is a public engine function the API can call later.
- Installing the full data. `docs/testing/engine.md` already has the steps; this change adds `verify` as the last one.

## Decisions

1. **`BLAST_USAGE_REPORT=false` in `run_tool` and in the `tools` stage.**
   - `run_tool` passes the caller's environment with that one variable set to `false`, overriding any value the caller has. It does this for every tool: HMMER, EPA-ng and Perl ignore it, and a list of which tools need it would be one more thing to keep current.
   - The `Dockerfile`'s `tools` stage sets `ENV BLAST_USAGE_REPORT=false`. `engine`, `api` and `csnp-reference` inherit it, which covers `blastp` run by hand in an image, as the step-1 golden command does.
   - *Alternative:* only the `Dockerfile`. Rejected: a native run, such as `panther-engine csnp score` with Homebrew's BLAST+, would still report, and so would any future image that doesn't start from `tools`.
   - *Alternative:* only in `blast.search`. Rejected: `panther-engine tools` and the API's startup also run `blastp -version`, through `core/tools.py`.
   - *Alternative:* an explicit, minimal environment, as the review's Improvements suggest. Rejected here: it changes `PATH`, the locale and `TMPDIR` for every tool, which needs its own tests. That's `harden-engine-tooling`.
2. **One identity formula, BLAST+ 2.17.0's: `(length - mismatch - gaps) / length * 100`, for both the check and the two-decimal value.**
   - The review ran eight ungapped tie pairs through `blastp -subject`, and 2.17.0 wrote `n / L * 100` in all eight.
   - Up to length 10,000, the two formulas give different three-decimal strings at 31 lengths, all multiples of 320, and different two-decimal strings at 62 lengths, all multiples of 160 (computed for this design).
   - Using BLAST+'s order for the ranking value too assumes the legacy BLAST+ computed `pident` the same way and only printed fewer decimals (proposal, Open Questions). The current formula has no evidence behind it either; `port-csnp` chose it before 2.17.0's order was known.
   - Under the new formula, all 109 BLAST lines in the goldens keep their written identity and their two-decimal value: the step-1 goldens, `release/HUMAN` and the generated step-2 inputs.
   - *Alternative:* BLAST+'s order for the check only, keeping `100 * n / L` for ranking. Rejected: two formulas for one number, the second with nothing to support it.
   - *Alternative:* a tolerance of ±0.001 in the check. Rejected: the check exists to prove the formula, so a BLAST+ upgrade that changes the formula or the columns fails loudly. A tolerance would let it drift.
   - `parity.py`'s `blast_line` uses the same formula, so every generated line is one BLAST+ could have written. `parity cases` must then give the same bytes as before.
3. **Two kinds of tie test.**
   - A unit test, with no tools, on a committed real line: 201 identities over 320 columns, as 2.17.0 wrote it in the engine image. It runs in CI's `engine` job, natively.
   - A `tools("blastp")` test that builds each of the eight pairs and aligns it with `blastp -subject` and the legacy `-outfmt`. It checks that each line has the intended length and identity count, so it really is a tie, and that step 2 reads it. The pairs are built in code from a fixed seed, with the mismatches spread inside the sequence so the alignment isn't trimmed. This test catches a future BLAST+ that changes its formula.
4. **A cheap data check in `score()`, every call, before `blastp`.**
   - It checks the BLAST database's `blast.phr`, `blast.pin` and `blast.psq`, that `PAML_RST/` has at least one entry, and `species_pthr8_time.nhx`. That's five `stat`s and one directory read, which is nothing next to a 4-second search. It runs every call, so a mount that goes away after startup is caught too.
   - It runs after the input checks and after the early return for no substitutions, so those behave as before. That return needs no data: `test_no_substitutions_give_no_family_and_nothing_is_searched`.
   - A failure raises `MissingDataError`, a new error in `core/data.py`. It isn't an `InputError`, so the API fails the job with the generic 500 and logs it with its traceback (`jobs/runner.py`). Its message names the data folder and each missing path. It's one string argument, so it pickles back from a worker unchanged.
   - The check is a public function in `panther_engine.csnp`, so the API can call it for readiness later without reaching into `score()`.
   - *Alternative:* check against the full manifest for presence, about 25,800 `stat`s per call. Rejected: developer folders hold the sample, which would fail it, and it's slow on network storage. Proving completeness is `data verify`'s job, at deploy.
   - *Alternative:* treat a hit whose family has no `.paml` as an error. Rejected: parity. Thousands of families have no library files, and the reference reports them as "No PANTHER family".
   - *Alternative:* check at API startup only. Rejected: that's the API's area, and the CLI and a mount lost later would be missed.
5. **A time limit of `(60 s + 0.02 s × residues) × scale`.**
   - Titin took 272 s, about 7.8 ms a residue, and an average protein takes 4 to 6 s. So 20 ms a residue gives titin 747 s, 2.7 times its time, and the API's longest accepted sequence (50,000 residues) 1,060 s. A 400-residue protein gets 68 s.
   - The numbers are provisional. Task 4.1 measures titin and a 50,000-residue query in the engine image and sets the rate so each gets at least 2.5 times its time. It records the times in `docs/testing/engine.md`, which the spec's Titin scenario refers to.
   - Task 4.1 measured 274.6 s for titin and 436.9 s for 50,000 residues, at worst, so the rate is 21 ms. That gives titin 781.4 s, the longest sequence 1,110 s and 400 residues 68.4 s (tasks.md, Notes).
   - `PANTHER_CSNP_BLAST_TIME_SCALE` is read on each call, not at import, so a test can set it and a bad value fails that call. A value that isn't a positive finite number fails before `blastp`, with an error naming the variable.
   - `search()` keeps its `timeout` keyword for tests. Without it, it uses the limit for its sequence.
   - *Alternative:* a fixed, higher limit, such as 900 s. Rejected: a hung search on a short protein would hold one of the server's few workers for 15 minutes. Scaling keeps those to about a minute.
   - *Alternative:* a `score()` keyword that the API passes from its settings. Rejected for now: it changes the interface agreed on #19 and needs the API developer. The variable follows `PANTHER_DATA_DIR`'s pattern, and the API's workers inherit it. The keyword can be added later without breaking callers.
   - *Alternative:* `blastp -num_threads`. Rejected: one job uses one worker and one core (hosting.md), as the legacy did.
6. **The full manifest is committed, at `engine/src/panther_engine/csnp/full.json`, beside `sample.json`.**
   - `verify` then works offline on the server, and the manifest is versioned with the code that reads the data.
   - The data is frozen, so it's written once. It's about 2.6 MB, one file per line in `sample.json`'s format. `.gitattributes` marks it `linguist-generated`, so reviews fold it away, and reviewers check it by rebuilding it, which gives the same bytes.
   - Besides `files`, it records the sha256 of each input it was built from, as `sample.json` does.
   - *Alternative:* a release asset pinned by its sha256, like the sample. Rejected: `verify` would need the network or a copy put on the server by hand, and publishing needs its own go-ahead. All it saves is repository size.
   - *Alternative:* commit it gzipped. Rejected: it can't be diffed or searched, and saves about 1.3 MB of checkout.
   - *Alternative:* pin only the two archives' checksums, which spec §7.1 already does. Rejected: that checks the archives, not the unpacked copy, which is what breaks.
7. **Built by streaming the archives, never unpacking.**
   - `csnp data manifest` reads each archive as a `r|gz` stream, as the survey does. It hashes each regular member and records it at its path under `csnp/9/`: `PAML_RST/<file>` and `blast/blast.{phr,pin,psq}`.
   - It hashes the species tree, and the copyright statement as `copyright_statement()` writes it from the README.
   - Each input's sha256 is checked against the pins `csnp/sample.py` already holds: `PINNED_ARCHIVE`, `PINNED_BLAST`, `PINNED_SPECIES`, and `sample.json`'s entry for `PSEP-COPYRIGHT.txt`. A mismatch writes nothing.
   - `blast.fasta` isn't listed, because `blastp` doesn't read it, so its presence or absence doesn't matter.
   - The generic streaming hash can move into `core` later, as the review's Improvements suggest. This change reuses the survey's.
8. **A `csnp data` command group: `manifest` and `verify`.**
   - `verify` reuses `core.manifest.verify` against `full.json`. It prints the two counts and the first 20 paths of each, and exits 1 if either count is non-zero.
   - *Alternative:* `csnp sample verify --full`. Rejected: the sample and the full data have different manifests. One command for both invites checking a folder against the wrong one.
9. **Status 1 is the input's fault only with a `BLAST query error:` line.**
   - Checked with 2.17.0 in the engine image (2026-11-02):
     - `1234567890` and `MK(VL` exit 1, writing one line: `BLAST query error: CFastaReader: Near line 2, there's a line that doesn't look like plausible data, but it's not marked as defline or comment.`
     - `-bogus_option` and `-best_hit_overhang 0.9` also exit 1. They write BLAST+'s usage text, then two `Error:` lines naming the argument.
   - Any other status 1 raises `BlastError` with the last three lines of standard error, as other statuses do now. For an argument error, those are the `Error:` lines. The API logs a `BlastError` with its traceback, so the cause reaches the log without an API change.
   - The input error's message doesn't change, and still holds no tool output (engine-core, Input errors). Divergence row 8 describes failures of the FASTA reader, so it still holds as written.
   - *Alternative:* match the whole message. Rejected: the text after the prefix names a line number and varies with the input. `BLAST query error:` is BLAST+'s own category.
   - *Alternative:* check the sequence's letters before searching. Rejected: it would change which sequences reach BLAST+, which `scoring-input` and divergence 8 settled.
   - *Alternative:* keep standard error on the input error as an attribute, for the log. Rejected: the API logs only an input error's message, and for a real query error BLAST+'s text adds nothing.
10. **Run `blastp` in the database's folder, with `-db blast`.**
    - BLAST+ splits `-db` on spaces. Checked with 2.17.0 in the engine image (2026-11-02), searching for APOE:
      - an absolute path with a space exits 2;
      - wrapped in double quotes inside the argument, it works, unless the path itself has a `"`;
      - run in the folder with `-db blast`, it works with a space and with a `"`, and gives exactly `blast/APOE.csv`.
    - The folder's path then reaches BLAST+ only as its working folder, which `run_tool` already supports.
    - BLAST+ looks in the working folder before `BLASTDB`, so a `BLASTDB` pointing elsewhere doesn't change the result (checked). If the folder had no database, BLAST+ would fall back to `BLASTDB`. Decision 4's check runs before the search, so the files are there. `search()` itself raises `BlastError`, naming the folder, when `blast/` isn't a folder.
    - *Alternative:* quote the path. Rejected: a `"` in the path still breaks it.
    - *Alternative:* refuse a data folder path with whitespace. Rejected: the working folder handles every path, so there's nothing to refuse.

## Risks / Trade-offs

- [If the legacy BLAST+ computed `100 × n / L`, the new two-decimal value differs from what it printed at lengths that are multiples of 160] → No golden has such a line. It changes a best hit only when two candidate lines for the species round across each other. It's recorded as an open question, not a divergence, because neither formula has evidence for the legacy BLAST+.
- [The limit's defaults come from a laptop core, not the server's] → `PANTHER_CSNP_BLAST_TIME_SCALE`. #34's runbook measures titin on the server.
- [Long jobs on a public API: the largest accepted query may hold a worker for about 18 minutes] → Today such a query fails at 300 s, so the new limit lets jobs run that used to fail. Capping the queue is API-2, and the API developer may choose a lower sequence limit (proposal, Open Questions).
- [`verify` hashes 19.2 GB, which takes minutes] → It runs at deploy, not at startup. Task 6.4 records the time.
- [A later BLAST+ changes the `BLAST query error:` prefix] → Unreadable queries would then fail with a 500 instead of a 422: wrong, but loudly. The `tools` test `test_a_query_blastp_cant_read_is_an_input_error` fails on the upgrade.
- [BLAST+ falls back to `BLASTDB` when its working folder has no database] → The data check runs first (decision 4), and `search()` refuses a missing `blast/` folder.
- [A 2.6 MB generated file in the repository and the package] → Once, for frozen data. It's folded away in reviews.
- [The variable overrides a caller who wants reports] → Intended. Nothing in this service needs them.

## Migration Plan

- **Developers:** nothing to do. The sample doesn't change, and no setting is needed.
- **The first deploy (#34):** install the full data as `docs/testing/engine.md` says, run `panther-engine csnp data verify`, and set `PANTHER_CSNP_BLAST_TIME_SCALE` if titin takes more than 40% of its limit there.
- **Rollback:** revert the change. Nothing is migrated, and the API and the data don't change.

## Open Questions

- **The legacy BLAST+'s identity formula** (proposal). It can't be checked without the legacy BLAST+ or its output at a tie. Answering it later changes nothing here unless it's `100 × n / L`. Then the ranking value would need its own formula again, with a test.
