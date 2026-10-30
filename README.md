# panther-scoring-services

Four of PANTHER's scoring services, rebuilt. They replace legacy Perl CGIs behind pantherdb.org:

- **`hmmscore`:** scores protein sequences against the PANTHER HMM library (sequence search).
- **`refmap`:** maps protein IDs to PANTHER families (gene list upload).
- **`csnp`:** coding-SNP impact scoring with the PANTHER-PSEP method ("Genetic Variant Impact").
- **`treegrafter`:** places a sequence in a PANTHER family tree, using EBI's Python `treegrafter`.

The frontend stack and the API's tooling are **accepted** ([docs/design/frontend-stack.md](docs/design/frontend-stack.md), [docs/design/api-stack.md](docs/design/api-stack.md)). The API's architecture and the engine are **proposed**, not final ([docs/design/tech-stack.md](docs/design/tech-stack.md)).

New to the repo? Start with [CONTRIBUTING.md](CONTRIBUTING.md): setup, the OpenSpec workflow and review rules.

## Folders

| Folder | What it is | Owner |
| ------ | ---------- | ----- |
| `frontend/` | Web UI: React 19, TypeScript, Vite, Mantine, Tailwind v4. See [frontend/README.md](frontend/README.md); conventions in [frontend/CLAUDE.md](frontend/CLAUDE.md) | Frontend developer |
| `api/` | FastAPI service for all four services, called by `frontend/` and by the PANTHER website (`panther-site-java`). See [api/README.md](api/README.md) | API developer |
| `engine/` | Engine: one Python package with a shared `core/` and a submodule per service, built as a library with a CLI that `api/` imports. See [docs/testing/engine.md](docs/testing/engine.md) | Engine developer |
| `docs/` | Design decisions, parity, testing, manual QA, code reviews, deployment. Start at [docs/README.md](docs/README.md) | Everyone |
| `openspec/` | Specs and change proposals (OpenSpec). The workflow is in [CLAUDE.md](CLAUDE.md#development-workflow) | Everyone |

To run everything with the pinned tools, you need only Docker. From the repository root:

```sh
docker compose run --rm engine         # the engine's checks, in the image
docker compose up --build api          # the API on localhost:8000
```

The native setup for each folder, and every command, is in [docs/testing/](docs/testing/README.md).

## Legacy Reference

The legacy code and its Phase 1 docs live in `panther-workspace`, a sibling of this repo (`../panther-workspace`). Only the parts for these four services are relevant here; [CLAUDE.md](CLAUDE.md) lists exactly which files.
