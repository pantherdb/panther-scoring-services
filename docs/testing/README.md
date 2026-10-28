# Testing

How we test, and how to run each suite. Someone new should be able to run every suite from these docs alone.

## What Goes Here

- `strategy.md`: what each kind of test is responsible for, and what it isn't.
- One file per area with run instructions: `frontend.md`, `api.md`, `backend.md`. Cover the commands, the test data needed, and how to run a single test.

## Kinds of Test

| Kind | Area | Notes |
| ---- | ---- | ----- |
| Unit and component | `frontend/` | Same setup as noctua: Vitest and React Testing Library |
| End-to-end | `frontend/` | Playwright, against a running API |
| API | `api/` | Request validation, the job lifecycle, the legacy XML endpoint |
| Engine | `backend/` | Unit tests per pipeline step |
| Parity | `backend/` | Python vs the Perl golden files. See [../parity/](../parity/README.md) |

Manual checks done by a person go in [../manual-qa/](../manual-qa/README.md), not here.
