# Design

## Context

See proposal.md for why. This change builds on these decisions, which it follows and doesn't revisit:

- [tech-stack.md](../../../docs/design/tech-stack.md), Shared Concerns:
  - **Data:** the versioned data folders, the sample picked from a one-time survey, and the full BLAST database;
  - **Environments:** the sample on developer machines and in CI, the full data on staging;
  - **Developer platforms:** everything runs in the image through `docker compose`.
- tech-stack.md, Engine conditions:
  - 2: `core/` first, one submodule per service;
  - 3: parity tests before porting;
  - 6: move the `.rst` parsing (`SCORE-9`) into one module with its own tests.
- [api-stack.md](../../../docs/design/api-stack.md): the tooling (uv, Ruff with the `S` rules, basedpyright strict, pytest).

The engine today, from `scaffold-engine`:

- `core/process.py` (`run_tool()`) and `core/tools.py`;
- the `panther-engine` CLI with `--version` and `tools`;
- the `tools` test marker;
- the image, `compose.yaml`, and CI's `engine` and `engine-image` jobs.

The data:

- **The library.** `PAML_RST.tar.gz` is 2,350,213,383 bytes, beside `panther-workspace` at `../panther_build/`. It holds 8,607 families, three files each, and unpacks to 19.2 GB. It was tarballed from the production server before that was shut down, so it is the build production ran (engine developer, 2026-10-29).
- **Its order.** Members are stored in hash order, not grouped by family. Its first entries are `PTHR15921.paml`, `PTHR23097_1.rst` and `PTHR24091.orig.tree` (checked 2026-10-29). A stream sees a family's third file at an unpredictable point, often far from the first.
- **The BLAST archive.** `PANTHER9.blast.tar.gz` (268 MB, in the PSEP 1.01 release) holds `blast/blast.fasta`, 326 MB. Its headers are all the survey reads from it.
- **The formats** are in the legacy behaviour spec §3.5 and §3.6.

How `PANTHER_PSEP1.01.pl` and `parse_blastp.pl` actually read the files is below, under decision 1.

## Goals / Non-Goals

**Goals:**

- Readers whose output equals what the Perl reads, wherever the survey finds no difference. Step 3 can then use them without a divergence row.
- A survey that runs once on a developer laptop, in minutes, with bounded memory, and never writes the 19.2 GB to disk.
- The smallest sample that covers every variant the survey finds. It is reproducible from the pinned archive, and can be checked offline.

**Non-Goals:**

- **Fast reads for scoring.** The `.paml` reader finds a site by reading the file up to it. Whether step 3 caches or indexes is the port's decision; tech-stack.md asks only that it not load a whole `.paml` per worker.
- **A general Newick or NHX parser.** The readers parse what the files contain and what the checks need.
- **Choosing a reading for the port.** Where the Perl's reading differs, this change measures the difference and doesn't decide it.

## Decisions

### 1. Strict readers, with the Perl's readings measured beside them

The readers reject anything that isn't the documented shape. A separate module, `csnp/legacy.py`, implements the Perl's readings, each citing its line in the Perl and its quirk ID. The survey runs both on every family and counts the differences. These are the readings it compares:

| Value | The Perl's reading | The strict reader |
| ----- | ------------------ | ----------------- |
| Start column | The last header column matching `Node(\d+) AN<n>$` (`readCSV_getNode`, `SCORE-2`) | The column below the root labelled `AN<n>`, the leaf's own |
| Root | The last column whose second-row cell contains `Node<k>`, unanchored | The one column whose parent is itself |
| Branch list | `([0-9]+)..([0-9]+)` anywhere on the 12th line, dots unescaped (`SCORE-9`) | The whole line is `p..c` tokens separated by spaces |
| Tree nodes | The 15th line without `_AN\d+` and spaces, then `([0-9]+)(,\|\)\|;)` | The same nodes, from a parse that checks the line's shape |
| AN order | `AN([0-9]+)(:\|\])` over the first line of `.orig.tree` | Leaf names and `ID=` attributes, in order |
| Event and taxon | `Ev=([0-9]>[0-9]):S=([a-zA-Z\-]+):ID=AN([0-9]+)` | Every NHX attribute of each internal node |
| Sequence | The first line between `List of extant and reconstructed sequences` and `Overall` matching `AN<n>` followed by three spaces, with spaces removed (`getCorrectnum`) | Each labelled line in that section, exactly one per AN |
| Gene lookup | The first line matching `AN([0-9]+):<species>\|<gene>\|<acc>`, with the parts unescaped (`findAN`) | An exact match on a gene line |
| Species ages | `:S=(([a-zA-Z]\|-)+):A=([0-9]+)\]` | Each bracketed attribute set that has `S` and `A` |
| Line ends | `chomp` removes only `\n`, so a `\r` stays in the last field | A carriage return is a format error |

