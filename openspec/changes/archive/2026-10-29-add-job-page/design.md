# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **Scoring runs as a job,** started with `POST /api/v1/jobs` and polled with `GET /api/v1/jobs/{id}`: [docs/design/tech-stack.md](../../../docs/design/tech-stack.md), API recommendation 1.
- **The frontend stack, RTK Query for every call, types from the schema, a job's results at their own URL:** [docs/design/frontend-stack.md](../../../docs/design/frontend-stack.md), Decision and Rules That Come With It.
- **How the frontend is organised:** [frontend/CLAUDE.md](../../../frontend/CLAUDE.md): one wire module renames the API's fields, polling with `pollingInterval` that stops when the job finishes, versions shown with results, no build details on screen, no clock read while rendering.
- **The job contract:** [add-scoring-jobs/specs/scoring-jobs/spec.md](../add-scoring-jobs/specs/scoring-jobs/spec.md) and its design ("The job is a union on `service`", "`GET /jobs/{job_id}` takes the id as a string"). A malformed id gets the same 404 as an expired one.
- **The versions list and the footer:** [add-api-types/design.md](../add-api-types/design.md), "Rendering".

What exists now:

- `src/app/api/api.ts` is the one RTK Query API (`baseUrl: '/api/v1'`). `features/versions/` injects `getVersions`.
- `schema.d.ts` already has `ToolsJobRequest`, `ToolsJob`, `ToolsResult`, `JobStatus` and `Problem`. The job is `ToolsJob` only; each service adds a member to the union.
- `features/versions/VersionList.tsx` renders a `Versions` value as a description list; only the footer uses it.
- `main.tsx` has no Mantine `Notifications` provider.

The behaviour is in [specs/scoring-ui/spec.md](specs/scoring-ui/spec.md).

## Goals / Non-Goals

**Goals:**

- A ported service joins by adding its request and job members to the wire module, its result view to the job page, and a form that calls `startJob`. Polling, the page's states and the route don't change.
- Each of the page's states can be reached from a test by changing only what the API answers.

**Non-Goals:**

- Progress inside a running job. The API reports none.
- Cancelling a job. The API has no endpoint for it.
- Formatting timestamps for display. The page shows how long the job ran, not when.

## Decisions

### Layout

```text
frontend/src/
  app/api/wire.ts              the wire module: the API's job -> the app's Job
  app/router.tsx               + jobs/:id
  components/VersionList.tsx   moved from features/versions/
  features/jobs/
    jobsApi.ts                 startJob, getJob; isFinished
    useJob.ts                  the query with its polling rule
    JobPage.tsx                reads :id, picks the state to show; not found, unavailable, loading
    JobDetails.tsx             a job: heading, status, outcome, versions
    JobStatus.tsx              the status, live, and how long the job ran
    JobResult.tsx              a succeeded job's result, by service
    ToolsResult.tsx            the tools result table
    StartToolsCheck.tsx        the home page action
    index.ts                   exports JobPage, StartToolsCheck
  features/home/HomePage.tsx   + <StartToolsCheck />
  mocks/data/jobs.ts           mocked job bodies
  mocks/jobs.ts                the mocked job store: create, poll, reset
  mocks/handlers.ts            + POST /api/v1/jobs, GET /api/v1/jobs/:id
frontend/tests/
  app/api/wire.test.ts
  features/jobs/JobPage.test.tsx, StartToolsCheck.test.tsx
frontend/e2e/jobs.spec.ts
```

### The wire module

`src/app/api/wire.ts` is the only module that knows the API's field names.

- **Wire types are aliases of the schema:** `WireJob = components['schemas']['ToolsJob']`, `JobRequest = components['schemas']['ToolsJobRequest']`. When a service adds a member, `WireJob` becomes a union; `Job` then becomes a union on `service` too, and `tsc` fails until `fromWireJob` produces it.
- **The app's `Job`** has `id`, `service`, `status`, `createdAt`, `startedAt`, `finishedAt`, `result`, `error` and `versions`. `result`, `error` and `versions` keep the schema's types: their fields (`name`, `version`, `detail`, …) have nothing to rename.
- **Timestamps become epoch milliseconds** (`number`, or `null` until reached), parsed with `Date.parse`.
  - *Why not `Date`:* RTK Query keeps the transformed response in the Redux store, and Redux Toolkit's serializability check warns on a `Date`.
  - *Why not the ISO string:* every reader would parse it again. A number subtracts directly, and the page's run time is `finishedAt - startedAt`, with no clock read while rendering.
