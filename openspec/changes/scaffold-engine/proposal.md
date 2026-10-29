# Proposal

**Area:** engine

## Why

`engine/` is empty. Every service port, starting with cSNP's library survey and parity harness, needs a Python package to land in, with tooling, tests and CI already wired. It also needs the external tools it calls, at the versions [tech-stack.md](../../../docs/design/tech-stack.md) pins. The stack decided on 2026-10-29 is that the container image pins those tools, and that every developer runs them there, on macOS, Linux and Windows alike. That image doesn't exist yet.

The engine reuses the tooling in [api-stack.md](../../../docs/design/api-stack.md) (uv, Python 3.13, Ruff, basedpyright, pytest). That doc is Accepted, so no separate engine-stack doc comes first. The engine developer signs off in this change's review, and records the acceptance in `api-stack.md`'s Review table, where the engine developer's row is Pending.

## What Changes

- New uv project in `engine/`, with its own `pyproject.toml`, `uv.lock` and `.python-version` (3.13). The Python package is `panther_engine` (distribution `panther-engine`), in a `src/` layout.
- The package skeleton from tech-stack.md: `core/`, plus `csnp/`, `hmmscore/`, `refmap/` and `treegrafter/` subpackages, which are empty apart from a docstring naming each service's reference.
- A first piece of `core/`: finding the external tools and reading their versions, always with an argument list and never through a shell.
- A CLI, `panther-engine` (also `python -m panther_engine`), with `--version` and a `tools` subcommand that lists each tool and its version. Each service adds its own subcommand later.
- Tooling: the same Ruff rules (including the `S` security rules), basedpyright in strict mode and pytest as `api/`, at the same versions.
- A **tools image**, built from a new root `Dockerfile` for `linux/amd64` and `linux/arm64`: Python 3.13, uv, BLAST+ 2.17.0, HMMER 3.4 and EPA-ng 0.3.8, each at an exact version and checksum, and the base images pinned by digest. An `engine` target adds the engine project, for tests and the CLI.
- A root `compose.yaml` with an `engine` service, so a developer on any platform runs the engine's checks and CLI in the image. The API joins it in a later change.
- CI:
  - an `engine` job (lint, format, types, tests) on the runner;
  - an `engine-image` job that builds the image on amd64 and arm64 and runs the tests that need the tools inside it.
  - Both fill the slot left in `ci.yml`, and are added to `ci-passed`.
- Docs:
  - new `docs/testing/engine.md`;
  - `docs/testing/README.md`'s CI table gains the two jobs;
  - `tech-stack.md` names the package;
  - `CONTRIBUTING.md`'s Spec Layout gains `engine-core` and drops `legacy-xml-endpoint`, which the move to the JSON API (2026-10-29) left without a purpose.

New dependencies: none at runtime. The dev group has `ruff`, `basedpyright` and `pytest`, at the versions `api/` pins. The image adds the three tools above, plus the `python`, `uv` and `micromamba` base images.

Not in this change:

- **The cSNP library survey and the data sample.** They come in their own change, which also sets the golden-files folder and its `-text` rule in `.gitattributes`.
- **The Perl reference image** for parity tests (Engine condition 3). It belongs with the parity harness.
- **Any scoring logic,** data paths, per-job work directories or FASTA parsing in `core/`. Each arrives with the first service that needs it.
- **The API in the image or in `compose.yaml`,** and `api/` depending on `engine/`. Those are API changes.
- **Production deployment** and the staging server.

## Capabilities

### New Capabilities

- `engine-core`: behaviour every engine service shares. Here: the CLI, the pinned external tools in the image, and how the engine finds them, reports their versions and runs them without a shell. Data paths, work directories and tool runners join it as the services need them. Each service's scoring behaviour belongs to its own capability, such as `psep-engine`.

### Modified Capabilities

None.

## Impact

- **Code:** new files under `engine/`; `engine/.gitkeep` is removed.
- **New shared files:** root `Dockerfile`, `.dockerignore` and `compose.yaml`.
- **Changed shared files:**
  - `.github/workflows/ci.yml`: the `engine` filter, the `engine` and `engine-image` jobs, and `ci-passed`'s `needs`.
  - `CONTRIBUTING.md`: the Spec Layout rows.
  - `docs/testing/README.md`: the CI table rows.
  - `docs/design/tech-stack.md`: the package name.
  - `docs/design/api-stack.md`: the engine developer's Review row.
- **Docs:** new `docs/testing/engine.md`.
- **Dependencies:** the Python dev packages, locked in `engine/uv.lock`, and the tools and base images, pinned in the `Dockerfile`. Dependabot covers neither; versions change through a proposal.
- **Parity with each service's reference:** not affected. This change has no scoring logic and needs no divergences.
- **API contract:** not affected. The API doesn't import the engine yet.

## Open Questions

Each needs team verification.

- **GitHub's arm64 runners.** Can this public repository use `ubuntu-24.04-arm` for the arm64 image build? If not, CI builds amd64 only, and arm64 is checked on an Apple Silicon machine before merge.
- **Base image updates.** The `python`, `uv` and `micromamba` base images are pinned by digest, so security fixes arrive only when someone bumps them. Who does that, and how often?
- **Windows.** No one has yet run the engine image on Windows. A Windows developer should run the `compose.yaml` checks once, from WSL2, before this is called done.
- **HMMER and EPA-ng on arm64.** HMMER 3.4 is built from source, and Bioconda lists EPA-ng 0.3.8 for `linux-aarch64`. Neither has been run on arm64 here yet.
