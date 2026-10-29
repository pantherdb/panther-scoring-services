# Tasks

## 1. Prerequisites

- [x] 1.1 The engine developer confirms the engine reuses `api-stack.md`'s tooling, and marks the "Engine developer" row of its Review table Accepted with the date; verify the row reads Accepted and that every tool and version in design.md's Context matches `api/pyproject.toml`
- [x] 1.2 Update the local uv to the version CI pins (0.13.6, `uv self update 0.13.6`); verify `uv --version` prints it, and that `docker buildx version` works. Record both versions in the Notes

## 2. Project and Package Skeleton

- [x] 2.1 Create the uv project in `engine/` with `uv init --package` (distribution `panther-engine`, package `panther_engine`, `uv_build` backend, `.python-version` `3.13`), with no runtime dependencies and a `dev` group pinning `ruff`, `basedpyright` and `pytest` to the exact versions in `api/pyproject.toml` (ruff 0.17.3, basedpyright 1.40.2, pytest 9.2.0 today); set `required-version` in `[tool.uv]`, add a `panther-engine` console script, and remove `engine/.gitkeep`. Verify `uv sync` writes `engine/uv.lock`, `uv run python --version` prints 3.13, and `git status` shows no virtualenv or cache files
- [x] 2.2 Add `[tool.ruff]`, `[tool.basedpyright]` and `[tool.pytest.ini_options]` copied from `api/pyproject.toml`, with the `tools` marker registered (the suite runs with `--strict-markers`). Add `py.typed`, an empty `core/`, and the `csnp/`, `hmmscore/`, `refmap/` and `treegrafter/` subpackages, each with a docstring naming the service and its reference (CLAUDE.md's table). Verify `uv run ruff check`, `uv run ruff format --check` and `uv run basedpyright` pass, and `uv run python -c "import panther_engine.csnp, panther_engine.hmmscore, panther_engine.refmap, panther_engine.treegrafter"` succeeds

## 3. CLI Version

- [x] 3.1 Add `cli.py` (argparse, `--version` from the installed metadata) and `__main__.py`; verify `tests/test_cli.py` passes and covers the spec's "Installed command" and "Run as a module" scenarios, with both printing the same version, and that `uv run panther-engine --version` works from a shell

## 4. Tools Image

- [x] 4.1 Add the root `.dockerignore` (allowlist: `engine/`, excluding `engine/.venv` and caches) and the `Dockerfile`'s `ARG`s and `blast` stage: the base image `python:3.13-slim-trixie` by digest, NCBI's BLAST+ 2.17.0 tarball per `TARGETARCH` with its sha256, keeping `blastp` and `blastdbcmd`. Verify the stage builds for `linux/arm64` and `linux/amd64`, `blastp -version` prints `2.17.0+` in each, and a wrong sha256 makes the build fail. Record where each checksum came from in a comment beside it
- [x] 4.2 Add the `hmmer` stage: HMMER 3.4's source with its sha256, built and installed under `/opt/tools`; verify it builds for both architectures and `hmmscan -h` and `hmmsearch -h` print `HMMER 3.4` in each
- [x] 4.3 Add `engine/tools-env/` with an explicit conda lock file for EPA-ng 0.3.8 per architecture (`linux-64`, `linux-aarch64`; build `_7`; a hash on every package), and the `epang` stage on `mambaorg/micromamba` by digest that creates `/opt/tools/conda` from the file for `TARGETARCH`; verify `epa-ng --version` prints 0.3.8 in that stage for both architectures
- [x] 4.4 Add the `tools` stage: copy `/opt/tools` from the three stages at the same paths, add `uv` from `ghcr.io/astral-sh/uv:0.13.6` by digest, put the tools on `PATH`, set `UV_PYTHON_DOWNLOADS=never`, and create a non-root user. Verify for both architectures that `ldd` reports no missing library for any of the four programs (install any missing ones from Debian and list them in the Notes), and that each prints its pinned version as that user. Save each program's version output from the arm64 image as a fixture in `engine/tests/fixtures/tool-versions/`

## 5. Running Tools

- [x] 5.1 Add `core/process.py` with `run_tool()` as design.md describes (absolute program path, argument list, `shell=False`, timeout, captured output), with its one `# noqa: S603` and the reason; verify `tests/test_process.py` passes and covers the spec's "Shell metacharacters in an argument" scenario with a fake tool in `tmp_path`, and that a scratch `subprocess.run([...])` elsewhere in `src/` is reported as `S603` (then removed)
- [x] 5.2 Add the `tools` marker handling to `tests/conftest.py`: a missing tool skips with its name in the reason, or fails when `PANTHER_REQUIRE_TOOLS=1`; verify with a `tools`-marked test for a tool that doesn't exist, run natively, that it is reported as skipped naming the tool, and with `PANTHER_REQUIRE_TOOLS=1` that it fails naming the tool (the spec's two "Tests that need the tools" scenarios)
- [x] 5.3 Add `core/tools.py` (the tools as data, found with `shutil.which`, versions read through `run_tool()`) and the `tools` subcommand; verify `tests/test_tools.py` passes: the version patterns parse the fixtures from 4.4; the spec's "A tool is missing" scenario, with `PATH` set to a folder holding fake tools for all but `epa-ng`; and a `tools`-marked test that the real tools report the pinned versions (skipped natively)

