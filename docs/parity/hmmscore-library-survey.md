# hmmscore Library Survey

The survey of PANTHER 19's HMM library, the data the `hmmscore` service scores with: one pass over its tarball with the engine's strict readers, beside `pantherScore.pl`'s own readings. It tells the port what the library holds and which of the Perl's readings it must reproduce. It also gives what was measured on the full library: fetching it, its models as text, the press check, `hmmscan`'s time and memory, and HMMER 3.1b2 against 3.4 (`add-hmmscore-survey-and-sample`, task groups 6, 7 and 10). And it says how the [hmmscore data sample](../testing/engine.md#the-hmmscore-data-sample) was chosen.

- **Run:** 2026-11-09, with the engine code of `add-hmmscore-survey-and-sample` before its first commit, on the branch `feat/add-hmmscore-survey-and-sample-apply`. The survey's code was committed as `72012f7`. Run again on 2026-11-10, with the engine at `b1a6db6`, it gave the same report, byte for byte, as text and as JSON.
- **Run time:** 240 s and 431 MB of memory, natively on an Apple Silicon Mac, with a `data manifest` pass over the same tarball at the same time. The tarball is read as a stream and never unpacked.
- **The full-library runs:** 2026-11-10, with the same code, whose `data fetch` and `data verify` were committed as `b560b8e`, on a node of CARC's Endeavour cluster at USC, `b11-19.hpc.usc.edu`: an AMD EPYC 7513, amd64, with 64 CPUs and 503 GB of memory. They ran in the engine image built for amd64, through Apptainer. The library was on `/scratch2`, a BeeGFS file system that other users share. Each step's wall time, CPU time and peak memory were read with `os.wait4`.
- **"The legacy readings"** are `pantherScore.pl`'s, in `panther-workspace/legacy/pantherScoring/` at `89ea0ae` (unchanged since `d7b28ee`): `getHmmNames` (299 to 310) for `names.tab`, and `runHmmscan` (387 to 389) from a model's name to its HMM ID.

## Input

| Input | Where it came from | sha256 |
| ----- | ------------------ | ------ |
| `PANTHER19.0_hmmscoring.tgz`, 18,494,793,691 bytes | `https://data.pantherdb.org/ftp/hmm_scoring/19.0/PANTHER19.0_hmmscoring.tgz`, downloaded on 2026-11-09. The same file is under `current_release/` | `77b3a9eae1d4d1baeaf345368b861f2474893711f0187a9767397a1a1d0e87c8` |

Every member is below the prefix `target/famlib/rel/PANTHER19.0_altVersion/hmmscoring/PANTHER19.0/`. The command, from `engine/`, with the tarball beside the repository in `hmm_scoring/19.0/`:

```sh
uv run panther-engine hmmscore survey ../../hmm_scoring/19.0/PANTHER19.0_hmmscoring.tgz --json survey.json
```

## Results

Every figure the change's design expected is reproduced, or the difference is traced to its cause.

| Check | Survey | Expected | Difference |
| ----- | ------ | -------- | ---------- |
| Members | 318,761, none the layout lacks and none outside the prefix | Nothing unexpected | None |
| Model files | 15,683 family and 128,010 subfamily model files | 15,683 and 128,012, the README's counts | `names.tab` lists two subfamilies that have no model file: `PTHR24068:SF521` (line 58,955) and `PTHR11937:SF561` (line 21,496). `binHmm` has no model for either, so `hmmscan` can't hit them |
| `names.tab` | 143,695 lines: 15,683 family and 128,012 subfamily IDs, every line in the two shapes, no ID repeated | All lines in the two shapes | None. `getHmmNames` keys every line as the strict reader does |
| Model files that read | All 143,693, one model each, every format line `HMMER3/f [3.1b2 \| February 2015]` | Format 3/f, from 3.1b2 | None |
| One-subfamily families | 5,450. In each, the subfamily's model file is the family's, byte for byte, named `PTHRnnnnn.orig.30.pir` | 5,450 | None. They are the 5,450 model files whose legacy ID, the family's, isn't their path's |
| `binHmm` | No flat `binHmm`. Its index, `binHmm.h3i`, lists 144,361 models; no name repeats, each has the model file the CGI aligns with, and every model file's name is among them | Every model has its model file | `binHmm` holds 6,118 models that no model file holds (below) |
| Pressed files | `.h3f`, `.h3m` and `.h3p` in format 3/f, `.h3i` an SSI 3.0 index | Format 3/f | None |

