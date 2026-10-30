# Design

## Context

See proposal.md for why. This change follows these decisions and doesn't revisit them:

- [tech-stack.md](../../../docs/design/tech-stack.md):
  - **Engine conditions:** 1 (a library with a CLI); 2 (`core/` first, one submodule per service); 3 (parity tests before porting, with a reference image as the test oracle); 4 (tools as binaries, through `subprocess`); 6 (never replicate `CGI-5` or `CGI-6`; fix plumbing freely); 7 (the code's thresholds and pDel bounds for M1).
  - **Pinning Tool Versions:** BLAST+ 2.17.0, and its 3-decimal `pident`.
  - **Shared Concerns:** the cSNP data under `csnp/9/`, the sample on developer machines and in CI, the full comparison on staging.
- [api-stack.md](../../../docs/design/api-stack.md): the tooling (uv, Ruff with the `S` rules, basedpyright strict, pytest).
- **The interface,** agreed with the API developer on #19 ([`add-csnp-job` design](../archive/2026-10-29-add-csnp-job/design.md)):
  - `score(CsnpInput) -> CsnpResult`, frozen dataclasses, one protein per call;
  - the input already normalised by the API;
  - `pdel` a two-decimal string;
  - "No PANTHER family" and "Invalid substitution" are result rows.
- **`InputError`'s contract:** [`add-job-input-errors` design](../add-job-input-errors/design.md). Its task group 1 lands here.
- **What the Perl reads, and where the strict readers agree with it:** [csnp-library-survey.md](../../../docs/parity/csnp-library-survey.md). They agree everywhere except the start column (`SCORE-2`) and 14 files in 7 broken families.

What the engine has, from `add-csnp-survey-and-sample`:

| Module | What it does |
| ------ | ------------ |
| `core/process.py` | `run_tool()`: an absolute program path and an argument list, no shell, output captured |
| `core/data.py` | `service_folder("csnp", "9")` |
| `csnp/paml.py`, `rst.py`, `orig_tree.py`, `species.py` | The strict readers. `paml.read_site` reads one site per pass |
| `csnp/legacy.py` | The Perl's own readings: `start_node`, `find_an` and `GeneLookup`, `sequence`, `events` |
| `csnp/sample.py` | The data sample: build, fetch, verify |

The test suite has the `tools` and `data` markers, and a `make_tool` fixture that writes fake programs.

The legacy pipeline, per request (spec §4): `snpScore.cgi` writes `>P0001\n<sequence>` and one `SNP_<n>|P0001|<pos>|<WT>;<MUT>` line per token. Then:

```text
blastp ---------> BLAST csv -----> parse_blastp.pl -----> snpParse csv ----> PANTHER_PSEP1.01.pl ----> result csv
 (step 1)          15 fields        (step 2: sort, filter,  8 fields          (step 3: gene, column,     6 or 3 fields
                                     best hit, map)                             walk, age, message, pDel)
```

## Goals / Non-Goals

**Goals:**

- Byte-for-byte the legacy output at each step boundary, so the §7 goldens and the reference image's output compare as text, not as parsed values.
- One scoring call reads each library file once, holds none of a `.paml` beyond the sites it needs, and writes nothing to disk.
- The oracle can run the same cases on the full library on staging, with no code change.

**Non-Goals:**

- **Speed beyond the legacy's.** Reading a `.paml` up to the last needed site is acceptable for M1. The legacy took about 10 s for `PTHR10366`. Indexing is a later change, if staging shows a need.
- **A general BLAST output parser.** Only the 15 fields of the legacy `-outfmt` line.
- **Batch scoring across proteins.** One protein per call, as the CGI did. A batch is a loop of calls.

## Decisions

### 1. Steps as functions over the legacy's own records

Each step is a function whose input and output are the legacy's records, as text:

- **Step 1** returns the BLAST CSV lines exactly as `blastp` wrote them.
- **Step 2** takes those lines and SNP records (`snpId`, `proteinId`, position as written, `WT`, `MUT`), and returns snpParse records.
- **Step 3** takes snpParse records and a library folder, and returns result records: `snpId, subst, family, age, message, pDel`, or the 3-field "Not scored" form.

`score()` only joins them:

- it builds `SNP_<n>|P0001|…` records from the tokens;
- it runs the three steps;
- it turns each result record into a `SubstitutionScore`. An empty age becomes `None`; a "Not scored" row has `None` age and pDel.

Why: the goldens sit at these boundaries. `HUMAN` is step 1's output, and §7.3 and §7.5 are step 3's. The reference image runs steps 2 and 3 as separate scripts. Comparing records as text catches formatting differences, such as `0.50` against `0.5`, or an empty age against `0`, that a comparison of parsed values would miss.

*Alternative:* one function from sequence to `CsnpResult`, tested only end to end. Rejected: §7.5's edge cases (`e5`'s extra residue, `e7`'s lower-case WT, `e10`'s CRLF) can't be expressed through the API's validated input, and every step-3 golden would then need BLAST.

