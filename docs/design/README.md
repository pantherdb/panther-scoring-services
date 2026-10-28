# Design

Architecture and tech decisions: what we chose, why, what we rejected, and what is still open.

## What Goes Here

- Tech stack and architecture choices.
- Contracts between the parts: frontend ↔ api, api ↔ engine.
- Decisions about the scientific method, such as the thresholds or adding HMMER or RAxML (milestone M2).

The proposal, design and tasks for one change go in `openspec/changes/<change>/`, not here. A change's `design.md` links to the decisions here that it relies on.

## How to Write One

- Name files by topic, in kebab-case: `tech-stack.md`, `job-queue.md`.
- Put a status line at the top: **Proposed**, **Accepted** or **Superseded**, with the date.
- End with a **Review** table listing who must sign off and their status.
- When a decision changes, don't delete the old doc. Mark it **Superseded** and link to the new one.

## Docs

| Doc | Status |
| --- | ------ |
| [tech-stack.md](tech-stack.md) | Proposed, 2026-10-27 (API, engine, shared concerns) |
| [frontend-stack.md](frontend-stack.md) | Accepted, 2026-10-28 |