- **The request needs no conversion.** `{service, input}` has nothing to rename, so `JobRequest` is the schema's type.
- **It converts in one direction for now.** Nothing the app sends has a field to rename. When a service's input does, its conversion goes here too.
- *Alternative:* convert in each endpoint's `transformResponse`. Rejected: frontend/CLAUDE.md asks for one module, so a renamed field is found in one place.

### Endpoints

`features/jobs/jobsApi.ts` injects into the one API:

- **`startJob`:** a mutation, `POST jobs` with the request as its body, `transformResponse: fromWireJob`.
- **`getJob`:** a query by id, `GET jobs/{id}` with the id URI-encoded, `transformResponse: fromWireJob`.
- **The page's URL comes from the job's `id`, not from `Location`.** `Location` is the API's path (`/api/v1/jobs/{id}`), not the app's route, and RTK Query's mutation result is the body. Both carry the same id, which the mocks and the api-mode e2e check.
- *Alternative:* seed the `getJob` cache from the mutation's result, so the job page opens with no loading state. Not done: it saves one request of about 10 ms and adds a second path into the cache. Revisit if the loading state flickers visibly.

### Polling

**`pollingInterval` is 1 second while the job is `queued` or `running`, and 0 otherwise.**

- **Why 1 second:** a `tools` job finishes within about 1.5 s against the image: the first after the API starts pays for a worker process, later ones run in about 0.3 s. At 1 s the user sees `queued` → `running` → `succeeded` as it happens, and the result appears at most 1 s late. A poll is a dictionary lookup in the API and a few hundred bytes, so one a second per open job page costs nothing. At 2 s or more, a 1.5 s check would feel slower than it is.
- **Scoring jobs will run for seconds to minutes.** A longer interval, or a backoff, may suit them better; the proposal lists it as an open question. The interval is one named constant in `jobsApi.ts`.
- **How it stops:** `useJob(id)` reads the cached entry with `getJob.useQueryState(id)` first, then subscribes with `useGetJobQuery(id, { pollingInterval })`, where the interval is 0 once the cached job has finished or the request has failed. `useQueryState` reads the cache without subscribing, so the interval is derived while rendering, with no effect and no state to keep in step.
  - *Alternative:* keep "stop polling" in component state and set it once the job finishes. Rejected: frontend/CLAUDE.md prefers deriving to storing, and the state would need resetting when `:id` changes.
  - *Alternative:* `skipPollingIfUnfocused`. Not used: a user who starts a check and switches tabs expects the result when they come back, and a poll a second is cheap.

### The job page's states

`JobPage` reads `:id` and shows one state, checked in this order:

| State | When | What the user sees |
| ----- | ---- | ------------------ |
| Not found | the query failed with 404 | heading "Job not found"; the job doesn't exist or has expired; a link home |
| Request failed | the query failed otherwise | heading "Job unavailable"; an alert that the job couldn't be loaded; a "Try again" button that refetches |
| Loading | no job yet (decided by the absence of data, not `isLoading`, which is false during a retry after an error) | a loader and "Loading the job…" |
| Queued or running | the job's status | the service's heading; the status in a live region; a loader and a line saying the page updates by itself |
| Succeeded | the job's status | the status; how long it ran; the result for its service; "Versions used" with the job's versions |
| Failed | the job's status | the status; an alert that the job failed, with the error's `detail`; the job's versions; no result |

- **The service's heading** comes from a map in the jobs feature (`tools` → "Scoring tools check"), so a new service adds a row.
- **Alerts and badges use the theme's primary colour.** The theme has no danger scale for Mantine, only the single `--color-danger` token, and frontend/CLAUDE.md asks for Mantine to be coloured through the theme. The alert's title says what went wrong. *(Decided during apply, 2026-10-29.)*
- **The status is a live region** (`role="status"`), so a screen reader hears it change. Tests read it by role.
- **The `tools` result is a table** named by its heading, with "Tool" and "Version" columns, in the order reported. A `null` version reads "not available", in italics, as in the footer.
- **Versions are shown with a finished job,** succeeded or failed, through the shared `VersionList`. The footer still shows what the service runs now; the job page shows what this job ran with.
- **No status code, error title or `type` is shown** for a failed request: only fixed text. A failed job's `detail` is shown, because the API guarantees it's generic (`scoring-jobs`, "A failing job reveals nothing internal").
- **The not-found text doesn't name the expiry time.** It's the API's setting, and could drift.

### A request that fails

