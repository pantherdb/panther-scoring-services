# Proposal

**Area:** frontend. Outside `frontend/`, it adds one manual QA checklist in `docs/manual-qa/` and edits `docs/testing/frontend.md`. It consumes the jobs contract from `add-scoring-jobs` and changes nothing in `api/` or `engine/`.

## Why

The API now runs jobs (`POST /api/v1/jobs`, `GET /api/v1/jobs/{id}`), and `frontend/src/app/api/schema.d.ts` already has their types, but the frontend can't start or show one. Every scoring service will hand its results to the user through a job, so the job page, its polling and the module that converts the API's job into the app's shape are needed before the first service form. The built-in `tools` job lets us build and test all of that now, against the real API, with no scoring logic, and gives the engine developer a way to try the whole path in a browser.

## What Changes

- **The wire module** in `src/app/api/`: converts the API's job (snake_case, ISO timestamps) into the app's shape. It's the only place that renames the API's fields. Its types come from the generated schema.
- **A `jobs` feature:** a `startJob` mutation and a `getJob` query, injected into the one RTK Query API. The query polls while the job is `queued` or `running`, and stops when it has `succeeded` or `failed`, or the job isn't found.
- **A job page at `/jobs/:id`,** so a reload or a shared link shows the same job. It has a loading state; a not-found state for an unknown, malformed or expired id, with a link home; a generic error state with no build details; the status while the job is `queued` or `running`, updating as it moves; the result for a `succeeded` job, shown with the versions the job ran with; and the error's `detail` for a `failed` job.
- **The `tools` result** is the tool list, with a `null` version shown as not available.
- **The versions list moves to `src/components/`,** so the footer and the job page share it without one feature importing the other's internals.
- **A "Check the scoring tools" action on the home page:** it starts a `tools` job and opens its page. It's disabled while the request is in flight, says so when starting fails, and is visibly secondary: a placeholder until the service forms exist.
- **The app title** becomes "PANTHER Scoring", in the header and the browser tab, since the app covers four services.
- **MSW handlers** for both endpoints. The mocked job moves through `queued`, `running` and `succeeded` on successive polls, with its state kept per job and reset between tests.
- **Tests, written first:** Vitest + React Testing Library with MSW for the wire module, the job page's states, polling that stops, and the home action; Playwright in mock mode on desktop and mobile, and in api mode against the real API.
- **Docs:** a manual QA checklist for the tools check in `docs/manual-qa/`, and `docs/testing/frontend.md` where running the tests changed.

No new dependency.

Not in this change:

- **Any service's form or results.** Each adds its own result view to the job page when its job type exists.
- **Notifications for finished jobs, or a list of past jobs.** The API has no way to list jobs, by design.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui` gains requirements for the job page (its URL, status updates, a succeeded job's result with its versions, a failed job, a job that isn't found, a request that fails) and for starting a tools check from the home page. The title change needs no spec change: the "App shell with title" requirement doesn't fix the text.

## Impact

- **Frontend code:** `src/app/api/` (the wire module), `src/app/router.tsx` (the route), `src/features/jobs/` (new), `src/features/home/HomePage.tsx`, `src/features/versions/` (uses the moved list), `src/components/VersionList.tsx` (moved), `src/layout/AppLayout.tsx` and `index.html` (the title), `src/mocks/`; tests in `tests/` and `e2e/`.
- **API contract:** consumed, not changed. `npm run api:types:check` still passes with the committed `schema.d.ts`.
- **Parity with each service's reference:** not affected. The `tools` job does no scoring, and the page shows what the API returns. No divergence is needed.

## Open Questions

Each needs team verification.

- **The polling interval** is 1 second (design.md, "Polling"). That suits the `tools` job, which finishes in about 1.5 seconds. Scoring jobs that run for minutes may want a longer interval or a backoff; revisit with the first ported service.
- **What a page shows while a poll fails mid-job.** This change stops polling and offers a retry, rather than retrying by itself (design.md, "A request that fails"). The API and frontend developers confirm that's acceptable until jobs run for minutes.
- **The home page's tools check is a placeholder.** It goes, or moves to an About or status page, when the first service form arrives. The team decides where it ends up.
- **How long a finished job is kept** is the API's setting (24 hours by default). The not-found page says a job may have expired, without naming a time, so it can't drift from the API's setting.
