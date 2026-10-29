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
| Engine | `engine/` | Unit tests per service and per pipeline step, and for `core/` |
| Parity | `engine/` | Python vs each service's golden files (the legacy Perl, or the pinned EBI `treegrafter`). In CI, on every pull request, with the sample of the cSNP data. On staging, by hand: the full-library Perl-vs-Python comparison for `csnp`, for M1 acceptance and before releases that change its file parsing or trace-back. After every deploy: a data checksum check and a smoke test with the golden requests. See [../parity/](../parity/README.md) and [Environments](../design/tech-stack.md#shared-concerns) |

## What CI Runs

`.github/workflows/ci.yml` runs on every pull request and every push to `main`. The required check, `ci-passed`, fails if any job below failed.

| Job | When | What it runs |
| --- | ---- | ------------ |
| `frontend` | `frontend/` changed | From `frontend/`: `npm ci`, `npm run format:check`, `npm run lint`, `npm run type-check`, `npm test`, `npm run build`, then `npm run test:e2e` (mock mode, Chromium only) |
| `api` | `api/` changed | From `api/`: `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run basedpyright`, `uv run pytest` (including the check that `api/openapi.json` is current). See [api.md](api.md) |
| `openspec-change` | Pull requests | Fails if code in `frontend/`, `api/` or `engine/` changed but `openspec/changes/` didn't, unless the pull request has the `no-spec` label |
| `repo` | Always | From the root: `npx markdownlint-cli2`, `npx openspec validate --all`, and a gitleaks scan of the new commits |
| `dependency-review` | Pull requests | New dependencies with a moderate or worse advisory, or a licence outside the allowed list. Reads `frontend/package-lock.json` and `api/uv.lock`. When GitHub's scanner misreads a package's licence, exempt that package by purl in `allow-dependencies-licenses`, with a comment saying why; never widen `allow-licenses` for one package |

There is no `engine/` job yet. The engine developer adds it once the folder has code, with the parity suite in it. The comments in `ci.yml` say where.

Manual checks done by a person go in [../manual-qa/](../manual-qa/README.md), not here.