- **Polling stops on any failed request,** and the page offers "Try again". A 404 can't recover. For a 500 or a network error, retrying by itself every second would flip the page between "loading" and "failed": RTK Query's `isError` is false while each retry is in flight, since the entry's status is then `pending`.
- **If a poll fails after the job was shown,** the page switches to the failure state, not the last status it saw, so it never shows a status it can't keep up to date.
- **"Try again" calls the query's `refetch`.** If the job is then still running, the interval is no longer 0, and polling resumes.

### Sharing the versions list

`VersionList` moves from `features/versions/` to `components/VersionList.tsx`, typed with the schema's `Versions`. The footer and the job page import it from there; neither imports the other feature. Its markup and tests don't change.

### The home page action

- **`StartToolsCheck`** lives in the jobs feature, which exports it from `index.ts`. The home page imports `@/features/jobs`, its public entry, not its internals.
- **It's secondary on purpose:** a `default`-variant button under a small heading ("Check the scoring tools"), after the page's main text, with one line saying it reports the version of each tool the services use. It's a placeholder until the service forms exist, then it goes or moves (proposal, Open Questions).
- **On click** it calls `startJob({service: 'tools', input: {}})`, unwraps the result and navigates to `/jobs/{id}`. While the request is in flight the button is disabled and shows a loader.
- **When starting fails,** an inline Mantine `Alert` under the button says the check couldn't be started, with fixed text. The button stays enabled, and a new click clears the alert.
  - *Alternative:* a Mantine notification. Not used: `main.tsx` has no `Notifications` provider, and adding one for a single message adds a portal the tests would need too. An inline alert stays next to the action it describes.

### The title

The header and `index.html`'s `<title>` read "PANTHER Scoring". The `AppLayout` test that asserted the old text is updated. The home page's own heading and text, about coding SNP scoring, stay until the service forms replace them.

### Mocks

- **`src/mocks/data/jobs.ts`** holds the bodies: a `tools` job builder for each status, the mocked tools result (the versions mock's tools), a failed job's error and the 404 problem. Like `versions.ts`, it has only type imports and relative imports, so the `@mock` e2e spec can import it.
- **`src/mocks/jobs.ts`** keeps the mocked jobs in a `Map` from id to poll count. `createJob()` makes a `queued` job with a random UUID. `pollJob(id)` returns the job's next state: `queued` on the first poll, `running` on the second, `succeeded` from the third on, or nothing for an unknown id. `resetJobs()` empties it.
- **The handlers:** `POST /api/v1/jobs` answers 202 with `Location` and the queued job, or 422 for a service other than `tools`. `GET /api/v1/jobs/:id` answers the next state, or 404 problem details for an unknown id. So, in mock mode, an unknown id shows "not found", as against the real API.
- **`tests/setup.ts` calls `resetJobs()` after each test,** beside `server.resetHandlers()`.
- **Tests override with `server.use`** for 404, 500, `failed`, a `null` tool version, and a slow or failing `POST`.

### Tests

- **Vitest, real timers.** The interval is 1 s, so a test that watches `queued` → `running` → `succeeded` takes about 2 s, with `waitFor` timeouts raised to 3 s. *(Decided during apply, 2026-10-29: real timers were fast enough, about 7 s for the whole job page file, so fake timers, which need care with MSW and user-event, weren't tried.)*
- **Counting requests:** a test that checks polling stops wraps the `GET` handler with a counter, waits for the finished state, waits longer than one interval, and checks the count didn't grow.
- **e2e:** a `@mock` spec runs the whole flow from the home page and checks each status and the mocked result, and that the job page doesn't scroll sideways. An untagged spec opens a malformed id, which every mode answers with 404. An `@api` spec starts a real check, waits for `succeeded`, compares the tools with `GET /api/v1/versions`, and reloads to check the result has its own URL. Starting a `tools` job is harmless on a shared deployment, so it's safe in site mode.

## Risks / Trade-offs

- **[One request a second per open job page]** Cheap for the in-memory store. With many users and long jobs it adds up; a backoff is the fix, and the interval is one constant.
- **[A transient failure ends the live view]** The user has to choose "Try again". Accepted for now (proposal, Open Questions): it's honest, and it can't flicker.
- **[Mock state lives in the page]** In mock mode the MSW handlers run in the page, so a reload forgets the mocked jobs and shows "not found". The reload check runs only in api mode.
- **[`WireJob` grows into a union]** `Job`'s `result` is typed for `tools` only, so a new service's result fails `tsc` in `fromWireJob` until `Job` becomes a union too, as intended.

## Migration Plan

Nothing to migrate. Rollback is reverting the pull request.