### 2. Module layout

```text
engine/src/panther_engine/
  core/errors.py        InputError (add-job-input-errors, group 1)
  core/process.py       run_tool(..., input=None, cwd=None): stdin text and a working folder
  csnp/__init__.py      exports score, CsnpInput, CsnpResult, SubstitutionScore, SPECIES_CODES
  csnp/scoring.py       the dataclasses and score()
  csnp/codes.py         SPECIES_CODES: the 85 codes, sorted, as a literal
  csnp/blast.py         step 1: run blastp, read its lines; BlastError for failures that aren't input errors
  csnp/hits.py          step 2: rank, filter, best hit, map positions
  csnp/psep.py          step 3: gene, column, .paml sites, tree, ages, walk, message, pDel
  csnp/parity.py        generate cases, run the Perl, compare
  csnp/cli.py           + `score` and `parity`
  csnp/paml.py          + read_sites(lines, name, sites): several sites in one pass
```

`codes.py` isn't `species.py`, which reads the species tree.

### 3. Step 1: `blastp` through stdin and stdout

- **The arguments:** `-db <csnp/9>/blast/blast`, then the legacy `-outfmt '10 qseqid sseqid pident length mismatch gapopen gaps qstart qend sstart send qseq sseq evalue bitscore'`, then `-best_hit_overhang 0.1 -best_hit_score_edge 0.1`. There's no `-query` (stdin), no `-out` (stdout) and no `-num_threads`, as in the legacy.
- **The query:** `>P0001\n<sequence>`, with no newline after it, as `createFasta` wrote it. The name matters: step 2's species filter matches anywhere in the line (decision 4), and `P0001` is in every line.
- **No file is written,** so there's nothing to share between requests (`CGI-6`) or clean up. `run_tool()` gains `input=` for stdin.
- **Exit status:**

  | Status | What `score()` does |
  | ------ | ------------------- |
  | 0 | Parse the lines |
  | 1 | The query couldn't be read: raise `InputError` (divergence 8) |
  | Anything else, a timeout, or no `blastp` on `PATH` | Raise `BlastError`, so the job fails with the generic `500` |

  A sequence that starts with `!`, `#` or `;` never reaches `blastp`: its FASTA reader takes the line for a comment, finds no sequence, and exits with 3 ("Sequence contains no data"), an engine error. `search()` raises the same `InputError` first (divergence 8; found in apply, decided by the engine developer on 2026-10-30).

  The `InputError` message is written once apply has found which inputs make `blastp` 2.17.0 exit with 1. It never quotes BLAST+'s stderr.
- **Timeout:** a module constant, 300 s. The search takes seconds against the 570,173 sequences.

*Alternative:* a per-job temporary folder in `core/`, as tech-stack.md's condition 2 lists. Not needed for `csnp`: stdin and stdout carry everything. It stays available for a later service that needs files.

### 4. Step 2: the legacy sort, filter and mapping, emulated

