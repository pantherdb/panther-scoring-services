# Tasks

## 1. The Legacy Service, Recorded

- [x] 1.1 Write `docs/parity/hmmscore-legacy-behaviour.md`, following `docs/parity/README.md`: what `scoreAlignXml.cgi` ran and returned, what the site sent and showed, the quirks `HMMSCORE-1` to `HMMSCORE-10` with file, line and a parity call (design.md, decision 9), the engine developer's character measurements (of 2026-11-13 on amd64, since 7.1), and proposed golden inputs. Link to the survey rather than repeating it. List it in `docs/parity/README.md`. Verify `npx markdownlint-cli2` passes.
- [x] 1.2 Add two rows to `docs/parity/divergences.md`. 11, approved by the product owner on 2026-11-12: hmmscore takes at most 10,000 residues where the reference took 50,000, expected to cover 99% of queries, and a server's lower value (#68) is recorded in it when set. 12, proposed with no approver: the sequences the API refuses where the reference scored them or answered no hit (`-`; no letters; other characters, such as digits and `+`; a `>` inside the sequence, as narrowed in 7.1), with the website's posting changes and the header after a blank line. Add a footer line for `HMMSCORE-` IDs. Verify `npx markdownlint-cli2` passes.

## 2. The hmmscore Input and Result Models

- [x] 2.1 Move cSNP's sequence normalising from `api/src/panther_api/jobs/csnp.py` to `jobs/fields.py`, with each service's messages and characters passed in. Verify `uv run pytest tests/test_csnp_input.py` passes unchanged.
- [x] 2.2 Add `api/src/panther_api/jobs/hmmscore.py`: `HmmscoreInput` with the rules in design.md, decision 3, and `log_summary()`; `HmmHit` and `HmmscoreResult`, every field required, only `hit` nullable. Verify `uv run basedpyright` passes.
- [x] 2.3 Write `api/tests/test_hmmscore_input.py` for every scenario of `scoring-input`'s hmmscore requirements, the header after a blank line, each rejected character, the final `*` and the 1,000,001 characters that normalise to one residue included. Each rejection asserts its `loc`, and that no message contains a distinctive part of the sequence. Verify they pass.

## 3. The Settings