A zero count means the strict reader is safe for parity. A non-zero count, as `SCORE-2` is known to be, leaves the port two options: use the legacy reading from `legacy.py` to match the goldens, or log a divergence.

**Rejected:**

- **Port the Perl's patterns as they are.** That is bug-compatible by construction, but it hides whether the loose readings ever matter, and keeps the port on fixed line numbers for good.
- **Lenient readers that do the "right" thing.** That diverges silently wherever the Perl does something else.

### 2. One streaming pass that joins each family when its third file arrives

The survey opens the archive with `tarfile` in stream mode (`r|gz`) and reads each member line by line as it arrives. It reduces each file to a small summary: node and parent lists, AN lists, events and the site count, never site rows. When a family's third summary arrives, it runs the cross-file and legacy checks, then drops the summaries.

- **The archive's sha256 comes from the same pass.** A reader wrapped around the compressed file feeds `hashlib` as `tarfile` reads.
- **Site rows are checked with whole-line patterns and a column count,** not by parsing cell by cell in Python. That is about 17 GB of `.paml` text.
- **The `.paml` reader checks rows with the same compiled patterns,** so the survey and the reader can't disagree on what a valid row is.

**Rejected:**

- **Unpacking to disk first.** It needs 19.2 GB free and writes everything twice.
- **Two passes,** one per file type. They take twice as long.

**Memory:** the families still waiting for a file are bounded by the family count, and their summaries hold numbers, not sequences. Peak memory and run time go in the Notes. If memory is too high, the summaries keep a hash of each list instead of the list.

### 3. Module layout

```text
engine/src/panther_engine/
  core/data.py        PANTHER_DATA_DIR → a service's data folder; the error when it's unset
  core/manifest.py    read a checksum manifest, hash files, verify a folder against it
  csnp/paml.py        strict readers. Each takes lines and a name for errors, so the survey
  csnp/rst.py           can feed tar members and the port can feed files. All raise one
  csnp/orig_tree.py     LibraryFormatError(name, line, message)
  csnp/species.py
  csnp/legacy.py      the Perl's readings, for comparison and for the port
  csnp/survey.py      the streaming survey, its report, and text and JSON output
  csnp/sample.py      build, fetch, verify
  csnp/sample.json    the sample manifest, shipped as package data
  csnp/cli.py         the `csnp` subcommands; the top-level cli.py registers them
```

The manifest is package data, so `fetch` and `verify` need no path argument. It is a few kilobytes, and production never runs `fetch`.

### 4. The sample is a release asset, pinned by a committed manifest

This was the engine developer's decision, on 2026-10-29.

- **The release:** tag `csnp-sample-<n>`, starting at 1, with the asset `csnp-sample-<n>.tar.gz`. It is created with `gh release create --latest=false`, and its notes link the survey doc.
- **A new sample is a new tag and a new manifest.** Old releases stay, so old commits can still fetch theirs. An asset is never replaced in place: the manifest pins its sha256, so every fetch would fail.
- **The download URL** is `https://github.com/pantherdb/panther-scoring-services/releases/download/<tag>/<asset>`. The repository is public, so it needs no token.
- **The manifest, `csnp/sample.json`,** holds:
  - the tag;
  - the asset's URL, sha256 and size;
  - the source archive's name and pinned sha256 (spec §7.1);
  - the family list;
  - each file's sha256, keyed by its path relative to the data folder: `csnp/9/PAML_RST/PTHR10366.paml` and so on.

  It's JSON because `sample build` writes it, and the standard library can't write TOML.

**Rejected:**

- **Git LFS.** Every clone and CI run draws on the organisation's LFS bandwidth quota, and every clone gets heavier, the frontend's included.
- **An extract script only.** CI has no archive to extract from.

### 5. A reproducible tarball

`sample build` streams the archive once, hashing it as it goes, and keeps only the named families' files. Then it writes the tarball:

- members sorted by path;
- USTAR format;
- mtime 0, uid and gid 0, no user or group names;
- mode 0644 for files and 0755 for folders;
- gzip at level 9, with header mtime 0 and no file name.

The species tree and the copyright statement go in beside the families:

- the species tree from `cSNP_analysis/species_pthr8_time.nhx`, checked against spec §7.1;
- the copyright statement from the top of the PSEP 1.01 README, as `csnp/9/PSEP-COPYRIGHT.txt`.

The tarball is written to a temporary file next to its destination, and renamed only when the archive's checksum matched. The build also writes the manifest that describes the tarball.

**A different zlib can compress differently.** So the asset's sha256 only matters to `fetch`, and the per-file checksums are the lasting contract.

### 6. `fetch` uses the standard library, checks before unpacking, and unpacks safely

1. **Download.** `urllib.request` over HTTPS only, streamed to a temporary file inside the data folder while hashing it.
2. **Check the sha256.**
3. **Unpack** into a temporary folder in the data folder. `tarfile`'s `filter="data"` applies, and on top of it only regular files and folders under `csnp/` are allowed.
4. **Verify** every file against the manifest.
5. **Move** the files into place.

