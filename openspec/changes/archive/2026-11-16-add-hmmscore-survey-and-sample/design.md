# Design

## Context

See proposal.md for why. This change follows these decisions and doesn't revisit them:

- **[tech-stack.md](../../../docs/design/tech-stack.md), Shared Concerns:**
  - **Data:** versioned data folders, and a sample picked from a one-time survey;
  - **Environments:** the sample on developer machines and in CI, the full data on staging;
  - **Developer platforms:** everything runs in the image through `docker compose`, on amd64 and arm64.
- **tech-stack.md, Engine conditions:**
  - 1: a library with a CLI;
  - 2: `core/` first, then one submodule per service;
  - 3: parity tests before porting.
- **tech-stack.md, Pinning Tool Versions:** HMMER 3.4 in the image.
- **[api-stack.md](../../../docs/design/api-stack.md):** the tooling (uv, Ruff with the `S` rules, basedpyright strict, pytest).
- **`engine-core`'s requirements:**
  - each service's data under `<service>/<version>/`, which puts this data under `hmmscore/19/` rather than tech-stack.md's shared `/data/panther/19/`;
  - checksum manifests;
  - the `data` test marker.
- **The precedents this change copies:**
  - [`add-csnp-survey-and-sample`](../archive/2026-10-29-add-csnp-survey-and-sample/design.md): the streamed survey, the sample as a pre-release asset, the reproducible tarball and the safe fetch;
  - [`port-refmap`](../port-refmap/design.md): a pinned public tarball, and fetching that never uses a member's name as a path.

### The engine today

| Module | What this change uses |
| ------ | --------------------- |
| `core/data.py` | `service_folder("hmmscore", "19", data_dir)`, `DataFolderError`, `MissingDataError` |
| `core/manifest.py` | `HashingReader`, `read_manifest`, `checksums`, `verify` and `sha256_file`. A manifest's `files` maps each path, from the data root, to its sha256 |
| `core/download.py` | `download()`: HTTPS only, redirects checked, User-Agent `panther-engine` |
| `core/tools.py` | `hmmscan`'s version pattern in `TOOLS`, to check `hmmpress`'s version |
| `csnp/survey.py` | `open_stream` and `member_lines`: a gzipped tar read as a stream, with tarfile's default buffer (cSNP's lesson) |
| `csnp/sample.py` | `write_tarball` (reproducible) and `unpack` (regular files and folders under one top folder only) |
| `tests/conftest.py` | the `data(*services)` marker, `DATA_MANIFESTS`, `PANTHER_REQUIRE_DATA`, `make_tool` |

### How the legacy code uses the library

The website's path is `scoreAlignXml.cgi`, which runs `pantherScore.pl -D B`, on the prod library.

```text
pantherScore.pl:377   hmmscan --domtblout <tmp> <binHmm library>/globals/binHmm <query>
pantherScore.pl:387   model name -> HMM ID: split on ".", add ":SFn" if the 2nd part =~ /^SF\d+/
scoreAlignXml.cgi:136 HMM ID -> <library>/books/<fam>/hmmer.hmm, or books/<fam>/<SFn>/hmmer.hmm
scoreAlignXml.cgi:137 die unless the file exists and isn't empty
scoreAlignXml.cgi:140 hmmsearch <that file> <query>
pantherScore.pl:299   getHmmNames: globals/names.tab, read for -n, which the CGI doesn't pass
```

The port shows names from `names.tab`, which is in sync with the database (engine developer, 2026-11-09). So scoring reads:

- `globals/binHmm`'s four pressed files;
- `globals/names.tab`;
- every `books/**/hmmer.hmm`.

The README says the `cluster.pir` and `tree.tree` in each family were for coding-SNP analysis. Nothing here reads them.

### The tarball, as far as it has been read (2026-11-09)

