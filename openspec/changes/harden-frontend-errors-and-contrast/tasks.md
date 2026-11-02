# Tasks

## 1. Render Errors (FE-1)

- [x] 1.1 Move the header to `src/layout/AppHeader.tsx`; add `src/components/ErrorPage.tsx` (fixed text, a link home, `console.warn` only under `import.meta.env.DEV`) and `src/layout/RootError.tsx` (banner when mocked, header, `ErrorPage`).
- [x] 1.2 In `src/app/router.tsx`, give the root route `errorElement: <RootError />` and each page route `errorElement: <ErrorPage />`.
- [x] 1.3 In `src/components/VersionList.tsx`, default a missing `tools` or `data` to an empty list.
- [x] 1.4 Add `tests/app/routeErrors.test.tsx`: the home page, header and footer when nothing throws; a page that throws shows the error page inside the shell with no details or developer screen; going home from it; the layout that throws keeps the header; the development-only log, and none outside development.
- [x] 1.5 In `tests/features/versions/AppVersions.test.tsx`, add a versions answer without `tools` or `data` on `/csnp`, and one without `tools` only, beside the existing success tests.
- [x] 1.6 In `e2e/versions.spec.ts`, add an untagged spec that answers `/api/v1/versions` without `tools` or `data` through `addInitScript`, and checks the footer, the header and the form, with no developer screen.

## 2. Contrast (FE-2)

- [x] 2.1 In `src/app/theme.ts`, export `cssVariablesResolver`, mapping `--mantine-color-error` to `var(--color-danger)` and `--mantine-color-dimmed` to `var(--color-ink-muted)`; pass it in `src/main.tsx` and `tests/utils/render.tsx`.
- [x] 2.2 Add `tests/app/theme.test.ts` for what the resolver returns.
- [x] 2.3 Add `e2e/contrast.spec.ts`: the sequence field's description, then its description and error after an empty submit, each at least 4.5:1 against the canvas.

## 3. Docs and Final Check

- [x] 3.1 `frontend/CLAUDE.md`: a line on error elements and one on the resolver. `docs/testing/frontend.md`: how to test a render error, and how to change an answer in mock-mode e2e. Check `docs/manual-qa/` for a step that changes (none expected: fields still turn red).
- [x] 3.2 Final check: in `frontend/`, `npm run api:types:check`, `format:check`, `lint`, `type-check`, `npm test -- --run` and `npm run test:e2e` pass; from the root, `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass, and this change is valid with `--strict`.

## Workflow follow-up

- **Review:** the frontend developer approves the code and the `scoring-ui` delta.
- **After the implementation merges,** archive with `/opsx:archive`.

## Notes

### Next action

Every task is done (2026-11-02). Next: the pull request and its review.

### Blockers

None.

### Failed approaches

- **`page.route` for the e2e versions answer (1.6, 2026-11-02).** Not tried in code: in mock mode MSW's service worker answers the request before Playwright's routing sees it, so the spec would pass or fail on the mock's own answer. `addInitScript` replacing `window.fetch` works in every mode.
- **A longer "keeps the shell" requirement (3.2, 2026-11-02).** It also named the development-only log, and went over 500 characters, which `--strict` fails as a warning. The log is in design.md and `frontend/CLAUDE.md` instead.
- **`typeof import('@/features/home')` in `vi.mock`'s `importOriginal` (1.4, 2026-11-02).** The lint's `consistent-type-imports` forbids `import()` type annotations. Use `import type * as Home from '@/features/home'` instead.

### Lessons learned

- **The contrast spec catches the regression (2.3, 2026-11-02).** With the resolver taken out of `src/main.tsx`, the spec failed at 3.32:1 for the description; with it, it passes.
- **React Router logs a caught render error with `console.error`** in every build, even with an `errorElement`, and React does too. The tests silence it; the screen shows nothing.
- **Final check (3.2, 2026-11-02).** In `frontend/`: `api:types:check`, `format:check`, `lint`, `type-check`, `npm test -- --run` (302 in 25 files) and `test:e2e` (32 passed). From the root: `markdownlint-cli2` and `openspec validate --all` pass, and this change is valid with `--strict`. `test:e2e:api` wasn't run.