Model names come in two shapes: `PTHRnnnnn.SFn.pir`, 122,560 files, and `PTHRnnnnn.orig.30.pir`, 21,133, which are the 15,683 family models and the 5,450 copies.

### The Members

| Member | Files | Bytes | sha256 |
| ------ | ----- | ----- | ------ |
| `README` | 1 | 4,210 | `040ff6497ff122eca7769692b5076743d5f4c9bebf15e7d60b99b47c4872885f` |
| `globals/names.tab` | 1 | 7,640,523 | `a0dfad734bb28e8649d26e226b01741bba21c57929adfd4aecbeed13cb72650b` |
| `globals/binHmm.h3f` | 1 | 5,265,690,109 | `09493c360ed3fc70ba53c97b69ebc4b94746b099f926778b9308ccc94b13d7f6` |
| `globals/binHmm.h3i` | 1 | 6,929,429 | `e4b0462912d9a4b181da6251e9357d8991dd6bd7602ef6814c90b5ca785be39a` |
| `globals/binHmm.h3m` | 1 | 13,554,818,829 | `67c91d653052147f7d164c2ba43283b553fed1520c2a0fc36c8cee85163b0791` |
| `globals/binHmm.h3p` | 1 | 15,826,161,352 | `4a1d3fcb10c5de21297a3ff32f96d5f07d20b8a0c6d7ca23f1b2f13e5640d4f2` |
| `books/PTHRnnnnn/hmmer.hmm` | 15,683 | 3,398,928,532 | in `books.sha256` |
| `books/PTHRnnnnn/SFn/hmmer.hmm` | 128,010 | 29,002,684,235 | in `books.sha256` |
| `books/PTHRnnnnn/cluster.pir` | 15,683 | 9,552,012,085 | not kept |
| `books/PTHRnnnnn/tree.tree` | 15,683 | 206,650,065 | not kept |
| Folders | 143,696 | | |

Fetching keeps the README, `globals/` and the model files: 67,062,857,219 bytes. It leaves out `cluster.pir` and `tree.tree`, 9,758,662,150 bytes, which nothing in scoring reads. The tarball's members come in this order: the README, `binHmm.h3f`, `names.tab`, `binHmm.h3i`, `binHmm.h3p`, `binHmm.h3m`, then `books/`.

### binHmm's Models Without a Model File

`hmmscan` searches `binHmm`, but the CGI aligns its best hit with the model file its HMM ID leads to (`scoreAlignXml.cgi:136` and `140`). `binHmm` holds 6,118 models whose names no model file holds, of two kinds. Both were read by cutting their records out of `binHmm.h3m` and converting them to text with HMMER 3.4's `hmmconvert`. For each model of those families that has a model file, the converted text is that file byte for byte, apart from the format line, which is 3.4's.

- **In each of the 5,450 one-subfamily families, the subfamily's own model,** `PTHRnnnnn.SFn.pir`. Its model file is a copy of the family's model, so the CGI reports a hit on it as the subfamily, `PTHRnnnnn:SFn`, and aligns it with the family's model. In `PTHR35774`, both models are 34 positions from 39 sequences, built half an hour apart on 2024-03-08. 12 of their emission scores differ in the fifth decimal, such as 4.62822 against 4.62823. So a query scores almost the same on each, and which of the two is the best hit, the family or the subfamily, can turn on that rounding.
- **In 668 families, a second family-level model named `PTHRnnnnn..pir`,** with nothing between its two dots. The legacy rule reads its HMM ID as the family's, and the CGI aligns it with the family's model. In `PTHR34093` it's a model of one sequence, 269 positions long, with a model mask; the family's own model is 511 positions, from 37 sequences. 80 of these families are one-subfamily families too. What these models are needs team verification.

