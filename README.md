# panther-scoring-services

Four of PANTHER's scoring services, rebuilt. They replace legacy Perl CGIs behind pantherdb.org:

- **`hmmscore`:** scores protein sequences against the PANTHER HMM library (sequence search).
- **`refmap`:** maps protein IDs to PANTHER families (gene list upload).
- **`csnp`:** coding-SNP impact scoring with the PANTHER-PSEP method ("Genetic Variant Impact").
- **`treegrafter`:** places a sequence in a PANTHER family tree, using EBI's Python `treegrafter`.

The frontend stack is **accepted** ([docs/design/frontend-stack.md](docs/design/frontend-stack.md)). The API and engine stacks are **proposed**, not final ([docs/design/tech-stack.md](docs/design/tech-stack.md)).

New to the repo? Start with [CONTRIBUTING.md](CONTRIBUTING.md): setup, the OpenSpec workflow and review rules.

## Folders

| Folder | What it is | Owner |
| ------ | ---------- | ----- |
| `frontend/` | Web UI: React 19, TypeScript, Vite, Mantine, Tailwind v4. Conventions in [frontend/CLAUDE.md](frontend/CLAUDE.md) | Frontend developer |
| `api/` | FastAPI service for all four services: scoring jobs, plus compatibility endpoints for the legacy website | API developer |
| `engine/` | Engine: one Python package with a shared `core/` and a submodule per service, built as a library with a CLI that `api/` imports | Engine developer |
| `docs/` | Design decisions, parity, testing, manual QA, code reviews, deployment. Start at [docs/README.md](docs/README.md) | Everyone |
| `openspec/` | Specs and change proposals (OpenSpec). The workflow is in [CLAUDE.md](CLAUDE.md#development-workflow) | Everyone |

The code folders are empty for now.

## Legacy Reference

The legacy code and its Phase 1 docs live in `panther-workspace`, a sibling of this repo (`../panther-workspace`). Only the parts for these four services are relevant here; [CLAUDE.md](CLAUDE.md) lists exactly which files.