A failure at any step leaves the data folder as it was. Ruff reports the URL open (`S310`) and the extraction (`S202`). Each gets one `noqa` with its reason, as `run_tool()`'s `S603` does.

**Rejected:**

- **`gh release download`.** It needs `gh` and a token, and not every machine has them.
- **`curl` and `sha256sum` in a shell script.** macOS has `shasum`, not `sha256sum`, and a shell script is neither linted nor tested.

Python is the one runtime every route has: uv natively, and the image in compose and CI.

### 7. The data folder: `PANTHER_DATA_DIR`, `csnp/9/`, and `.data/` for development

- **Version `9`** follows tech-stack.md's `/data/panther/<version>/` ("19 today").
- **The full library unpacks into the same layout:** `tar -xzf PAML_RST.tar.gz -C <root>/csnp/9/`. Code never needs to know whether it has the sample or the full data.
- **`.data/` at the repository root is the developer's data folder.** A committed `.data/.gitkeep` makes the folder exist before compose mounts it. Without it, Docker on Linux creates the folder owned by root, and the developer can't fetch into it.
- **The image never sees it.** `.dockerignore`'s allowlist already keeps `.data/` out of the build context.
- **`tests/conftest.py` uses `PANTHER_DATA_DIR`, or the repository's `.data/` when it's unset,** so `uv run pytest` works after a native fetch. Only the tests fall back. The CLI requires the variable, or `--data-dir`.

### 8. The `data` marker mirrors `tools`

- **Usage:** `@pytest.mark.data("csnp")`.
- **Presence check:** every file in the manifest exists. Nothing is hashed per test. One test, `data`-marked, hashes every file against the manifest.
- **Skip in setup, fail in call.** This is `scaffold-engine`'s lesson: a failure in setup is reported as an error, not a failure.
- **`PANTHER_REQUIRE_DATA=1` in CI only.** Compose leaves it unset, so a developer without the sample still gets a passing run, with the skips listed.

**Rejected:** requiring data in the image, as it requires the tools. The tools are part of the image, but the data is a separate download, and the image never ships data.

### 9. CI caches the unpacked sample and fetches on a miss

- **The cache:** `actions/cache`, pinned to a commit SHA, on `.data/csnp`, with the key `csnp-sample-${{ hashFiles('engine/src/panther_engine/csnp/sample.json') }}`. The `engine` job and both `engine-image` legs share it: the data is the same on every architecture.
- **`fetch` always runs.** On a hit it only verifies, which takes seconds, and downloads nothing. A corrupted cache can't pass.
- **In `engine-image`,** `fetch` runs inside the built image, with `.data` mounted writable and `--user "$(id -u):$(id -g)"`. The runner's user then owns the files, and the runner needs no uv. The tests then run with `.data` mounted read-only at `/data`.
- **Pull requests from forks** can fetch too, because the release is public.

### 10. The golden-files folder and byte-exact fixtures

- **`engine/tests/golden/<service>/`** is reserved for the parity harness.
- **`engine/tests/fixtures/csnp/`** holds hand-written library files.

Both get `-text` in `.gitattributes`. The fixtures are written by hand, not cut from real families. A three-leaf family is small enough to check by eye, and each broken variant is one edit away from it. The real files are covered through the sample.

## Risks / Trade-offs

- **[The survey's numbers differ from the parity review's]** (117,389 leaves in 6,897 families for `SCORE-2`; 40,506 nodes for `DATA-3`; 474,535 entries for `DATA-2`) → The review applied the Perl's own patterns, so a difference means `legacy.py` or a strict reader is wrong. Investigate until they agree, or explain each difference in the survey doc, before choosing the sample.
- **[The survey takes too long or too much memory on a laptop]** → Measure, and record it in the Notes. Fall back to hashed summaries (decision 2).
- **[The strict readers reject files the Perl reads]** → The survey lists every rejection, and the port decides file by file. If nothing beyond the four known broken families is rejected, there's nothing to decide.
- **[The release asset is deleted or replaced]** → `fetch` fails on the checksum, and `sample build` remakes the tarball from the pinned archive.
- **[The sample is thin for the trace-back]** → It covers file variants, not trace-back paths. The full comparison on staging covers those (tech-stack.md, Environments).
- **[One large pull request is hard to review]** → The pull request description walks through it in task order: the readers, the survey, the sample, then CI and docs.

## Migration Plan

Nothing in production changes. The work lands in this order:

1. The code and its tests.
2. The survey, run on the archive.
3. The sample, chosen and built.
4. The release, published.
5. The manifest, committed.
6. CI fetches the sample.

To roll back, revert the pull request. The release can stay.

## Open Questions

- **Which families go in the sample.** They're chosen from the survey's results during apply, and recorded in `docs/parity/csnp-library-survey.md`.