Both kinds sit among their family's models, in the family's run of `binHmm`'s order. The survey reports them as `binhmm-not-in-books`, with the model file the CGI aligns each one's hits with.

### The Legacy Readings

| Value | Where the Perl's reading differs from the strict reader's | What it means for the port |
| ----- | --------------------------------------------------------- | -------------------------- |
| A `names.tab` key | Nowhere: 0 of 143,695 lines | The strict reader is safe |
| A model's HMM ID | In the 5,450 copies: each subfamily file's model is named for the family, so its legacy ID is the family's | None for scoring: `hmmscan` reads `binHmm`, not the model files. The CGI reads them only to align |
| A `binHmm` model's HMM ID | The 5,450 subfamily models read as their subfamily, and the 668 `..pir` models as their family | The port reads HMM IDs as `runHmmscan` does, and must align as the CGI does |

## The Full Library

### Fetching It

On Endeavour (tasks 6.4 and 6.5):

| Step | Wall time | CPU time | Peak memory | Result |
| ---- | --------- | -------- | ----------- | ------ |
| `data fetch --tarball`, from a local copy | 875 s | 304 s | 330 MiB | 67,076,724,129 bytes in `hmmscore/19/` |
| `data fetch` from the URL, into an empty folder | 1,134 s | 352 s | 331 MiB | The same files, at the same sizes |
| `data verify`, once for each folder | 5,778 s and 5,916 s | 111 s and 114 s | 98 MiB | Every one of the 143,700 listed files matches the pin |
| `data fetch` again, the folder already there | 5,933 s | 113 s | 98 MiB | Nothing downloaded. It checks every file first |

- **The bytes:** the 67,062,857,219 the tarball's kept members hold, and `books.sha256`'s 13,866,910.
- **By hand:** `sha256sum --check books.sha256` reported all 143,693 lines OK.
- **Left out:** no `cluster.pir` or `tree.tree` was written.
- **The download:** `curl -C -` fetched the tarball in 226 s on Endeavour, against 3,055 s on the Mac's network (about 6 MB/s).
- **Checking the folder took about 96 minutes each time,** with under 2 minutes of CPU. That's the file system's cost for 143,700 files; the fetches, which write as they stream, took 15 and 19 minutes. A server's own disk wasn't measured.

### binHmm as Text

The tarball has no flat `binHmm`. So task 7.1 wrote `binHmm.h3m` out as text with HMMER 3.4's `hmmconvert` on Endeavour, and compared each model, without its format line, with a model file:

- for a model that a model file holds, that file;
- otherwise, the file its legacy ID leads to, which the CGI aligns its hits with.

All 144,361 are accounted for:

| Models | Count | Compared with their model file |
| ------ | ----- | ------------------------------ |
| Held by a model file | 138,243 | Identical, apart from the format line |
| The subfamily models of one-subfamily families, `PTHRnnnnn.SFn.pir` | 5,450 | Four groups, below |
| The second family-level models, `PTHRnnnnn..pir` | 668 | 666 differ in length. The other 2 have the family model's length, but other `NSEQ`, `EFFN` and `STATS` |

The 5,450 subfamily models fall into four groups:

- **324 differ only in their header:** `NAME`, `DATE` and, in 317, `CKSUM`.
- **4,955 differ in some scores too,** by at most 1.5e-5: rounding in the fifth decimal. 25 of these differ in `STATS` as well.
- **114 differ by more, at the same length:**
  - 89 by at most 1e-4;
  - 6 by up to 0.94;
  - 19 where a line differs other than in a number.
