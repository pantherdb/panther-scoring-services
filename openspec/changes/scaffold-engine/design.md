# Design

## Context

`engine/` holds only `.gitkeep`. This change relies on these decisions and doesn't repeat them:

- **The tooling:** uv 0.13, Python 3.13, Ruff with the `S` rules, basedpyright strict and pytest, at the versions `api/` pins. Also why `engine/` is its own uv project, not part of a workspace with `api/`. Both are in [docs/design/api-stack.md](../../../docs/design/api-stack.md). The engine reuses them (decided 2026-10-29).
- **The engine as a library with a CLI,** `core/` plus one subpackage per service, and external tools run as binaries through `subprocess`: [docs/design/tech-stack.md](../../../docs/design/tech-stack.md), Engine section.
- **The container image as the pin for the tools:** base images by digest, each tool by exact version and checksum, built for `linux/amd64` and `linux/arm64`, with BLAST+ 2.17.0. Also developers running everything in the image, on Windows inside WSL2. All in tech-stack.md, [Pinning Tool Versions](../../../docs/design/tech-stack.md#pinning-tool-versions) and Shared Concerns.

The behaviour is in [specs/engine-core/spec.md](specs/engine-core/spec.md).

Checked on 2026-10-29:

- `python:3.13-slim-trixie`, `ghcr.io/astral-sh/uv:0.13.6` and `mambaorg/micromamba` all publish `amd64` and `arm64` images.
- NCBI publishes BLAST+ 2.17.0 as `x64-linux` and `aarch64-linux` tarballs.
- Bioconda has EPA-ng 0.3.8 for `linux-64` and `linux-aarch64`, both build `_7`, depending only on `libgcc`, `libstdcxx` and `zlib`.
- The official `ncbi/blast` image is amd64 only.

## Goals / Non-Goals

**Goals:**

- The cSNP library survey, and each service port after it, adds a subpackage, a CLI subcommand and tests, without changing the project setup, the image's tool stages or CI.
- From a clean clone, the engine's checks pass on the runner, and the full test suite passes in the image, on both architectures.
- A developer on macOS, Linux or Windows (WSL2) runs every check with Docker alone. A local uv setup is optional.

**Non-Goals:**

- No data in the image or in `compose.yaml`. The sample comes with the survey change.
- No production image or entrypoint. The `engine` target is for tests and the CLI; the API's change adds the image that serves.
- No settings module or logging configuration. Each arrives with the change that needs it.

## Decisions

### Layout

```text
Dockerfile                stages: blast, hmmer, epang -> tools -> engine
.dockerignore             allowlist: engine/ only (the API adds api/)
compose.yaml              service `engine`
engine/
  pyproject.toml          project, dev group, [tool.ruff], [tool.basedpyright], [tool.pytest.ini_options]
  uv.lock
  .python-version         3.13
  tools-env/              explicit conda lock files for EPA-ng, one per architecture
  src/panther_engine/
    __init__.py           __version__ from the installed metadata
    __main__.py           python -m panther_engine
    cli.py                argparse: --version, `tools`
    py.typed
    core/
      __init__.py
      process.py          run_tool(): the one place the engine starts a subprocess
      tools.py            the tools the engine uses, how to find each and read its version
    csnp/ hmmscore/ refmap/ treegrafter/
      __init__.py         docstring: the service and its reference
  tests/
    conftest.py           the `tools` marker: skip, or fail when tools are required
    test_cli.py
    test_process.py       argument-list and shell-metacharacter tests, with a fake tool
    test_tools.py         version parsing from recorded output; `tools`-marked tests on the real binaries
```

- **`src/` layout, built with `uv_build`,** the same as `api/` and for the same reason: tests import the installed package.
- **The service subpackages are empty but present,** so the layout in tech-stack.md is visible, and each port starts by filling its folder in.

### One place starts subprocesses

`core/process.py` has `run_tool(program, args)`:

- `program` is an absolute path resolved with `shutil.which`;
- `args` is a sequence of strings;
- it calls `subprocess.run` with a list, `shell=False`, captured output, a timeout and `check=False`, and returns the completed process.

Every tool call in the engine goes through it.

- **Ruff:** an absolute program path avoids `S607`. `S603` still flags any `subprocess.run`, so this one call carries `# noqa: S603` with its reason. Anywhere else in the engine, `S603` stays an error, which keeps every subprocess call in one reviewed place.
- **The test:** `test_process.py` covers the spec's shell-metacharacter scenario with a fake tool, a small executable script in `tmp_path` that writes its `argv` to a file.
- *Alternative:* let each service call `subprocess` itself. Rejected: the `S` rules would need a `noqa` in every service, and the CGI-5 injection shows why one checked path is worth having.

### Tool discovery and the `tools` command

`core/tools.py` lists the tools as data: the command, the arguments that make it print its version, and a pattern for the version.

| Tool | Version arguments |
| ---- | ----------------- |
| `blastp` | `-version` |
| `hmmscan`, `hmmsearch` | `-h` (first lines have `HMMER 3.4`) |
| `epa-ng` | `--version` |

The exact output of each is recorded during apply, saved as a test fixture, and the pattern is written against it. `panther-engine tools` prints one line per tool, with name, version and path, or `not found`. It exits 1 if any tool is missing. The same data will give the "versions in every response" that tech-stack.md asks the API for.

### The `tools` test marker

Tests that run the real binaries are marked `tools`. `conftest.py` checks each marked test's tools:

- **without `PANTHER_REQUIRE_TOOLS=1`:** a missing tool skips the test, with the tool's name in the reason;
- **with it:** a missing tool fails the test.

The engine image sets `PANTHER_REQUIRE_TOOLS=1`, so a broken tool stage can't pass by skipping. CI's runner job and a plain local `uv run pytest` don't set it, so they skip those tests.

*Alternative:* a separate test folder for tool tests. Rejected: a marker keeps each tool's unit and binary tests in one file, and the environment variable is what stops silent skips.

### The image: one root `Dockerfile`, a stage per tool

The production image will hold the API and the engine together (tech-stack.md, Shared Concerns). One root `Dockerfile` with named stages lets the API's later change add an `api` stage on top of `tools`, without copying the pins.

| Stage | From | Does |
| ----- | ---- | ---- |
| `blast` | the Python base | Downloads NCBI's BLAST+ 2.17.0 tarball for `TARGETARCH` (`x64-linux` or `aarch64-linux`), checks its sha256, and keeps `blastp` and `blastdbcmd` |
| `hmmer` | the Python base, plus a compiler | Downloads HMMER 3.4's source, checks its sha256, and builds and installs it under `/opt/tools` |
| `epang` | `mambaorg/micromamba` | Creates `/opt/tools/conda` from the explicit lock file for `TARGETARCH` |
| `tools` | the Python base | Copies `/opt/tools` from the three stages; adds `uv` from `ghcr.io/astral-sh/uv:0.13.6`; puts the tools on `PATH`; creates a non-root user |
| `engine` | `tools` | Copies `engine/` to `/work/engine`, runs `uv sync --locked` into `/opt/venv`, and sets `PANTHER_REQUIRE_TOOLS=1` |

- **Pins:** each base image by digest, in `ARG`s at the top. Each tarball's version and sha256 per architecture in `ARG`s too, with a comment saying where the checksum came from. Changing any of them is a pull request that changes this file.
- **Same base for the build stages.** `blast`, `hmmer` and `tools` all start from the pinned `python:3.13-slim-trixie`, so every binary is built or checked against the glibc it runs on.
- **EPA-ng's environment** keeps the same prefix, `/opt/tools/conda`, in its stage and in `tools`. Conda fixes paths at install time, so the copy works only at the same path.
- **Python in the image** is the base image's 3.13. uv is told to use it and never download one (`UV_PYTHON_DOWNLOADS=never`).

Where each tool comes from:

| Tool | Source | Why |
| ---- | ------ | --- |
| BLAST+ | NCBI's tarball | The tested version, for both architectures. Bioconda has 2.17.0 only for `linux-64`; the official image is amd64 only |
| HMMER | Source | Plain C with autoconf, quick to build. Bioconda's HMMER package pulls in OpenMPI, which we don't use |
| EPA-ng | Bioconda, explicit lock | Its build pulls in submodules with x86 SIMD code. Bioconda has already done the arm64 build. Its only dependencies are `libgcc`, `libstdcxx` and `zlib` |

*Alternatives:*

- All three from Bioconda. One lock is simpler, but it can't give BLAST+ 2.17.0 on arm64, and HMMER brings OpenMPI.
- EPA-ng from source. Kept as the fallback if the conda copy fails.

### `compose.yaml` for developers

One service, `engine`, built from the `engine` target.

- **The working copy:** `./engine` is mounted at `/work/engine`, the path the image installed the project from. The editable install in `/opt/venv` then imports the mounted source.
- **The environment stays in the image,** through `UV_PROJECT_ENVIRONMENT=/opt/venv` and `UV_LOCKED=1`, so it never touches the developer's `engine/.venv`. An out-of-date `uv.lock` stops the run instead of being rewritten.
- **Nothing written into the mount:**
  - `PYTHONDONTWRITEBYTECODE=1`;
  - `RUFF_CACHE_DIR` under `/tmp`;
  - `PYTEST_ADDOPTS=-p no:cacheprovider`.

  Files the container's user wrote into the mount on a Linux host would belong to that user, and the developer couldn't delete them.
- **The default command** runs the four checks in order. `docker compose run --rm engine` runs them all, and `docker compose run --rm engine uv run pytest -k name` runs one test.

*Alternative:* each developer installs uv and runs the checks natively. That stays possible (`docs/testing/engine.md`), but it skips the tool tests and doesn't work for the tools on Windows.

### CI

Filling the `engine` slot in `ci.yml`:

- **`changes`:** an `engine` filter on `engine/**`, `Dockerfile`, `.dockerignore`, `compose.yaml` and `ci.yml`.
- **`engine` job,** from `engine/`, the same steps as the `api` job:
  - `setup-uv` at 0.13.6, its cache keyed on `engine/uv.lock`;
  - `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright`, `pytest`.

  The tool tests skip here.
- **`engine-image` job,** a matrix over `ubuntu-latest` (amd64) and `ubuntu-24.04-arm` (arm64):
  - `docker/setup-buildx-action` and `docker/build-push-action`, pinned to commit SHAs, build the `engine` target natively, with the GitHub Actions cache scoped per architecture, and load it.
  - In the image, it runs `panther-engine tools`, then `uv run --no-sync pytest` with the tools required.
- **`ci-passed`:** `needs` gains `engine` and `engine-image`.

If `ubuntu-24.04-arm` isn't available to the repository, the matrix drops it. arm64 is then checked on an Apple Silicon machine and noted in `tasks.md`. That's the proposal's first open question.

### Docs

- **`docs/testing/engine.md`,** following `docs/testing/README.md`: the compose commands first, then the native uv setup; the `tools` marker and `PANTHER_REQUIRE_TOOLS`; how to run one test; and that on Windows the repo must be cloned inside WSL2.
- **`docs/testing/README.md`:** the two CI rows.
- **`CONTRIBUTING.md`:** the Spec Layout gains `engine-core` and drops `legacy-xml-endpoint`.
- **`tech-stack.md`:** names the package in Engine conditions 1 and 2.
- **`api-stack.md`:** the engine developer's Review row is marked Accepted.

## Risks / Trade-offs

- **[NCBI's tarball binaries need system libraries the slim base lacks]** → Check with `ldd` in the `tools` stage during apply. Install only what's missing from Debian, and record it in the Notes.
- **[The conda environment doesn't work after the copy]** → It keeps the same prefix. If `epa-ng --version` still fails in `tools`, build EPA-ng 0.3.8 from source instead, and record why in the Notes.
- **[A tool's version output doesn't match the pattern]** → The patterns are written against output recorded from the image, and `test_tools.py` checks them against that fixture.
- **[`ubuntu-24.04-arm` is unavailable, or slow to start]** → See the CI fallback above.
- **[Building BLAST+ and HMMER makes the image job slow]** → Each stage only changes when its pins change, so the per-architecture build cache keeps most runs short. Record the first uncached and a cached build time in the Notes.
- **[Two Python environments to keep in step]** → Both come from the same `engine/uv.lock`. The image syncs with `--locked`, and so does CI's runner job, so neither can drift from the lock.
- **[Windows is untested]** → The proposal's third open question: a Windows developer runs the compose checks from WSL2 once before this is done.
- **[Pinned base images miss security fixes]** → The proposal's second open question. Until it's answered, the digests are bumped by hand, with a pull request.
