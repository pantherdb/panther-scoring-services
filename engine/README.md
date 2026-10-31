# engine

The scoring engine for PANTHER's four scoring services (`csnp`, `refmap`, `hmmscore`, `treegrafter`): one Python package, `panther_engine`, with a command line, `panther-engine`. It's a library, not a web service. The API in [`api/`](../api/README.md) imports it as a path dependency and calls it in its worker processes, so the boundary between them is a typed function call, never HTTP.

Each service is a submodule beside a shared `core/`. Each one either ports a legacy Perl service and proves it gives the same output, or, for `treegrafter`, adopts EBI's Python version. Only `csnp` is ported so far.

## Quick Start

Natively, from `engine/`, with uv 0.13.6 or later. uv downloads Python 3.13 if it isn't on the machine:

```sh
uv sync                                                       # .venv from uv.lock, with the dev tools
uv run panther-engine csnp sample fetch --data-dir ../.data   # the cSNP data sample, once (157 MB)
uv run pytest                                                 # the tests that run a tool skip natively
```

With the pinned tools, as CI runs it, from the repository root. You need only Docker:

```sh
docker compose run --rm engine                                # lint, format, types and every test
docker compose run --rm engine panther-engine tools           # each tool's version and path
```

Fetching the sample through compose, and every other command, are in [docs/testing/engine.md](../docs/testing/engine.md).

## The Stack

The engine's architecture is **proposed**, not final: "Engine: Agree, With Conditions" in [tech-stack.md](../docs/design/tech-stack.md#engine-engine-agree-with-conditions). Its tooling is the API's **accepted** tooling, at the same versions ([api-stack.md](../docs/design/api-stack.md)).

| Concern | Choice | Why |
| ------- | ------ | --- |
| Language | Python 3.13 | The API's language, so the API can import the engine. Porting the Perl removes the last Perl from these services |
| Shape | A library with a CLI, in a `src/` layout. Distribution `panther-engine`, package `panther_engine` | Engine condition 1: one function call between `api/` and `engine/` saves a network hop, a deployment and a second contract. The CLI is for checks by hand, the data sample and parity runs |
| Packages | uv 0.13.6 or later, with the `uv_build` backend and a committed `uv.lock` | The same tool as the API, for Python, the virtualenv and the lockfile |
| Runtime dependencies | None: the standard library only | Nothing has needed one yet. A new dependency comes with an OpenSpec proposal |
| Lint and format | Ruff 0.17.3, with the API's rules except `FAST`, which only checks FastAPI code | The rules include `S`, from bandit: `S603` flags a `subprocess` call outside `run_tool()` |
| Types | basedpyright 1.40.2, strict, over `src/` and `tests/` | The same as the API |
| Tests | pytest 9.2.0, with the `tools` and `data` markers | A test that needs a tool or a data sample says so, and skips without it. The image fails it instead when a tool is missing, and CI when the sample is |
| External tools | BLAST+ 2.17.0 (`csnp`), HMMER 3.4 (`hmmscore`, `treegrafter`), EPA-ng 0.3.8 (`treegrafter`) | Engine condition 4: kept as binaries, run with `subprocess`. Each service keeps its legacy toolchain; changing one needs the science owner |
| The pin | The `engine` stage of the root [`Dockerfile`](../Dockerfile): the Python base image by digest, each tool by version and sha256, for `linux/amd64` and `linux/arm64` | A tool's version is part of the reference: another BLAST+ can return other hits. The image is the pin for the runtime, the tests and CI |
| Data | A folder named by `PANTHER_DATA_DIR`, with each service's data under `<service>/<version>/` | Large frozen files, mounted read-only and checked against sha256 manifests. Developers and CI use a sample |

## The Services

| Service | Status | Tools | Reference |
| ------- | ------ | ----- | --------- |
| `csnp` | **Ported** (`port-csnp`). Matches the reference's goldens on the data sample | BLAST+ | The legacy Perl, `pantherdb/cSNP_analysis` at `cebb5ab` |
| `refmap` | Not started: a docstring only | None | The legacy Perl, `RefProteomeMapper/` |
| `hmmscore` | Not started: a docstring only | HMMER3 | The legacy Perl, `pantherScoring/` |
| `treegrafter` | Not started: a docstring only | HMMER3, EPA-ng | EBI's [`treegrafter`](https://github.com/ebi-pf-team/treegrafter), to be adopted and pinned by commit, not ported (Engine condition 5) |

### `csnp`, From the API

One protein per call. The API normalises and validates the request first, so the engine receives what the legacy scripts received:

```python
from panther_engine.csnp import SPECIES_CODES, CsnpInput, score

result = score(CsnpInput(sequence="MGWSCLVTGA…", substitutions=("A10E", "G15D"), species="HUMAN"))
result.family  # "PTHR10366", or None without a BLAST hit
result.scores[0]  # SubstitutionScore("A10E", 220, "possibly damaging", "0.50")
```

