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

## 7. The Engine Developer's Review on #30

- [x] 7.1 Cap a `422`'s errors in `problems._validation_error`: the first 100, each with its `loc`, and the total in `detail` when there are more. Measure 100,000 empty IDs before and after (design.md, decision 7). Add the MODIFIED `api-service` requirement, and tests in `test_problems.py` and `test_jobs.py`. Check that `frontend/` reads only `errors`.
- [x] 7.2 Add proposed rows 9 (`REFMAP-9`) and 10 (`REFMAP-10` and the new ID rules) to `docs/parity/divergences.md`, with no approver, and a footer line for `REFMAP-` IDs. Point the legacy doc's `REFMAP-9` and `REFMAP-10` at them.
- [x] 7.3 In `docs/testing/api.md`, say the refmap contract and input rules are proposed in this change, not settled.
- [x] 7.4 Check the legacy doc against RefProteomeMapper's `master` (`649c85f`), read-only: cite `master` for the CGI's lines, fix where the CGI reads its data (and design.md, decision 3), and say which version production ran needs team verification. Say only the CGI warns on an empty line.
- [x] 7.5 Put `pattern` and `maxLength` on `organism`, and `pattern` on each of `ids`, in the schema only (`json_schema_extra`). Regenerate `api/openapi.json` and the frontend's types, and test that the patterns agree with the validators.
- [x] 7.6 Note beside the `501` in `routers/jobs.py` that the organism check against `ORGANISM_CODES` lands with its removal. (Moved to refmap's row in `UNAVAILABLE` by 7.8.)
- [x] 7.7 design.md: why `id` stays in each mapping, the remaining reasons against `extra`, and the result's size in memory as a known issue for the wiring change. proposal.md: whether `RefmapResult` carries `organism`, as an open question.
- [x] 7.8 The review's optional cleanups, none changing `api/openapi.json`: one `UNAVAILABLE` table in `jobs/work.py`, which `routers/jobs.py` reads for the `501` and its description; `jobs/fields.py` for the printable-ASCII and species-code shapes `csnp.py` and `refmap.py` both check, with cSNP's messages unchanged; and a generic `JobFields` base for the nine job fields, keeping the discriminated union.
- [x] 7.9 Run every check in 6.1, without `test:e2e` and `docker build`, which this review's changes don't reach. Record the results in Notes.

## 8. When Archiving

- [x] 8.1 In `docs/testing/api.md`, "The refmap Job": replace "proposed in `openspec/changes/add-refmap-job/`" with where the contract and input rules then live (`openspec/specs/scoring-jobs/` and `openspec/specs/scoring-input/`), and drop any rule the review changed.

## Workflow follow-up

- Open a pull request with these artifacts and the implementation. Reviewers:
  - the API developer approves;
  - the frontend developer reviews the contract: `RefmapJobRequest`, `RefmapInput`, `RefmapJob`, `RefmapResult`, `IdMapping` and the `501`;
  - **the engine developer reviews the proposed interface** (design.md, decision 3), the input rules against `docs/parity/refmap-legacy-behaviour.md`, and answers the proposal's Open Questions, the organism key first;
  - the engine and API developers decide jobs or synchronous (design.md, decision 1), and the decision is recorded in `docs/design/tech-stack.md`'s `refmap` open questions.
- **The engine developer's port** (a change of its own) adds `panther_engine.refmap.map_ids`, its dataclasses and `ORGANISM_CODES`, the data under `PANTHER_DATA_DIR`, a reference image and the goldens.
- **The wiring change removes the `501`:** it deletes refmap's row in `UNAVAILABLE` (`jobs/work.py`), which takes the `501` and its schema entry with it, and the `501`'s tests; replaces `run_job`'s `refmap` case with an adapter to `map_ids`; checks `organism` against `ORGANISM_CODES` in the same change, never after the `501` goes (the comment on refmap's row says so); stores a large result compactly, and/or caps or shortens how long it's kept (design.md, Risks); adds `refmap`'s data version to `Versions.data`; and REMOVES "refmap not available yet" from `scoring-jobs`. An organism list endpoint, for a selector, follows the engine's list, as cSNP's species endpoint does.
- After this merges, archive with `/opsx:archive`.

## Notes

### Next action

The pull request is #30, under review, with `main` merged in (2026-10-30). The engine developer's review asked for changes; section 7 makes them. Next: the review's fixes are reviewed and pushed, then the engine developer answers the proposal's Open Questions, the organism key first, and approves or rejects divergence rows 9 and 10. Task 8.1 waits for the archive.

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
- **The review's fixes (7.9, 2026-10-30),** after merging `main` (#32): `api/` 245 passed and 5 skipped (the real `csnp` jobs, without `blastp` natively); `uv sync --locked`, `ruff check`, `ruff format --check` and `basedpyright` pass. `frontend/`: `api:types:check`, `format:check`, `lint`, `type-check`, and 205 unit tests pass; `schema.d.ts` doesn't change, since openapi-typescript emits no `pattern` or `maxLength`. `npx markdownlint-cli2`, `npx openspec validate --all` (9 items) and `--strict` on this change pass. Not run: `test:e2e` and `docker build`, which nothing in the review touches.
- **`panther-workspace`'s RefProteomeMapper is behind `master`.** Its checkout is at `4fc6a09`; `master` (`649c85f`) merges `origin/dustine32-config-yaml` (`907fb0d`), whose tree is the same, so `git show 907fb0d:<file>` reads `master` without fetching.
- **A `422`'s size was bounded only by each list's limit.** A list field with a large limit needs the error cap (decision 7); the time Pydantic takes to list every error before the cap is still there.
- **markdownlint's MD038** rejects a code span with a trailing space, such as an ID with one. Say "with a trailing space" in words instead.
