# Proposal

**Area:** cross-cutting: `frontend/` (a Dockerfile, an nginx config and a build check), `compose.yaml`, CI and the deployment docs. No API or engine code changes. The engine developer reviews the server side.

## Why

The site is already served from the team server, beside the API: the server's own nginx serves a build of `frontend/` at the site's root and forwards `/api/` to the API. Each update means installing Node, building and copying the files by hand. The API, by contrast, is rebuilt on the server from the repository with Docker.

This change gives the frontend the same routine, and keeps it optional: the server can keep its own web server and only use Docker to build the files, run the site as a container beside the API, or carry on as now.

## What Changes

- **`frontend/Dockerfile`,** with three stages from one build:
  - **`build`:** Node, pinned by digest, runs `npm ci` and `npm run build`. The production build: no mock data, which `npm run check:no-mocks` checks, as the Pages workflow does. `BASE_PATH` and `VITE_API_BASE_URL` are build arguments with the build's own defaults: served at `/`, calling the relative `/api/v1`. A network that re-signs TLS, as the server's does, passes its CA certificate as a build secret.
  - **`site`:** only the built files, for `docker build --output` to write to a folder that an existing web server serves.
  - **`web`** (the default): an unprivileged nginx, pinned by digest, serving the files on port 8080. It sends any path that isn't a file to `index.html`, so deep links work, and forwards `/api/` to the API at `API_UPSTREAM`, `http://api:8000` by default, looking its name up again so a replaced API container is found.
- **`npm run check:no-mocks`** (`frontend/scripts/check-no-mocks.mjs`): the check for mock data, shared by the Dockerfile and `pages.yml`.
- **`frontend/.dockerignore`,** so `node_modules`, `dist` and test output stay out of the build.
- **`compose.yaml`:** a `web` service, built from `frontend/`, on port 8080, after `api`. `docker compose up --build web` runs the site and the API together.
- **CI:** a `web-image` job, run when `frontend/` changes:
  - it builds the image, and checks the home page, a deep link, an asset's caching and `/api/v1/health` through the image, against a stand-in for the API;
  - it checks that the `site` stage writes `index.html` and `404.html`.
- **Docs:** a new `docs/deployment/runbook-server.md`: both ways to serve the site, the server's CA certificate, what the server's front end must pass on, updating and rolling back. Updates to `docs/design/hosting.md` (the server as an alternative to Pages, and what building on the server needs), `docs/testing/frontend.md`, the root `CLAUDE.md` and `docs/deployment/README.md`.

Not in this change:

- **HTTPS, the hostname and the ports the server exposes.** Those are the server's front end, the engine developer's call (hosting.md).
- **Publishing images to a registry.** A first version of this change had CI publish both images on a merge to `main`. It's for hosting.md's review to decide, as its "Getting the Image to the Server" says; that section now lists what review on #61 found publishing would need.
- **The server's CA in the root `Dockerfile`.** The API image's build has the same problem on the server; it's an open question in hosting.md.
- **Removing GitHub Pages.** Both use the same build; which one serves users is the team's call.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui`: new requirements for building the site in a container, writing the built files to a folder, the web image serving the site and forwarding the API, and running the site with the API in one command.

## Impact

- **Code:** new `frontend/Dockerfile`, `frontend/.dockerignore`, `frontend/nginx/` (the template and an entrypoint script) and `frontend/scripts/check-no-mocks.mjs`; `frontend/package.json` and `eslint.config.js`; `compose.yaml`; `.github/workflows/ci.yml` and `pages.yml`. No source in `frontend/src/` changes.
- **API contract:** none.
- **CI time:** the root `Dockerfile` doesn't change, so the engine and API image jobs don't run for a frontend change. The new job builds Node and nginx images, a few minutes.
- **Dependencies:** two base images, Node 24.22.2 (slim) and `nginxinc/nginx-unprivileged` 1.30.1 (Alpine), pinned by digest.
- **Parity with the reference:** not affected. No divergence row is needed.

## Open Questions

Each needs team verification:

- **Which way the server uses:** the `web` container behind the server's nginx, the built files served by that nginx, or neither for now.
- **The API container's name on the server,** for `API_UPSTREAM`, if the `web` image runs there.
- **Where the server's CA certificate is,** for the build secret.
