# Contributing

How the three of us work on this repo. The short version for Claude is in [CLAUDE.md](CLAUDE.md); this is the longer version for people.

## Setup

1. **Clone `panther-workspace` next to this repo.** The legacy code for the four services and its docs are read from `../panther-workspace`. It is read-only reference: never change files there.
2. **Install OpenSpec globally**, at the version pinned in `package.json`:

   ```sh
   npm install -g @fission-ai/openspec@1.15.0
   ```

   The `/opsx:*` commands call `openspec` directly, so it must be on your PATH.
3. **Use an AI assistant that has the OpenSpec commands.** Claude Code reads `.claude/commands/opsx/` and `.claude/skills/`. Other assistants read `.agents/skills/`. If yours needs something else, run `openspec init` again, select your tool, and commit what it generates.

## Workflow

Every non-trivial change goes through OpenSpec. We don't follow the five-phase PANTHER SDLC strictly: it was written for all of PANTHER, and this project covers four scoring services.

| Step | Command | What happens |
| ---- | ------- | ------------ |
| Explore (optional) | `/opsx:explore` | Think an idea through with the assistant. No files are written |
| Propose | `/opsx:propose <change-name>` | Creates `openspec/changes/<change-name>/` with `proposal.md`, `design.md`, `tasks.md` and spec deltas |
| Review | Open a pull request | The owner of every area the change touches approves it before any code is written |
| Apply | `/opsx:apply` | The assistant works through `tasks.md` and ticks tasks off |
| Archive | `/opsx:archive` | Spec deltas merge into `openspec/specs/`, and the change moves to `openspec/changes/archive/` |

The assistant drafts; we review, correct and own every artifact. Read the proposal and design before you approve them.

### Small Fixes

A typo, a broken link, a one-line bug fix or a dependency bump doesn't need a proposal. Add the **`no-spec`** label to the pull request instead.

- **The check:** CI's `openspec-change` check fails a pull request that changes code in `frontend/`, `api/` or `engine/` without touching `openspec/changes/`, unless it has that label.
- **Adding the label re-runs CI.**
- **When in doubt, propose.** If the fix changes behaviour someone would notice, or touches more than one area, it isn't small.
- **Use is visible.** Anyone can filter the pull request list by `no-spec`, and we look at how often it's used.

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

## Definition of Done

A change is done when:

- `ci-passed` is green.
- The owner of every area it touches has approved it.
- Every task in `tasks.md` is ticked, and its Notes are current.
- Docs are updated, or nothing in `docs/` needed to change.
- After merge, the change is archived with `/opsx:archive`.

## Pull Request Size

Keep pull requests under about 400 changed lines, not counting lock files and generated files. Split a larger one, or say in the description why it can't be split. A reviewer can't really read 2,000 lines, so a big pull request gets approved without being reviewed.

## AI-Written Code

- **You own what you merge.** The reviewer can ask about any line, and "the assistant wrote it" isn't an answer.
- **Read the diff before you open the pull request.** Run `/code-review` first if you like, but it doesn't replace reading.
- **No new dependencies without a proposal.** Name each new package in the change's proposal; dependency review in CI flags the rest.

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
| Project-wide decisions that need named sign-off (tech stack, scope, thresholds, a service's scientific method) | `docs/design/`, with a Review table |
| Parity setup and approved differences from the Perl | `docs/parity/`; the golden files live in `engine/` tests |
| Test strategy, manual QA, code reviews, deployment | The matching folder in `docs/`. Read its README first |

## Review Rules

- **Area owners approve.** A change that touches `frontend/`, `api/` or `engine/` needs that folder's owner. A `cross-cutting` change needs all three.
- **Contracts need both sides.** A change to the OpenAPI schema needs the frontend and API developers. A change to the engine interface needs the API and engine developers.
- **OpenSpec doesn't approve science.** Any difference from the Perl output ships only with a row in `docs/parity/divergences.md` that names an approver.
- **When the legacy code is unclear, write "needs team verification".** Don't guess, and don't let the assistant guess.

## Gates

Pull requests and CI are what actually stop mistakes. Everything else here is agreement.

| Gate | What it does |
| ---- | ------------ |
| `main` ruleset (`.github/rulesets/main.json`) | No direct pushes, force-pushes or deletion of `main`. Every merge needs a pull request, one approval from a code owner, resolved review threads and a passing `ci-passed`. Approvals are dismissed when new commits are pushed. It applies to admins too |
| `CODEOWNERS` (`.github/CODEOWNERS`) | Who GitHub asks to review, and whose approval counts |
| CI (`.github/workflows/ci.yml`) | What each job runs is in [docs/testing/README.md](docs/testing/README.md#what-ci-runs). Code changes need an OpenSpec change or the `no-spec` label ([Small Fixes](#small-fixes)) |
| Secret scanning with push protection | GitHub rejects a push that contains a known secret format |
| `.claude/settings.json` | Stops the assistant editing `panther-workspace`, force-pushing or pushing to `main`. A guardrail, not security |

**When `ci-passed` fails,** it only reports the other jobs' results. Open the pull request's Checks tab, find the job marked failed, and read its log. A failed `frontend` e2e run uploads a `playwright-report` artifact with traces.

### Changing the Ruleset

The ruleset is kept in the repo so changes to it are reviewed. Change the JSON in a pull request, then a repo admin applies it:

```sh
# First time: create it
gh api --method POST repos/pantherdb/panther-scoring-services/rulesets --input .github/rulesets/main.json

# Later: find its id, then replace it
gh api repos/pantherdb/panther-scoring-services/rulesets --jq '.[] | select(.name == "main") | .id'
gh api --method PUT repos/pantherdb/panther-scoring-services/rulesets/<id> --input .github/rulesets/main.json
```

**In an emergency,** an admin can turn it off in Settings → Rules → Rulesets → `main` (set Enforcement to Disabled), or with `gh api --method DELETE repos/pantherdb/panther-scoring-services/rulesets/<id>`. Tell the team, and turn it back on with the commands above.
