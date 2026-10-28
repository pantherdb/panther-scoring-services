# Tasks

## 1. Project and Tooling

- [x] 1.1 Create `frontend/package.json` with the stack from `docs/design/frontend-stack.md` plus MSW, exact versions pinned, and the scripts `dev`, `dev:api`, `build`, `build:e2e`, `preview`, `type-check`, `lint`, `format`, `test`, `test:e2e`, `test:e2e:api`, `test:e2e:site`; verify `npm install` succeeds and writes `frontend/package-lock.json`
- [x] 1.2 Add `index.html`, `vite.config.ts` (React with the React Compiler, `@tailwindcss/vite`, `@/` alias, and a `/api` proxy to `API_PROXY_TARGET` for both `server` and `preview`) and the `tsconfig` files (strict, `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`, `@/` path); verify `npm run build` produces `dist/` from a minimal `main.tsx`
- [x] 1.3 Add `eslint.config.js` (configs and order from `frontend/CLAUDE.md`, plus `no-restricted-imports` for the plain `react-redux` hooks and `consistent-type-imports`) and `.prettierrc` with the Tailwind plugin; verify `npm run lint` and `npx prettier --check .` pass

## 2. Styling and Theme

- [x] 2.1 Spike: check whether Mantine 9 accepts CSS variables in `theme.colors`; record the result and the chosen colour source in the Notes below
- [x] 2.2 Write `src/index.css` (layer order, `@mantine/core/styles.layer.css`, Tailwind, `@theme` tokens) and `src/app/theme.ts`, with colours defined once as the spike decided; verify in the dev server that a Mantine `Button` and a Tailwind-styled `div` both pick up the primary colour
- [x] 2.3 If the spike made Mantine's theme the colour source, update the colour rule in `frontend/CLAUDE.md`; verify that file and `docs/design/frontend-stack.md` no longer contradict each other

## 3. Store, API and Mocks

- [x] 3.1 Add `src/app/api/api.ts` (`createApi` with no endpoints), `src/app/store.ts` (API reducer and middleware only) and `src/app/hooks.ts`; verify `npm run type-check` passes and `tests/app/store.test.ts` shows the store starts with the API slice and nothing else
- [x] 3.2 Run `npx msw init public`, then add `src/mocks/handlers.ts` (empty) and `src/mocks/browser.ts`, started from `main.tsx` only when `VITE_API_MOCKING` is `on`; verify `npm run dev` logs that MSW started, `npm run dev:api` doesn't, and `npm run build` output contains no worker start-up
- [x] 3.3 Point the RTK Query base URL at the relative `/api/v1`; verify with `npm run dev:api` and any server on `API_PROXY_TARGET` that a request to `/api/v1/` reaches it through the proxy

## 4. Shell and Routes

- [x] 4.1 Add `src/layout/AppLayout.tsx` (header with the title as a heading, `<Outlet />`), `src/features/home/` (`HomePage.tsx`, `index.ts`) and `src/components/NotFoundPage.tsx` (message and link to `/`, no build details)
- [x] 4.2 Add `src/app/router.tsx` (layout route, index route, `*` route) and wire providers in `src/main.tsx` (Redux, Mantine, Router); verify in the dev server that `/` and `/does-not-exist` render as the spec says

## 5. Unit and Component Tests

- [x] 5.1 Add `vitest.config.ts` (jsdom, collects only `tests/**/*.test.{ts,tsx}`) and `tests/setup.ts` (jest-dom, reduced-motion `matchMedia`, MSW node server with `onUnhandledRequest: 'error'`); verify a test file placed under `src/` is not collected
- [x] 5.2 Add `tests/utils/render.tsx` (store, Mantine, memory router) and `tests/layout/AppLayout.test.tsx` and `tests/app/router.test.tsx` covering the spec's title, home and not-found scenarios; verify `npm test` passes

## 6. End-to-End Tests

