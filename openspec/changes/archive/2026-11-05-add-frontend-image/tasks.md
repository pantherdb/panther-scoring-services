# Tasks

## 1. The Image

- [x] 1.1 Add `frontend/Dockerfile` (stages `build`, `site`, `web`; design decision 2) and `frontend/.dockerignore`. Verified by building each target, by a build with `BASE_PATH=/scoring/` whose `index.html` names `/scoring/assets/`, and by the mock-data check failing on a `build:e2e` build.
- [x] 1.2 Add `frontend/nginx/default.conf.template` (decision 3). Verified by running the image beside a stand-in API: `/`, `/jobs/abc`, an asset's `Cache-Control`, `/api/v1/health` forwarded, and `id -u` not 0.
- [x] 1.3 Add the `web` service to `compose.yaml` (decision 4). Verified with `docker compose config`, and with the real API image by `docker run` on a test network and port, never the repository's own compose project: health, versions, a tools job, the docs and a 413 through the site.

## 2. CI

- [x] 2.1 Add the `web` filter and the `web-image` job to `.github/workflows/ci.yml`, and add it to `ci-passed`'s `needs` (decision 5). Verified by running the job's commands locally, then by the pull request's run.

## 3. Docs and Final Check

- [x] 3.1 Add `docs/deployment/runbook-server.md`: the two ways, the build settings, updating, rolling back and the checks after. List it in `docs/deployment/README.md`. Add the server option to `docs/design/hosting.md`, the image to `docs/testing/frontend.md`, and `frontend/Dockerfile` to the root `CLAUDE.md`'s layout.
- [x] 3.2 Final check: from the root, `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass, and this change is valid with `--strict`; in `frontend/`, `format:check` and `lint` pass (nothing in `src/` changed).

## 4. Review on #61

- [x] 4.1 Take publishing out: the `web-publish` and `api-publish` jobs, their filters, the concurrency for `main`, and the `docker cp` check. Restore hosting.md's "Getting the Image to the Server", add what building on the server needs and what publishing would need, and keep its open question. The work stays on the local branch `publish-images-draft` for after hosting.md's review.
- [x] 4.2 nginx looks the API's name up again: the address in a variable, `resolver ${NGINX_LOCAL_RESOLVERS} valid=10s`, and `NGINX_ENTRYPOINT_LOCAL_RESOLVERS=1` in the image (decision 3). Verified by replacing the stand-in API's container with one at a new IP while `web` ran: the next request through the site reached it (spec, The API's container replaced)
- [x] 4.3 Pass on the `Host` and `X-Forwarded-Proto` received, drop a trailing slash from `API_UPSTREAM` (`05-api-upstream.envsh`), and listen on IPv4 only (decision 3). Verified with an echoing stand-in: `API_UPSTREAM=http://…:8000/` still reached `/api/v1/health`, and `X-Forwarded-Proto: https` and the host with its port arrived (spec, Forwarded by a front end)
- [x] 4.4 Take the server's CA as a build secret for `npm ci` (decision 2). Verified by building the `build` stage without its cache, with a CA bundle as the secret: `npm ci` installed all 500 packages (spec, Behind a network that re-signs TLS)
- [x] 4.5 Add `npm run check:no-mocks` (`scripts/check-no-mocks.mjs`), and use it in the Dockerfile and `pages.yml`. Verified that it passes a production build and fails a `build:e2e` one, naming the two files
- [x] 4.6 In `web-image`: cache `mode=max`, wait for the stand-in API through the site too, and drop the `--cache-from` a `run` step can't use (decision 5). Verified with `actionlint`, then by the pull request's run
- [x] 4.7 In the runbook: the CA secret on every build, the front end's 17 MiB body limit and forwarded headers, a path with A only when the front end strips it, the trailing slash, and the API container replaced without restarting `panther-web`. Final check as in 3.2, with `actionlint` on both workflows

## Workflow follow-up

- **Review:** the engine developer approves the server side, and the frontend developer the rest.
- **After the implementation merges,** archive with `/opsx:archive`.
- **Publishing:** after hosting.md's review settles it, a new change from `main`, using `publish-images-draft` and the points hosting.md lists.

## Notes

### Next action

Every task is done (2026-11-05). The pull request, #61, is in review; the engine developer's review is answered by section 4. Next: their approval, then merge and archive. Don't open another pull request for this change.

### Blockers

None.

### Failed approaches

- **A stage in the root `Dockerfile` (design, 2026-11-04).** Recommended at first, dropped before writing it: CI's paths filters run the engine and API image jobs, on both architectures, for any change to that file, so every change to the frontend's image would have rebuilt them.
- **Publishing both images from this change (2026-11-05).** Added, then taken out after review on #61: it replaced hosting.md's decision while hosting.md's review is pending, and the server is the engine developer's call. The review also found it rebuilt the image instead of pushing the one CI checked, let the `main` tag go back to an older build, and didn't wait for the engine's tests before publishing the API image. hosting.md now lists those.
- **An IPv6 `listen` in the template.** It stops nginx on a host with IPv6 turned off; the base image adds one only where the host supports it.

### Lessons learned

- **The asset names match the server's.** The image built `index-nKQ7UjHD.js`, the same file the team server serves today, so the server's current build and this one are the same code.
- **A body over 17 MiB gets nginx's own `413`,** an HTML page, not the API's problem details. Between 16 and 17 MiB the API answers itself. The frontend shows its fixed "couldn't be started" text either way. A front end with nginx's default, 1 MiB, refuses far sooner.
- **In Git Bash, `curl -o /dev/null` fails with "error 23"** under `MSYS_NO_PATHCONV=1`. Harmless locally; CI runs on Linux.
- **nginx resolves a fixed `proxy_pass` host once, at start.** With the address in a variable and a `resolver`, it looks the name up again. The base image's entrypoint fills `NGINX_LOCAL_RESOLVERS` only when `NGINX_ENTRYPOINT_LOCAL_RESOLVERS` is set.
- **Docker reuses a freed IP.** A replaced container often gets its old address back, which hides a stale lookup; the test started another container first, to take it.
- **Node doesn't use the system's CA certificates,** so a build behind TLS re-signing needs `NODE_EXTRA_CA_CERTS`, here from a build secret.
- **`docker buildx build` in a `run` step can't use the `gha` cache:** the cache service's token and URL are given only to actions. It gets the builder's local cache from the step before.
- **Final check (2026-11-04).** The image built and ran on Docker 29.8; `markdownlint-cli2`, `openspec validate --all` and `--strict` for this change, and `format:check` and `lint` in `frontend/`, pass. The `web-image` job's checks passed when run locally against the image, and on the pull request.
