# treegrafter Library Survey

What PANTHER 19's TreeGrafter library and its PAINT annotation releases hold, the data the `treegrafter` service grafts with, and what EBI's `treegrafter` does with them on the full library. It gathers three records from `adopt-treegrafter`:

- **The spike, 2026-11-24:** EBI's `treegrafter.py` at `5ef350f`, unchanged, run as `treegrafter.sh search` runs it, one job at a time, in the engine image (HMMER 3.4, EPA-ng 0.3.8, Python 3.13.18) with Biopython 1.88 and NumPy 2.5.5, on an M1 Pro with Docker Desktop's 10 CPUs and 12.5 GB. Its scratch scripts weren't kept; `tasks.md`'s Notes and design.md's decisions keep its numbers, and the engine's commands replace its scripts.
- **The pinning, 2026-11-24 (task 3.4):** `panther-engine treegrafter data manifest`, `data fetch` and `data verify` on the same M1 Pro, natively.
- **The full-library run, 2026-11-24 (task 7.6):** `panther-engine treegrafter parity reference` and `check` on the full library, for the goldens' cases and a set of 30 proteins.

## The Library

| Input | Where it came from | sha256 |
| ----- | ------------------ | ------ |
| `PANTHER19.0_data_trees_hmms_only.tar.gz`, 3,073,460,727 bytes | `https://data.pantherdb.org/ftp/downloads/TreeGrafter/`, downloaded on 2026-11-24 | `789c31d7f1e051ae3dfdd4c6c41e97a970395cc490cab52da850d1b5abfd5e4f` |

- **Its members:** 62,742, every one below `PANTHER19.0_data/`: the prefix's folder, `PAINT_Annotations_README`, `Tree_MSF/` with four files for each of 15,683 families (`.AN.fasta`, `.bifurcate.newick`, `.newick` and `.tree`), `famhmm/` with `binHmm` and its four pressed files, and an empty `tmp/`. Every family ID is `PTHR` and five digits. 8.21 GB unpacked.
- **What the fetch keeps:** `famhmm/binHmm` and three tree files a family, 47,050 files listed in `library.sha256` (sha256 `6c0dbbed…`), 4.2 GB on disk. It skips the pressed files, the `.tree` files, the PAINT README and `tmp/`. EBI's README downloads `PANTHER19.0_data.tar.gz` instead, which adds an older annotation file.
- **The models:** `binHmm` holds 15,683 family HMMs, named `PTHRnnnnn.orig.30.pir`, sorted by family. Each HMM's length equals its alignment's width.
- **The trees:** 3,564,945 nodes in the `.newick` trees, 2,017,190 of them leaves, each labelled `ANn`. The `.bifurcate.newick` trees add `BIn` nodes, and leave some branch lengths out. The largest tree is PTHR11654's, with 3,226 leaves.
- **Times on the M1 Pro:** `data manifest` read the tarball in 19 s; `data fetch` from a local copy took 67 s; `data verify` takes 15 s.

### Ten Families That Can't Be Placed

In ten families, one leaf of the bifurcating tree has no row in the alignment, and no branch length in that tree. EPA-ng refuses such a tree ("Bad tree/ref msa combination"), so EBI's code returns the family alone, and so does the engine, with a warning:

PTHR11034, PTHR11134, PTHR11387, PTHR11489, PTHR11824, PTHR13104, PTHR23404, PTHR23411, PTHR43511 and PTHR46115.

