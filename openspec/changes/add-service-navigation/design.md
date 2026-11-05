# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **The frontend stack and its conventions:** [docs/design/frontend-stack.md](../../../docs/design/frontend-stack.md) (Accepted) and `frontend/CLAUDE.md`: Mantine for controls, Tailwind for layout, features that don't reach into each other's internals, and colours by their job.
- **The services and their order:** the priority table in the root `CLAUDE.md`.

What the code does today:

- `AppHeader` is a plain `<h1>`, shared by the layout and `RootError`.
- The home page has a section each for cSNP and refmap, then the tools check.
- `JobDetails` names the service and shows the status, result and versions, with no links. Only `JobNotFound` links home.
- Neither form keeps anything after a submit. The API never returns a job's input.

The behaviour is in [specs/scoring-ui/spec.md](specs/scoring-ui/spec.md).

## Goals / Non-Goals

**Goals:**

- One list of the services, read by the tabs, the home page and the coming-soon pages, so a service's name, page or mark changes in one place.
- Every page is one step from home and from each service.

**Non-Goals:**

- Forms for `hmmscore` and `treegrafter`. Their pages only say they're coming.
- A history of past jobs. "Edit and resubmit" covers the testing need; a list of jobs would need the API to keep them, and it keeps them in memory only.
- Keeping input across tabs or browser restarts.

## Decisions

### 1. One list of services, in `src/app/services.ts`

Each entry has an id, the tab's label, the page's title, a one-line summary, its path, and `comingSoon`. The order is the tabs' and the home page's.

It sits in `app/`, not a feature, because the layout, the home page and the router all read it.

`refmap` has a form and `comingSoon: true`. When #40 wires it, that becomes `false`, and nothing else changes.

### 2. The tabs are links, not Mantine `Tabs`

Mantine's `Tabs` is ARIA's tablist, for switching panels on one page. These change the page, so they're router `Link`s in a `<nav aria-label="Services">`, with `aria-current="page"` on the current one, which a screen reader announces.

- **Current tab:** the path is the service's path; or, on `/jobs/:id`, the job's service. The job is read from RTK Query's cache, with the same `useQueryState` that `useJob` uses, so the header sends no request of its own. Until the job has loaded, no tab is marked.
- **On a phone:** the list scrolls sideways inside the header (`overflow-x-auto`, no wrapping).
- **"Coming soon" in a tab:** a short visible "Soon", and an `aria-label` of the label followed by "(coming soon)", so the name starts with what the tab shows. Visually hidden text was tried first; see the Notes in tasks.md.
- **The current tab scrolls into view** when it's off the edge of a phone's screen.

The header is white on `primary-700`, like the title, so the text keeps its contrast. The current tab gets a white underline and a heavier weight, not a different colour.

### 3. "Coming soon" pages are routes

`/hmmscore` and `/treegrafter` each render one `ComingSoonPage`, which takes the service and reads its entry. Each route gets `errorElement: <ErrorPage />`, as every route must.

### 4. The job page's next step

`JobDetails` shows a row of links under the heading, whatever the status, so the user can start another job while one runs:

- "New cSNP search" or "New ID mapping", to the service's path, which opens an empty form;
- "Back to home" for the tools check;
- "Edit and resubmit", when the input is kept (decision 5).

The labels per service sit in `JobDetails` beside the existing `SERVICE_TITLES`.

### 5. The input is kept in the tab's session storage

On a successful submit, the form stores its values as typed under the job's id, in `sessionStorage`, before opening the job's page. The job's page offers "Edit and resubmit" only when an entry exists for its id and service.

- **Why session storage:** it survives a reload of the job's page, which an in-memory store doesn't. It belongs to one tab and is cleared when the tab closes, so the input isn't kept on the machine afterwards or shared with other tabs.
- **Bounded:** at most 20 jobs' inputs. The oldest is dropped when a new one is stored. A `refmap` list can be about 13 MB, more than session storage holds, so a failed write is ignored: that job just doesn't offer "Edit and resubmit".
- **Read defensively:** a missing, malformed or other-service entry reads as nothing. Storage that throws, as in some private modes, reads as nothing too.
- **To the form:** the link passes `{ editJob: <id> }` as router state, not in the URL, so the address stays `/csnp`. The form's reducer starts from the kept values when that state names a kept job, and from empty otherwise. A short note above the form says it was filled in from the earlier job.
- **Where it lives:** `src/features/jobs/keptInput.ts`, exported through the jobs feature's `index.ts`, which `csnp` and `refmap` already import from. It stores plain strings; each form checks the keys it needs.

Alternatives:

- **The input in the URL.** A cSNP sequence can be 50,000 residues, and a URL would carry it into logs and history.
- **Redux.** A reload of the job's page would lose it.
- **The API returning the input.** A contract change, and the job would hold user data longer; not worth it for this.

### 6. The API docs link

`target="_blank"` with `rel="noopener noreferrer"`, an external-link icon hidden from screen readers, and the `aria-label` "API docs (opens in a new tab)", as for the tabs.

## Risks / Trade-offs

- **[The kept input outlives the job]** → an expired job's page shows "not found", which has no "Edit and resubmit", so kept input for an expired job is never offered. It's dropped when the tab closes or after 20 newer jobs.
- **[Header tabs crowd a phone]** → they scroll inside the header, and `e2e/shell.spec.ts` checks the page doesn't scroll sideways.
- **[A service's mark goes stale]** → it's one value in `services.ts`; the proposal's open question asks who flips `refmap`'s.
