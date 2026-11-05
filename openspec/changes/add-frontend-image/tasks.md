# Tasks

## 1. The Image

- [x] 1.1 Add `frontend/Dockerfile` (stages `build`, `site`, `web`; design decision 2) and `frontend/.dockerignore`. Verified by building each target, by a build with `BASE_PATH=/scoring/` whose `index.html` names `/scoring/assets/`, and by the mock-data check failing on a `build:e2e` build.
- [x] 1.2 Add `frontend/nginx/default.conf.template` (decision 3). Verified by running the image beside a stand-in API: `/`, `/jobs/abc`, an asset's `Cache-Control`, `/api/v1/health` forwarded, and `id -u` not 0.
- [x] 1.3 Add the `web` service to `compose.yaml` (decision 4). Verified with `docker compose config`, and with the real API image by `docker run` on a test network and port, never the repository's own compose project: health, versions, a tools job, the docs and a 413 through the site.

## 2. CI

- [x] 2.1 Add the `web` filter and the `web-image` job to `.github/workflows/ci.yml`, and add it to `ci-passed`'s `needs` (decision 5). Verified by running the job's commands locally, then by the pull request's run.

## 3. Publishing

- [x] 3.1 Move the site to `/srv/site` in the `web` image, and add the `docker cp` check to `web-image` (design decision 5). Verified by rebuilding the image, running `web-image`'s checks against it, and comparing the copied files with the `site` stage's.
- [x] 3.2 Add the `web-publish` and `api-publish` filters and jobs, and the concurrency for `main`, to `ci.yml` (decision 6). Verified with `actionlint`; the jobs themselves run only on `main`, so the first merge is their first run.

## 4. Docs and Final Check

- [x] 4.1 Add `docs/deployment/runbook-server.md`: the two ways, the build settings, updating, rolling back and the checks after. List it in `docs/deployment/README.md`. Add the server option to `docs/design/hosting.md`, the image to `docs/testing/frontend.md`, and `frontend/Dockerfile` to the root `CLAUDE.md`'s layout.
- [x] 4.2 Add pulling to the runbook: the registry, the tags, the one-time step that makes a package public, getting the files from a pulled image, and the API image. Update hosting.md's "Getting the Image to the Server", `docs/testing/frontend.md` and `frontend/README.md`.
- [x] 4.3 Final check: from the root, `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass, and this change is valid with `--strict`; in `frontend/`, `format:check` and `lint` pass (nothing in `src/` changed).

## Workflow follow-up

- **Review:** the engine developer approves the server side, and the frontend developer the rest.
- **After the implementation merges,** archive with `/opsx:archive`.

## Notes

### Next action

Every task is done (2026-11-05). Next: the pull request, its CI run of `web-image`, and the engine developer's review. After it merges: check that `web-publish` ran on `main`, and ask an organization owner to make `panther-web` public; `panther-api` after the next merge that changes the API.

### Blockers

None.

### Failed approaches

- **A stage in the root `Dockerfile` (design, 2026-11-04).** Recommended at first, dropped before writing it: CI's paths filters run the engine and API image jobs, on both architectures, for any change to that file, so every change to the frontend's image would have rebuilt them.

### Lessons learned

- **The asset names match the server's.** The image built `index-nKQ7UjHD.js`, the same file the team server serves today, so the server's current build and this one are the same code.
- **A body over 17 MiB gets nginx's own `413`,** an HTML page, not the API's problem details. Between 16 and 17 MiB the API answers itself. The frontend shows its fixed "couldn't be started" text either way.
- **In Git Bash, `curl -o /dev/null` fails with "error 23"** under `MSYS_NO_PATHCONV=1`. Harmless locally; CI runs on Linux.
- **Final check (2026-11-04).** The image built and ran on Docker 29.8; `markdownlint-cli2`, `openspec validate --all` and `--strict` for this change, and `format:check` and `lint` in `frontend/`, pass. The `web-image` job's checks passed when run locally against the image; CI hasn't run it yet.
- **nginx's base image ships sample pages in `html/`** (`index.html`, `50x.html`). Copying that folder out of the image would carry `50x.html` along, so the site moved to `/srv/site` (2026-11-05).
- **The publish jobs can't run before merging.** They're gated on a push to `main`; `actionlint` checked them, and the build they run is `web-image`'s and `api-image`'s, with `push: true`.
- **Final check, with publishing (4.3, 2026-11-05).** The rebuilt image passed `web-image`'s checks locally, and its copied-out files matched the `site` stage's; `actionlint`, `markdownlint-cli2`, `openspec validate --all` and `--strict` for this change, and `format:check` and `lint` in `frontend/`, pass.