## 6. Engine Image and Compose

- [x] 6.1 Add the `engine` stage: copy `engine/` to `/work/engine`, `uv sync --locked` into `/opt/venv` (`UV_PROJECT_ENVIRONMENT`), `PANTHER_REQUIRE_TOOLS=1`. On this machine (arm64), verify the spec's "Tool report in the image" scenario with `panther-engine tools`, and that `uv run --no-sync pytest` passes with no test skipped. Repeat for `linux/amd64` under emulation, and record both build times, uncached and cached, in the Notes
- [x] 6.2 Add the root `compose.yaml` with the `engine` service as design.md describes (the mount at `/work/engine`, `UV_PROJECT_ENVIRONMENT=/opt/venv`, `UV_LOCKED=1`, `PYTHONDONTWRITEBYTECODE=1`, the ruff cache under `/tmp`, `PYTEST_ADDOPTS=-p no:cacheprovider`, the four checks as the default command). From a fresh clone, verify `docker compose run --rm engine` passes; `git status --ignored engine/` shows nothing new; and `uv run pytest` in the host's `engine/.venv` still works (the spec's "Engine checks run in the image" scenarios)
- [x] 6.3 Write `docs/testing/engine.md`, following `docs/testing/README.md`: the compose commands first (all checks, one test, the CLI), then the native uv setup, the `tools` marker and `PANTHER_REQUIRE_TOOLS`, and the Windows note (clone inside WSL2). Verify every command in it runs as written, from the folder it names

## 7. CI

- [x] 7.1 In `.github/workflows/ci.yml`, add the `engine` filter to `changes` (`engine/**`, `Dockerfile`, `.dockerignore`, `compose.yaml`, `ci.yml`) and the `engine` job in `engine/`, the same steps as the `api` job with its cache keyed on `engine/uv.lock`; add it to `ci-passed`'s `needs`. Verify actionlint (`uvx --from actionlint-py actionlint`) reports no errors, and that the job's steps, run in order from a copy of only the files git would commit, pass
- [x] 7.2 Add the `engine-image` job: a matrix over `ubuntu-latest` and `ubuntu-24.04-arm`, `docker/setup-buildx-action` and `docker/build-push-action` pinned to commit SHAs (version in a comment), building the `engine` target with the GitHub Actions cache scoped per architecture and loaded locally, then `panther-engine tools` and `uv run --no-sync pytest` in the image; add it to `ci-passed`'s `needs`. Verify actionlint reports no errors, and that the job's build and test steps pass locally with `docker buildx build --target engine --load` and `docker run`
- [x] 7.3 Add the `engine` and `engine-image` rows to the What CI Runs table in `docs/testing/README.md`, update its sentence about the missing engine job, and link `engine.md` from the Engine row of Kinds of Test; verify the commands named match `ci.yml`

## 8. Shared Docs

- [x] 8.1 In `CONTRIBUTING.md`'s Spec Layout, add `engine-core` ("Behaviour every engine service shares: the CLI, the pinned external tools in the image, finding them, reporting their versions and running them without a shell") and remove `legacy-xml-endpoint`; in `docs/design/tech-stack.md`, name the package `panther_engine` in Engine conditions 1 and 2. Verify `npx markdownlint-cli2` passes from the repo root

## 9. Final Check