- [x] 6.1 Add `playwright.config.ts` (`desktop` and `mobile` projects, only `e2e/` collected, `baseURL` from `E2E_BASE_URL` with no `webServer` when it's set, otherwise a `webServer` that builds for the mode and runs `preview` on a fixed port) and install browsers with `npx playwright install`; verify `npx playwright test --list` shows both projects
- [x] 6.2 Wire the three e2e scripts with the tag rules from the design (`@mock` only in mock mode, `@api` only in api and site modes, untagged everywhere), each printing its mode and target URL first; verify `--list` under each script shows the expected specs
- [x] 6.3 Add `e2e/shell.spec.ts` (untagged): title visible, unknown URL shows not-found, link returns home, no horizontal scroll on mobile, no port numbers or shell commands in the page text; verify it passes with `npm run test:e2e`, with `npm run test:e2e:api` (any server on `API_PROXY_TARGET`, or none, since the shell makes no API calls), and with `E2E_BASE_URL=http://localhost:4173 npm run test:e2e:site` against a separately started `npm run preview`

## 7. Docs and Final Check

- [x] 7.1 Write `docs/testing/frontend.md` (following `docs/testing/README.md`): install, each script, how to run a single Vitest test and a single Playwright spec, the three modes (mock, api, site) with their env vars and tags; update the e2e row in `docs/testing/README.md` to name the three modes; verify every command in `frontend.md` runs as written
- [x] 7.2 Remove `frontend/.gitkeep` if present, and add `node_modules/`, `dist/`, `test-results/`, `playwright-report/` to `.gitignore`; verify `git status` shows no build output
- [x] 7.3 Final check from a clean clone of the branch: `npm ci && npm run type-check && npm run lint && npm test && npm run test:e2e` all pass

## Workflow follow-up

- Open a PR with these artifacts; the frontend developer approves before apply.
- After the implementation merges, archive with `/opsx:archive` so `openspec/specs/scoring-ui/spec.md` is created.

## Notes

### Next action

All tasks are done. Commit, open a PR for the frontend developer's review, and archive with `/opsx:archive` after it merges.

7.3 ran on a copy of exactly the files git would commit (tracked plus untracked-but-not-ignored), because nothing was committed yet. Repeat it from a real clone once the branch is pushed.

### Blockers

None.

### Failed approaches

- **Inlining `react-router` in Vitest (2026-10-28).** Tried `test.server.deps.inline: ['react-router']`, then the regex `[/react-router/]`, to make `react-router/dom` share the app's copy of React Router in tests. Neither worked: the import still resolved to the CommonJS build, so nested routes rendered empty. Fixed instead by importing `RouterProvider` from `react-router` in `tests/utils/render.tsx`; see Lessons learned.

### Lessons learned

- **Colour source (2.1, 2026-10-28): Tailwind's `@theme`.** Mantine 9 accepts `var(--…)` colours: its `rgba` and `darken` helpers switch to `color-mix()` for them. `theme.ts` therefore lists each Mantine shade as `var(--color-<name>-<step>)`. One limit: Mantine's `luminance` returns `false` for `var()` colours, so `autoContrast` can't work out text colour on them.
- **Versions (1.1, 2026-10-28).** The latest releases are TypeScript 7, Vite 8, React Router 8 and ESLint 10, but the accepted stack names TypeScript 5, Vite 7, React Router 7 and ESLint 9, so the newest release of each of those majors is pinned. `@vitejs/plugin-react` 6 needs Vite 8, so it's 5.2.0. npm warns that ESLint 9 is end-of-life; moving to ESLint 10 needs a change to `docs/design/frontend-stack.md`.
- **esbuild install script (1.1).** npm's `allowScripts` skipped esbuild's postinstall. The build works anyway, because esbuild ships its binary as a platform package.
- **In tests, import `RouterProvider` from `react-router`, not `react-router/dom` (5.2).** Under Vitest, `react-router/dom` loads React Router's CommonJS build, whose contexts differ from the ESM build used by `Outlet` and `Link`. The layout then renders but `<Outlet />` stays empty, with no error. `main.tsx` keeps `react-router/dom`, which works in the browser. Worth adding to `frontend/CLAUDE.md` at archive.
- **MSW 3 renamed `onUnhandledRequest` to `onUnhandledFrame` (3.2, 5.1).** The behaviour is the same. `design.md` and task 5.1 use the old name.
- **Tailwind v4 emits only the theme variables its classes use** unless the block is `@theme static`. Mantine reads `--color-primary-*` directly, so the block must be static.
- **Playwright never reuses an existing server.** A preview left running on port 4173 could be a build for the other mode, so `reuseExistingServer` is always `false`, not only in CI as `design.md` says.
