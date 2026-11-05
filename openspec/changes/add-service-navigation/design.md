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

Mantine's `Tabs` is ARIA's tablist, for switching panels on one page. These change the page, so they're router `Link`s in a `<nav aria-label="Services">`, with `aria-current` on the current one, which a screen reader announces.

- **Current tab:** `aria-current="page"` when the router matches the service's path, with `useMatch`, so `/csnp/` and `/CSNP` count. On `/jobs/:id`, the job's service gets `aria-current="true"`: current in the set, but its link leads to the form, not this page. The job is read from RTK Query's cache, with the same `useQueryState` that `useJob` uses, selecting only the service, so the header sends no request of its own and doesn't re-render on each poll. Until the job has loaded, no tab is marked.
- **Not on the root error page:** the tabs read the route and the job cache, so they may be what failed. `RootError` draws `AppHeader` with `tabs={false}`, as it leaves out the footer.
- **Focus ring inside the tab:** the strip scrolls sideways, which clips anything drawn outside it, so the outline is inset.
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

The labels per service sit in `JobNextSteps`; the paths come from `services.ts`.

### 5. The input is kept in the tab's session storage

On a successful submit, the form stores its values as typed under the job's id, in `sessionStorage`, before opening the job's page. The job's page offers "Edit and resubmit" only when an entry exists for its id and service.

- **Why session storage:** it survives a reload of the job's page, which an in-memory store doesn't, and is cleared when the tab closes. It's not strictly the tab's alone: "Duplicate tab" copies it into the new tab, and a browser's session restore may write it to disk. Enforcing more, such as a per-tab id kept in memory, isn't worth it for a convenience whose input never leaves the browser (review on #59).
- **Bounded:** at most 20 jobs' inputs, and none over 1,000,000 characters, such as a list of 100,000 IDs: writing it would hold up the page right after submitting. When the storage is full, the oldest inputs are dropped until the new one fits; one that never fits isn't kept, and that job just doesn't offer "Edit and resubmit".
- **Read defensively:** a missing, malformed or other-service entry reads as nothing. Storage that throws, as in some private modes, reads as nothing too.
- **One check for every box:** `keptInput` returns an input only when it has every box the form has now, from `src/app/formFields.ts`, which the forms' drafts use too. The job's page and the form make the same check, so the button never opens an empty form, as it could after a deploy adds or renames a box while a tab stays open.
- **To the form:** the link passes `{ editJob: <id> }` as router state, not in the URL, so the address stays `/csnp`. The form's reducer starts from the kept values when that state names a kept job, and from empty otherwise. The draft's `filledFromJob` says so, shown as a short note above the form; the example clears it. The page keys the form on the location, so following the service's tab remounts it empty.
- **Where it lives:** `src/features/jobs/keptInput.ts`, exported through the jobs feature's `index.ts`, which `csnp` and `refmap` already import from.

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
