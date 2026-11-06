# Engine Tests

How to run the engine's checks, its tests and its CLI. The engine reuses the API's tooling ([api-stack.md](../design/api-stack.md)). The pinned external tools and the image are in [tech-stack.md](../design/tech-stack.md#pinning-tool-versions).

There are two ways to run everything:

- **In the engine image, with Docker.** This is the way that works on every platform, and the only way the tool tests run: the image has BLAST+ 2.17.0, HMMER 3.4 and EPA-ng 0.3.8.
- **Natively, with uv.** Optional. Quicker for lint and unit tests, but the tool tests skip.

## In the Image

Docker only. Run every command from the repository root:

```sh
docker compose run --rm engine                                      # lint, format, types and tests
docker compose run --rm engine uv run pytest tests/test_tools.py    # one file
docker compose run --rm engine uv run pytest -k metacharacters      # one test, by name
docker compose run --rm engine panther-engine tools                 # the CLI: each tool's version and path
```

- **The first run builds the image.** That takes about two minutes. Later runs reuse it.
- **Rebuild after a change to the image.** That means the `Dockerfile`, `engine/tools-env/` or `engine/uv.lock`. Add `--build`: `docker compose run --rm --build engine`. A changed `uv.lock` without a rebuild still works, but each run then reinstalls the packages in the container.
- **Your working copy is mounted** at `/work/engine`, so the checks run against your edits without a rebuild.
- **Your `.data/` folder is mounted read-only** at `/data`, with `PANTHER_DATA_DIR=/data`. Fetch the cSNP data sample and the refmap data into it first ([Test Data](#test-data)), or the tests that need them skip.
- **Nothing is written into `engine/`.** The image keeps its own environment in `/opt/venv`, and no bytecode or caches land in the mount. A local `engine/.venv` keeps working.
- **`uv.lock` is never rewritten.** If it's out of date with `pyproject.toml`, the run stops. Update it natively with `uv lock` in `engine/`.

### Windows

Clone the repository inside WSL2, for example under `~/` in the Ubuntu distribution, not under `C:\` or `/mnt/c/`. Run the commands from a WSL2 shell, with Docker Desktop's WSL2 integration turned on for that distribution. A clone on the Windows file system is mounted slowly, and doesn't keep Linux file permissions. Both `docker compose run --rm engine` and `docker compose run --rm engine panther-engine tools` were checked this way on 2026-10-29.

## Natively

uv `0.13.6` or later, the same as for the API. Run every command from `engine/`:

```sh
uv sync                                # creates .venv from uv.lock, with the dev group
uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest
```

uv downloads Python 3.13 itself if it isn't on the machine. In VS Code, use the basedpyright extension instead of Pylance, as for the API.

| Command | What it does |
| ------- | ------------ |
| `uv run ruff check` | Lint, including the `S` security rules |
| `uv run ruff format` / `ruff format --check` | Format files, or only report |
| `uv run basedpyright` | Type check `src/` and `tests/`, strict |
| `uv run pytest` | All tests. The tool tests skip, unless the tools are installed |
| `uv run pytest -k metacharacters` | One test, by name |
| `uv run panther-engine --version` | The CLI. `panther-engine tools` reports the tools found on your `PATH` |

**Breaking code on purpose to see a test fail?** Run that check with `PYTHONDONTWRITEBYTECODE=1`, or delete the module's `.pyc` after restoring it. Python reuses its cached bytecode while the source's size and its modification time, in whole seconds, are unchanged, so an edit undone within a second at the same size still runs the broken code (`add-csnp-species-names`, task 1.3).

## Tests That Need the Tools

A test that runs a real tool is marked with the tools it needs:

```python
@pytest.mark.tools("blastp")
def test_blastp_finds_the_family() -> None: ...
```

- **Where a tool is missing,** the test is skipped, and the reason names the tool: `needs blastp, epa-ng, not found on PATH`. pytest lists skipped tests at the end of its output.
- **With `PANTHER_REQUIRE_TOOLS=1`,** a missing tool fails the test instead. The engine image sets it, so a broken tool can't pass there by skipping.
- **Tools installed natively at other versions** don't skip. For example, Homebrew's HMMER is 3.1b2. If all four tools are on your `PATH`, `test_the_installed_tools_report_the_pinned_versions` fails unless they are the pinned versions. Run the tool tests in the image.

## Running External Tools

Every external tool is started through `run_tool()` in `src/panther_engine/core/process.py`: an absolute program path, a list of arguments and no shell. Ruff's `S603` reports any other `subprocess` call in the engine whose arguments include a variable. It doesn't report a call made only of string literals, such as `subprocess.run(["/bin/echo", "x"])`, so don't take a clean lint as proof that no such call exists.

**BLAST+'s usage reports are off.** BLAST+ 2.17.0 otherwise sends NCBI a usage report on every run, `-version` included, and where that traffic is dropped it waits about 10 seconds first. `run_tool()` sets `BLAST_USAGE_REPORT=false` for every tool, over whatever the caller's environment has, and the `Dockerfile`'s `tools` stage sets it too, so a `blastp` run by hand in any image doesn't report either.

In tests, the `make_tool` fixture (`tests/conftest.py`) writes a fake tool: a small shell script in a temporary folder. `tests/test_process.py` and `tests/test_tools.py` show how to use it.

## Scoring From the Command Line

`panther-engine csnp score` scores one protein as the API's `csnp` job does, for checks by hand and smoke tests. It needs `blastp`, so run it in the image, and the cSNP data sample or the full data. From the repository root:

```sh
docker compose run --rm -T engine sh -c \
  'head -n 2 tests/golden/csnp/release/sample.fasta > /tmp/P26439.fasta &&
   panther-engine csnp score /tmp/P26439.fasta --species HUMAN A10E G15D'
```

It prints tab-separated text:

```text
family        PTHR10366
substitution  age   message            pdel
A10E          220   possibly damaging  0.50
G15D          4200  probably damaging  0.95
```

- **The file holds one protein:** FASTA with one header line, or the sequence alone. It's normalised as the API normalises a request: the header and all whitespace removed, upper case. A file with more than one sequence is refused.
- **Substitutions** are a residue letter, a position and a residue letter, such as `A10E`, in any case.
- **`--species`** is a code of the PANTHER9 BLAST database, such as `HUMAN`.
- **`--json`** prints the result as `score()` returns it. **`--data-dir`** overrides `PANTHER_DATA_DIR`.
- **Exit status 1** for input it can't score, with the reason on standard error.

## Mapping IDs From the Command Line

`panther-engine refmap map` maps IDs for one organism as the API's `refmap` job does, for checks by hand. It needs the refmap data ([Test Data](#the-refmap-data)), and no external tool. From `engine/`:

```sh
uv run panther-engine refmap map --organism ENDPU U1G4Q5 U1GLV9 U1HQ27 --data-dir ../.data
```

It prints one line per ID, in order, the ID and its PANTHER ID or `NOHIT`, separated by a tab:

```text
U1G4Q5  PTHR11360:SF130
U1GLV9  PTHR28011
U1HQ27  NOHIT
```

- **`--organism`** is the organism's code, such as `ENDPU`: the last part of its long name. The engine's list is `src/panther_engine/refmap/organisms.json`, with each organism's genes and those with a PANTHER ID, from `stats`. It holds no organism in PANTHER's own 143 genomes, such as `HUMAN`.
- **The IDs** come from the arguments, or from a file with `--file FILE`, read as `map_panther.pl` read its list: the text before the first tab of each line, with every carriage return removed. `--file ../.data/refmap/19/panther_classification/ARAVE` maps the largest genome, 246,021 IDs, in about half a second.
- **The lookup is exact,** as the legacy's was: case-sensitive, with no isoform or version stripped (`REFMAP-1`). A repeated ID is mapped each time.
- **`--json`** prints the result as `map_ids()` returns it, with `null` for `NOHIT`. **`--data-dir`** overrides `PANTHER_DATA_DIR`.
- **Exit status 1** for a request the API would reject, such as an organism refmap doesn't map for or an ID with a space, and for missing data, with the reason on standard error.

## The BLAST+ Time Limit

Each search's time limit grows with the sequence: 60 s, plus 21 ms a residue, times `PANTHER_CSNP_BLAST_TIME_SCALE` (`csnp/blast.py`). A search past its limit fails the job with a `500`.

| Sequence | Residues | Slowest of three searches | Limit | Headroom |
| -------- | -------- | ------------------------- | ----- | -------- |
| A typical protein | 400 | 4 to 6 s | 68.4 s | over 10 times |
| Titin (Q8WZ42) | 34,350 | 274.6 s (267.2, 273.9, 274.6) | 781.4 s | 2.85 times |
| The API's longest accepted sequence: titin, then its first 15,650 residues | 50,000 | 436.9 s (424.0, 427.1, 436.9) | 1,110 s | 2.54 times |

- **Measured on 2026-11-02,** in the arm64 engine image on an Apple M1 Pro, one search at a time. `blastp` runs on one thread, as the legacy did, so each job uses one core. The rate was set so each long query gets at least 2.5 times its slowest search; `tests/test_csnp_blast.py` checks the limit against these times.
- **On a slower machine,** time titin there with the command below, then set `PANTHER_CSNP_BLAST_TIME_SCALE` so its search takes at most 40% of its limit. For example, `2` doubles every limit. Unset or empty, the scale is 1; anything but a positive number fails each job before BLAST+ runs, naming the variable.
- **To time a search,** without a limit that might cut it off, from the repository root, with the sequence alone in `titin.seq`:

  ```sh
  docker compose run --rm -T -v "$PWD/titin.seq:/tmp/titin.seq:ro" engine python -c '
  import time
  from pathlib import Path
  from panther_engine.csnp import blast
  sequence = Path("/tmp/titin.seq").read_text().strip()
  start = time.monotonic()
  blast.search(sequence, Path("/data/csnp/9"), timeout=3600)
  print(f"{len(sequence)} residues: {time.monotonic() - start:.1f} s")'
  ```

## Parity Tests

The parity tests check the port against golden files made by the service's reference. For `csnp`, `tests/test_csnp_golden.py` reads `tests/golden/csnp/`, and compares byte for byte:

| Test | Needs | Checks |
| ---- | ----- | ------ |
| Step 2 | Nothing | `parse_blastp.pl`'s output for the spec's inputs and every generated step-2 run |
| Step 3 | `data("csnp")` | The spec's §7.3 and §7.5, from step 2 on; every family's generated cases; the broken families give "Invalid substitution" |
| Step 1 | `tools("blastp")`, `data("csnp")` | BLAST+ 2.17.0's output for the three sample proteins, and each one's best hit against the legacy `HUMAN` fixture |

`tests/test_csnp_scoring.py` adds `score()` end to end, with `blastp`: spec §7.3 as three calls, one per protein.

`panther-engine csnp parity check` runs the same comparisons and reports every case that differs, by family and SNP id, and the kinds of node the walks reached. From `engine/`, with the data sample:

```sh
uv run panther-engine csnp parity check tests/golden/csnp/generated --data-dir ../.data
```

It exits with status 1 if any case differs. Making the goldens needs the legacy Perl, in the `csnp-reference` image: see [golden-setup.md](../parity/golden-setup.md).

For `refmap`, `tests/test_refmap_golden.py` reads `tests/golden/refmap/`. Each mapping must equal the first two fields of the Perl's line, with `NOHIT` for none:

| Test | Needs | Checks |
| ---- | ----- | ------ |
| The made-up files | Nothing | Small classification files for what the release never holds: a repeated ID, CRLF endings, a line with no value, more fields |
| The divergences | Nothing | The port refuses what rows 9 and 10 of [divergences.md](../parity/divergences.md) say it refuses, where the Perl answered `NOHIT`, with the error and the part of its message each case names |
| The cases on ENDPU | `data("refmap")` | The data server's two test lists, every ENDPU ID among them, and the hand-made lists |

`panther-engine refmap parity check` runs the same comparisons and lists every line that differs, by case and line. From `engine/`, with the refmap data:

```sh
uv run panther-engine refmap parity check --data-dir ../.data
```

It exits with status 1 if any line differs. Without a data folder, it still checks the made-up files and the refused cases, lists the cases on ENDPU as not checked, and exits with status 1. Making the goldens needs `map_panther.pl`, in the `refmap-reference` image: see [golden-setup.md](../parity/golden-setup.md#refmap).

## Input Errors

A service raises `InputError` (`src/panther_engine/core/errors.py`) when it can't process the input **as a whole**, and only the engine can tell. For example, an organism its data doesn't have. The API fails the job with status `422` and shows the message to the user as it is.

- **Single-item problems go in the result,** not in an exception. One substitution that can't be mapped, or one ID with no family, is a row of the result, so the rest of the input still gets its answers.
- **The message is written for the person who submitted the input.** Say what's wrong and what to fix, in a sentence: "Unknown organism."
- **The message never contains file paths, tool output or internal identifiers.** The API can't tell a safe message from an unsafe one, so review and each service's tests are the guard.
- **Raise it only on purpose.** Never convert other exceptions into it. A bug, a broken data file or a failing tool raises anything else, and the API reports it as a generic `500`.
- **Subclasses are fine,** with any constructor, such as `UnknownOrganism(organism)`. The base class rebuilds them across processes, so they keep their type, message and attributes. `tests/test_errors.py` checks this through a real `spawn` worker.

## Test Data

### The cSNP Data Sample

The cSNP tests read a sample of the cSNP data: one family of the PAML_RST library for each variant the [library survey](../parity/csnp-library-survey.md) found, and the family of the scoring form's example, the whole PANTHER9 BLAST database, the species tree, and the PSEP 1.01 release's copyright statement. The full library is 19.2 GB unpacked, too big for a laptop or a CI runner.

- **Where it lives:** a public release asset of this repository, `csnp-sample-3.tar.gz` (157 MB, 624 MB unpacked), pinned by `engine/src/panther_engine/csnp/sample.json`. The manifest holds the tarball's URL and sha256, the sha256 of each source archive, and the sha256 of each file in the tarball.
- **What it holds:** under `csnp/9/`, the families in `PAML_RST/`, the BLAST database's `blast.phr`, `blast.pin` and `blast.psq` in `blast/`, `species_pthr8_time.nhx` and `PSEP-COPYRIGHT.txt`. The database is whole, so `blastp` finds the same hits as against the full data. The release's 326 MB `blast.fasta` stays out: `blastp` doesn't read it.
- **Where it goes:** the data folder, under `csnp/9/`. The data folder is `PANTHER_DATA_DIR`. For development it's `.data/` at the repository root, which git ignores.

Fetch it natively, from `engine/`:

```sh
uv run panther-engine csnp sample fetch --data-dir ../.data
uv run panther-engine csnp sample verify --data-dir ../.data    # optional: check every file again
```

Or through compose, from the repository root, with `.data/` mounted writable at another path:

```sh
docker compose run --rm --user "$(id -u):$(id -g)" -v "$PWD/.data:/fetch" engine \
  panther-engine csnp sample fetch --data-dir /fetch
```

- **`fetch` checks before it unpacks.** It downloads the tarball over HTTPS, checks its sha256 against the manifest, unpacks it into a temporary folder, checks every file, then moves the files into place. If anything fails, the data folder is left as it was.
- **Run it again any time.** When the folder already matches the manifest, it downloads nothing.
- **`--from FILE`** takes a local copy of the tarball instead of downloading it.
- **`--user "$(id -u):$(id -g)"`** makes you the owner of the fetched files. On Linux, files written by the image's user would otherwise belong to that user, and you couldn't delete them.

### The refmap Data

The refmap tests read the whole PANTHER 19 release of the classification files refmap maps against: one file for each of 1,533 Reference Proteome organisms, and the `stats` that lists them. At 157 MB it's the size of the cSNP sample, so there's no refmap sample.

- **Where it lives:** `data.pantherdb.org`, the 2024-06-20 release in `ftp/generic_mapping/archive/2024-06-20/`: a tarball of 157 MB, 523 MB unpacked, and `stats`. `engine/src/panther_engine/refmap/data.json` pins both by URL, size and sha256, and lists the sha256 of every file as laid out in the data folder. What the release holds is in [refmap-legacy-behaviour.md](../parity/refmap-legacy-behaviour.md#the-pinned-release).
- **Where it goes:** the data folder, under `refmap/19/`: `stats`, and each organism's classification file at `panther_classification/<code>`, such as `panther_classification/ENDPU`.

Fetch it natively, from `engine/`:

```sh
uv run panther-engine refmap data fetch --data-dir ../.data
uv run panther-engine refmap data verify --data-dir ../.data    # optional: check every file again
```

Or through compose, from the repository root, as for the sample:

```sh
docker compose run --rm --user "$(id -u):$(id -g)" -v "$PWD/.data:/fetch" engine \
  panther-engine refmap data fetch --data-dir /fetch
```

- **`fetch` checks before it saves.** It downloads the tarball and `stats` over HTTPS, and checks each one's size and sha256 against the manifest. Then it reads the tarball as a stream, writes each classification file into a temporary folder in the data folder, checks every file, and moves into place only the files that were missing or differed. If anything fails, nothing under `refmap/19/` changes. It took about 30 s on 2026-11-06, almost all of it the download.
- **Run it again any time.** When the folder already matches the manifest, it downloads nothing; the check takes about 2 s.
- **`--tarball FILE` and `--stats FILE`** take local copies instead of downloading them, checked against the same pins.
- **`verify`** lists each file that is missing (`missing: PATH`) or differs (`differs: PATH`), and exits with status 1 if there is any. Files the manifest doesn't list are ignored.

**Why the files are named by code.** The tarball names each file by its organism's long name, as `Escherichia_coli_O157:H7_ECO57`. Ten long names contain `:`, which Windows can't use in a file name, so `fetch` saves each file under its code, as `ECO57`. The code comes from the engine's organism list, never from the member's name, so no member of the tarball can write outside the folder. The published names don't change: `stats` and the organism list keep them (#52, the update to question 4).

**Pinning a new release.** `data.json` and the engine's organism list, `src/panther_engine/refmap/organisms.json`, are generated from a release's tarball and `stats`, never edited by hand. The engine reads the organism list when it's imported, so a change to that file's format needs the new file in place before `panther-engine` runs: write it once from `stats` with a short script, then regenerate both files with the command below. Download both, then run from `engine/`:

```sh
uv run panther-engine refmap data manifest panther_classifications.tar.gz stats \
  --tarball-url https://data.pantherdb.org/ftp/generic_mapping/archive/<date>/panther_classifications.tar.gz \
  --stats-url https://data.pantherdb.org/ftp/generic_mapping/archive/<date>/stats
```

- **It writes both files only if every check passes:** `stats` and the tarball list the same organisms; each file's lines, and its lines with a PANTHER ID, are the counts its `stats` line gives; and every code is unique, 1 to 5 upper-case letters or digits, and not a Windows device name. Otherwise it names each problem and writes nothing.
- **It reads the tarball once, as a stream,** in about 6 s. The release's name in `data.json` is the folder its tarball is in, such as `2024-06-20`.
- **The same inputs give the same bytes.** Run on the pinned release, it writes the committed files unchanged.
- **A new PANTHER version** also changes `VERSION` in `src/panther_engine/refmap/organisms.py`, so the files go under `refmap/<version>/`.
- **Commit both files.** CI's cache is keyed on `data.json`, so the next run fetches the new release.

### Tests That Need the Data

A test that reads a service's data is marked with the service:

```python
@pytest.mark.data("csnp")
def test_reads_every_sample_family(csnp_data: Path) -> None: ...


@pytest.mark.data("refmap")
def test_every_file_matches_the_manifest(refmap_data: Path) -> None: ...
```

- **The data folder is `PANTHER_DATA_DIR`,** or `.data/` at the repository root where it isn't set. The `csnp_data` fixture is its `csnp/9/` folder, and `refmap_data` its `refmap/19/` folder. compose mounts `.data/` read-only at `/data` and sets `PANTHER_DATA_DIR=/data`, so the same tests run in the image.
- **Where the data isn't there,** the test is skipped, and the reason names the data and `PANTHER_DATA_DIR`: `needs the refmap data, not found in …`.
- **With `PANTHER_REQUIRE_DATA=1`,** missing data fails the test instead. CI sets it. compose doesn't, so without the data `docker compose run --rm engine` still passes, listing the skips.
- **Each test checks only that the files are there.** `test_the_sample_matches_its_manifest`, and refmap's `test_every_file_matches_the_manifest`, hash every file against their manifests. `test_the_organism_list_is_the_one_the_data_folders_stats_gives` regenerates the organism list from the folder's `stats`, and fails if it differs from the committed one.

### Using the Full Library

The full data unpacks into the same layout, so code never needs to know which it has. From the parent folder of this repository:

```sh
mkdir -p ~/panther-data/csnp/9
tar -xzf panther_build/PAML_RST.tar.gz -C ~/panther-data/csnp/9
tar -xzf PANTHER_PSEP1.01/PANTHER9.blast.tar.gz -C ~/panther-data/csnp/9
cp panther-workspace/legacy/cSNP_analysis/species_pthr8_time.nhx ~/panther-data/csnp/9/
(cd panther-scoring-services/engine && uv run panther-engine csnp sample fetch --data-dir ~/panther-data)
(cd panther-scoring-services/engine && uv run panther-engine csnp data verify --data-dir ~/panther-data)
```

The BLAST archive unpacks to `csnp/9/blast/`, with the `blast.fasta` the sample leaves out; it's harmless. The `fetch` line adds the copyright statement and checks the sample's files, which the full data also holds. Then set `PANTHER_DATA_DIR=~/panther-data`. It needs 19.9 GB free. On an Apple M1 Pro, the steps took 43 s.

**The last line checks every file of the full data** against `engine/src/panther_engine/csnp/full.json`: 25,826 files, each by its sha256. It prints how many are missing and how many differ, names the first 20 of each, and exits with status 1 if there is any. Files it doesn't list, such as `blast.fasta`, are ignored. It took 21 s natively, and 68 s in the engine image with the folder bind-mounted on macOS. A deploy runs it before the API takes traffic; scoring itself checks only that the library, the database and the species tree are there (`check_data()`), so a copy that stopped halfway would otherwise answer "No PANTHER family" for the families it lacks.

`full.json` is generated, from the same pinned inputs as the sample, reading each archive as a stream. The data is frozen, so it shouldn't need rebuilding. To check it, rebuild it from `engine/`; this takes about 30 s, and must give the same bytes:

```sh
uv run panther-engine csnp data manifest ../../panther_build/PAML_RST.tar.gz \
  --blast-archive ../../PANTHER_PSEP1.01/PANTHER9.blast.tar.gz \
  --species ../../panther-workspace/legacy/cSNP_analysis/species_pthr8_time.nhx \
  --readme ../../PANTHER_PSEP1.01/README.txt
git diff --exit-code src/panther_engine/csnp/full.json
```

### Publishing a New Sample

A new sample is a new release tag and a new manifest. Old releases stay, so old commits can still fetch their sample. Never replace the asset of an existing release: the manifests that pin it would fail to fetch.

1. **Choose the families** from the survey, and record them in [csnp-library-survey.md](../parity/csnp-library-survey.md). To rebuild the current sample, list its families with `jq -r '.families[]' src/panther_engine/csnp/sample.json > families.txt`.
2. **Build** from `engine/`, with the next tag. The two archives and the species tree must match the checksums in the legacy behaviour spec §7.1:

   ```sh
   uv run panther-engine csnp sample build ../../panther_build/PAML_RST.tar.gz \
     --blast-archive ../../PANTHER_PSEP1.01/PANTHER9.blast.tar.gz \
     --species ../../panther-workspace/legacy/cSNP_analysis/species_pthr8_time.nhx \
     --readme ../../PANTHER_PSEP1.01/README.txt \
     --families families.txt --tag csnp-sample-3
   ```

   It writes `csnp-sample-3.tar.gz` and `src/panther_engine/csnp/sample.json`, in about two minutes. A second build gives the same bytes.
3. **Publish** the tarball. It needs write access to the repository:

   ```sh
   gh release create csnp-sample-3 csnp-sample-3.tar.gz --prerelease \
     --title "cSNP data sample 3" --notes "See docs/parity/csnp-library-survey.md"
   ```

   `--prerelease` keeps the sample from becoming the repository's Latest release. `--latest=false` isn't enough: GitHub makes the only release Latest anyway, as it did with `csnp-sample-1`.
4. **Fetch it** into an empty folder with `fetch --data-dir`, to check the upload.
5. **Commit the manifest.** CI's cache is keyed on it, so the next run fetches the new sample.

### Tool Version Fixtures

`tests/fixtures/tool-versions/` holds each tool's version output, recorded in the arm64 image. `tests/test_tools.py` checks the version patterns against it. When a tool's pin changes, rebuild the image, then record each file again from the repository root:

```sh
docker compose build engine
docker compose run --rm -T engine blastp -version > engine/tests/fixtures/tool-versions/blastp.txt
docker compose run --rm -T engine hmmscan -h > engine/tests/fixtures/tool-versions/hmmscan.txt
docker compose run --rm -T engine hmmsearch -h > engine/tests/fixtures/tool-versions/hmmsearch.txt
docker compose run --rm -T engine epa-ng --version > engine/tests/fixtures/tool-versions/epa-ng.txt
```

- **`-T` turns off the terminal,** which would otherwise end each line with a carriage return.
- **Don't add `--build` to these commands.** Without a terminal, the build log goes to standard output, and into the file.
