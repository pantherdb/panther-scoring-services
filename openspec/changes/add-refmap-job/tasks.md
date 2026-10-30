# Tasks

## 1. The Legacy Service, Recorded

- [x] 1.1 Read `RefProteomeMapper/` (`map_panther.pl`, `genericMapping.cgi`), the website's callers (`RefProteomeMapping.java`, `OrganismHelper.java`, `MapOrganism.java`, `GeneListAnalysisAction.java`, `SelectFilesListsServlet.java`, `UploadedFile.java`, `extra.properties.example`, the help pages) and the Phase 1 guides, read-only. Write `docs/parity/refmap-legacy-behaviour.md`: the lookup, what the website called and did with the answer, the data, the quirks `REFMAP-1` to `REFMAP-11` with file and line and a parity call, and the proposed golden inputs. List it in `docs/parity/README.md`. Verify `npx markdownlint-cli2` passes.

## 2. The refmap Input and Result Models

- [x] 2.1 Add `api/src/panther_api/jobs/refmap.py`: `RefmapInput` with the validation in design.md ("Validation, rule by rule"), and `IdMapping` and `RefmapResult` with every field required, nullable where the proposed engine dataclass is. It imports only pydantic. Verify `uv run basedpyright` passes.
- [x] 2.2 Write `api/tests/test_refmap_input.py` for every `scoring-input` refmap scenario, on `RefmapInput`: organism codes accepted; each other shape rejected (lower case, a path, a pipe, a long name, too long, a trailing newline, empty, not a string); no organism; IDs kept unchanged, in order, repeats included; IDs with punctuation accepted; 100,000 IDs and a 64-character ID accepted; 100,001, none, missing and not a list rejected; each bad ID rejected at its index (two IDs, a tab, leading or trailing space, CR, non-ASCII, a control character, 65 characters, empty, not a string); every invalid field listed; an extra field. Each rejection asserts its `loc`, and that no message contains a distinctive part of the value. Verify they pass.

## 3. The refmap Job in the API

- [x] 3.1 Add `RefmapJobRequest` to `JobRequest` and `RefmapResult` to `JobResult` in `jobs/work.py`, with `run_job`'s `refmap` case raising `NotImplementedError`; `RefmapJob` to `Job` in `jobs/models.py`; and, in `routers/jobs.py`, the `501` before `submit`, and a `501` response with the `Problem` model on `POST /jobs` that names `refmap` only. Verify the existing tests still pass.
- [x] 3.2 Write the API tests in `api/tests/test_jobs.py`: an invalid organism (`xyzzy|`: 422 at `["body", "refmap", "input", "organism"]`, the value not in the body, no job); each other field with a distinctive invalid value, at its `loc`; every invalid field listed; a field the input doesn't take; a valid request gets the 501 problem, with no `Location` and no job stored; a `tools` job succeeds after a 501; `run_job` with a `refmap` request raises `NotImplementedError`. Verify they pass.

## 4. The Contract Files

- [x] 4.1 Regenerate `api/openapi.json` (`uv run python -m panther_api.openapi`, from `api/`). Update `api/tests/test_openapi.py`: both unions list `refmap` third with its mapping; the result test covers `RefmapJob`; `RefmapJobRequest` and `RefmapInput` (required fields, no extra properties, the `ids` limits); `RefmapResult` and `IdMapping` (required, `panther_id` a string or null); the `501` documented as a problem that names `refmap` only, replacing the test that there's no `501`. Verify `uv run pytest` passes, including `test_committed_schema_is_current`.
- [x] 4.2 Regenerate the frontend's types: `npm run api:types`, from `frontend/`. Verify `npm run api:types:check`, `format:check`, `lint`, `type-check` and `npm test -- --run` pass, and that only `src/app/api/schema.d.ts` changed in `frontend/` (`git status frontend/`).

## 5. Docs

- [x] 5.1 In `docs/testing/api.md`, add "The refmap Job" to "Try the Jobs by Hand": a valid request and its `501`, an invalid one and its `422`, with `curl`, and the bodies the API returns. In `api/README.md`, add a line for `refmap` and its `501`. Verify `npx markdownlint-cli2` passes.

## 6. Final Check