- **The download:** `https://data.pantherdb.org/ftp/hmm_scoring/19.0/PANTHER19.0_hmmscoring.tgz`. It's 18,494,793,691 bytes, `Last-Modified` 2024-04-02, and the server accepts ranges. The same file is under `current_release/`. A download here ran at about 6 MB/s, so one pass from the network takes about 50 minutes.
- **The prefix:** every member is under `target/famlib/rel/PANTHER19.0_altVersion/hmmscoring/PANTHER19.0/`.
- **The first members,** from the first 3 GiB of the stream:

  | Member | Bytes |
  | ------ | ----- |
  | `README` | 4,210 |
  | `globals/binHmm.h3f` | 5,265,690,109 |
  | `globals/names.tab` | 7,640,523 |
  | `globals/binHmm.h3i` | 6,929,429 |
  | `globals/binHmm.h3p` | 15,826,161,352 |

  The rest was unread then. The survey has read it all (task 5.1): `binHmm.h3m`, 13,554,818,829 bytes, then `books/`. There's no flat `binHmm`. Its results are in [hmmscore-library-survey.md](../../../docs/parity/hmmscore-library-survey.md).
- **The README:**
  - it counts 15,683 family and 128,012 subfamily HMMs;
  - it gives the layout and `names.tab`'s format;
  - it carries a GPL v2 notice and InterPro's copyright statement, which allows copying and redistribution "provided that this Copyright statement is reproduced with each copy".
- **`binHmm.h3f`:**
  - it starts with `0xb3e6e6f3`, HMMER's magic number for format 3/f;
  - its first model is `PTHR32401.SF33.pir`, 274 positions long.
- **A first look at PANTHER 19's other downloads,** which the engine developer set aside in favour of this tarball, found:
  - models in format `HMMER3/f [3.1b2 | February 2015]`, built 2024-03-08;
  - a `names.tab` of the same size, 7,640,523 bytes, whose 143,695 lines all have the two expected shapes;
  - 5,450 one-subfamily families. In each of the five checked, the subfamily's file is the family's model, byte for byte, named `PTHRnnnnn.orig.30.pir`.

  The survey checks each of these in this tarball.

### HMMER 3.4, the version the image pins

Checked in its source on 2026-11-09, the tarball the `Dockerfile` pins (`ca70d94f…`):

- **Its amd64 and arm64 builds write and read the same pressed format.**
  - `src/impl_sse/io.c` and `src/impl_neon/io.c` use the same magic numbers. For format 3/f, they're `0xb3e6e6f3` for `.h3f` and `0xb3e6f0f3` for `.h3p`.
  - Both write the same fields in the same order, as 16-byte vectors.
- **It reads format 3/f,** the shipped files' format, and 3.1b2's.
- **`hmmscan` doesn't need the flat file.** `src/p7_hmmfile.c` opens `<name>.h3m` when `<name>` itself is absent, and requires `.h3f`, `.h3p` and `.h3i` beside it.
- **Measured in apply (2026-11-10), it doesn't compute quite the same numbers on each architecture.** From the same pressed files, `hmmscan` on arm64 gives a few last-digit differences from amd64, and a domain near a cutoff can move its envelope. Production's numbers are amd64's ([the survey doc](../../../docs/parity/hmmscore-library-survey.md)).
- **It reads a text model's probabilities in single precision,** `expf(-1.0 * atof(tok1))`. So it can't press the shipped text models into the shipped `.h3m`'s floats.

## Goals / Non-Goals

**Goals:**

- **A survey that runs once on a developer laptop:**
  - it reads the tarball front to back in one pass;
  - its memory stays bounded;
  - it never unpacks to disk.
- **A pin that checks all of the roughly 144,000 model files,** without a 15 MB manifest in the package and the API image.
- **A fetch that never leaves a half-written `hmmscore/19/`,** and, when it downloads, needs no disk for the 18.5 GB tarball.
- **A sample small enough for CI:**
  - it covers every variant the survey finds, and the example inputs;
  - its pressed files work on both architectures.
- **The numbers the port, the API and the server need:**
  - sizes, times and memory;
  - whether HMMER 3.4 changes anything that 3.1b2 gave.

**Non-Goals:**

