# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **The frontend stack and its conventions:** [docs/design/frontend-stack.md](../../../docs/design/frontend-stack.md) (Accepted) and [frontend/CLAUDE.md](../../../frontend/CLAUDE.md): Mantine for controls, Tailwind for the rest, RTK Query for every call, types from the schema, `wire.ts` as the one module that knows the API's shapes, no new dependency without a proposal.
- **The `refmap` contract:** [add-refmap-job](../add-refmap-job/design.md), decisions 2 (the request and result) and 4 (the input rules, with the legacy evidence for each), and its `501` until the engine maps IDs. Its `scoring-input` delta is the rule list the form mirrors.
- **The legacy service:** [docs/parity/refmap-legacy-behaviour.md](../../../docs/parity/refmap-legacy-behaviour.md). Its quirk IDs (`REFMAP-1`, …) are used here.
- **The pattern this change repeats:** the archived [add-csnp-form](../archive/2026-10-29-add-csnp-form/design.md): the draft reducer, client checks that mirror the API, `422`s on their fields with a list item named from the form's own copy, a fixed-text `501`, `isUnreachable`, and the job page's per-service result. Its `501` branch was removed by #26 (`3e18128`); this change has one for `refmap` until the wiring change removes it.

The behaviour is in [specs/scoring-ui/spec.md](specs/scoring-ui/spec.md).

## Goals / Non-Goals

**Goals:**

- A user can paste or load a list of up to 100,000 IDs, see how many will be sent, and get every mistake the API would reject named before anything is sent.
- The page stays responsive at 100,000 IDs, on the form and on the results.
- The day the API returns `202` for `refmap`, the form and the results work with no frontend change.

**Non-Goals:**

- An organism selector: the engine exports no organism list yet. A follow-up, as cSNP's species selector was (#24, #31).
- Re-attaching a user's other columns (such as an expression value) to the results, or sending the mappings on to an enrichment analysis. The download is the hand-off.
- Help text beyond the field descriptions.
- Filtering or sorting the results table.

## Decisions

### 1. How the IDs box splits

Each line is read up to its first tab; what's before the tab is split at every run of whitespace and commas; empty pieces are dropped. IDs are sent exactly as typed, in order, repeats included. Line breaks are LF, CRLF or CR.

- **The first column, as the legacy read it.** `genericMapping.cgi` and `map_panther.pl` looked up each line's first tab field and echoed the rest (`REFMAP-5`). The website's help told users a second column can carry an expression value (`tips_toolsUploadFile.jsp` 46), and its mapping files were tab-separated. A pasted or loaded two-column list must not turn each value, such as `1.5`, into an ID.
- **Whitespace and commas within it, as cSNP's substitutions box.** A list copied from a paper or an email is often `P04217, P01023`. An ID can't hold whitespace (the API rejects it), and a comma in a list separates. So splitting there never loses a valid ID; it only makes more lists acceptable. The legacy, given `P04217 P01023` on one line through the website, looked up one ID with a `+` in it and answered `NOHIT` (`REFMAP-7`); the API rejects it. Splitting is the UI's choice of how text becomes a list, which the API leaves to the client (add-refmap-job, decision 2), so it changes no mapping.
- **What's left out is said.** The count under the box says how many IDs will be sent, and on how many lines something after a tab was left out, so a spreadsheet row pasted sideways (`P04217⇥P01023`) can't silently lose IDs.
- **Nothing is trimmed inside an ID, upper-cased or de-duplicated:** the lookup is exact and case-sensitive (`REFMAP-1`), with one row per input (`REFMAP-4`). The box's description says case matters.
- *Alternative:* cSNP's rule as it is, splitting at tabs too. Rejected: a two-column list, the legacy's own format, would send every value as an ID, each answered "No PANTHER ID", and the results would no longer line up with the user's rows.
- *Alternative:* one ID per line, the whole line. Rejected: a comma- or space-separated list would be one invalid ID.