- **Filter (`MAP-2`):** keep the lines in which the species code occurs anywhere, as `grep '<species>'` does: a case-sensitive substring of the whole line, the aligned sequences included.
- **Rank (`MAP-1`):** emulate `sort -t, -k1,1 -k3nr,3` in the C locale:
  - by `qseqid`;
  - then `pident` descending, as a number;
  - then, as `sort`'s last resort, the whole line compared byte by byte.

  BLAST+ 2.17.0 writes `pident` with 3 decimals, where the legacy BLAST+ wrote 2 (tech-stack.md, Pinning Tool Versions). So `pident` is recomputed as `100 × (length − mismatch − gaps) / length` and formatted with `%.2f`, as the old BLAST+ printed it. The 2-decimal value replaces the 3-decimal one in the line used for ranking and the tie-break. A recomputed value that doesn't round to the 3-decimal one fails with `BlastError`, so a wrong formula can't pass silently. The `HUMAN` fixture's 2-decimal values check it.
- **Best hit:** the first ranked line per `qseqid`, as `readBLASToutput` keeps it.
- **Family and gene (`MAP-3`):** split `sseqid` on `:`. The second field is the family, the first is `ANinfo`.
- **Mapping:** a line-for-line port of `getCorrectPosition`, `MAP-4` included:
  - a `qseq` character counts as a residue when it's `A`–`Z`, and as a gap when it's `-`;
  - the count starts at `qstart`;
  - the break test comes after the increment;
  - `mappedPos = sstart + num - 1 - (gaps in sseq up to num)`.

  The position is compared as a number, so `010` maps as `10`, but it's echoed as written.

### 5. Step 3: the Perl's order, with lenient reads before strict ones

Per snpParse record, in `PANTHER_PSEP1.01.pl`'s order (`SCORE-1`):

1. **The family's files.** The family field must name a `.paml` in the library, else "No PANTHER family". A family field that isn't a `PTHR` family name, such as `AN12345` or anything with a `/`, counts as missing. The legacy's file test would fail for those too.
2. **`mappedPos`** must contain a digit, else "Invalid substitution".
3. **The gene's AN:** `legacy.GeneLookup`, the Perl's open-ended pattern (`SCORE-8`).
4. **The gene's sequence and column:** `legacy.sequence`, the Perl's flip-flop over the `.rst`. Then a literal port of `getCorrectnum`'s loop: it counts `-` and `A`–`Z` matches, but indexes the string by position, as the Perl does. If the character found isn't `WT`, the result is "Invalid substitution".
   - **This is what keeps the broken families harmless.** All 7 have no sequence list in their `.rst`, so they stop here, before any strict reader sees their broken `.paml`, exactly as the Perl does.
5. **Only now the strict readers:**
   - the `.paml` header;
   - the needed sites, through `read_sites`, in one pass;
   - the `.rst` branch list and tree line;
   - the species tree.

   Then the rest of the Perl's readings:
   - **the start column:** `legacy.start_node` (`SCORE-2`), the one reading that differs;
   - **events and taxa:** `legacy.events`. Only `Ev=<d>><d>:S=<taxon>:ID=AN<n>` counts, so `Ev=UNK` roots have no event;
   - **nodes paired with ANs** by order of appearance, the strict tree line's nodes zipped with the `.orig.tree` ANs.

   A strict reader that fails here raises `LibraryFormatError`, a `500`. The survey found no accepted family where that can happen.

**The walk** follows spec §4.3:

- Each node's cell is `residues[y - 1]` and `probabilities[y - 1]` at site `col`. "Kept" means `probability > 0.99`, which is false for NaN, and `residue == WT`.
- Parents come from the `.paml` header.
- A start column of `None` gives an empty age, as the Perl's column 0 does.
- A site past the file's last site counts as not kept.

The survey found no family where either of the last two can happen. Both are written so they match the Perl if one ever does.

**Ages (`getYear`):**

| Event | Age |
| ----- | --- |
| Leaf (column below the root) | 0 |
| `0>1`, taxon in the species tree | The taxon's age |
| `1>0`, or a taxon the species tree lacks (`DATA-3`) | Over the children in `1..I` other than itself: the largest child age + 1, where an empty child age counts as 0. Capped at 4200; empty with no child |
| Anything else that matches `\d>\d`, such as `0>0` with a known taxon | Empty |

