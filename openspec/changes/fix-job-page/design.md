# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **The frontend stack and its conventions:** [docs/design/frontend-stack.md](../../../docs/design/frontend-stack.md) (Accepted), and `frontend/CLAUDE.md`. These conventions apply most:
  - "Types come from the OpenAPI schema … Never hand-write a type the schema already has";
  - "One module converts between the API's shapes and the app's" (`wire.ts`);
  - "Poll job status with RTK Query's `pollingInterval`, and stop when the job finishes or fails";
  - "Effects must be idempotent";
  - "Don't read refs while rendering";
  - "The form page keys the form on `location.key`".
- **The findings:** FE-4, FE-5 and FE-6 in `docs/code-review/2026-11-22-whole-repo-review-0f39e33.md`.

The behaviour is in [specs/scoring-ui/spec.md](specs/scoring-ui/spec.md).

How the code stands today:

- **Converting a job:** `jobsApi.ts`'s `getJob` and `startJob` both turn the API's job into the app's `Job` with `fromWireJob`.
- **Showing and checking a job:** `JobPage` shows `useJob(id).data`. `useJob` stops polling once the cached job has finished, or its request has failed.
- **Opening a new job:** the forms' submit hooks and `StartToolsCheck` call `navigate` after `startJob(...).unwrap()`.

## Goals / Non-Goals

**Goals:**

- A job from a newer API is never checked forever, and never shown half-understood.
- A new service in the schema fails `type-check` in the frontend before it reaches a user.
- A job's page never shows another job's data or state.
- A submit never moves a user who has already gone elsewhere.

**Non-Goals:**

- Telling a user who left that their job started, or listing their recent jobs (#84).
- Cancelling the request, or the job, when the user leaves: the API has no cancel.
- FE-105, FE-108 and FE-8 (proposal, Open Questions).

## Decisions

### 1. A job the app doesn't know becomes `null`, and the page says it can't show it

`fromWireJob` returns `Job | null`. It returns `null` when:

- the `service` is none of the switch's cases (its `default`, unreachable by type, reachable at runtime);
- the `status` isn't one the app knows. The statuses are listed in a `Record<JobStatus, true>`, so a status added to the schema fails `type-check` until it's added to the list.

`getJob` becomes `build.query<Job | null, string>`. Then:

- **`useJob`** stops polling when the cached data is `null`, as it does for a finished job;
- **`JobPage`** shows `JobCantBeShown` for `null`. It has fixed text, saying the job may come from a newer version of the scoring service, and a button that reloads the page. It doesn't show the unknown value: the API's own text stays off the screen, as for a failed request.

`undefined` still means "not loaded yet", so loading and can't-show stay apart.

**Alternatives:**

- **Throwing in `transformResponse`:** RTK Query turns that into a failed request. The page would say the job couldn't be loaded and offer "Try again", which can never succeed.
- **An `unknown` member of `Job`:** every switch over `service` in the app would have to handle a pseudo-service.

### 2. Starting a job returns only its id

`startJob`'s `transformResponse` returns the wire job's `id`, and the mutation is typed `<string, JobRequest>`. All four callers need only the id, for `keepInput` and the job's address. So a `202` whose job has a status this build doesn't know still opens the job's page, and the page then applies decision 1.

**Alternative:** keep `fromWireJob` there. Its `null` would then need handling in four places that only want an id.

### 3. `WireJob` and `JobRequest` come from `paths`

- **`WireJob`** is the `200` response body of `GET /api/v1/jobs/{job_id}`;
- **`JobRequest`** is the request body of `POST /api/v1/jobs`.

Both come from `paths` in `schema.d.ts`, so both follow the API's unions. `fromWireJob`'s switch has a case per service with no fall-through, so a service added to the union fails `type-check` there until it has a case. `src/mocks/jobs.ts` imports `WireJob` from `wire.ts` instead of listing a third union. The app's own `Job`, one member per service with its result type, stays in `wire.ts`, tied to the wire type by that switch.

**Alternative:** keep the hand-listed unions and add a test comparing them with the schema. The type is the test, and it fails where the fix goes.

### 4. The job page is keyed by the job id

The route's element becomes a small `JobRoute` that reads `:id` and renders `<JobPage key={id} id={id} />`. A new id remounts the page. Everything starts again from "Loading the job…":

- `useGetJobQuery`'s last result;
- `useSlowPolling`'s timer;
- `MappingsTable`'s page;
- the "Edit and resubmit" link.

It's keyed by the id, not by `location.key`, so a link to the page already shown keeps it.

**Alternative:** read `currentData` instead of `data`. That fixes only the fetched job. The page's own state, such as the table's page and when slower checking starts, would still carry over from the previous job.

### 5. A hook opens a started job only from where it was started

A hook in `features/jobs`, used by the three submit hooks and `StartToolsCheck` in place of `navigate`:

- **Tracking where the page is:** an effect keeps the current `location.key` in a ref while the page is mounted, and sets it to `null` in its cleanup.
- **When a submit starts,** the handler reads the key.
- **When the `202` arrives,** it navigates to `/jobs/<id>` only if the ref still holds that key.

Why each part:

- **The cleanup matters.** Leaving a page unmounts it without rendering it again with the new location, so without the cleanup the ref would still hold the old key.
- **StrictMode is fine.** Under StrictMode the effect runs, cleans up and runs again, and ends with the key set.
- **Following the form's own tab counts as leaving.** It changes `location.key` and starts the form afresh (`frontend/CLAUDE.md`).
- **The input is still kept.** `keepInput` runs either way, so the job's input is kept for "Edit and resubmit".

**Alternatives:**

- **A mounted flag alone:** following the form's own tab keeps the component mounted, so the flag would still say yes, and the user would be moved to the job.
- **Aborting the request on unmount:** the API may already have accepted the job, and aborting the request doesn't stop it. The job's id would then be lost.

### 6. Tests drive the real router and the mocked API

- **Unknown values:** a job with an unknown `service` or `status` is served with `serveJob`, cast from a plain object. Each test sits beside a known job's.
- **A changed id:** `renderRoute` returns its memory router. The test calls `router.navigate('/jobs/<b>')`, with B's answer held back, and checks that A's heading and table are gone before B appears.
- **Leaving:**
  - an MSW handler holds the `POST` until the test releases it;
  - the user clicks a header tab;
  - the test releases the `202`, and checks the location.

  The leaving tests run under `StrictMode`, through a `strict` option on `renderRoute`, because the hook's effect is what StrictMode doubles.

## Risks / Trade-offs

- **[Regenerating the types fails once the API adds a service]** → That's intended. `add-treegrafter-job` adds the case, and the job page's result for it, in the same pull request as its types.
- **[A user who leaves never learns the job started]** → The job runs and expires as usual. Listing recent jobs is #84.
- **[Reloading doesn't help if the site is old because its host is behind]** → The text says the job may come from a newer version. It doesn't promise that reloading fixes it.

## Migration Plan

Frontend only. It deploys with the site, and rolls back by reverting it. No API, data or storage changes.
