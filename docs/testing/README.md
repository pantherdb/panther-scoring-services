# Testing

How we test, and how to run each suite. Someone new should be able to run every suite from these docs alone.

## What Goes Here

- `strategy.md`: what each kind of test is responsible for, and what it isn't.
- One file per area with run instructions: `frontend.md`, `api.md`, `engine.md`. Cover the commands, the test data needed, and how to run a single test.

## Kinds of Test

| Kind | Area | Notes |
| ---- | ---- | ----- |
| Unit and component | `frontend/` | Vitest and React Testing Library |
| End-to-end | `frontend/` | Playwright, in three modes: against mocks, a real API, or an already-running site. See [frontend.md](frontend.md) |
| API | `api/` | pytest with FastAPI's `TestClient`: request validation, error responses, the OpenAPI schema, and the job lifecycle through a real worker pool (with stand-in work). Tests marked `tools` and `data` run real `csnp` jobs with `blastp` and the cSNP data sample, where both are there, as in the engine's tests. See [api.md](api.md) |
| Engine | `engine/` | Unit tests per service and per pipeline step, and for `core/`, with pytest. Tests marked `tools` run the pinned external tools, in the engine image. Tests marked `data` read a service's data sample, such as the cSNP sample, from `PANTHER_DATA_DIR`. The parity tests check each pipeline step against the service's golden files, byte for byte, without the reference: for `csnp`, `tests/test_csnp_golden.py`. See [engine.md](engine.md#parity-tests) |
| Parity | `engine/` | Python vs each service's golden files (the legacy Perl, or the pinned EBI `treegrafter`). In CI, on every pull request, with the sample of the cSNP data. On staging, by hand: the full-library Perl-vs-Python comparison for `csnp`, for M1 acceptance and before releases that change its file parsing or trace-back. After every deploy: a data checksum check and a smoke test with the golden requests. See [../parity/](../parity/README.md) and [Environments](../design/tech-stack.md#shared-concerns) |

## What CI Runs

`.github/workflows/ci.yml` runs on every pull request and every push to `main`. The required check, `ci-passed`, fails if any job below failed.

| Job | When | What it runs |
| --- | ---- | ------------ |
| `frontend` | `frontend/` or `api/openapi.json` changed | From `frontend/`: `npm ci`, `npm run api:types:check` (that `src/app/api/schema.d.ts` matches `api/openapi.json`), `npm run format:check`, `npm run lint`, `npm run type-check`, `npm test`, `npm run build`, then `npm run test:e2e` (mock mode, Chromium only) |
| `api` | `api/`, `engine/`, the `Dockerfile`, `.dockerignore` or `compose.yaml` changed | From `api/`: `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run basedpyright`, `uv run pytest` (including the check that `api/openapi.json` is current). See [api.md](api.md) |
| `api-image` | As for `api` | On `ubuntu-latest` (amd64) and `ubuntu-24.04-arm` (arm64): builds the `api` target of the root `Dockerfile`, and fetches the cSNP data sample as `engine-image` does, from the same cache, with the image's `panther-engine`. It starts the image with `.data` mounted read-only at `/data` and `PANTHER_DATA_DIR=/data`, and waits for `/api/v1/health`. Then it checks with `jq` that `/api/v1/versions` lists the four tools, each with a version, and that a `csnp` job for the release sample's P26439 succeeds with its family and spec §7.3 scores |
| `engine` | `engine/`, the `Dockerfile`, `.dockerignore` or `compose.yaml` changed | From `engine/`: `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run basedpyright`. Then it restores `.data/csnp` from the Actions cache, keyed on `sample.json`, and runs `uv run panther-engine csnp sample fetch --data-dir ../.data`, which only checks the files on a cache hit. Last, `uv run pytest` with `PANTHER_REQUIRE_DATA=1`, so a missing sample fails the tests marked `data`. The tests marked `tools` skip. See [engine.md](engine.md) |
| `engine-image` | As for `engine` | On `ubuntu-latest` (amd64) and `ubuntu-24.04-arm` (arm64): builds the `engine` target of the root `Dockerfile` and runs `panther-engine tools` in it. Then it restores the same cache, and runs `panther-engine csnp sample fetch --data-dir /fetch` in the image as the runner's user, with `.data` mounted writable at `/fetch`. Last, `uv run --no-sync pytest` in the image, with `.data` mounted read-only at `/data`, `PANTHER_DATA_DIR=/data` and `PANTHER_REQUIRE_DATA=1`. A missing tool (`PANTHER_REQUIRE_TOOLS=1`) or missing data fails its tests |
| `openspec-change` | Pull requests | Fails if code in `frontend/`, `api/` or `engine/` changed but `openspec/changes/` didn't, unless the pull request has the `no-spec` label |
| `repo` | Always | From the root: `npx markdownlint-cli2`, `npx openspec validate --all`, and a gitleaks scan of the new commits |
| `dependency-review` | Pull requests | New dependencies with a moderate or worse advisory, or a licence outside the allowed list. Reads `frontend/package-lock.json`, `api/uv.lock` and `engine/uv.lock`. When a pull request adds a lock file, check that the job's log has a `File:` section listing its packages: a pass looks the same when a file isn't read. A package with no licence metadata, such as this repository's own `panther-engine`, is reported ("We could not detect a license") but doesn't fail the job. When GitHub's scanner misreads a package's licence, exempt that package by purl in `allow-dependencies-licenses`, with a comment saying why; never widen `allow-licenses` for one package |

The parity tests run in both engine jobs, against the committed goldens: `engine` checks steps 2 and 3, and `engine-image` adds step 1 and `score()` end to end, with `blastp`. CI never runs the legacy Perl. Its image, `csnp-reference`, is built by hand to make the goldens ([golden-setup.md](../parity/golden-setup.md)).

Manual checks done by a person go in [../manual-qa/](../manual-qa/README.md), not here.
