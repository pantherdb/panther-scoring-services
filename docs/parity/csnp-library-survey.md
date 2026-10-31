# cSNP Library Survey

The survey of the cSNP PAML_RST library: one pass over all 8,607 families with the engine's strict readers, beside the legacy scorer's own readings, and against the PANTHER9 BLAST database. It is how the [cSNP data sample](../testing/engine.md#the-csnp-data-sample) was chosen, and it tells the port which of the Perl's readings it must reproduce.

- **Run:** 2026-10-29, with the engine code of `add-csnp-survey-and-sample`, merged in #21 as `234d650`.
- **Run time:** 395 s and 277 MB of memory on an Apple Silicon Mac. The archive is read as a stream and never unpacked.
- **Quirk IDs** (`SCORE-2`, `DATA-1`, …) refer to the legacy behaviour spec, `panther-workspace/legacy/cSNP_analysis/.specs/2026-10-28-legacy-behavior-spec.md`. "The review" is that repository's `docs/2026-10-28-parity-review.md`.

## Inputs

| Input | Where it came from | sha256 |
| ----- | ------------------ | ------ |
| `PAML_RST.tar.gz`, 2,350,213,383 bytes | Tarballed from the legacy production server before it was shut down, so it is production's library build. The developer copy is `panther_build/PAML_RST.tar.gz`, beside `panther-workspace` | `6791f43325afdae3a1872c7655d103f9cdd98d5dbf6695a1187bb30985a869c5` |
| `PANTHER9.blast.tar.gz` | The PSEP 1.01 release (`PANTHER_PSEP1.01/`) | `2cf4428c97b99c4bce3705a80dc7f55c17779e54a0bcae9ddb7d75a67b40dcc9` |
| `species_pthr8_time.nhx` | The PSEP 1.01 release; identical in `cSNP_analysis` at `cebb5ab` | `23b035c293337966bd766628dd721c0a264230a49e4763188c607e301623d1e9` |

All three match spec §7.1. The command, from `engine/`, with the inputs beside the repository:

```sh
uv run panther-engine csnp survey ../../panther_build/PAML_RST.tar.gz \
  --species ../../panther-workspace/legacy/cSNP_analysis/species_pthr8_time.nhx \
  --blast-archive ../../PANTHER_PSEP1.01/PANTHER9.blast.tar.gz --json survey.json
```

## Results

Every figure in the review is reproduced, or the difference is traced to its cause.

| Check | Survey | Review | Difference |
| ----- | ------ | ------ | ---------- |
| Families | 8,607; 25,821 files, three per family | 8,607 | None |
| Split parts whose base family has no files (`DATA-1`) | 1,887 parts, of 410 bases | 1,887 parts, 410 families | None. Every split part in the library lacks its base. Split names nest: `PTHR10024_1_1` |
| Files the strict readers reject | 14, in 7 families (below) | 4 broken files | The review checked only for an empty `.rst` and a `.paml` without a root. The other 10 files are in the same families, or in 3 more families broken the same ways |
| Start column (`SCORE-2`) | 117,335 of 674,930 leaves, in 6,894 of 8,600 families | 117,389 of 676,233 leaves, in 6,897 of 8,605 families | The survey counts families whose `.paml` reads. The review counted every family with a root, including 5 whose `.paml` the strict reader rejects: `PTHR11711`, `PTHR19241` and `PTHR13902_1` (all-`0` sites), and `PTHR10127_2_1` and `PTHR24073_10_1` (truncated header). Those hold 1,303 leaves, 54 of them moved, in 3 families. Added in, the figures match exactly |
| Speciation nodes whose taxon is missing from the species tree (`DATA-3`) | 40,506: Perissodactyla 15,568, Artiodactyla 14,288, Sauria 10,650 | 40,506 | None |
| `Ev=0>0` nodes | 1,977 | 1,977 | None |
| Nodes "without `Ev`" | 0 without `Ev`; 319 with `Ev=UNK` | 319 | The same nodes: every `Ev=UNK` is on a root (`AN0`). The Perl's `Ev=([0-9]>[0-9])` doesn't match it, so the review counted them as having no event |
| BLAST entries in a family with a `.paml` (`DATA-2`) | 474,535, every one on a gene line of its family's `.orig.tree` | 474,535 found | None |
| BLAST entries with no `.paml` | 95,639 | 95,638 | One header in `blast.fasta` is a lone `>` with no sequence, at the end of the file. The BLAST database, built from it, has 570,173 sequences |

### Files the strict readers reject

Each of these families is broken in both its `.paml` and its `.rst`, so the Perl can't score it either: it finds no sequence for the gene, and reports `Not scored: Invalid substitution` (needs confirming against the reference image).

| Family | `.paml` | `.rst` |
| ------ | ------- | ------ |
| `PTHR11711` | Every site is `0` in every column | Empty |
| `PTHR19241` | The same, byte for byte as `PTHR11711.paml` | Empty |
| `PTHR13902_1` | Every site is `0` in every column | No sequence list: the file ends after 20 lines |
| `PTHR21493` | No root: the header is cut short, and parents point past it | No sequence list |
| `PTHR23125_2` | No root, as `PTHR21493` | No sequence list |
| `PTHR10127_2_1` | The header is cut short: column 2's parent, `Node266`, isn't a column | No sequence list |
| `PTHR24073_10_1` | The header is cut short: column 1's parent, `Node359`, isn't a column | No sequence list |

No `.orig.tree` is rejected.

### Variants in the Strict Shape

Three shapes that spec §3.5 doesn't describe are read as variants (engine developer, 2026-10-29). The Perl reads each without harm.

| Variant | Families | Read as |
| ------- | -------- | ------- |
| Unreconstructed cells: a NUL residue with a `-nan` probability, always as a pair | 4, 74,496 cells: `PTHR10366`, `PTHR24220`, `PTHR24322`, `PTHR11695` | No residue, probability NaN. The Perl's `> 0.99` is false for NaN, so its walk stops there |
| Internal columns labelled `Node<k>` with no AN | 415, 45,310 columns | AN None. The Perl never reads an internal column's AN |
| A tree line with one `)` too many, just before the `;` | 135 split parts, such as `PTHR23125_2` | The `)` is ignored. The Perl's patterns never see it |

### The Legacy Readings

For each value the Perl reads with a loose pattern or a fixed line, the survey compared its reading with the strict reader's, on every file the strict reader accepts.

| Reading | Families where they differ |
| ------- | -------------------------- |
| Start column, the last header match (`SCORE-2`) | 6,894 families, 117,335 leaves |
| Root | 0 |
| `.rst` branch list, line 12 (`SCORE-9`) | 0 |
| `.rst` tree nodes, line 15 | 0 |
| `.orig.tree` AN order | 0 |
| Pairing of nodes with ANs | 0 |
| Events and taxa, `Ev=…:S=…:ID=…` | 0 |
| Sequences, `AN<n>` and three spaces | 0 |
| Species ages, `:S=…:A=…]` | 0 taxa |
| Gene lookup, first match of an unescaped pattern (`SCORE-8`) | 0 of 474,535 BLAST entries |
| Carriage returns kept by `chomp` | No file has one |

The `.rst` and `.orig.tree` files agree with the `.paml` everywhere: parents and branch list, leaf labels, node counts, tree shapes, and sequence lengths against the site count.

### The BLAST Database

The 95,639 entries without a `.paml` are of three kinds:

- **81,323 entries whose header is `GENE:AN<n>:FAMILY`,** not `GENE:FAMILY:SF`. Step 2 takes the second field as the family (`parse_blastp.pl:63, 69`), looks for `AN<n>.paml`, and finds none. In 75,712 of them, the third field names a family that has a `.paml`: 62,400 in 810 split parts, and 13,312 in base families.
- **14,315 entries in 111 families** with no files in the library.
- **The lone `>`** above.

`DATA-1` says the split parts can't be reached because BLAST ids carry the base family. That holds only in part. 4,768 entries name 849 split parts directly, as `GENE:PTHRnnnnn_N:SF`, and the Perl can score them. Most split-part members are among the `AN<n>` headers, which it can't.

## The Sample

One family for each check that found something, the smallest that shows it; the four families the spec names; the other two known broken `.paml` files; the family with the largest `.paml`; and, since `csnp-sample-3`, the family of the scoring form's example.

| Family | Bytes | Stands for |
| ------ | ----- | ---------- |
| `PTHR10366` | 76,922,468 | Golden family (spec §7), `SCORE-2` (`del28`), unreconstructed cells, internal columns without an AN, `Ev=0>0`, missing taxa |
| `PTHR15126` | 234,817 | Golden family (spec §7) |
| `PTHR11711` | 9,328,465 | Known broken: empty `.rst`, all-`0` `.paml` |
| `PTHR19241` | 9,272,208 | Known broken: empty `.rst`, all-`0` `.paml` |
| `PTHR21493` | 5,675,949 | Known broken: `.paml` with no root |
| `PTHR23125_2` | 3,441,557 | Known broken: `.paml` with no root; one `)` too many |
| `PTHR24073_10_1` | 2,265,757 | Smallest rejected `.paml` and `.rst`: a truncated header, no sequence list |
| `PTHR31369_2` | 10,438 | Smallest split part with no base family (`DATA-1`) |
| `PTHR10183_6` | 25,105 | Smallest with internal columns without an AN |
| `PTHR16675_3` | 230,761 | Smallest tree with one `)` too many |
| `PTHR17486` | 10,133 | Smallest with a moved start column (`SCORE-2`) |
| `PTHR11941_9` | 31,581 | Smallest with an `Ev=0>0` node |
| `PTHR24073_7_3` | 142,857 | Smallest with `Ev=UNK` |
| `PTHR17358` | 5,443 | Smallest with a taxon missing from the species tree (`DATA-3`) |
| `PTHR11695` | 151,919,041 | The largest `.paml`, 136,336,728 bytes; unreconstructed cells |
| `PTHR18976` | 1,884,798 | The scoring form's example: human APOE, the legacy site's (`tips_exampleCsnpInput_content.jsp`). Added in `csnp-sample-3` (`add-apoe-to-csnp-sample`) |

Every check that found something in the full library also finds something in the sample, apart from the BLAST checks, which read the BLAST archive's FASTA. The sample holds the BLAST database since `csnp-sample-2`, but not the FASTA. `tests/test_csnp_sample_data.py` checks this.

## What It Means for the Port

- **The strict readers are safe for parity everywhere but the start column.** Every other legacy reading agrees with them on every file they accept. Step 3 can use them without a divergence row.
- **The start column (`SCORE-2`) differs for 17.4% of leaves.** To match the goldens, step 3 must start from the last header match, `legacy.start_node`. Starting from the leaf's own column is proposed divergence row 2.
- **The seven broken families can't be scored,** by the Perl or the port. Matching the Perl means reporting `Not scored: Invalid substitution` for a SNP in them. The reference image confirmed it for the five in the sample (`port-csnp`, [inputs.md](inputs.md#generated-step-3-cases)). That holds for one protein per call, as the service scores. In a Perl batch, a SNP in one of them after another family's record keeps that record's `$nth`, and can be scored from column 0 (`SCORE-8`).
- **BLAST entries with `AN<n>` in the family field are never scored by the Perl.** 75,712 of them belong to families the library has. Matching the Perl means reporting `Not scored: No PANTHER family for input sequence` when one is the best hit. Reading the third field instead would score them: that would be a divergence, and is the port's decision, with the science owner.
- **Events are reported as written.** The strict reader gives `0>0` and `UNK` as they are, and a missing taxon as missing. Step 3 must age those nodes as the Perl does (spec §4.4, `DATA-3`).
