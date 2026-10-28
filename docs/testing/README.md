# Testing

How we test, and how to run each suite. Someone new should be able to run every suite from these docs alone.

## What Goes Here

- `strategy.md`: what each kind of test is responsible for, and what it isn't.
- One file per area with run instructions: `frontend.md`, `api.md`, `engine.md`. Cover the commands, the test data needed, and how to run a single test.

## Kinds of Test

| Kind | Area | Notes |
| ---- | ---- | ----- |
| Unit and component | `frontend/` | Vitest and React Testing Library |
| End-to-end | `frontend/` | Playwright, in three modes: against mocks, a real API, or an already-running site. See [frontend.md](frontend.md) |
| API | `api/` | Request validation, the job lifecycle, the legacy XML endpoint |
| Engine | `engine/` | Unit tests per pipeline step |
| Parity | `engine/` | Python vs the Perl golden files. See [../parity/](../parity/README.md) |

## What CI Runs

`.github/workflows/ci.yml` runs on every pull request and every push to `main`. The required check, `ci-passed`, fails if any job below failed.

| Job | When | What it runs |
| --- | ---- | ------------ |
| `frontend` | `frontend/` changed | From `frontend/`: `npm ci`, `npm run format:check`, `npm run lint`, `npm run type-check`, `npm test`, `npm run build`, then `npm run test:e2e` (mock mode, Chromium only) |
| `repo` | Always | From the root: `npx markdownlint-cli2`, `npx openspec validate --all`, and a gitleaks scan of the new commits |
| `dependency-review` | Pull requests | New dependencies with a moderate or worse advisory, or a licence outside the allowed list |

There are no `api/` or `engine/` jobs yet. Each owner adds theirs once the folder has code, with the parity suite in the engine's job. The comments in `ci.yml` say where.

Manual checks done by a person go in [../manual-qa/](../manual-qa/README.md), not here.
