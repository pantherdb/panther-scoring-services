# Design

## Context

See proposal.md for why. The current state that shapes the approach:

- **Repo hosting.** `pantherdb/panther-scoring-services` is public and owned by an organization. The frontend developer has admin rights. The repo has nine collaborators, more than the three developers on this project.
- **What exists today.** There is no `.github/` folder and no `.claude/settings.json`. Only `frontend/` has code. `api/` and `engine/` hold a `.gitkeep`.
- **Frontend checks.** These scripts already exist: `format:check`, `lint`, `type-check`, `test`, `build`, and `test:e2e` (mock mode). Both Playwright projects use Chromium. Node must match `^22.22.2 || >=24.15.0`, and Node 24 is used locally. How to run them is in [docs/testing/frontend.md](../../../docs/testing/frontend.md).
- **OpenSpec.** It's pinned in the root `package.json`. `openspec validate --all` already runs.
- **Line endings.** Every tracked file is already LF, and `core.autocrlf` is `false`.
- **Decisions this relies on.** The review rules in [CONTRIBUTING.md](../../../CONTRIBUTING.md#review-rules), and the parity and divergence rules in [docs/parity/](../../../docs/parity/README.md). This change enforces them; it doesn't change them.

## Goals / Non-Goals

**Goals:**

- A pull request can't merge unless CI is green and a teammate has approved it. No one can push to `main` directly.
- When a pull request changes only docs, CI takes under a minute and nothing is left waiting.
- When the API and engine developers add their jobs, they only add jobs. They don't change the required checks or the ruleset.

**Non-Goals:**

- No `api/` or `engine/` lint, type or test jobs. Their tools are still Proposed, and the owners add the jobs.
- No OpenAPI drift check, parity golden-file check, or check that every divergence row has an approver. Each needs code that doesn't exist yet. They belong to the changes that create that code.
- No deployment, release or preview environments.
- No pre-commit hooks on developers' machines. CI is the gate, and local hooks differ across operating systems.

## Decisions

### One workflow, with one required check

`.github/workflows/ci.yml` has these jobs:

| Job | Runs | What it does |
| --- | ---- | ------------ |
| `changes` | Always | Works out which areas the change touches, with `dorny/paths-filter` |
| `frontend` | Only when `frontend/**` changes | `npm ci`, `format:check`, `lint`, `type-check`, `test`, `build`, then `npx playwright install --with-deps chromium` and `test:e2e` |
| `repo` | Always | Secret scan, Markdown lint, `npx openspec validate --all` |
| `dependency-review` | Pull requests only | `actions/dependency-review-action` |
| `ci-passed` | Always (`if: always()`) | Needs every job above, and fails if any of them failed or was cancelled. A skipped job counts as passing |

- **The ruleset requires only `ci-passed`.**
- **Why one summary check:** GitHub treats a required check that never reports as pending forever. A docs-only pull request would then be blocked by the skipped frontend check. Filtering with `paths:` at the workflow level has the same problem.
- **Alternative rejected: a workflow per area.** It's simpler to read, but each workflow would need its own required check, and every new area would mean editing the ruleset.
- **Slots for `api/` and `engine/`:** comments in `changes` and between the jobs mark where those jobs go.
- **Dependency review settings:**
  - It fails on advisories of moderate severity or worse. `markdownlint` depends on `katex`, which has a low-severity advisory with no fix.
  - It checks development dependencies as well as runtime ones; by default it checks only runtime.
  - Licences are limited to a list of permissive ones in `ci.yml`.

### Code changes need an OpenSpec change, or the `no-spec` label

The `openspec-change` job runs on pull requests.

- **How it decides:** it uses two more `paths-filter` outputs: `code` (`frontend/**`, `api/**`, `engine/**`) and `openspec-change` (`openspec/changes/**`).
- **When it fails:** when code changed and `openspec/changes/` didn't, unless the pull request has the `no-spec` label.
- **Re-running:** the workflow also triggers on `labeled` and `unlabeled`, so adding the label re-runs CI.
- **Why a label rather than text in the description:** it's a deliberate act, and anyone can filter the pull request list by it.

It checks only that a change exists. It can't check that the proposal was reviewed first, or that the code matches it; reviewers do that.

**Alternatives rejected:**

- **A warning instead of a failure.** Warnings get ignored, and this is the gate against unplanned AI-written code.
- **A line-count threshold.** It's arbitrary, and a 20-line change to scoring logic still needs a proposal.

Revisit after a month: if `no-spec` is used on most pull requests, the rule isn't working.

### Pin actions to commit SHAs, and keep them current with Dependabot

- Every `uses:` names a full commit SHA, with the version in a comment. A tag can be moved to different code; a SHA can't.
- `.github/dependabot.yml` updates `github-actions` only, weekly. Without it, pinned SHAs go stale.
- npm updates are left out. With them, Dependabot would open pull requests that bump the accepted stack's majors.

### Secret scanning: two layers

1. **GitHub push protection,** turned on in the repo settings. It's free for public repositories, and it rejects a push that contains a known secret format before the secret is on GitHub.
2. **gitleaks in the `repo` job.** It scans only the pull request's commits, or a push's new commits, and catches generic secrets that push protection doesn't recognize. The release binary is downloaded at a pinned version, and its SHA-256 is checked before it runs.

**Alternatives rejected:**

- **`gitleaks-action`.** It needs a paid licence for repositories owned by an organization.
- **The gitleaks container image.** Inside it, git refuses to read a checkout owned by a different user ("dubious ownership") unless extra git config is passed in.

### Markdown lint

- `markdownlint-cli2` runs with `.markdownlint-cli2.jsonc`. It's a pinned dev dependency in the root `package.json`, beside OpenSpec, so `npx markdownlint-cli2` runs the same version locally and in CI. Its globs include `.github/**/*.md` explicitly, because `**` skips dot-folders.
- **Rules turned off:**
  - `MD013` (line length): the docs use one paragraph per line.
  - `MD033` (inline HTML): it isn't needed, but it's harmless.
- **Rules kept:** the rest, notably heading levels, fenced-code languages and list style.
- **Ignored folders:** `.claude/`, `.agents/` (generated by `openspec init`), `node_modules/`, and `frontend/` build output.
- **Fixing existing docs:** existing Markdown is fixed in this change, not ignored. Otherwise the first docs pull request after this one fails on problems it didn't create.

### `CODEOWNERS`: all three for now, then an owner and a backup per area

For now, until backups are chosen:

```text
*             @tmushayahama @mugitty @dustine32
/frontend/    @tmushayahama @mugitty @dustine32
/api/         @mugitty @tmushayahama @dustine32
/engine/      @dustine32 @tmushayahama @mugitty
```

Once backups are chosen:

```text
/frontend/                     @tmushayahama @<backup>
/api/                          @mugitty @<backup>
/engine/                       @dustine32 @<backup>
/docs/parity/divergences.md    @dustine32 @<science-owner>
```

- **Area lines list the owner first.** On those lines that order is only for people reading the file, until the backups narrow them.

- **The default line (`*`) covers everything else:** shared docs, `openspec/`, `.github/`, `CLAUDE.md`. Every developer is requested on those.
- **Why each area will have a backup:** GitHub doesn't count the author's own approval. If a folder had only one owner, that owner's own pull requests could never get a code-owner approval.
- **Why all three on every path is only for now:** it's simpler, but any teammate can approve `engine/` code, and the reviewer GitHub requests doesn't tell you whose area it is. It still keeps approvals within the team, and the repo has nine collaborators.
- **No placeholders.** Every login in the file is real, so "require code owner review" is on from the start. The `divergences.md` line is added once the science owner is known; until then, the default line covers that file.
- **What it can't enforce:** "a cross-cutting change needs all three", and science sign-off on divergences. GitHub can require one code owner per path, not every one. Both stay review rules, and the pull request template asks for them.

### Branch protection as a ruleset kept in the repo

- `.github/rulesets/main.json` holds a repository ruleset for `~DEFAULT_BRANCH`.
- It's applied with `gh api --method POST repos/pantherdb/panther-scoring-services/rulesets --input .github/rulesets/main.json`, and later changes use `PUT` with the ruleset's id.
- **What it sets:**
  - `deletion` and `non_fast_forward`
  - `pull_request`: 1 approval, dismiss stale reviews on push, require code-owner review, require all review threads to be resolved
  - `required_status_checks`: `ci-passed`, with "require branches to be up to date" off, because with three people that only causes rebase churn. The check is tied to the GitHub Actions app (`integration_id` 15368), so only a workflow run can satisfy it
- **No bypass actors.** Everyone on the team is a repo admin, so an admin can still edit the ruleset itself.
- **Alternative rejected: classic branch protection set by hand in Settings.** Rulesets are GitHub's current mechanism. A JSON file can be reviewed in a pull request, and the settings can be rebuilt if someone changes them by hand.

### Shared Claude Code settings

`.claude/settings.json` holds only `permissions.deny`:

- `Edit(//**/panther-workspace/**)`. It's anchored at the filesystem root, so it matches the folder wherever each developer cloned it.
  - A relative `../panther-workspace/**` would match nothing: a rule only matches files under its anchor.
  - `Write(...)` path rules never match either. `Edit` rules cover the Write tool as well.
- **Force-pushes and pushes to `main`,** as `Bash(...)` rules and the same patterns as `PowerShell(...)` rules:
  - `git push --force*`, `git push -f*`, `git push * --force*`, `git push * -f`, `git push * -f *`
  - `git push * main`, `git push * *:main`

These are guardrails for the assistant, not security. Bash patterns can be worked around (for example `git -C . push`), and a script Claude runs isn't checked at all. The ruleset is what actually stops a push. Each developer's own settings still apply, and `deny` always wins over them.

### Line endings and editor settings

- **`.gitattributes`:**
  - `* text=auto eol=lf`
  - binary types marked `binary`
  - `frontend/src/app/api/schema.d.ts linguist-generated=true`. This fixes the output path for `npm run api:types`.
  - a comment asking the engine developer to add `-text` for the golden-files folder once its path is chosen. Golden files must be compared byte for byte, so git mustn't convert them.
- **`.editorconfig`:** UTF-8, LF, a final newline, trimmed trailing whitespace (except in `.md`), and 2-space indents. Python files use 4 spaces.
- **`.nvmrc` at the root:** `24`, used by CI's `setup-node` and by developers.
- **Renormalizing:** every file is already LF, so `git add --renormalize .` should change nothing. If it does change something, that goes in its own commit.

### `CONTRIBUTING.md` additions

New sections, each a short list:

- **Definition of Done:**
  - CI green
  - area owners approved
  - `tasks.md` ticked, with its Notes current
  - docs updated
  - the change archived after merge
- **Pull Request Size:** under about 400 changed lines, not counting lock files and generated files. Larger pull requests are split, or explained in the description.
- **AI-Written Code:**
  - You own what you merge.
  - The reviewer can ask about any line, and "the assistant wrote it" isn't an answer.
  - New dependencies are named in the proposal.
- **Gates:** what CI checks, what the ruleset enforces, and how to read a failed `ci-passed`.

`CLAUDE.md` gets one sentence under Development Workflow: CI (`ci-passed`) and the `main` ruleset are the enforced gates.

## Risks / Trade-offs

- **Risk: the ruleset is applied before the CI workflow is on `main`.** Every pull request then waits on a check that never runs, including the one that adds CI.
  **Mitigation:** apply the ruleset as the last task, after this change merges. Confirm `ci-passed` has reported on `main` first.
- **Risk: Playwright on CI is slow or flaky.** Installing the browser takes about a minute.
  **Mitigation:** install Chromium only, and cache `~/.cache/ms-playwright` keyed on the Playwright version. CI already gets `retries: 1` from `playwright.config.ts`, and traces are uploaded when a test fails.
- **Risk: no bypass on the ruleset locks the team out in an emergency.**
  **Mitigation:** a repo admin can edit or turn off the ruleset in Settings. That is deliberate, and visible in the audit log.
- **Risk: any of the three can approve any area until backups are chosen.**
  **Mitigation:** the review rule in `CONTRIBUTING.md` (area owners approve) still applies, and the pull request template asks for it. Narrowing `CODEOWNERS` is a one-file pull request.
- **Risk: every admin can turn the ruleset off.**
  **Mitigation:** it's a team agreement. Every change shows in the audit log, and `.github/rulesets/main.json` is the record of what it should be.
- **Trade-off: one required approval.** The rule that cross-cutting changes need all three relies on reviewers following it. The pull request template has a box for it.
- **Trade-off: Markdown lint on existing docs.** The first run may touch many files. It's done once, here, so later pull requests aren't blamed for old problems.

## Migration Plan

1. Merge order: `chore/adopt-openspec`, then `feat/scaffold-frontend`, then this change.
2. Once this change is on `main`, check that `ci-passed` has run on a `main` commit.
3. Turn on secret scanning and push protection: Settings, then Code security.
4. Apply `.github/rulesets/main.json` with `gh api`, then open a test pull request to check it's enforced.
5. Later, once backups are chosen and the science owner is known, narrow `CODEOWNERS` in a follow-up pull request. The ruleset doesn't change.

**Rollback:** delete or disable the ruleset in Settings, then Rules. CI files can be reverted in a normal pull request.

## Open Questions

These don't change the approach or the tasks:

- **Who backs up whom.** Narrows the area lines in `CODEOWNERS`.
- **The science owner's GitHub login.** Adds the `divergences.md` line.
