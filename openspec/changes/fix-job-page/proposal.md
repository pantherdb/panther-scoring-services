# Proposal

**Area:** frontend. Outside `frontend/`, it adds manual QA cases to `docs/manual-qa/`. It changes nothing in `api/` or `engine/`.

## Why

The code review at `0f39e33` (`docs/code-review/2026-11-22-whole-repo-review-0f39e33.md`, tracked in #89) found three problems with how the frontend opens and shows a job. All three were in the earlier review at `64174c9` too.

- **FE-4: a job the page doesn't know is checked every second, forever.**
  - `fromWireJob` (`src/app/api/wire.ts`) has a case for each service and no default. A `service` it doesn't know returns nothing, so the page says "Loading the job…" and keeps checking.
  - A `status` it doesn't know isn't finished either, so it's checked forever too, with an empty status badge.
  - This happens whenever the API is newer than the site, which separate deploys make likely. GitHub Pages and the server update apart, and `add-treegrafter-job` will add a service.
  - `WireJob` and `JobRequest` are hand-listed unions, so even regenerating the types doesn't flag a new service.
- **FE-5: going from one job's page to another's shows the first job under the second's address.**
  - `JobPage` reads `data` from `useGetJobQuery`, which keeps the previous job's result while the next one loads, and the route doesn't remount the page.
  - Going from `/jobs/A` to `/jobs/B` shows A's heading, status and result under `/jobs/B`, until B loads. The browser's history menu is one way to do it.
  - The page's own state stays from A too:
    - the results table's page;
    - when slower checking starts;
    - "Edit and resubmit", which points at A's input.
- **FE-6: leaving a form while its job is starting still moves the user to that job.** The three forms and the tools check each `await navigate('/jobs/<id>')` when the `202` arrives, wherever the user has gone since. A large refmap request takes long enough for the user to click elsewhere, and then be pulled back to the job.

## What Changes

- **A job the page can't show.**
  - When the API returns a job whose `service` or `status` this build doesn't know, the job page says it can't show the job, and suggests reloading the site to get the latest version. It stops checking the job.
  - Starting a job needs only the new job's id, so starting one never depends on knowing its shape.
- **Types from the schema.**
  - `WireJob` comes from `GET /api/v1/jobs/{job_id}`'s `200` response, and `JobRequest` from `POST /api/v1/jobs`' body, in the generated `schema.d.ts`, instead of hand-listed unions.
  - `fromWireJob`'s switch covers every member. So regenerating the types after the API adds a service fails `type-check` until the frontend handles it.
  - The mocks use the same type instead of a third copy.
- **One job per page.** The job page is remounted when the job id in the address changes. So it starts from "Loading the job…", with none of the previous job's result or state.
- **A started job opens only from where it was started.**
  - The three forms and the tools check open the new job's page only if the user is still where they submitted.
  - If they've gone elsewhere, they stay there. The job still runs, and a form's input is still kept for "Edit and resubmit".
- **Tests:**
  - an unknown service, and an unknown status, each beside a known one;
  - a change of id on a mounted job page;
  - leaving each form, and the home page, while a job starts, beside staying.
- **Manual QA:** a case in each form's checklist for leaving while a job starts.

No new dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui`:
  - adds "A job the page can't show";
  - "Job page at its own URL" gets a scenario for going from one job's page to another's;
  - "Submitting a cSNP request opens its job", "Submitting a refmap request opens its job", "Submitting an hmmscore request opens its job" and "Start a tools check from the home page" open the job only while the user is still on the page that started it, each with a scenario for leaving.

## Impact

- **Frontend code:**
  - `src/app/api/wire.ts`, `src/app/router.tsx`;
  - in `src/features/jobs/`: `jobsApi.ts`, `JobPage.tsx`, `useJob.ts` and `StartToolsCheck.tsx`, plus a new hook that opens a started job;
  - `useSubmitCsnp.ts`, `useSubmitRefmap.ts`, `useSubmitHmmscore.ts`;
  - `src/mocks/jobs.ts`.
- **Tests:** `tests/features/jobs/JobPage.test.tsx`, `StartToolsCheck.test.tsx`, and the three form pages' tests.
- **API contract:** unchanged. `npm run api:types:check` passes with the committed `schema.d.ts`.
- **Parity:** none. No service's output changes, and no divergence row is needed.
- **Later services:** once this is in, `add-treegrafter-job`'s regenerated types fail `type-check` until `fromWireJob` and the job page handle `treegrafter`. That's intended.

## Open Questions

None. These review findings stay out of this change:

- FE-105 (Back after "Edit and resubmit");
- FE-108 (polling compares two clocks);
- FE-8 (one failed check ends updates), which needs `scoring-ui` changed first.
