# Tasks

## 1. The Legacy Service, Recorded

- [ ] 1.1 Write `docs/parity/hmmscore-legacy-behaviour.md`, following `docs/parity/README.md`: what `scoreAlignXml.cgi` ran and returned, what the site sent and showed, the quirks `HMMSCORE-1` to `HMMSCORE-10` with file, line and a parity call (design.md, decision 9), the engine developer's character measurements of 2026-11-11, and proposed golden inputs. Link to the survey rather than repeating it. List it in `docs/parity/README.md`. Verify `npx markdownlint-cli2` passes.
- [ ] 1.2 Add two rows to `docs/parity/divergences.md`. 11, approved by the product owner on 2026-11-12: hmmscore takes at most 10,000 residues where the reference took 50,000, expected to cover 99% of queries, and a server's lower value (#68) is recorded in it when set. 12, proposed with no approver: the sequences the API refuses where the reference answered no hit (empty, a character other than a letter, a `*` before the end, `-`, `.`, `_` and `~` included, with the engine developer's 3.1b2 and 3.4 scores), with the website's posting changes and the header after a blank line. Add a footer line for `HMMSCORE-` IDs. Verify `npx markdownlint-cli2` passes.

## 2. The hmmscore Input and Result Models

- [ ] 2.1 Move cSNP's sequence normalising from `api/src/panther_api/jobs/csnp.py` to `jobs/fields.py`, with each service's messages and characters passed in. Verify `uv run pytest tests/test_csnp_input.py` passes unchanged.
- [ ] 2.2 Add `api/src/panther_api/jobs/hmmscore.py`: `HmmscoreInput` with the rules in design.md, decision 3, and `log_summary()`; `HmmHit` and `HmmscoreResult`, every field required, only `hit` nullable. Verify `uv run basedpyright` passes.
- [ ] 2.3 Write `api/tests/test_hmmscore_input.py` for every scenario of `scoring-input`'s hmmscore requirements, the header after a blank line, each rejected character, the final `*` and the 1,000,001 characters that normalise to one residue included. Each rejection asserts its `loc`, and that no message contains a distinctive part of the sequence. Verify they pass.

## 3. The Settings

