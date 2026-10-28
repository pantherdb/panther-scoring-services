# Proposal

**Area:** cross-cutting

## Why

Today every rule in `CLAUDE.md`, `CONTRIBUTING.md` and `frontend/CLAUDE.md` is guidance only. Nothing stops a push to `main`, a merge without review, a committed secret, or a pull request full of code nobody read. The other two developers start writing code soon, many of them with an AI assistant. The gates have to be in place before that, not added after the first bad merge.

## What Changes

- **CI on every pull request** (GitHub Actions):
  - **Frontend:** format check, lint, type check, unit tests, build, and Playwright e2e in mock mode. It runs only when `frontend/` changes.
  - **Repo-wide:** secret scan, Markdown lint, and `openspec validate --all`.
  - **Dependency review:** fails on new dependencies with known vulnerabilities or disallowed licences.
  - **One summary check** that branch protection requires, so skipped jobs don't block pull requests.
  - `api/` and `engine/` jobs are left as marked slots for their owners to fill once those folders have code.
- **`CODEOWNERS`:** `frontend/` is owned by `tmushayahama`, `api/` by `mugitty` and `engine/` by `dustine32`. Until each area has a backup reviewer, all three developers are listed on every path. Shared files (`docs/design/`, `openspec/specs/`, `openspec/config.yaml`, `CLAUDE.md`, `CONTRIBUTING.md`, `.github/`) are owned by all three. `docs/parity/divergences.md` gets its own line once the science owner is known.
- **A pull request template.** It covers:
  - the OpenSpec change it belongs to, and its Area
  - the effect on parity and any divergence row it needs
  - new dependencies
  - how it was tested
  - a box confirming "I have read and can explain every line"
- **`.gitattributes` and `.editorconfig`:** LF line endings everywhere, byte-exact golden files, and generated OpenAPI types marked as generated so GitHub collapses them in review.
- **Shared Claude Code settings** (`.claude/settings.json`, committed). They deny edits to `../panther-workspace`, force-pushes, and pushes to `main`.
- **A branch ruleset on `main`,** kept as JSON in the repo and applied with `gh`:
  - changes only through pull requests
  - one approval, which must come from a code owner
  - approvals dismissed when new commits are pushed
  - the CI summary check must pass
  - no force-push and no deletion

  It's applied after the CI workflow is on `main`, because a required check has to exist first.
- **GitHub secret scanning with push protection** turned on. It's free for public repositories and blocks a secret before it reaches GitHub.
- **New `CONTRIBUTING.md` sections:** a definition of done, a pull request size norm, and the rule for AI-written code: you own what you merge.

## Capabilities

### New Capabilities

None. This change is tooling and process only; no system behaviour changes. `.openspec.yaml` sets `skip_specs: true`.

### Modified Capabilities

None.

## Impact

- **New files:**
  - `.github/workflows/ci.yml`
  - `.github/CODEOWNERS`
  - `.github/pull_request_template.md`
  - `.github/rulesets/main.json`
  - `.gitattributes`, `.editorconfig`
  - `.markdownlint-cli2.jsonc`
  - `.claude/settings.json`
- **Changed files:**
  - `CONTRIBUTING.md`: new sections.
  - `CLAUDE.md`: one line saying CI and the ruleset are the enforced gates.
  - Existing Markdown files: only where the linter flags a real problem.
  - Line endings: renormalized once by `.gitattributes`, so one commit changes only line endings.
- **GitHub settings,** changed by a repo admin: the ruleset, secret scanning and push protection.
- **Dependencies:** none at runtime. CI uses published GitHub Actions, pinned to commit SHAs, and the `markdownlint-cli2` and gitleaks tools.
- **Parity with the Perl:** not affected; no divergences are needed.
- **API contract:** not affected.
- **Team workflow:** after this, nobody can push to `main`, including admins, and every merge needs a teammate's approval. That includes your own pull requests to your own area: another developer approves them. Everyone on the team is a repo admin, and the ruleset binds admins too.

## Open Questions

- **Who backs up whom.** Deferred. Until it's decided, all three developers own every path, so any teammate can give the code-owner approval.
- **The science owner's GitHub login.** This is for `docs/parity/divergences.md`, and isn't needed until there are divergences.

Decided on 2026-10-28:

- **Logins:** `tmushayahama` (frontend), `mugitty` (API), `dustine32` (engine).
- **No bypass actors on the ruleset for now.** Everyone is an admin, so anyone can still edit the ruleset in an emergency, and that shows in the audit log.
- **One required approval.** The rule that cross-cutting changes need all three stays a review rule, because GitHub can't require approval from every listed owner.
- **Merge order.** CI's frontend job runs `frontend/` scripts that exist only on `feat/scaffold-frontend`. This change is branched from it, so the order is: `chore/adopt-openspec`, then `feat/scaffold-frontend`, then this one.