- **57 differ in length,** by 1 to 29 positions.

So for 5,279 of the 6,118 models no file holds, the CGI aligns with a model that's the same up to rounding. For the other 839, including every `..pir` model, it aligns with a different model from the one that scored.

### The Press Check

Task 7.2 asked whether HMMER 3.4's `hmmpress` reproduces the shipped pressed files. On Endeavour, `hmmconvert`'s text of `binHmm.h3m` (449 s) was pressed with 3.4 (395 s):

| File | Against the shipped one, at the same size |
| ---- | ----------------------------------------- |
| `binHmm.h3f` | Differs from byte 319,468 |
| `binHmm.h3i` | The same, byte for byte |
| `binHmm.h3m` | Differs from byte 1,037 |
| `binHmm.h3p` | Differs from byte 22,008 |

So `hmmscan` ran the example and `test.fasta` against both sets. Without their `#` lines, the tables differ:

- **The example:** one c-Evalue, 0.00029 against the shipped files' 0.0003, and one hit's two lines in another place in the order.
- **`test.fasta`:** PTHR24235.SF9's domain scores 54.0 bits instead of 53.6, its envelope at 83 to 344 instead of 78 to 355. Three other lines differ in the last digit of a score or an E-value.

Then, on the Mac, the first 25,000 models showed where the differences come from. That ran in the engine image, on arm64 and on Docker's emulated amd64, which gave Endeavour's numbers exactly (below).

- **The text changes the probabilities.** 3.4 reads a text model's probabilities in single precision, `expf(-1.0 * atof(tok1))` (`src/p7_hmmfile.c`). So about 1 in 1,000 comes out one unit in the last place, about 1e-7, from the shipped float. This Mac's own 3.1b2, an arm64 build, doesn't reproduce them from text either.
- **Pressing the binary records instead gives back the shipped `.h3m` and `.h3f`,** byte for byte, on both architectures. `.h3p` still differs, in 5,185,856 of its 2,700,545,045 bytes on amd64: some of its floats differ in their last bits.
- **That `.h3p` still moves domains near a cutoff:** 2 of the 417 that the example, `test.fasta` and Q14204 hit among those models.
  - `test.fasta`'s PTHR24235.SF9, as above;
  - one of Q14204's PTHR37739.SF8 domains, at 2.5 bits instead of 1.8.

**The decision (engine developer, 2026-11-10):** the full library keeps its shipped pressed files, and fetch never presses. On amd64, 3.4 gives the shipped files' tables exactly, as 3.1b2 does (below), so they keep production's numbers. The sample presses its records cut out of `binHmm.h3m` as they are, with no text step. So its `.h3m` and `.h3f` are the library's, and only its `.h3p` is 3.4's.

### hmmscan on arm64

The same 25,000 shipped models, and the same pressed files, give slightly different numbers on arm64. HMMER 3.4 has an SSE build for amd64 and a NEON build for arm64. Against Endeavour's full-library tables, on the 417 domains they share:

| Run | Domains that differ | How |
| --- | ------------------- | --- |
| Docker's emulated amd64, on the Mac | 0 | |
| arm64, on the Mac | 4 | The example's PTHR34360.SF1 domain scores 13.2 bits instead of 13.1, and PTHR41394.SF5's has a bias of 0.7 instead of 0.8. `test.fasta`'s PTHR24235.SF9 domain moves, as above. One of Q14204's PTHR34491.SF166 domains scores 18.3 instead of 18.2 |

Production ran on amd64, so production's numbers are amd64's. The sample's committed `hmmscan` table has one version for each architecture (engine developer, 2026-11-10).

## hmmscan on the Full Library

Task 7.3, on the Endeavour node above, in the engine image, with the library fetched in task 6.4.

### The Queries

