# Whole-Repository Review at `64174c9`, 2026-10-30

**Reviewed:** the whole repository. That's `engine/`, `api/` and `frontend/`; the images, compose and CI; and the specs, the divergence log and the docs, checked against the code.

**Commit:** `main` at `64174c9` (#49). Since the earlier draft review at `13d97b3`, `main` has gained:

- the refmap job contract (#30), including the 100-error cap on a `422`;
- `api/CLAUDE.md` (#47);
- two `CLAUDE.md` corrections (#49).

`engine/` is unchanged since then, and so is `frontend/`, except the generated `schema.d.ts`. Two pull requests merged after this commit aren't covered; see "After `64174c9`" near the end.

**Reviewer:** dustine32.

**How it was checked:** each area had its own review pass:

- the cSNP port, against the Perl at `cebb5ab`;
- the engine's core and data tooling;
- the API, and the contracts between areas;
- the frontend;
- the images, CI and docs;
- the specs, against the code and tests.

Every finding was then checked again against the code at `64174c9`, and each one says how:

- **reproduced:** run, with the result given;
- **traced:** the code path read end to end;
- **suspected:** plausible, not confirmed.

No code was changed. Experiments ran in a scratch folder outside the repository. Images ran with the working copy mounted read-only, and GitHub was only read.

**Earlier draft:** `2026-10-30-whole-repo-review.md`, untracked, written at `13d97b3`. All 48 of its findings were re-checked here, and every one still holds. Five are raised in severity, and one of its claims was wrong; "Earlier Findings at `64174c9`" has the details. This review supersedes it.

## Summary

The code is in good shape for where the project is.

- **Checks:** every suite passes, natively and in the images with the tools and data. Lint, format, strict types, markdownlint and `openspec validate` are clean.
- **cSNP parity:** the port reproduces every golden. A fresh fuzz of step 2 (2,601 SNP records) and a new seeded step-3 run (4,245 cases), both against the Perl, found no difference.
- **The form against the API:** the form's checks agree with the API's own validators on 20,001 random drafts, except for one contrived case (FE-13).
- **Specs:** no requirement in the seven main specs is unimplemented.

The Medium findings:

- **cSNP (CSNP-1 to CSNP-4):**
  - one BLAST+ 2.17.0 line at an identity tie fails the whole job;
  - a protein submitted with a species other than its best match's gets "No PANTHER family", and the form defaults to HUMAN. Parity holds here, so it's a question for the science owner;
  - a missing library gives plausible "not scored" answers instead of an error;
  - titin uses 91% of the BLAST+ time limit.
- **BLAST+ and NCBI (ENG-1):** every `blastp` run contacts NCBI. That adds about 10 seconds to each job wherever outbound traffic is dropped, and reports usage wherever it isn't.
- **API limits:** nothing bounds a request's size (API-1) or the number of queued jobs (API-2).
- **CI on `main` (REPO-2):** CI cancels merge runs on `main` and never re-runs them, so `64174c9` itself never had its frontend or image jobs run after merging.
- **Frontend:**
  - one malformed API response replaces every page with React Router's developer error screen, stack trace included (FE-1);
  - field errors fail WCAG AA contrast (FE-2).

Decisions the team owes, each of which blocks work:

- refmap's divergence rows 9 and 10, which merged without an approver (SPEC-1);
- refmap's data layout, and whether it runs as a job or synchronously (SPEC-5);
- for the science owner: the species filter (CSNP-2), and who approves divergence rows, row 1 included (SPEC-4).

Several Medium findings take a line or two to fix:

- ENG-1: `BLAST_USAGE_REPORT=false`;
- REPO-2: `cancel-in-progress` for pull requests only;
- FE-1: an `errorElement`;
- CSNP-1: the identity formula, plus a test.

| Severity | Repository, images and CI | API | cSNP port | Engine core and tooling | Frontend | Specs and process | Total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Medium | 1 | 2 | 4 | 1 | 2 | 0 | 10 |
| Low | 8 | 7 | 3 | 10 | 10 | 6 | 44 |
| Nit | 2 | 6 | 4 | 12 | 5 | 0 | 29 |
| Total | 11 | 15 | 11 | 23 | 17 | 6 | 83 |

Of the 83 findings, 36 are new, and 47 carry over the earlier draft's findings.

## Checks Run

All on 2026-10-30, at `64174c9`.

| Area | Where | Checks | Result |
| --- | --- | --- | --- |
| `engine/` | Natively on macOS, without BLAST+ | `uv lock --check`, `ruff check`, `ruff format --check`, `basedpyright`, `pytest` | All clean. 396 passed, 21 skipped: they need `blastp`, `blastdbcmd` or `epa-ng` |
| `engine/` | The engine image, working copy mounted read-only, `PANTHER_REQUIRE_DATA=1` | `pytest`; compose's own command (lint, format, types, tests) | 417 passed; compose's command clean, with nothing written to the mount |
| `api/` | Natively | `uv lock --check`, `ruff check`, `ruff format --check`, `basedpyright`, `pytest` | All clean. 245 passed, 5 skipped: they need `blastp` |
| `api/` | The API image, by the command in `docs/testing/api.md`, `PANTHER_REQUIRE_TOOLS=1`, `PANTHER_REQUIRE_DATA=1` | `pytest` | 250 passed |
| `api/` | The API image built at `64174c9`, then removed | CI's `api-image` checks, run by hand | Pass: four tool versions, and P26439's scores match spec §7.3 |
| `frontend/` | Natively, on Node 25.0.0 (`.nvmrc` pins 24, which isn't installed here) | `api:types:check`, `format:check`, `lint`, `type-check`, `test`, `vite build`, `npm audit --omit=dev` | All clean. 205 passed; 0 vulnerabilities. The build warns of one 586 kB chunk |
| Root | Natively | `npm ci`, `markdownlint-cli2`, `openspec validate --all`, `npm audit` | 0 issues in 131 files. 10 items valid, with 4 warnings for requirement text over 500 characters. `npm audit` reports 3 high and 2 low (REPO-7) |

Playwright wasn't run: no browsers are installed here.

## Findings

Most severe first. Each ID names an area:

- **REPO:** the repository, images, CI and gates;
- **API;**
- **CSNP:** the cSNP scoring port;
- **ENG:** the engine's core and data tooling;
- **FE:** the frontend;
- **SPEC:** specs and process.

"Earlier" gives the draft's ID for a finding it already had.

### Medium

#### CSNP-1. One BLAST+ 2.17.0 line at an identity tie fails the whole job

- **Files:** `engine/src/panther_engine/csnp/hits.py:153-170`, and `engine/src/panther_engine/csnp/parity.py:164`. In `hits.py`, the formula is at 162, the raise at 165-169, and `ranked()` calls it for every line at 147.
- **Checked:** reproduced. **Earlier:** M1.
- **What's wrong:**
  - `two_decimals` recomputes each line's identity as `100 * identities / length`, and raises `BlastError` unless the result matches BLAST+'s own three-decimal value.
  - BLAST+ 2.17.0 computes `identities / length * 100`, which rounds twice. At exact three-decimal ties the strings differ, in either direction.
  - Every line of the output is checked, for every species, so one such line fails the job with the generic 500.
  - `parity.py`'s case generator uses the port's formula. So neither the goldens nor the unit tests can catch the difference.
- **What could go wrong:**
  - **Crafted lines:** eight ungapped pairs were run through `blastp -subject`: 161/320, 199/320, 201/320, 402/640, 603/960, 804/1280, 1005/1600 and 1021/1600.
    - BLAST+'s value equalled `n / L * 100` in all eight, and the port's formula in none.
    - For 199/320, BLAST+ writes `62.187` and the port computes `62.188`.
    - Fed to `hits.parse`, the 201/320 line raised `BlastError: the identity 62.813 isn't 100 * (length - mismatch - gaps) / length = 62.81250`.
  - **Exposure:**
    - Up to length 10,000, only alignment lengths that are multiples of 320 are at risk: 31 lengths, and 1,343 identity counts.
    - At every such length but 8,000, the identities at risk are at most 63.81%.
    - 550 real human queries against the full database gave 1,955 lines, and none was at risk: the best-hit filter kept only lines at 64% identity or more.
    - So the queries at risk are those whose best hits are distant homologs.
  - **Suspected:** the two-decimal value used for ranking (`MAP-1`) has the same mismatch at multiples of 160. Which BLAST+ version the legacy ran is unknown.
- **Fix:**
  - compute `(length - mismatch - gaps) / length * 100` in both places;
  - add a test with a real 2.17.0 tie line, such as the 201/320 one;
  - correct `port-csnp`'s design note, which says the formula was checked "on every line".

#### CSNP-2. A protein submitted with any species but its best match's gets "No PANTHER family", and the form defaults to HUMAN

- **Files:**
  - `engine/src/panther_engine/csnp/blast.py:20` (`OPTIONS`);
  - `engine/src/panther_engine/csnp/hits.py:115-136`, with the species filter at 121;
  - the legacy `run_blastp.pl:22` and `parse_blastp.pl:41-44`;
  - the form's default species, `frontend/src/features/csnp/draft.ts:39`.
- **Checked:** reproduced. New.
- **Parity holds.** The legacy pipeline does the same, so this is a question for the science owner, not a porting bug. It isn't in the legacy spec's §6, the parity review, the library survey or the earlier draft.
- **What's wrong:**
  - `-best_hit_overhang 0.1 -best_hit_score_edge 0.1` make BLAST+ drop every hit that a much better hit covers, across subjects and species.
  - Step 2's species filter then sees only what's left. Other species' orthologs are already gone before it runs.
- **What could go wrong:**
  - **P26439** (human, `PTHR10366`), scored as MOUSE or RAT, has no family. Every substitution is "Not scored: No PANTHER family for input sequence"; this was re-run for this review.
    - With the legacy options, BLAST+ keeps 5 lines, all from primates.
    - Without them, it returns 506 lines, including 12 mouse hits in `PTHR10366` at 70.9% identity over 371 residues.
  - **Mouse P24815**, submitted with the default HUMAN, gets "No PANTHER family": BLAST+ keeps only the protein's own mouse entry.
  - **100 mouse proteins** that have a family were sampled: every 40th mouse entry of 200 to 600 residues. For 69 of them, BLAST+ keeps no human line, so under the default species they would all come back "No PANTHER family".
  - The answer reads as a fact about the protein, when it's really about the species chosen.
- **Fix:** the science owner's call, and any changed score needs a divergence row. Two options:
  - filter by species before the best-hit step: search without `-best_hit_*`, then filter;
  - or keep the scores, and say in the result that the best hit was in another species, so the user can correct it. This one changes no score.

#### CSNP-3. A missing or partial library gives a family and "No PANTHER family" answers, not an error

- **Files:** `engine/src/panther_engine/csnp/psep.py:363-370`, with the `.exists()` check at 367.
- **Checked:** reproduced; the earlier draft only traced it. **Earlier:** M3.
- **What's wrong:**
  - Whether a family is scored depends only on its `.paml` existing, as with the Perl's `-e`. Thousands of families legitimately have none.
  - Nothing in the engine or the API checks that the library or the species file is there at all.
- **What could go wrong:**
  - With a data folder that held only `csnp/9/blast/`, scoring P26439 (`A10E`, `G15D`) returned family `PTHR10366`, with both substitutions "Not scored: No PANTHER family for input sequence", and no error.
  - So a volume that fails to mount, or a copy of the 19.2 GB library that stops halfway, gives every job a plausible answer.
- **Fix:**
  - fail with an engine error when `PAML_RST/` or the species file is missing;
  - check the installed library against a manifest at startup, or in a readiness check. `core/manifest.py` already does this for the sample.

#### CSNP-4. The 300-second BLAST+ limit leaves titin 9% headroom

- **Files:** `engine/src/panther_engine/csnp/blast.py:24-25`.
- **Checked:** reproduced. **Earlier:** M2.
- **What's wrong:**
  - `TIMEOUT = 300.0` is the only time limit; the API has none per job. The comment above it says the search "takes seconds".
  - `blastp` runs on one thread, as the legacy did, and its time grows with the query's length. The API accepts up to 50,000 residues.
- **What could go wrong:**
  - Titin (Q8WZ42, 34,350 residues) is a common target for clinical variants. Through `score()` in the engine image, on one Apple Silicon core, it took 272 s: 91% of the limit. The earlier draft measured 266.9 s.
  - On slower server cores or under load, every titin job would fail with the generic 500. ENG-1's 10 seconds bring it closer still.
  - An average human protein takes 4 to 6 s.
- **Fix:** measure titin on the production hardware. Then raise the limit or scale it with the query's length, and make it configurable.

#### ENG-1. Every `blastp` run contacts NCBI, which adds about 10 seconds where outbound traffic is dropped

- **Files:**
  - `Dockerfile:88-104`: the `tools` stage sets no `BLAST_USAGE_REPORT`;
  - `engine/src/panther_engine/core/process.py:33-43`: the child inherits the whole environment;
  - the callers: `engine/src/panther_engine/csnp/blast.py:61`, `engine/src/panther_engine/core/tools.py:61` and `api/src/panther_api/main.py:39`.
- **Checked:** reproduced three ways. **Earlier:** L4, raised from Low.
- **What's wrong:** BLAST+ 2.17.0 sends a usage report to `www.ncbi.nlm.nih.gov` on every run, `-version` included, unless `BLAST_USAGE_REPORT=false`. Nothing in the repository sets it.
- **What could go wrong:**
  - **Where outbound traffic is dropped:**
    - With NCBI unreachable (`--add-host www.ncbi.nlm.nih.gov:10.255.255.1`), `blastp -version` took 11.1 s, against 0.5 s with the variable set.
    - With DNS unanswered, an APOE search took 14 s, against 4 s.
    - So where a host silently drops outbound traffic, a common container setting, each of these waits about 10 s more: the API's start, which reads the tool versions; every `tools` job; and every `csnp` job.
  - **Where it's allowed:**
    - Starting the API and running one `tools` job made 4 DNS lookups for NCBI.
    - A search opened TLS to `www.ncbi.nlm.nih.gov:443`.
    - So the server reports usage to a third party for every user's job.
- **Fix:**
  - `ENV BLAST_USAGE_REPORT=false` in the `tools` stage, which every image inherits;
  - set it in the engine's tool runner too, so native runs are covered (Improvements);
  - a test that it's set.

#### API-1. The API reads a request body in full before any size limit applies

- **Files:**
  - `api/src/panther_api/jobs/csnp.py:20-27, 94-98`;
  - `api/src/panther_api/jobs/refmap.py:25-28, 82`;
  - `api/src/panther_api/main.py`;
  - `Dockerfile:168`.
- **Checked:** traced at this commit. The earlier draft reproduced it: one 200 MB request took the process from 78 MB to 1,016 MB before its 422. **Earlier:** M4.
- **What's wrong:**
  - The input limits are Pydantic checks. They run after Starlette has read the whole body and decoded the JSON.
  - Neither the app nor `fastapi run` limits a body's size, and no proxy is defined yet.
- **What could go wrong:** a few large requests at once can exhaust the container's memory. The API is then killed, and every job in its in-memory store goes with it.
- **New since the draft:** refmap raises the largest valid body.
  - 100,000 IDs of up to 64 printable characters come to about 13 MB of JSON, since each `"` or `\` is escaped as two characters.
  - With typical 10-character accessions, it's about 1.4 MB.
  - The draft's suggested cap of a few MB would refuse valid refmap requests.
- **Fix:**
  - refuse a body over a bound that fits the largest valid request, such as 16 MB, both by `Content-Length` and by counting what's streamed, in a middleware or at the proxy;
  - record the bound in the deployment runbook.

#### API-2. Nothing limits how many jobs can wait

- **Files:** `api/src/panther_api/jobs/runner.py:52-69`, `api/src/panther_api/jobs/store.py:69-75`.
- **Checked:** traced; the code hasn't changed since the earlier draft. The draft reproduced it: 1,000 submissions were accepted with 202 in 0.9 s, and 999 were left `queued` behind one worker. **Earlier:** M5.
- **What's wrong:**
  - Every valid `POST /api/v1/jobs` stores a job and starts a task that waits for a worker.
  - Nothing bounds how many wait, per client or in total.
  - The API never answers 429 or 503.
- **What could go wrong:**
  - One client can delay everyone else's jobs by tens of minutes.
  - Every queued job holds its input in memory: with refmap, up to 100,000 IDs per job.
- **Fix:**
  - a configurable cap on queued jobs, answered with 503 and `Retry-After`;
  - a per-client limit at the proxy.

  It's new behaviour, so it needs a `scoring-jobs` requirement.

#### REPO-2. CI cancels merge runs on `main` and never re-runs them, so `64174c9` never had its frontend or image jobs run after merging

- **Files:**
  - `.github/workflows/ci.yml:23-25`: `cancel-in-progress` applies to every ref, `main` included;
  - `.github/workflows/ci.yml:42-72`: on a push, the path filter compares only with the previous commit;
  - `.github/rulesets/main.json:29`: `strict_required_status_checks_policy: false`.
- **Checked:** reproduced with `gh run list` and `gh run view`. **Earlier:** L1, raised from Low.
- **What's wrong:**
  - A second merge cancels the first merge's run. The second run checks only its own diff, so the jobs the cancelled run would have run never run.
  - With non-strict checks, nothing tests the combined tree of two back-to-back merges.
- **What could go wrong:**
  - **#30's merge** (`8450485`, the refmap job): run 41163621078 had its `frontend` and both `api-image` jobs cancelled when #49 merged 46 seconds later.
  - **`64174c9` itself:** run 41163673692 ran only `repo`. So `64174c9` shows green, but its frontend and its API image were never checked on `main`.
  - **Before and after:** it happened earlier with #24's merge (run 41127399319: `engine`, `engine-image` and `api-image` cancelled), and again after this commit with #50's.
  - **Today:** nothing is broken. The image jobs' checks pass at `64174c9` when run by hand, and so do the frontend's.
  - **The risk:** two merges can each be green against an older `main`, yet conflict with each other, for example one changing `api/openapi.json` and the other the frontend's use of it. `main` is then broken and still green.
- **Fix:**
  - `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`;
  - on a push to `main`, run every area job;
  - optionally, strict checks or a merge queue.

#### FE-1. One rendering error replaces every page with React Router's developer screen, stack trace included, in production

- **Files:** `frontend/src/app/router.tsx:11-21`, where no route has an `errorElement`, and `frontend/src/components/VersionList.tsx:13-21`.
- **Checked:** reproduced. **Earlier:** L23, raised from Low: its trigger is now reproduced, and it takes the whole page.
- **What's wrong:**
  - Any exception while rendering falls through to React Router's default error screen.
  - `react-router` 7.18.5 exports only its development build, so the production bundle includes that screen; "Hey developer" is in the built JavaScript.
  - The screen shows the error, its stack and "Hey developer", and logs the error to the console.
- **What could go wrong:**
  - `GET /api/v1/versions` can answer 200 without `tools` or `data`, for example from an API older than `3e18128` during a rollout. The footer's `versions.data.map` then throws.
  - In a test, `/csnp` then showed only "Unexpected Application Error!", the `TypeError` and its stack. There was no header, form or footer, and nothing to click. A reload repeats it.
  - The stack carries the bundle's URLs, against `scoring-ui`'s "No build details on screen" and `frontend/CLAUDE.md`.
- **Fix:**
  - an `errorElement` on the root route and on each page route, with fixed text and a link home, so the page's shell survives;
  - show error details only under `import.meta.env.DEV`.

#### FE-2. Field errors and field descriptions fail WCAG AA contrast

- **Files:**
  - `frontend/src/app/theme.ts:20-29`: only `primary` is mapped into Mantine;
  - `frontend/src/index.css:31`: `--color-danger` is defined and never used;
  - `frontend/src/features/csnp/CsnpForm.tsx:47-64` and `frontend/src/features/csnp/SpeciesField.tsx:21-66`.
- **Checked:** reproduced. New.
- **What's wrong:**
  - Mantine's light scheme colours an input's error with `--mantine-color-error` (red-6, `#fa5252`), and its description with `--mantine-color-dimmed` (gray-6, `#868e96`). Both are about 12 px.
  - On the page's canvas, that's 3.15:1 and 3.18:1. WCAG 1.4.3 needs 4.5:1.
  - The project's own `--color-danger` gives 4.56:1, and `--color-ink-muted` 7.24:1.
- **What could go wrong:**
  - For a low-vision user, all of these are at about 3.2:1:
    - the only explanation after an empty submit ("Enter a protein sequence…");
    - the substitutions hint;
    - the species fallback's note;
    - "No species matches".
  - It's also a second, unmanaged set of colours, against `frontend/CLAUDE.md`'s "Every colour is defined once".
- **Fix:** map `--mantine-color-error` to `var(--color-danger)` and `--mantine-color-dimmed` to `var(--color-ink-muted)`, through `MantineProvider`'s `cssVariablesResolver`, in both `main.tsx` and `tests/utils/render.tsx`.

### Low

Grouped by area, so each owner can find theirs.

#### Low: Repository, Images and CI

##### REPO-3. CI skips the API's real-job tests and the compose commands, and several spec scenarios are checked only by hand

- **Files:**
  - `.github/workflows/ci.yml:151-174, 263-341`;
  - `api/tests/test_csnp_scoring.py:19`;
  - `frontend/playwright.config.ts:27`;
  - `compose.yaml`.
- **Checked:** traced. **Earlier:** L2 and L14.
- **What's wrong:**
  - **The API's five real-job tests** skip in CI's `api` job, which has no `blastp`. They cover every sample protein, a species with no hit, and a sequence `blastp` can't read. `api-image` submits one P26439 job with curl and checks its scores.
  - **Two `scoring-jobs` scenarios have no end-to-end test:**
    - "A substitution that isn't scored" (`M1V`) has none anywhere;
    - "The data isn't there" has only the manual steps in `docs/testing/api.md`.
  - **compose** appears in CI only in path filters. `engine-image` runs pytest, but not ruff or basedpyright.
  - **Checked only by hand:**
    - the API image's exact tool versions; CI checks only that they aren't null;
    - that the API image has no legacy scripts, and no Perl beyond `perl-base`;
    - the reference image's checksum check, since CI never builds `csnp-reference`;
    - `csnp parity` through the CLI;
    - that the production build has no mocks.
  - **The frontend's eight `@api` e2e specs** never run in CI, including `scoring-ui`'s "Real scores".
- **What could go wrong:** a regression in the API-to-engine path merges with `ci-passed` green, if the one curl doesn't cover it. Examples: the 422 for an unreadable sequence through a real worker, the no-family path, or the 500 on missing data.
- **Fix:**
  - in `api-image`, run `docs/testing/api.md`'s in-image pytest with `PANTHER_REQUIRE_TOOLS=1` and `PANTHER_REQUIRE_DATA=1`. At `64174c9` it passes: 250 tests in about 51 s;
  - add an `M1V` test and an empty-data test;
  - check the exact versions with `jq`, and that `/opt/csnp-reference` is absent and `dpkg -s perl` fails;
  - run `docker compose run --rm engine`;
  - grep `dist` for `msw` and "mock data";
  - optionally, run Playwright's api mode against the container.

##### REPO-4. The API must run as one server process, and nothing enforces it

- **Files:** `Dockerfile:168`, `api/src/panther_api/jobs/store.py:62-64`.
- **Checked:** reproduced. **Earlier:** L3.
- **What's wrong:** jobs live in one process's memory. When `--workers` isn't given, `fastapi run` takes the process count from `WEB_CONCURRENCY`.
- **What could go wrong:** with `WEB_CONCURRENCY=2`, 12 polls of one job returned seven 200s and five 404s. Some hosts set that variable themselves.
- **Fix:** `"--workers", "1"` in `CMD`, with a comment tying it to the in-memory store.

##### REPO-5. compose publishes the API on every network interface

- **Files:** `compose.yaml:48`.
- **Checked:** traced. **Earlier:** L5.
- **What's wrong:** `"8000:8000"` binds `0.0.0.0`, and on Linux Docker's rules bypass ufw.
- **What could go wrong:** anyone on the same network can queue `blastp` jobs on a developer's machine.
- **Fix:** `"127.0.0.1:8000:8000"`.

##### REPO-6. The API's runtime user can rewrite the installed code, and uv and pip ship in the runtime image

- **Files:** `Dockerfile:96, 151-154`.
- **Checked:** reproduced. **Earlier:** L6.
- **What's wrong:**
  - The `api` stage gives `/opt/venv`, `/work/api` and `/work/engine` to `panther`, the user the server runs as.
  - uv and uvx come along from the `tools` stage, and pip from the Python base image.
- **What could go wrong:** a compromised server process can change `site-packages`, and the change survives restarts of that container.
- **Fix:**
  - install as root, and switch to `panther` only to run;
  - copy uv into the `engine` stage only, and remove pip.

  A read-only root filesystem already works: a csnp job scored with `read_only`, a tmpfs `/tmp` and `cap_drop: ALL`.

##### REPO-7. Supply chain: open alerts with no owner, no image scan, floating apt packages, broad Actions defaults

- **Files:** `.github/dependabot.yml`, `Dockerfile:30-31, 50-51, 89-92`, `package.json`, and the repository's settings.
- **Checked:** reproduced, with `gh api` and `npm audit`. **Earlier:** L7.
- **What's wrong:**
  - **Alerts:**
    - Dependabot alerts #1 (low, `katex`) and #2 (high, a `re2js` ReDoS) have been open since 2026-10-28. Both come from the root `package-lock.json`, through `markdownlint-cli2`.
    - The root `npm audit` reports 3 high and 2 low.
    - `markdownlint` 0.42.0 pins `re2js` 2.8.6 exactly, so only an `overrides` entry can clear #2.
    - Dependabot's security updates are off, and no doc says who handles alerts.
  - **Images:**
    - Nothing scans them.
    - apt packages float: `libgomp1`, the gcc that builds HMMER, and the Perl in `csnp-reference`, although `golden-setup.md:12` records that Perl's exact version.
  - **Actions defaults:** the repository grants a write token, lets Actions approve pull requests, allows any action, and requires no SHA pinning. `ci.yml` overrides them, but a new workflow wouldn't.
- **What could go wrong:**
  - a CVE in FastAPI, Starlette or the base image goes unnoticed;
  - the image that passed the parity tests isn't the one that ships.
- **Fix:**
  - name an owner and a deadline for alerts;
  - add the `re2js` override;
  - scan the images with a pinned Trivy or Grype;
  - pin apt through `snapshot.debian.org`, or record `dpkg -l` with each image;
  - make the Actions defaults read-only, with SHA pinning required.

##### REPO-8. A sample tarball built in `engine/` isn't ignored by git or Docker

- **Files:** `engine/src/panther_engine/csnp/cli.py:136, 321`, `.gitignore`, `.dockerignore`.
- **Checked:** reproduced. **Earlier:** L8.
- **What's wrong:** `csnp sample build` writes `<tag>.tar.gz` to the current folder by default, and the docs run it from `engine/`. Neither ignore file covers it.
- **What could go wrong:** a 157 MB file that `git add -A` stages, and that `COPY engine/ ./` bakes into the image.
- **Fix:** ignore `engine/*.tar.gz` in both files, or default to a folder that's ignored.

##### REPO-9. No timeouts on CI jobs or on the Dockerfile's downloads

- **Files:** `.github/workflows/ci.yml`, where no job sets `timeout-minutes`, and `Dockerfile:34, 53`.
- **Checked:** traced. **Earlier:** L9.
- **What could go wrong:** a stalled download from NCBI or eddylab.org holds up to four runners for GitHub's 6-hour default.
- **Fix:**
  - `timeout-minutes` on each job;
  - `curl --connect-timeout 30 --max-time 600 --retry 3`.

##### REPO-10. `.claude/settings.json` misses force-push and admin spellings that GitHub doesn't stop

- **Files:** `.claude/settings.json:4-20`, `CONTRIBUTING.md:137`.
- **Checked:** traced against Claude Code's wildcard matching; not run. **Earlier:** N13, raised from Nit.
- **What's wrong:** none of these matches a deny rule:
  - `git push origin +feat/x`, a real force push, which GitHub allows on every branch but `main`;
  - `git push -uf origin feat/x`;
  - `git -C . push --force`;
  - any shell write into `panther-workspace`, since `Edit(…)` covers only the edit tools.

  CONTRIBUTING.md says the file stops force-pushing.
- **What could go wrong:** an assistant denied `git push --force` retries with a `+` refspec, and overwrites a teammate's commits on a shared branch.
- **Fix:**
  - add deny rules for `+` refspecs, `git -C … push`, and combined short flags;
  - say in CONTRIBUTING.md what the file doesn't cover.

#### Low: API

##### API-3. A job submitted just after a worker dies can fail without ever running

- **Files:** `api/src/panther_api/jobs/runner.py:64-75`.
- **Checked:** reproduced; the earlier draft only suspected it. **Earlier:** L11.
- **What's wrong:**
  - When a worker dies, `ProcessPoolExecutor` marks itself broken at once. The event loop replaces the pool only when it handles the first failed job.
  - A job that takes a free slot in between calls `submit()` on the broken pool. That raises `BrokenProcessPool`, and the job fails as though its own worker had died.
- **What could go wrong:**
  - Reproduced with two workers:
    - job A's worker exits;
    - the loop is busy for a moment, as it is during a slow validation or a large response;
    - job B, submitted in that moment, fails with "The worker running the job stopped unexpectedly." without having run;
    - job C, submitted afterwards, succeeds.
  - `scoring-jobs` says jobs submitted after a crash run normally.
- **Fix:** when `pool.submit()` itself raises `BrokenProcessPool`, replace the pool and submit the job once more.

##### API-4. A `422` echoes a submitted field name in full, at any length

- **Files:** `api/src/panther_api/problems.py:159-162`.
- **Checked:** reproduced. New.
- **What's wrong:**
  - `loc` is copied as Pydantic gives it. For an unknown field, its last item is the client's own key.
  - `api/CLAUDE.md` says never to echo a submitted value, but the tests check values only.
- **What could go wrong:**
  - A `tools` request whose `input` held one key, `<img src=x onerror=alert(1)>` followed by 100,000 more characters, got a 422 of 100,243 bytes that holds the key verbatim.
  - A client that shows `loc` as HTML would reflect that markup.
  - The 100-error cap doesn't bound the size, because one key can be as long as the body (API-1).
- **Fix:**
  - for `extra_forbidden` errors, replace the key with a fixed placeholder, or keep it only when it's short and plain, such as `[A-Za-z0-9_]{1,64}`;
  - test with a distinctive key.

##### API-5. The docs page loads an unpinned Swagger UI from a CDN

- **Files:** `api/src/panther_api/main.py:57-64`, which uses FastAPI's defaults.
- **Checked:** reproduced. New.
- **What's wrong:**
  - `/api/v1/docs` loads `swagger-ui-dist@5`, meaning any 5.x release, from `cdn.jsdelivr.net` without SRI. Its favicon comes from `fastapi.tiangolo.com`.
  - Everything else the project ships is pinned, by digest or checksum.
- **What could go wrong:**
  - a changed or compromised 5.x release runs on the API's origin for every docs visitor;
  - for a visitor who can't reach jsdelivr, the page is blank.
- **Fix:** pin an exact version with SRI (`get_swagger_ui_html` takes the URLs), serve the files from the image, or turn the docs page off in production.

##### API-6. The docs page's OAuth redirect is served outside `/api/v1`

- **Files:** `api/src/panther_api/main.py:57-64`.
- **Checked:** reproduced. New.
- **What's wrong:**
  - `create_app` sets `docs_url`, but not `swagger_ui_oauth2_redirect_url`, so FastAPI serves its default `/docs/oauth2-redirect`.
  - `GET /docs/oauth2-redirect` answers 200 with HTML, and `/api/v1/docs/oauth2-redirect` answers 404.
  - `api-service`'s "Versioned base path" says every endpoint, documentation pages included, is under `/api/v1`, and that anything outside gets a 404. The tests check only `/health`.
- **Fix:**
  - `swagger_ui_oauth2_redirect_url=None`, since no OAuth is used, or a URL under the prefix;
  - a test that every route starts with `/api/v1`.

##### API-7. A large job expiry passes the startup check, then breaks every request

- **Files:** `api/src/panther_api/settings.py:14-17`, `api/src/panther_api/jobs/store.py:54-56`.
- **Checked:** reproduced. **Earlier:** L10.
- **What's wrong:** `job_expiry_seconds` and `job_workers` have no upper bound.
- **What could go wrong:**
  - With `PANTHER_API_JOB_EXPIRY_SECONDS=80000000000000`, the API starts and accepts a job.
  - Once that job finishes, its poll answers 500, and so does every new `POST`, because `finished_at + expiry` overflows.
  - `scoring-jobs` says an invalid value must stop the API from starting.
- **Fix:** `le=` bounds, such as 30 days and 64 workers, with tests.

##### API-8. The job store's memory and work grow with traffic

- **Files:** `api/src/panther_api/jobs/store.py:21-34, 69-72`, `api/src/panther_api/routers/jobs.py:47-60`.
- **Checked:** traced, with the poll measured. **Earlier:** L12.
- **What's wrong:**
  - Each `POST` scans every stored job for expiry, on the event loop.
  - A finished job keeps its whole request for 24 hours, though no response returns it. That's up to 50,000 residues for cSNP, and 100,000 IDs for refmap.
  - Each poll of a finished job re-validates and re-serialises its result on the loop. For a simulated 100,000-mapping refmap result, that took 37 to 40 ms and sent 4.6 MB.
  - Expired jobs are freed only by the next submit or by a poll of that job, though `scoring-jobs` says the API "MUST release the memory".
- **What could go wrong:** nothing at today's traffic. With tens of thousands of jobs a day, each submission blocks the loop for the scan, and requests dominate memory.
- **Fix:**
  - keep finished jobs in the order they finished, and drop expired ones from the front;
  - drop `request` when a job finishes;
  - serialise a finished job once.

##### API-9. Operators can't see input errors or the queue

- **Files:** `api/src/panther_api/jobs/runner.py:80`, `Dockerfile:168`.
- **Checked:** traced. **Earlier:** L13.
- **What's wrong:**
  - Input errors are logged at INFO, which nothing shows: nothing configures the app's loggers, and uvicorn's default configuration leaves the root logger alone.
  - Nothing measures queue depth, job duration or worker restarts.
- **What could go wrong:** in production, a run of rejected sequences (or of CSNP-5's misread BLAST+ errors), or a growing queue, stays invisible until users complain.
- **Fix:**
  - configure logging for `panther_api` at startup;
  - log each finished job with its duration and the queue's depth.

#### Low: cSNP Port

##### CSNP-5. Every `blastp` exit status 1 is blamed on the user's sequence, and BLAST+'s message is dropped

- **Files:** `engine/src/panther_engine/csnp/blast.py:26-27, 66-67`, `api/src/panther_api/jobs/runner.py:76-81`.
- **Checked:** reproduced. New.
- **What's wrong:**
  - BLAST+ 2.17.0 exits with 1 both for a query it can't read and for an option error. `-bogus_option` and `-best_hit_overhang 0.9` both exit 1.
  - `search()` turns every 1 into `InputError`, with the "can't be read as a protein sequence" message, and discards stderr.
  - The API logs only that message, at INFO.
- **What could go wrong:** a BLAST+ upgrade, or an edit to `OPTIONS` or `OUTFMT`, could make `blastp` reject an option. Every csnp job would then become a 422 telling users to fix their sequence, and no log would show why.
- **Fix:**
  - map status 1 to `InputError` only when stderr says "BLAST query error", as 2.17.0 does for `1234567890` or `MK(VL`;
  - map it to `BlastError` otherwise;
  - keep the tail of stderr on the exception, for the log.

##### CSNP-6. A data folder path with a space breaks every search

- **Files:** `engine/src/panther_engine/csnp/blast.py:57`.
- **Checked:** reproduced. **Earlier:** L15.
- **What's wrong:** BLAST+ reads `-db` as a list of database names separated by spaces, and `search()` passes the path unquoted.
- **What could go wrong:** with the data at `/my data`, `blastp` exits 2 ("No alias or index file found for protein database [/my]"), and every job fails with the generic 500.
- **Fix:** quote the path as BLAST+ expects, or refuse a path with whitespace at startup.

##### CSNP-7. Paths no test reaches

- **Checked:** traced; one path reproduced against the Perl. New.
- **What's wrong:** no test reaches these paths:
  - **A real BLAST+ 2.17.0 tie line** at `hits.py:162-169`. The case generator (`parity.py:164`) and the unit tests' `blast_line` both build the identity with the port's formula (CSNP-1), so they can't disagree with it.
  - **A gene missing from the `.orig.tree`** (`psep.py:150-152, 181-182`; `SCORE-8`, through `findAN`). The service can't reach it (`DATA-2`), and nothing pins it. For this review, 6 rows of `PTHR17486` were checked against the Perl, and they agree.
  - **The guard branches:**
    - `age()`'s cycle guard (`psep.py:219-220`);
    - `search()`'s `OSError` branch (`blast.py:64-65`);
    - counts that aren't integers, and a length of 0 (`hits.py:158-161`).
- **Fix:**
  - a test with a real tie line;
  - the `PTHR17486` rows as a fixture test;
  - unit tests for the guards.

#### Low: Engine Core and Tooling

##### ENG-2. `run_tool` rewrites tool output: CR becomes LF, and invalid bytes become U+FFFD

- **Files:** `engine/src/panther_engine/core/process.py:21, 39-40`.
- **Checked:** reproduced. New.
- **What's wrong:**
  - `encoding="utf-8", errors="replace"` puts `subprocess` in text mode. That turns `\r\n` and a lone `\r` into `\n`, and invalid UTF-8 into U+FFFD. The docstring says only "captured as UTF-8 text".
  - `legacy.lines_of` is written to keep a `\r` inside a line, as Perl does, but by then the runner has already removed it.
  - A fake tool that printed `a\r\nb\rc\xffd\n` came back as `a\nb\nc\ufffdd\n`.
- **What could go wrong:** it's latent. None of the BLAST database's 570,173 headers has a CR or a non-ASCII byte. But in a project that's checked byte for byte, it's a silent difference waiting for the next tool.
- **Fix:** capture bytes and decode without changing newlines (Latin-1, or `surrogateescape`), or document the behaviour. Test it either way.

##### ENG-3. A timeout kills only the tool, not what the tool started

- **Files:** `engine/src/panther_engine/core/process.py:33-43`, `engine/tests/test_process.py:54-58`.
- **Checked:** reproduced. New.
- **What's wrong:**
  - On a timeout, `subprocess.run` kills only the direct child. There's no new session and no process-group kill.
  - The test uses `exec sleep 5`, which sidesteps the case.
  - A wrapper that ran a child without `exec` timed out after 0.31 s. The child still finished its work 1.5 s later.
- **What could go wrong:** there's no impact today: the three binaries run directly. But:
  - the Perl reference starts `sort` and `grep` through a shell;
  - EBI's `treegrafter.py` starts `epa-ng` itself, so run through `run_tool`, a timeout would leave `epa-ng` running.
- **Fix:**
  - `start_new_session=True`, and `os.killpg` on timeout;
  - a test where a grandchild writes a marker file.

##### ENG-4. `csnp score` normalises differently from the API, and the normalisation is written three times

- **Files:**
  - `engine/src/panther_engine/csnp/cli.py:22-24, 362-392`;
  - compared with `api/src/panther_api/jobs/csnp.py:39-72` and `frontend/src/features/csnp/checks.ts:27-56`.
- **Checked:** reproduced. New.
- **What's wrong:**
  - The CLI's help says it normalises "as the API normalises it". But it upper-cases before any ASCII check, and has no 50,000-residue limit.
  - `str.upper()` turns some non-ASCII letters into ASCII ones. So a FASTA holding `MKßVﬀı` is scored by the CLI as `MKSSVFFI`, where the API answers 422. A token `ı10E` becomes `I10E`.
  - The rules are written three times: in the API, the frontend and the CLI. Only the frontend's limits are tested against the API's.
- **Fix:**
  - one normalising function in the engine, used by the CLI and the API, for example in a core sequence module, which hmmscore and treegrafter will also need;
  - at least, check `[!-~]` before `upper()` in the CLI.

##### ENG-5. The survey reports part of an archive and exits 0

- **Files:** `engine/src/panther_engine/csnp/survey.py:242-292`.
- **Checked:** reproduced again. **Earlier:** L16.
- **What's wrong:**
  - Reading a stream, `tarfile` stops quietly at an invalid header, or at a missing end-of-archive marker.
  - It doesn't check the gzip CRC either.
- **What could go wrong:**
  - A tarball cut at its 4th member's header gave "Families: 1" and exit 0.
  - A gzip with a bad CRC was read in full without an error.
  - `csnp-data` says an archive that ends early exits non-zero.
- **Fix:**
  - require the end-of-archive blocks;
  - read through `gzip.GzipFile`, which checks the CRC;
  - warn when the sha256 isn't the pinned one.

##### ENG-6. `sample fetch` isn't atomic, though its docs say it is

- **Files:** `engine/src/panther_engine/csnp/sample.py:296-303`, `engine/src/panther_engine/csnp/cli.py:169`, `docs/testing/engine.md:152`.
- **Checked:** reproduced, with a realistic trigger. **Earlier:** L17.
- **What's wrong:** files move into place one `os.replace` at a time, while the docs say "If anything fails, the data folder is left as it was."
- **What could go wrong:**
  - **A partial update:**
    - fetch v1, `chmod 555 csnp/9/blast`, then fetch v2;
    - fetch exited 1 after replacing the `.paml` files, but not `blast.phr` or the species tree;
    - `verify` then failed against both manifests.
  - **The trigger is realistic:** the docs warn that a compose fetch without `--user` creates folders the user can't write.
  - **Leftovers:** a killed fetch leaves its `.csnp-sample-*` work folder, up to 157 MB plus 624 MB, and later fetches never remove it.
- **Fix:**
  - remove stale work folders first;
  - swap the whole `csnp/9` folder in one rename, or check that every target is writable before moving anything, or correct the docs.

##### ENG-7. `sample fetch` trusts the manifest and the server more than it needs to

- **Files:** `engine/src/panther_engine/csnp/sample.py:76-89, 281, 307-320, 339`.
- **Checked:** traced. **Earlier:** L18.
- **What's wrong:**
  - `asset.bytes` is never used, so the download has no size cap and no deadline;
  - `asset.name` isn't checked, so `../x` writes outside the work folder;
  - redirects are followed before the https check;
  - `extractall` unpacks members the manifest doesn't list, with no size limit.
- **What could go wrong:** each needs a hostile manifest, which would be a reviewed commit, or a compromised server. The sha256 still protects what gets installed, so the realistic harm is a full disk.
- **Fix:**
  - stop reading at `asset.bytes`;
  - allow only a plain file name;
  - refuse non-https redirects;
  - extract only the manifest's files, after summing their sizes.

##### ENG-8. Several CLI mistakes end in a traceback

- **Files:**
  - `engine/src/panther_engine/csnp/cli.py:353, 431, 484-498`;
  - `survey.py:301-319`;
  - `parity.py:276, 334, 400, 470`;
  - `sample.py:171`.
- **Checked:** reproduced. **Earlier:** L19, with two more paths.
- **What's wrong:** each of these ends in a traceback:
  - `survey --species` with a bad species file;
  - `survey --json` into a missing folder: it fails after the whole 400-second survey, and the result is lost;
  - `parity cases --positions 3` or `--genes -1`: it fails after some case files are written;
  - `parity cases` on a species tree or `.orig.tree` with CRLF line ends, since `LibraryFormatError` isn't caught;
  - `sample build --readme` with a Latin-1 README (`UnicodeDecodeError`).
- **Fix:**
  - catch `LibraryFormatError`, `ValueError` and `UnicodeDecodeError` in the handlers;
  - write the JSON inside the `try`;
  - bound the numbers in argparse.

##### ENG-9. The scoring tests ignore the `.data/` fallback the markers use

- **Files:** `engine/tests/conftest.py:25-28`, `engine/tests/test_csnp_scoring.py:66-69`, `engine/tests/test_csnp_cli.py:128-160`.
- **Checked:** reproduced. **Earlier:** L20.
- **What's wrong:**
  - Without `PANTHER_DATA_DIR`, the `data` marker finds the sample in `.data/`.
  - But the tests call `score()` without a data folder, so the engine raises `DataFolderError`.
  - The API's real-job tests set the variable from the marker's folder, so they're fine.
- **What could go wrong:** a developer with a native BLAST+ who fetched the sample into `.data/`, as the docs say, gets about a dozen failures. CI and the image set the variable, so they don't.
- **Fix:** an autouse fixture that sets `PANTHER_DATA_DIR` to the marker's folder when it's unset.

##### ENG-10. `parity cases` takes every `.paml` in the data folder, not the sample's families

- **Files:** `engine/src/panther_engine/csnp/parity.py:266-271`, `engine/src/panther_engine/csnp/sample.py:296-299`.
- **Checked:** traced. New, and latent.
- **What's wrong:**
  - Without `--family`, the step-3 cases cover whatever `.paml` files the folder holds.
  - `fetch` never removes files that a newer manifest drops.
- **What could go wrong:**
  - Suppose a future sample drops a family. The documented regenerate command then commits goldens for a family that CI's fresh sample lacks.
  - `test_csnp_golden.py` fails only after the push.
  - Samples 1 to 3 only added families, so nothing is affected yet.
- **Fix:** default to `sample.json`'s families, or have `fetch` remove unlisted files under `csnp/9/`.

##### ENG-11. Untested behaviour in core and the data tooling

- **Checked:** traced, with a grep of `engine/tests/`. New.
- **What's wrong:** these aren't tested:
  - **`test_process.py:54-58`:** nothing checks that a timed-out tool is gone. Output rewriting, the stdin default and the environment aren't tested.
  - **`core/tools.py:60-63`:** a version command that fails to start or times out.
  - **`core/manifest.py:79-84`:** a manifest that's unreadable, invalid, or not an object.
  - **`csnp/sample.py`:**
    - the build's refusal of a wrong species sha256 (117-119);
    - its refusal of a README without a copyright statement (169-176);
    - its refusal of a bad family name (114-116);
    - fetch's check of each file after unpacking (290-295);
    - any successful download, redirect or size check.
  - **`csnp/cli.py:406-475`:** the `parity cases`, `reference` and `check` handlers never run through `main()`.
- **Fix:** add the tests.

#### Low: Frontend

##### FE-3. The sequence check's trim is quadratic in a run of whitespace, so a big paste freezes the tab

- **Files:** `frontend/src/features/csnp/checks.ts:30, 40`, `frontend/tests/features/csnp/checks.test.ts:80-84`.
- **Checked:** reproduced. **Earlier:** L22.
- **What's wrong:**
  - The pattern `/^[\u0000- ]+|[\u0000- ]+$/g` tries its second branch at every position in a run of whitespace inside the text. So its cost grows with the square of the run's length.
  - It runs on the main thread, on submit.
  - The existing test uses trailing whitespace, which is linear.
- **What could go wrong:**
  - 50,000 residues, then 20,000 blank CRLF lines, then one more residue: the tab froze for 2.6 s.
  - 80,000 spaces inside the text froze it for 10.6 s.
- **Fix:**
  - trim the start with an anchored pattern, and the end with a `charCodeAt` loop;
  - add a timing test with a run of whitespace inside the text.

##### FE-4. A job whose `service` or `status` the page doesn't know is polled every second, forever

- **Files:**
  - `frontend/src/app/api/wire.ts:9, 60-68`;
  - `frontend/src/features/jobs/useJob.ts:11-13`;
  - `frontend/src/features/jobs/JobPage.tsx:20`;
  - `frontend/src/mocks/handlers.ts:21-37`.
- **Checked:** reproduced with MSW. **Earlier:** L21.
- **What's wrong:**
  - `WireJob` lists `ToolsJob | CsnpJob` by hand, so the schema's new `RefmapJob` never reaches it.
  - `fromWireJob` has no default case, so an unknown service returns `undefined`, which RTK Query stores as a success.
  - `useJob` stops only on an error or a known finished status.
- **What could go wrong:**
  - For a job from an unknown service, the page polls once a second and says "Loading the job…" forever.
  - An unknown status, such as `cancelled`, does the same, with an empty badge.
  - The mock answers a refmap `POST` with a 422 the API never gives: the API validates the request, then answers 501.
- **Since this commit:** #35 added `RefmapJob` and a refmap case. An unknown service or status still polls forever.
- **Fix:**
  - derive `WireJob` from the schema's response union, with an exhaustive switch, so a new service fails `tsc`;
  - at run time, throw on an unknown service, and treat every status except `queued` and `running` as finished.

##### FE-5. When the job id changes on a mounted job page, the previous job's result shows under the new job's address

- **Files:** `frontend/src/features/jobs/JobPage.tsx:12, 20-21`.
- **Checked:** reproduced. New. The earlier draft listed this case as correct.
- **What's wrong:**
  - `JobPage` reads RTK Query's `data`, which is the latest result whatever the argument.
  - React Router keeps the page mounted from `/jobs/A` to `/jobs/B`.
- **What could go wrong:** FE-6 makes this reachable:
  1. On job A's results, the user goes to `/csnp` and submits.
  2. While the request is in flight, they press Back to `/jobs/A`.
  3. The 202 then opens `/jobs/B`, which shows A's family, A's scores and "Succeeded" until B's first poll answers.

  On a slow network the wrong results stay up, against `scoring-ui`'s "While the job is loading, the page MUST say so".
- **Fix:** use `currentData`, or remount the page for each id (`key={id}`).

##### FE-6. Leaving the form while a job is being started still moves the user to that job

- **Files:** `frontend/src/features/csnp/useSubmitCsnp.ts:37-38`, `frontend/src/features/jobs/StartToolsCheck.tsx:16-17`.
- **Checked:** reproduced. **Earlier:** N11, raised from Nit, since it leads to FE-5.
- **What's wrong:**
  - The data router's `navigate` keeps working after the component unmounts, so the `navigate` after the `await` runs anyway.
  - With the POST held back, navigating home gave `/`. Once the 202 arrived, the page moved to `/jobs/…`.
- **What could go wrong:** sending a 1 MB sequence over a slow uplink takes seconds. If the user leaves in that time, they are pulled back to the new job.
- **Fix:** skip the `navigate` once the component has unmounted, or when the location is no longer the form's.

##### FE-7. A species typed while the list was unavailable can be sent, though the selector shows none

- **Files:** `frontend/src/features/csnp/SpeciesField.tsx:25`, `frontend/src/features/csnp/checks.ts:102-108`, `frontend/src/features/csnp/draft.ts:83`.
- **Checked:** reproduced. **Earlier:** L24.
- **What's wrong:**
  - The selector shows the draft only if the untrimmed text is a listed code.
  - The check and the request both trim it.
- **What could go wrong:**
  - The user types `MOUSE` with a trailing space while the list is down, and the list then loads.
  - The selector is blank, no error shows, and the request sends `MOUSE`.
  - That's against `scoring-ui`'s "Whatever the selector shows, the request MUST send the species' code".
- **Fix:**
  - compare the trimmed value;
  - once the list has loaded, answer any value that isn't in it with "Choose a species from the list."

##### FE-8. One failed poll ends live updates, and requests have no timeout

- **Files:** `frontend/src/features/jobs/useJob.ts:11`, `frontend/src/features/jobs/JobPage.tsx:14-18`, `frontend/src/app/api/api.ts:8`.
- **Checked:** reproduced. **Earlier:** L25.
- **What's wrong:**
  - Any error except a 404 stops polling, and replaces a running job with "Job unavailable" until the user retries.
  - `fetchBaseQuery` has no `timeout`, so a hung request stalls polling silently.
  - Nothing refetches when the network comes back, and hidden tabs keep polling.
- **What could go wrong:** a phone user watching a job loses it to one dropped request.
- **Fix:** `scoring-ui` requires today's behaviour, so change the spec first. Then:
  - retry with backoff;
  - a 30 s `timeout`;
  - `refetchOnReconnect`;
  - `skipPollingIfUnfocused`.

##### FE-9. Errors and page changes aren't announced, and focus is lost

- **Files:**
  - `frontend/src/features/csnp/CsnpForm.tsx:32-38`;
  - `frontend/src/features/csnp/SpeciesField.tsx:67-69`;
  - `frontend/src/features/jobs/JobPage.tsx:20-21`;
  - `frontend/src/features/jobs/JobStatus.tsx:30`;
  - `frontend/index.html:6`.
- **Checked:** reproduced. **Earlier:** L26, with more cases.
- **What's wrong:**
  - After a failed check, focus stays on the submit button, and the errors are plain `<p>` elements with no role and no live region.
  - Once "Load the list of species again" brings the list back, its button disappears and focus drops to `<body>`.
  - After moving to a job page, focus is on `<body>`.
  - The `role=status` region appears together with its first status, so "Queued" usually isn't announced.
  - Every page has the same title.
- **What could go wrong:** a screen-reader user who submits an empty form hears nothing.
- **Fix:**
  - focus the first invalid field, or an error summary with `role=alert`;
  - focus the species field once the list loads;
  - give each route its own title, and focus its heading after navigation;
  - render the status region empty first.

##### FE-10. The form's input is lost on Back or reload

- **Files:** `frontend/src/features/csnp/CsnpForm.tsx:14`, `frontend/src/features/csnp/draft.ts`.
- **Checked:** traced. **Earlier:** L27.
- **What's wrong:** the draft is component state, so it's gone when the route changes.
- **What could go wrong:** after a job that failed on its input, Back shows an empty form, and the user has to paste up to 50,000 residues again.
- **Fix:** either:
  - keep the values in `sessionStorage` under a versioned key, with `try`/`catch` and a size cap; or
  - carry them in the job page's history state, with an "edit and resubmit" link.

##### FE-11. The form and job pages link nowhere

- **Files:**
  - `frontend/src/layout/AppLayout.tsx:12-16`;
  - `frontend/src/features/jobs/JobDetails.tsx:21-44`;
  - `frontend/src/features/jobs/JobPage.tsx:45-61`;
  - `frontend/src/features/csnp/CsnpPage.tsx:4-17`.
- **Checked:** traced. New.
- **What's wrong:** links exist only on the home page and the not-found views. The header is a bare `<h1>`.
- **What could go wrong:**
  - A colleague who opens a shared `/jobs/{id}` link can't reach the form or the home page without editing the address.
  - Scoring another protein needs Back, which empties the form (FE-10).
- **Fix:**
  - make the header's title a link home;
  - add "Score another protein" and "Home" links to the job page.

##### FE-12. Frontend test gaps

- **Files:**
  - `.github/workflows/ci.yml:123, 140`;
  - `frontend/tests/utils/render.tsx:26-34`;
  - `frontend/e2e/csnp.spec.ts:122-124`.
- **Checked:** traced. **Earlier:** L28, with one of its claims corrected (FE-5).
- **What's wrong:**
  - CI builds the frontend but never inspects `dist`. `scoring-ui`'s "The production build" scenario is a manual grep.
  - Tests don't render in StrictMode, though `frontend/CLAUDE.md` says effects run twice in tests.
  - The e2e step "must not scroll the page away from it" asserts nothing about scrolling. Playwright's `click` scrolls its target into view first, so reverting `floatingStrategy: 'fixed'` would still pass.
  - Untested:
    - polling stopping after a running job succeeds (it works);
    - an unknown service or status (FE-4);
    - a job id change (FE-5);
    - a 422 on `sequence`;
    - the slow trim (FE-3).
- **Fix:**
  - `! grep -rliE 'msw|mock data' dist` after the build;
  - StrictMode in `tests/utils/render.tsx`;
  - assert `window.scrollY` before the click;
  - add the missing tests.

#### Low: Specs and Process

##### SPEC-1. refmap's divergence rows 9 and 10 were merged without an approver

- **Files:**
  - `docs/parity/divergences.md:15-16`;
  - `api/src/panther_api/jobs/refmap.py:31-82` and `api/src/panther_api/jobs/fields.py:9-16`, merged in #30;
  - `openspec/changes/add-refmap-job/proposal.md:44`.
- **Checked:** traced. New.
- **What's wrong:**
  - The API answers 422 where the reference answered `NOHIT`:
    - an empty ID;
    - an ID with whitespace, or over 64 characters;
    - an organism that isn't a 1-to-5-character code.
  - `CLAUDE.md` says a row without an approver is a proposal: "flag it, don't ship it". `add-refmap-job` says neither row may ship without one.
  - Getting them approved was still the change's next action when #30 merged.
- **What could go wrong:**
  - Today no user gets a different mapping, since a valid refmap request gets a 501.
  - But the refmap form (#35, after this commit) and the website's port are built on these refusals.
  - If the wiring change removes the 501 first, an unapproved divergence ships.
- **Fix:** approve or reject rows 9 and 10 before archiving `add-refmap-job`. In its `tasks.md`, make both the archive and the wiring change wait on that decision.

##### SPEC-2. The main specs lag merged code, and one delta will contradict them

- **Checked:** traced. New.
- **What's wrong:** `add-refmap-job` (#30) and `add-apoe-to-csnp-sample` (#36) are merged but not archived, so `openspec/specs/` doesn't describe `main`:
  - `api-service` has no 100-error cap, which `problems.py:141-170` implements;
  - `scoring-jobs` has no refmap;
  - `csnp-data` doesn't require `PTHR18976`;
  - `psep-engine` has no goldens for the form's example.
- **What could go wrong:** after the archive, `scoring-jobs`' "Submit a job" (`spec.md:9-16`) will still say a valid request "MUST respond with status 202". Beside it will be the added "refmap not available yet", which answers 501.
- **Fix:**
  - archive `add-apoe-to-csnp-sample` now. Its Notes still say "Open the pull request";
  - give `add-refmap-job` a MODIFIED "Submit a job";
  - archive `add-refmap-job` after SPEC-1 and SPEC-5 are settled.

##### SPEC-3. Some of the API's refusals have no divergence row, and the log's scope is unclear

- **Files:**
  - `docs/parity/divergences.md:3, 15-16`;
  - `api/src/panther_api/jobs/csnp.py:26-27, 60-72`;
  - `docs/parity/README.md`.
- **Checked:** traced, against `snpScore.cgi:212` at `cebb5ab`. New.
- **What's wrong:**
  - **The log's scope:** it says it covers differences "between the Python engine and a service's reference", yet rows 9 and 10 log API input refusals.
  - **cSNP refusals with no row:**
    - a token whose mutant residue is a pipe, such as `G12|`, which the CGI's pattern accepted and scored;
    - more than 1,000 tokens;
    - a token over 32 characters.

    These were decided on #19, and `CLAUDE.md` records the first.
  - **Row 10 is incomplete:** it leaves out refmap's refusal of more than 100,000 IDs, and of an empty list. The CGI refused neither.
  - **Not divergences:** a missing or unknown cSNP species, and a lower-case mutant residue. The website's form handled both before the CGI saw them.
- **Fix:**
  - say in `docs/parity/README.md` whether API refusals belong in the log;
  - then add a cSNP row, or move the API-only parts out of rows 9 and 10;
  - complete row 10.

##### SPEC-4. Who approves a divergence isn't written down, and row 1 is treated as decided without an approver

- **Files:**
  - `docs/parity/divergences.md:7`;
  - `CLAUDE.md:12`;
  - `docs/design/tech-stack.md:199, 360`;
  - `docs/parity/README.md:64`;
  - `.github/CODEOWNERS`.
- **Checked:** traced. New.
- **What's wrong:**
  - **Row 1,** adopting EBI's treegrafter, says "Decided by the team on 2026-10-28" but has no approver. By the log's own rule, that makes it a proposal.
    - `CLAUDE.md`, `openspec/config.yaml` and `tech-stack.md` treat it as decided.
    - `tech-stack.md` shows the science owner's review of it as pending.
  - **Row 8** is approved by "Engine developer", while `tech-stack.md` asks the science owner to approve result-changing fixes.
  - **CODEOWNERS** has no line for `divergences.md`; `add-quality-gates` deferred it. So any developer can merge an "Approved by".
- **Fix:**
  - write down who approves which kind of row;
  - fill in row 1's approver, or soften `CLAUDE.md`;
  - give `divergences.md` to the science owner in CODEOWNERS.

##### SPEC-5. Two open questions block refmap's port, though its contract is merged

- **Files:**
  - `openspec/specs/engine-core/spec.md:92-99`, against `docs/design/tech-stack.md:271-276`;
  - `docs/design/tech-stack.md:322`;
  - `CLAUDE.md:40`.
- **Checked:** traced. New.
- **What's wrong:**
  - **The data layout:**
    - `engine-core` puts each service's data under `<service>/<version>/`.
    - `tech-stack.md` puts hmmscore, refmap and treegrafter in a shared `/data/panther/<version>/`.
    - `add-refmap-job`'s proposal asks which applies.
    - It blocks provisioning refmap's data, and its `Versions.data` entry.
  - **Jobs or synchronous:**
    - `add-refmap-job` specifies refmap as a job.
    - `tech-stack.md` and `CLAUDE.md` still list the question as open.
    - The change's own follow-up says the decision goes into `tech-stack.md`.
- **Fix:** decide both, and record the decisions before archiving `add-refmap-job`.

##### SPEC-6. Active changes have stale Notes, and one can't close

- **Checked:** traced, with `gh api`. New.
- **What's wrong:**
  - **`add-quality-gates`:**
    - tasks 6.2 and 6.3 are unticked;
    - its Blocker, "needs this change merged", is stale;
    - its CODEOWNERS follow-up isn't done.
  - **`add-refmap-job`:**
    - its Next action says #30 is under review, though it merged;
    - its lessons and `refmap-legacy-behaviour.md:9` give RefProteomeMapper's checkout as `4fc6a09`. Checkouts differ by developer, so cite commits instead.
  - **`add-apoe-to-csnp-sample`** is ready to archive (SPEC-2).
- **Fix:**
  - update the Notes;
  - finish and archive `add-quality-gates`.

### Nits

- **REPO-11.** `.editorconfig:3-9`: `[*]` forces LF line endings, trims trailing whitespace and adds a final newline, with no exception for the fixtures and goldens that must stay byte-exact. `.gitattributes:23-26` keeps git's hands off them, but an editor that honours EditorConfig changes them on save:
  - `crlf.paml` and the `edge-cases` files have CRLF;
  - three `.rst` fixtures and two goldens have trailing whitespace;
  - `sample.fasta` and `sample.input` have no final newline.

  Add an `[engine/tests/{fixtures,golden}/**]` section that unsets all three rules. New.
- **REPO-12.** Docs that disagree with the code, or with each other. **Earlier:** N14, with more found.
  - `CLAUDE.md:31-34` and `openspec/config.yaml:16` call the API stack Proposed, and don't mention `docs/design/api-stack.md`, which has been Accepted since 2026-10-28.
  - `CONTRIBUTING.md:137` says `.claude/settings.json` stops force-pushing (REPO-10).
  - `docs/testing/README.md` has four drifts:
    - line 7 lists `strategy.md`, which doesn't exist;
    - line 22 doesn't say `ci-passed` also fails on a cancelled job;
    - lines 26-30 leave out that `.nvmrc` and `ci.yml` trigger jobs;
    - line 33 says dependency review reads three lock files, but GitHub's dependency graph also has the root `package-lock.json`, where both open alerts are.
  - `docs/manual-qa/README.md:7-8` names `01-single-substitution.md`, `02-batch-input.md` and `00-results-sheet.md`. The files are `01-tools-check.md` and `02-csnp-form.md`, and there's no results sheet.
  - `docs/manual-qa/02-csnp-form.md:7` lists Docker, curl and Node, but the fetch at line 74 also needs uv.
  - `docs/testing/api.md:292` says `fastapi[standard]`. The dependency is `fastapi[standard-no-fastapi-cloud-cli]`.
  - `docs/design/tech-stack.md:285` stops at `csnp-sample-2`. `sample.json` pins `csnp-sample-3`: 16 families, 624 MB unpacked.
  - `docs/parity/inputs.md:14`, `docs/testing/engine.md:106` and `tech-stack.md:252` say `blast/` holds the three sample proteins. It also holds `APOE.csv`.
  - `docs/design/frontend-stack.md:39, 44` keep the form's draft in `useForm`. It's a reducer.
  - `docs/testing/frontend.md:16-19`, `frontend/README.md:33` and `frontend/CLAUDE.md:7-10` leave `format:check` and `api:types:check` out of the checks to run before a pull request. CI runs both.
  - `docs/parity/golden-setup.md:83`'s compose command writes into the engine mount as uid 1000, against `compose.yaml:28-29` ("Nothing is written into the mount"). On a Linux host whose uid isn't 1000 it would fail (suspected).
  - The `openspec-change` job's `code` filter leaves out `Dockerfile`, `compose.yaml`, `.github/` and `.claude/`. So a change to pins, CI or the ruleset needs neither a proposal nor `no-spec`, and CONTRIBUTING.md doesn't say so.
  - `docs/code-review/README.md:10` asks for the reviewer, while `CONTRIBUTING.md:93` forbids assistant credit in docs. Say what to write when an assistant helped.
  - In `openspec/changes/archive/`, 77 relative links break, because archiving moves a change one folder deeper (for example `archive/2026-10-30-port-csnp/design.md:7`).
- **API-10.** `api/src/panther_api/jobs/work.py:41-62`: the job request models don't forbid extra fields, so `{"service": "tools", "input": {}, "priority": "high"}` gets a 202 (reproduced). Each `input` model does forbid them. **Earlier:** N1.
- **API-11.** `api/src/panther_api/jobs/csnp.py:94-122`: the cSNP request's schema carries none of its rules, though `api/CLAUDE.md` asks for them and `RefmapInput` has them. There's no `pattern` or `maxLength` on `species`, and no `pattern` on a substitution. The equivalent patterns are `^[A-Z0-9]{1,5}$` and `^[A-Za-z][0-9]+[A-Za-z]$`. New.
- **API-12.** `api/src/panther_api/problems.py:75-76`: every operation with a parameter documents a 422. So `GET /api/v1/jobs/{job_id}` lists one it can't return: `job_id` is a string, and a malformed one is a 404. New.
- **API-13.** `api/src/panther_api/routers/jobs.py:79`: `Location` comes from `app.url_path_for`, which leaves out the root path. Behind a proxy that serves the API under a prefix (`--root-path /scoring`), it points outside the prefix (reproduced). The frontend uses the body's `id`, so only clients that follow the header are affected. Use `request.url_for`. New.
- **API-14.** `api/CLAUDE.md:48` says to import only names in a module's `__all__`, but only `panther_engine.csnp` defines one. The API imports `InputError`, `report_tools` and `TOOLS` from `core.errors` and `core.tools`. Add `__all__` to the engine's public core modules, or reword the rule. New.
- **API-15.** `scoring-jobs` says the API "MUST NOT offer a way to list jobs", and no test pins it. Today `GET /api/v1/jobs` answers 405. New.
- **CSNP-8.** `engine/src/panther_engine/csnp/psep.py:192-200`: the trace-back walk has no guard against a cycle in a `.paml`'s parents, though `age()` has one. It can't happen with the surveyed library. **Earlier:** N7.
- **CSNP-9.** `engine/src/panther_engine/csnp/scoring.py:91` reaches `legacy` through `hits.legacy`; import it directly. **Earlier:** N8.
- **CSNP-10.** `engine/src/panther_engine/csnp/psep.py:145-153`, `legacy.py:213`, `rst.py:143`: a family's `.rst` is held three times while it's scored. Validating in the same pass would save 13 to 27 MiB per worker for `PTHR11695`. **Earlier:** N9.
- **CSNP-11.** `engine/src/panther_engine/csnp/scoring.py:63-71` and `blast.py:31, 52-53`. New.
  - `score()`'s docstring names `ValueError`, `InputError` and `BlastError`. It can also raise `LibraryFormatError`, `FileNotFoundError` and `DataFolderError`.
  - `legacy.find_an` raises a `ValueError` of the same type as the one for "input the API rejects".
  - A sequence that starts with `>` makes `blastp` exit 3, which becomes a `BlastError`, where `#`, `!` and `;` give an `InputError`. Only callers that bypass the API can send one.
- **ENG-12.** `engine/src/panther_engine/core/data.py:19-20`: `--data-dir ""` means the current folder, while an empty `PANTHER_DATA_DIR` is an error. **Earlier:** N2.
- **ENG-13.** `engine/src/panther_engine/core/errors.py:22-30`: `InputError.__reduce__` copies only `__dict__`, so a subclass's `__slots__` attributes are lost on the way back from a worker. That breaks `engine-core`'s promise. **Earlier:** N3.
- **ENG-14.** `engine/src/panther_engine/csnp/survey.py:379-382`: a duplicated member counts its family once per duplicate while the family is incomplete, and not at all once it's complete. **Earlier:** N4.
- **ENG-15.** `engine/src/panther_engine/csnp/cli.py:145-162` and `sample.py:134-139`: the sha256 overrides replace the pins without a warning, against `csnp-data`'s "MUST refuse". The build requires only one of a family's three files. **Earlier:** N5.
- **ENG-16.** `engine/src/panther_engine/core/process.py:33-43`: with no `input`, the child inherits stdin; a tool that read it waited for its 2 s timeout in a test. Captured output has no size limit. **Earlier:** N6.
- **ENG-17.** `engine/src/panther_engine/csnp/parity.py:721-724`: `parity reference --family TYPO` runs no step-3 case and exits 0. New.
- **ENG-18.** `engine/src/panther_engine/csnp/sample.py:122-133`: `sample build` creates the output folder and unpacks both archives into it before checking their sha256. A refused build leaves an empty output folder. New.
- **ENG-19.** `engine/src/panther_engine/core/data.py:24`: the error tells the reader to "pass --data-dir", a CLI flag. The API logs this message too, and has no such flag. New.
- **ENG-20.** `engine/tests/conftest.py:43`: `@pytest.mark.data("refmap")` raises `KeyError` in setup, not a clear message. New.
- **ENG-21.** `engine/src/panther_engine/csnp/cli.py:320, 335`: the number of families is printed before duplicates are removed. New.
- **ENG-22.** `psep-engine`'s "Data version" is tested only from the API (`api/tests/test_versions.py:50-61`), and `csnp/sample.py:47` keeps its own `VERSION = "9"` beside `scoring.py:19`. New.
- **ENG-23.** Spec wording is broader than the tests. New.
  - `csnp-data` says "every check", where `test_csnp_sample_data.py` rightly leaves out the BLAST checks.
  - `engine-core` says "no test that needs it is skipped", but natively in CI, the tests marked both `tools` and `data` skip for lack of `blastp`.
- **FE-13.** `frontend/src/features/csnp/checks.ts:37, 66`: lengths are counted in UTF-16 units, while Pydantic counts code points. So an input with many astral characters, such as emoji in a header, can be refused by the form and accepted by the API. It's contrived: 20,001 random drafts found no other disagreement. **Earlier:** N10.
- **FE-14.** `frontend/src/features/csnp/substitutions.ts:9`: JavaScript's `\s` also splits at no-break space, U+2028, U+3000 and U+FEFF, while `scoring-ui` says to split at whitespace and commas. Decide which counts, and pin it with a test. **Earlier:** N12.
- **FE-15.** `docs/manual-qa/02-csnp-form.md:130`: TC 2.6 says to clear the species box, then use the example. The example refills the box with `HUMAN`, so the request is sent. Say "use the example first". New.
- **FE-16.** `frontend/src/main.tsx:15-25`: the manual QA's "On a phone" steps run in mock mode. A phone reaches the dev server over plain http at a LAN address, so it has no `navigator.serviceWorker`. MSW's `worker.start()` then throws, and the top-level `await` stops the app from rendering. Catch the error and render anyway, or test phone widths in desktop devtools. New.
- **FE-17.** `frontend/src/components/VersionList.tsx:1` and `frontend/src/features/versions/versionsApi.ts:2` import schema types directly, not through `wire.ts`, the one module meant to know the API's field names. **Earlier:** N14.

## Gaps: What M1 Still Needs

The seven main specs are implemented: no requirement is missing, and nearly every scenario has an automated test. REPO-3 lists the exceptions. What's missing is the rest of M1.

| Service | Exists | Missing before parity can be shown | Open questions that block it |
| --- | --- | --- | --- |
| `csnp` | The port, with goldens on the 16-family sample (§7.3, §7.5, step 1 and the form's example); the API job; the form and results page; CI on the goldens, natively and in the image | The full-library parity run on staging, with a dated report in `docs/parity/`. It needs the staging server, the 19.2 GB library and the reference image. To go live: a checksum manifest of the full data, a deploy smoke test, and the website's move to the JSON API | Keep or fix rows 2, 3 and 5; `DATA-1` and `DATA-3`; the licence for a port of GPLv2 PSEP; CSNP-2 |
| `refmap` | The API contract, with its 422 rules (unapproved) and a 501; the schema and frontend types; `refmap-legacy-behaviour.md`. After this commit, the form (#35) | The engine's `map_ids` and `ORGANISM_CODES`; the PANTHER 19 classification files, whose source, count and format are unknown; goldens from `map_panther.pl`; a reference image; the wiring change; rows 9 and 10 approved | The organism key; the data layout, and jobs or synchronous (SPEC-5); what replaces `stats` and the whole-file download; extra columns after the ID; which CGI version production ran |
| `hmmscore` | A docstring stub; HMMER 3.4 in the images, with its version reported | A record of the legacy behaviour; a reference image (`pantherScoring` is private); the HMM library, and the FASTA file with its DBM index; a HMMER runner in `core`; the port of `pantherScore.pl`, and probably of the two CGIs; goldens; the API contract; the UI | Which CGI copies production ran; the prod and build library modes; who builds the data; input size limits |
| `treegrafter` | A docstring stub; HMMER and EPA-ng 0.3.8 in the images; divergence row 1, unapproved | A pinned EBI commit (`golden-setup.md` has no treegrafter section); an adapter that catches `SystemExit` and checks EPA-ng's result; provisioning of `prepare`'s output for each PAINT release; goldens from the pinned version; the API contract; the UI; row 1 approved | Python 3.13 support; PyPI or git; in-process or the CLI; the missing `treeGrafter.cgi` source |

Across all four, `docs/design/tech-stack.md` is still Proposed, and all four of its reviews are pending. Still open there:

- the staging server;
- input sizes;
- who builds each release's data;
- whether anything else calls the legacy URLs.

### Core, for the Next Three Services

CLAUDE.md wants shared code written once, in `core/`.

**Already there:**

- `run_tool`: an absolute program, an argument list, no shell, and a timeout;
- the registry of the four tools, with version reading;
- the `<PANTHER_DATA_DIR>/<service>/<version>` layout;
- sha256 manifests and `verify`;
- `InputError`, which survives pickling;
- a CLI with a subcommand per service;
- the `tools` and `data` test markers.

**Missing:**

- FASTA parsing, which hmmscore's batch mode and treegrafter need for multi-record input;
- per-job work folders with cleanup, for hmmscan's table output and EPA-ng's output folder;
- runner controls: the environment, stdin, a process-group kill and an output cap (ENG-1 to ENG-3, ENG-16);
- the tools' pinned versions, kept in core;
- a check that a service's data is there, for startup or readiness (CSNP-3);
- generic sample fetch, build and verify;
- one picklable error base;
- a generic parity harness. refmap's reference, `map_panther.pl`, is Perl too.

**Generic code that sits in `csnp/`:**

- `sample.py`'s download, unpack, fetch and reproducible tarball;
- `survey.py`'s streaming hash;
- `cli.py`'s copy of the API's normalisation (ENG-4);
- `parity.py`'s `Reference`, `diff_records`, `read` and `write`.

**EBI's `treegrafter.py`:**

- runs `epa-ng` with `subprocess.call` and no timeout, in its own temporary folder;
- imports Biopython, which would be the engine's first runtime dependency and needs a proposal.

Imported as a library, it bypasses `run_tool`. Run through `run_tool`, it hits ENG-3. Which version to pin needs team verification.

## Improvements

Changes that aren't fixes, but would make the code safer, faster or easier to maintain.

### For the API

- **`routers/jobs.py:47-60`:** serialise a finished job's body once, when it finishes. Today every poll re-validates and re-serialises it on the event loop: 37 to 40 ms for 100,000 mappings.
- **`runner.py:48-50`:** set `max_tasks_per_child` on the pool. Then a slow leak, or a heap grown by a large family such as `PTHR11695` (136 MB), doesn't last for the process's whole life.
- **A readiness endpoint,** beside the liveness check, that checks the data (CSNP-3) and the tools.

### For the Images and CI

- **`Dockerfile:165`:** set `UV_COMPILE_BYTECODE=1`. The API image has no `.pyc` files for its 1,908 modules, so every start and every spawned worker compiles its imports.
- **`Dockerfile:166-168` and `compose.yaml:43-52`:** add a `HEALTHCHECK`, and `init: true` or tini. PID 1 is Python, and won't reap a `blastp` orphaned when a worker is killed.
- **A hardened production run,** documented or in compose: `read_only`, a tmpfs `/tmp`, `cap_drop: ALL` and `no-new-privileges`. The image already scores a job that way.
- **`persist-credentials: false`** on every checkout (`ci.yml:41, 108, 160, 185, 232, 277, 347, 389`). The `repo` job runs npm install scripts while the token sits in `.git/config`.
- **Pin versions:** the buildx and BuildKit version (`ci.yml:233, 278`), and an exact Node in `.nvmrc`.
- **Repository settings:**
  - enable CodeQL;
  - enable private vulnerability reporting, and add a SECURITY.md, since the repository is public;
  - add a tag ruleset or immutable releases for `csnp-sample-*`, because "never replace the asset" is only a rule today.
- **A link checker** in the `repo` job, for REPO-12's broken archive links.

### For the Engine

- **`core/process.py:33-43`:** every service needs these in `run_tool`:
  - an explicit environment, with `BLAST_USAGE_REPORT=false` and `LC_ALL=C`;
  - `stdin=DEVNULL` when there's no `input`;
  - a process-group kill;
  - an optional output cap, or a bytes mode.
- **`csnp/parity.py:124-127`:** set `LC_ALL=C` for the Perl reference in code, not only in the Dockerfile. `parse_blastp.pl` sorts through a shell, and when identities tie, it falls back to a whole-line comparison that depends on the locale (`MAP-1`).
- **`core/tools.py`:** keep each tool's pinned version there, so `tools` and the API can flag a binary that isn't the pinned one. A `require(name)` would then replace the direct `shutil.which` calls in `csnp/blast.py:54` and `csnp/parity.py:90`.
- **`csnp/sample.py` and `csnp/survey.py`:** move the generic download, unpack, verify, reproducible-tarball and streaming-hash code into core. Unpack in one streaming pass, and only the manifest's files; write the manifest atomically.
- **One picklable error base in core.** Today `core/errors.py:22-30` and `csnp/library.py:29-31` each implement `__reduce__`.
- **`psep.py:383-388`:** stop `correct_site` once `residues >= position`. The result is the same, and it saves a pass over the gene's sequence for every SNP: up to about 9,000 columns × 1,000 SNPs in `PTHR11695`.
- **Document the Perl's `..` flip-flop** in `legacy.py:202-209` and `psep.py:145-153`.
  - In the Perl, its state persists across SNPs.
  - The port resets it for each SNP. That's equivalent only because no line of the sample's `.rst` files matches.
  - Add that check to the survey.
- **`psep.py:138-143`:** build `GeneLookup` after the strict `.orig.tree` reader has run. Then a malformed gene line is a `LibraryFormatError`, not a bare `ValueError`.

### For the Frontend

- **`app/api/errors.ts:17-25`:** treat any error response without problem details as "not the API", as `scoring-ui` defines it. Today a static host's 405, or a proxy's 413 for a large sequence, says the job "couldn't be started, try again".
- **Clear the submit alert** when the client checks fail or the example is used (`useSubmitCsnp.ts:34`, `CsnpForm.tsx:35-37`).
- **React keys:** `VersionList.tsx:26` and `ToolsResult.tsx:28` key on labels and tool names, which can collide. Add the index.
- **`SpeciesField.tsx:39-52`:** while the list loads, the field is a disabled Select with only a placeholder. `HUMAN`, which a submit sends, is invisible.
- **Deployment** (needs team verification). The static host must:
  - fall back to `index.html` for `/csnp` and `/jobs/:id`;
  - serve `/api/v1` on the same origin, since `api.ts:8` is relative;
  - accept request bodies larger than nginx's 1 MB default.
- **Load routes lazily.** The bundle is one 586 kB chunk, 188 kB gzipped.
- **E2E checks:** the e2e `BUILD_DETAILS` patterns lack the unit tests' file-path checks (`/usr/`, `/opt/`, `C:\`).
- **A favicon:** every load gets a 404 for `/favicon.ico`.

## Earlier Findings at `64174c9`

Every finding of the earlier draft still holds. None was fixed: `engine/` and `frontend/src` haven't changed since `13d97b3`, and neither has the API's runner, store or settings.

| Earlier | Here | Status at `64174c9` | New evidence |
| --- | --- | --- | --- |
| M1 | CSNP-1 | Holds | Eight crafted BLAST+ lines; exposure measured |
| M2 | CSNP-4 | Holds | Titin took 272 s |
| M3 | CSNP-3 | Holds | Now reproduced |
| M4 | API-1 | Holds | refmap raises the largest valid body to about 13 MB |
| M5 | API-2 | Holds | |
| L1 | REPO-2 | Holds; raised to Medium | Happened again with #30 and #50; `64174c9`'s area jobs never ran |
| L2 | REPO-3 | Holds | Merged with L14 and the scenarios checked only by hand |
| L3 | REPO-4 | Holds | Reproduced: 5 of 12 polls were 404s |
| L4 | ENG-1 | Holds; raised to Medium | Reproduced: about 10 s per call |
| L5 | REPO-5 | Holds | |
| L6 | REPO-6 | Holds | pip comes from the base image, not uv |
| L7 | REPO-7 | Holds | Root `npm audit`: 3 high, 2 low; `re2js` needs an override |
| L8 | REPO-8 | Holds | |
| L9 | REPO-9 | Holds | |
| L10 | API-7 | Holds | |
| L11 | API-3 | Holds | Now reproduced |
| L12 | API-8 | Holds | refmap makes it larger; a poll measured |
| L13 | API-9 | Holds | |
| L14 | REPO-3 | Holds | |
| L15 | CSNP-6 | Holds | |
| L16 | ENG-5 | Holds | |
| L17 | ENG-6 | Holds | A realistic trigger reproduced |
| L18 | ENG-7 | Holds | |
| L19 | ENG-8 | Holds | Two more paths |
| L20 | ENG-9 | Holds | |
| L21 | FE-4 | Holds | refmap's job type isn't in `WireJob` |
| L22 | FE-3 | Holds | A realistic input: blank CRLF lines |
| L23 | FE-1 | Holds; raised to Medium | Trigger reproduced; it takes the whole page |
| L24 | FE-7 | Holds | |
| L25 | FE-8 | Holds | |
| L26 | FE-9 | Holds | More cases |
| L27 | FE-10 | Holds | |
| L28 | FE-12 | Holds; one claim wrong | A job id changing on a mounted page isn't handled correctly today (FE-5) |
| N1 | API-10 | Holds | |
| N2 | ENG-12 | Holds | |
| N3 | ENG-13 | Holds | |
| N4 | ENG-14 | Holds | |
| N5 | ENG-15 | Holds | |
| N6 | ENG-16 | Holds | |
| N7 | CSNP-8 | Holds | |
| N8 | CSNP-9 | Holds | |
| N9 | CSNP-10 | Holds | |
| N10 | FE-13 | Holds | |
| N11 | FE-6 | Holds; raised to Low | Leads to FE-5 |
| N12 | FE-14 | Holds | |
| N13 | REPO-10 | Holds; raised to Low | More spellings |
| N14 | REPO-12, FE-17 | Holds | More drift |

Corrections to the draft's "Checked and Found Sound" lists:

- **"`run_tool` … kills the child on timeout":** only the direct child (ENG-3).
- **"`sample build` refuses a wrong archive before writing anything":** it leaves an empty output folder (ENG-18).
- **"the parity harness compares exact text":** true for steps 2 and 3. Step 1's output passes through ENG-2's rewriting, which is harmless for the PANTHER 9 headers.
- **"The status is a `role=status` live region":** true, but its first status usually isn't announced (FE-9).
- **`getCorrectnum`, ported "line for line":** true except that the Perl's flip-flop state persists across SNPs. No output differs on the sample (Improvements).

## Checked and Found Sound

What was checked and found to have no problem, so the coverage is clear.

### In the Repository, Images and CI

- **Actions:**
  - every action is pinned to a full commit SHA that matches its tag;
  - permissions are minimal;
  - there's no `pull_request_target`, no secret, and no `${{ }}` inside `run:`.
- **`ci-passed`** needs all nine jobs, and fails on a failed or cancelled one.
- **Path filters** reach the jobs that need each file.
- **Caches** are keyed on what they hold, and re-verified on a hit.
- **Pinned inputs:**
  - base images are pinned by digest;
  - BLAST+ and HMMER are checked with `sha256sum --strict`;
  - micromamba refuses a lock line with a wrong sha256.
- **The API image at `64174c9`:**
  - it runs as uid 1000, with no git, curl, wget, gcc or make;
  - it has only `perl-base`, and no `/opt/csnp-reference`;
  - SIGTERM stops it in 1 s, even after a job ran;
  - the documented 422, 501 and species responses match `docs/testing/api.md` exactly.
- **Live settings:**
  - secret scanning and push protection are on;
  - CODEOWNERS has no errors;
  - every merge to `main` came through a pull request;
  - the sample asset's digest matches `sample.json`.

### In the API

- **Errors:**
  - every error is problem details, and a 405 keeps `Allow`;
  - a 422 never echoes a submitted value (keys aside, API-4);
  - a 500 shows nothing about the exception.
- **Jobs:**
  - job ids are random UUID4s, and a malformed id is a 404;
  - only the event loop touches the store;
  - jobs run in the order they were submitted.
- **Workers:**
  - they start with `spawn`;
  - an engine `InputError` becomes a 422 with its message, across processes;
  - a dead worker fails only the jobs it held, and the pool is replaced.
- **The 100-error cap:** a 422 for 100,000 bad IDs is under 20 kB.
- **refmap:**
  - a valid 100,000-ID request is validated in about 31 ms, then answered with a 501, and no job is created;
  - the schema's patterns agree with the validators;
  - the input rules match `map_panther.pl` and the CGI, except where rows 9 and 10 say.
- **Schema and versions:**
  - the committed schema matches the one served;
  - versions are read once, at startup;
  - the species list is built once.

### In the cSNP Port

- **The reference:** the legacy scripts are unchanged from `cebb5ab` to the legacy repository's HEAD.
- **Step 1:** `blastp` gets `run_blastp.pl`'s options, with no shell and no temporary file, and the query goes on stdin.
- **Step 2:** 2,601 fuzzed SNP records gave no difference between `hits.parse` and `parse_blastp.pl` in the reference image. The fuzz covered:
  - random alignments, with gaps on both sides, `*` and `X`;
  - offset starts;
  - positions such as `010`, `+5`, `5.0`, 0 and past the end;
  - wrong wild types;
  - three species.
- **Step 3:** a new seeded run gave no difference: 4,245 cases in 9 families, through `parity cases`, `reference` and `check`.
  - The self-check reproduced §7.3 and §7.5.
  - Walks stopped at every kind of node.
- **Read against the Perl by hand:**
  - `getCorrectPosition`;
  - `getCorrectnum` (`SCORE-8`);
  - the last header match (`SCORE-2`);
  - the walk: a strict `> 0.99`, with NaN never kept;
  - `getYear`, with the 4,200 cap and `DATA-3`;
  - `ageMessage` and `getPdel`;
  - the record format, and the CGI's family cut.
- **Database ids:** all 570,173 have two colons and two pipes, and no comma. So the regex emulation never meets a metacharacter other than `.`.
- **Independence and memory:**
  - `score()` keeps no module state, so calls are independent;
  - a `.paml` is streamed, never held, as `tech-stack.md` advises.

### In the Engine's Core and Tooling

- **`run_tool`** takes an absolute program and an argument list, and uses no shell. Shell metacharacters reach the tool unchanged.
- **Pickling:** `InputError`, `LibraryFormatError` and `BlastError` all cross a spawn worker intact.
- **Manifests:**
  - they reject absolute paths, `..`, empty or `.` parts and backslashes;
  - digests must be 64 lower-case hex digits.
- **`fetch`:**
  - it checks the sha256 before unpacking, and uses https only;
  - it checks every member before extracting, then applies tarfile's `data` filter;
  - `--from` stays offline.
- **`build`:** byte-reproducible, with all three pins checked before any output is written.
- **The sample:** `sample.json` lists 16 families and 53 files. There are 648 step-3 cases and 296 step-2 SNPs, as `inputs.md` says.

### In the Frontend

- **Input checks:** 20,001 random drafts went through the form's checks and the API's own `CsnpInput`. They included NBSP, U+2028, BOM, ß, dotless ı, ligatures, emoji, C0 controls and DEL. No field disagreed, except for FE-13.
- **Species:** the species endpoint and the validator have the same 85 codes.
- **Errors:** a 422's `loc` lands on its field, and "can't be reached" is told apart from an error from the API.
- **Polling:**
  - it stops after success, on a 404 and on an error;
  - it unsubscribes on unmount, and requests never overlap;
  - "Try again" resumes it.
- **Rendering:** API text is rendered as text only, with no `dangerouslySetInnerHTML`, and the job id is encoded.
- **The production build** has no MSW code, no worker and no "mock data" text.
- **Results** are shown exactly as given, with the job's own versions.
- **Conventions:** `frontend/CLAUDE.md`'s conventions are followed.

### In the Specs

- **Main specs:** no requirement in the seven main specs is unimplemented.
- **Input scenarios:** the cSNP and refmap input scenarios are tested with distinctive values that must not be echoed.
- **Divergence rows:** rows 2 to 8 match what the code does.

## After `64174c9`

During this review, `origin/main` moved to `46410f1`. Two pull requests merged at 20:44 PDT on 2026-10-30, and neither is reviewed here:

- **#50** adds a skill (`spill-the-tea`, under `.claude/skills/` and `.agents/skills/`) and puts #30's parts into `api/CLAUDE.md`.
- **#35** adds the refmap form and results page: 44 files, mostly in `frontend/`.
  - It adds `RefmapJob` to `WireJob`, with a refmap case (part of FE-4).
  - Its mock now accepts refmap jobs and maps the IDs, while the API answers 501.
  - It adds no `errorElement` (FE-1), and `useSubmitCsnp` still navigates after its `await` (FE-6).

Pull request #35's CI run cancelled #50's (REPO-2).

Pull request #35 is now reviewed in `2026-11-02-refmap-form.md`, untracked.

## Follow-ups

None of these has an OpenSpec change yet. The change names are suggestions for the owners.

| Follow-up | Covers | Owner | OpenSpec change |
| --- | --- | --- | --- |
| Finish and archive `add-quality-gates`, and add the missing deny rules to `.claude/settings.json` | REPO-10, SPEC-6 | All three developers | `add-quality-gates`'s remaining tasks |
| The science owner on the species filter, on who approves divergences, and on row 1 | CSNP-2, SPEC-4 | Science owner, engine developer | None until decided. A changed score then needs a divergence row and a change |
| refmap: approve or reject rows 9 and 10; record the data layout and jobs or synchronous; a MODIFIED "Submit a job"; rows for cSNP's refusals; archive `add-apoe-to-csnp-sample` | SPEC-1, SPEC-2, SPEC-3, SPEC-5 | Engine developer, API developer | [`add-refmap-job`](../../openspec/changes/add-refmap-job/), before it's archived |
| cSNP: the identity formula, BLAST+'s time limit, a library check, telling status 1 apart, path quoting, tests and nits | CSNP-1, CSNP-3 to CSNP-11 | Engine | [`fix-csnp-blast-handling`](../../openspec/changes/fix-csnp-blast-handling/) covers CSNP-1 and CSNP-3 to CSNP-6, and CSNP-7's tie line. CSNP-7 to CSNP-11 have none yet |
| Images and runtime: `BLAST_USAGE_REPORT=false`, `--workers 1`, compose on `127.0.0.1`, a root-owned venv, ignoring sample tarballs, the supply chain | ENG-1, REPO-4 to REPO-8 | Engine, API | ENG-1: [`fix-csnp-blast-handling`](../../openspec/changes/fix-csnp-blast-handling/). REPO-4 to REPO-8: none yet, to propose, such as `harden-images` |
| CI: keep the runs on `main`, run every job on a push, timeouts, compose, the in-image API suite, the image checks, `dist`, the `@api` e2e specs | REPO-2, REPO-3, REPO-9, FE-12 | Whoever owns CI | None yet: to propose. Today `openspec-change` doesn't require one for `.github/` (REPO-12) |
| API load and robustness: body size, a queue cap, settings bounds, resubmitting on a broken pool, the store, logging, the echoed keys, the docs page's assets and redirect, and the nits | API-1 to API-15 | API | None yet: to propose, such as `bound-api-load`, with new `scoring-jobs` and `api-service` requirements |
| Engine core and data tooling | ENG-2 to ENG-23 | Engine | None yet: to propose, such as `harden-engine-tooling`. ENG-4 together with the API |
| Frontend robustness and accessibility | FE-1 to FE-17 | Frontend | None yet: to propose. FE-8 changes `scoring-ui` first |
| Doc drift | REPO-11, REPO-12 | Each doc's owner | None needed: docs only |
| Review #50, which merged after this commit. #35 is reviewed in `2026-11-02-refmap-form.md`, untracked | FE-4 | Frontend, API | None needed: a review, not a change |