- **A general HMMER file parser.** The reader gives the format line, `NAME`, `LENG` and each model's bytes, which is what the checks need, not the model's parameters.
- **Reading the binary formats.** The survey reads only the pressed files' magic numbers and, if it must, the index's list of names (decision 3).
- **Choosing readings for the port.** The survey measures where `pantherScore.pl`'s readings differ, and the port decides.
- **The production server's layout and deploy.**

## Decisions

### 1. Module layout

```text
engine/src/panther_engine/
  core/archive.py      moved from csnp: open_stream, member_lines, write_tarball, unpack
  core/download.py     + open_https(url): the response as a stream; download() uses it
  hmmscore/library.py  the layout's patterns, names.tab and HMM text readers, LibraryFormatError
  hmmscore/legacy.py   pantherScore.pl's readings, each citing its line at the pinned commit
  hmmscore/survey.py   the streamed survey, and its report as text and JSON
  hmmscore/data.py     the pin (data.json): manifest, fetch, verify
  hmmscore/sample.py   build, fetch, verify (sample.json)
  hmmscore/cli.py      survey; data manifest|fetch|verify; sample build|fetch|verify
```

- **`LibraryFormatError` is never an `InputError`,** as in cSNP. A broken library file isn't the submitter's fault, and its message names a file and a line.
- **The readers take lines and a name for errors,** so the survey can feed them tar members and the port can feed them files.

### 2. Strict readers, with `pantherScore.pl`'s readings measured beside them

| Value | `pantherScore.pl` (`legacy.py`) | Strict reader |
| ----- | ------------------------------- | ------------- |
| A `names.tab` key | `split(/\./, $line)` on the whole line. The key is the 1st part, then `:` and the 2nd part unless it's empty or `mag` (`getHmmNames`, 306 to 310) | The whole line is `PTHRnnnnn.mag.mod` or `PTHRnnnnn.SFn.mod`, a tab, then the name |
| A repeated key | The later line wins, by hash assignment (310) | Format error |
| A model's HMM ID | `split(/\./, $target)`, then `:` and the 2nd part if it matches `/^SF\d+/`, unanchored (387 to 389) | None: the ID rule is the legacy one. The survey counts names of other shapes |
| Line ends | `chomp` drops only `\n` | A carriage return is a format error |

**What the survey's counts mean:**

- **Zero differences:** the strict reader is safe for the port.
- **Any difference:** the port must use the legacy reading, or log a divergence.

The model-ID rule has no strict alternative. It is the behaviour M1 must match, so the port takes it from `legacy.py`.

### 3. One streamed pass, `globals/` before `books/`

The survey opens the tarball with `core/archive.py`'s `open_stream`, through a `HashingReader` for the sha256 and size.

- **Every member is classified by its path below the prefix:**
  - `README`;
  - `globals/names.tab`;
  - `globals/binHmm`, or its `.h3f`, `.h3i`, `.h3m` or `.h3p`;
  - `books/PTHRnnnnn/hmmer.hmm`;
  - `books/PTHRnnnnn/SFn/hmmer.hmm`;
  - `books/PTHRnnnnn/cluster.pir` and `tree.tree`.

  Anything else is unexpected until the survey shows what it is.
- **The order helps.** `globals/` comes before `books/`, so `binHmm`'s model list and `names.tab` are known before the first model file arrives.
- **What it holds in memory:**
  - per `binHmm` model: its name, and with the flat file the sha256 of its text;
  - per `names.tab` line: its ID;
  - per model file: its path, sha256, `NAME` and `LENG`.

  That's three tables of about 144,000 small rows: tens of MB. The peak goes in the Notes.
- **`binHmm`'s model list:**
  - **With a flat `binHmm`,** from its text, with each model's sha256.
  - **Without one,** from `binHmm.h3i`, the 6.9 MB index `hmmpress` writes in Easel's SSI format (`easel/esl_ssi.c`): a header, then each name with its offset in `.h3m`. Ordering by offset gives `binHmm`'s order.

  Without the text, the survey can compare models with `books/` by name only. So the same check runs once on the unpacked library, with `hmmconvert` writing `binHmm.h3m` out as text (task 7.1).

  By name, it reports each name `binHmm` holds that no model file does (`binhmm-not-in-books`), with the model file the CGI would align its hits with. PANTHER 19's `binHmm` holds 6,118: in each one-subfamily family the subfamily's own model, and in 668 families a second family-level model named `PTHRnnnnn..pir` (tasks.md, Notes).