| Query | Residues | Where it came from | sha256 |
| ----- | -------- | ------------------ | ------ |
| The site's example, `engine/tests/golden/hmmscore/example/apoe.fasta` | 317 | The HMM scoring help page | `e1a6ca45e9377ec39a7cd19c4edc99649d5f73b98078d666cfd58ae291b68dd3` |
| `test.fasta`, `>test` | 381 | `https://data.pantherdb.org/ftp/hmm_scoring/19.0/pantherScore2.2/test.fasta` | `097bbf0c629a0b7aaa00c73c5368d11b9a5ba689412f4051ab5b353e03db2499` |
| Human DYNC1H1 | 4,646 | `https://rest.uniprot.org/uniprotkb/Q14204.fasta` | `39c4c48c73e21f0207c64336bbb1cf9c8844a105d897038b4162e418a0c89c80` |
| `titin-50000`: titin, UniProt Q8WZ42, then its first 15,650 residues | 50,000 | Q8WZ42's FASTA, sha256 `2bb79b409b2540249a432bd638215e5a789e69116eaf1ea0d15e48304e5c80f2` | `157165b96b2b91a69dd45720ef5ef50f3ceb84712e7e860e43bf8ae7c7954f91` |

50,000 residues is the website's limit for HMM scoring (`SequenceSearchForm.java:84`).

### Alone

A "cold" run came just after `posix_fadvise(DONTNEED)` on the four pressed files, as far as a user without root can drop them from the node's cache. A "warm" run came next. CPU time is user and system time together, of the warm run. Peak memory is the larger of the two runs'.

| Query | `--cpu` | Wall time, cold | Wall time, warm | CPU time | Peak memory |
| ----- | ------- | --------------- | --------------- | -------- | ----------- |
| The example | 0 | 14.2 s | 13.6 s | 6.5 s | 63 MiB |
| | 2 | 9.2 s | 9.0 s | 9.3 s | 315 MiB |
| | 4 | 8.9 s | 8.7 s | 9.3 s | 396 MiB |
| `test.fasta` | 0 | 15.7 s | 16.0 s | 9.5 s | 41 MiB |
| | 2 | 9.2 s | 9.4 s | 12.3 s | 463 MiB |
| | 4 | 8.6 s | 9.1 s | 12.4 s | 392 MiB |
| Q14204, 4,646 residues | 0 | 93.3 s | 52.9 s | 45.2 s | 512 MiB |
| | 2 | 27.6 s | 27.4 s | 48.0 s | 1,503 MiB |
| | 4 | 17.6 s | 18.9 s | 51.6 s | 2,857 MiB |
| `titin-50000` | 0 | 1,153 s | 1,186 s | 1,103 s | 21,600 MiB |
| | 2 | 597 s | 603 s | 1,088 s | 42,976 MiB |
| | 4 | 369 s | 362 s | 1,087 s | 47,953 MiB |

- **Each query's tables were the same** at every `--cpu`, cold or warm, alone or at once.
- **Threads shorten the long queries.** Q14204 drops from 53 s to 27 s and 19 s, and `titin-50000` from 20 minutes to 10 and 6. The short ones gain less: they spend half their time waiting to read the pressed files.
- **Memory grows with the query's length, and with each thread.** `titin-50000` needs 21 GiB at `--cpu 0`, 42 GiB at `--cpu 2` and 47 GiB at `--cpu 4`.
- **Cold and warm runs mostly took the same time.** The exception is Q14204 at `--cpu 0`, at 93 s cold and 53 s warm. On a file system the node shares, dropping the node's cache may not make a run as cold as on a server's own disk.

### At Once

Copies of the same query, started together, warm, at `--cpu 0`:

| Query | Copies | Wall time, each | CPU time, each | Alone |
| ----- | ------ | --------------- | -------------- | ----- |
| The example | 2 | 111 s | 12 s | 13.6 s |
| | 3 | 47 s | 12 to 15 s | |
| Q14204 | 2 | 134 s | 51 s | 52.9 s |
| | 3 | 86 s | 50 to 53 s | |