- **The last row is the Perl falling through `getYear`'s `if` chain.** It returns Perl's false value, which prints empty and counts as 0. Spec §4.4 says these nodes are aged as duplications. The code says otherwise, so the generated cases include nodes of every event kind, and the reference image's output decides.
- **`I` is the family's tree-node count.** With one family per call, the Perl's stale `$i` (`SCORE-7`) has no effect.
- **Children come from the `.rst` branch list,** as the Perl's `%child_mother`.
- **Ages are computed iteratively and memoised,** so a deep tree can't hit Python's recursion limit.

**Message and pDel:** 180 / 380, and the `age < bound` table (spec §4.5), with an empty age as 0. pDel is the table's string.

### 6. `score()`: what it checks, and the result

- **Before anything is searched:** the species code must be in `SPECIES_CODES`, the sequence must be non-empty printable ASCII with no whitespace, and each token must match `[A-Z][0-9]+[A-Z]`. Anything else is a `ValueError`. The API rejects all of these first, so only a bug can reach it (#19).
- **The data folder:** `PANTHER_DATA_DIR`, or a keyword-only `data_dir` for tests. The keyword doesn't change the agreed call.
- **`family`:** the first snpParse record's family field, cut with the CGI's `s/(PTHR[0-9]+).*/$1/`, or `None` when it's empty.

### 7. The species codes

`SPECIES_CODES` is a literal frozenset of 85 codes, read once from the PANTHER9 BLAST database: the first `|` field of each `sseqid`. A test marked `tools` and `data` lists the sample database's titles with `blastdbcmd` and checks they give exactly these codes.

*Alternative:* read them from the database at import time. Rejected: the API checks membership at submit time, in a process that has no data folder.

### 8. `csnp-sample-2`

- **`sample build`** gains `--blast-archive`. It checks that archive against spec §7.1 (`2cf4428c…`), then copies `blast/blast.phr`, `.pin` and `.psq` to `csnp/9/blast/`, the layout that `tar -xzf PANTHER9.blast.tar.gz -C <root>/csnp/9/` gives the full data. The extra `blast.fasta` there is harmless.
- **The manifest** records the BLAST archive's name and sha256 beside the PAML archive's.
- **Same tarball rules** as `csnp-sample-1`. A new tag and a new asset; `csnp-sample-1` stays for old commits.
- **CI:** nothing to change. The cache key is the manifest's hash, and `fetch` and the `data` marker read the file list from the manifest.

### 9. The reference image

A `csnp-reference` stage after `engine` in the root `Dockerfile`:

```text
FROM engine AS csnp-reference
  apt: perl                                  (Debian's; Getopt::Long is core)
  COPY --from=csnp-reference-scripts         run_blastp.pl parse_blastp.pl PANTHER_PSEP1.01.pl
       -> /opt/csnp-reference/
  sha256sum --check --strict                 the three pins, taken from cebb5ab on 2026-10-29:
                                             5368a43c…, e19ecf1a…, b931ff66…
```

- **`csnp-reference-scripts` is a named build context:** a folder that `git archive cebb5ab` extracts from the developer's `cSNP_analysis` checkout. `docs/parity/golden-setup.md` gives the commands. The checkout is only read, so `panther-workspace` stays untouched.
- **Building `engine` or `api` never needs the context,** so compose and CI are unaffected.
- **Built `FROM engine`,** so Perl, the scripts and the Python harness are in one container. The `api` stage gets neither the scripts nor Debian's `perl` package. Like every image from the Python base, it has Debian's Essential `perl-base`, which `dpkg` won't remove; the engine developer accepted it (2026-10-30).
- **The species tree** comes from the data folder (`csnp/9/species_pthr8_time.nhx`, the same sha256 as `cebb5ab`'s). Each Perl run gets a fresh working folder with a link to it, because `PANTHER_PSEP1.01.pl` opens the file by relative path (`RUN-1`) and `parse_blastp.pl` writes `./<species>` (`MAP-2`).
- **Self-check first:** before generating anything, the image must reproduce spec §7.3 and §7.5 byte for byte from their inputs. That catches a Perl version that reads the scripts differently.

### 10. Parity cases and goldens

```text
engine/tests/golden/csnp/
  README.md                 where each file came from, its sha256, the PSEP copyright statement,
                            how to regenerate
  release/                  HUMAN, sample.input, sample.fasta (PSEP 1.01 release)
  spec/                     §7.3 output; §7.5 input and output (e10 keeps its CRLF)
  blast/                    step-1 output of BLAST+ 2.17.0 for the three sample proteins
  generated/                step-2 cases and outputs; per family, step-3 cases and outputs
```

- **Step-3 cases**, per family:
  - a `random.Random` seeded with `<seed>:<family>` chooses genes from the `.orig.tree` gene lines, 5 by default;
  - for each gene, it chooses 8 positions: valid residues, a wrong wild type, one past the sequence end, and both ends of the sequence;
  - each family also gets a "no family" row and an unmapped row.

  Cases are grouped by gene, because the Perl re-reads the `.paml` whenever the AN changes (`SCORE-11`). That keeps `PTHR11695`'s 136 MB to 5 reads. The genes chosen cover leaves whose walk passes nodes of every event kind the family has.
- **Step-2 cases:** a listed set of alignments, plus seeded random ones:
  - gaps on either side, `X`, and start offsets;
  - a position at `qstart`, after a gap, and past `qend`;
  - tied identities and species substrings, written as BLAST lines.

  All of them go through `parse_blastp.pl` in the image, with GNU `sort` in the C locale.
- **`panther-engine csnp parity`:**
  - `cases` generates;
  - `reference` runs the Perl, one process per family, and writes outputs (reference image only);
  - `check` runs the Python and diffs.
- **The pytest golden tests** call the same comparison functions as `check`, against the committed goldens. CI never runs Perl.
- **On staging,** `parity cases` and `parity reference` on the full library, then `parity check`, are the M1 acceptance run. Its report goes in `docs/parity/`.

### 11. Tests

| Marker | What's tested |
| ------ | ------------- |
| None | Hand-written fixtures: steps 2 and 3 on the `tests/fixtures/csnp/` family and synthetic BLAST lines; `blastp` exit statuses through `make_tool`; `InputError` across processes |
| `data("csnp")` | The goldens: `spec/`, `generated/`, and step 2 + 3 from `release/HUMAN` |
| `tools("blastp")` and `data("csnp")` | Step 1 against `blast/`, `score()` end to end for §7.3, the species codes. These run in CI's `engine-image` job, where both are required |

## Risks / Trade-offs

- **[The oracle's Perl reads the scripts differently from production's]** → The self-check (decision 9) must reproduce §7.3 and §7.5 byte for byte before any generated golden is trusted.
- **[Spec §4.4 is wrong about some nodes, such as `0>0` with a known taxon]** → The reference image's output decides, not the spec. Apply records each finding in `docs/parity/inputs.md`. The spec is in read-only `panther-workspace`, so it isn't edited.
- **[`blastdbcmd` can't list species from a database built without `-parse_seqids`]** → Fall back to the FASTA headers in `PANTHER9.blast.tar.gz`. The check then runs only where the archive is, not in CI, and the Notes say so.
- **[A `.paml` read is slow on the largest family]** → Measure `PTHR11695` (136 MB) in the image and record it in the Notes. Above about 10 s, open a follow-up for an index. It doesn't block M1.
- **[The recomputed `pident` differs from what the old BLAST+ printed]** → Checked against all 4 `HUMAN` rows, and checked to round to 2.17.0's own value on every line.
- **[The sample grows by about 360 MB unpacked]** → One download per new manifest, then the Actions cache. Record the CI fetch time in the Notes.
- **[One very large pull request]** → The description walks through it in task order. Each task group passes its own tests before the next starts.

## Migration Plan

Nothing in production changes: the API still answers `501` until its own change wires the engine in. The order:

1. `InputError`, the divergence row and the shared docs.
2. The sample with the BLAST database, published.
3. The reference image, its self-check and the goldens.
4. Steps 2 and 3, step 1 and `score()`, then the CLI.

Rollback is reverting the pull request. `csnp-sample-2` can stay; `csnp-sample-1` is still there for older commits.

## Open Questions

- **How many genes and positions per family** for the staging run on the full library. The defaults (5 × 8) take about 3 hours of Perl on 17 GB of `.paml`. They can change by command-line option, without a code change.
