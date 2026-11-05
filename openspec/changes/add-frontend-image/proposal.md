# Proposal

**Area:** cross-cutting: `frontend/` (a Dockerfile and an nginx config), `compose.yaml`, CI, which also publishes the API image, and the deployment docs. No API or engine code changes. The engine developer reviews the server side.

## Why

The site is already served from the team server, beside the API: the server's own nginx serves a build of `frontend/` at the site's root and forwards `/api/` to the API. Each update means installing Node, building and copying the files by hand. The API, by contrast, is rebuilt on the server from the repository with Docker.

This change gives the frontend the same routine, and keeps it optional: the server can keep its own web server and only use Docker to build the files, run the site as a container beside the API, or carry on as now.

It also does hosting.md's "Later" for both images: CI publishes them to GitHub's container registry after a merge to `main`, so the server can pull the image CI checked instead of building it.

## What Changes

- **`frontend/Dockerfile`,** with three stages from one build:
  - **`build`:** Node, pinned by digest, runs `npm ci` and `npm run build`. The production build: no mock data, which the stage checks for, as the Pages workflow does. `BASE_PATH` and `VITE_API_BASE_URL` are build arguments with the build's own defaults: served at `/`, calling the relative `/api/v1`.
  - **`site`:** only the built files, for `docker build --output` to write to a folder that an existing web server serves.
  - **`web`** (the default): an unprivileged nginx, pinned by digest, serving the files on port 8080. It sends any path that isn't a file to `index.html`, so deep links work, and forwards `/api/` to the API at `API_UPSTREAM`, `http://api:8000` by default.
- **`frontend/.dockerignore`,** so `node_modules`, `dist` and test output stay out of the build.
- **`compose.yaml`:** a `web` service, built from `frontend/`, on port 8080, after `api`. `docker compose up --build web` runs the site and the API together.
- **CI:** a `web-image` job, run when `frontend/` changes:
  - it builds the image, and checks the home page, a deep link, an asset's caching and `/api/v1/health` through the image, against a stand-in for the API;
  - it checks that the `site` stage writes `index.html` and `404.html`, and that copying the files out of the image gives the same files.
- **Publishing:** on a push to `main`, after the image's checks pass, `web-publish` and `api-publish` push the image to GitHub's container registry, as `ghcr.io/pantherdb/panther-web` and `ghcr.io/pantherdb/panther-api`, tagged `main` and with the commit's SHA, for `linux/amd64`. Each runs only when what's in its image changed. Pull requests never publish. Runs on `main` no longer cancel each other, so no push skips its publish.
- **Docs:** a new `docs/deployment/runbook-server.md`: pulling or building each image, both ways to serve the site, updating and rolling back. Updates to `docs/design/hosting.md` (the server as an alternative to Pages), `docs/testing/frontend.md`, the root `CLAUDE.md` and `docs/deployment/README.md`.

Not in this change:

- **HTTPS, the hostname and the ports the server exposes.** Those are the server's front end, the engine developer's call (hosting.md).
- **Deploying automatically.** The server pulls when someone chooses to; CI never reaches the server.
- **`linux/arm64` images on the registry.** The server needs `amd64`; an `arm64` machine builds the image itself.
- **Deleting old images.** They're kept until someone deletes them on the package's page.
- **Removing GitHub Pages.** Both use the same build; which one serves users is the team's call.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui`: new requirements for building the site in a container, writing the built files to a folder, the web image serving the site and forwarding the API, running the site with the API in one command, and publishing the web image.
- `api-service`: a new requirement for publishing the API image.

## Impact

- **Code:** new `frontend/Dockerfile`, `frontend/.dockerignore` and `frontend/nginx/default.conf.template`; `compose.yaml`; `.github/workflows/ci.yml`. No source in `frontend/src/` changes.
- **API contract:** none.
- **CI time:** the root `Dockerfile` doesn't change, so the engine and API image jobs don't run for a frontend change. The new job builds Node and nginx images, a few minutes. On `main`, a publish job rebuilds its image from the cache and pushes it, a minute or two; free for a public repository.
- **Permissions:** only the two publish jobs can write packages, and only on a push to `main`.
- **Dependencies:** two base images, Node 24.22.2 (slim) and `nginxinc/nginx-unprivileged` 1.30.1 (Alpine), pinned by digest.
- **Parity with the reference:** not affected. No divergence row is needed.

## Open Questions

Each needs team verification:

- **Which way the server uses:** the `web` container behind the server's nginx, the built files served by that nginx, or neither for now.
- **The API container's name on the server,** for `API_UPSTREAM`, if the `web` image runs there.
- **The server's architecture:** the published images are `linux/amd64`.
- **Who makes the two packages public** after their first publish: an organization owner.