Each copy's wall time grew far more than its CPU time: 8 times against 2 for the example. So the copies spent the time waiting on the file system, which other users share, and three at once, run after two, were faster than two. These numbers describe BeeGFS at that time, not a server. How many hmmscore jobs a server can run at once has to be measured on the server, with the pressed files on its own disk.

### What a Server Needs

- **Memory:**
  - `binHmm.h3f`'s 5.3 GB kept in the page cache, since every query reads all of it. A query reads from `binHmm.h3p`, 15.8 GB, only the models that pass the first filters;
  - plus each running query's peak: about 0.5 GiB at 5,000 residues and `--cpu 0`, and 21 GiB at 50,000, for titin. Each thread adds to it.
- **Disk:**
  - 67.1 GB for the kept files;
  - 18.5 GB more for the tarball, if fetching from a local copy;
  - another 67.1 GB while a new copy replaces an older one, since fetch checks the new files before moving them.

  At most about 153 GB.
- **Time at 50,000 residues:** about 20 minutes at `--cpu 0`, 10 at `--cpu 2` and 6 at `--cpu 4`, on these EPYC cores. If the API accepts the website's 50,000 residues, that sets its time limit for a job.

## The Sample

`hmmscore-sample-1` holds 14 families, chosen in task 7.4, each one whole: its family model and every subfamily's, so the best hit among them is the same as in the full library.

- **The example's hits:** every model that passes the CGI's cutoff, a full-sequence E-value of 1e-3, is one family's. The cutoff is `pantherScore.pl`'s `$distantHmmCutoff` (51), which the best-hit output (`-D B`) applies in `getBestHit` (338).
- **`test.fasta`'s hits:** 773 models in 56 families pass the cutoff. The sample has the ten families whose best models score highest.
- **The survey's checks:** the smallest family that shows each check on families or models that found something in the full library.
- **The library's shapes:** a one-subfamily family, a family with many subfamilies, and families with a `PTHRnnnnn..pir` model, as `binhmm-not-in-books` counts both kinds of model together.

| Family | Model files | Bytes | Why it's in |
| ------ | ----------- | ----- | ----------- |
| `PTHR18976` | 8 | 1,569,710 | The example's hits: all 6 models that pass 1e-3. Its best is the example's best on the full library, `PTHR18976.SF2.pir`, 439.0 bits, E-value 7e-131 |
| `PTHR10489` | 45 | 7,689,571 | `test.fasta`'s best on the full library: `PTHR10489.SF627.pir`, 310.5 bits, E-value 9.1e-92 |
| `PTHR24232` | 39 | 6,515,282 | `test.fasta`'s hits: its best here scores 189.5 bits, the family model |
| `PTHR24226` | 5 | 846,333 | `test.fasta`'s hits: 176.0 bits, the family model |
| `PTHR24229` | 39 | 7,660,562 | `test.fasta`'s hits: 175.6 bits, `SF112` |
| `PTHR24237` | 10 | 1,653,140 | `test.fasta`'s hits: 170.3 bits, the family model |
| `PTHR24231` | 19 | 3,141,568 | `test.fasta`'s hits: 170.3 bits, the family model |
| `PTHR24225` | 33 | 5,499,570 | `test.fasta`'s hits: 167.4 bits, the family model |
| `PTHR24228` | 29 | 5,133,222 | `test.fasta`'s hits: 166.3 bits, `SF8` |
| `PTHR24230` | 45 | 7,780,675 | `test.fasta`'s hits: 165.2 bits, the family model |
| `PTHR24234` | 11 | 1,812,733 | `test.fasta`'s hits: 163.3 bits, the family model |
| `PTHR24068` | 165 | 14,117,172 | `name-without-model`: `names.tab`'s `PTHR24068:SF521` has no model file. The smaller of the two families. It also has many subfamilies, 164, and a `..pir` model |
| `PTHR35774` | 2 | 33,684 | A one-subfamily family, the smallest showing `model-legacy-id`, `one-subfamily-copy` and `binhmm-not-in-books` |
| `PTHR34093` | 4 | 927,142 | A `..pir` model, of one sequence with a model mask (above), which the CGI aligns with the family's model of 511 positions |

