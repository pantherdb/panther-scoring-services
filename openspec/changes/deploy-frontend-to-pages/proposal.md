# Proposal

**Area:** cross-cutting: `frontend/`, `api/` and `.github/`, with their docs. No engine code changes.

## Why

[hosting.md](../../../docs/design/hosting.md) proposes the frontend on GitHub Pages and the API on our server, at another origin (#33, #34). Issue #39 lists what the code needs for that. Today the frontend can only call `/api/v1` on its own origin, assumes it's served at `/`, has no fallback for a reload of a deep link on a static host, and has no deploy workflow; the API sends no CORS headers, so a browser would withhold every answer from a page on another origin.

The API's public hostname, and the Pages address, aren't decided yet (hosting.md, Open Questions). So every value the server decides is a setting with a placeholder: going live means setting values, never changing code.

## What Changes

- **The frontend:**
  - **The API's URL** comes from `VITE_API_BASE_URL` at build time, read in one place, `src/app/apiBaseUrl.ts`. Empty or unset keeps today's relative `/api/v1`, so dev, the dev proxy, the e2e modes and compose are unchanged. Set, every call goes to `<url>/api/v1`.
  - **The base path** comes from `BASE_PATH` at build time: `/` by default, `/panther-scoring-services/` for the Pages build. The router's `basename` is the same value, so links, the "Back to home" links and the not-found page work under it.
  - **A `404.html` fallback,** a copy of `index.html` in every build, so a reload of `/jobs/<id>` on Pages starts the app.
  - **A link to the API's interactive docs** in the footer, beside the versions, at `<API URL>/api/v1/docs`; hidden in mock mode.
  - **Mock mode is never deployed:** the production build keeps MSW off, a build with mocking on and an API URL set fails, and the deploy workflow refuses a build that contains MSW or the mock data banner.
- **The API:** `PANTHER_API_CORS_ORIGINS`, a comma-separated list of allowed origins, empty by default. Empty adds no CORS at all, as today. Set, Starlette's `CORSMiddleware` allows exactly those origins, `GET` and `POST`, the `Content-Type` header, and exposes `Location` and `Retry-After`; no wildcard and no credentials. It wraps the body limit, so a preflight is answered before the limit, and a `413` still carries the CORS headers.
- **The deploy workflow,** `.github/workflows/pages.yml`: on a push to `main` that touches `frontend/**` or the workflow, or by hand. It builds with `npm ci` and `npm run build`, `VITE_API_BASE_URL` from the repository variable `PANTHER_API_URL` and `BASE_PATH` from `PAGES_BASE_PATH` (default `/panther-scoring-services/`), and deploys with GitHub's official Pages actions. While `PANTHER_API_URL` is empty, it builds and deploys nothing, and says so in the run's summary, so it can merge before the server exists.
- **Docs:** a new `docs/deployment/runbook-pages.md`; updates to `docs/design/hosting.md`, `docs/testing/api.md`, `docs/testing/frontend.md`, `api/README.md`, `api/CLAUDE.md` and `frontend/CLAUDE.md`.

Not in this change:

- **The server:** its hostname, HTTPS front end and DNS (#34).
- **A custom domain for Pages.** `PAGES_BASE_PATH=/` covers one, but setting it up is a decision for later.
- **Changes to `ci.yml`.** The new workflow needs no paths filter there: it builds what CI's `frontend` job already checks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui`: new requirements: the API's address set at build time, a base path, deep links on a static host, the API docs link, and no mock mode in a deployed build.
- `api-service`: a new requirement, CORS for the allowed origins, with the body limit.

## Impact

- **Code:** frontend: `vite.config.ts`, `src/main.tsx`, `src/app/api/api.ts`, a new `src/app/apiBaseUrl.ts`, `src/layout/AppLayout.tsx` and a new `src/layout/ApiDocsLink.tsx`. API: `settings.py`, `main.py` and a new `cors.py`.
- **API contract:** none. CORS is headers only; `openapi.json` doesn't change.
- **Behaviour:** with the settings empty, the only visible difference is the footer's "API docs" link. With them set, the frontend calls the API on another origin.
- **Tests:** `frontend/tests/app/apiBaseUrl.test.ts`, `tests/app/router.test.tsx` (the base path), `tests/layout/ApiDocsLink.test.tsx`; `api/tests/test_cors.py` and `test_settings.py`.
- **Dependencies:** none. `CORSMiddleware` is part of Starlette.
- **Parity with the reference:** not affected. Nothing here changes what a job computes. No divergence row is needed.

## Open Questions

Each needs team verification:

- **The API's public URL,** for `PANTHER_API_URL`. Until it's set, the workflow deploys nothing.
- **The Pages address:** the project page `https://pantherdb.github.io/panther-scoring-services/`, the default, or a custom domain, which would set `PAGES_BASE_PATH=/` and change the origin for `PANTHER_API_CORS_ORIGINS`.
- **Who enables Pages** (Settings → Pages → Source: GitHub Actions). It needs a repository admin.