- [x] 9.1 From a clean clone of the branch, in `engine/`: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest` passes, with the `tools` tests skipped; and from the root, `docker compose run --rm engine` passes with none skipped
- [x] 9.2 A Windows developer, with the repo cloned inside WSL2, runs `docker compose run --rm engine` and `docker compose run --rm engine panther-engine tools`; verify both pass, and record who ran it, the date and the Docker Desktop version in the Notes. If no one can run it before merge, record that under Blockers and keep the proposal's open question
- [x] 9.3 From the repo root, `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass

## Workflow follow-up

- Open a pull request with these artifacts. The engine developer approves. The API developer reviews the root `Dockerfile` and `compose.yaml`, which the API's image and service will build on. Apply starts after that.
- When the implementation's pull request is opened, confirm on it that:
  - both `engine-image` legs run and pass under `ci-passed`, and whether `ubuntu-24.04-arm` was available (the proposal's first open question);
  - `dependency-review` lists the packages in `engine/uv.lock`.
- Decide who bumps the base image digests, and how often (the proposal's second open question), and record it in `tech-stack.md`.
- After the implementation merges, archive with `/opsx:archive`, so `openspec/specs/engine-core/spec.md` is created.
- Next change: the cSNP library survey and data sample, which also adds the golden-files `-text` rule to `.gitattributes`.

## Notes

### Next action

All tasks are done (2026-10-29). The implementation merged in #14, approved by tmushayahama, after every CI job passed, including both `engine-image` legs. Next: archive with `/opsx:archive`.

### Blockers

None.

### Windows check (9.2)

Tremayne ran `docker compose run --rm engine` and `docker compose run --rm engine panther-engine tools` on 2026-10-29, from a clone inside WSL2, after #14 merged. Both passed. The Docker Desktop version wasn't recorded. This answers the proposal's third open question.

### Failed approaches

- **BLAST+ on the bare slim base (4.1).** NCBI's `blastp` and `blastdbcmd` fail to start on `python:3.13-slim-trixie`: `libgomp.so.1: cannot open shared object file`. `ldd` showed that `libgomp.so.1` was the only missing library, on both architectures. Fixed by installing Debian's `libgomp1` in the `blast` stage, which checks its own binary, and in the `tools` stage.
- **Recording the fixtures with `docker compose run --rm --build -T` (6.3).** Without a terminal (`-T`), compose writes the build log to stdout, so the redirected fixture file held the log instead of the version output. `docs/testing/engine.md` now rebuilds first with `docker compose build engine`, then records without `--build`. The fixture was restored and checked byte for byte.
- **Asserting on pytest's short summary line (5.2).** The pytester test first expected the failure message in the `FAILED … - message` summary line, but pytest drops the message there at that width. The test now matches the message in the failure section.

### Lessons learned

- **Versions (1.2).** uv updated from 0.11.11 to 0.13.6 with `uv self update 0.13.6`. Docker 29.0.1, buildx v0.29.1-desktop.1, on an arm64 Mac (10 CPUs).
- **Where each pin came from (4.1–4.4, 2026-10-29).**
  - **Base image digests:** read with `docker buildx imagetools inspect`. All three are multi-platform indexes with `linux/amd64` and `linux/arm64`.
  - **micromamba:** the `2.10.0-debian13-slim` tag, chosen because Debian 13 is trixie, the same as the Python base.
  - **BLAST+ sha256:** computed from NCBI's tarballs after each matched the `.md5` NCBI publishes beside it.
  - **HMMER sha256:** computed from the source tarball, and equal to the one in Bioconda's `hmmer` 3.4 recipe.
- **Missing libraries (4.4).** In the `tools` stage, `ldd` reports nothing missing for `blastp`, `hmmscan`, `hmmsearch` or `epa-ng` on either architecture. The only Debian package added is `libgomp1`.
- **The EPA-ng locks use sha256, not md5 (4.3).** `micromamba env export --explicit` writes only md5. The lock files are written instead from a `micromamba create --dry-run --json` solve, as `url#sha256:…` lines. Both architectures solve to the same 7 packages (EPA-ng `_7`, GCC 16.2 runtime libraries, zlib). micromamba checks the hashes: one changed digit stops the build with `tarball has incorrect SHA256`.
- **`S603` skips literal-only argument lists (5.1).** Ruff 0.17 doesn't report `subprocess.run(["/bin/echo", "x"])`. It does report every call with a variable in its arguments, such as `subprocess.run([program, *args])`, and `run_tool()`'s own call when its `noqa` is removed. Every call a service would write is still caught. design.md's "S603 still flags any `subprocess.run`" overstates it slightly.
- **CLI tests go through `run_tool()` (3.1).** `test_cli.py` starts the installed command and `python -m`, so `core/process.py` was written before 3.1, keeping S603 clean in `tests/` too. 5.1's own checks ran in their turn.
- **Image tool versions:** BLAST+ prints `blastp: 2.17.0+`; HMMER's `-h` prints `# HMMER 3.4 (Aug 2023)` on its second line; EPA-ng prints `EPA-ng v0.3.8`. All on stdout, with nothing on stderr. The image's Python is 3.13.18.
- **The `tools` marker fails in the call phase (5.2).** `pytest.fail` in `pytest_runtest_setup` reports an *error*, not a failure. So `conftest.py` skips in setup and fails in `pytest_runtest_call`, which reports the test as failed, as the spec says. `tests/test_tools_marker.py` keeps both spec scenarios under test with pytester (`-p pytester` in `addopts`), rather than checking them once by hand.
- **`panther-engine tools` also fails on an unreadable version (5.3).** A tool that is found but whose version doesn't match its pattern prints `version unknown` and makes the command exit 1, as a missing tool does. A tool that prints no recognisable version is a broken install.
- **Build times (6.1), this machine.** The `engine` target took 102 s uncached and 1 s cached on arm64. Under emulation, amd64 took 140 s uncached and 0 s cached. Uncached means `--no-cache` after pruning the builder cache. Of each stage: `blast` about 100 s (the download), `hmmer` 59 s on arm64 and 110 s on amd64 (the build), `epang` about 5 s.
- **The image installs the engine editable (6.2).** `/opt/venv/…/panther_engine.pth` holds `/work/engine/src`, so compose's mount is what gets imported. Checked because a regular install would quietly test the copy baked into the image.
- **compose checks (6.2).** From a copy of the files git would commit, `docker compose run --rm engine` passes, and `git status --ignored` shows nothing new in `engine/`. In the working repo, the untracked and ignored files are identical before and after, and `uv run pytest` still works in the host's `engine/.venv`.
- **A changed `uv.lock` in compose (6.3).** Checked in a scratch copy. If `pyproject.toml` changes without `uv lock`, the run stops with uv's hint, because of `UV_LOCKED=1`. If `uv.lock` was updated natively but the image wasn't rebuilt, `uv run` installs the change into the container's `/opt/venv` (the venv belongs to `panther` for this), and the run works.
- **CI checked locally (7.1, 7.2).** actionlint 1.7.12 reports no errors. The `engine` job's steps pass from a copy of the files git would commit, and so do the `engine-image` build and test steps (`docker buildx build --target engine --load`, then `docker run`) on arm64. The actions are pinned as follows:
  - `docker/setup-buildx-action` v4.4.1: `f87e5991a6d7451dcb8d9637bfbc97413f497069`;
  - `docker/build-push-action` v7.4.0: `c3c9e263c25d99ce0380d002d59b67737d91b0dc`.

  GitHub ran both on #14: see "On #14" below.
- **9.1 was run from a copy, not a clone.** The working tree isn't committed, so the copy holds the files git would commit (`git ls-files -co --exclude-standard`), without `.venv` or caches. Rerun 9.1 from a real clone once committed if you want it literally.
- **On #14 (2026-10-29), every job passed under `ci-passed`.**
  - **`ubuntu-24.04-arm` is available to this repository.** That answers the proposal's first open question, so the matrix keeps both legs. `engine-image` took 2m25s on amd64 and 2m6s on arm64, on the first run, with an empty GitHub Actions cache.
  - **`dependency-review` reads `engine/uv.lock`.** Its log has a `File: engine/uv.lock` section listing the 8 locked packages: `basedpyright`, `ruff`, `pytest`, `iniconfig`, `nodejs-wheel-binaries`, `packaging`, `pluggy` and `pygments`. It found no vulnerable packages and no denied licences, and needed no new exemptions. `docs/testing/README.md` already says it reads the file.
  - **Check the log, not just the result.** A passing dependency review looks the same when it never saw a lock file. Look for the `File:` section naming the lock.
