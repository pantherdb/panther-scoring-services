# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **The frontend stack and its conventions:** [docs/design/frontend-stack.md](../../../docs/design/frontend-stack.md) (Accepted) and [frontend/CLAUDE.md](../../../frontend/CLAUDE.md).
- **The `hmmscore` contract:** [add-hmmscore-job](../add-hmmscore-job/design.md), decisions 2 (the request and result) and 3 (the input rules), its `501` until the engine scores, its residue limit checked by the API (decision 7), and its running cap (decision 6). Its `scoring-input` delta is the rule list the form mirrors.
- **The busy `503`:** `scoring-jobs`, "A cap on waiting jobs", with `Retry-After` exposed to another origin (`api/src/panther_api/cors.py` 16).
- **The legacy service:** `docs/parity/hmmscore-legacy-behaviour.md`, from `add-hmmscore-job`. Its quirk IDs (`HMMSCORE-1`, …) are used here.
- **The pattern this change repeats:** the archived [add-refmap-form](../archive/2026-10-30-add-refmap-form/design.md) and [add-csnp-form](../archive/2026-10-29-add-csnp-form/design.md), and how [wire-refmap](../archive/2026-11-10-wire-refmap/design.md) removed refmap's `501`.

The behaviour is in [specs/scoring-ui/spec.md](specs/scoring-ui/spec.md).

## Goals / Non-Goals

**Goals:**

- A user can paste a protein, see every mistake the API would reject before anything is sent, and read the hit and its alignment as the legacy page showed them.
- The day the API returns `202` for `hmmscore`, the form and the results work with no frontend change but the wiring's removals.

**Non-Goals:**

- Several sequences, or a file upload: the contract takes one sequence.
- The site's relatedness icon (proposal, Open Questions).
- Parsing the alignment into domains, or downloading it.
- A busy message on the cSNP and refmap forms: their requirements give every status but a `422` one message ("cSNP job not started").

## Decisions

### 1. The page

- **`src/features/hmmscore/`:** `HmmscorePage`, `HmmscoreForm`, `useSubmitHmmscore`, `checks.ts` and `index.ts`. One box, so the draft is component state, not a reducer. `/hmmscore` in `router.tsx` renders the page, with `errorElement: <ErrorPage />`, in place of its coming-soon page.
- **`services.ts`:** HMM scoring gains `action`, "Score a protein sequence", and keeps `comingSoon: true` until the wiring, as ID mapping did. While it's set, the page shows a short notice that HMM scoring isn't available yet, so the flag the wiring turns off removes the notice too.
- **"Edit and resubmit":** `formFields.ts` gains `HMMSCORE_FIELDS = ['sequence']`, and `KEPT_FIELDS` in `features/jobs/keptInput.ts` (11) gains `hmmscore`. Without it, `isEditable('hmmscore')` is false, and `keepInput` and `useEditedInput` don't type-check with `'hmmscore'`.
- **The example** is the help page's APOE (`tips_exampleHmmScoreInput_content.jsp` 9 to 20): 317 residues in lines of 35, no header. It's cSNP's example sequence, so it moves to `src/components/apoe.ts`, which `csnp/example.ts` and the hmmscore form import. Features don't import each other.

### 2. The checks