- [x] 6.1 In `api/`: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest`. In `frontend/`: `npm run api:types:check`, `format:check`, `lint`, `type-check`, `npm test -- --run` and `npm run test:e2e`. From the root: `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive` and `docker build --target api .`. All pass; record the results in Notes.
- [x] 6.2 Against the image, on port 8002 (never 8000): `docker build --target api -t panther-api:refmap .`, then `MSYS_NO_PATHCONV=1 docker run -d --rm --name panther-api-refmap -p 8002:8000 panther-api:refmap`. With the commands in `docs/testing/api.md` against port 8002, a valid `refmap` request gets the `501`, the invalid one gets the `422` without its values, and a `tools` job still reaches `succeeded`. Then `docker stop panther-api-refmap`. Record the result in Notes.

## Workflow follow-up

- Open a pull request with these artifacts and the implementation. Reviewers:
  - the API developer approves;
  - the frontend developer reviews the contract: `RefmapJobRequest`, `RefmapInput`, `RefmapJob`, `RefmapResult`, `IdMapping` and the `501`;
  - **the engine developer reviews the proposed interface** (design.md, decision 3), the input rules against `docs/parity/refmap-legacy-behaviour.md`, and answers the proposal's Open Questions, the organism key first;
  - the engine and API developers decide jobs or synchronous (design.md, decision 1), and the decision is recorded in `docs/design/tech-stack.md`'s `refmap` open questions.
- **The engine developer's port** (a change of its own) adds `panther_engine.refmap.map_ids`, its dataclasses and `ORGANISM_CODES`, the data under `PANTHER_DATA_DIR`, a reference image and the goldens.
- **The wiring change removes the `501`:** it deletes the branch in `routers/jobs.py`, its schema entry and tests; replaces `run_job`'s `refmap` case with an adapter to `map_ids`; checks `organism` against `ORGANISM_CODES`; adds `refmap`'s data version to `Versions.data`; and REMOVES "refmap not available yet" from `scoring-jobs`. An organism list endpoint, for a selector, follows the engine's list, as cSNP's species endpoint does.
- After this merges, archive with `/opsx:archive`.

## Notes

### Next action

Every task is done (2026-10-30) and committed locally on the agent's branch, from `origin/feat/refmap-job` at `32f7299`. Next: the coordinator reviews the commit and opens the pull request (Workflow follow-up); the engine developer answers the proposal's Open Questions.

### Blockers

None for this change. The engine side (`panther_engine.refmap.map_ids`, its organism list, the PANTHER 19 classification files) blocks the wiring change, not this one. The classification files aren't in `panther-workspace`, so nothing about their contents was checked.

### Failed approaches

- **Editing several API files with one inline Python script from the shell (3.1, 2026-10-30)** was refused by the agent's worktree guard as too complex to check. The same edits were made with the file tools.
- **Planning `refmap` in `frontend/src/app/api/wire.ts` (4.2, 2026-10-30).** The brief allowed a frontend change if the new job type broke `type-check`. It didn't: `wire.ts` lists each service's job by hand, so the new schema members never reach its union, and no `refmap` job can exist while the `501` stands. The proposal and design were corrected to "only `schema.d.ts` changes".

### Lessons learned

- **The website didn't normalise refmap input, unlike cSNP's form.** `GeneListAnalysisAction` posted the text box or file as it was, so the API's rules follow the CGI, and are marked new where it had none.
- **The site, not the service, rejected repeated IDs and dropped a first `NOHIT` row** (`UploadedFile.parseIdFamId`). The service returns one row per input line. The JSON contract keeps the service's behaviour; the site's port decides its own handling.
- **The organism key is the contract's riskiest assumption.** The site sent the long name; the contract takes the short code the site's Java derives from it. It's the first open question for the engine developer.
- **Counts (6.1, 2026-10-30):** `api/` 211 passed and 5 skipped (the real `csnp` jobs, without `blastp` natively): 35 in `test_refmap_input.py`, 11 refmap tests in `test_jobs.py`, and 3 new and 4 extended in `test_openapi.py`, where the `501` test replaces "no `501`". Every new test passed on its first run. `frontend/` 187 unit tests and 20 e2e tests, unchanged. `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive` (12 items) and `npx openspec validate add-refmap-job --strict` pass, as does `docker build --target api .`.
- **The image (6.2, 2026-10-30):** `panther-api:refmap` on port 8002. The valid `refmap` request in `docs/testing/api.md` got the `501` problem with no `Location`; the invalid one got the `422` on `organism` and `ids[1]`, without `Homo_sapiens` or `P01023`; a `tools` job reached `succeeded` with `blastp` 2.17.0, `hmmscan` 3.4, `hmmsearch` 3.4 and `epa-ng` 0.3.8; the served schema has the `501` naming `refmap`. The container was stopped.
- **markdownlint's MD038** rejects a code span with a trailing space, such as an ID with one. Say "with a trailing space" in words instead.
