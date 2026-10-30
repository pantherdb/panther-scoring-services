# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **Jobs, the request union tagged by `service`, the job union, `work.py` as what the workers run, and adding a service by adding a request member, a result and a `run_job` case:** [openspec/specs/scoring-jobs/spec.md](../../specs/scoring-jobs/spec.md) and the archived [add-scoring-jobs design](../archive/2026-10-29-add-scoring-jobs/design.md).
- **Problem details, `422`s that never echo a value, and the committed schema:** [openspec/specs/api-service/spec.md](../../specs/api-service/spec.md) and [docs/design/api-stack.md](../../../docs/design/api-stack.md).
- **Pydantic replaces the CGIs' hand-written form parsing, and the website moves to the JSON API with no compatibility endpoints:** [docs/design/tech-stack.md](../../../docs/design/tech-stack.md), API section and API recommendation 2. So the website's `+`-joined substitutions (`CGI-2`, `CGI-3`) never reach this API.
- **`species` never goes near a shell (`CGI-5`),** and each service keeps its toolchain: [CLAUDE.md](../../../CLAUDE.md), Working Rules, and tech-stack.md, Engine condition 6.
- **The engine's input errors:** [add-job-input-errors](../add-job-input-errors/design.md). Its task group 2, handling `InputError` in the runner, waits for the engine and isn't done here.

Decided with the engine developer on 2026-10-29, and not reopened here:

- `panther_engine.csnp.score(CsnpInput) -> CsnpResult`, frozen dataclasses, one protein per call: `CsnpInput(sequence: str, substitutions: tuple[str, ...], species: str)`, `CsnpResult(family: str | None, scores: tuple[SubstitutionScore, ...])`, `SubstitutionScore(substitution: str, age: int | None, message: str, pdel: str | None)`. It doesn't exist yet.
- `message` is the legacy text; `pdel` is the legacy two-decimal string, because parity is byte for byte.
- "No family hit" and "invalid substitution" are result rows, not errors: the job succeeds.
- The engine will export the species codes it accepts; the API checks membership when that list exists.
- No stub returns made-up ages, messages or pDel values, even in a test.

The behaviour is in [specs/scoring-input/spec.md](specs/scoring-input/spec.md) and [specs/scoring-jobs/spec.md](specs/scoring-jobs/spec.md).

## Goals / Non-Goals

**Goals:**

- The frontend and the website can build the cSNP form against the real request, the real result type and the real `422`s now.
- Wiring the engine in later changes the API's code, not its contract: the `501` goes, and nothing else in the schema moves.
- Every validation rule is traceable to the legacy code, line by line.

**Non-Goals:**

- Scoring, or calling the engine. There is no adapter and no import of `panther_engine.csnp`.
- Checking `species` against the engine's list, which doesn't exist yet.
- Handling `InputError` (add-job-input-errors, group 2).
- The frontend's form, and splitting a text box into tokens. That's the client's job.

## Decisions

### Layout

```text
api/src/panther_api/jobs/
  csnp.py      CsnpInput (with its validation), SubstitutionScore, CsnpResult. Pydantic only,
               so a worker can import it
  work.py      CsnpJobRequest joins JobRequest, CsnpResult joins JobResult; run_job's csnp case
  models.py    CsnpJob joins Job
api/src/panther_api/routers/jobs.py
               the 501 for a csnp request, and the 501 documented on POST /jobs
api/tests/
  test_csnp_input.py   the scoring-input rules, on the model, in the test process
  test_jobs.py         the csnp request through the API: 422s, the 501, no job stored
  test_openapi.py      the csnp members of both unions, the result shape, the 501
```

- **`csnp.py` mirrors `tools.py`:** one module per service holds its input and result. The adapter that calls the engine joins it with the port.

### The contract

The request:

```json
{
  "service": "csnp",
  "input": {
    "sequence": ">sp|P02649|APOE_HUMAN\nMKVLWAALLVTFLAGCQAKVEQAVETEPEPELRQQ\n…",
    "substitutions": ["L46P", "C130R", "R163C", "R176C"],
    "species": "HUMAN"
  }
}
```

The job, once the engine is wired in. These are types, not values: nothing in this change produces a result.

```text
{
  "id": …, "service": "csnp", "status": …, "created_at": …, "started_at": …, "finished_at": …,
  "result": {
    "family": string | null,                  e.g. a PANTHER family id; null with no family hit
    "scores": [
      {
        "substitution": string,               the token, as scored
        "age": integer | null,                millions of years; null when not scored
        "message": string,                    the legacy text, e.g. "Not scored: Invalid substitution"
        "pdel": string | null                 the legacy two-decimal string; null when not scored
      }, …
    ]
  } | null,
  "error": Problem | null,
  "versions": Versions
}
```