In PTHR11034, the NDRG family, that leaf is AN186, a dog protein. Whether the next library build fixes them, and who does it, needs team verification (the proposal's open questions).

## The Annotation Releases

Of the eleven 19.0 releases under `paint/19.0/`, only the three newest have a `PAINT_TreeGrafter_Annotations_TOTAL.txt.gz`: the eight from 2024-09-23 to 2025-10-01 answer 404. All three are in the TreeGrafter format, three tab-separated columns (the node, its annotations, its graft point's public ID), and cover every node of the library, so all three are pinned:

| Release | Bytes | sha256 | GO release | Lines |
| ------- | ----: | ------ | ---------- | ----: |
| 2026-01-05 | 24,063,007 | `3ed5780a…` | 2025-10-06 | 3,566,035 |
| 2026-06-02 | 23,970,953 | `f17e2b9c…` | 2026-04-28 | 3,564,945 |
| 2026-08-28 | 23,980,614 | `03ad195b…` | 2026-08-05 | 3,564,945 |

- **`current`:** on 2026-11-24, `paint/current/` held 2026-08-28's file: the same sha256 and ETag, `"16dea46-65a2436625380"`. The server has no other marker of which release `current` is, so the engine resolves it by sha256.
- **`pango/`** holds a third file, 23,942,358 bytes, dated 2026-03-11, though the library's README lists it first. The engine doesn't use it.
- **2026-01-05's 1,090 extra lines** are for nodes no tree has, which EBI's code never looks up. Between 2026-01-05 and 2026-08-28, 84 nodes changed subfamily.
- **GO terms:** 2026-08-28's 10,500 distinct GO IDs are all in the 2026-08-05 `go.obo`, and none is obsolete.
- **Preparing a release** with EBI's `prepare` took 45 s and 1.4 GB in the spike, and wrote 320 MB: 15,683 family files. With the engine's node check and the library's verification, pinning a release took about 1 minute and 1.39 GB, and the fetch of 2026-08-28 53 s.

### Subfamilies at the Root

In 2026-08-28, 13,550 of the 15,683 family roots carry a subfamily: actin's AN0, for one, is SF274. 2,235 nodes have no subfamily, 2,133 of them roots. So EBI's code names a subfamily for almost any graft, even one at a family's root. Whether that's intended needs team verification: the science owner, or whoever builds the PAINT TreeGrafter file (the proposal's open questions).

## Timings

### The Spike

One job at a time, as `hmmsearch` plus EBI's step, with EPA-ng's share of that step in brackets:

| Query | Time |
| ----- | ---- |
| APOE | 10 s + 1.7 s (0.6 s) |
| A leaf of the largest tree | 9 s + 26 s (26 s) |
| CFTR | 20 s + 48 s (29 s) |
| DYNC1H1 | 51 s + 4 s |
| Titin's first 10,000 residues | 63 s + 2 s |
| A 7,243-residue leaf | 142 s + 1 s |

- **The 7,243-residue leaf** passes `hmmsearch`'s first filter for 5,978 HMMs.
- **Peak memory:** EPA-ng 2.3 GB, on PTHR11654, the largest tree; `hmmsearch` 1.26 GB, on the 7,243-residue leaf.
- **Threads don't help one query:** `hmmsearch --cpu 4` is slower than `--cpu 0` (APOE 14.2 s against 9.8 s), its reports byte-identical, and the pressed `binHmm.h3m` is no faster than the text file. EPA-ng placed on actin's family in 10.95 s at `-T 1`, and 11.92 s at `-T 4`. So the engine runs both with one thread (design.md, decision 6).
- **EBI's in-process steps** took up to about 20 s, on CFTR's family, where the graft node sits high and `process_tree` asks Biopython for the common ancestor of every leaf below it.

### On the Full Library

On the same M1 Pro, with the same 10 CPUs and 12.5 GB, the engine took 43 to 103 s a protein, a median of 50 s, and EBI's command line about as long (below). Almost all of it is `hmmsearch`, and it doesn't reproduce the spike's 10 s:

- **`hmmsearch` took 45 s and 43 s for an empty query,** with the library in a Docker volume, where `cat` read `binHmm` in 1.5 s. So the time is `hmmsearch` reading the 15,683 text HMMs, not the file, and not the query.
- **Through a bind mount from macOS,** APOE's graft took 59 s cold and 50 s warm: about the same.
- **Why the spike measured 10 s** on this machine needs team verification. The hosting server's own timings come with `add-treegrafter-job`, before its time limits are set. If they're as slow, the first lever is design.md's two-stage search, `hmmscan` on the pressed files first.

## Against InterPro 111.0 and PANTHER's Classification

The spike grafted 24 proteins and compared each with InterPro 111.0, on PANTHER 19.0, and with PANTHER's own classification:

- **17 of 24** have the same subfamily as InterPro.
- **4 that InterPro gives only a family match** get the subfamily PANTHER's own classification gives: OR1A1 SF50, MAPK1 SF584, H3.1 SF242 and GroEL SF3.
- **Actin** is SF575, where PANTHER says SF414: a near-tie, with 7 placements of 3% each.
- **Titin's first 10,000 residues** miss the region InterPro places full titin by.
- **The SARS-CoV-2 spike** has no hit in either.
- **Calmodulin** is PTHR23048:SF0 here and in InterPro, but PTHR23050:SF531 in PANTHER's tree.
- **E-values** equal InterPro's in all 13 cases where InterPro's isn't 0.

So 22 of 24 agree with InterPro or PANTHER's own classification, and the other two are explained. Why InterPro shows no subfamily for 5 of the 24 needs team verification. One lead (task 7.4): InterProScan 6 doesn't run EBI's `treegrafter` repository. Its PANTHER module searches with `hmmsearch -Z 65000000 -E 0.001`, without `--domE`, picks the best family in its own Groovy code, and places with its own `bin/treegrafter.py`.

## The Full-Library Run

On 2026-11-24, `panther-engine treegrafter parity reference` and `check`, with `--goldens full`, on the full library and release 2026-08-28, with `data verify` clean first ([inputs.md](inputs.md#the-treegrafter-full-library-run)):

- **The goldens' 12 cases:** all 12 match, each byte-identical to its golden on the fixture.
- **30 more proteins** (`engine/tests/golden/treegrafter/library/`): all 30 match. This set replaces the spike's 33 queries, whose list wasn't kept.

| Protein | Hit |
| ------- | --- |
| CFTR | PTHR24223:SF19 at AN168 |
| DYNC1H1 | PTHR46532:SF13 at AN38, E-value 0.0 |
| Titin's first 10,000 residues | PTHR47633:SF4 at AN92, E-value 0.0 |
| OR1A1 | PTHR48001:SF50 at AN1842 |
| MAPK1 | PTHR24055:SF584 at AN2190 |
| H3.1 | PTHR11426:SF242 at AN1140 |
| Actin (ACTB) | PTHR11937:SF575 at AN1128 |
| Calmodulin (CALM1) | PTHR23048:SF0 at AN316 |
| TP53 | PTHR11447:SF6 at AN14 |
| BRCA1 | PTHR13763:SF0 at AN23 |
| EGFR | PTHR24416:SF91 at AN462 |
| Insulin | PTHR11454:SF9 at AN15 |
| GAPDH | PTHR10836:SF111 at AN71 |
| Rhodopsin | PTHR24240:SF15 at AN702 |
| Polyubiquitin-B | PTHR10666:SF437 at AN682 |
| KRAS | PTHR24070:SF388 at AN1448 |
| Lysozyme C | PTHR11407:SF28 at AN222 |
| GroEL | PTHR45633:SF3 at AN1022 |
| RecA | PTHR45900:SF1 at AN355 |
| SARS-CoV-2 spike | No hit |
| Yeast CDC28 | PTHR24056:SF254 at AN947 |
| Spinach RbcL | PTHR42704:SF16 at AN101 |
| Drosophila Notch | PTHR24049:SF22 at AN254, E-value 0.0 |
| Bacteriorhodopsin | PTHR28286:SF2 at AN54 |
| Arabidopsis FLC | PTHR48019:SF238 at AN1028 |
| LacI | PTHR30146:SF153 at AN198 |
| SLC15A5, of the largest tree | PTHR11654:SF91 at AN98 |
| AP3B1 | PTHR11134 alone: its tree's AN40 has no alignment row |
| COX6B1 | PTHR11387 alone: AN54 |
| MOCS2 | PTHR23404 alone: AN111 |

- **The spike's answers hold:** OR1A1 SF50, MAPK1 SF584, H3.1 SF242, GroEL SF3, actin SF575 and calmodulin PTHR23048:SF0 are the subfamilies the spike recorded, and the SARS-CoV-2 spike again has no hit.
- **Without a protein class:** DYNC1H1, titin, GroEL, polyubiquitin-B and bacteriorhodopsin graft to nodes whose entry has no `PC` term.
- **Time:** 43 to 103 s a protein for the engine, a median of 50 s; titin's first 10,000 residues took the longest, 103 s, then DYNC1H1's 89 s and Notch's 86 s.
