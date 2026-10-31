---
name: spill-the-tea
description: Team catch-up for pantherdb/panther-scoring-services. It asks whose view (yours, Dustin's or Anushya's) and which areas (engine, api, frontend), then shows what's waiting on that person, what they're waiting on from others, and what changed since the last check. Then it starts the follow-up work, and confirms before posting anything. Use when someone says "spill the tea", "what's waiting on me", "what is Dustin waiting on", "anything new from Dustin" or "did Anushya reply", or runs /spill-the-tea.
---

# spill-the-tea

What's going on in `pantherdb/panther-scoring-services`, from one person's side, for the areas they choose.

**Arguments:** $ARGUMENTS. They may already answer the two questions below, for example `dustine32 engine`, or `me api frontend`. `since <date>` overrides the last check.

## The Team

| Person | GitHub | Areas by default |
| ------ | ------ | ---------------- |
| Tremayne | `tmushayahama` | frontend and api; frontend only once Anushya takes over the api |
| Dustin | `dustine32` | engine |
| Anushya | `mugitty` | api |

- **Each area is its folder:** `engine/`, `api/` or `frontend/`.
- **Shared files belong to everyone,** and every view includes them: `Dockerfile`, `compose.yaml`, `.github/`, `CLAUDE.md`, `CONTRIBUTING.md`, `docs/` and `openspec/`.
- **If `.github/CODEOWNERS` or the team table in `CLAUDE.md` disagrees** with this table, they win. Say so, and suggest updating this table.

## 1. Ask Whose View, and Which Areas

Unless the arguments answer them, ask both questions at once, with AskUserQuestion:

- **Whose view?** The person running this first, found with `gh api user --jq .login`, marked as the default; then the other two.
- **Which areas?** Multiple choice: engine, api, frontend, with the chosen person's default areas recommended.

For example:
- "What is Dustin waiting on from me?" is **me + engine**.
- "What's on Anushya's plate?" is **`mugitty` + api**.

## 2. Gather

```bash
R=pantherdb/panther-scoring-services
ME=$(gh api user --jq .login)
PERSON=<the chosen login>
STATE="$(git rev-parse --git-common-dir)/spill-the-tea/last-$PERSON-<areas, joined with +>"
SINCE=$(cat "$STATE" 2>/dev/null || date -u -d '2 days ago' +%Y-%m-%dT%H:%M:%SZ)
```

The last check is kept per view, in the clone's git folder, so it's never committed, and worktrees share it.

- **Open PRs, with their files:**
  `gh pr list -R $R --state open --json number,title,author,isDraft,reviewDecision,reviewRequests,mergeable,files,url`
  - Keep those that touch the chosen areas or the shared files.
  - For each one kept, read its reviews (`repos/$R/pulls/<n>/reviews`), its inline comments (`pulls/<n>/comments`), its conversation (`issues/<n>/comments`) and its CI (`gh pr checks <n>`).
- **Open issues:**
  - `gh issue list -R $R --search "involves:$PERSON"`
  - `gh issue list -R $R --search "assignee:$PERSON"`
  - Read the newest comments on each.
- **Since the last check:**
  - merged PRs: `gh pr list -R $R --state merged --search "merged:>=$SINCE" --json number,title,author,files,url`, kept as above;
  - mentions: `gh pr list` and `gh issue list` with `--state all --search "mentions:$PERSON updated:>=$SINCE"`.

Read every comment and review in full before judging it.

## 3. Sort Into Three Lists

**Waiting on them.** The chosen person needs to act:

- a review requested from them;
- another person's PR in their area that they haven't reviewed;
- their own PR with changes requested, failing CI, or a conflict;
- a question or mention to them, where the thread's last word isn't theirs;
- an issue assigned to them.

**They're waiting on.** Others need to act:

- their PRs waiting for a review: who's asked, and who hasn't answered;
- their questions with no answer yet;
- their approved PRs that are ready to merge.

**What changed since the last check** in those areas:

- merges, new PRs, reviews, answers, and new or closed issues;
- whether the person's open branches now need `main` merged in. Check with `git merge-tree --write-tree origin/main origin/<branch>`.

## 4. Spill It

- Three short sections, in that order. One line per item: `#n` with its link, who did what, and what happens next.
- When the view is someone else's, also say which items the person running this can unblock. For example, "Dustin is waiting on you for #49's review".
- Use plain words, and keep it light.

## 5. Get It Moving, and Confirm What Goes Out

- **Work can start right away on the runner's own items:** reading code, planning fixes, drafting replies, running checks, and making review fixes on a branch. For anything bigger than a few edits, use an agent in its own worktree, and review its work before it goes on the PR's branch.
- **Ask before anything goes out:** posting a review, approving, replying, opening or editing an issue or PR, pushing, merging.
  - Show the exact text first.
  - For several items, ask once, with the choices listed.
- **After fixing a review:**
  - push;
  - post one reply on the PR that answers each point in order (blockers, the rest, optional), linking the commits;
  - re-request the reviewer: `gh api -X POST repos/$R/pulls/<n>/requested_reviewers -f "reviewers[]=<login>"`.

## Rules

The project's rules are in `CLAUDE.md` and `CONTRIBUTING.md`. These matter most here:

- **No AI attribution** in commits, PRs, comments or docs: no `Co-Authored-By` line for an assistant, and no "Generated with" footer.
- **Respect each area's owner.** Don't change another developer's area unless they ask for that change in a review or an issue, and say so in the PR.
- **Open every PR against `main`.** CI runs only on PRs into `main`, and a PR based on another PR's branch merges into that branch, not into `main`.
- **Plan in `openspec/`.** Decisions go into the change's design.md, answers into its proposal's Open Questions, and progress into tasks.md's Notes.
- **Public text describes the work, not who owns it.** Mention `@login` only where that person needs to act.
- **Don't disturb a developer's running services.** Their dev server (5173) or API (8000) may be running from the repository's compose project. Never `docker compose down`, `stop` or `up` that project; test on a spare port with `docker run`. In Git Bash, prefix `docker run` with `MSYS_NO_PATHCONV=1`.

## 6. Finish

Once the tea is spilled, save this check's time, so the next run for the same view starts from it:

```bash
mkdir -p "$(dirname "$STATE")" && date -u +%Y-%m-%dT%H:%M:%SZ > "$STATE"
```

If the run stops before the report, don't save it.
