# Tasks

Test-first: for each task, write its tests from the spec scenarios, run them and see them fail for the right reason, then write the code. Record each red run in the Notes.

## 1. The cSNP Input and Result Models

- [x] 1.1 Write `api/tests/test_csnp_input.py` for every `scoring-input` scenario, on `CsnpInput` in the test process: the normalised sequence ("FASTA header and line breaks", "Lower case and spaces"), each rejected sequence ("Only a header", "Two sequences", "Too long", "Not printable ASCII", and a raw value over 1,000,000 characters), "Longest sequence"; the substitutions ("Valid tokens, upper-cased", "Tokens that aren't substitutions are kept", "No substitutions", "Too many substitutions", "A token that isn't one token"); the species ("A species code", "Not a species code", "No species"); and an extra field. Each rejection asserts the error's `loc`, and that its `msg` doesn't contain the value. Run them and verify they fail first, because `panther_api.jobs.csnp` doesn't exist.
- [x] 1.2 Add `api/src/panther_api/jobs/csnp.py`: `CsnpInput` with the validation in design.md ("Validation, rule by rule"), and `SubstitutionScore` and `CsnpResult` with every field required and nullable where the engine's is. It imports only pydantic. Verify 1.1's tests pass, and `uv run basedpyright` passes.

## 2. The cSNP Job in the API

- [x] 2.1 Write the API tests in `api/tests/test_jobs.py`:
  - "Invalid species" (`xyzzy;id`: 422, one error at `["body", "csnp", "input", "species"]`, `xyzzy` not in the body, no job stored);
  - a distinctive invalid value for each other field (`sequence` with two `>` and `xyzzy`, a `substitutions` token `xyzzy xyzzy`), each a 422 at its `loc` without the value;
  - "Every invalid field is listed" and "A field the input doesn't take";
  - "A valid cSNP request": 501, `application/problem+json`, the detail, and the store's job count unchanged;
  - "Tools jobs still run" after a 501;
  - `run_job` with a `csnp` request raises `NotImplementedError`.

  Run them and verify they fail first: the `csnp` requests get a 422 for an unknown `service`, and `run_job` can't be given one.
- [x] 2.2 Add `CsnpJobRequest` to `JobRequest` and `CsnpResult` to `JobResult` in `jobs/work.py`, with `run_job`'s `csnp` case raising `NotImplementedError`; `CsnpJob` to `Job` in `jobs/models.py`; and the `501` in `routers/jobs.py`, before `submit`. Verify 2.1's tests pass, and the existing ones still do.

## 3. The Contract Files

- [x] 3.1 Write the schema tests in `api/tests/test_openapi.py`: the request union is `oneOf` `ToolsJobRequest`, `CsnpJobRequest` with mapping `tools` and `csnp`; the job union likewise with `ToolsJob` and `CsnpJob`; "The result in the schema" (`CsnpJob.result` is `CsnpResult` or null, `family` required and nullable, `SubstitutionScore` requiring all four fields with `age` integer or null and `pdel` string or null); "Documented in the schema" (`POST /api/v1/jobs` has a 501 with the `Problem` schema under `application/problem+json`). Update the existing union tests for the second member. Run them and verify they fail first where 2.2 didn't already build the contract, and that `test_committed_schema_is_current` fails until the schema is regenerated.
- [x] 3.2 Document the `501` on `POST /jobs`, then regenerate `api/openapi.json` (`uv run python -m panther_api.openapi`, from `api/`). Verify 3.1's tests pass.
- [x] 3.3 Regenerate the frontend's types: `npm ci` if needed, then `npm run api:types`, from `frontend/`. Verify `npm run api:types:check`, `npm run type-check` and `npm test` pass in `frontend/`, and that nothing else in `frontend/` changed (`git status frontend/`).

## 4. Docs

- [x] 4.1 In `docs/testing/api.md`, add a cSNP subsection to "Try the Jobs by Hand": a valid request and its `501`, an invalid one and its `422`, both with `curl`. In `api/README.md`, add a line for the `csnp` job. Verify `npx markdownlint-cli2` passes.

## 5. Final Check

