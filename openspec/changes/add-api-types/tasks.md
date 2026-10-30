# Tasks

## 1. Generated Types and Their Check

- [x] 1.1 In `frontend/`, add `openapi-typescript` as an exact devDependency at its newest version, and the `api:types` script from design.md. Run it, and add `src/app/api/schema.d.ts` to `.prettierignore` and to `globalIgnores` in `eslint.config.js`. Verify:
  - `package.json` pins the version with no range, and every package it adds to `package-lock.json` has a licence on `dependency-review`'s `allow-licenses` in `ci.yml`; `npm audit` reports nothing;
  - `schema.d.ts` has `components['schemas']['Versions']`, with `ToolVersion.version` typed `string | null`, and only LF line endings;
  - `npm run format:check`, `npm run lint` and `npm run type-check` pass.
- [x] 1.2 Add the `api:types:check` script. Verify it exits 0 on the committed file; exits 1, naming the stale types, after one field name in `schema.d.ts` is edited by hand; and writes nothing in either case (`git status` shows only the hand edit, which is then reverted).
- [x] 1.3 In `.github/workflows/ci.yml`, add `api/openapi.json` to the `frontend` paths filter, and an `npm run api:types:check` step after `npm ci` in the `frontend` job, named so its failure says to run `npm run api:types`. Update the `frontend` row of `docs/testing/README.md`'s What CI Runs table, and only that row. Verify actionlint (`uvx --from actionlint-py actionlint .github/workflows/ci.yml`) reports nothing, and the row's paths and commands match `ci.yml`.
- [x] 1.4 In `docs/testing/frontend.md`, add `api:types` and `api:types:check` to the Scripts table, and an "API Types" section: when to run it (after `api/openapi.json` changes, including in the API's pull request), that the result is committed, and that it's left out of Prettier and ESLint. Verify both commands run as written from `frontend/`.

## 2. Versions on Every Page (Test-First)

- [x] 2.1 Add `src/mocks/data/versions.ts` (the mocked `Versions` body, typed from the schema, with the image's pinned versions) and its `GET /api/v1/versions` handler in `src/mocks/handlers.ts`. Verify `npm test` and `npm run type-check` pass, with no UI changed yet.
- [x] 2.2 Write `tests/features/versions/AppVersions.test.tsx` from the spec scenarios, before any UI: "All versions reported" (including the loading state first), "A tool is missing", "Versions can't be loaded", "On the not-found page" and "Versions are not build details". Run it and verify every test fails because the page has no versions, not because of an import, type or setup error. Record the red run in the Notes.
- [x] 2.3 Write `e2e/versions.spec.ts`: a `@mock` test that the footer shows the mocked versions and the page doesn't scroll sideways, and an `@api` test that it shows what `/api/v1/versions` answers. Update `e2e/shell.spec.ts`'s comment that the shell makes no API calls. Run `npm run test:e2e` and verify the new test fails on both projects because the versions aren't shown. Record the red run in the Notes.
- [x] 2.4 Implement design.md's endpoint and rendering: `features/versions/` (`versionsApi.ts`, `AppVersions.tsx`, `VersionList.tsx`, `index.ts`) and the footer in `AppLayout.tsx`. Verify:
  - the tests from 2.2 and every existing Vitest test pass (`npm test`);
  - `npm run test:e2e` passes on both projects;
  - `npm run format:check`, `npm run lint`, `npm run type-check` and `npm run build` pass;
  - no API type is written by hand: `Versions` is an alias of the generated type.
- [x] 2.5 Verify api mode against the real API, from the worktree's root: `docker compose up --build -d api`, then `npm run test:e2e:api` in `frontend/` passes, and the footer shows `blastp` 2.17.0, `hmmscan` 3.4, `hmmsearch` 3.4 and `epa-ng` 0.3.8; then `docker compose down`.

## 3. Spec Purpose and Final Check

- [x] 3.1 Edit the Purpose of `openspec/specs/scoring-ui/spec.md` to name the four services (`hmmscore`, `refmap`, `csnp`, `treegrafter`). Verify `npx openspec validate --all --no-interactive` passes.
- [x] 3.2 Final check:
  - in `frontend/`: `npm run api:types:check`, `npm run format:check`, `npm run lint`, `npm run type-check`, `npm test`, `npm run build` and `npm run test:e2e` pass;
  - from the root: `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive` pass;
  - actionlint on `ci.yml` reports nothing.

## Workflow follow-up

- **No separate artifact-review pull request** (team decision, 2026-10-29). The artifacts and the code are reviewed together in #16, from `feat/api`. Reviewers there:
  - the frontend developer approves the frontend code, the versions placement and the `scoring-ui` delta and Purpose;
  - the API developer reviews the `ci.yml` change, since a contract change now runs the frontend job.
- **Settle the proposal's open questions in review:** where the versions appear, versions as provenance rather than build details, the tool labels.
- **After both this change and the API's jobs change merge,** regenerate `schema.d.ts` with `npm run api:types` and commit it; `api:types:check` fails until then.
- **On #16,** confirm the `frontend` job runs the check, and that `dependency-review` lists `openapi-typescript` and passes.
- **After the implementation merges,** archive with `/opsx:archive`, which merges the requirement into `openspec/specs/scoring-ui/spec.md`.

## Notes

### Next action

Every task is done (2026-10-29), and the change is committed on its own branch. Next: the coordinator merges it into `feat/api` (#16) with the API's jobs change, then reruns `npm run api:types` in `frontend/` and commits `schema.d.ts`; `api:types:check` fails until then. Then reviews on #16 settle the proposal's open questions.

### Blockers

None.

### Failed approaches

- **Relative URLs under Vitest (2.4, 2026-10-29).** With the footer in place, RTK Query's request for `/api/v1/versions` failed in every test with "TypeError: Failed to parse URL from /api/v1/versions". jsdom leaves Node's `Request` in place, and Node's `Request` doesn't resolve a relative URL against the page as a browser's does. Making `api.ts` build an absolute URL from `location` was not tried: the app must keep calling a relative `/api/v1`. Fixed in `tests/setup.ts` instead (design.md, Risks).

### Lessons learned

- **Artifacts and code in one pull request (2026-10-29).** The team chose to skip the separate artifact-review pull request: this change's artifacts and its implementation are reviewed together in #16.
- **The branch (2026-10-29).** The worktree started at `main` (`c61b850`), not `feat/api`. It was fast-forwarded to `feat/api` (`b604087`) before any work, since `/api/v1/versions` and `connect-api-to-engine` exist only there.
- **The dependency (1.1).** `openapi-typescript` 7.13.0 (MIT), the newest release. It adds 20 transitive packages: MIT, ISC, Apache-2.0 (`yaml-ast-parser`) and `MIT OR CC0-1.0` (`type-fest`), all on `allow-licenses`, so `ci.yml`'s licence settings don't change. `npm audit` reports nothing.
- **The generator writes LF on Windows (1.1),** with a trailing newline, so `--check` matches the file git checks out (`eol=lf`).
- **`--check` (1.2)** compares the generated text with the file exactly, exits 1 with "Generated types are not up-to-date!", and writes nothing. Checked by renaming `engine` by hand in `schema.d.ts`: exit 1, and `git status` showed only the hand edit; after reverting it, exit 0.
- **The Vitest red run (2.2).** All five tests failed with "Unable to find an accessible element with the role "contentinfo"": the layout had no footer. The file type-checked and linted, so no failure came from an import or a type.
- **The e2e red run (2.3).** In mock mode, the `@mock` spec failed on desktop and mobile: `getByRole('contentinfo').getByRole('term')` resolved to 0 elements, where API, Engine and the four tools were expected. The eight shell runs passed. The spec imports `src/mocks/data/versions.ts` directly; Playwright's transform drops its type-only import of the schema.
- **A failure test can pass for the wrong reason (2.4).** Before the `Request` fix, "Versions can't be loaded" passed, because every request failed. The other tests caught it. When a test asserts a failure state, keep a success test beside it.
- **Green (2.4).** `npm test`: 13 tests in 4 files, with no act() or other warnings. `npm run test:e2e`: 10 passed (the `@mock` spec and the four shell specs, on both projects). The production build contains neither the mock data nor MSW.
- **api mode (2.5).** `docker compose up --build -d api` from the worktree's root; `/api/v1/versions` answered `blastp` 2.17.0, `hmmscan` 3.4, `hmmsearch` 3.4 and `epa-ng` 0.3.8. `npm run test:e2e:api`: 10 passed (the `@api` spec, which checks the footer against that response, and the four shell specs, on both projects). Then `docker compose down`.
- **Final check (3.2).** In `frontend/`: `api:types:check`, `format:check`, `lint`, `type-check`, `npm test` (13), `build` and `test:e2e` (10) pass. From the root: `npx markdownlint-cli2` (45 files, 0 issues) and `npx openspec validate --all` (6 items) pass, and actionlint reports nothing on `ci.yml`. Not checked locally: `dependency-review`, which runs only on the pull request.
