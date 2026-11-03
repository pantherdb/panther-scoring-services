# Design

## Context

See proposal.md, Why. This change relies on these decisions, and doesn't change them:

- **[hosting.md](../../../docs/design/hosting.md):** the frontend on GitHub Pages, the API on our server at an HTTPS hostname, and what the frontend and API need for that.
- **[frontend-stack.md](../../../docs/design/frontend-stack.md):** Vite, React Router and RTK Query; mock mode with MSW, never in a production build.
- **`harden-api-for-hosting`:** the body limit, `limits.BodyLimit`, and the settings read once in the lifespan.

What the code does today:

- `src/app/api/api.ts` calls `fetchBaseQuery({ baseUrl: '/api/v1' })`. Vite's `base` is the default `/`, and `createBrowserRouter(routes)` has no `basename`.
- `vite.config.ts` reads `.env.*` with `loadEnv(mode, cwd, '')`, so it also sees variables without the `VITE_` prefix, such as `API_PROXY_TARGET`, which never reach the app.
- `create_app()` adds `BodyLimit` and no CORS. The settings are read in the lifespan, after the middleware stack is built.

## Goals / Non-Goals

**Goals:**

- Going live is setting values: two repository variables and one server setting.
- Every setting empty: dev, the dev proxy, the e2e modes and compose work as today.
- No mock mode, and no build details, in a deployed site.

**Non-Goals:**

- The server, its HTTPS front end and its hostname (#34).
- Runtime configuration of the frontend, such as a `config.json` fetched at startup. The API's URL is fixed per build.

## Decisions

1. **`VITE_API_BASE_URL`, read only in `src/app/apiBaseUrl.ts`.**
   - `apiBaseUrl()` returns `<url>/api/v1`, or `/api/v1` when the value is empty or unset. It trims spaces and trailing slashes, so `https://api.example.org/` works. It keeps a path, so an API behind a path on a shared hostname works too (hosting.md, Options for the HTTPS Front End).
   - It sits beside `isApiMocked()`, in the same style: one function, tested with `vi.stubEnv`.
   - `api.ts` passes it to `fetchBaseQuery`. The footer's API docs link uses it too.
   - The value is the origin, not the full `/api/v1` URL, so the API's version prefix stays in the code.
2. **`BASE_PATH`, without the `VITE_` prefix, read in `vite.config.ts`.**
   - It sets Vite's `base`, normalised to a slash at each end; empty is `/`. The app reads it back as `import.meta.env.BASE_URL`, which Vite always defines, so nothing else needs a new variable.
   - `main.tsx` passes `import.meta.env.BASE_URL` as `createBrowserRouter`'s `basename`. Every `Link` and `navigate()` in the app is relative to the route table, so they gain the base path with no change. The "Back to home" links point at `/panther-scoring-services/`.
   - MSW's worker is registered from `${BASE_URL}mockServiceWorker.js`, so a mocked build under a base path still works, though none is deployed.
   - *Alternative:* `VITE_BASE_PATH`. Rejected: the app has no use for it beyond `BASE_URL`, and like `API_PROXY_TARGET` it stays out of the bundle.
   - **In Git Bash,** a variable such as `BASE_PATH=/panther-scoring-services/` is rewritten into a Windows path unless `MSYS_NO_PATHCONV=1` is set. The testing doc says so. CI runs on Linux.
3. **`404.html` in every build,** a copy of `index.html`, written by a small plugin in `vite.config.ts` after the bundle.
   - GitHub Pages answers a path with no file, such as a reload of `/panther-scoring-services/jobs/<id>`, with the site's `404.html`, at status 404. As a copy of `index.html`, with absolute asset URLs under the base path, it starts the app, and the router shows the page for that URL.
   - Every build, not only the Pages build: it's harmless elsewhere (Vite's preview and the dev server have their own fallback, and nothing else serves `dist/`), and one build path is simpler to test than two.
   - The status stays 404. Browsers render the page anyway; search engines may not index a deep link, which no job page should be.
   - *Alternative:* the `spa-github-pages` redirect trick, which rewrites the URL into a query string and back. Rejected: more code, and a visible redirect, for no gain.
4. **Mock mode is never deployed.** Three layers:
   - **Today's guard:** `npm run build` is the `production` mode, whose `.env.production` sets `VITE_API_MOCKING=off`; MSW and the banner are dropped from the bundle, and `mockServiceWorker.js` from `dist/`.
   - **A build with mocking on and `VITE_API_BASE_URL` set fails,** in `vite.config.ts`. MSW answers only the relative `/api/v1`, so such a build would call the real API while showing the mock data banner.
   - **The workflow checks the build:** it fails if any file in `dist/` contains `mockServiceWorker` or "mock data". Not a bare `msw`, which a minified name could match by chance.
