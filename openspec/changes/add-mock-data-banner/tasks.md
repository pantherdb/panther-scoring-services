# Tasks

Test-first: each group writes its tests from the spec scenarios, runs them and sees them fail for the right reason, records the red run in the Notes, then implements.

## 1. The Flag and the Banner

- [x] 1.1 Extend `tests/layout/AppLayout.test.tsx` (Home page on mocks, Not a build detail, Against the real API): with `VITE_API_MOCKING` stubbed `on`, the shell shows a region named "Mock data" whose text says mock data and the scoring service, with no build details, and the page body is still in `main`; with it `off`, there is no such region. Add `tests/app/mocking.test.ts` for `isApiMocked()` (`on` is true; `off` and unset are false). In `tests/app/router.test.tsx`, the not-found page shows the region with the flag on. Run them and verify the "on" tests fail because there's no region and the module doesn't exist, while the "off" tests and the existing tests pass. Record the red run in the Notes.
- [x] 1.2 Add `src/app/mocking.ts`, make `src/main.tsx` use it, add `src/layout/MockDataBanner.tsx` and show it from `AppLayout`, as design.md describes. Verify the tests from 1.1 and every other Vitest test pass with no warnings, and `npm run format:check`, `npm run lint` and `npm run type-check` pass.

## 2. In the Browser

- [x] 2.1 Write `e2e/mock-data.spec.ts`: a `@mock` test that `/`, `/csnp`, a succeeded cSNP job's page and `/does-not-exist` each show the region, with no build details and no sideways scroll, and that the region is still in the viewport at the end of the job's page (Form, job and not-found pages on mocks; Scrolled to the end; Mobile width); and an `@api` test that `/`, `/csnp` and `/does-not-exist` show no region (Against the real API). Check port 4173 is free, run `npm run test:e2e` and verify the `@mock` test fails on desktop and mobile because there's no region. Record the red run in the Notes.
- [x] 2.2 After group 1, verify `npm run test:e2e` passes on both projects. Then, with an API image built from this branch running on port 8001, `API_PROXY_TARGET=http://localhost:8001 npm run test:e2e:api` passes on both projects, including the new `@api` test.

## 3. The Production Build

- [x] 3.1 Run `npm run build`, then search `dist/` for the banner's text, `msw` and `mockServiceWorker`. Verify it finds `dist/mockServiceWorker.js` (the red run) and nothing else, and record it in the Notes.
- [x] 3.2 Add the plugin to `vite.config.ts` that removes the worker script from builds without mocking, as design.md describes. Verify the search from 3.1 finds nothing after `npm run build`, that `npm run build:e2e` still writes `dist/mockServiceWorker.js` and its bundle has the banner's text, and that `npm run test:e2e` still passes.

## 4. Docs and Final Check

- [x] 4.1 Update `docs/testing/frontend.md` ("Mocking in the Dev Server": the banner, where the flag is read, and that the production build leaves the worker script out) and `docs/manual-qa/02-csnp-form.md` (the banner beside the mock results in TC 2.3, and its absence against the real API in TC 2.4). Verify every command they name runs as written from `frontend/`.
- [x] 4.2 Final check: in `frontend/`, `npm run api:types:check`, `format:check`, `lint`, `type-check`, `npm test`, `npm run build` (then the search of `dist/`), `npm run test:e2e`, and the api-mode run from 2.2; from the root, `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass, and this change is valid with `--strict`.

## Workflow follow-up

- **Review:** the frontend developer approves the code, the banner's wording, its colours and its role, and the `scoring-ui` delta. The engine developer, who asked for it on #20, checks that a screenshot from mock mode can't pass for a real result.
- **After the implementation merges,** archive with `/opsx:archive`. `split-substitutions-on-commas` changes another `scoring-ui` requirement; either can be archived first. Both deltas were archived together in a scratch copy of `openspec/` (2026-10-29), in both orders' worth: this one adds 2 requirements, the other renames and modifies 1, with no conflict.

## Notes

### Next action

Every task is done (2026-10-29). Next: the pull request and its review, together with `split-substitutions-on-commas` in one commit.

### Blockers

None.

### Failed approaches

- **Shell heredocs to write the test files (2026-10-29).** The worktree's command guard refused a heredoc that wrote two files as too complex to verify. They were written with the file tools.
- **A `scrollTo` at the default viewport size (2.1, 2026-10-29).** The first draft scrolled to the end of the job's page and checked the banner was in view. The succeeded cSNP page fits both projects' screens (Desktop Chrome 1280×720, Pixel 7), so nothing scrolled and the check passed with the banner not sticky. The test now shortens the window to 400 px high, checks it scrolled more than 200 px, then checks the banner. With `sticky top-0` removed (a mutant), it failed on both projects with "viewport ratio 0"; restored, it passes.
- **Screenshots from a stale `dist/` (2026-10-29).** `test:e2e:api` runs `npm run build`, so a `vite preview` afterwards served the production build, with no mocks: the job never appeared. Rebuild with `npm run build:e2e` before previewing mock mode by hand.

### Lessons learned

- **The Vitest red run (1.1).** `tests/app/mocking.test.ts` failed to resolve `@/app/mocking`; in `AppLayout.test.tsx` and `router.test.tsx`, the two "on" tests failed with "Unable to find an accessible element with the role "region" and name `/mock data/i`". The 10 other tests in those files passed, including the four "off" tests, which pass before and after, as guards should. Green after 1.2: 168 tests in 14 files, no warnings.
- **The e2e red run (2.1).** With the shell from `HEAD` put back for the run (`git show HEAD:frontend/src/layout/AppLayout.tsx`), "marks every page as mock data" failed on desktop and mobile at the first page, `/`: `getByRole('region', { name: /mock data/i })`, element not found. Restored, `npm run test:e2e`: 20 passed (18 before).
- **The `dist/` red run (3.1).** Before the plugin, `npm run build` then `grep -rli -e "Mock data" -e "comes from the scoring service" -e msw -e mockServiceWorker -e setupWorker dist` found only `dist/mockServiceWorker.js`. The bundle already had no banner text: Rollup folds `isApiMocked()` to `false` once Vite has replaced `import.meta.env.VITE_API_MOCKING`, and drops the banner. After 3.2, the same search finds nothing. `npm run build:e2e` still writes the worker script, its bundle contains the banner's text, and MSW is in its own `browser-*.js` chunk.
- **api mode (2.2).** `docker buildx build --target api --load -t panther-api:mock-banner .` from this worktree, run on port 8001 (`/api/v1/health` answered `ok`). `API_PROXY_TARGET=http://localhost:8001 npm run test:e2e:api`: 24 passed (22 before, plus the `@api` banner test on both projects). The container was stopped afterwards.
- **Screenshots (2026-10-29).** Of the mock build's succeeded cSNP job, on Desktop Chrome and Pixel 7: the banner is one line on desktop and two on the phone, dark above the blue header, with nothing cut off. White on `ink` is about 17:1.
- **Final check (4.2, 2026-10-29).** In `frontend/`: `api:types:check`, `format:check`, `lint`, `type-check`, `npm test` (185 tests in 14 files, with `split-substitutions-on-commas`), `build` and the `dist/` search (nothing found), `test:e2e` (20 passed) and `test:e2e:api` (24 passed). From the root: `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass, and this change is valid with `--strict`.
- **Not walked by a person:** TC 2.4's new first step (no banner against the real API). The `@api` e2e test checks it on `/`, `/csnp` and `/does-not-exist`.