cSNP's `checkSequence` moves from `features/csnp/checks.ts` to `src/components/sequence.ts`, with the limits as exported constants: `LONGEST_RAW_SEQUENCE`, `CSNP_MOST_RESIDUES` (50,000) and `HMMSCORE_MOST_RESIDUES` (10,000). If the product owner's limit changes (#74), it's one line, and its tests follow.

- **It takes each service's rules:** the most residues, the characters accepted, the message naming them, and whether one final `*` is allowed. A character set alone can't say "`*` once, and only last". With `finalStop`, the check normalises, tests for empty, then drops one final `*` before testing the characters and counting, so `MKVL*` passes and `MKV*L` and `MKVL**` don't.
- **Letters are A to Z, either case,** an ASCII class, not a Unicode one, since the API refuses `Ä`. cSNP keeps its printable-ASCII rule and message.
- **Residues are letters:** a final `*` isn't counted, as `add-hmmscore-job` now says too.
- **The form checks the most the setting allows,** a rule that holds on every server. The server's own limit, which can be lower, comes back as a `422` on the field, with the API's message naming it.
- **Tests move with it:** `checkSequence`'s cases leave `tests/features/csnp/checks.test.ts` for `tests/components/sequence.test.ts`, mirroring `src/`, rather than a one-argument wrapper in `csnp/checks.ts`.

### 3. Submit failures

The `useSubmit*` hooks repeat the same classification, and `csnp/SubmitAlert.tsx` and `refmap/SubmitAlert.tsx` differ only in an import. Both move to `src/components/`:

- **`submitProblem(error)`** returns `unavailable` for a `501` with problem details, `busy` for a `503` with problem details, `unreachable` as `isUnreachable` says, and `failed` for the rest. A `501` or `503` without problem details came from something in between, such as nginx answering 501 for an unsupported `Transfer-Encoding`, and is `unreachable`. Each hook still handles its `422` first, on its own fields.
- **cSNP and refmap** show `unavailable` and `busy` as `failed`, as their requirements say. hmmscore shows each.
- **`Retry-After`:** `startJob` gains a `transformErrorResponse` that adds the header's seconds to the error, since `unwrap()` drops the response. Whole seconds give "in about N seconds" (or minutes, past 90); anything else gives "in a few minutes".
- **`SubmitAlert`** takes the problem, the service's title for the `unavailable` and `busy` texts, and the seconds.

### 4. The results

In `src/features/jobs/`:

- **`HmmscoreHit`** shows the PANTHER ID as a link to `https://www.pantherdb.org/panther/family.do?clsAccession=` plus the ID through `encodeURIComponent`, as the site linked to its own family page (`HMMHitBean.java` 47 to 49); the name; and the E-value and score as text, exactly as given. The link follows `ApiDocsLink.tsx`: `target="_blank"`, `rel="noopener noreferrer"`, and an accessible name ending "(opens in a new tab)".
- **`AlignmentText`** is a `<pre>` in an `overflow-x-auto` box, with no wrapping, so `hmmsearch`'s columns line up and a long line scrolls within the box, not the page. The box has `tabIndex={0}`, `role="region"` and the name "Alignment", so a keyboard can scroll it in browsers that don't focus scrollers, such as Safari (WCAG 2.1.1).
- **Titles from `services.ts`:** `JobDetails` heads a job with `service(job.service).title`, keeping its own title only for `tools`, which isn't a service there. The `SERVICE_TITLES` rows for cSNP and refmap equal those titles today, so their headings don't change.
- **No thresholds in the UI.** The page doesn't repeat the site's sentence about the cutoff, which states it backwards (`HMMSCORE-4`), or its relatedness icon.

### 5. Checking a long job

The job page checks a queued or running job every second (`JOB_POLL_INTERVAL_MS`, `jobsApi.ts` 14). An hmmscore job can wait behind the running cap and then run up to 720 s, so one tab would send hundreds to thousands of `GET`s. The page checks every second for a job's first 30 seconds on the page, then every 5 seconds. The tools job (about 1.5 s) and a typical cSNP job still show each status as it happens, and a 720 s job costs about 170 checks.

### 6. Mocks and tests

- **Mocks:** an `hmmscore` `POST` returns a queued job that succeeds with an obviously made-up hit, `PTHR00000:SF1`, named as mock data, with an alignment marked as mock whose lines are 200 characters, wider than a phone. Tests reproduce the real `501` and a busy `503` with `server.use`.
- **Vitest:** the shared check (cSNP's cases moved, hmmscore's added), `submitProblem`, the form (example, notice, checks, `422`, `501`, `503`, `500`, network, each beside a success), the results (hit, link, no hit, running, the alignment kept and focusable), the titles, the polling interval and the mocks.
- **Playwright:** mock mode on desktop and mobile, where the alignment box scrolls and the page doesn't; api mode against the real `501` and a `422`.
- **The coming-soon tests move to `/treegrafter`:** `tests/components/ComingSoonPage.test.tsx` (12, 27) and `e2e/shell.spec.ts` (79) open `/hmmscore` today.

## Risks / Trade-offs

- **[The server's limit is lower than the form's]** → The API's `422` names it on the field, and the sequence is kept.
- **[A wide alignment on a phone]** → It scrolls within its box; an e2e test checks the page doesn't, with a mock alignment wide enough to need it.
- **[A long queue]** → The page shows "queued" with no reason while an hmmscore job waits for the running cap. Checking every 5 seconds keeps the cost down; saying why it waits is a later idea.
- **[The busy `503` comes sooner for hmmscore]** → The form says when to try again. The `Retry-After` is sized for cSNP, and the waiting cap is shared; both are `add-hmmscore-job`'s Risks.
- **[The mock hit's link]** → In mock mode, `PTHR00000:SF1` links to pantherdb.org's page for a family that doesn't exist. The hit is marked as mock data.
- **[The `501` path outlives its purpose]** → The wiring change removes the `501` requirement and the notice, as `wire-refmap` did refmap's. The submit failures stay in their own requirement.
