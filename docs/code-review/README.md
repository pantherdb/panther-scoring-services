# Code Review

Notes from code reviews that are worth keeping after the pull request closes: whole-area reviews, security reviews, and findings that need follow-up work.

Comments on a single pull request stay on the pull request.

## How to Write One

- Name it `YYYY-MM-DD-<topic>.md`, for example `2026-11-15-api-job-queue.md`.
- At the top, say what was reviewed: area, branch or commit range, and reviewer.
- List findings, most severe first. For each one, give the file, what is wrong, and what could go wrong because of it.
- End with **Follow-ups**: each one either links to an OpenSpec change in `openspec/changes/` or says why no action is needed.
