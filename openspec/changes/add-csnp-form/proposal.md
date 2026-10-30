# Proposal

**Area:** frontend. Outside `frontend/`, it adds one manual QA checklist, `docs/manual-qa/02-csnp-form.md`, and edits `docs/testing/frontend.md`. It changes nothing in `api/` or `engine/`.

**Depends on** `add-csnp-job` (PR #19): the `csnp` job contract, its `422` validation problem and its `501`, and the regenerated `frontend/src/app/api/schema.d.ts`. This change's branch starts from PR #19's head, `9b34dbe`, and merges after it.

**A rule changed on PR #19 after `9b34dbe` (2026-10-30):** the engine developer decided that the API rejects a substitution token that isn't `[A-Z][0-9]+[A-Z]` once upper-cased (the legacy CGI's own rule), with a `422` at `["body", "csnp", "input", "substitutions", <index>]` that doesn't echo the token. Before, `scoring-input` kept such tokens. This change follows the new rule; the API's side lands on PR #19's branch, not in `9b34dbe`.

## Why

`csnp` is the first scoring service to be ported, and its contract is settled: the request, the result and the input rules (`scoring-input`). Users have no way to submit a cSNP request from the new UI, and the job page can show only the `tools` job. Building the form, the submit flow and the results view now, against the real `422`s and the real `501`, means the UI is ready the day the engine's scoring is wired in, and the team can try the whole path in a browser before then.

## What Changes

- **A cSNP page at `/csnp`,** linked from the home page's "Coding SNP impact scoring" section, with:
  - a **sequence** box that takes plain residues or FASTA with one header;
  - a **substitutions** box where tokens such as `L46P` are separated by spaces, tabs or new lines, as the old site allowed. One tested function splits it into the request's list;
  - a **species** box, `HUMAN` by default, checked against the API's format rule. There is no species list in the API yet;
  - a **"Use an example"** action that fills all three with the old site's example input (APOE, `L46P C130R R163C R176C`, `HUMAN`).
- **Client checks** that mirror `scoring-input`: the sequence has residues, holds one protein, isn't too long and is printable ASCII; there are 1 to 1,000 substitutions of at most 32 characters each, each like `L46P` once upper-cased, and the form names each one that isn't; the species is 1 to 5 upper-case letters or digits. They run before anything is sent. **The server stays the authority:** each `422` error is shown on the field its `loc` names, with its `msg`; an error about one substitution names the token from the form's own copy of what it sent, since the API never echoes it.
- **Submitting** through the existing `startJob` mutation:
  - `202`: the UI opens `/jobs/{id}`;
  - `501`: a fixed message that cSNP scoring isn't available yet; the input stays and the page doesn't change;
  - any other failure: a fixed, generic message with no build details;
  - the submit button is disabled while the request is in flight.
- **cSNP results on the job page:** the PANTHER family, or "No PANTHER family" when it's `null`; a table of substitution, age (Mya), prediction or message, and pDel, each exactly as the API gives it; and the job's versions, as for `tools`.
- **The wire module's job becomes a union** of the `tools` and `csnp` jobs, narrowed by `service` where results render. The `tools` path doesn't change.
- **Mocks:** a `csnp` `POST` returns a queued job that moves to `succeeded` with a mock result, marked as mock data, with family `PTHR00000`, a "Not scored: …" row and a `null` pDel. Tests reproduce the real `501` with `server.use`.
- **Tests, written first,** from the spec scenarios: Vitest + React Testing Library for the splitting, the client checks, the `422` mapping, the `501`, submit and navigate, and the results; Playwright in mock mode on desktop and mobile; Playwright in api mode against the real API's `422` and `501`.
- **Docs:** `docs/manual-qa/02-csnp-form.md`, and `docs/testing/frontend.md` where running the tests changed.

No new dependency.

Not in this change:

- **CSV export** of the results (`csnpScoreResExport.jsp`) and the **help text** (`tips_csnpScores_content.jsp`). Both are in `frontend-stack.md`'s list of legacy features, and each is its own change once results are real. The help text in particular states thresholds, which are an open question.
- **A species selector.** It waits for the engine's species list.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui`: new requirements for the cSNP form and its client checks, server field errors shown on their fields, the not-yet-available `501`, opening the new job, and cSNP results on the job page. Only ADDED requirements; the existing ones don't change.

`scoring-input` is not modified: the form follows its rules, which `add-csnp-job` adds, and adds none of its own.

## Impact

- **Frontend code:** `src/app/api/wire.ts` (the job and request unions, the `422` helpers), `src/app/router.tsx` (`/csnp`), a new `src/features/csnp/`, `src/features/jobs/` (the `csnp` result and title), `src/features/home/HomePage.tsx` (the link), `src/mocks/`; tests in `tests/` and `e2e/`.
- **API contract:** consumed, not changed. `npm run api:types:check` passes with the committed `schema.d.ts`.
- **Parity with the legacy cSNP service:** not affected. The UI scores nothing: it shows the API's `message`, `age` and `pdel` as given, and hard-codes no threshold, prediction label or pDel value. Its checks reject only what the API rejects. The token form check is the legacy CGI's own, so a token it turns away is one the legacy would have dropped without a row. No divergence row is needed for this change; whether rejecting, rather than dropping, needs one is PR #19's question.

## Open Questions

Each needs team verification.

- **A species list from the API.** The form takes a typed species code checked only for its shape. When the engine exports its species list (`add-csnp-job`, Open Questions), the API should publish it, and the form should become a selector. Who adds the endpoint, and when?
- **Commas between substitutions.** The old site separated substitutions only by whitespace, so `L46P,C130R` is one token, and now a rejected one: the form names it and asks for the `L46P` form. Should the form split at commas too, as users may expect? That would accept input the old site didn't.
- **`scoring-input`'s text.** Its "Tokens that aren't substitutions are kept" scenario becomes a rejection with PR #19's rule change. This change's checks follow the new rule; the `scoring-input` spec itself is PR #19's to update.
- **The PANTHER 9 note.** The old form said the cSNP tool uses PANTHER 9.0 data. The new UI shows only the versions the API reports, and those don't name the data version yet. Should the API report the PANTHER library version, as `frontend/CLAUDE.md` expects?
- **What the `501` page should offer.** It keeps the input and says scoring isn't available yet. Should it also point to the downloadable PANTHER-PSEP tool, as the old form did for large inputs?
