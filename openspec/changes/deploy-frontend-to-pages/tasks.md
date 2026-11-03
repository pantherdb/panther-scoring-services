# Tasks

## 1. The Frontend

- [x] 1.1 Add `apiBaseUrl()` in `src/app/apiBaseUrl.ts`, reading `VITE_API_BASE_URL`, type it in `src/vite-env.d.ts`, and use it in `api.ts`'s `fetchBaseQuery` (design.md, decision 1). Verify with `tests/app/apiBaseUrl.test.ts`: empty, blank and unset give `/api/v1`; a URL, with or without trailing slashes, gives `<url>/api/v1`; a path is kept (spec, The API's address set at build time)
- [x] 1.2 Set Vite's `base` from `BASE_PATH` in `vite.config.ts`, pass `import.meta.env.BASE_URL` as `createBrowserRouter`'s `basename` in `main.tsx`, and register MSW's worker under it (decision 2). Verify with `tests/app/router.test.tsx`, given a `basename` through `renderRoute`: the home page at the base path, `/csnp` under it, and the not-found page's link to the base path and back home (spec, Served under a base path)
- [x] 1.3 Write `404.html`, a copy of `index.html`, in every build (decision 3), and fail a build with mocking on and `VITE_API_BASE_URL` set (decision 4). Verify that a build with `VITE_API_BASE_URL=https://api.example.org` and `BASE_PATH=/panther-scoring-services/` has an identical `404.html`, asset URLs under the base path, the URL in its JavaScript, and no `msw`, `mockServiceWorker` or "mock data" (spec, Deep links survive a reload on a static host; No mock mode in a deployed build)
- [x] 1.4 Add the API docs link to the footer, `src/layout/ApiDocsLink.tsx`, hidden in mock mode (decision 5). Verify with `tests/layout/ApiDocsLink.test.tsx`: the href with the setting empty and set, and no link when mocked (spec, API docs link)
- [x] 1.5 Check the build in a browser under the base path: `vite preview` of the build in 1.3, with the API's origin answered by Playwright's `page.route`. The home page, the versions from the API's origin, a link to `/csnp` and a reload of it, the not-found page and its link home, and a job's URL. A one-off script, not committed (Notes)

## 2. The API

- [x] 2.1 Add `cors_origins` to `settings.py`: a comma-separated list, each an exact origin (decision 6). Verify with `tests/test_settings.py`: empty by default, the list split and trimmed, and `*`, a wildcard host, a path, a trailing `/`, a bare host and another scheme refused (spec, Only exact origins are allowed)
- [x] 2.2 Add `cors.Cors`, wrapping Starlette's `CORSMiddleware`, and add it in `create_app()` after `BodyLimit` (decisions 7 and 8). Verify with `tests/test_cors.py`: no headers and a `405` preflight without origins; an allowed origin's preflight and request get the headers, without credentials; another origin and a request without an `Origin` get no `Access-Control-Allow-Origin`; a preflight declaring a body over the limit is answered; a `413` carries the headers for an allowed origin only (spec, CORS for allowed origins; CORS with the body limit)
- [x] 2.3 Check that `api/openapi.json` doesn't change: CORS is headers only. `tests/test_openapi.py` passes

## 3. The Workflow

- [x] 3.1 Add `.github/workflows/pages.yml`: the `configured`, `build` and `deploy` jobs, the variables, the mock check, and the Pages actions pinned by commit SHA (decision 9). Verify the SHAs with `gh api repos/<owner>/<repo>/git/ref/tags/<tag>`, and run `actionlint` on it if it's available
- [ ] 3.2 After merging: a repository admin turns on Pages, the variables are set, and the workflow deploys a site that calls the API (runbook-pages.md). Needs #34's server

## 4. Docs

- [x] 4.1 Write `docs/deployment/runbook-pages.md`, and update `docs/design/hosting.md`, `docs/testing/api.md` (the setting, a CORS section), `docs/testing/frontend.md` (Build Settings), `api/README.md`, `api/CLAUDE.md` and `frontend/CLAUDE.md`. Verify with `npx markdownlint-cli2`

## 5. Final Check

- [x] 5.1 In `api/`: `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run basedpyright`, `uv run pytest`. In `frontend/`: `npm run api:types:check`, `format:check`, `lint`, `type-check`, `npm test`, `npm run test:e2e`. At the root: `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive`. All pass

## Notes

### Next action

Review: open the pull request against `main` with this change's artifacts and code, for the frontend and API owners' approval. After merging, task 3.2, once #34's server has a hostname.

### Blockers

- Task 3.2 needs the API's public URL (#34) and a repository admin to turn on Pages.

### Failed approaches

- **`BASE_PATH=/panther-scoring-services/ npm run build` in Git Bash (2026-11-02)** built with asset URLs under `/C:/Program Files/Git/panther-scoring-services/`: MSYS rewrote the value into a Windows path. `MSYS_NO_PATHCONV=1` fixes it; the testing doc says so. CI runs on Linux and isn't affected.
- **A first browser check (2026-11-02)** answered every API path with the versions body, so the cSNP page got a malformed species list and showed the error page. The stub was wrong, not the app: answering each path with its own body passed.

### Lessons learned

- **React Router keeps the trailing slash of a `basename`:** a `Link to="/"` under `/panther-scoring-services/` points at `/panther-scoring-services/`, which is what Pages serves its `index.html` at.
- **Starlette's `CORSMiddleware` adds the CORS-safelisted request headers** (`Accept`, `Accept-Language`, `Content-Language`) to a preflight's allowed headers, whatever `allow_headers` says.
- **The settings are read in the lifespan, after the middleware stack is built,** so a middleware configured by a setting reads it from `app.state.settings` per request, as `BodyLimit` and `Cors` do.
- **The `@mock` refmap spec of 100,000 IDs can time out** when `npm run test:e2e` runs with Playwright's default workers on a loaded Windows machine (twice on 2026-11-02, on its 5 s wait for the ID count). It passes alone and with `--workers=2`, where all 32 pass. It's unrelated to this change; CI hasn't shown it.
- **A bare `msw` is a poor check of a minified build:** a short mangled name could match it. The workflow checks for `mockServiceWorker` instead, which MSW's start-up always names.
