# Tasks

## 1. API: The Species List

- [x] 1.1 Add `routers/csnp.py` (design.md, decisions 1 and 3): the `CsnpSpecies` model, the list built once from `panther_engine.csnp.SPECIES_NAMES`, and `GET /csnp/species` with `Cache-Control: public, max-age=3600`. Include it in `create_app()` after `jobs`. Verify with `tests/test_csnp_species.py`: the body is `SPECIES_NAMES` as `{code, name}` entries, in its order; `HUMAN` and `PLAF7` have their names; the header; the list is built once, not per request; it needs no `PANTHER_DATA_DIR`; every listed code is accepted by the `csnp` request's species check, and `XENLA` isn't.
- [x] 1.2 Regenerate `api/openapi.json` with `uv run python -m panther_api.openapi`, and check its diff is only the new path and `CsnpSpecies`. Verify with `tests/test_openapi.py`: the path, its 200 response as an array of `CsnpSpecies`, the model's two required strings, and no enum on the request's `species`. Then `uv sync --locked`, `uv run ruff check`, `uv run ruff format --check`, `uv run basedpyright` and `uv run pytest` pass.
- [x] 1.3 Document the endpoint in `api/README.md` ("What It Serves") and `docs/testing/api.md` (by hand, with curl). Verify `npx markdownlint-cli2` passes.

## 2. Frontend: The Species Selector

- [x] 2.1 Run `npm run api:types`. Export `CsnpSpecies` from `wire.ts`; add `features/csnp/speciesApi.ts` (`getCsnpSpecies`) and `useCsnpSpecies.ts` (design.md, decision 4). Add the MSW handler and `src/mocks/data/species.ts`, eight real species with no runtime imports (decision 6). Verify `npm run api:types:check` and `type-check` pass.
- [x] 2.2 Add `SpeciesField.tsx` (loaded, loading and failed states) and use it in `CsnpForm`; give `checkSpecies` and `checkDraft` the list's codes (decision 5). If `Select` needs a jsdom polyfill, add the smallest one to `tests/setup.ts` and a line to `frontend/CLAUDE.md`. Verify with Vitest: `checks.test.ts` (a code not in the list, and shape only without one); `CsnpPage.test.tsx` (the options and their labels, search by name and by code, the keyboard, the default, the example after another species, a submit sending the chosen code, the loading state, the failure fallback with no build details, a submit from the fallback, a retry that brings the selector back with the typed code, a typed code not in the list after a retry); and the existing tests updated for the selector. `format:check`, `lint`, `type-check` and `npm test -- --run` pass.
- [x] 2.3 Update the e2e specs: the untagged empty-form test for the selector; a mock-mode test that chooses a species by typing part of its name and submits it; api-mode tests that the selector offers the API's whole list, and that a job starts with a species chosen from it other than `HUMAN`; the existing api-mode tests for the selector. Verify `npm run test:e2e` and `API_PROXY_TARGET=http://localhost:8001 npm run test:e2e:api` against the API image with the data sample.
- [x] 2.4 Update `docs/manual-qa/02-csnp-form.md` (the dropdown, search, the default, the example, the failure fallback) and `docs/testing/frontend.md` (the mocked species). Verify `npx markdownlint-cli2` passes.

## 3. Final Check

- [x] 3.1 From the files git would commit:
  - in `api/`: `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright` and `pytest` pass, and `openapi.json` is current;
  - in `frontend/`: `api:types:check`, `format:check`, `lint`, `type-check`, `npm test -- --run`, `npm run test:e2e`, and api-mode e2e against the image with the data sample pass;
  - from the root: `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive` and `docker build --target api .` pass.

## Workflow follow-up

- Open a pull request after `wire-csnp-scoring` (#26) merges, or onto its branch. The frontend and API developers approve: it changes the schema.
- The frontend developer answers the open question on the order on screen.
- After merge, and after `wire-csnp-scoring` is archived, archive this change with `/opsx:archive`.

## Notes

### Next action

Every task is done and committed on the worktree branch, for the coordinator's review. Next: open the pull request after #26, and get the frontend and API developers' approvals.

### Blockers

None. The branch is based on `wire-csnp-scoring`'s (#26) with `main` merged in, so it merges after #26.

### Progress

- **Final check, 2026-10-30:**
  - in `api/`: `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright` pass; `pytest` 172 passed, 5 skipped (the `tools("blastp")` tests, natively). `openapi.json`'s diff is only the new path and `CsnpSpecies`.
  - in `frontend/`: `api:types:check`, `format:check`, `lint`, `type-check` pass; Vitest 205 passed; `npm run test:e2e` 22 passed (and 44 with `--repeat-each=2`); api-mode e2e 28 passed against the API image on port 8001 with the data sample.
  - from the root: `npx markdownlint-cli2` (114 files, no issues), `npx openspec validate --all --no-interactive` (12 passed) and `docker build --target api .` pass.
- **Not checked:** the API's `tools`/`data` tests in the image (nothing they cover changed); the manual QA checklist in a browser by a person; the failure fallback against a stopped API in a browser (Vitest covers it with MSW).

### Failed approaches

- **Opening the selector on a phone (2026-10-30).** With Mantine's default absolute dropdown, mobile e2e found no options: the dropdown was `display: none`, and the page had scrolled from 211 px to the top. On opening, `Select` scrolls the chosen option into view before floating-ui places the dropdown, so the option is at the top of the page then, the window scrolls to it, and `hideDetached` hides the dropdown with the field now out of view. Fixed with `comboboxProps={{ floatingStrategy: 'fixed' }}`: a fixed element is already in the viewport, so nothing scrolls.
- **Finding options under jsdom with Mantine's default provider (2026-10-30).** The options were rendered but inside a `display: none` dropdown, since jsdom gives the field no layout and `hideDetached` treats it as out of view. `MantineProvider env="test"` turns that check off, with transitions and portals.
- **Shell heredocs and multi-command lines (2026-10-30).** The worktree guard refuses commands it can't check, such as heredocs that append to files. Use the Edit and Write tools.

### Lessons learned

- **A searchable Mantine `Select` below the fold needs `floatingStrategy: 'fixed'`,** or opening it scrolls the page to the top on a phone and hides its dropdown. Any later `Select`, `Autocomplete` or `MultiSelect` will hit the same; propose moving this to `frontend/CLAUDE.md` when archiving.
- **Mantine `Select` under jsdom** needs `ResizeObserver` and `scrollIntoView` stubs and `MantineProvider env="test"`; already in `frontend/CLAUDE.md`.
- **A click leaves the chosen option's label in a searchable `Select`,** so typing adds to it. Tests clear the box before typing a search; tabbing in selects the text, as in a browser.
