# Design

## Context

**The design decisions this change relies on:**

- **[tech-stack.md](../../../docs/design/tech-stack.md):**
  - the engine's layout, with `core/` first, and "`core`'s HMMER runner";
  - parity tests before porting, with the reference container as a test oracle;
  - pinned tools, and HMMER 3.4 giving production's numbers on amd64;
  - `pantherScoring` being private, so the reference image builds from a developer's checkout.
- **[add-hmmscore-job](../add-hmmscore-job/design.md):**
  - the result, decision 2: `hit` or `null`, with five strings, and the alignment unescaped;
  - the engine interface, decision 4, approved by the engine developer on #70;
  - the settings, decision 5: 10,000 residues, 720 s, one running at once, `--cpu 0`.
- **[add-hmmscore-survey-and-sample](../add-hmmscore-survey-and-sample/design.md):**
  - the library's layout and fetch;
  - the data sample, `hmmscore-sample-1`: 14 whole families, cut from `binHmm.h3m` and pressed by HMMER 3.4;
  - the full library keeping its shipped pressed files.
- **The legacy pipeline:**
  - [hmmscore-legacy-behaviour.md](../../../docs/parity/hmmscore-legacy-behaviour.md), with its quirk IDs and proposed golden inputs;
  - the survey's [What It Means for port-hmmscore](../../../docs/parity/hmmscore-library-survey.md#what-it-means-for-port-hmmscore).

**What exists:**

- **`hmmscore/` holds the data and survey code:**
  - `legacy.model_id` and `legacy.names_key`, which read IDs and `names.tab` keys as the Perl did;
  - `library.read_names` and `library.path_of`, the CGI's model file for an ID;
  - `data.VERSION`, `"19"`.

  There's no scoring, no `__init__` export and no `score` command.
- **`core/`** has `run_tool`, which runs a program with an argument list, no shell, a timeout, and byte-for-byte `stdout` to a file. It also has `InputError`, `service_folder` and `MissingDataError`. It has no work-folder helper. Callers use `tempfile` directly.
- **The legacy code is at `pantherScoring` `89ea0ae`**, read-only in `../panther-workspace`.

## Goals / Non-Goals

**Goals:**

- Every field of a hit traces to a line of `scoreAlignXml.cgi` or `pantherScore.pl`, or to an approved or proposed row.
- The goldens are production's answers: the CGI and `pantherScore.pl`, with HMMER 3.1b2, on amd64.
- `score()` is what the wiring calls, unchanged from decision 4.

**Non-Goals:**

- The wiring: the `501`, the API's data check and version, and passing the settings.
- The hosting server's values (#68).
- All hits, InterProScan output and batch scoring, which `pantherScore.pl` has and the CGI never used.
- `alignOnTheFly.cgi`.
- A shared work-folder helper in `core/`, which `core/__init__.py` promises. That's a refactor for every service.

## Decisions

### 1. The interface, as decision 4

`panther_engine.hmmscore` exports these:

- `DATA_VERSION`, which is `data.VERSION`;
- the frozen dataclasses `HmmscoreInput(sequence)`, `HmmHit(panther_id, name, evalue, score, alignment)` and `HmmscoreResult(hit)`;
- `score(request, *, data_dir=None, cpu=0, timeout=None)` and `check_data(data_dir=None)`;
- `HmmscoreError`, for failures that aren't the input's.

The order follows `csnp`'s `score()`:

1. A `ValueError` for a sequence the API never sends. That's one that isn't upper-case letters, `.`, `_`, `~` and `*`, or that has no letter.
2. Then `check_data()`.
3. Then the search.

The engine doesn't apply the residue limit, because it's the API's setting (decision 7).

*Alternative:* return the tied set and let the API pick. Rejected: the rule is scoring's, and the contract has one `hit`.

### 2. The steps, line by line

