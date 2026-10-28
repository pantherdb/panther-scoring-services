# panther-scoring-services

PANTHER's coding-SNP (cSNP) impact scoring, rebuilt. It scores amino-acid substitutions with the PANTHER-PSEP method, replacing the legacy Perl CGI behind pantherdb.org's "Genetic Variant Impact" tool.

The frontend stack is **accepted** ([docs/design/frontend-stack.md](docs/design/frontend-stack.md)). The API and engine stacks are **proposed**, not final ([docs/design/tech-stack.md](docs/design/tech-stack.md)).

New to the repo? Start with [CONTRIBUTING.md](CONTRIBUTING.md): setup, the OpenSpec workflow and review rules.

## Folders

| Folder | What it is | Owner |
| ------ | ---------- | ----- |
| `frontend/` | Web UI: React 19, TypeScript, Vite, Mantine, Tailwind v4. Conventions in [frontend/CLAUDE.md](frontend/CLAUDE.md) | Frontend developer |
| `api/` | FastAPI service: scoring jobs, plus the legacy XML compatibility endpoint | API developer |
| `engine/` | Scoring engine: Python port of the Perl pipeline, built as a library with a CLI that `api/` imports | Engine developer |
| `docs/` | Design decisions, parity, testing, manual QA, code reviews, deployment. Start at [docs/README.md](docs/README.md) | Everyone |
| `openspec/` | Specs and change proposals (OpenSpec). The workflow is in [CLAUDE.md](CLAUDE.md#development-workflow) | Everyone |

The code folders are empty for now.

## Legacy Reference

The legacy code and its Phase 1 docs live in `panther-workspace`, a sibling of this repo (`../panther-workspace`). Only the cSNP parts are relevant here; [CLAUDE.md](CLAUDE.md) lists exactly which files.
