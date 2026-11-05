# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **[hosting.md](../../../docs/design/hosting.md)** (Proposed): the API image is built on the server from the repository, and the server's front end, its HTTPS and its ports are the engine developer's call.
- **[frontend-stack.md](../../../docs/design/frontend-stack.md)** (Accepted) and the build settings in [docs/testing/frontend.md](../../../docs/testing/frontend.md#build-settings): `BASE_PATH`, `VITE_API_BASE_URL`, `404.html` in every build, no mock data in a production build.
- **The root `Dockerfile`'s rules:** every base image pinned by digest, a change to a pin is a pull request.

What the server does today: its nginx serves a build of `frontend/` at the site's root, sends deep links to `index.html`, and forwards `/api/` to the API container. So the page and the API share one origin, with no CORS.

The behaviour is in [specs/scoring-ui/spec.md](specs/scoring-ui/spec.md).

## Goals / Non-Goals

**Goals:**

- One build, used three ways: an image, files for an existing web server, or not at all.
- The same update routine as the API's: pull, build with Docker, restart.
- Or no build on the server at all: pull the image CI checked, for the site and the API.
- No Node on the server.

**Non-Goals:**

- HTTPS and the public hostname: the server's front end.
- Deploying from CI: the server pulls when someone chooses to.

## Decisions

### 1. `frontend/Dockerfile`, not a stage in the root `Dockerfile`

CI's paths filters run the engine and API image jobs, both architectures, on any change to the root `Dockerfile`. A stage there would rebuild them for every frontend change to the image. In `frontend/`, with `frontend/` as its build context, the image needs nothing outside the folder, and the root `.dockerignore`, an allowlist of `engine/` and `api/`, stays as it is.

### 2. Three stages from one build

- **`build`:** `node:24.22.2-slim`, by digest; `.nvmrc` says 24, and `package.json` allows `>=24.15.0`.
  - It runs on the build machine's platform (`--platform=$BUILDPLATFORM`), since the output is the same everywhere.
  - Dependencies install before the source is copied, so a source change reuses the `npm ci` layer.
  - After `npm run build`, it fails if `dist/` names `mockServiceWorker` or "mock data", the same check as `pages.yml`.
- **`site`:** `FROM scratch` holding only `dist/`. `docker build --target site --output type=local,dest=<folder> frontend` writes the files and starts nothing.
- **`web`:** last, so it's the default target.

Alternative: **a script that runs `npm` in a Node container with the folder mounted.** It writes as root into the checkout on Linux, and isn't the API's routine.

### 3. nginx, unprivileged, with the API's address set when it starts

`nginxinc/nginx-unprivileged:1.30.1-alpine`, by digest: the official build that runs as a non-root user and listens on 8080. Its entrypoint fills `/etc/nginx/templates/*.template` from the environment, replacing only variables that are set, so `$host` and nginx's other variables survive.

- **`API_UPSTREAM`,** `http://api:8000` by default, compose's service name. On the server it's whatever the API container is called.
- **`/api/`** is forwarded with `Host`, `X-Forwarded-For` and `X-Forwarded-Proto`. `client_max_body_size` is 17m, a little over the API's 16 MiB limit, so the API answers an oversized body itself, with its problem details and CORS headers.
- **Deep links:** `try_files $uri $uri/ /index.html`.
- **Caching:** `/assets/` files have hashed names, so they're cached for a year, `immutable`. Everything else is `no-cache`, so a new build shows on the next load.
- **No HTTPS:** the server's front end terminates it. Behind that front end, the API sees the `web` container's address, not the user's, unless the API trusts forwarded headers. That's a later setting on the API, not this change.

### 4. compose: `web` beside `api`

`depends_on: api`, port 8080, built from `./frontend`. nginx looks up `api` when it starts, so it starts after the API's container. The existing services don't change.

### 5. CI: its own job, with a stand-in API

A `web` paths filter (`frontend/**`, `compose.yaml`, `ci.yml`) and a `web-image` job, amd64 only:

- It builds the `web` target with the GitHub Actions cache.
- It runs the image on a Docker network beside a stand-in API: the root `Dockerfile`'s pinned Python image serving a fixed `api/v1/health` file. Building the API image here would add many minutes to every frontend change, and forwarding is all this checks.
- It checks the home page, a deep link, an asset's `Cache-Control`, and `/api/v1/health` through the image.
- It writes the `site` stage to a folder, and checks `index.html` and `404.html` are there.
- It copies the files out of the image with `docker cp`, the runbook's way for a pulled image, and checks they're the same as the `site` stage's.
- `ci-passed` needs it.

The site sits in `/srv/site`, not nginx's `html/`, which holds nginx's own sample pages: copying the folder out gives exactly the build.

### 6. Publishing to GitHub's container registry

Two jobs in `ci.yml`, `web-publish` and `api-publish`, on a push to `main` only:

- **After the checks:** each needs its image job and its unit-test job, which always run when it does, so it's never skipped by a skipped need. A failing check means nothing is published.
- **Only when the image changed:** its own paths filter, narrower than the check's. `web-publish` is `frontend/**`. `api-publish` is what the API image copies: `api/`, the engine's `src/`, `pyproject.toml` and `tools-env/`, the root `Dockerfile` and `.dockerignore`. A change to `compose.yaml` or `ci.yml` alone publishes nothing.
- **Rebuilt from the cache:** the same build arguments and the check job's cache, so the layers are the ones checked, and the job takes a minute or two.
- **Tags:** `main`, which moves, and the full commit SHA, which never does. Rolling back is running an earlier SHA.
- **`linux/amd64` only.** The API image's `arm64` build is checked but not published: publishing both means building on two runners and joining them into one manifest, for a server that needs one.
- **`GITHUB_TOKEN` with `packages: write`,** on those two jobs only. It logs in with `docker login`, so there's no new action to pin. The image's `org.opencontainers.image.source` label links the package to the repository.
- **Concurrency:** runs on `main` no longer cancel each other. A cancelled run would skip its push's publish, and the next run's filter only sees the next push. Each publish job has its own group, one at a time, so the `main` tag can't go back to an older build.

Alternatives:

- **A separate workflow** on a push to `main`. It would publish without waiting for CI's checks on the merged commit, or wait on `workflow_run` and repeat CI's paths filters.
- **The built files as a release's `.tar.gz`.** The runbook copies them out of the published image instead, so there's one thing to publish.

## Risks / Trade-offs

- **[Two web servers in a row on the server]** if the `web` image runs behind the server's nginx → the runbook also offers the `site` files, which keep one nginx. Which one is the server's choice.
- **[nginx can't start if the API's container isn't up]** → compose starts `api` first; the runbook says to start the API first, and how to check it.
- **[A base image pin goes stale]** → as with the root `Dockerfile`, a pin changes by pull request; Dependabot doesn't update it.
- **[The packages start private]** → the first publish creates them private; an organization owner makes each public once. The runbook says so, and until then the server can build as before.
- **[The `main` tag moves under a running server]** → the server only changes when someone pulls and restarts; the SHA tags never move.
- **[Old images pile up]** → they're small and free for a public package. The runbook says how to delete them.

## Migration Plan

Nothing changes on the server until someone chooses to use it. The first merge of this change publishes the web image; the API image follows the next merge that changes it. Rolling back is the runbook's: an earlier SHA tag, the previous image tag, or the previous folder.