### 2. Loading a text file

A "Load IDs from a text file" button (Mantine `FileButton`) reads the chosen file with `Blob.text()` and puts its contents in the box, replacing what was there. The same split, count and checks then apply, and the user can see and edit what will be sent.

- **Never uploaded:** only the IDs, as split, go in the request, exactly as when they're pasted.
- **At most 10 MB.** 100,000 lines of a 64-character ID, a tab and an expression value are under 8 MB; a larger file isn't a list of IDs, and reading it would only slow the page. A larger file, or one that can't be read, puts a fixed message on the IDs field and leaves the box as it was.
- **UTF-8.** The decoder drops a byte-order mark. A non-text file decodes to characters the checks reject, by place and line.
- **The input is reset after each file,** so choosing the same file again reads it again.
- *Alternative:* Mantine's `FileInput` or a drop zone. Rejected: a field that shows a file name suggests the file is what's sent; the box is.

### 3. The checks, and naming a bad ID

`checks.ts` mirrors add-refmap-job's rules: the organism, trimmed, is 1 to 5 of `A`–`Z` and `0`–`9`; there are 1 to 100,000 IDs; each is 1 to 64 characters from `!` to `~`. After the split, an ID has no whitespace, so these are all the per-ID rules the API has.

- **One pass, no regular expression over the whole list.** Each ID is tested once; 100,000 take milliseconds (tested). The checks run only on submit.
- **A bad ID is named by its place in the list, counted from 1, its line, and as typed:** `ID 3 (P0é4217, line 2)`. The place matches the API's `loc` index; the line is where to find it in the box, since a line can hold several IDs or none. Ten at most, then "and N more". An ID is shown cut to 24 characters, with control characters as U+FFFD, so a 64-character or invisible one still reads. The organism is never quoted, as cSNP's species isn't.
- **A `422` about one ID** names it the same way, from the split the form sent: the API never echoes it.
- **Too many IDs** says how many there are, and checks no ID: the list can't be sent either way.

### 4. Responsiveness with 100,000 IDs

- **The count follows the box through `useDeferredValue`.** Splitting a 100,000-line text takes some milliseconds; deferring it keeps each keystroke's render to the textarea itself, and the React Compiler reuses the split while the text is unchanged. Submitting splits the current text, not the deferred one.
- **The checks and the request** use that split once. The request body is the list; RTK Query sends it as JSON.
- *Alternative:* a Web Worker for the split. Rejected: the measured cost doesn't need one, and it would add a build path.

### 5. The results view

`RefmapMappings` shows a summary, a download button and `MappingsTable`; `JobResult` renders it for a `refmap` job, and `JobDetails` titles the page "Protein ID mapping".

- **The summary:** "6 IDs: 5 have a PANTHER ID, 1 has none." Counted from `mappings`, repeats included. The organism isn't shown: the job doesn't carry its input (proposal, Open Questions).
- **The table:** position (from 1, as submitted), ID and PANTHER ID; a `null` is "No PANTHER ID", muted. Each value exactly as the API gives it: no PANTHER ID or version is written by the UI.
- **Pagination, 100 rows a page,** with Mantine's `Pagination` (one sibling and one boundary page each side, so 1,000 pages fit a phone) inside a `nav` named "Pages of mappings", with "Rows 101 to 200 of 250". Only one page's rows are rendered, so 100,000 mappings render as fast as 100. *Alternative:* a virtualised list. Rejected: it needs a dependency (none in the stack virtualises), and a page number is something a user can say to a colleague. *Alternative:* render everything. Rejected: 300,000 cells freeze the page.
- **Tables wrap in `overflow-x-auto`,** as cSNP's do: a long ID scrolls the table, not the page.

### 6. The download

A button builds the file in the browser, from the job already loaded, and saves it through an object URL; nothing is fetched.