- [ ] 3.1 Add `hmmscore_max_residues` (10,000, 1 to 10,000), `hmmscore_time_limit_seconds` (720, at least 1), `hmmscore_max_running` (1, at least 1) and `hmmscore_cpu` (0, at least 0) to `api/src/panther_api/settings.py`, each pointing at design.md, decision 5. Pass the residue limit to the router and the cap to `JobRunner`; keep the other two on the app's state for the wiring.
- [ ] 3.2 Extend `api/tests/test_settings.py`: the four defaults, each set from its variable, and each invalid value stopping startup. Verify they pass.
- [ ] 3.3 In `docs/testing/api.md`, list the four variables, their defaults as starting points the server sets (#68), and that the time limit and `--cpu` take effect with the wiring. Verify `npx markdownlint-cli2` passes.

## 4. The hmmscore Job in the API

- [ ] 4.1 Add `HmmscoreJobRequest` and `HmmscoreResult` to the unions in `jobs/work.py`, hmmscore's `UNAVAILABLE` row with a comment on what the wiring adds, `run_job`'s case raising `NotImplementedError`, and `HmmscoreJob` in `jobs/models.py`. In `routers/jobs.py`, check the configured limit after the model and before the `501` (decision 7). Verify the existing tests still pass.
- [ ] 4.2 Add the running cap to `jobs/runner.py`, taken before the worker slot (decision 6). Verify the existing tests still pass.
- [ ] 4.3 Write the tests in `api/tests/test_jobs.py`: two `>` (422, the residues not in the body, no job); no sequence; `opType` as an extra field; 10,000 residues get the `501` and 10,001 the `422` naming 10,000; with the limit at 5,000, 5,000 get the `501` and 5,001 the `422`; a valid request's `501` with no `Location` and no job; a `tools` job after it; `run_job` refusing; the running cap's three scenarios on a `JobRunner` with a stand-in `run_job`. In `test_job_logs.py`, an hmmscore job's line gives its residues only. Verify they pass.

## 5. The Contract Files

- [ ] 5.1 Regenerate `api/openapi.json`, and update `api/tests/test_openapi.py`: both unions list `hmmscore` fourth; the request, input, result and hit components; the `501` naming `hmmscore`. Verify `uv run pytest` passes, `test_committed_schema_is_current` included.
- [ ] 5.2 Run `npm run api:types` in `frontend/`. Verify `api:types:check` and `type-check` pass, and only `schema.d.ts` changed there.
- [ ] 5.3 In `docs/testing/api.md`, add "The hmmscore Job": a valid request and its `501`, a sequence with a digit and its `422`, with `curl`. Add `hmmscore` to `api/README.md` and to `api/CLAUDE.md`, "Adding a Service". Verify `npx markdownlint-cli2` passes.

## 6. Final Check

- [ ] 6.1 In `api/`: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest`. In `frontend/`: `npm run api:types:check`, `type-check` and `npm test -- --run`. From the root: `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive`, `npx openspec validate add-hmmscore-job --strict --no-interactive` and `docker build --target api .`. Record the results in Notes.

## Workflow follow-up

- Reviewers: the API developer approves; the frontend developer reviews the contract; the engine developer reviews decision 4, answers the engine Open Questions, and approves or rejects row 12. The product owner approved row 11 on 2026-11-12. That closes the contract part of #42.
- `port-hmmscore` adds `score()`, its dataclasses, `DATA_VERSION`, `check_data()`, a reference image and the goldens. It, or the server's measuring (#68), times a 10,000-residue query to check the 720 s default (design.md, decision 5). The wiring change then removes the `501`.
- `add-hmmscore-form` (#71) checks the most the setting allows, so its 50,000 becomes 10,000.
- After this merges, archive with `/opsx:archive`.

## Notes

### Next action

The engine developer reviewed #70 on 2026-11-11, and the review is addressed (below). His follow-up and his engine answers (ties, strings, the name) are folded in too, and so is the product owner's residue limit of 2026-11-12: 10,000, with the time limit's default at 720 s. Next: the area owners approve; code starts after.

### Blockers

- None.

### Failed approaches

- **Citing `SequenceSearchForm.java` from a `cat -n` of two files at once (2026-11-10).** `cat -n` numbers lines across files, so every citation was off by `SequenceSearchAction.java`'s 116 lines. Fixed on 2026-11-11; number one file at a time.

### Lessons learned

- **The engine developer's review, 2026-11-11:**
  - split the form into `add-hmmscore-form`;
  - the residue limit defaults to the reference's 50,000 until the product owner answers, and the time limit's default covers it, 3,600 s (since replaced by the product owner's 10,000 and 720 s, below);
  - accept only what `hmmscan` 3.4 reads, from his measurements against 3.1b2 and 3.4;
  - the reference answered no hit, not an error, for a sequence `hmmscan` refused, since `runHmmscan` ignores its exit status; so the `422` is row 12;
  - `DATA_VERSION` is a plain string, `"19"`;
  - ties come from up to 5,279 families, not 5,450;
  - a header after a blank line is where trimming first differs from the website.
- **His follow-up, 2026-11-11:** 3.1b2 split a hit at `.`, `_`, `~` and an inner `*`, as at `-`, and 3.4 doesn't, so only letters and a final `*` are accepted; ties go to the subfamily, then the lowest ID; `evalue` and `score` stay strings; `name` is always a string.
- **The product owner, 2026-11-12, through the engine developer:** hmmscore takes at most 10,000 residues to start, expected to cover 99% of queries. It's the default and the maximum, and row 11 is approved with it. The time limit's default follows, at 720 s: three times about 240 s, scaled from the survey's per-residue times, since no 10,000-residue query was measured.
- **Measure each character in both versions, not only whether it's read.** "Read" by both hid a different score.
- **Check the reference's failure path, not only its success.** "The CGI died" was assumed from a `die`; the line that mattered was the unchecked `system` before it.
- **The CGI's XML is thinner than the site's page:** the name came from the site's database, and the page's "score" was the E-value.