- **The pressed files:** the survey reads each one's first 4 bytes for its magic number, then reads past it.
- **Pinning and the sample read the tarball in the same way:** `data manifest` and `sample build` share the member classification and the stream.
- **A local copy is the norm.** Each pass reads 18.5 GB, which takes about 50 minutes from the network, so the commands that read the whole tarball take a local file. The developer downloads once, with `curl -C -` to resume.
- **Only `data fetch` downloads by itself,** and only where its container can reach `data.pantherdb.org`. On the hosting server it can't:
  - the server's outbound HTTPS goes through a TLS-inspecting proxy whose CA the image doesn't trust;
  - a CA given to the build as a secret leaves nothing in the image.

  So there, as for refmap's data (`docs/deployment/runbook-server.md`), the host downloads the tarball with `curl -C -`, which also resumes, and `fetch` reads it with `--tarball`.

**Rejected:**

- **Unpacking first.** It needs disk for everything, `cluster.pir` and `tree.tree` included, and writes it all twice.
- **One pass per check.** Each pass costs the whole tarball.

### 4. The pin: a small `data.json` and a generated `books.sha256`

```json
{
  "version": "19",
  "tarball": {"url": "https://data.pantherdb.org/ftp/hmm_scoring/19.0/PANTHER19.0_hmmscoring.tgz",
              "bytes": 18494793691, "sha256": "…"},
  "prefix": "target/famlib/rel/PANTHER19.0_altVersion/hmmscoring/PANTHER19.0/",
  "books": {"files": 143695},
  "files": {"hmmscore/19/README": "…",
            "hmmscore/19/books.sha256": "…",
            "hmmscore/19/globals/binHmm.h3f": "…", "…": "…",
            "hmmscore/19/globals/names.tab": "…"}
}
```

- **`files` is in `core/manifest.py`'s format,** so `verify()` checks these files unchanged:
  - the README;
  - each `globals/` file the tarball has;
  - `books.sha256`.
- **`books.sha256` has one line per model file, as `sha256sum` writes them:**
  - the line is `<sha256>  books/PTHR10000/SF55/hmmer.hmm`;
  - lines are sorted by path, as bytes;
  - each ends in LF.

  Its own sha256 is in `files`, so it pins every model file through one digest. `shasum -a 256 -c books.sha256` checks the files by hand from `hmmscore/19/`.
- **It is generated, never committed or edited.**
  - `data manifest` streams the tarball once, hashing every kept member, and computes `books.sha256` in memory to pin its digest.
  - `data fetch` writes the file into the data folder from the hashes it computed while extracting.
- **`data verify`:**
  1. Run `verify()` on `files`.
  2. If `books.sha256` matched, check every model file it lists.
  3. Print the missing and differing files, the first 20 of each with the counts, as cSNP's full verify does.

**Why not a per-file manifest in the package?** At about 108 bytes a file, cSNP's `full.json` is 2.8 MB for 25,826 files. This library's would be about 15 MB, in the repository on every release and in the API image.

**Rejected:**

- **That per-file JSON.** Its size, as above.
- **The tarball's sha256 alone.** A deploy must check the data folder itself before it takes traffic, as cSNP's does (`fix-csnp-blast-handling`).
- **The per-file list as a release asset.** That's a second home for the pin outside git, and a server would need GitHub to verify.

**A new PANTHER release** gets a new URL and prefix. `data manifest` writes a new `data.json`, and the data goes under `hmmscore/<version>/`.

### 5. Fetch streams, keeps what scoring reads, checks, then moves