Every check on families or models that found something in the full library finds something in the sample too, and no other does. `tests/test_hmmscore_sample_data.py` checks this.

- **Its size:** 33,247,636 bytes as a tarball, and 134,680,343 unpacked, in 460 files: 454 model files, `names.tab`'s 455 lines, the README and the four pressed files, of 456 models. It has no flat `binHmm`, as the library has none.
- **How it was pressed:** its records were cut out of `binHmm.h3m` and pressed as they are by HMMER 3.4, in the engine image on amd64 (decision of 2026-11-10, above), with the `sample build` of `b1a6db6`. Its `binHmm.h3m` is those records, byte for byte; the build checks that it is.
- **Its scores, on amd64:** the same as the full library's for all 11 of the example's domains. For `test.fasta`, 256 of the 257 models both hit score the same; `PTHR24228.SF63` scores 47.7 bits instead of 47.8, from the sample's 3.4-pressed `.h3p`. Its E-values are smaller than the full library's: `hmmscan` multiplies each P-value by the 456 models searched instead of 144,361.

## HMMER 3.1b2 Against 3.4

Production most likely ran HMMER 3.1b2 (engine developer, 2026-11-09). Task 10.1 compared it with 3.4, the image's, on amd64:

| Where | 3.1b2 | What was compared | Result |
| ----- | ----- | ----------------- | ------ |
| The full library, on Endeavour | Built from its source tarball, sha256 `dd16edf4385c1df072c9e2f58c16ee1872d855a018a2ee6894205277017b5536`, with `CFLAGS="-O3 -fcommon"` | `hmmscan`'s tables for the example and `test.fasta`, against the shipped pressed files, without their `#` lines | Identical |
| The sample, on the Mac, under Docker's emulated amd64 | Bioconda's `hmmer` 3.1b2, `quay.io/biocontainers/hmmer:3.1b2--3`, digest `sha256:e7b1a7a131b7acd6546a6a77cfffc3007fc80f74f7b40b5c660fe29fda122158` | Each version pressed its own copy of the sample's models. Then `hmmscan`'s tables for the example (11 lines) and `test.fasta` (282 lines), without their `#` lines | Identical |
| The sample, likewise | The same | `hmmsearch` of each best hit's model file against its query, as the CGI runs it (`scoreAlignXml.cgi:140`): `PTHR18976.SF2.pir`'s for the example and `PTHR10489.SF627.pir`'s for `test.fasta`. Compared from "Domain annotation for each sequence" to "Internal pipeline statistics summary:" | Identical |

So production's numbers survive the upgrade to 3.4, on amd64, with the same pressed files. The two versions' presses of the sample differ only in 4,653 bytes of `.h3p`, which change no table.

Neither version reproduces the shipped `.h3p`. Bioconda's 3.1b2 presses the first 25,000 models' records into the shipped `.h3m`, `.h3f` and `.h3i`, as 3.4 does. But its `.h3p` differs from the shipped one in 5,462,372 bytes, and from 3.4's in 400,138. So the shipped `.h3p` came from a build that neither reproduces, and pressing the sample with 3.1b2 instead of 3.4 wouldn't bring it closer to production.

## What It Means for port-hmmscore

**The legacy readings to match:**

