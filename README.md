# panther-scoring-services

PANTHER's coding-SNP (cSNP) impact scoring, rebuilt. It scores amino-acid substitutions with the PANTHER-PSEP method, replacing the legacy Perl CGI behind pantherdb.org's "Genetic Variant Impact" tool.

The tech stack is **proposed**, not final. See [docs/design/tech-stack.md](docs/design/tech-stack.md).

## Folders

| Folder | What it is | Owner |
| ------ | ---------- | ----- |
| `frontend/` | Web UI: React 19, TypeScript, Vite, Tailwind v4 | Frontend developer |
| `api/` | FastAPI service: scoring jobs, plus the legacy XML compatibility endpoint | API developer |
| `backend/` | Scoring engine: Python port of the Perl pipeline, built as a library with a CLI that `api/` imports | Engine developer |
| `docs/` | Design decisions, parity, testing, manual QA, code reviews, deployment. Start at [docs/README.md](docs/README.md) | Everyone |
| `.plans/` | Task plans for ongoing work. See [.plans/template.md](.plans/template.md) | Everyone |

The code folders are empty for now.

## Legacy Reference

The legacy code and its Phase 1 docs live in `panther-workspace`, a sibling of this repo (`../panther-workspace`). Only the cSNP parts are relevant here; [CLAUDE.md](CLAUDE.md) lists exactly which files.