```text
data.json --> verify the data folder: it matches? --> done, nothing downloaded
          --> open the tarball: core/download.py's open_https(url), or --tarball FILE
          --> HashingReader --> open_stream
              each member below the prefix, by its kind (decision 3):
                README, globals/<known file>, books/PTHRnnnnn/[SFn/]hmmer.hmm
                    --> <root>/.hmmscore-fetch-*/hmmscore/19/<path>, hashed as it's written
                cluster.pir, tree.tree  --> read past
                anything else           --> stop, name it, remove the temporary folder
          --> size and sha256 == the pin?                    no --> stop, name both, remove it
          --> write books.sha256 from the hashes; verify against files and the model count
          --> os.replace each file into <root>/hmmscore/19/
```

- **A member's name is never used as a path,** as in refmap. The path is rebuilt from a validated match: `PTHR\d{5}` and `SF\d+` folders, and fixed file names. So `..`, absolute paths and links can't reach the filesystem.
- **The tarball is never saved,** unlike refmap's 157 MB. So files are written before the tarball's sha256 is known, but only into the temporary folder in the data root. That folder is removed unless every check passes, so nothing unchecked reaches `hmmscore/19/`.
- **Disk:**
  - the kept files once, since `os.replace` within one filesystem doesn't copy;
  - twice while replacing an older copy;
  - plus the 18.5 GB tarball until the fetch ends, wherever it's downloaded first, as on the hosting server (decision 3).
- **Time:** mostly the download. With no resume, a dropped connection starts over. On a slow or unreliable link, and on the hosting server, download with `curl -C -` and pass `--tarball`.
- **Already fetched:** `verify` runs first and hashes everything. That's minutes, for a command run once per release.

### 6. Pressed files: the shipped ones for the full library, the pinned `hmmpress` for the sample

- **The full library keeps its shipped `.h3f`, `.h3i`, `.h3m` and `.h3p`,** pinned like every other file. HMMER 3.4 reads their format on both architectures (Context).

  **The press check (task 7.2), on amd64:**
  1. Press the shipped models with 3.4's `hmmpress`.
  2. Compare the four files with the shipped ones, byte for byte.
  3. If they differ, compare `hmmscan`'s tables for the example and `test.fasta` against both sets.

  If the tables differ, that's recorded in the survey doc. Pressing at fetch is then decided before `port-hmmscore` starts (Notes, Decisions during apply).

  **The outcome (2026-11-10):** 3.4 can't reproduce the shipped files, and its re-pressed files move a few `hmmscan` domains near a cutoff. On amd64, 3.1b2 and 3.4 give exactly the shipped files' tables. So the full library keeps the shipped files, and fetch never presses (engine developer, 2026-11-10).
- **The sample is pressed by `sample build`,** since no tool cuts models out of pressed files.
  1. The build writes the chosen families' models to `binHmm` in its temporary folder.
  2. It presses that with the pinned `hmmpress` in the engine image.
  3. The tarball carries the four pressed files, pinned like every file. It carries `binHmm` itself only when the library has a flat one.
- **`fetch` never presses.** So CI's native job and machines without HMMER can fetch, and every pressed file has a pin.
- **Making the build reproducible:**
  - `hmmpress` runs inside the build's temporary folder on the relative name `binHmm`, so the `.h3i` records `binHmm.h3m`, not a temporary path;
  - the build refuses an `hmmpress` whose version line isn't the pinned 3.4.
- **What the build presses:**
  - **With a flat `binHmm` in the tarball,** its text models for the chosen families, byte for byte, in its order.
  - **Without one,** as for PANTHER 19, the chosen families' records cut out of `binHmm.h3m`. The index gives each model's offset in `binHmm.h3m`, whose records are contiguous, so the build cuts them as the tarball streams past, before `books/`.

    `hmmpress` reads the records as a binary model file. It gives them back in the sample's `binHmm.h3m` byte for byte, which the build checks, and it gives back the shipped `.h3f` too. Only `.h3p` differs, as from any 3.4 press, so a few domains near a cutoff can score differently from the full library (decision 7).

    The model files can't stand in: `binHmm` holds models that no model file holds (decision 3). Nor can `hmmconvert`'s text of the records. It's each model file byte for byte, apart from the format line, but 3.4 reads text in single precision (Context), so pressing it would change about 1 probability in 1,000 by one unit in the last place (engine developer, 2026-11-10).
