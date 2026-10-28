# Tasks

## 1. Project and Tooling

- [ ] 1.1 Create `frontend/package.json` with the stack from `docs/design/frontend-stack.md` plus MSW, exact versions pinned, and the scripts `dev`, `dev:api`, `build`, `build:e2e`, `preview`, `type-check`, `lint`, `format`, `test`, `test:e2e`, `test:e2e:api`, `test:e2e:site`; verify `npm install` succeeds and writes `frontend/package-lock.json`
- [ ] 1.2 Add `index.html`, `vite.config.ts` (React with the React Compiler, `@tailwindcss/vite`, `@/` alias, and a `/api` proxy to `API_PROXY_TARGET` for both `server` and `preview`) and the `tsconfig` files (strict, `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`, `@/` path); verify `npm run build` produces `dist/` from a minimal `main.tsx`
- [ ] 1.3 Add `eslint.config.js` (configs and order from `frontend/CLAUDE.md`, plus `no-restricted-imports` for the plain `react-redux` hooks and `consistent-type-imports`) and `.prettierrc` with the Tailwind plugin; verify `npm run lint` and `npx prettier --check .` pass

## 2. Styling and Theme

- [ ] 2.1 Spike: check whether Mantine 9 accepts CSS variables in `theme.colors`; record the result and the chosen colour source in the Notes below
- [ ] 2.2 Write `src/index.css` (layer order, `@mantine/core/styles.layer.css`, Tailwind, `@theme` tokens) and `src/app/theme.ts`, with colours defined once as the spike decided; verify in the dev server that a Mantine `Button` and a Tailwind-styled `div` both pick up the primary colour
- [ ] 2.3 If the spike made Mantine's theme the colour source, update the colour rule in `frontend/CLAUDE.md`; verify that file and `docs/design/frontend-stack.md` no longer contradict each other

## 3. Store, API and Mocks

- [ ] 3.1 Add `src/app/api/api.ts` (`createApi` with no endpoints), `src/app/store.ts` (API reducer and middleware only) and `src/app/hooks.ts`; verify `npm run type-check` passes and `tests/app/store.test.ts` shows the store starts with the API slice and nothing else
- [ ] 3.2 Run `npx msw init public`, then add `src/mocks/handlers.ts` (empty) and `src/mocks/browser.ts`, started from `main.tsx` only when `VITE_API_MOCKING` is `on`; verify `npm run dev` logs that MSW started, `npm run dev:api` doesn't, and `npm run build` output contains no worker start-up
- [ ] 3.3 Point the RTK Query base URL at the relative `/api/v1`; verify with `npm run dev:api` and any server on `API_PROXY_TARGET` that a request to `/api/v1/` reaches it through the proxy

## 4. Shell and Routes

- [ ] 4.1 Add `src/layout/AppLayout.tsx` (header with the title as a heading, `<Outlet />`), `src/features/home/` (`HomePage.tsx`, `index.ts`) and `src/components/NotFoundPage.tsx` (message and link to `/`, no build details)
- [ ] 4.2 Add `src/app/router.tsx` (layout route, index route, `*` route) and wire providers in `src/main.tsx` (Redux, Mantine, Router); verify in the dev server that `/` and `/does-not-exist` render as the spec says

## 5. Unit and Component Tests

- [ ] 5.1 Add `vitest.config.ts` (jsdom, collects only `tests/**/*.test.{ts,tsx}`) and `tests/setup.ts` (jest-dom, reduced-motion `matchMedia`, MSW node server with `onUnhandledRequest: 'error'`); verify a test file placed under `src/` is not collected
- [ ] 5.2 Add `tests/utils/render.tsx` (store, Mantine, memory router) and `tests/layout/AppLayout.test.tsx` and `tests/app/router.test.tsx` covering the spec's title, home and not-found scenarios; verify `npm test` passes

## 6. End-to-End Tests

- [ ] 6.1 Add `playwright.config.ts` (`desktop` and `mobile` projects, only `e2e/` collected, `baseURL` from `E2E_BASE_URL` with no `webServer` when it's set, otherwise a `webServer` that builds for the mode and runs `preview` on a fixed port) and install browsers with `npx playwright install`; verify `npx playwright test --list` shows both projects
- [ ] 6.2 Wire the three e2e scripts with the tag rules from the design (`@mock` only in mock mode, `@api` only in api and site modes, untagged everywhere), each printing its mode and target URL first; verify `--list` under each script shows the expected specs
- [ ] 6.3 Add `e2e/shell.spec.ts` (untagged): title visible, unknown URL shows not-found, link returns home, no horizontal scroll on mobile, no port numbers or shell commands in the page text; verify it passes with `npm run test:e2e`, with `npm run test:e2e:api` (any server on `API_PROXY_TARGET`, or none, since the shell makes no API calls), and with `E2E_BASE_URL=http://localhost:4173 npm run test:e2e:site` against a separately started `npm run preview`

## 7. Docs and Final Check

- [ ] 7.1 Write `docs/testing/frontend.md` (following `docs/testing/README.md`): install, each script, how to run a single Vitest test and a single Playwright spec, the three modes (mock, api, site) with their env vars and tags; update the e2e row in `docs/testing/README.md` to name the three modes; verify every command in `frontend.md` runs as written
- [ ] 7.2 Remove `frontend/.gitkeep` if present, and add `node_modules/`, `dist/`, `test-results/`, `playwright-report/` to `.gitignore`; verify `git status` shows no build output
- [ ] 7.3 Final check from a clean clone of the branch: `npm ci && npm run type-check && npm run lint && npm test && npm run test:e2e` all pass

## Workflow follow-up

- Open a PR with these artifacts; the frontend developer approves before apply.
- After the implementation merges, archive with `/opsx:archive` so `openspec/specs/scoring-ui/spec.md` is created.

## Notes

### Next action

Review the proposal, spec and design. Then run `/opsx:apply` and start at 1.1.

### Blockers

None.

### Failed approaches

None yet. Record each as: what was tried, why it failed, date.

### Lessons learned

None yet.
