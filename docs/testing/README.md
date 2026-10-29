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
| API | `api/` | pytest with FastAPI's `TestClient`: request validation, error responses, the OpenAPI schema; later the job lifecycle. See [api.md](api.md) |
| Engine | `engine/` | Unit tests per service and per pipeline step, and for `core/`, with pytest. Tests marked `tools` run the pinned external tools, in the engine image. See [engine.md](engine.md) |
| Parity | `engine/` | Python vs each service's golden files (the legacy Perl, or the pinned EBI `treegrafter`). In CI, on every pull request, with the sample of the cSNP data. On staging, by hand: the full-library Perl-vs-Python comparison for `csnp`, for M1 acceptance and before releases that change its file parsing or trace-back. After every deploy: a data checksum check and a smoke test with the golden requests. See [../parity/](../parity/README.md) and [Environments](../design/tech-stack.md#shared-concerns) |

## What CI Runs

`.github/workflows/ci.yml` runs on every pull request and every push to `main`. The required check, `ci-passed`, fails if any job below failed.

| Job | When | What it runs |
| --- | ---- | ------------ |
| `frontend` | `frontend/` changed | From `frontend/`: `npm ci`, `npm run format:check`, `npm run lint`, `npm run type-check`, `npm test`, `npm run build`, then `npm run test:e2e` (mock mode, Chromium only) |
| `api` | `api/` changed | From `api/`: `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run basedpyright`, `uv run pytest` (including the check that `api/openapi.json` is current). See [api.md](api.md) |
| `engine` | `engine/`, the `Dockerfile`, `.dockerignore` or `compose.yaml` changed | From `engine/`: `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run basedpyright`, `uv run pytest`. The tests marked `tools` skip. See [engine.md](engine.md) |
| `engine-image` | As for `engine` | On `ubuntu-latest` (amd64) and `ubuntu-24.04-arm` (arm64): builds the `engine` target of the root `Dockerfile`, then runs `panther-engine tools` and `uv run --no-sync pytest` in the image, where a missing tool fails its tests (`PANTHER_REQUIRE_TOOLS=1`) |
| `openspec-change` | Pull requests | Fails if code in `frontend/`, `api/` or `engine/` changed but `openspec/changes/` didn't, unless the pull request has the `no-spec` label |
| `repo` | Always | From the root: `npx markdownlint-cli2`, `npx openspec validate --all`, and a gitleaks scan of the new commits |
| `dependency-review` | Pull requests | New dependencies with a moderate or worse advisory, or a licence outside the allowed list. Reads `frontend/package-lock.json`, `api/uv.lock` and `engine/uv.lock`. When a pull request adds a lock file, check that the job's log has a `File:` section listing its packages: a pass looks the same when a file isn't read. When GitHub's scanner misreads a package's licence, exempt that package by purl in `allow-dependencies-licenses`, with a comment saying why; never widen `allow-licenses` for one package |

The parity suite isn't in the engine jobs yet. It joins them with the parity harness, which also brings the image of the legacy Perl references ([tech-stack.md](../design/tech-stack.md), Engine condition 3).

Manual checks done by a person go in [../manual-qa/](../manual-qa/README.md), not here.
