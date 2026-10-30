# Proposal

**Area:** frontend. It also changes shared files: `.github/workflows/ci.yml` (the `frontend` job and its paths filter), `docs/testing/README.md` (the `frontend` row) and the Purpose of `openspec/specs/scoring-ui/spec.md`.

## Why

The API now publishes a real contract (`api/openapi.json`, with `GET /api/v1/versions` from `connect-api-to-engine`), but the frontend has no generated types and makes no API call. [frontend-stack.md](../../../docs/design/frontend-stack.md) says the types come from the schema, and that CI generates them so an API change can't silently break the frontend. Doing it now, with one small read-only endpoint, settles the generation, the check and the first RTK Query endpoint before the jobs endpoints arrive.

## What Changes

- **`npm run api:types`** in `frontend/` generates `src/app/api/schema.d.ts` from `../api/openapi.json` with `openapi-typescript`, with no running API. The generated file is committed, and left out of Prettier and ESLint.
- **`npm run api:types:check`** fails when `schema.d.ts` doesn't match what the schema generates. CI's `frontend` job runs it, and the job's paths filter adds `api/openapi.json`, so a contract change runs the frontend's checks.
- **The first API call:** a `getVersions` RTK Query endpoint, injected from a new `features/versions/` folder and typed from the generated schema. An MSW handler answers it in the dev server, the e2e build and Vitest.
- **The versions on every page:** the app shell's footer shows the API version, the engine version and each external tool's version. A tool with a `null` version shows as not available. A failed request says the versions are unavailable.
- **Tests,** written first from the spec scenarios: Vitest + React Testing Library with MSW for the footer, including the `null` and failure cases; Playwright for mock mode and api mode.
- **The `scoring-ui` Purpose** names the four services, not cSNP scoring only.
- **Docs:** `docs/testing/frontend.md` (the two scripts and when to run them) and the `frontend` row of `docs/testing/README.md`'s What CI Runs table.

New dependency: **`openapi-typescript` 7.13.0** (MIT), a devDependency pinned exactly, as frontend-stack.md names it. Its 20 transitive packages are MIT, ISC, Apache-2.0 or `MIT OR CC0-1.0`, all on `dependency-review`'s allow list.

Not in this change:

- **The jobs endpoints' types.** The API's jobs change regenerates `api/openapi.json`; `schema.d.ts` is regenerated after both changes merge.
- **Versions with each job's results** (frontend/CLAUDE.md, cSNP-Specific Rules). That needs job results; it reuses this change's endpoint types and display.
- **The app's title,** which still says "PANTHER cSNP Scoring".
- **A shared module converting the API's shapes to the app's.** `Versions` has no field to rename.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui` gains one requirement: the versions shown on every page, with `null` and failure handled. Its Purpose is edited directly to name the four services.

## Impact

- **Frontend code:** `package.json` (the dependency, two scripts), `src/app/api/schema.d.ts` (generated), `src/features/versions/`, `src/layout/AppLayout.tsx` (the footer), `src/mocks/`, `.prettierignore`, `eslint.config.js`; tests in `tests/` and `e2e/`.
- **CI:** the `frontend` job runs one more command, and runs when `api/openapi.json` changes. The API developer's contract changes now also run the frontend job.
- **API contract:** consumed, not changed. No change to `api/` or `engine/`.
- **Parity with each service's reference:** not affected. No scoring logic, no divergence.

## Open Questions

Each needs team verification.

- **Where the versions appear.** The working choice is the app shell's footer, on every page. An About page, or the results page only, are the alternatives (design.md, "Where the versions appear").
- **Versions as provenance, not build details.** The `scoring-ui` spec forbids build details on screen. This change treats tool and engine versions as scientific provenance, which frontend/CLAUDE.md asks for with results. The frontend developer confirms the footer doesn't conflict with that rule's intent.
- **Version labels.** The footer shows each tool by its executable name (`blastp`, `hmmscan`), as the API reports it, not by package (BLAST+, HMMER). The API's design leaves room to add a package name later.
- **The PANTHER data version** isn't in the API's response yet. When the API adds it, it shows in the footer after `api:types` is rerun.
