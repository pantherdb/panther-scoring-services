# engine

The scoring engine: `panther_engine`, a Python library with a command line, `panther-engine`. [`api/`](../api/README.md) imports it; there is no HTTP between them. It has a shared `core/` and one subpackage per service. `hmmscore`, `refmap` and `csnp` are ports of the legacy Perl. `treegrafter` adapts EBI's Python `treegrafter`. Each must match its reference's golden files ([docs/parity/](../docs/parity/README.md)).

## Quick Start

The external tools run only in the image: BLAST+ 2.17.0, HMMER 3.4 and EPA-ng 0.3.8. From the repository root, with Docker:

```sh
docker compose run --rm engine                          # lint, format, types and tests
docker compose run --rm engine panther-engine tools     # each tool's version and path
```

Natively, from `engine/`, with uv 0.13.6 or later. It's quicker for lint and unit tests, but the tests that need the tools skip:

```sh
uv sync
uv run pytest
```

## Layout

```text
src/panther_engine/
  cli.py           panther-engine: --version and tools; each service adds a subcommand
  core/process.py  run_tool(): the one place a subprocess starts, from an argument list, never a shell
  core/tools.py    the external tools: how to find each and read its version
  csnp/ hmmscore/ refmap/ treegrafter/
                   one subpackage per service
tests/             pytest; tests marked `tools` run the real tools
tools-env/         conda lock files for EPA-ng, one per CPU architecture
```

The image is built by the root [`Dockerfile`](../Dockerfile), which pins every tool by version and checksum. [`compose.yaml`](../compose.yaml) runs it.

## Rules

- **Start external tools only through `core.process.run_tool()`.** Ruff's `S` rules report other `subprocess` calls.
- **Shared code goes in `core/`:** data paths, tool runners, FASTA parsing, and a work directory per job.
- **Write the parity tests before porting a service.** Any difference from its reference needs an approved row in [docs/parity/divergences.md](../docs/parity/divergences.md).

## More

- [docs/testing/engine.md](../docs/testing/engine.md): every command, and the `tools` test marker.
- [docs/design/tech-stack.md](../docs/design/tech-stack.md): the Engine section, and Pinning Tool Versions.
- [openspec/specs/engine-core/spec.md](../openspec/specs/engine-core/spec.md): the behaviour every service shares.