- **Built on one architecture, read on both, with a committed table for each.** The test in the spec's "both architectures" requirement runs on both `engine-image` legs. Each leg checks its own architecture's table, as 3.4 computes a few numbers differently on each (Context; engine developer, 2026-11-10).

**Rejected:**

- **Pressing at fetch.** Machines without HMMER couldn't fetch, and the files pressed there couldn't be pinned.
- **Shipping the shipped pressed files cut down.** No tool cuts a pressed database. The `.h3f` and `.h3p` records hold offsets into the other files, which such a tool would have to rewrite.

### 7. The sample: families, E-values and the release

**Families,** chosen in apply and recorded in the survey doc:

- **The example inputs' families:**
  - the families of the site's example (human APOE) hits on the full library that pass the CGI's 1e-3 cutoff, up to ten;
  - the families of `test.fasta`'s sequences, the sample input published with `pantherScore2.2`.

  With these, the best-scoring model for each is the full library's (spec, "The example's best hit").
- **The smallest family that shows each family- or model-level check** the survey finds non-zero.
- **A one-subfamily family,** and **a family with many subfamilies.**
- **A family with a `PTHRnnnnn..pir` model.** `binhmm-not-in-books` counts both kinds of model together, so its smallest example alone would leave one kind out.

Each family is whole: its family model and every subfamily's. So the best-hit choice between them is as in the full library.

**E-values differ from the full library's,** and that's expected.

- `hmmscan` multiplies each P-value by the number of models searched. The sample holds hundreds, the library about 140,000.
- E-values change, and so do the hits that pass a cutoff. The best-scoring model doesn't.
- Scores barely change. The sample's `.h3p` is 3.4's, not the shipped one (decision 6), so a few domains near a cutoff can score differently, as when the full library is re-pressed.
- The Perl and the port will read the same sample, so parity holds.
- Production's numbers come from the full library, in `port-hmmscore`'s staging run.
- Passing `-Z` isn't an option. The CGI doesn't, and the reference must run as it is.

**The release:**