- **Schema component names:** `CsnpJobRequest`, `CsnpInput`, `CsnpJob`, `CsnpResult` and `SubstitutionScore`. They read the same as the engine's dataclasses, so the adapter is a field-for-field copy.
- **`substitutions` is a list,** not a text box. The client splits; the API never parses separators, so neither `CGI-2` (`main` splits only on tab, space and LF) nor `CGI-3` (`tr/%2B/ /` on the site's copy) can arise.
- **Every result field is required and nullable where the engine's is,** as `ToolVersion.version` is, so the generated TypeScript is `T | null`, never optional.
- **`age` is an integer and `pdel` a string,** as the engine's dataclass has them. A `pdel` of `"0.50"` stays `"0.50"`; a float would print `0.5`, and the frontend would show something the legacy never did.
- **The job doesn't echo the input,** as for `tools` (add-scoring-jobs design). The client already has its sequence and substitutions.
- **Union order:** `tools` first, then `csnp`, so the existing member keeps its place in the generated types.

### Not available yet: a `501` at submit

`create_job` validates the body as now, then, for a `CsnpJobRequest`, raises `HTTPException(501, "cSNP scoring isn't available yet.")` before calling `submit`. The existing handler makes it a problem: `title` "Not Implemented", `status` 501. No `JobRecord` is created, so polling has nothing to find.

- **Why at submit, not a failed job:** a job that is always going to fail would look like a scoring fault, and the frontend would show it as one. A `501` says what's true: the server doesn't do this yet. *Alternative:* accept the job and fail it with a `500`. Rejected: indistinguishable from a bug, and it fills the store with jobs that can't run.
- **Why validate first:** clients get the real `422`s now, and the only change when scoring lands is that a valid request gets a `202` instead of a `501`.
- **Documented in the schema:** `POST /jobs` declares a `501` response with the `Problem` model. `document_problems()` moves its body to `application/problem+json`, as for every 4xx and 5xx, so the frontend's generated types know the `501` is a problem.
- **`run_job` has a `csnp` case that raises `NotImplementedError`.** The router never submits a `csnp` job, so it can't be reached; but `run_job`'s `match` must cover every member for the strict type check, and if something did reach it, the job would fail with the generic `500`, never with a made-up score. The port replaces the raise with the adapter call.
- **Removing it:** the port's API change deletes the `501` branch, its schema entry and its tests, replaces the `run_job` case, adds the adapter, and does add-job-input-errors group 2. Its `scoring-jobs` delta REMOVES "cSNP scoring not available yet".

### Validation, rule by rule

The legacy service is two layers: the website's form (`panther-site-java`), which normalised and checked the input, then `snpScore.cgi`, which split the substitutions and ran the scripts. The new frontend and API replace the form and the CGI's input handling together, so the API's rules follow the form, and where the form didn't check, the CGI. Paths are under `../panther-workspace/legacy/`.

| Field | Rule | Legacy evidence |
| ----- | ---- | --------------- |
| `sequence` | Strip leading and trailing characters up to U+0020, as Java's `trim()` does | `CsnpScoreForm.java` 16 to 22 (`trim()`, then `toUpperCase()`) |
| `sequence` | More than one `>` anywhere: rejected | `CsnpScoreForm.java` 69 to 75 (`errors.too.many.sequences`) |
| `sequence` | One header line at the very start (`^>[^\n]*`) removed | `CsnpScoreForm.java` 77 to 82. The help says "FASTA format, or just the protein sequence itself" (`tips_exampleCsnpInput_content.jsp` 6) |
| `sequence` | Then every whitespace character (Java's `\s`: space, tab, LF, VT, FF, CR) removed | `CsnpScoreForm.java` 83 to 87 |
| `sequence` | Upper-cased | `CsnpScoreForm.java` 19 |
| `sequence` | Empty after normalising: rejected | `CsnpScoreForm.java` 62 to 67 checked before stripping; a header-only input then reached the CGI empty, and it died: `die "Missing input sequence"` (`snpScore.cgi` 57) |
| `sequence` | More than 50,000 residues after normalising: rejected | `CsnpScoreForm.java` 89 to 94 (`errors.sequence.too.long`) |
| `sequence` | A character outside printable ASCII (U+0021 to U+007E) after normalising: rejected | **New.** The form checked no alphabet. No protein residue code is outside printable ASCII. Open question for which printable characters BLAST+ scores |
| `sequence` | More than 1,000,000 characters as submitted: rejected | **New.** Bounds the work before normalising; a 50,000-residue FASTA is about 51,000 characters |
| `substitutions` | Required, a list of at least one token | `CsnpScoreForm.java` 96 to 99 (`errors.substitutions.not.available`) |
| `substitutions` | At most 1,000 tokens | **New** (Open Questions) |
| `substitutions` | Each token 1 to 32 printable ASCII characters | The 32 is **new**. The CGI splits on tab, runs of spaces and LF (`snpScore.cgi` 197) and the form on any whitespace run (`CsnpScoreAction.java` 154 to 156), so no legacy token contains whitespace. A token the CGI can score matches `(^[A-Z]\|a-z)([0-9]+)([A-Z\|a-z]$)` (`snpScore.cgi` 212), all printable ASCII; 32 characters allows a 30-digit position |
| `substitutions` | Each token upper-cased | `CsnpScoreForm.java` 28 to 34 |
| `substitutions` | Once upper-cased, each token matches `[A-Z][0-9]+[A-Z]`: rejected otherwise | **New** (decided with the engine developer on #19, 2026-10-30). The CGI dropped a non-matching token without a row (`snpScore.cgi` 212 to 214), so no score is lost; the `422` points at the token by its index. Two CGI quirks aren't kept: `[A-Z\|a-z]` also took `\|` as the mutant residue (`G12\|` was scored as `G12`), and the CGI dropped `*` (`A10*`) although steps 2 and 3 score it (spec §7.5 `e4`, `SCORE-12`); accepting `*` would be new behaviour, to revisit once cSNP is live. A token in the form that can't be mapped still gets "Not scored: Invalid substitution" (`PANTHER_PSEP1.01.pl` 74 to 86). No divergence row: the engine's output for each token it receives doesn't change |
| `species` | Required | The CGI defaults an empty value to `HUMAN` (`snpScore.cgi` 72 to 77), but the form required an organism and rejected an unknown one (`CsnpScoreForm.java` 101 to 107), preselecting the session's default (`dataset.jsp` 20 to 30, 66). Every request that reached scoring had one |
| `species` | 1 to 5 characters, `A`–`Z` and `0`–`9` | The form sent a mnemonic from its cSNP list, `HUMAN`, `RAT`, `PLAF7`, `SYNY3` and 81 more (`OrganismConstants.java` 79, `CsnpScoreAction.java` 157 to 158). The CGI put it unquoted into a shell command and a `grep` pattern (`snpScore.cgi` 91, `parse_blastp.pl` 42: `CGI-5`); this shape has no shell or pattern metacharacters |
| `input` | No other fields | As every input model (add-scoring-jobs design) |

- **The order of the `sequence` steps** is the form's: trim, count `>`, remove the header, remove whitespace, then check. Upper-casing comes last here, after the ASCII check, because Python's `str.upper()` maps some non-ASCII letters to ASCII ones (`ß` to `SS`); Java's did too, but here those are rejected first.
- **Not imitated:** the CGI's form decoding (`snpScore.cgi` 38 to 46), including removing `<!-- … -->` from every value. JSON has no form encoding.
- **Each rule raises its own message,** written without the value: for example "The sequence has more than one '>', so it holds more than one sequence. Submit one protein." Pydantic's built-in messages for types, lengths and missing fields don't quote the input either, and tests check every field with a distinctive value.
- *Alternative:* check each token against the substitution format, as the frontend's example spec in CONTRIBUTING.md does ("A12" rejected). Rejected for the API: the legacy didn't reject such tokens, and the result already reports them per substitution. The UI may still warn about a token before submitting; that's `scoring-ui`'s call, not a `scoring-input` rule.
- *Alternative:* default `species` to `HUMAN`, as the CGI does. Rejected: the website never relied on it, and an explicit species keeps a client bug from silently scoring against human.

### Where normalising happens

The API normalises, and the engine receives residues only, upper-cased, with no header or whitespace, and upper-cased tokens. The engine then writes its own FASTA, as `snpScore.cgi` wrote `>P0001` (line 188). The engine's parity tests start from that normalised input, which is what the legacy scripts received from the form. Open question: confirm the engine expects it.

### Tests

- **The rules,** in `test_csnp_input.py`, on `CsnpInput` itself: the normalised value is only visible there, since the API returns no job.
- **Through the API,** in `test_jobs.py`: each field with a distinctive invalid value gets a `422` at the right `loc`, the value isn't in the body, and no job is stored; a valid request gets the `501` with nothing stored; a `tools` job still succeeds afterwards.
- **The schema,** in `test_openapi.py`: both unions' `csnp` members and mappings, the result's required and nullable fields, and the `501`.
- **No test builds a `CsnpResult` with values.** Its shape is tested through the schema only, so no made-up age, message or pDel exists anywhere.

## Risks / Trade-offs

- **[A rule rejects input the legacy would have scored]** → Every rule but four comes from the legacy form or CGI, with its line. The four new ones (printable ASCII in the sequence, the 1,000,000-character raw cap, 1,000 tokens, 32 characters per token) are listed as open questions for the engine developer, and are easy to relax: relaxing a `422` breaks no client.
- **[The `501` outlives its purpose]** → It's tied to the port in the Workflow follow-up, and the spec says it lasts only until the engine is wired in.
- **[Contract drift from the engine's dataclasses]** → The field names and types are the agreed ones; the port's adapter maps them one to one, and its tests fail on any mismatch.

## Migration Plan

Nothing to migrate: the contract is additive, and a `csnp` request was a `422` (unknown `service`) before this change. Rollback is reverting the pull request and regenerating the frontend's types.

## Open Questions

The engine developer answered the proposal's questions on #19 (2026-10-30); proposal.md records the answers. Only the token rule changed this change. The rest confirm its rules, or land with the port.
