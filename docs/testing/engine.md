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
- **Your `.data/` folder is mounted read-only** at `/data`, with `PANTHER_DATA_DIR=/data`. Fetch the cSNP data sample into it first ([Test Data](#test-data)), or the tests that need it skip.
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

In tests, the `make_tool` fixture (`tests/conftest.py`) writes a fake tool: a small shell script in a temporary folder. `tests/test_process.py` and `tests/test_tools.py` show how to use it.

## Test Data

### The cSNP Data Sample

The cSNP tests read a sample of the PAML_RST library: one family for each variant the [library survey](../parity/csnp-library-survey.md) found, the species tree, and the PSEP 1.01 release's copyright statement. The full library is 19.2 GB unpacked, too big for a laptop or a CI runner.

- **Where it lives:** a public release asset of this repository, `csnp-sample-1.tar.gz`, pinned by `engine/src/panther_engine/csnp/sample.json`. The manifest holds the tarball's URL and sha256, and the sha256 of each file in it.
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

### Tests That Need the Data

A test that reads a service's data sample is marked with the service:

```python
@pytest.mark.data("csnp")
def test_reads_every_sample_family(csnp_data: Path) -> None: ...
```

- **The data folder is `PANTHER_DATA_DIR`,** or `.data/` at the repository root where it isn't set. The `csnp_data` fixture is its `csnp/9/` folder. compose mounts `.data/` read-only at `/data` and sets `PANTHER_DATA_DIR=/data`, so the same tests run in the image.
- **Where the sample isn't there,** the test is skipped, and the reason names the data and `PANTHER_DATA_DIR`: `needs the csnp data sample, not found in …`.
- **With `PANTHER_REQUIRE_DATA=1`,** missing data fails the test instead. CI sets it. compose doesn't, so without the sample `docker compose run --rm engine` still passes, listing the skips.
- **Each test checks only that the files are there.** One test, `test_the_sample_matches_its_manifest`, hashes every file against the manifest.

### Using the Full Library

The full library unpacks into the same layout, so code never needs to know which it has. From the parent folder of this repository:

```sh
mkdir -p ~/panther-data/csnp/9
tar -xzf panther_build/PAML_RST.tar.gz -C ~/panther-data/csnp/9
cp panther-workspace/legacy/cSNP_analysis/species_pthr8_time.nhx ~/panther-data/csnp/9/
(cd panther-scoring-services/engine && uv run panther-engine csnp sample fetch --data-dir ~/panther-data)
```

The last line adds the copyright statement and checks the sample's files, which the full library also holds. Then set `PANTHER_DATA_DIR=~/panther-data`. It needs 19.2 GB free.

### Publishing a New Sample

A new sample is a new release tag and a new manifest. Old releases stay, so old commits can still fetch their sample. Never replace the asset of an existing release: the manifests that pin it would fail to fetch.

1. **Choose the families** from the survey, and record them in [csnp-library-survey.md](../parity/csnp-library-survey.md). To rebuild the current sample, list its families with `jq -r '.families[]' src/panther_engine/csnp/sample.json > families.txt`.
2. **Build** from `engine/`, with the next tag. The archive and the species tree must match the checksums in the legacy behaviour spec §7.1:

   ```sh
   uv run panther-engine csnp sample build ../../panther_build/PAML_RST.tar.gz \
     --species ../../panther-workspace/legacy/cSNP_analysis/species_pthr8_time.nhx \
     --readme ../../PANTHER_PSEP1.01/README.txt \
     --families families.txt --tag csnp-sample-2
   ```

   It writes `csnp-sample-2.tar.gz` and `src/panther_engine/csnp/sample.json`. A second build gives the same bytes.
3. **Publish** the tarball. It needs write access to the repository:

   ```sh
   gh release create csnp-sample-2 csnp-sample-2.tar.gz --prerelease \
     --title "cSNP data sample 2" --notes "See docs/parity/csnp-library-survey.md"
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
