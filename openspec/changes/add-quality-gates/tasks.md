# Tasks

## 1. Repo Hygiene Files

- [x] 1.1 Add `.gitattributes` (`* text=auto eol=lf`, binary types, `frontend/src/app/api/schema.d.ts linguist-generated=true`, a comment for the engine developer's golden-files `-text` line), `.editorconfig` and a root `.nvmrc` (`24`); verify `git add --renormalize .` followed by `git status` shows no changed files, or commit any it shows on their own
- [x] 1.2 Add `.claude/settings.json` with the `permissions.deny` rules from design.md; verify it's valid JSON and that, in a new Claude Code session, asking Claude to edit a file in `../panther-workspace` is refused

## 2. Pull Request Template and CODEOWNERS

- [x] 2.1 Add `.github/pull_request_template.md` (OpenSpec change link, Area, parity impact and divergence row, new dependencies, how it was tested, "all affected area owners approved" box, "I have read and can explain every line" box); verify it passes `markdownlint-cli2` (GitHub reads the template from `main`, so it's seen on a pull request only after merge: 6.3)
- [x] 2.2 Add `.github/CODEOWNERS` with the interim layout from design.md (all three logins on every path, owner first); verify `gh api repos/pantherdb/panther-scoring-services/codeowners/errors?ref=chore/add-quality-gates` returns no errors once the branch is pushed (GitHub requests reviewers from `main`'s copy, so that's checked after merge: 6.3)

## 3. CI Workflow

- [x] 3.1 Add `.github/workflows/ci.yml` with the `changes`, `frontend`, `repo`, `dependency-review` and `ci-passed` jobs from design.md. Every action pinned to a commit SHA with its version in a comment, Node from `.nvmrc`, npm and Playwright caches, and a Playwright report uploaded on failure. Mark the `api/` and `engine/` slots with comments; verify `ci-passed` runs and passes on the draft pull request
- [x] 3.2 Add `.markdownlint-cli2.jsonc` (`MD013` and `MD033` off; ignore `.claude/`, `.agents/`, `node_modules/`, `frontend/dist/`, `frontend/playwright-report/`, `frontend/test-results/`) and fix what it reports in existing Markdown; verify `npx markdownlint-cli2` passes locally and in the `repo` job
- [x] 3.3 Wire gitleaks into the `repo` job (release binary pinned by version and SHA-256, scanning the pull request's commits); verify it passes on this branch in CI. Locally it already passes on this branch's commits, and exits 1 on a throwaway repo with a made-up AWS key
- [ ] 3.4 Prove the summary check: push a docs-only commit and check that `frontend` is skipped and `ci-passed` still passes. Push a commit that breaks a frontend lint rule and check that `ci-passed` fails, then revert it. For `openspec-change`'s failing case, open a throwaway pull request that changes only `frontend/` without the label, check that it fails, add `no-spec`, check that it passes, then close it
- [x] 3.5 Add `.github/dependabot.yml` (`github-actions` only, weekly); verify it parses as YAML (Dependabot reads it from `main` only, so it's checked after merge: 6.3)
- [ ] 3.6 Add the `openspec-change` job (code changed without `openspec/changes/` fails unless the pull request has the `no-spec` label; re-runs on `labeled`/`unlabeled`) and create the `no-spec` label; document it under Small Fixes in `CONTRIBUTING.md`, in the pull request template and in `docs/testing/README.md`. Verify it passes on this pull request, which touches `openspec/changes/`. Its failing case is tested in 3.4

## 4. Documentation

- [x] 4.1 Add Definition of Done, Pull Request Size, AI-Written Code and Gates sections to `CONTRIBUTING.md`, and one sentence to `CLAUDE.md` under Development Workflow naming `ci-passed` and the `main` ruleset as the enforced gates; verify both pass `markdownlint-cli2` and their links resolve
- [x] 4.2 Add a CI note to `docs/testing/README.md`: which suites CI runs, and that the API and engine jobs are added by their owners; verify the commands it names match `ci.yml`

## 5. Branch Ruleset

- [x] 5.1 Write `.github/rulesets/main.json` as in design.md, with `require_code_owner_review: true`, one approval and no bypass actors; verify it parses and its required check name matches the `ci-passed` job name in `ci.yml`
- [x] 5.2 Document in `CONTRIBUTING.md` (Gates section) how to apply and update the ruleset with `gh api`, and how to roll it back; verify the commands are the ones used in 5.3

## 6. Turn It On (after this change is on `main`)

- [ ] 6.1 Confirm `ci-passed` has reported on a `main` commit, then turn on secret scanning and push protection (Settings → Code security); verify `gh api repos/pantherdb/panther-scoring-services --jq .security_and_analysis` shows both enabled
- [ ] 6.2 Apply the ruleset with `gh api --method POST .../rulesets --input .github/rulesets/main.json`; verify `git push origin main` with a test commit is rejected, and that a test pull request shows "Merging is blocked" until `ci-passed` passes and one approval is given
- [ ] 6.3 Check what GitHub reads only from `main`: a new pull request opens with the template filled in, requests the other two developers as code owners, and Dependabot's page (Insights → Dependency graph → Dependabot) lists the config without errors

## Workflow follow-up

- Archive with `/opsx:archive add-quality-gates` after group 6 is done.
- Later, in a small follow-up pull request rather than this change: narrow `CODEOWNERS` to an owner and a backup per area, and add the `divergences.md` line with the science owner.

## Notes

### Next action

Push `chore/add-quality-gates` and open a draft pull request against `main`, so CI runs. Then check 2.2, 3.1 to 3.3 on it, and do 3.4. Everything that can be checked locally passes:

- the frontend checks (`format:check`, `lint`, `type-check`, `test`)
- `npx markdownlint-cli2` (22 files)
- `openspec validate`
- gitleaks on this branch's commits

Until the first two branches merge, the draft pull request also shows their commits.

### Blockers

- Group 6 needs this change merged to `main` first.

### Failed approaches

- **`markdownlint-cli2` 0.23.3 (2026-10-28).** I picked it as the newest release over two weeks old. It pulled in a high and two moderate advisories (`markdown-it`, `smol-toml`), which dependency review would fail on. 0.24.0 fixes them.
- **The gitleaks container image (2026-10-28).** Dropped before trying it in CI. In a container, git rejects a checkout owned by another user unless extra config is passed in. The checksummed release binary avoids that.

### Lessons learned

- **Dependency review needs the dependency graph (3.1, 2026-10-28).** It was off for this repo, and the API couldn't switch it on. It had to be done by hand in Settings → Advanced Security.
- **The first licence list was too narrow (3.1).** It rejected MIT-0, BSD-2-Clause-Views and PSF-2.0, all permissive, used by `@csstools/*`, `uri-js` and `argparse`. When dependency review rejects a licence, check whether it's permissive before adding it to the list.

- **Claude Code path rules (1.2, 2026-10-28).**
  - `Write(...)` path rules never match; `Edit(...)` rules cover the Write tool as well.
  - A relative rule can't reach above its anchor, so `../panther-workspace/**` matches nothing. `Edit(//**/panther-workspace/**)` works wherever the folder is cloned, and a probe edit was refused.
  - Worth a line in `CLAUDE.md` or `CONTRIBUTING.md` at archive.
- **What GitHub reads only from `main` (2.1, 2.2, 3.5).** These take effect only after merge, so a branch's own pull request can't test them:
  - the pull request template
  - `CODEOWNERS` review requests
  - Dependabot config

  CI workflows do run from the pull request's branch.
- **`markdownlint-cli2` skips dot-folders with `**`.** `.github/**/*.md` has to be listed explicitly.
- **gitleaks allowlists AWS's documented example key** (`AKIAIOSFODNN7EXAMPLE`). To test that a scan fails, use a made-up key.
