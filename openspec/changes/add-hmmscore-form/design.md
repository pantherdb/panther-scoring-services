# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **The frontend stack and its conventions:** [docs/design/frontend-stack.md](../../../docs/design/frontend-stack.md) (Accepted) and [frontend/CLAUDE.md](../../../frontend/CLAUDE.md).
- **The `hmmscore` contract:** [add-hmmscore-job](../add-hmmscore-job/design.md), decisions 2 (the request and result) and 3 (the input rules), its `501` until the engine scores, and its residue limit checked by the API (decision 7). Its `scoring-input` delta is the rule list the form mirrors.
- **The legacy service:** `docs/parity/hmmscore-legacy-behaviour.md`, from `add-hmmscore-job`. Its quirk IDs (`HMMSCORE-1`, …) are used here.
- **The pattern this change repeats:** the archived [add-refmap-form](../archive/2026-10-30-add-refmap-form/design.md) and [add-csnp-form](../archive/2026-10-29-add-csnp-form/design.md): client checks that mirror the API, `422`s on their fields, a fixed-text `501`, `isUnreachable`, and the job page's per-service result.

The behaviour is in [specs/scoring-ui/spec.md](specs/scoring-ui/spec.md).

## Goals / Non-Goals

**Goals:**

- A user can paste a protein, see every mistake the API would reject before anything is sent, and read the hit and its alignment as the legacy page showed them.
- The day the API returns `202` for `hmmscore`, the form and the results work with no frontend change.

**Non-Goals:**

- Several sequences, or a file upload: the contract takes one sequence.
- The site's relatedness icon (proposal, Open Questions).
- Parsing the alignment into domains, or downloading it.

## Decisions

### 1. The page

- **`src/features/hmmscore/`:** `HmmscorePage`, `HmmscoreForm`, `useSubmitHmmscore`, `SubmitAlert`, `example.ts` and `index.ts`. One box, so the draft is component state, not a reducer. `/hmmscore` in `router.tsx` renders the page, with `errorElement: <ErrorPage />`, in place of its coming-soon page.
- **`services.ts`:** HMM scoring gains `action`, "Score a protein sequence", and keeps `comingSoon: true` until the wiring, as ID mapping did. `formFields.ts` gains `HMMSCORE_FIELDS = ['sequence']`, so "Edit and resubmit" works.
- **The example** is the help page's APOE (`tips_exampleHmmScoreInput_content.jsp` 9 to 20): 317 residues in lines of 35, no header. It's cSNP's example sequence, so both forms import one constant.

### 2. The checks

cSNP's `checkSequence` moves from `features/csnp/checks.ts` to `src/components/sequence.ts`, since features don't import each other. It takes the residue limit and the characters accepted as arguments, so cSNP's behaviour and messages don't change, and hmmscore's follow its own `scoring-input` rules.

- **The form checks the most the setting allows,** a rule that holds on every server. The server's own limit, which can be lower, comes back as a `422` on the field, with the API's message naming it.
- *Alternative:* an endpoint for the server's limit, so the field's description can say it. Not now (proposal, Open Questions).

### 3. The results

In `src/features/jobs/`:

- **`HmmscoreHit`** shows the PANTHER ID as a link to `https://www.pantherdb.org/panther/family.do?clsAccession=<id>`, opening in a new tab, as the site linked to its own family page (`HMMHitBean.java` 47 to 49); the name; and the E-value and score as text, exactly as given. The job is titled "HMM scoring", and its next step links to an empty form.
- **`AlignmentText`** is a `<pre>` in an `overflow-x-auto` box, with no wrapping, so `hmmsearch`'s columns line up and a long line scrolls within the box, not the page.
- **No thresholds in the UI.** The page doesn't repeat the site's sentence about the cutoff, which states it backwards (`HMMSCORE-4`), or its relatedness icon.

### 4. Mocks and tests

- **Mocks:** an `hmmscore` `POST` returns a queued job that succeeds with an obviously made-up hit, `PTHR00000:SF1`, named as mock data, with a short alignment marked as mock. Tests reproduce the real `501` with `server.use`.
- **Vitest:** the shared check (cSNP's cases still pass), the form (example, checks, `422`, `501`, `500`, network, each beside a success), the results (hit, no hit, running, the alignment kept) and the mocks.
- **Playwright:** mock mode on desktop and mobile, where the alignment box scrolls and the page doesn't; api mode against the real `501` and a `422`.

## Risks / Trade-offs

- **[The server's limit is lower than the form's]** → The API's `422` names it on the field, and the sequence is kept.
- **[A wide alignment on a phone]** → It scrolls within its box; an e2e test checks the page doesn't.
- **[The `501` path outlives its purpose]** → The wiring change removes it, as `wire-refmap` did refmap's.
