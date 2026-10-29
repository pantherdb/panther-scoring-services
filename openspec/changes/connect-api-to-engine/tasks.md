# Tasks

## 1. Engine Dependency

- [x] 1.1 In `api/pyproject.toml`, add `panther-engine` to `dependencies`, with `[tool.uv.sources]` set to `{ path = "../engine", editable = true }`, and run `uv lock`. Verify:
  - `uv sync --locked` passes in `api/`, and `uv run python -c "import panther_engine; print(panther_engine.__version__)"` prints the engine's version;
  - `api/uv.lock` adds no third-party package;
  - `uv run basedpyright` in `api/` reports a scratch call with a wrong argument type to `panther_engine.core.tools.report`, which proves it reads the engine's types (then remove the call; if it doesn't, follow design.md's Risks and record it in the Notes);
  - the existing `ruff check`, `ruff format --check`, `basedpyright` and `pytest` all pass.

## 2. Versions Endpoint

- [x] 2.1 Add `src/panther_api/versions.py` with the `ToolVersion` model (`name`; `version: str | None`, required), the `Versions` model (`api`, `engine`, `tools`) and `read_versions()`, which builds `Versions` from the package versions and `report_tools()`, copying only each tool's name and version. In `tests/conftest.py`, add an autouse fixture that replaces `panther_api.versions.report_tools` with a fake reporting all four tools with fixed versions and made-up paths. Verify that `tests/test_versions.py` unit tests for `read_versions()` pass and cover:
  - the engine's tool order;
  - `null` both for a tool with no path and for one with a path but no version;
  - none of the fake's paths in `model_dump_json()`.