- [x] 5.1 In `api/`: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest`. In `frontend/`: `npm run api:types:check`, `npm run type-check` and `npm test`. From the root: `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive`. All pass.
- [x] 5.2 Against the image: `docker compose up --build -d api`, then, with the commands in `docs/testing/api.md`, a valid `csnp` request gets the `501`, an invalid one gets the `422` without the submitted value, and a `tools` job still reaches `succeeded`. Then `docker compose down`. Record the result in Notes.

## 6. The Engine Developer's Review (#19, 2026-10-30)

- [x] 6.1 Reject a substitution token that, once upper-cased, doesn't match the legacy CGI's `[A-Z][0-9]+[A-Z]`, in place of keeping it. Test-first: in `tests/test_csnp_input.py`, the "Tokens that aren't substitutions are kept" test becomes a rejection test, with an error on the token's index and its value not in the message. Cover letters only, no mutant, `|` or `*` as the mutant, two wild-type residues, no wild-type residue, `-`, `.`, and a non-ASCII letter that upper-cases to ASCII. Add a test that tokens in the form that can't be mapped (`G99999R`, `M1P`, `a10v`) are still accepted. Verify the new rejection tests fail first, then pass. Update the `scoring-input` spec ("Tokens that aren't substitutions are rejected", "Substitutions that can't be mapped are accepted"), design.md's rule table and Risks, and proposal.md's answered Open Questions. Then regenerate `api/openapi.json` and `frontend/src/app/api/schema.d.ts` (the input's description changed), and verify that the API checks and the frontend's `api:types:check`, `type-check` and `npm test` pass.

## Workflow follow-up

- Open a pull request with these artifacts and the implementation. Reviewers:
  - the API developer approves;
  - the frontend developer reviews the contract: `CsnpJobRequest`, `CsnpInput`, `CsnpJob`, `CsnpResult`, `SubstitutionScore` and the `501`;
  - **the engine developer reviews the input rules** (design.md, "Validation, rule by rule") against the legacy behaviour spec and the parity review, and answers the proposal's Open Questions.
- **The port's API change removes the `501`:** it deletes the branch in `routers/jobs.py`, its schema entry and its tests; replaces `run_job`'s `csnp` case with the adapter to `panther_engine.csnp.score`; checks `species` against the engine's exported list; does add-job-input-errors group 2; and REMOVES "cSNP scoring not available yet" from `scoring-jobs`.
- After it merges, archive with `/opsx:archive`, which creates `openspec/specs/scoring-input/spec.md`.

## Notes

### Next action

Every task is done (2026-10-29) and committed locally on the agent's branch, from `origin/main` at `f1c711b`. Next: open the pull request (Workflow follow-up), and have the engine developer review the input rules and answer the proposal's Open Questions.

### Blockers

None for this change. The engine side (`panther_engine.csnp.score`, its species list, `InputError`) blocks the port's API change, not this one.

### Failed approaches

- **A heredoc rewrite of `api/src/panther_api/jobs/work.py` and of the tests from the shell (2.1, 2026-10-29)** was refused by the agent's worktree guard as too complex to check. The same edits were made with the file tools.
- **The first mutant for 3.1 (2026-10-29)** renamed the `501` key to a string, which crashed FastAPI at import (`int('MUTANT501')`) instead of failing the assertion. A `503` key in its place was the useful mutant (below).

### Lessons learned

- **Red runs, test-first (2026-10-29).**
  - **1.1:** `test_csnp_input.py` failed to collect: `No module named 'panther_api.jobs.csnp'`. After 1.2, two cases failed on the tests themselves: the species message names `HUMAN` as an example, so `HUMAN` can't be the "not echoed" marker. The markers became `''` and `XYZZY`; `XYZZY\n` still checks that a trailing newline is rejected (`re.fullmatch`, not `$`, which matches before a final newline).
  - **2.1:** first a collection error (no `CsnpJobRequest` in `work.py`). With the request in the union but no `501`, the two `501` tests failed because the valid `csnp` request **was stored as a job**, and then couldn't be rendered (`union_tag_invalid` for `ToolsJob`). That's what the `501` prevents. The `422` tests passed once `CsnpInput` was in the union: validation is the model's.
  - **3.1:** the new schema tests passed at once, because 2.2 built the contract and the `501` entry; `test_committed_schema_is_current` was red until 3.2 regenerated the schema, and the three union tests were red until updated for the second member. A mutant (the `501` entry moved to `503`) made `test_the_csnp_501_is_documented` fail with `KeyError: '501'`, and was reverted.
- **Counts:** `api/` 137 tests (48 in `test_csnp_input.py`, 11 new in `test_jobs.py`, 4 new or extended in `test_openapi.py`); `frontend/` 13 tests, unchanged.
- **The legacy drops malformed tokens; it doesn't reject them.** `snpScore.cgi` line 212 writes only tokens matching its regex; the rest get no row. "Not scored: Invalid substitution" is only for tokens that match but can't be mapped (`PANTHER_PSEP1.01.pl` 74 to 86). The API first kept every token. After the engine developer's review on #19 (2026-10-30), it rejects them with a `422`, since a dropped token was never scored (task 6.1).
- **The review's red run (6.1, 2026-10-30).** 8 of the 9 new rejection cases failed with "DID NOT RAISE ValidationError": the token was kept. The ninth, a dotless i that `str.upper()` turns into an ASCII `I`, was already rejected by the printable-ASCII check, which runs before upper-casing. Green after the change: 146 API tests. Ruff's `RUF001` flags a literal dotless i in a test, so the test builds it with `chr(0x131)`.
- **The website, not the CGI, normalised the input** (`CsnpScoreForm.java`): trim, upper-case, one header, whitespace, 50,000 residues, at most one `>`. The API does the same, so the engine receives what the legacy scripts received.
- **The frontend's types (3.3):** `npm run api:types` added the five components and the `501`; `type-check` and the 13 tests passed with no other change in `frontend/`.
- **The image (5.2, 2026-10-29):** `docker compose up --build -d api` from this worktree, on port 8000. The valid `csnp` request in `docs/testing/api.md` got the `501` problem; the invalid one got the `422` listing `substitutions` and `species`, without `human; id`; a `tools` job reached `succeeded` with `blastp` 2.17.0, `hmmscan` 3.4, `hmmsearch` 3.4 and `epa-ng` 0.3.8. `docker compose down` removed it.