| Step | Legacy | Port |
| ---- | ------ | ---- |
| Query file | `>sequence\n` and the posted text, no final newline (`scoreAlignXml.cgi` 93 to 105) | The same bytes, in the search's folder. The name is in the alignment (`>> sequence`), so it must match |
| Search | `hmmscan --domtblout /tmp/temp.domtblout <lib>/globals/binHmm <query> > /dev/null`, status ignored (`pantherScore.pl` 376 to 381) | `hmmscan --domtblout <folder>/hits.domtblout --cpu <cpu> <data>/globals/binHmm <query>`, `stdout` discarded, status checked |
| Table | Skip `#` lines, split on whitespace; target 0, E-value 6, score 7; ID by 387 to 389 (383 to 399) | The same columns, as strings, split on Perl's whitespace, `[ \t\n\r\f\v]`, not Python's `\s`, which also matches `\x85` and `\xa0` in Latin-1 text; the ID by `legacy.model_id` |
| Best hit | `getBestHit` (316 to 340) | Decision 3 |
| Name | None in the CGI (`HMMSCORE-2`) | `library.read_names` on `globals/names.tab`, or "No name" for an ID it has no line for or an empty name. `pantherScore.pl -n` printed an empty name for both, so the goldens can't tell them apart |
| Alignment | `hmmsearch <model file> <query>`, status ignored, kept from after "Domain annotation for each sequence" to before "Internal pipeline statistics summary:", with `>` and `<` escaped (`scoreAlignXml.cgi` 133 to 154) | `hmmsearch --cpu <cpu> <data>/<library.path_of(id)> <query>`, `stdout` to a file byte for byte, status checked, the same lines, unescaped |

- **The tables are read as bytes, decoded as ASCII.** That avoids port-refmap's lesson: text-mode capture rewrites CR.
- **`names.tab` is read on each call.** That's about 145,000 lines, small beside `hmmscan`'s seconds. A cache can come later, with a measurement.

### 3. The best hit and ties

`getBestHit` keeps the strings as printed, and compares them as numbers:

1. the highest score;
2. for that score, the smallest E-value;
3. every ID with both.

Then `next if ($bestEval > $cutoff)`: no hit if that E-value is over 1e-3, so exactly 1e-3 is kept. The port does the same with `float` of the printed strings.

**Ties** are divergence 13:

1. Drop a family's ID when one of its own subfamilies is among the tied IDs.
2. Take the lowest by family number, then subfamily number. A family's own ID counts as subfamily 0.

**Two `binHmm` models with one ID,** such as `PTHR34093.pir` and `PTHR34093..pir`, are one ID, as in the Perl's hash. Two different strings for one number can't occur: `hmmscan` prints each column in one format.

### 4. The time limit, threads and failures

- **One deadline for the whole search.** It starts when `score()` does. `hmmscan` gets what's left of it, then `hmmsearch` gets what's left after that.
  - `run_tool`'s `subprocess.TimeoutExpired` kills the tool. The port then raises `InputError` with decision 4's message.
  - It's an input error, unlike `csnp`'s BLAST time limit, because the submitter can shorten the sequence (`add-hmmscore-job`, decision 4).
- **`--cpu`** goes to both tools. 0 runs no worker threads, the least memory (the survey).
- **Failures are `HmmscoreError`:**
  - a non-zero exit;
  - a missing table or report;
  - a report with no "Domain annotation" line;
  - a hit's model file that's missing.

  The API reports them as the generic `500`. The reference ignored both statuses. For inputs that's `HMMSCORE-8`, which row 12 covers. For the rest it's the new `HMMSCORE-11`.
- **The folder** is a `tempfile.TemporaryDirectory` per call. That's never `/tmp/temp.domtblout` (`HMMSCORE-7`), so concurrent jobs can't read each other's tables.

### 5. HMMER runners in `core/`

`core/hmmer.py` adds `hmmscan(database, query, *, table, cpu, timeout, cwd)` and `hmmsearch(model, query, *, report, cpu, timeout, cwd)`.

