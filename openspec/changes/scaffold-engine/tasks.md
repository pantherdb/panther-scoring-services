# Tasks

## 1. Prerequisites

- [ ] 1.1 The engine developer confirms the engine reuses `api-stack.md`'s tooling, and marks the "Engine developer" row of its Review table Accepted with the date; verify the row reads Accepted and that every tool and version in design.md's Context matches `api/pyproject.toml`
- [ ] 1.2 Update the local uv to the version CI pins (0.13.6, `uv self update 0.13.6`); verify `uv --version` prints it, and that `docker buildx version` works. Record both versions in the Notes

## 2. Project and Package Skeleton

- [ ] 2.1 Create the uv project in `engine/` with `uv init --package` (distribution `panther-engine`, package `panther_engine`, `uv_build` backend, `.python-version` `3.13`), with no runtime dependencies and a `dev` group pinning `ruff`, `basedpyright` and `pytest` to the exact versions in `api/pyproject.toml` (ruff 0.17.3, basedpyright 1.40.2, pytest 9.2.0 today); set `required-version` in `[tool.uv]`, add a `panther-engine` console script, and remove `engine/.gitkeep`. Verify `uv sync` writes `engine/uv.lock`, `uv run python --version` prints 3.13, and `git status` shows no virtualenv or cache files
- [ ] 2.2 Add `[tool.ruff]`, `[tool.basedpyright]` and `[tool.pytest.ini_options]` copied from `api/pyproject.toml`, with the `tools` marker registered (the suite runs with `--strict-markers`). Add `py.typed`, an empty `core/`, and the `csnp/`, `hmmscore/`, `refmap/` and `treegrafter/` subpackages, each with a docstring naming the service and its reference (CLAUDE.md's table). Verify `uv run ruff check`, `uv run ruff format --check` and `uv run basedpyright` pass, and `uv run python -c "import panther_engine.csnp, panther_engine.hmmscore, panther_engine.refmap, panther_engine.treegrafter"` succeeds

## 3. CLI Version

- [ ] 3.1 Add `cli.py` (argparse, `--version` from the installed metadata) and `__main__.py`; verify `tests/test_cli.py` passes and covers the spec's "Installed command" and "Run as a module" scenarios, with both printing the same version, and that `uv run panther-engine --version` works from a shell

## 4. Tools Image

- [ ] 4.1 Add the root `.dockerignore` (allowlist: `engine/`, excluding `engine/.venv` and caches) and the `Dockerfile`'s `ARG`s and `blast` stage: the base image `python:3.13-slim-trixie` by digest, NCBI's BLAST+ 2.17.0 tarball per `TARGETARCH` with its sha256, keeping `blastp` and `blastdbcmd`. Verify the stage builds for `linux/arm64` and `linux/amd64`, `blastp -version` prints `2.17.0+` in each, and a wrong sha256 makes the build fail. Record where each checksum came from in a comment beside it
- [ ] 4.2 Add the `hmmer` stage: HMMER 3.4's source with its sha256, built and installed under `/opt/tools`; verify it builds for both architectures and `hmmscan -h` and `hmmsearch -h` print `HMMER 3.4` in each
- [ ] 4.3 Add `engine/tools-env/` with an explicit conda lock file for EPA-ng 0.3.8 per architecture (`linux-64`, `linux-aarch64`; build `_7`; a hash on every package), and the `epang` stage on `mambaorg/micromamba` by digest that creates `/opt/tools/conda` from the file for `TARGETARCH`; verify `epa-ng --version` prints 0.3.8 in that stage for both architectures
- [ ] 4.4 Add the `tools` stage: copy `/opt/tools` from the three stages at the same paths, add `uv` from `ghcr.io/astral-sh/uv:0.13.6` by digest, put the tools on `PATH`, set `UV_PYTHON_DOWNLOADS=never`, and create a non-root user. Verify for both architectures that `ldd` reports no missing library for any of the four programs (install any missing ones from Debian and list them in the Notes), and that each prints its pinned version as that user. Save each program's version output from the arm64 image as a fixture in `engine/tests/fixtures/tool-versions/`

## 5. Running Tools

- [ ] 5.1 Add `core/process.py` with `run_tool()` as design.md describes (absolute program path, argument list, `shell=False`, timeout, captured output), with its one `# noqa: S603` and the reason; verify `tests/test_process.py` passes and covers the spec's "Shell metacharacters in an argument" scenario with a fake tool in `tmp_path`, and that a scratch `subprocess.run([...])` elsewhere in `src/` is reported as `S603` (then removed)
- [ ] 5.2 Add the `tools` marker handling to `tests/conftest.py`: a missing tool skips with its name in the reason, or fails when `PANTHER_REQUIRE_TOOLS=1`; verify with a `tools`-marked test for a tool that doesn't exist, run natively, that it is reported as skipped naming the tool, and with `PANTHER_REQUIRE_TOOLS=1` that it fails naming the tool (the spec's two "Tests that need the tools" scenarios)
- [ ] 5.3 Add `core/tools.py` (the tools as data, found with `shutil.which`, versions read through `run_tool()`) and the `tools` subcommand; verify `tests/test_tools.py` passes: the version patterns parse the fixtures from 4.4; the spec's "A tool is missing" scenario, with `PATH` set to a folder holding fake tools for all but `epa-ng`; and a `tools`-marked test that the real tools report the pinned versions (skipped natively)

