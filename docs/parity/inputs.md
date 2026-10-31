# Parity Inputs

Each service's test inputs, and why each is in the set. The files are in `engine/tests/golden/<service>/`; how they were made, and how to make them again, is in [golden-setup.md](golden-setup.md). Only `csnp` has inputs so far.

## `csnp`

Quirk IDs (`MAP-4`, `SCORE-2`, …) refer to the legacy behaviour spec, `panther-workspace/legacy/cSNP_analysis/.specs/2026-10-28-legacy-behavior-spec.md`.

| Folder | What it is | Made by |
| ------ | ---------- | ------- |
| `release/` | The PSEP 1.01 release's sample: `HUMAN`, `sample.input`, `sample.fasta` | The release, copied |
| `spec/` | The spec's goldens: §7.3's output, §7.5's input and output | The spec, transcribed; the reference image reproduces them |
| `generated/` | Step-2 runs and step-3 cases, and the reference's output for each | `panther-engine csnp parity`, seed `port-csnp` |
| `blast/` | BLAST+ 2.17.0's output for the three sample proteins | The engine image |

### The Release Sample (§7.3)

35 substitutions in three human proteins, scored in one batch: P26439 (`del1`–`del26`) and Q9H2F3 (`del27`, `del28`) in `PTHR10366`, P78314 (`del29`–`del35`) in `PTHR15126`. They cover:

- **`SCORE-2`:** `del27` and `del28` start the walk at an internal node, column 1380, not Q9H2F3's leaf.
- **The cap:** `del3`, `del26` and `del27` are 4200.
- **`SCORE-6`:** `del14`, `del19` and `del25` are aged 91, Euarchontoglires, and get 0.19.
- **`MAP-5`:** `del26`'s mutant residue keeps the input's trailing space, `P341L`.
- **`SCORE-7`:** the batch spans two families. Spec §7.4 shows the `PTHR15126` rows don't depend on the order, so the port, which scores one family per call, reproduces every row.

`tests/test_csnp_scoring.py` also scores the three proteins end to end, one call each, as the service does: `blastp`, then steps 2 and 3. The API accepts no trailing space, so `del26` is submitted as `P341L`.

### The Edge Cases (§7.5)

Ten SNP lines, run through step 2 with species `NA` against `release/HUMAN`, then step 3, in one batch. How each reaches the service, whose input the API has already checked:

| Case | Input | What it shows | Through the service |
| ---- | ----- | ------------- | ------------------- |
| `e1` | `M1V` | `MAP-4`: the alignment's first residue isn't mapped | The same: "Invalid substitution" |
| `e2` | `G2V` | The next residue is | The same: 910 |
| `e3` | `E10A` | The wild type must come first (`MAP-5`) | The same: "Invalid substitution" |
| `e4` | `A10*` | `MUT` doesn't change the score (`SCORE-12`) | The API rejects `*` |
| `e5` | `A10;E;V` | Fields after `MUT` are ignored | Can't be sent: one token is one substitution |
| `e6` | Protein `NOPE` | No hit: "No PANTHER family" | The query is always `P0001`. No hit comes from the species instead: P26439 for `PLAF7` |
| `e7` | `a10E` | Lower case is a wrong wild type | The API upper-cases it to `A10E`, which is scored |
| `e8` | `Q372R` | The last residue | The same: 97 |
| `e9` | `X373R` | One past the end, with a wrong wild type | The same: "Invalid substitution" |
| `e10` | `A10E` and CRLF | The `\r` stays in the substitution | The API removes whitespace |

`tests/test_csnp_scoring.py` scores `M1V`, `G2V`, `E10A`, `Q372R` and `X373R` through the service, and `A010E` for a leading zero.

### Generated Step-2 Runs

Step 2 alone: BLAST lines and SNP lines, through `parse_blastp.pl`. Each case is one query id, with one or more hits, and its SNPs. 296 SNPs in four runs:

| Run | Species | Cases |
| --- | ------- | ----- |
| `listed` | `HUMAN` | Hand-written alignments, below. 47 SNPs |
| `species` | `RAT` | `MAP-2`: a `MOUSE` hit whose aligned sequences spell `RAT` gets through the filter, and beats a `RAT` hit with a lower identity. A `rat` in lower case doesn't. 3 SNPs |
| `unfiltered` | `NA` | The `listed` alignments without the species filter, so the `MOUSE` hits count. 47 SNPs |
| `random` | `HUMAN` | 30 random alignments with gaps on either side, one to three hits each. SNPs at the start, just after it, after each gap in the query, at the end, past it, and two at random; one in six with a wrong wild type. 199 SNPs |

The `listed` alignments:

| Query | What it shows |
| ----- | ------------- |
| `gap-in-query` | `MAP-4`: the residue right after a gap in the query isn't mapped |
| `gap-in-subject` | A gap in the subject is taken off the mapped position |
| `gaps-both-sides` | Gaps in both, with the alignment starting at query 3 and subject 7 |
| `offset` | `qstart` 5 and `sstart` 20: positions before, at and past the alignment |
| `x-and-stop` | `X` is a residue; `*` is neither a residue nor a gap, so it shifts the column |
| `leading-zero` | `010`, `03`, `0`, `+5` and `10.0`, read as Perl numbers and echoed as written |
| `wrong-wt` | A wrong, a lower-case, a two-letter and an empty wild type |
| `tie` | `MAP-1`: two hits with the same identity, settled by comparing the lines byte by byte (`A` before `a`) |
| `ranking` | 10.00% beats 9.09%: the identity is compared as a number |
| `filtered` | `MAP-2`: a 100% `MOUSE` hit and a 90% `HUMAN` one |
| `no-hit` | SNPs for a protein with no hit |
| `NA` | A query named `NA` never gets a hit: `readBLASToutput` starts with `$lastline = 'NA'` |

