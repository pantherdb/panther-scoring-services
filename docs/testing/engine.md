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
- **Nothing is written into `engine/`.** The image keeps its own environment in `/opt/venv`, and no bytecode or caches land in the mount. A local `engine/.venv` keeps working.
- **`uv.lock` is never rewritten.** If it's out of date with `pyproject.toml`, the run stops. Update it natively with `uv lock` in `engine/`.

### Windows

Clone the repository inside WSL2, for example under `~/` in the Ubuntu distribution, not under `C:\` or `/mnt/c/`. Run the commands from a WSL2 shell, with Docker Desktop's WSL2 integration turned on for that distribution. A clone on the Windows file system is mounted slowly, and doesn't keep Linux file permissions.

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

Every external tool is started through `run_tool()` in `src/panther_engine/core/process.py`: an absolute program path, a list of arguments and no shell. Ruff's `S603` reports any other `subprocess` call in the engine.

In tests, the `make_tool` fixture (`tests/conftest.py`) writes a fake tool: a small shell script in a temporary folder. `tests/test_process.py` and `tests/test_tools.py` show how to use it.

## Test Data

No scoring data yet. The cSNP data sample comes with the survey change.

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