5. **The API docs link in the footer.**
   - `<apiBaseUrl()>/docs`: `/api/v1/docs` relative when the setting is empty, which works through the dev proxy and on one origin; `https://api.example.org/api/v1/docs` when set.
   - Hidden when `isApiMocked()`, since no API stands behind mocked answers.
   - A plain `<a>`, not the router's `Link`: the docs are the API's page, not a route of this app. It opens in the same tab; a job's page has its own URL, so Back returns to it.
   - It's in `src/layout/`, beside the footer, not in the `versions` feature, since it doesn't depend on the versions request.
6. **`PANTHER_API_CORS_ORIGINS`, a comma-separated list in `settings.py`.**
   - Typed `tuple[str, ...]` with pydantic-settings' `NoDecode`, so the variable is a plain list, not JSON. Spaces and empty items are ignored.
   - **Each item must be an exact origin:** `http` or `https`, a host and an optional port, with no path, wildcard or trailing slash. Anything else stops the API at startup, like every invalid setting. The likely mistake, the Pages URL with its path, `https://pantherdb.github.io/panther-scoring-services/`, would otherwise match no request, silently. The error names the value: it's configuration, not request data.
7. **CORS through `cors.Cors`, which wraps Starlette's `CORSMiddleware`.**
   - The settings are read in the lifespan, after `create_app()` has built the middleware stack, so the origins can't be passed to `add_middleware`. `Cors` reads them from `app.state.settings` on each request, as `BodyLimit` reads its limit, and builds the `CORSMiddleware` for them once.
   - **No origins:** the request passes straight through. No CORS header is ever added, and a preflight gets the app's own `405`, as today.
   - **Origins set:** `allow_origins` exactly those, `allow_methods` `GET` and `POST`, `allow_headers` `Content-Type`, `expose_headers` `Location` and `Retry-After` (the `202`'s and the `503`'s), `allow_credentials` false. Starlette also lists the CORS-safelisted request headers (`Accept`, `Accept-Language`, `Content-Language`) in a preflight's answer; those are always allowed by browsers anyway.
   - **Another origin** gets no `Access-Control-Allow-Origin`; its preflight gets Starlette's `400`. The API still answers a simple request: it's the browser that withholds the answer.
   - *Alternative:* read `Settings()` in `create_app()` and add `CORSMiddleware` directly. Rejected: `app = create_app()` runs at import, so an invalid setting would fail the import instead of the startup, and the settings would be read twice.
8. **Middleware order: `Cors` outside `BodyLimit`.** `add_middleware` puts each new middleware outside the ones before it, so `create_app()` adds `BodyLimit`, then `Cors`.
   - A preflight is answered by `Cors` before the limit sees it, even one that declares a large `Content-Length`.
   - A `413` from `BodyLimit` passes back through `Cors`, which adds `Access-Control-Allow-Origin` for an allowed origin, so the browser lets the page read the problem details instead of reporting a network error.
9. **The workflow, `.github/workflows/pages.yml`:** three jobs.
   - **`configured`** checks `vars.PANTHER_API_URL`. Empty: it writes a notice to the job summary and an annotation, and ends successfully, so `build` and `deploy` are skipped and the run is green. Set but not `https://`: it fails, since a Pages site is HTTPS and browsers block its calls to an HTTP API.
   - **`build`:** `npm ci` and `npm run build` with `VITE_API_BASE_URL` and `BASE_PATH` from the variables, passed as `env`, never written into a script. Then the mock check (decision 4) and `actions/upload-pages-artifact`.
   - **`deploy`:** `actions/configure-pages`, which fails naming the setting if Pages' source isn't GitHub Actions, then `actions/deploy-pages`, in the `github-pages` environment. Only this job gets `pages: write` and `id-token: write`; the workflow's default is `contents: read`.
   - **Triggers:** a push to `main` touching `frontend/**` or the workflow, and `workflow_dispatch`, to deploy after the variables are first set.
   - **Concurrency:** one `pages` group, never cancelled in progress, so a deployment isn't cut off.
   - **Pinned by commit SHA,** with the version in a comment, as `ci.yml` does: `actions/configure-pages` v6.0.0, `actions/upload-pages-artifact` v5.0.0, `actions/deploy-pages` v5.0.1, and `ci.yml`'s `checkout` and `setup-node`. All three tags are lightweight, pointing at the commits pinned.
   - **No secrets:** `PANTHER_API_URL` is public anyway, in every copy of the bundle.
   - `ci.yml` is unchanged: the `frontend` job already builds, lints and tests what this workflow builds.

## Risks / Trade-offs

- **The API's URL is in the bundle** and fixed per build: changing the server means running the workflow again. It's public by nature; a browser has to call it.
- **Deep links get status 404** on Pages, with the app's page as the body. Users don't see the status.
- **Jobs live in the API's memory** (hosting.md, A Public API). A deployed link to a job stops working when the API restarts; the job page already says the job wasn't found.
- **A Pages deploy doesn't wait for CI.** It runs on a push to `main`, which the ruleset admits only after `ci-passed`.

## Migration Plan

None for developers: with every setting empty, nothing changes but the footer link. Going live is the runbook, `docs/deployment/runbook-pages.md`.