The step-2 port passes every one, and the release sample and the edge cases, byte for byte.

### Generated Step-3 Cases

Step 3 alone: snpParse rows, one file per family of the [data sample](csnp-library-survey.md#the-sample), each run through `PANTHER_PSEP1.01.pl` in a fresh process. 648 cases in 16 families.

Per family:

- **A "no family" row,** for `PTHR00000`, which no library has, and **an unmapped row,** with no mapped position.
- **Five genes,** chosen with a seeded `random.Random`. First, for each kind of node on the paths from the genes' start columns to the root, rarest kind first, a gene whose path has one; then genes at random. The start column is the Perl's (`SCORE-2`).
- **Eight positions per gene, grouped by gene,** because the Perl reads the `.paml` again whenever the gene changes (`SCORE-11`):
  - the first and last residues of the gene's `.rst` sequence;
  - one past the last, with the wild type the Perl would find there: `getCorrectnum` takes the last column it steps on;
  - a wrong wild type at a random position;
  - for each kind of node not yet covered in the family, a position whose walk stops at one, found by walking every site;
  - random positions for the rest.
- **The submitted position differs from the mapped one,** so the output shows that the substitution keeps the submitted one (`SCORE-10`).

The five families with no sequence list in their `.rst` (`PTHR11711`, `PTHR19241`, `PTHR21493`, `PTHR23125_2`, `PTHR24073_10_1`) give "Invalid substitution" for every gene's case, before their broken `.paml` is read, in the Perl and in the port.

#### Kinds of Node the Walks Reach

What `parity check` reports for the committed set: the walks that stopped at a node of each kind, and those that visited one.

| Kind | How the Perl ages it | Stopped at | Visited |
| ---- | -------------------- | ---------- | ------- |
| `0>1`, a speciation in a taxon of the species tree | The taxon's age | 224 | 258 |
| `Ev=1>0, not read`: a duplication | Its oldest child plus one, capped at 4200 | 63 | 99 |
| `Ev=0>0, not read` | As a duplication | 16 | 29 |
| `Ev=UNK, not read`: the root of `PTHR24073_7_3` and `PTHR24073_10_1` | As a duplication | 7 | 7 |
| `missing taxon`: a speciation in a taxon the species tree lacks (`DATA-3`) | As a duplication | 24 | 82 |
| `leaf` | 0 | 0 | 295 |

**No `1>0` or `0>0` node is read as an event.** The data writes duplications and `0>0` nodes without `S=`, and the Perl's pattern needs `Ev=…:S=…:ID=…` in that order, so it reads no event for them and ages them as duplications. Spec §4.4 says so. The "Not read" in the kind is the port's, for this report.

**A `0>0` node with a known taxon gets an empty age.** The Perl falls through `getYear`'s `if` chain. No family in the sample has one; the hand-written fixture `PTHR00004` does, and the reference image confirmed the empty age (`tests/test_csnp_psep.py`).

**No walk stops at a leaf:** a leaf's probability is always 1, and its residue is the gene's own.

### The Step-1 Golden

`blast/` holds the BLAST+ 2.17.0 output for the three sample proteins and the form's example (below), each named `P0001`, against the sample's database. Each sample protein's best hit for `HUMAN` has the subject id, start positions and aligned sequences of its first row in `release/HUMAN`, the legacy BLAST+'s output. Only the identity's decimals differ: 2.17.0 writes 3 (`93.801`), the legacy 2 (`93.80`), so step 2 recomputes it with 2 ([tech-stack.md](../design/tech-stack.md#pinning-tool-versions)). The output is the same on arm64 and amd64.

### The Form's Example

The scoring form's example, from the legacy site's help page (`tips_exampleCsnpInput_content.jsp`): human APOE, with `L46P`, `C130R`, `R163C` and `R176C`, for `HUMAN`. It's the first thing most users score, and the generated cases needn't reach its gene or its positions. Its family, `PTHR18976`, joined the data sample for it in `csnp-sample-3`.

- **Step 1:** `blast/APOE.csv`. The best hit for `HUMAN` is `APOE_HUMAN` itself (`P02649`), identical over all 317 residues, so step 2 maps each position to itself.
- **Steps 2 and 3:** `example/apoe.input` holds the four SNP lines as `score()` gives them to step 2. The reference image's output is `apoe.snpparse` and `apoe.out`: L46P 91 Mya and C130R 6 Mya, probably benign; R163C and R176C 220 Mya, possibly damaging.
- **The numbering includes the signal peptide,** as the help page says: `C130R` is APOE4's substitution, which the literature calls C112R.

### What Isn't in the Set

- **A gene missing from the `.orig.tree` (`SCORE-8`).** No BLAST entry whose family has a `.paml` is missing from its tree (`DATA-2`), so the service never sees one. The fixture `PTHR00004` tests the Perl's stale start column instead.
- **A batch spanning families (`SCORE-7`).** The service scores one protein per call. Divergence row 3 stays a proposal for batch use.
- **The full library.** The staging run covers it ([golden-setup.md](golden-setup.md#the-staging-run-on-the-full-library)).