- **A model's HMM ID** is `runHmmscan`'s (`pantherScore.pl` 387 to 389): the name split on `.`, with `:SFn` added when its second part starts with `SF` and a digit. So the 5,450 subfamily models no file holds read as their subfamily, and the 668 `..pir` models as their family. `hmmscore/legacy.py`'s `model_id` reads them so.
- **`names.tab`'s keys** are `getHmmNames`'s, which the strict reader matches on every line.
- **The best hit** is `getBestHit`'s (316 to 340):
  1. the highest full-sequence bit score;
  2. for that score, the smallest E-value;
  3. every model with that score and E-value.

  Only then does the 1e-3 cutoff apply, to the best hit alone (338). If it fails, the sequence gets no result, even when a lower-scoring hit passes: `next` leaves the subroutine and moves the caller's loop to the next sequence. Scores and E-values are compared as `hmmscan` prints them.
- **The alignment** is `hmmsearch` of the model file at the best hit's HMM ID against the query (`scoreAlignXml.cgi` 136 to 140). For the 6,118 models no file holds, that file holds another model than the one that scored. For 5,279 of them it's the same model up to rounding. For the other 839, including every `..pir` model, it's a different one ([binHmm as Text](#binhmm-as-text)).

**How the one-subfamily copies are reported.** In each of the 5,450 one-subfamily families, a hit on the subfamily's own model, `PTHRnnnnn.SFn.pir`, is reported as `PTHRnnnnn:SFn`, and a hit on the family's model as `PTHRnnnnn`. In 5,279 of them the two models are the same up to rounding. So whether a sequence is reported in the family or in its subfamily can turn on the fifth decimal of a score. The port reports the model that scored best, as the CGI does.

**HMMER differences to propose as divergence rows:** none. On amd64, 3.4 gives 3.1b2's tables and alignments. Two things matter for the port's tests:

- **Parity on amd64.** On arm64, `hmmscan` gives some scores a different last digit, and can move a domain near a cutoff ([hmmscan on arm64](#hmmscan-on-arm64)). A golden made on amd64 can fail on arm64 for that alone. Where the two differ, keep a version for each, as the sample's committed table does.
- **Goldens made on the sample are for the sample.** Its `.h3p` is 3.4's, not the shipped one, so a few domains near a cutoff score differently from the full library: one of the 257 models `test.fasta` hits in both. The Perl and the port read the same sample, so parity holds. The staging run on the full library gives production's numbers.

**What a server needs, against the hosting server.** The engine developer read the hosting server's numbers on 2026-11-10, with `nproc`, `free -g`, and `df -h` of its data folder:

| | The hosting server | What hmmscore needs ([What a Server Needs](#what-a-server-needs)) |
| --- | ------------------ | ----------------------------------------------------------------- |
| CPUs | 2 | 1 for each `hmmscan` at `--cpu 0`, the default |
| Memory | 7 GiB in all, 5 GiB of it available, and 7 GiB of swap | `binHmm.h3f`'s 4.9 GiB in the page cache, plus each running query's peak: 0.5 GiB for Q14204's 4,646 residues, 21 GiB for `titin-50000` |
| Free disk where the data folder is | 189 GiB (203 GB), on `/home` | At most 153 GB: 67.1 GB kept, 18.5 GB for a local copy of the tarball, and 67.1 GB more while a new copy replaces an older one |

- **The disk is enough,** with about 50 GB to spare at the peak, if nothing else on `/home` grows.
- **The memory isn't.**
  - Keeping `binHmm.h3f` cached would take nearly all the memory available, so a query may have to read it from disk each time. That wasn't measured on the server.
  - `titin-50000` needs 21 GiB at `--cpu 0`, more than the server's memory and swap together. It's the only 50,000-residue query measured, and it hits titin's own very long models, so other sequences of that length may need less. Q14204's 0.5 GiB fits.
- **The two CPUs** run at most two `hmmscan`s at once at `--cpu 0`, and the other services' jobs share them.

So before hmmscore runs there, it needs more memory, a residue limit below the website's 50,000, or both. That's for `port-hmmscore` and the deploy to decide, with the API developer.