- **Format:** UTF-8 TSV, `text/tab-separated-values`: a header line `id⇥panther_id`, then one line per mapping in the API's order, with an empty `panther_id` for none. LF line endings, and a final LF. IDs are printable ASCII without whitespace, so nothing needs quoting. A header is safe for the legacy website's own parser, which skipped a first line whose second column didn't start with `PTHR` (`UploadedFile.java` 380 to 383).
- **File name:** `panther-id-mapping-<job id>.tsv`, so two downloads don't overwrite each other.
- **Every mapping, not the page shown.**
- *Alternative:* CSV. Rejected: the legacy service, its files and the website's analyses are all tab-separated.
- Whether an empty `panther_id` should be `NOHIT` instead is an open question (proposal).

### 7. Submitting

`useSubmitRefmap` is `useSubmitCsnp`'s shape with `refmap`'s `501`, as cSNP's was before #26:

| Answer | What the form does |
| ------ | ------------------ |
| `202` | Opens `/jobs/{id}` |
| `422` with errors | Each on the field its `loc` names; an ID by place, line and as sent; anything else with the form |
| `501` | "Protein ID mapping isn't available yet", fixed text; the input stays |
| No answer from the API (`isUnreachable`) | "The scoring service can't be reached" |
| Anything else | "The job couldn't be started" |

The two helpers that read a failed request's status and body move from `useSubmitCsnp.ts` to `src/app/api/errors.ts`, where both hooks import them. `SubmitAlert` stays per feature: refmap's has the `501` case, cSNP's no longer does.

### 8. The organism field

A text box, trimmed on submit, with no default: the API has none, so that a list is never mapped against an organism nobody chose (add-refmap-job, decision 4). The example fills `HUMAN`. When the engine exports `ORGANISM_CODES` with names, it becomes a searchable selector like cSNP's species, in a follow-up.

### 9. The example

Six reviewed human UniProtKB/Swiss-Prot accessions, one per line: A1BG (`P04217`) and A2M (`P01023`), the IDs add-refmap-job's docs use; APOE (`P02649`), cSNP's example protein; TP53 (`P04637`), BRCA1 (`P38398`) and EGFR (`P00533`). With `HUMAN`. Whether they map, and to what, is the engine's answer. If `HUMAN` turns out not to be a refmap organism, the example changes (proposal, Open Questions).

### 10. The mock

The mocked `POST` accepts `refmap` and remembers the submitted `input.ids` with the job; once it has succeeded, its result maps each:

- **Deterministic per ID:** from the sum of the ID's character codes, so a repeated ID gets the same answer, and reloading the dev server doesn't change it.
- **A mix:** a sum divisible by 3 is no PANTHER ID; the rest are `PTHR00000:SF<sum mod 10>`. `PTHR00000` is cSNP's mock family, and no real one. The example maps five and leaves one, `P38398`, with none.
- **No `501` in mock mode,** so the whole flow can be tried; Vitest serves the `501` with `server.use`, and the api-mode e2e test meets the real one.
- `src/mocks/data/jobs.ts` keeps to type and relative imports, as Playwright imports it.

## Risks / Trade-offs

- **[A list's other columns are left out silently]** → The count names how many lines were cut at a tab; the box's description says only the first column is read.
- **[The organism has no list]** → A typo is a `422` today, and the job's error once the API checks membership. The selector is the follow-up.
- **[A very large paste is slow to type into]** → The textarea itself holds the text; only the count is deferred. Loading a file is the better path for 100,000 IDs, and the e2e test does it.
- **[The `501` outlives its purpose]** → The wiring change that makes the API answer `202` removes the `unavailable` outcome, its test, the `@api` `501` test and this branch in `SubmitAlert`, as #26 did for cSNP.
- **[The results can't say which organism]** → An open question for the API; the job page shows what the job carries.

## Migration Plan

Nothing to migrate: a new page, a new section on the home page and a new job type on the job page. Rollback is reverting the commit. When the API's `501` for `refmap` is removed, the frontend's `unavailable` path goes with it (Risks).
