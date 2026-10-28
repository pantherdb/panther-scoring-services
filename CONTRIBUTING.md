# Contributing

How the three of us work on this repo. The short version for Claude is in [CLAUDE.md](CLAUDE.md); this is the longer version for people.

## Setup

1. **Clone `panther-workspace` next to this repo.** The legacy cSNP code and its docs are read from `../panther-workspace`. It is read-only reference: never change files there.
2. **Install OpenSpec globally**, at the version pinned in `package.json`:

   ```sh
   npm install -g @fission-ai/openspec@1.15.0
   ```

   The `/opsx:*` commands call `openspec` directly, so it must be on your PATH.
3. **Use an AI assistant that has the OpenSpec commands.** Claude Code reads `.claude/commands/opsx/` and `.claude/skills/`. Other assistants read `.agents/skills/`. If yours needs something else, run `openspec init` again, select your tool, and commit what it generates.

## Workflow

Every non-trivial change goes through OpenSpec. We don't follow the five-phase PANTHER SDLC strictly: it was written for all of PANTHER, and this project is cSNP scoring only.

| Step | Command | What happens |
| ---- | ------- | ------------ |
| Explore (optional) | `/opsx:explore` | Think an idea through with the assistant. No files are written |
| Propose | `/opsx:propose <change-name>` | Creates `openspec/changes/<change-name>/` with `proposal.md`, `design.md`, `tasks.md` and spec deltas |
| Review | Open a pull request | The owner of every area the change touches approves it before any code is written |
| Apply | `/opsx:apply` | The assistant works through `tasks.md` and ticks tasks off |
| Archive | `/opsx:archive` | Spec deltas merge into `openspec/specs/`, and the change moves to `openspec/changes/archive/` |

The assistant drafts; we review, correct and own every artifact. Read the proposal and design before you approve them.

### What a Spec Delta Looks Like

Each requirement uses SHALL or MUST and has at least one scenario:

```markdown
## ADDED Requirements

### Requirement: Substitution input
The form SHALL accept one or more substitutions written as <reference><position><alternate>, for example A12P.

#### Scenario: Missing alternate residue
- **WHEN** the user enters "A12"
- **THEN** the form shows an error and does not submit
```

A delta can also have `## MODIFIED Requirements` and `## REMOVED Requirements` sections.

### Useful CLI Commands

| Command | What it does |
| ------- | ------------ |
| `openspec list` | Show active changes. Check it before proposing, to avoid overlapping someone else's work |
| `openspec status --change <change-name>` | Show which artifacts of a change are done |
| `openspec validate --all` | Check every spec and change is well formed |

## Conventions

- **One change per pull request.** The proposal can be reviewed on its own first; the implementation follows on the same branch or a new one.
- **Name changes verb-first, in kebab-case:** `add-scoring-form`, `define-scoring-api-contract`, `fix-substitution-parsing`.
- **State the Area** in every proposal: `frontend`, `api`, `engine` or `cross-cutting`.
- **Don't run two changes on the same capability at once.** Their deltas conflict when archived. If you must, agree the order with the other developer.
- **Archive when the work merges**, so `openspec/specs/` always describes what is actually built.
- **Keep the Notes in `tasks.md` current**: next action, blockers, failed approaches and lessons learned. Before archiving, move any lesson that matters beyond the change into `CLAUDE.md` or `docs/`.

## Spec Layout

Specs are organized by capability, not by developer. This is the starting layout; change it through a proposal if it stops fitting.

| Capability | Covers |
| ---------- | ------ |
| `scoring-input` | Validating sequence, substitutions and species. Shared by the UI and the API |
| `scoring-jobs` | The API job lifecycle: `POST /api/v1/jobs`, `GET /api/v1/jobs/{id}` |
| `scoring-ui` | The form, job status, results table, CSV export and help content |
| `psep-engine` | Pipeline behaviour, thresholds, and parity with the Perl |
| `legacy-xml-endpoint` | The synchronous XML endpoint that keeps `panther-site-java` working |

## Where Things Go

| What | Where |
| ---- | ----- |
| A change's proposal, design and tasks | `openspec/changes/<change-name>/` |
| What the system does now | `openspec/specs/` |
| Project-wide decisions that need named sign-off (tech stack, thresholds, HMMER/RAxML) | `docs/design/`, with a Review table |
| Parity setup and approved differences from the Perl | `docs/parity/`; the golden files live in `engine/` tests |
| Test strategy, manual QA, code reviews, deployment | The matching folder in `docs/`. Read its README first |

## Review Rules

- **Area owners approve.** A change that touches `frontend/`, `api/` or `engine/` needs that folder's owner. A `cross-cutting` change needs all three.
- **Contracts need both sides.** A change to the OpenAPI schema needs the frontend and API developers. A change to the engine interface needs the API and engine developers.
- **OpenSpec doesn't approve science.** Any difference from the Perl output ships only with a row in `docs/parity/divergences.md` that names an approver.
- **When the legacy code is unclear, write "needs team verification".** Don't guess, and don't let the assistant guess.
