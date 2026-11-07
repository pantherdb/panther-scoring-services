# Tasks

## 1. The Services and the Header

- [x] 1.1 Add `src/app/services.ts`, the four services in priority order with their label, title, summary, path and `comingSoon` (design decision 1). Verified by the header and home page tests below.
- [x] 1.2 Make the title in `src/layout/AppHeader.tsx` a router link home, and add the service tabs under it (decision 2), with the job's service read from the cache through a hook the jobs feature exports. Add `tests/layout/AppHeader.test.tsx`: the title's link, the four tabs in order, the current tab on a form, on a job's page and on home (none), and the coming-soon names.
- [x] 1.3 Add `src/components/ComingSoonPage.tsx` and the `/hmmscore` and `/treegrafter` routes, each with `errorElement: <ErrorPage />`. Test in `tests/components/ComingSoonPage.test.tsx`: each page's heading, summary, "coming soon" and link home.

## 2. The Home Page

- [x] 2.1 Show the four services as cards from the list, with their marks and form links, above the tools check. Update `tests/features/home/HomePage.test.tsx`: the four headings in order, the two form links, the three marks, and the tools check.

## 3. The Job Page

- [x] 3.1 Add the next-step links to `JobDetails` (decision 4). Test in `tests/features/jobs/JobPage.test.tsx`: "New cSNP search" for a `csnp` job while running and when finished, "New ID mapping" for `refmap`, "Back to home" for the tools check.
- [x] 3.2 Add `src/features/jobs/keptInput.ts` (decision 5). Add `tests/features/jobs/keptInput.test.ts`: stored and read back; another service's entry, a malformed entry and a missing one read as nothing; storage that throws on write or read; the 20-job cap drops the oldest.
- [x] 3.3 Keep the input on a successful submit in `useSubmitCsnp` and `useSubmitRefmap`, and start each form's draft from it when the router state names a kept job, with the note. Show "Edit and resubmit" on the job's page when the input is kept. Test in `CsnpPage.test.tsx` and `RefmapPage.test.tsx`: submit, follow "Edit and resubmit", the form is filled as typed and says so, and submitting starts a new job; a job page without kept input has no "Edit and resubmit"; and "New cSNP search" opens an empty form.

## 4. The API Docs Link

- [x] 4.1 Open "API docs" in a new tab (decision 6). Update `tests/layout/ApiDocsLink.test.tsx`: `target`, `rel`, and the accessible name.

## 5. End to End, Docs and Final Check

- [x] 5.1 `e2e/shell.spec.ts`: the title goes home from `/csnp`; the tabs open their pages and mark the current one; `/hmmscore` says coming soon; no sideways scroll on `/csnp`. `e2e/csnp.spec.ts` (mock mode): after a submit, "Edit and resubmit" opens the form filled in, and "New cSNP search" opens it empty.
- [x] 5.2 Docs: `frontend/CLAUDE.md`, a line on `src/app/services.ts` and one on the kept input; `docs/manual-qa/01-tools-check.md` TC 1.1 (the tabs and cards) and `02-csnp-form.md` TC 2.3 (the next step and "Edit and resubmit").
- [x] 5.3 Final check: in `frontend/`, `npm run api:types:check`, `format:check`, `lint`, `type-check`, `npm test -- --run` and `npm run test:e2e` pass; from the root, `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass, and this change is valid with `--strict`.

## 6. Review on #59

- [x] 6.1 Keep the note in step with the form: `filledFromJob` in both drafts, cleared by the example, and the page keys the form on the location so its tab remounts it (design.md, decision 5). Verify in `tests/features/{csnp,refmap}/draft.test.ts` and the page tests: the tab gives an empty form with no note, the example removes the note (spec, The tab or the example after editing)
- [x] 6.2 Leave the tabs out of the root error page (`AppHeader tabs={false}`, decision 2). Verify in `tests/layout/AppHeader.test.tsx` with a route whose element throws
- [x] 6.3 One check for the kept input: `keptInput` picks every box from `src/app/formFields.ts`, used by the button and the forms, replacing the four `startingDraft`/`keptValues` helpers (decision 5). Verify that an input missing a box offers no button (spec, An input kept before a box was added), and that extra boxes are ignored
- [x] 6.4 When the storage is full, drop the oldest inputs until the new one fits, keeping the order consistent; skip an input over 1,000,000 characters (decision 5). Verify in `tests/features/jobs/keptInput.test.ts`
- [x] 6.5 Tabs: `useMatch` per tab, `aria-current="true"` on a job's page, an inset focus ring, and `selectFromResult` for the shown job's service (decision 2). Verify `/csnp/` and `/CSNP`, and the job page's `true`, in `tests/layout/AppHeader.test.tsx`
- [x] 6.6 The home page's tools check gets an h2; `JobNextSteps` takes its paths from `services.ts`; one e2e helper, `e2e/layout.ts`, replaces the sideways-scroll copies; the spec and design say what session storage does and doesn't guarantee. Final check as in 5.3

## Workflow follow-up

- **Review:** the frontend developer approves the code and the `scoring-ui` delta.
- **After the implementation merges,** archive with `/opsx:archive`.

## Notes

### Next action

The pull request, #59, is in review. The engine developer's review (2026-11-05) is answered by section 6. Next: approval, then merge and archive. Don't open another pull request for this change.

### Blockers

None.

### Failed approaches

- **Visually hidden text for "(coming soon)" in a tab (1.2, 2026-11-04).** A `sr-only` span after the label gave the accessible name "ID mapping(coming soon)", with no space, in Testing Library's name computation; a leading space in the span didn't survive it either. An `aria-label` that starts with the visible label is used instead, for the tabs and the API docs link.

### Lessons learned

- **The kept-input tests caught an unguarded read (3.2, 2026-11-04):** `getItem` was outside the `try`, so storage that throws on read would have broken the job's page. Both reading and writing are now inside it.
- **`useQueryState(skipToken)`** reads nothing and sends nothing, so the header can ask for the shown job's service on every page.
- **Final check (5.3, 2026-11-04).** In `frontend/`: `api:types:check`, `format:check`, `lint`, `type-check`, `npm test -- --run` (353 in 30 files) and `test:e2e` (40 passed, desktop and mobile). From the root: `markdownlint-cli2` and `openspec validate --all` pass (one existing length warning in a main spec, not this change), and this change is valid with `--strict`. `test:e2e:api` wasn't run.
- **A form's reducer reads its starting state once, on mount.** Following a link to the page already shown changes the location but keeps the component, so anything derived from the location while rendering can disagree with the reducer's state. Keying the form on `location.key` remounts it; flags that describe the state belong in the state (review on #59).
- **`aria-current="page"` means the link leads to this page.** On a job's page, its service's tab is current in the set, `aria-current="true"`.
- **Final check, after the review (6.6, 2026-11-05).** In `frontend/`: `format:check`, `lint`, `type-check`, `npm test` (372 in 30 files) and `test:e2e` (40 passed, desktop and mobile). From the root: `markdownlint-cli2` and `openspec validate --all` pass, and this change is valid with `--strict`.