- [x] 2.2 Add the lifespan to `create_app()` (`read_versions()` through `fastapi.concurrency.run_in_threadpool`, stored on `app.state.versions`) and `routers/versions.py` (`GET /versions`, response model `Versions`, tag `versions`), included in the `/api/v1` router. Verify `tests/test_versions.py` passes and covers the spec's scenarios through `TestClient`:
  - "All tools present" (200, both versions, the four tools in order);
  - "A tool is missing" (a fake without `epa-ng`: 200, `epa-ng` is `null`, the other three are listed);
  - "No file paths" (none of the fake's paths in the body);
  - "Repeated requests" (a counting fake is called once for three requests, and the bodies are equal).

  Also verify that `tests/test_health.py` passes unchanged, and that `GET /health` still answers with the report fake made to raise.
- [x] 2.3 Regenerate `api/openapi.json` with `uv run python -m panther_api.openapi`. Verify:
  - `test_committed_schema_is_current` passes;
  - the schema lists `GET /api/v1/versions` with its `default` and `500` problem responses and no 422;
  - `ToolVersion.version` is required and allows `null`.

  The frontend has no `api:types` script yet, so it has no generated types to regenerate; record that in the Notes. Also start `uv run fastapi dev --port 8000` and verify `curl localhost:8000/api/v1/versions` returns 200 with each tool's version `null` (no tools on this machine) and no paths.
- [x] 2.4 In `docs/testing/api.md`:
  - add `/api/v1/versions` to the list of URLs with the dev server running, and say that natively the tools show as `null`;
  - in the Tests section, describe the autouse fake for the engine's tool report and how a test swaps in its own.

  Verify every command in the doc still runs as written from `api/`.

## 3. Image and Compose

- [x] 3.1 Add `!api/` (and `api/.venv`) to `.dockerignore`, and the `api` stage to the `Dockerfile` as design.md describes; update the header comment's stage list. Verify on this machine:
  - `docker buildx build --target api --load -t panther-api:local .` builds;
  - `docker run --rm -d -p 8000:8000 --name panther-api panther-api:local` serves `/api/v1/health` (200), and `/api/v1/versions` reports `blastp` 2.17.0, `hmmscan` 3.4, `hmmsearch` 3.4 and `epa-ng` 0.3.8 with no paths (the spec's "Versions in the image");
  - `docker exec panther-api id -un` prints `panther`;
  - after editing only a file in `api/src/`, a rebuild reuses the dependency layer (`CACHED` in the build log).

  Record the uncached and cached build times in the Notes. If the dependency layer or `fastapi run` needs a fallback (design.md's Risks), record which.
- [x] 3.2 Verify the `engine` stage is unaffected: `docker compose run --rm engine` passes with no test skipped, and `docker compose run --rm engine panther-engine tools` reports the four tools.
- [x] 3.3 Add the `api` service to `compose.yaml` (build target `api`, port `8000:8000`, no mount, no command), and update its header comment, which says the API joins later. Verify the spec's "Start the API" scenario from a copy of the files git would commit:
  - `docker compose up --build -d api`, then `curl localhost:8000/api/v1/health` (200) and `curl localhost:8000/api/v1/versions` (four tools with versions);
  - with it running, `npm run dev` in `frontend/` and `curl localhost:5173/api/v1/versions` returns the same body through the dev proxy;
  - `docker compose down` stops it.
- [x] 3.4 Add a "Running the API in the Image" section to `docs/testing/api.md`:
  - `docker compose up --build api`, from the repository root;
  - that it's for the frontend to call, with no reload;
  - that it and the native dev server both use port 8000, so run one at a time;
  - `docker compose down`.

  Verify the commands run as written.

## 4. CI

- [x] 4.1 In `.github/workflows/ci.yml`:
  - add `engine/**`, `Dockerfile`, `.dockerignore` and `compose.yaml` to the `api` filter, replacing its "once api/ depends on engine/" comment;
  - add the `api-image` job from design.md: the same matrix as `engine-image`; `docker/build-push-action` at the SHA `engine-image` uses; `cache-from` the `engine-<arch>` and `api-<arch>` scopes, `cache-to` `api-<arch>`; then run detached, wait for `/api/v1/health` with `curl --retry`, check `/api/v1/versions` with `jq` (four tools, none `null`), and print `docker logs` on failure;
  - add `api-image` to `ci-passed`'s `needs`.

  Verify actionlint (`uvx --from actionlint-py actionlint`) reports no errors. Run the job's build, run, wait and `jq` steps locally in order, and check that they pass, and that the `jq` check fails when the response is edited to give one tool a `null` version.
- [x] 4.2 In `docs/testing/README.md`'s What CI Runs table, update the `api` row's When column and add the `api-image` row. Verify the paths and commands match `ci.yml`.

## 5. Shared Docs

- [x] 5.1 Make two edits, then verify `npx markdownlint-cli2` passes from the repository root:
  - **`CONTRIBUTING.md`, Spec Layout:** extend the `api-service` row to cover the versions report and the API image.
  - **`CLAUDE.md`, Layout and Team:** replace "There is no code yet … `api/` and `engine/` hold only a `.gitkeep`" with what exists now: the API app, the engine package, the API depending on the engine, and the root `Dockerfile` and `compose.yaml`.

## 6. Final Check

- [x] 6.1 From a copy of the files git would commit:
  - in `api/`: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest` passes;
  - from the root: `docker compose run --rm engine` passes, `docker compose up --build -d api` serves `/api/v1/versions` with the four pinned versions, then `docker compose down`;
  - `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass.

## Workflow follow-up

- **One pull request for the artifacts and the implementation,** from `feat/api` (decided 2026-10-29, to move fast). Later API changes can join the same branch. Reviewers on that pull request:
  - the API developer approves;
  - the engine developer reviews the `Dockerfile`, `.dockerignore`, `compose.yaml` and `ci.yml` parts;
  - the frontend developer reviews the new contract: `/api/v1/versions`, `Versions` and `ToolVersion`.
- **On that pull request,** confirm:
  - both `api-image` legs run and pass under `ci-passed` (the spec's "Each architecture"); record their uncached and cached times and the cache size in the Notes;
  - `dependency-review` reads `api/uv.lock`. If it flags `panther-engine`, follow design.md's Risks.
- **Settle the proposal's open questions in review:** the endpoint's name, whether it's public in production, and `null` for both missing and unreadable tools.
- **After the implementation merges,** archive with `/opsx:archive`. That merges the three requirements into `openspec/specs/api-service/spec.md`.
- **The next API change:** the jobs endpoints and worker pool (`scoring-jobs`), with `Versions` in each job result.

## Notes

### Next action

Every task is done (2026-10-29). Next: open the pull request from `feat/api`. On it, check the items in the Workflow follow-up: both `api-image` legs, whether `jq` is on the `ubuntu-24.04-arm` runner, the build cache, and `dependency-review` with `panther-engine`. Record each result in Lessons learned.

### Blockers

None.

### Failed approaches

- **Waiting for the container with `curl --retry-connrefused` (3.1, 2026-10-29).** Docker's port proxy accepts the connection before the app listens, so the first requests fail with `curl: (52) Empty reply from server`, not "connection refused", and curl doesn't retry that. Waiting with `--retry-all-errors` works, and is what the `api-image` CI job uses.

### Lessons learned

- **uv (1.1).** This machine had uv 0.11.7, below `required-version`; updated with `uv self update 0.13.6`.
- **The lock (1.1).** `uv lock` added only `panther-engine`, as an `editable = "../engine"` source, and no third-party package. basedpyright in `api/` reads the engine's types through the editable install with no `extraPaths`: a scratch `report("not a tool")` was reported as `reportArgumentType` against the engine's `Tool`.
- **Ruff sorts `panther_engine` with the third-party imports (2.1).** It's a separate distribution, so `I001` puts it beside `fastapi` and `pytest`, not beside `panther_api`.
- **`tests/` has no `__init__.py` (2.1).** Test modules can't import from `conftest.py`, so the autouse `fake_tools` fixture returns its reports, and tests take it as an argument.
- **A failing tool report (2.2).** If `report_tools()` raised, say on undecodable output, the lifespan would fail and take the health check down with it. `read_versions()` now logs it and lists every tool as `null`. design.md records this; a test covers it.
- **The lifespan is typed `AsyncGenerator[None]` (2.2).** basedpyright reports `AsyncIterator` with `@asynccontextmanager` as deprecated (`reportDeprecated`).
- **No frontend types to regenerate (2.3).** The frontend has no `api:types` script or `schema.d.ts` yet, so the contract change is only `api/openapi.json`.
- **The schema export writes CRLF on Windows (2.3).** `openapi.py` uses `write_text`, which writes the platform's line endings. The test reads in text mode, so it passes, and `.gitattributes` (`eol=lf`) makes git store LF; git only prints a warning. Passing `newline="\n"` would stop the warning; not changed here.
- **The image (3.1), on this machine (amd64, Docker 29.8.0).** The `api` stage built in 16 s with the tool stages already cached from the engine image, and in 2 s after a source-only change, with the dependency layer `CACHED`. The dependency layer needed only `engine/pyproject.toml`; no fallback was needed, and `fastapi run` found the app through `[tool.fastapi]`. The API and engine are installed as regular packages, with no `.pth`. The container runs as `panther`. `/api/v1/versions` reports `blastp` 2.17.0, `hmmscan` and `hmmsearch` 3.4, `epa-ng` 0.3.8, with no paths.
- **CI checked locally (4.1).** actionlint 1.7.12 reports no errors. The `api-image` job's build, run, health wait and versions steps pass locally. This machine has no `jq`, so the expression was checked with `ghcr.io/jqlang/jq:1.7.1`: it prints `true` and exits 0 on the real response, and prints `false` and exits 1 when one version is `null`. GitHub's Ubuntu runner images include `jq`; whether `ubuntu-24.04-arm` does too is checked on the pull request.
- **The cache mode (4.1).** `api-image` reads both the `engine-<arch>` and `api-<arch>` scopes and writes `api-<arch>` with `mode=min`: only the layers in the API image, not the blast, hmmer and epang build stages, which `engine-image` already caches.
- **Final check (6.1).** Run from a copy of the files git would commit: the API's native checks (25 tests), `docker compose run --rm engine` (17 tests, none skipped), and `docker compose up --build -d api` with the four pinned versions. markdownlint (42 files) and `openspec validate --all` (5 items) ran from the working repository, since the copy has no root `node_modules`.
- **Compose (3.3).** From a copy of the files git would commit, `docker compose up --build -d api` serves health and versions. With the frontend's `npm run dev` running, `localhost:5173/api/v1/versions` returns the same body through its proxy. `docker compose run --rm engine` still passes 17 tests with none skipped.

- **Artifacts and code in one pull request (2026-10-29).** The team chose to skip the separate artifact-review pull request for the API work and review the artifacts and the implementation together. The artifacts were reviewed in conversation before apply started. `feat/api` was branched from `main` at `c61b850`, after `scaffold-engine` was archived.
