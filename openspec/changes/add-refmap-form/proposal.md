# Proposal

**Area:** frontend. Outside `frontend/`, it adds one manual QA checklist, `docs/manual-qa/03-refmap-form.md`, and edits `docs/testing/frontend.md`. It changes nothing in `api/` or `engine/`.

**Depends on** `add-refmap-job` (PR #30): the `refmap` job contract, its `422` validation problem and its `501`, and the regenerated `frontend/src/app/api/schema.d.ts`. This change's branch starts from PR #30's head merged with `main`, `efd4fe3`, and merges after it.

## Why

`refmap` is the second service to port, and PR #30 settles its contract: the request, the result and the input rules (`scoring-input`). Users have no way to map IDs from the new UI. Building the form, the submit flow and the results view now, against the real `422`s and the real `501`, means the UI is ready the day the engine's mapping is wired in, as `add-csnp-form` (#20) did for cSNP.

## What Changes

- **A refmap page at `/refmap`,** linked from a new "Protein ID mapping" section of the home page, beside cSNP, with:
  - an **IDs** box for a pasted list. Each line is read up to its first tab, as the legacy read only a line's first column (`REFMAP-5`); the rest is split at whitespace and commas. IDs are kept as typed, case and repeats included (`REFMAP-1`, `REFMAP-4`). The form shows how many IDs will be sent, and on how many lines a column after a tab was left out;
  - a button that **loads a text file** into the box. The file is read in the browser and never uploaded; one over 10 MB isn't read;
  - an **organism** box for a UniProt species code, checked for its shape only. It starts empty: the API has no default. It becomes a selector when the engine exports its organism list (follow-up);
  - a **"Use an example"** action: six reviewed human UniProtKB accessions (A1BG, A2M, APOE, TP53, BRCA1, EGFR) and `HUMAN`.
- **Client checks** that mirror `scoring-input`'s refmap rules: 1 to 100,000 IDs, each 1 to 64 printable ASCII characters, and an organism of 1 to 5 upper-case letters or digits. A bad ID is named by its place, its line and as typed, ten at most, then a count. Checking 100,000 IDs takes milliseconds. **The server stays the authority:** each `422` error is shown on the field its `loc` names, and an error about one ID names it from the form's own copy, since the API never echoes it.
- **Submitting** through the existing `startJob` mutation: a `202` opens `/jobs/{id}`; a `501` says, in fixed text, that protein ID mapping isn't available yet, keeping the input; an unreachable API and any other failure reuse cSNP's messages (`isUnreachable`).
- **refmap results on the job page:** a summary (how many IDs, how many have a PANTHER ID, how many have none), a table of position, ID and PANTHER ID ("No PANTHER ID" for `null`), 100 rows a page with Mantine's `Pagination`, a download of every mapping as a tab-separated file built in the browser, and the job's versions, as for every job.
- **The wire module's job and request unions gain `refmap`.** `errors.ts` gains the two helpers that read a failed request's status and body, which `useSubmitCsnp` and the refmap hook now share.
- **Mocks:** a `refmap` `POST` returns a queued job that succeeds with a mock result mapping the submitted IDs: the same ID always gets the same answer, about a third get none, and the rest get obviously made-up `PTHR00000:SF<n>` values. Tests reproduce the real `501` with `server.use`.
- **Tests:** Vitest for the splitter, the checks (limits, and 100,000 IDs staying fast), the reducer, the file reader, the page (fill, example, file, submit, `422`, `501`, unreachable, each failure beside a success) and the results (summary, table, pagination, download); Playwright in mock mode on desktop and mobile, 100,000 IDs included; Playwright in api mode against #30's `501` and `422`.
- **Docs:** `docs/manual-qa/03-refmap-form.md`, and `docs/testing/frontend.md` for mocked `refmap` jobs.

No new dependency. `FileButton` and `Pagination` are in `@mantine/core`, and the download icon in `@tabler/icons-react`, both already installed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui`: new requirements for the refmap form, splitting its IDs, loading a file, its client checks, its `422` errors, its `501` and other failures, opening the job, and refmap results on the job page. Only ADDED requirements, so it doesn't conflict with `wire-csnp-scoring` and `add-csnp-species-list`, which modify other `scoring-ui` requirements; any of them can archive first.

`scoring-input` is not modified: the form follows the refmap rules `add-refmap-job` adds.

## Impact

- **Frontend code:** `src/app/api/wire.ts` (the `refmap` job and request), `src/app/api/errors.ts` (two shared helpers), `src/app/router.tsx` (`/refmap`), a new `src/features/refmap/`, `src/features/jobs/` (the `refmap` result and title), `src/features/home/HomePage.tsx` (the link), `src/features/csnp/useSubmitCsnp.ts` (the shared helpers), `src/mocks/`; tests in `tests/` and `e2e/`. `e2e/shell.spec.ts` now expects more than one section heading on the home page.
- **API contract:** unchanged; `npm run api:types:check` passes with the committed `schema.d.ts`.
- **Parity with the legacy refmap service:** not affected. The UI maps nothing: it shows each `panther_id` as the API gives it. Its checks reject only what the API rejects. How the box is split is the UI's own: the API takes a list, and the legacy CGI's text input never reaches it (`REFMAP-7`). No divergence row is needed.

## Open Questions

Each needs team verification.

- **Is `HUMAN` among refmap's organisms?** The legacy help says this list type was for genomes that aren't among PANTHER's own (`tips_toolsUploadFile.jsp` 26 to 27), which include human. If the engine's list has no `HUMAN`, the example needs another organism and accessions from it. For the engine developer, with #30's organism-key question.
- **The organism on the results.** A `refmap` job doesn't say which organism it mapped against, since jobs don't echo their input (add-scoring-jobs design), so the results page can show only the ID count. A shared link then loses that context. Should `RefmapResult` carry the organism? For the API and engine developers.
- **The download's format.** `id` and `panther_id`, tab-separated, with a header and an empty `panther_id` for no PANTHER ID, as briefed. The legacy website's own parser for a mapping file refused an empty value, wanting `NOHIT` (`UploadedFile.java` 395 to 398). If the file is meant to be uploaded to that analysis as it is, should no PANTHER ID be written `NOHIT`? For the frontend developer.
- **A `\r` in a PANTHER ID** (`REFMAP-3`). If a classification file has CRLF endings, the API would return PANTHER IDs ending in `\r`, which the table and the download show as they are. Needs the engine developer's answer on the files' line endings.
- **Columns after the ID.** The form reads a line's first column and leaves out the rest, as the API takes IDs only. The legacy echoed the rest back, and the website's enrichment test read an expression value from it (`REFMAP-5`). Re-attaching a user's columns to the results by position is a possible follow-up, if the frontend developer wants it.
