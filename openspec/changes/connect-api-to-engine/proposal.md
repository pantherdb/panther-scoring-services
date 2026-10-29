# Proposal

**Area:** api. It also changes shared root files: the `Dockerfile`, `compose.yaml`, `.dockerignore` and `.github/workflows/ci.yml`.

## Why

The engine package and its tools image are merged (`scaffold-engine`, #14), but the API doesn't depend on the engine, isn't in the image, and can't be started with the tools. Every API change that runs a real tool needs this connection, starting with the jobs endpoints and the first service. Doing it now, in a change with no scoring logic, settles the image, compose and CI setup on their own. It also gives the frontend a real API to call on port 8000.

## What Changes

- **The API depends on the engine.** `panther-engine` is an editable path dependency in `api/pyproject.toml`, as [api-stack.md](../../../docs/design/api-stack.md) ("How the engine joins") planned, and is locked in `api/uv.lock`. There are no new third-party dependencies.
- **New endpoint: `GET /api/v1/versions`.** It returns the API version, the engine version, and each external tool the engine uses (`blastp`, `hmmscan`, `hmmsearch`, `epa-ng`) with its version, or `null` when the tool is missing. It reads them once at startup through the engine's tool report, not per request. It never includes file paths. This is the versions model that job results will later include ([tech-stack.md](../../../docs/design/tech-stack.md), API recommendation 3).
- **An `api` stage in the root `Dockerfile`,** on top of the `tools` stage. It installs the API and the engine without the dev group and without an editable install, and serves the API on port 8000. It builds for `linux/amd64` and `linux/arm64`, like the engine image. `.dockerignore` lets `api/` in.
- **A compose `api` service,** built from that stage, on `localhost:8000`, where the frontend's dev proxy already sends `/api`. It has no source mount and no reload: it runs the API for the frontend to call. API development itself stays native, with `uv run fastapi dev`.
- **CI:**
  - The `api` paths filter adds `engine/**` and the image files.
  - A new `api-image` job builds the `api` stage on both architectures, starts it, and checks that `/api/v1/versions` reports all four tools.
  - `ci-passed` needs `api-image`.
- **Docs:**
  - `docs/testing/api.md`: running the API in the image, and the versions endpoint.
  - `docs/testing/README.md`: the CI table.
  - `CONTRIBUTING.md`: the `api-service` row.
  - `CLAUDE.md`: its Layout section still says `api/` and `engine/` are empty.

Not in this change:

- **The PANTHER data version** in the versions response. There are no data settings yet. Adding the field later doesn't break the frontend's generated types.
- **A settings module** (pydantic-settings). Nothing in this change is configurable.
- **Jobs, the worker pool and any service endpoint.** Jobs are the next API change.
- **Production serving:** worker count, proxy headers and the deployment itself.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `api-service` gains three requirements:
  - the versions report at `GET /api/v1/versions`;
  - an image that serves the API with the pinned tools, on both architectures;
  - one command to run that image on a developer's machine.

  The health check's requirement doesn't change: it still depends on no engine, tools or data.

## Impact

- **Code:** `api/pyproject.toml` and `api/uv.lock`; a new `versions` router and a lifespan in `create_app()`; new tests; a regenerated `api/openapi.json`.
- **Shared files:**
  - `Dockerfile` (a new `api` stage, and its header comment)
  - `.dockerignore` (`api/`)
  - `compose.yaml` (the `api` service, and its header comment)
  - `.github/workflows/ci.yml` (the `api` filter, the `api-image` job, `ci-passed`)

  The engine developer reviews these, since the engine image and compose service build on the same files.
- **API contract:** a new endpoint and two new schema components in `api/openapi.json`. The frontend developer reviews them. The frontend has no `api:types` script yet, so it has no generated types to update.
- **Engine:** no code changes. The API uses the engine's existing `report_tools()` and `__version__`.
- **Parity with each service's reference:** not affected. There's no scoring logic and no divergence.
- **CI time:** one more image job per architecture. It reuses the engine image's cached tool stages, so only the API's Python layers build each time.

## Open Questions

Each needs team verification.

- **Endpoint name.** `/api/v1/versions` is the working name. The API developer confirms it, or picks another such as `/api/v1/about`.
- **Public in production?** The endpoint shows tool versions, which are already public in the `Dockerfile`, and the API and engine versions. The working default is public. The site and the frontend can then show which versions produced a result.
- **`null` for both cases.** A missing tool and a tool whose version can't be read both show as `null`. The engine's `panther-engine tools` tells them apart; the endpoint doesn't need to, unless the frontend or operations want it to.