- Both are thin layers over `run_tool`, finding the program as `core/tools.py` does.
- They write the table or the full text report to a file. `tech-stack.md` asks for both outputs, so `treegrafter` can reuse them.
- They return the finished process, as `run_tool` does. Checking its exit status is the caller's job; `score()` puts the end of its standard error into the error, for the log.
- **Beside them in `core/`:**
  - `run_tool` takes `timeout=None`, for `score()` with no time limit, and `environment`, variables set over the caller's, for the CGI's `REQUEST_METHOD` and `CONTENT_LENGTH`;
  - `read_protein` moves from `csnp`'s command line to `core/fasta.py`, since `hmmscore score` reads one protein the same way.

*Alternative:* call `run_tool` from `hmmscore/` directly. Rejected: `tech-stack.md` puts the HMMER runner in `core/`.

### 6. The reference image

**Two test-only stages in the root `Dockerfile`:**

- **`hmmer-3.1b2`** is `FROM quay.io/biocontainers/hmmer:3.1b2--3@sha256:e7b1a7a1…`, the survey's digest, which the 2026-11-13 character measurements also used. The reference stage copies `hmmscan`, `hmmsearch`, `hmmpress` and `hmmconvert` from it into `/opt/hmmer-3.1b2/bin/`.
  - They link only glibc's `libc`, `libm` and `libpthread` (checked 2026-11-16), so they run on Debian.
  - `hmmscore-reference` runs each tool's `-h` once they're copied, and checks that it reports 3.1b2, which also shows that they run on Debian.
- **`hmmscore-reference`** is `FROM engine` and is amd64 only, since 3.1b2 has no arm64 build with vector code. It adds:
  - Debian's `perl` and `libyaml-libyaml-perl`, which provides YAML::XS for the CGI's `config.yaml` (18);
  - the scripts in `/opt/hmmscore-reference/`.

**The scripts come from a named build context, `hmmscore-reference-scripts`.** It's a `git archive 89ea0ae scoreAlignXml.cgi pantherScore.pl lib` of the developer's checkout, as for `csnp`. Each file is pinned with `sha256sum --check --strict`.

**3.1b2 reads its own presses of the sample,** as in the survey's task 10.1:

- `hmmconvert` turns the sample's `binHmm.h3m` back to text, and 3.1b2's `hmmpress` presses it into the run's `globals/`.
- `names.tab` and `books/` are linked beside it, because `FamLibBuilder::exists` needs both folders.
- On the full library, it reads the shipped pressed files, as the survey's 3.1b2 did.

**`panther-engine hmmscore parity reference` runs each case in a fresh folder, one at a time.** One at a time matters because `pantherScore.pl`'s table path is fixed (`HMMSCORE-7`). For each case, it:

1. writes the CGI's `config.yaml`. `library_directory` is the data folder. `binHmm_library_directory` is the 3.1b2 presses. `tmp_directory` is the run's folder. `hmmer_bin_directory` is `/opt/hmmer-3.1b2/bin`;
2. runs `scoreAlignXml.cgi` in the case's folder, which holds the `config.yaml` and links to the scripts, since the CGI finds them by relative path, with `REQUEST_METHOD=POST`, `CONTENT_LENGTH`, and `sequence=<posted>` on standard input. It checks that the CGI printed its `Content-type` header and a blank line, and saves the rest as `cgi.xml`, so no hit is `<scores>\n</scores>\n`;
3. runs `pantherScore.pl -l <presses> -D B -n -i <query> -o best.tsv -H /opt/hmmer-3.1b2/bin`. `-n` adds the Perl's names, and the file lists every tied best ID, where the CGI reads only the first line (117 to 161);
4. runs the CGI's `hmmsearch` command for each ID in `best.tsv`, and saves it as `hmmsearch/<ID>.out`, with the ID's `:` as `.`, such as `PTHR18976.SF2.out`, since Windows can't hold `:` in a file name.

Each run writes to a temporary folder, then moves the outputs into place, as `refmap parity reference` does.

