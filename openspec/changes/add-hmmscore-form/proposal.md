# Proposal

**Area:** frontend. Outside `frontend/`, it adds one manual QA checklist, `docs/manual-qa/04-hmmscore-form.md`, and edits `docs/testing/frontend.md`. It changes nothing in `api/` or `engine/`.

**Depends on:**

- **`add-hmmscore-job`, applied and merged:** the `hmmscore` job contract, its `422`s and its `501`, and the regenerated `frontend/src/app/api/schema.d.ts`. The form's code starts after that change's code is on `main`, not after its proposal (#70).
- **`wire-refmap`**, archived in #69: this change modifies two `scoring-ui` requirements that `wire-refmap` also modifies ("Services that aren't available yet" and "The home page shows every service"). Its text here starts from `wire-refmap`'s.

**Follows `add-hmmscore-job` as applied in #76,** which took this review's points on the API side: the residue limit doesn't count a final `*`, a sequence with no letters is refused, and its Risks name the busy `503`'s `Retry-After`. #76 then accepted `.`, `_`, `~` and `*` anywhere, after the engine developer measured them again on amd64, and the form's checks follow.

## Why

`add-hmmscore-job` settles hmmscore's contract. Users have no way to score a sequence from the new UI. Building the form, the submit flow and the results now, against the real `422`s and `501`, means the UI is ready the day the engine's scoring is wired in, as `add-refmap-form` (#35) did for refmap.

## What Changes

- **An HMM scoring page at `/hmmscore`,** opened from HMM scoring's tab and its home page card, with one sequence box and a "Use an example" action that fills in the legacy help page's human APOE (`tips_exampleHmmScoreInput_content.jsp` 9 to 20). Until the wiring, a short notice on the form says HMM scoring isn't available yet.
- **Client checks** that mirror `scoring-input`'s hmmscore rules, with the most residues the setting allows, 10,000, counting every character but a final `*`. A sequence over the server's own limit is told by the API's `422`, on the field.
- **Submitting** through the existing `startJob` mutation: a `202` opens `/jobs/{id}`; the API's `501` says, in fixed text, that HMM scoring isn't available yet; a busy `503` says when to try again, from `Retry-After`; an unreachable API and any other failure reuse the other forms' messages. Each keeps the sequence.
- **hmmscore results on the job page:** the hit's PANTHER ID, linking to its page on pantherdb.org in a new tab, its name, its E-value and bit score as the API gives them, and the alignment as monospaced text that scrolls within its own box, by keyboard too. With no hit, it says there were no hits to PANTHER for the sequence.
- **HMM scoring's tab and card** open the form, and keep the "coming soon" mark until the wiring, as ID mapping did. A job's next step links to an empty form, and "Edit and resubmit" works.
- **Shared with the cSNP and refmap forms,** in `src/components/`: the sequence check and its limits, the APOE sequence, the submit-failure classification and its alert. The job page takes every service's title from `services.ts`, and checks a long job less often after its first 30 seconds.
- **Mocks:** a mocked `hmmscore` job succeeds with an obviously made-up hit and an alignment wider than a phone. Tests reproduce the real `501` and a busy `503` with `server.use`.
- **Docs:** `docs/manual-qa/04-hmmscore-form.md`, and `docs/testing/frontend.md` for mocked `hmmscore` jobs.

No new dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui`: new requirements for the hmmscore form, its notice, its checks, its `422`s, its `501`, its other submit failures, opening its job, its results, the family link and the alignment. "Services that aren't available yet", "The home page shows every service" and "The next step from a job's page" are MODIFIED, so HMM scoring opens its form.

## Impact

- **Frontend code:** a new `src/features/hmmscore/`; `src/features/jobs/` (the hmmscore result, the titles, the next step, `KEPT_FIELDS`, the polling interval, `startJob`'s `Retry-After`); `src/features/csnp/` and `src/features/refmap/` (the shared check, example and submit failures); `src/components/`; `src/app/services.ts`, `router.tsx`, `formFields.ts` and `api/wire.ts`; `src/mocks/`; tests in `tests/` and `e2e/`.
- **API contract:** none. The form reads the types `add-hmmscore-job` generates.
- **Parity with the reference:** this change scores nothing, and the page shows the API's values as given. Its checks ship two divergences that `add-hmmscore-job` adds to `docs/parity/divergences.md` (its task 1.2):
  - **the residue limit,** 10,000 where the reference took 50,000, approved by the product owner on 2026-11-12;
  - **the refused sequences,** those the API refuses that the reference read differently or answered no hit for (`-`, no letters, digits and other characters, a `>` inside the sequence), proposed, and awaiting the engine developer's approval. The form's code waits for it (tasks.md, Blockers). If it's rejected, `scoring-input` changes and the form's checks follow it.

## Open Questions

None open. Answered on #71:

- **The relatedness label** (`PantherScore.java` 110 to 120) stays out of this change. If it's shown later, the API computes it, so panther-site-java doesn't keep its own cutoffs (engine developer); whether to show it is the product owner's call. Deferred.
- **An endpoint for the server's residue limit:** not now. The form checks 10,000, and the API's `422` names a server's lower limit (`add-hmmscore-job`, design.md, decision 7). A later idea.
