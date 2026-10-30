# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **The frontend stack, the form draft in component state, RTK Query for every call, types from the schema, matching the legacy features (species, example input, results table):** [docs/design/frontend-stack.md](../../../docs/design/frontend-stack.md), "How the Pieces Fit" and "Rules That Come With It".
- **How the frontend is organised:** [frontend/CLAUDE.md](../../../frontend/CLAUDE.md): features don't import each other's internals; one wire module knows the API's field names; a form whose inputs depend on each other keeps its draft in a reducer; and its cSNP-Specific Rules: no hard-coded thresholds, prediction labels or pDel values, results at their own URL, versions with the results, no build details on screen.
- **The job page, its states and polling, `startJob`, the mocked job store:** the archived [add-job-page design](../archive/2026-10-29-add-job-page/design.md). Its Goals said a service joins by adding its members to the wire module, a result view to the job page, and a form that calls `startJob`; this change does exactly that.
- **The cSNP contract and its input rules:** [add-csnp-job](../add-csnp-job/design.md) (the request, the result, the `501`, and each rule's legacy source) and its [`scoring-input` spec](../add-csnp-job/specs/scoring-input/spec.md). The `422` problem is `api-service`'s: `errors[]` with `loc`, `msg` and `type`, never echoing a value.
- **Scoring runs as a job, and the website moves to the JSON API with no legacy URLs:** [docs/design/tech-stack.md](../../../docs/design/tech-stack.md), API recommendations 1 and 2.

What exists now (PR #19's head, `9b34dbe`):

- `schema.d.ts` has `CsnpJobRequest`, `CsnpInput`, `CsnpJob`, `CsnpResult`, `SubstitutionScore`, `ValidationProblem` and `FieldError`, and a `501` on `POST /api/v1/jobs`.
- `wire.ts` types the job as `ToolsJob` only; `JobResult` has one case; the mocked `POST` answers `422` for any service but `tools`.
- `@mantine/form` is **not** a dependency: only `@mantine/core`, `hooks` and `notifications` are.

The behaviour is in [specs/scoring-ui/spec.md](specs/scoring-ui/spec.md).

## Goals / Non-Goals

**Goals:**

- The day the API's `501` goes, the form works with no frontend change: a valid request gets a `202`, and the job page shows the result.
- Each rule the form checks has one home in the client, next to its tests, and names the `scoring-input` rule it mirrors.
- Every submit outcome (`202`, `422`, `501`, anything else) is reachable from a test by changing only what the API answers.

**Non-Goals:**

- Normalising the input for the API. The client sends the sequence as typed; the API normalises, as `scoring-input` says. The client normalises only to check.
- CSV export, help text and a species selector (proposal, "Not in this change").

## Decisions

### Layout

```text
frontend/src/
  app/api/wire.ts                 Job and JobRequest become unions; ValidationProblem, isValidationProblem,
                                  inputErrors (a 422's errors by input field)
  app/router.tsx                  + csnp
  features/csnp/
    CsnpPage.tsx                  the page: heading, one line on the method, the form
    CsnpForm.tsx                  the fields, the example action, the submit button, the form's errors
    SubmitAlert.tsx               the 501's and other failures' fixed messages
    draft.ts                      the draft reducer: values and errors, edits clear their field's error
    checks.ts                     the client checks, one function per field, mirroring scoring-input
    substitutions.ts              splitSubstitutions: the box's text into the request's list
    example.ts                    the legacy website's example input
    useSubmitCsnp.ts              startJob, then the outcome: navigate, field errors, 501, or failed
    index.ts                      exports CsnpPage
  features/jobs/
    CsnpScores.tsx                a csnp job's family and score table
    JobResult.tsx, JobDetails.tsx + the csnp case and title
    index.ts                      + useStartJobMutation, for the csnp feature
  features/home/HomePage.tsx      + a link to /csnp in the cSNP section
  mocks/data/jobs.ts              + csnpResult (mock), csnpJob(id, status), csnpUnavailable (the 501)
  mocks/jobs.ts                   the store remembers each job's service
  mocks/handlers.ts               POST accepts csnp
frontend/tests/
  app/api/wire.test.ts            + the csnp job, inputErrors
  features/csnp/                  substitutions, checks, draft, CsnpPage
  features/jobs/JobPage.test.tsx  + csnp results
  features/home/HomePage.test.tsx the link
frontend/e2e/csnp.spec.ts         mock flow, client checks, real 422 and 501
```

- **`csnp` is its own feature,** since it has state (the draft), UI and logic that belong together. The job page stays in `jobs`, which renders every service's result, as add-job-page planned. `csnp` uses `startJob` through `@/features/jobs`, whose `index.ts` now exports `useStartJobMutation`; it imports nothing else from `jobs`.
- *Alternative:* the cSNP result view in `features/csnp/`, imported by `jobs`. Rejected: it would make `jobs` depend on every service's feature, and `csnp` on `jobs`, a cycle.

### The draft: a reducer, not `useForm`

frontend/CLAUDE.md and frontend-stack.md put a form's draft in Mantine `useForm`, "or a reducer if inputs depend on each other". `useForm` is in `@mantine/form`, which isn't installed, and this change adds no dependency. **The draft is a reducer** (`draft.ts`), held with `useReducer` in `CsnpForm`, and tested on its own. *(Decided during apply, 2026-10-29: the conservative option of the two. Adding `@mantine/form` is a separate decision for the frontend developer; if it's added, the reducer's checks and error mapping move into `useForm`'s `validate` and `setErrors` unchanged.)*

- **State:** `values` (`sequence`, `substitutions` and `species`, each the box's text) and `errors` (for each field, a list of messages; and `form`, messages that belong to no field).
- **Actions:** `edited` (a field's new text; clears that field's errors and the form's), `exampleUsed` (all three values from the example; clears every error), `checked` (the client checks' errors), `rejected` (a `422`'s errors).
- The reducer is where inputs and errors depend on each other: editing a field clears what the API said about it. That's the case frontend/CLAUDE.md names for a reducer.

### Splitting the substitutions

`splitSubstitutions(text)` splits at every run of whitespace and drops empty tokens: `text.split(/\s+/).filter(Boolean)`.

- **Whitespace only,** because that's what the old site documented ("separated by a tab, space, or return", `tips_exampleCsnpInput_content.jsp` line 22) and its form did (`CsnpScoreAction.java` 154 to 156, in add-csnp-job's design). A comma is part of a token, so `L46P,C130R` is one token, which the form check then rejects and names (proposal, Open Questions).
- **As typed, not upper-cased.** The API upper-cases each token (`scoring-input`); doing it here too would be a second place for the rule.

### The client checks

`checks.ts` has one function per field, each returning a list of messages, and `checkDraft(values)` returning them all. Each mirrors a `scoring-input` rule:

| Field | Check | `scoring-input` rule |
| ----- | ----- | -------------------- |
| sequence | More than 1,000,000 characters as typed | "rejected … longer than 1,000,000 characters before normalising" |
| sequence | After trimming characters up to U+0020, more than one `>` | "more than one `>`" |
| sequence | After also removing one header line and every space, tab, LF, VT, FF and CR: empty | "empty" |
| sequence | … a character outside `!` to `~` | "outside printable ASCII" |
| sequence | … more than 50,000 residues | "longer than 50,000 residues" |
| substitutions | No token after splitting | "1 to 1,000 tokens" |
| substitutions | More than 1,000 tokens | "1 to 1,000 tokens" |
| substitutions | A token longer than 32 characters, or with a character outside `!` to `~` | "1 to 32 printable ASCII characters" |
| substitutions | A token that, upper-cased, doesn't fully match `[A-Z][0-9]+[A-Z]` | The rule decided on PR #19, 2026-10-30, after `9b34dbe` (proposal): the legacy CGI's own pattern |
| species | After trimming, not 1 to 5 of `A`–`Z` and `0`–`9` | "1 to 5 upper-case letters or digits" |

- **The normalising steps are the API's,** in its order (add-csnp-job design, "The order of the `sequence` steps"), so a sequence the API accepts passes, and one it rejects for any of these reasons is caught here. The spec's "A valid input is sent" scenario guards the first half.
- **The limits are named constants** in `checks.ts`, each with a comment pointing to its rule. They're input limits, not scoring thresholds, so frontend/CLAUDE.md's rule against hard-coded thresholds doesn't apply; but they're a copy. If the API relaxes one, the form still blocks until the constant changes (Risks).
- **The species is trimmed** before it's checked and sent. The API doesn't trim it, but a space pasted after `HUMAN` is invisible in the box, and the user would see an error they can't explain. Trimming only the species box's own text sends exactly what the user meant; the API still checks it. Lower case is **not** fixed up: `human` is an error, as the API's rule says.
- **The messages are the client's own,** short, and don't name prediction labels or thresholds. They don't quote the value, with one exception: **malformed tokens are named,** by place and as typed ("Substitutions 2 (XYZ), 4 (G12|): use the form L46P, …"), at most ten, then a count, so the user can find them in a long list. It's the user's own text on their own screen, escaped by React like any text. A token too long or not printable ASCII isn't checked for its form or named: its own message, by place, comes first. *(Decided during apply, 2026-10-30, from the coordinator's rule change.)*
- **When checks run:** on submit, for every field. A field's errors clear as soon as it's edited, so a corrected field doesn't keep its error until the next submit.
  - *Alternative:* check each field as it's edited, or on blur. Not done: a long paste would show an error before the user had finished, and the API's own errors arrive only on submit, so one moment for both is easier to follow.

### The `422`: the server's errors on their fields

`wire.ts` gains `isValidationProblem(value)` and `inputErrors(problem, service)`, since they read the API's shapes:

- **`loc`'s layout** is `["body", <service>, "input", <field>, …]` (`api-service`; `docs/testing/api.md`, cSNP subsection). `inputErrors(problem, service, fields)` returns, for each of `fields`, its errors in order as `{msg, item}`, where `item` is a list item's index or `null`, and, under `other`, the `msg` of every error whose `loc` doesn't have that layout or names another field.
- **A list item's error** (`["body", "csnp", "input", "substitutions", 2]`) goes on the `substitutions` field, prefixed with the token's place, counted from 1, and the token itself, "Substitution 3 (G12V): ", because the box holds every token and the message alone wouldn't say which. The token comes from the form's own copy of the list it sent (the `rejected` action's `sent`), never from the response, which doesn't echo it; if the index is past that list, only the place is given. The prefix is the cSNP form's wording, so the draft reducer adds it, not `wire.ts`. *(Decided during apply, 2026-10-29 and 2026-10-30: the first test expected `wire.ts` to word it, and naming the token came with the rule change.)*
- **`CsnpForm` puts each field's messages on that field,** through the Mantine input's `error` prop, which sets `aria-invalid` and describes the input. The form's other errors, such as an input field the form doesn't have, go in an alert above the submit button.
- **The `msg` is shown as the API wrote it,** for example "Value error, The species must be a PANTHER species code of 1 to 5 upper-case letters or digits, such as HUMAN." The "Value error, " prefix is Pydantic's. Stripping it would be the client rewriting the server's text, so it's left as it is (Risks).

### Submitting

`useSubmitCsnp()` wraps `useStartJobMutation` and returns `submit(values)`, `isSubmitting` and the last outcome:

| API answer | Outcome | What the user sees |
| ---------- | ------- | ------------------ |
| `202` | navigate | `/jobs/{id}`, from the job's `id`, as the tools check does |
| `422` with a `ValidationProblem` body | `rejected` | each `msg` on its field; the input unchanged |
| `501` | `unavailable` | an alert: cSNP scoring isn't available yet, and the input is kept so it can be submitted later |
| anything else, including a network error or a `422` without the expected body | `failed` | an alert: the job couldn't be started, try again in a moment |

- **The request body** is `{service: "csnp", input: {sequence, substitutions, species}}`: the sequence as typed, the split substitutions, the trimmed species.
- **The alerts' text is fixed.** The `501`'s `detail` ("cSNP scoring isn't available yet.") is the API's, but the UI's own words say the same and add that the input is kept. For other failures nothing from the response is shown: its status or body could carry build details. In development, the error is logged with `console.warn` behind `import.meta.env.DEV`, as frontend/CLAUDE.md asks.
- **The button** shows a loader and is disabled while the request is in flight (`isLoading`), as `StartToolsCheck` does. A new submit clears the last alert.
- **The `501` branch is temporary.** When the API removes the `501`, nothing calls it; the port's frontend follow-up removes the branch, its test and its e2e test (Workflow follow-up).

### The example

`example.ts` holds the old site's example input (`tips_exampleCsnpInput_content.jsp` lines 9 to 30): the APOE sequence as its 10 lines, without a header, the substitutions `L46P`, `C130R`, `R163C` and `R176C` one per line, and `HUMAN`. "Use an example" fills all three, replacing what's there.

- *Alternative:* a FASTA header on the example, to show that FASTA is accepted. Not done: the old site's example has none, and the sequence box's description says FASTA is accepted.

### The page

- **`/csnp`,** headed "Coding SNP impact scoring", with one line saying what PANTHER-PSEP estimates, taken from the old form's text without its thresholds.
- **Fields:** a `Textarea` "Protein sequence" (description: plain residues or FASTA with one header), a `Textarea` "Substitutions" (description: such as `L46P`, separated by spaces or new lines, positions counted from 1 in this sequence), a `TextInput` "Species" (description: a PANTHER species code, such as `HUMAN`). Monospace text in the two boxes, so residues line up. The boxes have a fixed number of rows and resize vertically. *(Decided during apply, 2026-10-29: Mantine's `autosize` uses `react-textarea-autosize`, which listens on `document.fonts`; jsdom has none, so the page crashed in every Vitest test. A fixed height is what the old form had too.)*
- **Actions:** "Score substitutions" (the primary button) and "Use an example" (a subtle button above the fields).
- **The home page** keeps its cSNP section and gains a "Score coding SNPs" link button to `/csnp`. The tools check stays below it.

### The results on the job page

`JobResult` gains a `csnp` case that renders `CsnpScores`; `SERVICE_TITLES` gains `csnp: "Coding SNP impact scoring"`.

- **The family** is a line, "PANTHER family" and the id, or "No PANTHER family" in italics when it's `null`. It's a paragraph, not a description list, so the job's versions stay the only `term`s on the page, which the existing tests rely on.
- **The table** is named by its heading, "Scores", with the columns Substitution, Age (Mya), Prediction or message, and pDel, one row per score in the API's order. Each value is the API's, as a string: `age` is printed as the integer it is, `pdel` as its string (`"0.50"` stays `"0.50"`), `message` unchanged. A `null` age or pDel is an empty cell, as the old site left a missing preservation time blank. Nothing is coloured or labelled by its value: that would be a threshold in the UI.
- **The columns wrap to fit a phone,** and a wrapper with `overflow-x-auto` scrolls the table, not the page, if a long token or message still doesn't fit. *(Decided during apply, 2026-10-29: Mantine's `Table.ScrollContainer` is a `ScrollArea`, which needs `ResizeObserver`, missing in jsdom; and with a minimum width, the pDel column was off screen on a Pixel 7.)*
- **Versions** are shown by `JobDetails` for every finished job, so the `csnp` job's come with no change.

### The wire module's union

```text
WireJob    = ToolsJob | CsnpJob                     (schema)
JobRequest = ToolsJobRequest | CsnpJobRequest       (schema)
Job        = ToolsJob' | CsnpJob'                   (app: camelCase times, result typed by service)
```

`fromWireJob` switches on `service`, so each member keeps its own `result` type and `tsc` fails if a third service is added without a case. Every reader narrows by `service`: `JobResult` switches on it.

### Mocks

- **`csnpResult`** in `src/mocks/data/jobs.ts`, commented as mock data that the engine didn't produce: family `PTHR00000`, which no PANTHER family has, and four scores for the example's substitutions, with round ages and the legacy's message texts, the last "Not scored: Invalid substitution" with a `null` age and pDel. `csnpJob(id, status)` builds the job body.
- **`csnpUnavailable`:** the API's `501` problem, copied from `api/src/panther_api/jobs/work.py` (`CSNP_UNAVAILABLE`), for tests to serve with `server.use`.
- **The mocked store** remembers each job's service, so polling a `csnp` job returns a `csnp` body. `createJob(service)` defaults to `tools`, so existing callers don't change.
- **The mocked `POST`** accepts `csnp` and answers `202`, as the API will once scoring lands. It doesn't validate: the form's checks run first, and the `422` and `501` tests serve their own answers.

### Tests

- **Vitest:** `splitSubstitutions`, each check and `checkDraft`, the reducer and `inputErrors` directly; `CsnpPage` through the UI, with the request bodies recorded, for the example, the client checks (no request sent), the `422` on each field and on no field, the `501`, a `500`, the disabled button and the navigation. `JobPage` gains the `csnp` results, with a `null` family, age and pDel. Each failure test has a success test beside it.
- **Playwright, mock mode, desktop and mobile (`@mock`):** from `/`, follow the link, use the example, submit, see the job reach `succeeded`, the family, the rows and the versions, with no sideways scroll.
- **Playwright, untagged:** submitting an empty form shows the three field errors and stays at `/csnp`. No request is sent, so it holds in every mode.
- **Playwright, api mode (`@api`):** the example gets the real `501`, shown as not available yet, with the input kept. For the real `422`, the test rewrites the outgoing request's species to one the client would have refused (`page.route` with `route.continue({ postData })`), so the real API's `422` reaches the form, and its `msg` shows on the species field. A third test calls the API directly and checks the `loc` the form relies on. None of them creates a job, so they're safe in site mode.

## Risks / Trade-offs

- **[The client's checks drift from the API's]** A rule relaxed in the API still blocks in the form. → The constants are in one file, each naming its rule; the scoring-input change that relaxes one updates `checks.ts` in the same pull request (it regenerates the frontend's types anyway). A rule tightened in the API is caught by the server, and shown on the field.
- **[The `501` test fails the day scoring lands]** The `@api` test expects a `501`. → Intended: the port's pull request removes it, with the frontend's `501` branch (Workflow follow-up).
- **[Pydantic's "Value error, " prefix]** shows in the field's message. → Shown as the API wrote it; raise it with the API developer as a wording change, not a client rewrite.
- **[Mock results look real]** → The family id is `PTHR00000`, the data is commented as mock, and mock mode exists only in development and e2e builds.

## Migration Plan

Nothing to migrate. Rollback is reverting the pull request.
