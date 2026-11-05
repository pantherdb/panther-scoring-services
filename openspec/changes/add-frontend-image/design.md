# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **[hosting.md](../../../docs/design/hosting.md)** (Proposed): the API image is built on the server from the repository, and the server's front end, its HTTPS and its ports are the engine developer's call. Whether CI publishes images is for hosting.md's review; this change doesn't decide it.
- **[frontend-stack.md](../../../docs/design/frontend-stack.md)** (Accepted) and the build settings in [docs/testing/frontend.md](../../../docs/testing/frontend.md#build-settings): `BASE_PATH`, `VITE_API_BASE_URL`, `404.html` in every build, no mock data in a production build.
- **The root `Dockerfile`'s rules:** every base image pinned by digest, a change to a pin is a pull request.

What the server does today: its nginx serves a build of `frontend/` at the site's root, sends deep links to `index.html`, and forwards `/api/` to the API container. So the page and the API share one origin, with no CORS. The server re-signs TLS, so a download during a build there must trust its CA (review on #61).

The behaviour is in [specs/scoring-ui/spec.md](specs/scoring-ui/spec.md).

## Goals / Non-Goals

**Goals:**

- One build, used three ways: an image, files for an existing web server, or not at all.
- The same update routine as the API's: pull, build with Docker, restart.
- No Node on the server.

**Non-Goals:**

- HTTPS and the public hostname: the server's front end.
- Publishing images: hosting.md's review decides it (Context).

## Decisions

### 1. `frontend/Dockerfile`, not a stage in the root `Dockerfile`

CI's paths filters run the engine and API image jobs, both architectures, on any change to the root `Dockerfile`. A stage there would rebuild them for every frontend change to the image. In `frontend/`, with `frontend/` as its build context, the image needs nothing outside the folder, and the root `.dockerignore`, an allowlist of `engine/` and `api/`, stays as it is.

### 2. Three stages from one build

- **`build`:** `node:24.22.2-slim`, by digest; `.nvmrc` says 24, and `package.json` allows `>=24.15.0`.
  - It runs on the build machine's platform (`--platform=$BUILDPLATFORM`), since the output is the same everywhere.
  - Dependencies install before the source is copied, so a source change reuses the `npm ci` layer.
  - **The server's CA:** `npm ci` runs with a build secret, `id=ca`, mounted when given, and points `NODE_EXTRA_CA_CERTS` at it. Node uses its own CA bundle, not the system's, so behind the server's TLS re-signing `npm ci` fails without it. A secret is never kept in a layer and doesn't change the cache key; without one, the build is unchanged.
  - After `npm run build`, `npm run check:no-mocks` fails if `dist/` names `mockServiceWorker` or "mock data". The Pages workflow runs the same script, so the check is written once (`scripts/check-no-mocks.mjs`, Node, so it also runs on Windows).
- **`site`:** `FROM scratch` holding only `dist/`. `docker build --target site --output type=local,dest=<folder> frontend` writes the files and starts nothing.
- **`web`:** last, so it's the default target.

Alternatives:

- **A script that runs `npm` in a Node container with the folder mounted.** It writes as root into the checkout on Linux, and isn't the API's routine.
- **The CA as a build argument or a copied file.** Either would stay in the image's history or a layer.

### 3. nginx, unprivileged, with the API's address set when it starts

`nginxinc/nginx-unprivileged:1.30.1-alpine`, by digest: the official build that runs as a non-root user and listens on 8080. Its entrypoint fills `/etc/nginx/templates/*.template` from the environment, replacing only variables that are set, so `$host` and nginx's other variables survive.

- **`API_UPSTREAM`,** `http://api:8000` by default, compose's service name. On the server it's whatever the API container is called. An entrypoint script, `05-api-upstream.envsh`, drops a trailing slash, which would otherwise make every request reach the API as `/`.
- **The API's name is looked up again.** nginx resolves a fixed `proxy_pass` host once, at start, so after the API's container is replaced, with a new IP, every call would fail until `web` restarted (review on #61). The address goes in a variable, with `resolver ${NGINX_LOCAL_RESOLVERS} valid=10s`. The base image's entrypoint sets `NGINX_LOCAL_RESOLVERS` from the container's `resolv.conf`, Docker's DNS, when `NGINX_ENTRYPOINT_LOCAL_RESOLVERS` is set, which the image does. A variable with no path passes the request's path unchanged.
- **`/api/`** is forwarded with the `Host` it received (`$http_host`, with the port), `X-Forwarded-For`, and the `X-Forwarded-Proto` the front end sent, or this server's scheme if none: a `map` at the http level. Replacing them would tell the API `http` behind HTTPS.
- **`client_max_body_size` is 17m,** a little over the API's 16 MiB limit, so the API answers an oversized body itself, with its problem details and CORS headers. A front end before this needs the same; nginx's default is 1 MiB, and the runbook says so.
- **IPv4 only.** The base image adds an IPv6 listen only where the host supports it; a fixed one stops nginx on a host with IPv6 turned off.
- **Deep links:** `try_files $uri $uri/ /index.html`.
- **Caching:** `/assets/` files have hashed names, so they're cached for a year, `immutable`. Everything else is `no-cache`, so a new build shows on the next load.
- **No HTTPS:** the server's front end terminates it.
- **Served at `/`.** A site built with a `BASE_PATH` works behind a front end that strips the path, and the runbook says how; otherwise the built files (B) suit a path.

The site sits in `/srv/site`, not nginx's `html/`, which holds nginx's own sample pages.

### 4. compose: `web` beside `api`

`depends_on: api`, port 8080, built from `./frontend`. The existing services don't change.

### 5. CI: its own job, with a stand-in API

A `web` paths filter (`frontend/**`, `compose.yaml`, `ci.yml`) and a `web-image` job, amd64 only:

- It builds the `web` target with the GitHub Actions cache, `mode=max`, so the build stage's `npm ci` layer is cached too.
- It runs the image on a Docker network beside a stand-in API: the root `Dockerfile`'s pinned Python image serving a fixed `api/v1/health` file. Building the API image here would add many minutes to every frontend change, and forwarding is all this checks.
- It waits for the site, then for the stand-in through it, which answers 502 until it listens.
- It checks the home page, a deep link, an asset's `Cache-Control`, and `/api/v1/health` through the image.
- It writes the `site` stage to a folder, from the builder's own cache, and checks `index.html` and `404.html` are there.
- `ci-passed` needs it.

## Risks / Trade-offs

- **[Two web servers in a row on the server]** if the `web` image runs behind the server's nginx → the runbook also offers the `site` files, which keep one nginx. Which one is the server's choice.
- **[nginx can't start if the API's name doesn't resolve]** → compose starts `api` first; the runbook says to start the API first, on the named network.
- **[A base image pin goes stale]** → as with the root `Dockerfile`, a pin changes by pull request; Dependabot doesn't update it.
- **[The front end's body limit]** → nginx's 1 MiB default refuses a large job before it reaches the API; the runbook lists 17 MiB among what the front end needs.

## Migration Plan

Nothing changes on the server until someone chooses to use it. Rolling back is the runbook's: the previous image tag, or the previous folder.