- [x] 3.1 Add `hmmscore_max_residues` (10,000, 1 to 10,000), `hmmscore_time_limit_seconds` (720, at least 1), `hmmscore_max_running` (1, at least 1) and `hmmscore_cpu` (0, at least 0) to `api/src/panther_api/settings.py`, each pointing at design.md, decision 5. Pass the residue limit to the router and the cap to `JobRunner`; keep the other two on the app's state for the wiring.
- [x] 3.2 Extend `api/tests/test_settings.py`: the four defaults, each set from its variable, and each invalid value stopping startup. Verify they pass.
- [x] 3.3 In `docs/testing/api.md`, list the four variables, their defaults as starting points the server sets (#68), and that the time limit and `--cpu` take effect with the wiring. Verify `npx markdownlint-cli2` passes.

## 4. The hmmscore Job in the API

- [x] 4.1 Add `HmmscoreJobRequest` and `HmmscoreResult` to the unions in `jobs/work.py`, hmmscore's `UNAVAILABLE` row with a comment on what the wiring adds, `run_job`'s case raising `NotImplementedError`, and `HmmscoreJob` in `jobs/models.py`. In `routers/jobs.py`, check the configured limit after the model and before the `501` (decision 7). Verify the existing tests still pass.
- [x] 4.2 Add the running cap to `jobs/runner.py`, taken before the worker slot (decision 6). Verify the existing tests still pass.
- [x] 4.3 Write the tests in `api/tests/test_jobs.py`: two `>` (422, the residues not in the body, no job); no sequence; `opType` as an extra field; 10,000 residues, alone or with a final `*`, get the `501` and 10,001 the `422` naming 10,000; with the limit at 5,000, 5,000 get the `501` and 5,001 the `422`; a valid request's `501` with no `Location` and no job; a `tools` job after it; `run_job` refusing; the running cap's three scenarios on a `JobRunner` with a stand-in `run_job`. In `test_job_logs.py`, an hmmscore job's line gives its residues only. Verify they pass.

## 5. The Contract Files

- [x] 5.1 Regenerate `api/openapi.json`, and update `api/tests/test_openapi.py`: both unions list `hmmscore` fourth; the request, input, result and hit components; the `501` naming `hmmscore`. Verify `uv run pytest` passes, `test_committed_schema_is_current` included.
- [x] 5.2 Run `npm run api:types` in `frontend/`. Verify `api:types:check` and `type-check` pass, and only `schema.d.ts` changed there.
- [x] 5.3 In `docs/testing/api.md`, add "The hmmscore Job": a valid request and its `501`, a sequence with a digit and its `422`, with `curl`. Add `hmmscore` to `api/README.md` and to `api/CLAUDE.md`, "Adding a Service". Verify `npx markdownlint-cli2` passes.

## 6. Final Check

- [x] 6.1 In `api/`: `uv sync --locked && uv run ruff check && uv run ruff format --check && uv run basedpyright && uv run pytest`. In `frontend/`: `npm run api:types:check`, `type-check` and `npm test -- --run`. From the root: `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive`, `npx openspec validate add-hmmscore-job --strict --no-interactive` and `docker build --target api .`. Record the results in Notes.

## 7. The Engine Developer's Review on #76

- [x] 7.1 The character rule (engine developer, 2026-11-13): accept letters, `.`, `_`, `~` and `*` anywhere, with at least one letter, in `jobs/hmmscore.py`; a sequence with no letters gets "The sequence has no residues." through `SequenceRules.needs_a_letter` in `jobs/fields.py`, which cSNP leaves unset. Update `scoring-input`'s delta, design.md decision 3, the proposal, `hmmscore-legacy-behaviour.md`'s "The Characters" with the amd64 measurements, row 11's count and row 12, narrowed and still proposed. Verify `test_hmmscore_input.py`, `test_csnp_input.py` unchanged, and `test_jobs.py` pass.
- [x] 7.2 The waiting count in `JobRunner.submit`: a job waiting for its service's running cap counts as waiting; `max_running`'s keys typed as `work.Service`, and checked in `__init__`. Tests on a `JobRunner` with a stand-in `run_job`: the `503` at the right count with a cap of 1, a `tools` job beside waiting hmmscore jobs, a waiting cap of 0, an unknown key. Update the `503`'s description, `docs/testing/api.md` and `scoring-jobs`' delta. Verify they pass, and fail with the old count.
- [x] 7.3 Restore `test_openapi.py`'s check that no `501` is documented once `UNAVAILABLE` is empty, the router reloaded with the table empty. Point `docs/testing/api.md`'s hmmscore input rules at the change's spec delta. Regenerate `api/openapi.json` and `schema.d.ts`, and rerun 6.1's checks but the image build.

## Workflow follow-up

- Reviewers: the API developer approves; the frontend developer reviews the contract; the engine developer reviews decision 4, answers the engine Open Questions, and approves or rejects row 12 as narrowed on #76. The product owner approved row 11 on 2026-11-12; what it counts changed on 2026-11-13 (7.1), and the limit didn't. That closes the contract part of #42.
- `add-hmmscore-form` (#71) follows `scoring-input` as changed in 7.1: `.`, `_`, `~` and `*` accepted, "The sequence has no residues." for no letters, and the residue count.
- `port-hmmscore` adds `score()`, its dataclasses, `DATA_VERSION`, `check_data()`, a reference image and the goldens. It, or the server's measuring (#68), times a 10,000-residue query to check the 720 s default (design.md, decision 5). The wiring change then removes the `501`.
- `add-hmmscore-form` (#71) checks the most the setting allows, so its 50,000 becomes 10,000.
- After this merges, archive with `/opsx:archive`. The archive also points `docs/testing/api.md`'s "The hmmscore Job" back at `openspec/specs/scoring-input/`, which until then has no hmmscore rules.

## Notes

### Next action

The engine developer reviewed #70 on 2026-11-11, and the review is addressed (below). His follow-up and his engine answers (ties, strings, the name) are folded in too, and so is the product owner's residue limit of 2026-11-12: 10,000, with the time limit's default at 720 s. On 2026-11-13, from #71's review, a final `*` stopped counting toward the residue limit, and the Risks name the busy `503`'s `Retry-After`.

Applied on 2026-11-13: every task is done, and 6.1's checks pass. In `api/`: `uv sync --locked`, `ruff check`, `ruff format --check` and `basedpyright` clean, and `pytest` 469 passed, 9 skipped (the `blastp` and refmap-data tests, natively on Windows). In `frontend/`: `api:types:check` and `type-check` pass, and `npm test -- --run` 408 passed in 31 files; only `schema.d.ts` changed there. From the root: `markdownlint-cli2` 0 issues in 201 files, `openspec validate --all` 14 passed (the long-requirement warnings are the main specs', from before), `openspec validate add-hmmscore-job --strict` valid, and `docker build --target api .` built. Next: review in the pull request: the API developer approves, the frontend developer reviews the contract, and the engine developer reviews decision 4 and approves or rejects row 12. Then `/opsx:archive`.

The engine developer reviewed #76 on 2026-11-13, and the review is addressed in group 7: the character rule and row 12 narrowed (still proposed, for him to approve on #76), the residue count, "The sequence has no residues." for no letters, both character tables measured again on amd64, the waiting count with the running cap, typed cap keys, the restored no-`501` test and the doc link. 7.3's checks pass: in `api/`, `uv sync --locked`, `ruff check`, `ruff format --check` and `basedpyright` clean, and `pytest` 491 passed, 9 skipped; in `frontend/`, `api:types:check` and `type-check` pass, and `npm test -- --run` 408 passed in 31 files, only `schema.d.ts` changed there; from the root, `markdownlint-cli2` 0 issues in 202 files, `openspec validate --all` 14 passed, and `openspec validate add-hmmscore-job --strict` valid. The image wasn't rebuilt: no dependency or `Dockerfile` changed. Next: the engine developer approves row 12 on #76.

Decided while applying, for the reviewers:

- **The shared normalising** is `fields.normalise_sequence()` with a `SequenceRules` of each service's characters and messages; `LONGEST_RAW_SEQUENCE` moved to `fields.py` with it. cSNP's length check stays in `csnp.py`.
- **A lone `*`,** as in `">only a header\n*"`, gets "The sequence has no residues." since 7.1, as does any sequence of `.`, `_`, `~` and `*` without a letter. A sequence with no letters and a refused character, such as `*-1`, gets the characters message: the character check comes first.
- **The router reads the residue limit from the app's settings** (`app.state.settings`), where the time limit and `--cpu` also wait for the wiring; `JobRunner` takes the cap as `max_running={"hmmscore": …}`.
- **The hmmscore log-line test lifts the `501`** for that test (`monkeypatch.delitem(UNAVAILABLE, "hmmscore")`) and stands in for the work, so the line comes through the real router and runner.
- **Row 12 doesn't list more than one `>`:** the website refused that too, so it isn't a difference. A single `>` inside the sequence, which the website passed, is in it (7.1).
- **The no-letters check is opt-in** (`SequenceRules.needs_a_letter`): cSNP's printable characters accept a sequence with no letters, such as `123`, and its behaviour and messages stay as they were.
- **The no-`501` test reloads `routers/jobs.py`** with `UNAVAILABLE` emptied, since the router documents the `501` when it's imported, and reloads it again afterwards with the table back (7.3).
- **The refusal's log line still gives every unfinished job** as "running or waiting"; only the decision to refuse changed (7.2).

### Blockers

- None.

### Failed approaches

- **Citing `SequenceSearchForm.java` from a `cat -n` of two files at once (2026-11-10).** `cat -n` numbers lines across files, so every citation was off by `SequenceSearchAction.java`'s 116 lines. Fixed on 2026-11-11; number one file at a time.
- **Editing Python through a Git Bash heredoc (2026-11-13).** A quoted heredoc still turned `\n` and `\t` inside a script's strings into real line breaks and tabs, which broke `fields.py`'s patterns. Use the editor, or a script file, for text with backslashes.

### Lessons learned

- **The engine developer's review, 2026-11-11:**
  - split the form into `add-hmmscore-form`;
  - the residue limit defaults to the reference's 50,000 until the product owner answers, and the time limit's default covers it, 3,600 s (since replaced by the product owner's 10,000 and 720 s, below);
  - accept only what `hmmscan` 3.4 reads, from his measurements against 3.1b2 and 3.4;
  - the reference answered no hit, not an error, for a sequence `hmmscan` refused, since `runHmmscan` ignores its exit status; so the `422` is row 12;
  - `DATA_VERSION` is a plain string, `"19"`;
  - ties come from up to 5,279 families, not 5,450;
  - a header after a blank line is where trimming first differs from the website.
- **His follow-up, 2026-11-11:** ties go to the subfamily, then the lowest ID; `evalue` and `score` stay strings; `name` is always a string. Its character rule, only letters and a final `*`, came from measurements he withdrew on #76 (7.1).
- **The product owner, 2026-11-12, through the engine developer:** hmmscore takes at most 10,000 residues to start, expected to cover 99% of queries. It's the default and the maximum, and row 11 is approved with it. The time limit's default follows, at 720 s: three times about 240 s, scaled from the survey's per-residue times, since no 10,000-residue query was measured.
- **Measure each character in both versions, not only whether it's read.** "Read" by both hid a different score.
- **Check the reference's failure path, not only its success.** "The CGI died" was assumed from a `die`; the line that mattered was the unchecked `system` before it.
- **The CGI's XML is thinner than the site's page:** the name came from the site's database, and the page's "score" was the E-value.
- **From reading the legacy code for 1.1 (2026-11-13):** `panther-site-java/scoring/scoreAlignXml.cgi` reads `./PANTHER7.2` with HMMER2, so it's most likely not what PANTHER 19 ran; `pantherScore.pl` reads `-c` but never passes `--cpu`; and the website's form checked emptiness before normalising, so a sequence of only a header reached the CGI empty. All are in `docs/parity/hmmscore-legacy-behaviour.md`.
- **Test a cap by taking it away.** The three running-cap tests fail with the cap replaced by `nullcontext()`, and the one beside a tools job fails too if the cap were taken after the worker slot.
- **The engine developer's review on #76, 2026-11-13:**
  - the characters he measured on 2026-11-11 ran on a Mac build of 3.1b2 for CPUs without SSE (`impl_dummy`), which split hits; on amd64, 3.1b2 and 3.4 score `.`, `_`, `~` and an inner `*` alike, so they're accepted, and row 12 narrows to `-`, no letters, other characters and a `>` inside the sequence;
  - the residue limit counts every position `hmmscan` reads but a final `*`;
  - the waiting count treated an hmmscore job waiting for the cap as running, so with the defaults 52 were taken and a cSNP job then waited behind about 51 of them;
  - a misspelled `max_running` key left the service uncapped;
  - the test that no `501` is documented once every service runs had gone with hmmscore's row.
- **Measure on the platform production ran.** A build's fallback code path gave different scores; the amd64 SSE build is the one to compare.
- **A second limit changes what the first counts.** The waiting count assumed every worker takes the next job; a running cap breaks that, so count what can run: min(workers, Σ min(unfinished, cap)).