- **The pipeline is the legacy one,** step for step: `blastp` against the PANTHER9 database, the best hit and the mapped positions, then the trace-back through the family tree to an age, a message and pDel. Its defects are kept, such as `SCORE-2` and `MAP-4`, until a divergence row is approved.
- **`InputError`** means the input as a whole can't be scored: today, a sequence BLAST+ can't read (divergence row 8). The API reports it as `422`, with the message as it is.
- **Anything else is a `500`:** `ValueError` for input the API should have rejected, such as a species not in `SPECIES_CODES`, and `BlastError` when BLAST+ fails.
- **A substitution that can't be scored is a row of the result,** with the legacy "Not scored: …" message, not an error.

## Layout

```text
src/panther_engine/
  cli.py          the panther-engine command; each service adds its own subcommand
  core/           what every service shares
    process.py    run_tool(): the one place a subprocess starts. An absolute path, a list of
                  arguments, no shell
    tools.py      the external tools: finding each on PATH and reading its version
    data.py       the data folder, PANTHER_DATA_DIR, laid out as <service>/<version>/
    manifest.py   sha256 manifests of data files, and checking a folder against one
    errors.py     InputError, which the API reports as 422
  csnp/           PANTHER-PSEP, ported from the legacy scripts, citing their lines and quirk IDs
    scoring.py    score() and its types: the interface the API calls
    codes.py      SPECIES_CODES and SPECIES_NAMES: the 85 species of the PANTHER9 BLAST database
    blast.py      step 1, run_blastp.pl: blastp, with the query on stdin and the hits on stdout
    hits.py       step 2, parse_blastp.pl: the best hit, and each position mapped onto it
    psep.py       step 3, PANTHER_PSEP1.01.pl: the trace-back, the age, the message and pDel
    paml.py, rst.py, orig_tree.py, species.py
                  strict readers of the library files and the species tree
    legacy.py     the Perl's own readings of the same files, where they differ
    survey.py     the PAML_RST library survey
    sample.py     the data sample: build, fetch, verify. sample.json pins the current one
    parity.py     the parity cases, the run through the Perl, and the comparison
    cli.py        the csnp subcommands
  hmmscore/, refmap/, treegrafter/
                  a docstring each, naming the service's reference
tests/            pytest. conftest.py applies the tools and data markers, which pyproject.toml
                  declares, and has make_tool, which writes a fake tool
  fixtures/       hand-written library files, and each tool's recorded version output
  golden/csnp/    the reference's outputs the port must match; its README gives each file's source
tools-env/        EPA-ng's Bioconda lock, per architecture, for the image
```

## The CLI

`panther-engine`, or `python -m panther_engine`. Each command has `--help`.

| Command | What it does |
| ------- | ------------ |
| `panther-engine tools` | Each external tool's version and path. Exits with 1 if one is missing or its version can't be read |
| `panther-engine csnp score FASTA A10E … --species HUMAN` | Scores one protein as the API's `csnp` job does. Needs `blastp`, so run it in the image |
| `panther-engine csnp sample fetch` / `verify` / `build` | Fetches the cSNP data sample into the data folder, checks it, or builds a new one |
| `panther-engine csnp survey ARCHIVE` | Checks every family of the PAML_RST library, streaming the archive |
| `panther-engine csnp parity cases` / `reference` / `check` | Generates parity cases, runs them through the Perl in the `csnp-reference` image, and checks the port against its output |

## Working on It

- **Before a pull request,** from `engine/`: `uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest`. Natively the tool tests skip, so also run `docker compose run --rm engine` from the root.
- **Match the goldens.** A port must give the reference's output byte for byte, defects included. A difference ships only with an approved row in [divergences.md](../docs/parity/divergences.md). Write the parity tests before the port.
- **Start every external tool with `run_tool()`.** Never pass request data through a shell, and check values such as species codes against a known list.
- **Raise `InputError` only on purpose,** for a problem with the input as a whole. Write its message for the submitter, with no file paths or tool output. A problem with one item belongs in the result.
- **Shared code goes in `core/`,** not in one service's folder.
- **Port the Perl; don't copy it.** The legacy code is in `../panther-workspace`, which is read-only. [CLAUDE.md](../CLAUDE.md) lists the files for each service.
- **Plan changes in [`openspec/`](../openspec/).** The engine's specs are `engine-core`, `csnp-data` and `psep-engine`.

## More

- [docs/testing/engine.md](../docs/testing/engine.md): every command, the test markers, the data sample, and scoring by hand.
- [docs/parity/](../docs/parity/README.md): the golden setup, the reference image, why each input is in the set, and the divergences.
- [docs/design/tech-stack.md](../docs/design/tech-stack.md): the engine's conditions, the pinned tools and the data (Proposed). [docs/design/api-stack.md](../docs/design/api-stack.md): the shared tooling (Accepted).
- [openspec/specs/](../openspec/specs/): `engine-core` (the CLI and the tools), `csnp-data` (the library and the sample), `psep-engine` (cSNP scoring).
