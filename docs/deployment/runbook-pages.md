# Runbook: the Frontend on GitHub Pages

How the frontend gets to GitHub Pages, calling the API on another origin ([hosting.md](../design/hosting.md)). The workflow is `.github/workflows/pages.yml`; the change that added it is `deploy-frontend-to-pages`.

Going live is setting values, never changing code: one GitHub setting, two repository variables, and one setting on the API's server. No secrets are involved: the API's URL is in the built site for anyone to read.

## How It Runs

- **When:** on every push to `main` that touches `frontend/**` or the workflow, and by hand (Actions → Pages → Run workflow).
- **What:** `npm ci` and `npm run build` in `frontend/`, the production build, with the API's URL and the base path from the repository variables. It fails if the build contains the API mocking library or the mock data banner. Then it deploys `frontend/dist/` with GitHub's Pages actions.
- **While `PANTHER_API_URL` is empty,** it builds and deploys nothing, and the run's summary says "Not deployed: the repository variable PANTHER_API_URL isn't set". The run is still green.

## One-Time Setup

### 1. Turn on Pages (a repository admin)

Settings → Pages → Build and deployment → Source: **GitHub Actions**.

Until this is done, the `deploy` job fails at `configure-pages`.

### 2. Set the repository variables

Settings → Secrets and variables → Actions → **Variables** tab → New repository variable. Variables, not secrets.

| Variable | Example | What it sets |
| -------- | ------- | ------------ |
| `PANTHER_API_URL` | `https://api.example.org` | The API's public URL, without `/api/v1`. It must start with `https://`: browsers block an HTTPS page's calls to HTTP. It may include a path, such as `https://example.org/panther`, if the API is served under one |
| `PAGES_BASE_PATH` | `/panther-scoring-services/` | Optional. The path the site is served under. Unset, it's `/panther-scoring-services/`, the project page. Set it to `/` for a custom domain |

The example values are placeholders: the real API hostname is decided in #34.

### 3. Allow the Pages origin on the API's server

Set `PANTHER_API_CORS_ORIGINS` in the API container's environment to the Pages site's **origin**, and restart the API:

```text
PANTHER_API_CORS_ORIGINS=https://pantherdb.github.io
```

- **CORS takes the origin, not the URL:** the scheme and host, with no path and no trailing `/`. Not `https://pantherdb.github.io/panther-scoring-services/`. The API refuses to start with a value that isn't an origin, naming it in the error.
- For more than one origin, such as a custom domain as well, separate them with commas.
- The setting is in [api.md's settings](../testing/api.md#settings).

### 4. Deploy

Actions → Pages → Run workflow, on `main`. Later pushes to `frontend/` deploy on their own.

## Checking It's Live

1. **The run:** Actions → Pages. All three jobs, `configured`, `build` and `deploy`, are green, and `deploy` links the site's URL.
2. **The site:** open `https://pantherdb.github.io/panther-scoring-services/` (or the custom domain). The footer shows the versions from the API, not "Versions are unavailable", and its "API docs" link opens `<PANTHER_API_URL>/api/v1/docs`.
3. **A deep link:** open the cSNP form, reload the page; it still shows the form, not a GitHub 404 page.
4. **CORS,** if the footer says the versions are unavailable: in the browser's developer tools, a CORS error on `/api/v1/versions` means `PANTHER_API_CORS_ORIGINS` doesn't list the site's origin. From a shell:

   ```bash
   curl -si https://api.example.org/api/v1/health -H 'Origin: https://pantherdb.github.io' | grep -i access-control-allow-origin
   ```

   It should print `access-control-allow-origin: https://pantherdb.github.io`.
5. **A job:** score the cSNP example on the form; the job's page shows its results.

## Changing Things Later

- **A new API URL:** change `PANTHER_API_URL`, then run the workflow again. The URL is fixed in each build.
- **A custom domain:** set it in Settings → Pages, set `PAGES_BASE_PATH` to `/`, add the domain's origin to `PANTHER_API_CORS_ORIGINS`, and run the workflow again.
- **Taking the site down:** Settings → Pages → Unpublish site. Emptying `PANTHER_API_URL` only stops new deployments.
