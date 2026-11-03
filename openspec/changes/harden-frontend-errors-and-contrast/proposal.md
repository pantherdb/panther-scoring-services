# Proposal

**Area:** frontend. Outside `frontend/`, it edits `docs/testing/frontend.md`. It changes nothing in `api/` or `engine/`.

## Why

The whole-repository review at `64174c9` (`docs/code-review/2026-10-30-whole-repo-review-64174c9.md`) found two Medium problems in the frontend:

- **FE-1.** No route in `src/app/router.tsx` has an `errorElement`, so any exception while rendering falls through to React Router's default error screen. `react-router` 7.18.5 ships that screen in the production bundle: it shows "Unexpected Application Error!", the error, its stack with the bundle's URLs, and "Hey developer", with no header, form, footer or link. The review triggered it with `GET /api/v1/versions` answering 200 without `data`, as an older API could during a rollout: the footer's `versions.data.map` threw, and every page was replaced. That's against `scoring-ui`'s "No build details on screen".
- **FE-2.** Mantine colours a field's error with `--mantine-color-error` (red-6, about 3.15:1 on the canvas) and its description with `--mantine-color-dimmed` (gray-6, about 3.18:1). WCAG 2.1 AA (1.4.3) needs 4.5:1. The project's own `--color-danger` gives 4.56:1 and `--color-ink-muted` 7.24:1; `--color-danger` is defined in `src/index.css` and never used.

## What Changes

- **Every route gets an `errorElement`.** Each page route shows `ErrorPage` inside the layout, so the header and footer stay; the root route shows `RootError`, the header around the same `ErrorPage`, for when the layout itself throws. `ErrorPage` has fixed text and a link home. The error goes to `console.warn` only under `import.meta.env.DEV`, never on screen.
- **The header moves to `src/layout/AppHeader.tsx`,** shared by `AppLayout` and `RootError`.
- **`VersionList` tolerates a missing `tools` or `data` array,** showing what there is. It's shared by the footer and the job page.
- **Mantine's error and dimmed colours map to the project's tokens** through `MantineProvider`'s `cssVariablesResolver`: `--mantine-color-error` to `var(--color-danger)`, `--mantine-color-dimmed` to `var(--color-ink-muted)`. The resolver is defined once in `src/app/theme.ts` and passed by `src/main.tsx` and `tests/utils/render.tsx`.
- **Tests:** Vitest for a page that throws, the layout that throws, going home, the development-only log, a versions answer without `tools` or `data`, and the resolver; Playwright for the contrast of a field's description and error, and for a versions answer without `tools` or `data` in the built app.
- **Docs:** `frontend/CLAUDE.md` gets a line on error elements and one on the resolver; `docs/testing/frontend.md` says how to test a render error and how to change an answer in mock-mode e2e.

No new dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui`:
  - adds "A page that fails to render keeps the shell" and "Field text meets WCAG AA contrast";
  - "Versions on every page" requires the page to work when the answer leaves out the tools or the data, with a scenario for it.

## Impact

- **Frontend code:** `src/app/router.tsx`, `src/app/theme.ts`, `src/main.tsx`, `src/components/VersionList.tsx`, `src/layout/AppLayout.tsx`; new `src/components/ErrorPage.tsx`, `src/layout/AppHeader.tsx`, `src/layout/RootError.tsx`. Tests in `tests/app/`, `tests/features/versions/` and `e2e/`.
- **API contract:** unchanged. `npm run api:types:check` passes with the committed `schema.d.ts`. The schema still requires `tools` and `data`; the UI only stops failing when they're missing.
- **Parity:** none. No service's output changes, and no divergence row is needed.
- **Colours:** errors are a darker red, and descriptions a darker grey, than before. Fields still turn red on an error, so the manual QA checklists don't change.

## Open Questions

None. The Low frontend findings (FE-3 to FE-17) stay open; none is part of this fix.
