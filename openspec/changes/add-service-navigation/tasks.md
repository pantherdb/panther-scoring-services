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

## Workflow follow-up

- **Review:** the frontend developer approves the code and the `scoring-ui` delta.
- **After the implementation merges,** archive with `/opsx:archive`.

## Notes

### Next action

Every task is done (2026-11-04). Next: the pull request and its review.

### Blockers

None.

### Failed approaches

- **Visually hidden text for "(coming soon)" in a tab (1.2, 2026-11-04).** A `sr-only` span after the label gave the accessible name "ID mapping(coming soon)", with no space, in Testing Library's name computation; a leading space in the span didn't survive it either. An `aria-label` that starts with the visible label is used instead, for the tabs and the API docs link.

### Lessons learned

- **The kept-input tests caught an unguarded read (3.2, 2026-11-04):** `getItem` was outside the `try`, so storage that throws on read would have broken the job's page. Both reading and writing are now inside it.
- **`useQueryState(skipToken)`** reads nothing and sends nothing, so the header can ask for the shown job's service on every page.
- **Final check (5.3, 2026-11-04).** In `frontend/`: `api:types:check`, `format:check`, `lint`, `type-check`, `npm test -- --run` (353 in 30 files) and `test:e2e` (40 passed, desktop and mobile). From the root: `markdownlint-cli2` and `openspec validate --all` pass (one existing length warning in a main spec, not this change), and this change is valid with `--strict`. `test:e2e:api` wasn't run.
