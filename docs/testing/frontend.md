# Frontend Tests

How to run the frontend's checks, unit and component tests, and end-to-end tests. Run every command from `frontend/`. The conventions for writing tests are in [frontend/CLAUDE.md](../../frontend/CLAUDE.md).

## Setup

Node `^22.22.2` or `>=24.15.0`.

```sh
npm ci                                 # install exactly what package-lock.json lists
npx playwright install chromium        # once per machine, for the e2e tests
```

## Before Claiming Anything Works

```sh
npm run type-check && npm run lint && npm test
npm run test:e2e
```

## Scripts

| Script | What it does |
| ------ | ------------ |
| `npm run dev` | Dev server on port 5173, with the API mocked by MSW |
| `npm run dev:api` | Dev server on port 5173, with `/api` sent to the real API (see [Modes](#modes)) |
| `npm run build` | Type-check, then a production build in `dist/`. MSW is not included |
| `npm run build:e2e` | A production build with MSW turned on, used by mock-mode e2e tests |
| `npm run preview` | Serves `dist/` on port 4173, with `/api` sent to the real API |
| `npm run type-check` | TypeScript over `src/`, `tests/`, `e2e/` and the config files |
| `npm run lint` | ESLint |
| `npm run format` / `format:check` | Prettier: rewrite files, or only report |
| `npm test` | Vitest, once |
| `npm run test:watch` | Vitest, re-running on change |
| `npm run test:e2e` | Playwright in mock mode |
| `npm run test:e2e:api` | Playwright in api mode |
| `npm run test:e2e:site` | Playwright in site mode |
| `npm run api:types` | Generates `src/app/api/schema.d.ts` from `../api/openapi.json` (see [API Types](#api-types)) |
| `npm run api:types:check` | Fails if `src/app/api/schema.d.ts` isn't what `api:types` would generate. Changes no file |

## API Types

The API's types are generated from the committed schema, `api/openapi.json`, with `openapi-typescript`. The API doesn't need to be running.

```sh
npm run api:types          # regenerate src/app/api/schema.d.ts
npm run api:types:check    # check it's current, as CI does
```

- **Run `api:types` whenever `api/openapi.json` changes,** including in the API's own pull request, and commit `schema.d.ts` with it. CI's `frontend` job runs on any change to `api/openapi.json`, and `api:types:check` fails it until the types are regenerated.
- **A renamed or removed field then fails `npm run type-check`** where the frontend uses it, instead of failing in the browser.
- **Never edit `schema.d.ts` by hand.** Name a schema type with an alias, such as `type Versions = components['schemas']['Versions']`.
- **Prettier and ESLint skip it.** The check compares the generator's exact output, so reformatting it would fail the check.

## Unit and Component Tests (Vitest)

Tests live in `tests/`, mirroring `src/`. Vitest collects only `tests/**/*.test.{ts,tsx}`; a test file under `src/` doesn't run.

- **No test data is needed.** API calls are answered by the MSW handlers in `src/mocks/handlers.ts`. A call with no handler fails the test.
- **To change a response in one test**, use `server.use(...)` from `tests/mocks/server.ts`. It's reset after each test.
- **MSW 3 renamed `onUnhandledRequest` to `onUnhandledFrame`.** The behaviour is the same, but examples written for MSW 2 won't type-check. `tests/setup.ts` uses `onUnhandledFrame: 'error'`.
- **To render a page**, use `renderRoute(path)` from `tests/utils/render.tsx`. It wraps the page in the same store, theme and routes as the app.

Run one file, or one test by name:

```sh
npx vitest run tests/app/router.test.tsx
npx vitest run -t "goes back home"
```

## End-to-End Tests (Playwright)

Specs live in `e2e/`. They run in two projects, `desktop` (Desktop Chrome) and `mobile` (Pixel 7).

Run one spec, one test by name, or one project:

```sh
npx playwright test e2e/shell.spec.ts
npx playwright test -g "not-found"
npx playwright test --project=mobile
```

After a run, `npx playwright show-report` opens the HTML report.

### Modes

The app always calls a relative `/api/v1`. The mode decides what answers it.

| Mode | Command | What runs | API calls go to |
| ---- | ------- | --------- | --------------- |
| mock | `npm run test:e2e` | `build:e2e`, then `preview` on port 4173 | MSW, in the browser |
| api | `npm run test:e2e:api` | `build`, then `preview` on port 4173 | The real API at `API_PROXY_TARGET` (default `http://localhost:8000`) |
| site | `npm run test:e2e:site` | Nothing is built or started | Whatever API the site at `E2E_BASE_URL` uses |

Each run prints its mode and target first, for example `[e2e] mode: api, target: http://localhost:4173`.

- **Port 4173 must be free** in mock and api modes. Playwright never reuses a running server, because it could be a build for the other mode.
- **Point the api mode at another API** by setting `API_PROXY_TARGET`. It also works for `npm run dev:api` and `npm run preview`.
- **Site mode needs `E2E_BASE_URL`** and fails without it.

Setting the variables, in bash and in PowerShell:

```sh
API_PROXY_TARGET=http://localhost:9000 npm run test:e2e:api
E2E_BASE_URL=https://staging.example.org npm run test:e2e:site
```

```powershell
$env:API_PROXY_TARGET = 'http://localhost:9000'; npm run test:e2e:api
$env:E2E_BASE_URL = 'https://staging.example.org'; npm run test:e2e:site
```

To check site mode locally, start `npm run preview` in one terminal, then run `E2E_BASE_URL=http://localhost:4173 npm run test:e2e:site` in another.

### Tags

Tags choose which specs run in which mode:

| Tag | Use it for | mock | api | site |
| --- | ---------- | ---- | --- | ---- |
| (none) | Specs that need nothing from the API | yes | yes | yes |
| `@mock` | Specs that rely on specific mock data | yes | no | no |
| `@api` | Specs that need a live API | no | yes | yes |

Tag a spec with `test('...', { tag: '@api' }, async ({ page }) => { ... })`.

- **Site mode can point at a shared deployment.** Before tagging a spec `@api`, check it's safe to run there: for example, that submitting jobs to that site is acceptable.

## Mocking in the Dev Server

`npm run dev` starts MSW and logs `[MSW] Mocking enabled.` in the browser console. To develop against a real API instead, run `npm run dev:api`. Which modes mock is set in the `.env.*` files in `frontend/` (`VITE_API_MOCKING=on` or `off`).
