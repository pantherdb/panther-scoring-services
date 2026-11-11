# Proposal

**Area:** frontend. Outside `frontend/`, it adds one manual QA checklist, `docs/manual-qa/04-hmmscore-form.md`, and edits `docs/testing/frontend.md`. It changes nothing in `api/` or `engine/`.

**Depends on:**

- **`add-hmmscore-job`:** the `hmmscore` job contract, its `422`s and its `501`, and the regenerated `frontend/src/app/api/schema.d.ts`. This change merges after it.
- **`wire-refmap`**, archived first: this change modifies two `scoring-ui` requirements that `wire-refmap` also modifies ("Services that aren't available yet" and "The home page shows every service"). Its text here starts from `wire-refmap`'s.

## Why

`add-hmmscore-job` settles hmmscore's contract. Users have no way to score a sequence from the new UI. Building the form, the submit flow and the results now, against the real `422`s and `501`, means the UI is ready the day the engine's scoring is wired in, as `add-refmap-form` (#35) did for refmap.

## What Changes

- **An HMM scoring page at `/hmmscore`,** opened from HMM scoring's tab and its home page card, with one sequence box and a "Use an example" action that fills in the legacy help page's human APOE (`tips_exampleHmmScoreInput_content.jsp` 9 to 20).
- **Client checks** that mirror `scoring-input`'s hmmscore rules, with the most residues the setting allows. A sequence over the server's own limit is told by the API's `422`, on the field.
- **Submitting** through the existing `startJob` mutation: a `202` opens `/jobs/{id}`; a `501` says, in fixed text, that HMM scoring isn't available yet, keeping the sequence; an unreachable API and any other failure reuse the other forms' messages.
- **hmmscore results on the job page:** the hit's PANTHER ID, linking to its page on pantherdb.org, its name, its E-value and bit score as the API gives them, and the alignment as monospaced text that scrolls within its own box. With no hit, it says there were no hits to PANTHER for the sequence.
- **HMM scoring's tab and card** open the form, and keep the "coming soon" mark until the wiring, as ID mapping did. A job's next step links to an empty form, and "Edit and resubmit" works.
- **The sequence check is shared** with the cSNP form, moved to `src/components/`, and the two forms share the APOE sequence.
- **Mocks:** a mocked `hmmscore` job succeeds with an obviously made-up hit. Tests reproduce the real `501` with `server.use`.
- **Docs:** `docs/manual-qa/04-hmmscore-form.md`, and `docs/testing/frontend.md` for mocked `hmmscore` jobs.

No new dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui`: new requirements for the hmmscore form, its checks, its `422`s, its `501` and other failures, opening its job, its results and the alignment. "Services that aren't available yet", "The home page shows every service" and "The next step from a job's page" are MODIFIED, so HMM scoring opens its form.

## Impact

- **Frontend code:** a new `src/features/hmmscore/`; `src/features/jobs/` (the hmmscore result and title, the next step); `src/features/csnp/` (the shared check and example); `src/components/`; `src/app/services.ts`, `router.tsx`, `formFields.ts` and `api/wire.ts`; `src/mocks/`; tests in `tests/` and `e2e/`.
- **API contract:** none. The form reads the types `add-hmmscore-job` generates.
- **Parity with the reference:** this change scores nothing. The page shows the API's values as given.

## Open Questions

- **The relatedness label.** The site showed an icon from the E-value: closely related below 1e-23, related below 1e-11, distantly related below 1e-3 (`PantherScore.java` 110 to 120). Should the results show that label, and should the API compute it rather than the page?
- **The residue limit before submitting.** The form checks the most the setting allows. Showing the server's own limit before submitting needs an endpoint (`add-hmmscore-job`, design.md, decision 7).
