# Proposal

**Area:** `frontend`. No API or engine changes.

## Why

Testing the site shows it's hard to move around in. A job's page has no way back to its form or to home. The "PANTHER Scoring" title isn't a link. Nothing shows the four services, or which of them work yet: `hmmscore` and `treegrafter` don't appear at all, and `refmap`'s form exists, but the API answers it with "not available yet". The footer's "API docs" link also replaces the page the user was on.

## What Changes

- **The title links home,** on every page.
- **Tabs for the four services,** under the title, in the project's priority order: cSNP scoring, ID mapping, HMM scoring and TreeGrafter. The current page's tab is marked, and so is the service of the job being shown. On a phone the tabs scroll sideways inside the header, never the page.
- **"Coming soon" marks** on every service the API can't score yet: `refmap`, `hmmscore` and `treegrafter`. `refmap`'s tab still opens its form. `hmmscore` and `treegrafter` get a page each (`/hmmscore`, `/treegrafter`) saying what the service will do, and that it's coming.
- **The home page shows all four services,** as cards with the same marks, above the scoring tools check.
- **A job's page offers the next step:** "New cSNP search" for a `csnp` job, "New ID mapping" for a `refmap` job, and "Back to home" for the tools check.
- **"Edit and resubmit":** a job submitted from this browser tab can reopen its form, filled in with the input as it was typed, to change and submit again as a new job. The API doesn't return a job's input, so the input is kept in the tab's session storage, for the last few jobs only. A job opened from a shared link, or in another tab, doesn't offer it.
- **"API docs" opens in a new tab,** and says so to a screen reader.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui`: new requirements for the title link, the service tabs, the "coming soon" marks and pages, the home page's services, a job page's next step, "Edit and resubmit", and the API docs link's new tab.

## Impact

- **Code:** frontend only.
  - `src/layout/` (header, the API docs link);
  - `src/features/home/`;
  - `src/features/jobs/` (job page, the kept input);
  - `src/features/csnp/` and `src/features/refmap/` (keep the input on submit, fill the form from it);
  - `src/app/router.tsx`;
  - a new list of the services, in one place.
- **API contract:** none. `openapi.json` doesn't change.
- **Tests:** unit tests for the header, home page, job page, the kept input and both forms; e2e specs for the tabs and "Edit and resubmit"; the manual QA checklists for the home page and the cSNP form.
- **Dependencies:** none. The icon comes from `@tabler/icons-react`, already installed.
- **Parity with the reference:** not affected. Nothing here changes what a job computes, and no divergence row is needed.

## Open Questions

- **When `refmap` loses its "coming soon" mark.** Once its wiring (#40) lands, its mark is one value in the services list. Who removes it, in that change or this one's follow-up, needs team verification.