**Self-check:** before the cases, APOE on the sample must give `PTHR18976:SF2` at 439.0 bits, as the survey and `sample-hmmscan/amd64/apoe.domtblout` say. That catches an image that reads the sample wrongly.

*Alternatives:*

- **3.4 in the reference, as `csnp`'s uses the runtime BLAST+.** The engine developer chose 3.1b2 on 2026-11-16, so the goldens are production's.
- **Building 3.1b2 from its source tarball** (the survey's `dd16edf4…`, `CFLAGS="-O3 -fcommon"`). That's the fallback if the Bioconda tools don't run in the stage.

### 7. The cases and the goldens

They live in `engine/tests/golden/hmmscore/parity/`, stored byte for byte:

- **`cases.json`:** each case's name and why it's there. The engine's sequence is in `inputs/<case>.txt`. A case also has the CGI's `posted` text, when that differs from the engine's.
- **`sample/<case>/`:** the reference on the data sample, amd64. That's `cgi.xml`, `best.tsv` and `hmmsearch/`.
- **`full/<case>/`:** the same on the full library, from the staging run (decision 9).

**The expected result** is derived from the reference's files:

- If `best.tsv` is empty, there's no hit, and `cgi.xml` must be `<scores>\n</scores>\n`.
- Otherwise:
  - the tied IDs are `best.tsv`'s lines, and decision 3's rule picks one;
  - its name, E-value and score come from that line;
  - its alignment comes from `hmmsearch/<ID>.out`, by the CGI's rule.
- **Cross-checks:**
  - `cgi.xml`'s `<id>` and `<eval>` are one of `best.tsv`'s lines. Not necessarily its first: the CGI and `pantherScore.pl -n` are two runs of Perl, with two hash orders, so a tie can come first in one and second in the other;
  - its `<align>`, unescaped, equals the alignment from that ID's report.

**The cases,** from `hmmscore-legacy-behaviour.md`'s Golden Inputs, plus a few more:

| Case | Sequence | Why |
| ---- | -------- | --- |
| `apoe` | `example/apoe.fasta` | The site's example |
| `test` | The release's `test.fasta`, from `data.pantherdb.org`, sha256 `097bbf0c…` | The release's own query: 773 models in 56 families |
| `tie-pthr35774` | PTHR35774's consensus, `hmmemit -c` of its family model by 3.4 | `HMMSCORE-1`, divergence 13 |
| `pir-pthr34093` | The consensus of `PTHR34093..pir` | `HMMSCORE-9`: the alignment comes from another model's file |
| `no-hit` | A short repeat of one letter, with no row in the table | `hit: null` |
| `over-cutoff` | A fragment of APOE whose best E-value is over 1e-3 | No hit, though the table has rows (`HMMSCORE-5`) |
| `best-over-cutoff` | 12 residues of `PTHR24068.SF460.pir`'s consensus, found by searching the sample | `HMMSCORE-5`: the best model, SF508 at 0.0012, is over 1e-3 beside a lower-scoring one under it, SF502 at 0.0009, so no hit |
| `apoe-lower` | APOE in lower case. The CGI gets it lower-case; the engine gets it upper-cased, as from the API | Upper-casing changes nothing |
| `apoe-stop` | APOE with a final `*` | A final stop |
| `apoe-uncommon` | APOE with `B`, `J`, `O`, `U`, `X` and `Z` at fixed positions | The uncommon letters |
| `apoe-dot`, `apoe-underscore`, `apoe-tilde`, `apoe-star` | APOE with three of the character, after residues 80, 160 and 240, as measured on 2026-11-13 | What `add-hmmscore-job` left for the goldens: 3.4 scores them as 3.1b2 did, on PANTHER's models |
| `titin-10000` | The first 10,000 residues of UniProt Q8WZ42, from the FASTA the survey pinned (`2bb79b40…`) | The residue limit (row 11), and the timing (decision 9). No family of titin's is in the sample, so it has no hit there |

`HMMSCORE-5`'s best hit over 1e-3, beside a lower-scoring hit under it, turned up once in a search of 110,991 windows of the sample's consensus sequences, APOE and `test.fasta`: `best-over-cutoff`. 3.1b2 and 3.4 give it the same rows. Hand-written tables test the rule too.

### 8. The parity tests and the architectures

- **Unit tests, with no marker,** use hand-written `--domtblout` tables and saved `hmmsearch` reports. They cover:
  - the columns, the IDs, score before E-value, and the cutoff at and over 1e-3;
  - ties, the alignment's lines, and "No name";
  - `ValueError`s;
  - the time limit and failures, with `make_tool`'s fake tools.
- **`tools("hmmscan", "hmmsearch")`** runs the real HMMER on the fixture library, `PTHR99999`.
- **`tools(…)` with `data("hmmscore")`** runs every sample case against its golden. Both `engine-image` legs run it.
- **amd64 is the parity target.** The reference is amd64 only, and on arm64 HMMER 3.4 can differ in a last digit (the survey). A case whose arm64 result differs gets an arm64 copy of its expected result, `sample-arm64/<case>.json`, made by the port. The README lists what differs, as `sample-hmmscan/` does. The first run needed none: every sample case gave its amd64 result on arm64 too.
- **`panther-engine hmmscore parity check [--goldens sample|full]`** uses the same comparison as the tests. It prints each case that differs and each case's time, and exits non-zero on a difference.

### 9. The staging run, and the time limit

This is the M1 acceptance for hmmscore's engine, on any amd64 machine that has the full library and the reference image:

1. `parity reference` on the full library, then commit `full/`;
2. `parity check --goldens full`;
3. record it in `docs/parity/inputs.md`, as `refmap`'s full run is.

Then, in fresh processes, `panther-engine hmmscore score --usage` times `titin-10000` and APOE at `--cpu 0`. It reports the wall time and the tools' peak memory, from the kernel's accounting of child processes, on standard error, so `--json` stays one object. The results go on #68, and in the survey doc's timing section.

Decision 5 put 720 s at three times an estimate of 240 s. If `titin-10000` takes more than 240 s, the comment on #68 proposes a new default, for the API developer.

## Risks / Trade-offs

- **[The Bioconda 3.1b2 tools may not run on Debian]** → They need only glibc's `libc`, `libm` and `libpthread`. The stage runs `hmmscan -h` when it's built. If it fails, the stage builds 3.1b2 from the survey's source tarball (decision 6).
- **[The two versions press the sample differently]** → Their `.h3p` files differ in 4,653 bytes, which changed no table for APOE or `test.fasta` (the survey). If a sample case differs only for that reason, the README says so, and the full library, which both versions read from the same shipped files, settles it. It isn't a row.
- **[The reference picks ties at random]** → The goldens keep `pantherScore.pl`'s whole tied set. The check applies divergence 13, and requires only that `cgi.xml`'s pick is among the tied IDs.
- **[An accepted query runs past the time limit]** → It would get an error where the reference answered. The limit is the API's setting, passed by the wiring. Decision 9 checks that the default covers 10,000 residues.
- **[Emulated amd64 on a Mac is slow]** → The sample cases are small. The staging run uses a native amd64 machine.
- **[The full library needs 67 GB on disk]** → It's for the staging run only. CI and developers use the 33 MB sample.

## Migration Plan

This is additive: nothing calls `score()` until the wiring change does. Rollback is a revert. The wiring then:

- removes `UNAVAILABLE`'s hmmscore row and `run_job`'s `NotImplementedError`;
- calls `score()` with `hmmscore_time_limit_seconds` and `hmmscore_cpu`;
- adds `check_data()` to the API's startup checks, and `DATA_VERSION` to its versions.

## Open Questions

- **Production's thread count** needs team verification. It doesn't affect parity (proposal, Open Questions).