- **The tag:** `hmmscore-sample-<n>`, with the asset `hmmscore-sample-<n>.tar.gz`, created with `--prerelease` (cSNP's lesson) and never replaced.
- **`hmmscore/sample.json` holds:**
  - the tag;
  - the asset's name, URL, sha256 and size;
  - the source tarball's name and pinned sha256;
  - the HMMER version that pressed it;
  - the families;
  - `files`.
- **The tarball** is written by `core/archive.py`'s `write_tarball`: sorted, USTAR, owned by 0, dated 0, gzip at level 9 with no name or date.
- **The README goes in as it is.** Its copyright statement must go with each copy.

### 8. The shared helpers move to `core/`

- **`core/archive.py` takes:**
  - `open_stream` and `member_lines` from `csnp/survey.py`;
  - `write_tarball` and `unpack` from `csnp/sample.py`. `unpack` gains the top folder its members must be under, `csnp` or `hmmscore`.

  csnp's imports change. Tests that exercise only the helpers move to `tests/test_archive.py`. It's mechanical, like refmap's move of `download()`.
- **`core/download.py` gains `open_https(url)`.** It's a context manager yielding the response, HTTPS only, with the URL a redirect led to checked, as `download()` checks it. `download()` is rewritten on top of it.
  - Its timeout applies to each socket read, not to the whole download, so a long download that keeps flowing doesn't time out.

### 9. Measurements, recorded in the survey doc

Each number is recorded with its machine, its architecture, and whether it ran natively or in the image.

- **The library:**
  - the tarball's unpacked size;
  - the kept bytes;
  - `fetch`'s time and peak memory.
- **`hmmscan` on the full library, in the engine image.** The queries:
  - the example (317 residues);
  - `test.fasta`'s sequences;
  - a sequence of about 5,000 residues;
  - one of 50,000 residues, the website's limit for HMM scoring (`SequenceSearchForm.java:84`, once the header and whitespace are removed). The API has no hmmscore input rule yet. Its cSNP limit is the same.

  For each: wall time with the file cache cold and warm, and peak memory, at each of these settings:
  - **`--cpu 0`, no worker threads.** It's 3.4's default for `hmmscan` (`src/hmmscan.c`: "hmmscan is i/o bound on almost all systems"), and `pantherScore.pl` passes no `--cpu` (377). Its `-c` option is read but never used;
  - **`--cpu 2` and `--cpu 4`,** to show whether threads shorten one job.

  The tables must be the same at every setting.
- **Queries at once:** two and then three copies of the example, and of the 5,000-residue query, run together with the cache warm and `--cpu 0`. Each one's wall time, against its time alone, shows how many hmmscore jobs a server can run at once.
- **What a server needs,** stated in the survey doc for the API and the deploy:
  - **memory:** `binHmm.h3f` kept cached, since every query reads all of it, plus each running query's peak. A query reads from `binHmm.h3p` only the models that pass the first filters (`src/p7_pipeline.c`, 739 to 742), so how much of it is read depends on the query;
  - **disk:** the kept files, plus the tarball while it's on the host, plus the kept files again while replacing an older copy (decision 5);
  - **time:** the 50,000-residue query's, which sets the API's time limit for a job.
- **The press check** (decision 6).
- **HMMER 3.1b2 against 3.4.**
  - **The setup:** 3.1b2 from Bioconda's `linux-64` build, in a throwaway `linux/amd64` container, not a `Dockerfile` stage.
  - **The runs:** on the sample, each version presses its own copy of the sample's models, its `binHmm.h3m`, and runs:
    - `hmmscan` on the example and `test.fasta`;
    - `hmmsearch` of each best hit's model file against the example, as the CGI runs it.
  - **What's compared:**
    - the tables, without their `#` lines;
    - each alignment, from "Domain annotation for each sequence" to "Internal pipeline statistics summary:".
  - **The full library on amd64,** with the shipped pressed files, if such a machine is at hand. It's not required.
  - **Identical:** production's numbers survive the upgrade.
  - **Not identical:** each difference goes in the doc, for `port-hmmscore` to propose as a divergence row.

### 10. CI and the tests

- **`conftest.py`:** `DATA_MANIFESTS["hmmscore"]` is `hmmscore/sample.json`, and the `hmmscore_data` fixture gives `data_folder() / "hmmscore/19"`.
- **`ci.yml`, the `engine` job:**
  - an `actions/cache` step on `.data/hmmscore`, keyed `hmmscore-sample-${{ hashFiles('engine/src/panther_engine/hmmscore/sample.json') }}`;
  - then `uv run panther-engine hmmscore sample fetch --data-dir ../.data`, which on a hit only verifies.
- **The `engine-image` legs:** the same key, with the fetch run in the image into `/fetch`, as for the other data.
- **The cross-architecture test:**
  - it's marked `tools("hmmscan")` and `data("hmmscore")`, so it runs where the tools are, in both image legs;
  - the query is the site's HMM scoring example, in hmmscore's own copy, `engine/tests/golden/hmmscore/example/apoe.fasta`:
    - it holds the help page's ten lines as written (`tips_exampleHmmScoreInput_content.jsp`);
    - they go under `>sequence`, the name `scoreAlignXml.cgi` gives a sequence without a header (93 to 95);
    - they're the same 317 residues as cSNP's `example/apoe.fasta` (checked 2026-11-09), but each service's tests read their own file, so a change to one service's example never changes the other's tests;
  - the committed tables are `engine/tests/golden/hmmscore/sample-hmmscan/amd64/apoe.domtblout` and `arm64/apoe.domtblout`, with their `#` lines removed. Each leg checks its own architecture's;
  - `engine/tests/golden/hmmscore/README.md` says where each file comes from, as cSNP's does, and that both tables are regenerated when the sample or HMMER changes.

  It guards the sample and the tool, like cSNP's step-1 BLAST golden. It isn't parity.
- **Fixtures:**
  - hand-written files under `engine/tests/fixtures/hmmscore/`, which `.gitattributes` marks `-text`, so the carriage-return cases stay byte-exact;
  - small tarballs built in `tmp_path` for the survey, manifest, fetch and sample tests, with the pins passed in.

| Marker | What's tested |
| ------ | ------------- |
| None | The readers and legacy readings on the fixtures. The survey, `data manifest`, `data fetch` and `verify`, and the sample's build, fetch and verify, on small built tarballs. The moved helpers. The command line |
| `data("hmmscore")` | The sample against its manifest. Every sample model file against the pin's `books.sha256` lines, committed with the sample's families. The survey on the sample tarball ("Every variant") |
| `tools("hmmscan")`, `data("hmmscore")` | Each architecture's committed table. The example's best model |

### 11. The shared docs

Task group 1 records the engine developer's answers of 2026-11-09:

- **`CLAUDE.md`:**
  - the gotcha on the two copies of the HMM scoring CGIs;
  - hmmscore's data line;
  - `alignOnTheFly.cgi`'s row.
- **`tech-stack.md`:**
  - hmmscore's Data line;
  - its two open questions;
  - the Shared Concerns data table and sample;
  - a HMMER note in Pinning Tool Versions;
  - the Status line.

Each answer names the engine developer and the date, as earlier answers do.

## Risks / Trade-offs

- **[The tarball holds something unexpected after `.h3p`]** Examples: no `.h3m`, another `globals/` file, or members out of order. → The survey lists every member before anything depends on it. `data manifest` and `fetch` refuse what they don't expect. The design is adjusted in apply, and recorded in the Notes.
- **[A pass takes too long from the network]** → Download once and pass the local copy. Each pass's time goes in the Notes.
- **[The survey uses too much memory]** → It holds names and hashes, never model text. Peak memory goes in the Notes.
- **[3.4's `hmmpress` doesn't reproduce the shipped files, and the tables differ]** → It happened. The full library keeps the shipped files, and the sample presses the shipped records as they are (decision 6).
- **[The sample's pressed files behave differently on amd64 and arm64]** → The files don't, but `hmmscan` does: it computes a few numbers differently on each architecture, from the same files. Each architecture has its own committed table (decision 6).
- **[The sample's E-values aren't production's]** → Expected (decision 7). The staging run on the full library gives production's.
- **[`data.pantherdb.org` changes or drops the tarball]** → The pin fails loudly. CI needs only the sample, a GitHub release.
  - A release asset can't mirror the full tarball: GitHub limits each asset to 2 GiB.
  - So the fallback is a team copy, such as the one the hosting server will hold.
- **[`books.sha256` lives only in the data folder]** → Its digest is pinned, and `data manifest` regenerates it from the tarball.
- **[The developer's disk]** → The tarball is 18.5 GB, and the kept files, for the measurements, 67 GB (the survey). The press check needs about 48 GB besides, and task 6.5's fetch another 67 GB. Where a laptop lacks the room, the full-library tasks run on a cluster, or one after another, each one's files removed before the next.
- **[One large pull request]** → It splits as the proposal says.

## Migration Plan

Nothing in production changes. The work lands in this order:

1. The shared docs (task group 1).
2. The moves to `core/`, and `open_https`.
3. The readers, legacy readings and survey, with their fixtures.
4. The survey of the tarball. The design is adjusted to what it finds.
5. `data manifest`, then `data.json` committed, then `fetch` and `verify`. Then fetch the full library, take the measurements and run the press check.
6. Choose the families, build the sample and the committed table, publish the release and commit `sample.json`.
7. CI.
8. The 3.1b2 comparison, and the survey doc.

To roll back, revert the pull request. The release can stay, and so can a fetched `hmmscore/19/`.

## Open Questions

- **Which families go in the sample.** They're chosen in apply from the survey and the full-library runs, and recorded in the survey doc.