## 6. Engine Image and Compose

- [ ] 6.1 Add the `engine` stage: copy `engine/` to `/work/engine`, `uv sync --locked` into `/opt/venv` (`UV_PROJECT_ENVIRONMENT`), `PANTHER_REQUIRE_TOOLS=1`. On this machine (arm64), verify the spec's "Tool report in the image" scenario with `panther-engine tools`, and that `uv run --no-sync pytest` passes with no test skipped. Repeat for `linux/amd64` under emulation, and record both build times, uncached and cached, in the Notes
- [ ] 6.2 Add the root `compose.yaml` with the `engine` service as design.md describes (the mount at `/work/engine`, `UV_PROJECT_ENVIRONMENT=/opt/venv`, `UV_LOCKED=1`, `PYTHONDONTWRITEBYTECODE=1`, the ruff cache under `/tmp`, `PYTEST_ADDOPTS=-p no:cacheprovider`, the four checks as the default command). From a fresh clone, verify `docker compose run --rm engine` passes; `git status --ignored engine/` shows nothing new; and `uv run pytest` in the host's `engine/.venv` still works (the spec's "Engine checks run in the image" scenarios)
- [ ] 6.3 Write `docs/testing/engine.md`, following `docs/testing/README.md`: the compose commands first (all checks, one test, the CLI), then the native uv setup, the `tools` marker and `PANTHER_REQUIRE_TOOLS`, and the Windows note (clone inside WSL2). Verify every command in it runs as written, from the folder it names

## 7. CI

- [ ] 7.1 In `.github/workflows/ci.yml`, add the `engine` filter to `changes` (`engine/**`, `Dockerfile`, `.dockerignore`, `compose.yaml`, `ci.yml`) and the `engine` job in `engine/`, the same steps as the `api` job with its cache keyed on `engine/uv.lock`; add it to `ci-passed`'s `needs`. Verify actionlint (`uvx --from actionlint-py actionlint`) reports no errors, and that the job's steps, run in order from a copy of only the files git would commit, pass
- [ ] 7.2 Add the `engine-image` job: a matrix over `ubuntu-latest` and `ubuntu-24.04-arm`, `docker/setup-buildx-action` and `docker/build-push-action` pinned to commit SHAs (version in a comment), building the `engine` target with the GitHub Actions cache scoped per architecture and loaded locally, then `panther-engine tools` and `uv run --no-sync pytest` in the image; add it to `ci-passed`'s `needs`. Verify actionlint reports no errors, and that the job's build and test steps pass locally with `docker buildx build --target engine --load` and `docker run`
- [ ] 7.3 Add the `engine` and `engine-image` rows to the What CI Runs table in `docs/testing/README.md`, update its sentence about the missing engine job, and link `engine.md` from the Engine row of Kinds of Test; verify the commands named match `ci.yml`

## 8. Shared Docs

- [ ] 8.1 In `CONTRIBUTING.md`'s Spec Layout, add `engine-core` ("Behaviour every engine service shares: the CLI, the pinned external tools in the image, finding them, reporting their versions and running them without a shell") and remove `legacy-xml-endpoint`; in `docs/design/tech-stack.md`, name the package `panther_engine` in Engine conditions 1 and 2. Verify `npx markdownlint-cli2` passes from the repo root

## 9. Final Check

- [ ] 9.1 From a clean clone of the branch, in `engine/`: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest` passes, with the `tools` tests skipped; and from the root, `docker compose run --rm engine` passes with none skipped
- [ ] 9.2 A Windows developer, with the repo cloned inside WSL2, runs `docker compose run --rm engine` and `docker compose run --rm engine panther-engine tools`; verify both pass, and record who ran it, the date and the Docker Desktop version in the Notes. If no one can run it before merge, record that under Blockers and keep the proposal's open question
- [ ] 9.3 From the repo root, `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass

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

Open the pull request with these artifacts for review (Workflow follow-up). Then start with 1.1.

### Blockers

None yet.

### Failed approaches

None yet.

### Lessons learned

None yet.
