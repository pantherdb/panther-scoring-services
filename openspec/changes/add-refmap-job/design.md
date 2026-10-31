# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **Jobs, the request union tagged by `service`, the job union, `work.py` as what the workers run, and adding a service by adding a request, a result and a `run_job` case:** `openspec/specs/scoring-jobs/` and the archived [add-scoring-jobs design](../archive/2026-10-29-add-scoring-jobs/design.md).
- **A contract with a `501` first, then the port:** the archived [add-csnp-job design](../archive/2026-10-29-add-csnp-job/design.md), "Not available yet: a `501` at submit", and how the archived [wire-csnp-scoring](../archive/2026-10-30-wire-csnp-scoring/design.md) removed it. This change reuses that shape for `refmap` only.
- **Problem details, `422`s that never echo a value, and the committed schema:** `openspec/specs/api-service/` and [docs/design/api-stack.md](../../../docs/design/api-stack.md). This change caps the `422`'s errors (decision 7).
- **The engine is a library the API imports; the website moves to the JSON API with no compatibility endpoints; scoring goes through jobs, and engine code never runs on the event loop:** [docs/design/tech-stack.md](../../../docs/design/tech-stack.md), Engine condition 1 and API recommendations 1 and 2. So the website's form-encoded `fileContents` (`REFMAP-7`) never reaches this API.
- **Input errors:** an engine `InputError` fails the job with a `422` and its message (`add-job-input-errors`, implemented by `wire-csnp-scoring`).
- **`refmap` uses no external tool,** and its parity reference is `map_panther.pl` (tech-stack.md, Runtime Tools and Milestones).

The legacy service, with the evidence for every statement below, is in [docs/parity/refmap-legacy-behaviour.md](../../../docs/parity/refmap-legacy-behaviour.md). Its quirk IDs (`REFMAP-1`, …) are used here, and `genericMapping.cgi`'s line numbers are RefProteomeMapper's `master` (`649c85f`). In short: `genericMapping.cgi` loads the organism's classification file into a hash of first column to second column, and prints, for each input line, the line's first tab field, its PANTHER ID or `NOHIT`, and the rest of the line. The website sent the raw text box or file, unnormalised, and the organism's long name from its `stats` list.

The behaviour is in [specs/scoring-input/spec.md](specs/scoring-input/spec.md) and [specs/scoring-jobs/spec.md](specs/scoring-jobs/spec.md).

## Goals / Non-Goals

**Goals:**

- The frontend and the website can build against the real `refmap` request, result type and `422`s now.
- The engine developer can port `map_panther.pl` against a fixed interface, and wiring it in changes the API's code, not its contract.
- Every validation rule is traceable to the legacy code, or marked new.

**Non-Goals:**

- Mapping anything, or importing `panther_engine.refmap`, which is empty.
- Checking `organism` against the engine's list, which doesn't exist yet. A follow-up, as for cSNP's species (#24).
- An organism list endpoint, or a replacement for `map_panther_cls` (proposal, Open Questions).
- A refmap form or results view in the frontend.
- Versions: `Versions.data` gains `{"service": "refmap", "panther": "19"}` when the engine exports its data version, with the wiring.

## Decisions

### 1. A job, not a synchronous endpoint

`refmap` goes through `POST /api/v1/jobs` like every service. Recommended to the engine and API developers, who decide; the alternative is recorded here so the decision can be revisited without redoing this change's validation.

- **One contract.** The frontend's job page, polling, error handling, versions and expiry, and the website's client, work for `refmap` with no new pattern. A `refmap` result is also what the website feeds into its enrichment and overrepresentation tests, so a result that can be polled again for 24 hours is useful.
- **The work isn't free.** Each job reads one organism's classification file, of unknown size, and up to 100,000 IDs. It runs in a worker either way: tech-stack.md's API recommendation 1 says any synchronous endpoint uses the same pool, so a synchronous endpoint wouldn't save the pool, only the polling.
- **The cost:** a second round trip, and at least one poll interval of latency, for a lookup the legacy answered in one request; the website's Java has to loop.
- *Alternative:* `POST /api/v1/refmap` returning `200` and the result, running `map_ids()` in the pool and awaiting it. Simpler for the website, and closer to the CGI. Rejected for now: a second pattern every client must handle, and a request that can hold a connection open for as long as a large list takes. If the engine developer finds a typical request takes milliseconds once the file is cached, it can be added beside the job, with the same input and result models.

### 2. The contract

The request:

```json
{
  "service": "refmap",
  "input": { "organism": "HUMAN", "ids": ["P04217", "P01023", "P04217", "NOT_AN_ID"] }
}
```

The job, once the engine is wired in. These are types, not values: nothing in this change produces a result.

```text
{
  "id": …, "service": "refmap", "status": …, "created_at": …, "started_at": …, "finished_at": …,
  "result": {
    "mappings": [
      { "id": string, "panther_id": string | null }, …     one per submitted ID, in order
    ]
  } | null,
  "error": Problem | null,
  "versions": Versions
}
```

- **Schema components:** `RefmapJobRequest`, `RefmapInput`, `RefmapJob`, `RefmapResult` and `IdMapping`. They read the same as the proposed engine dataclasses (decision 3), so the adapter is a field-for-field copy.
- **`ids` is a list,** not the legacy text. The client splits; the API never parses separators or tabs, so `REFMAP-7` (the CGI decoding `%XX` but not `+`) can't arise.
- **IDs only, no extra columns.** The legacy echoed the rest of each line after the PANTHER ID (`REFMAP-5`), and the website's enrichment test read its value from there. Here a mapping per ID, in order, duplicates kept, lets a client re-attach its own columns by position. *Alternative:* an `extra` list of strings per ID, echoed back. Rejected: the API would carry, store for a day and serve on every poll data it never reads, up to 100,000 lists of any length; it would need limits and validation of its own; and the only reader, the website's enrichment test, already holds the columns it sent, so it can re-attach them by position.
- **`id` is in each mapping,** although the order already says which ID it is, as cSNP's `substitution` is. A job doesn't return its input, so without `id` the result can't say which ID mapped to what: the frontend's job page, and anyone opening a shared job link, would have only a list of PANTHER IDs. With it, a row can be read on its own, and a client that sorts or filters keeps it. Its cost, up to about 6.4 MB of IDs in a 100,000-ID result, is part of the result's size (Risks).
- **`panther_id` is `null` for `NOHIT`.** The legacy string means "no PANTHER ID", which JSON says with `null`, as cSNP's `family` does for no hit. The engine's parity test reads `NOHIT` as `None` (decision 5). `panther_id` is whatever the classification file's second column holds, family or subfamily, never split by the API: splitting `PTHR10078:SF1` would be new behaviour, and a client can do it.
- **Every result field is required, and nullable where the engine's is,** so the generated TypeScript is `T | null`, never optional.
- **Union order:** `tools`, `csnp`, then `refmap`, so the existing members keep their places in the generated types.

### 3. The engine interface, proposed

For the engine developer to accept or change before porting, as `score()` was agreed on #19. Nothing in this change imports it.

```python
# panther_engine.refmap
ORGANISM_CODES: frozenset[str]          # the organisms there is a classification file for

@dataclass(frozen=True)
class RefmapInput:
    organism: str                        # an ORGANISM_CODES member
    ids: tuple[str, ...]                 # as submitted: 1 to 100,000, no whitespace

@dataclass(frozen=True)
class IdMapping:
    id: str
    panther_id: str | None               # None where the legacy printed NOHIT

@dataclass(frozen=True)
class RefmapResult:
    mappings: tuple[IdMapping, ...]      # one per input ID, in input order

def map_ids(request: RefmapInput, *, data_dir: Path | str | None = None) -> RefmapResult: ...
```

- **One organism per call,** as the CGI took one. The data folder is `PANTHER_DATA_DIR`, or `data_dir` in tests, as for `score()`.
- **The API validates first.** `map_ids()` raises `ValueError` for input the API rejects: an organism not in `ORGANISM_CODES`, no IDs, or an ID outside the API's rule. The API can't send one, so it's a bug and a generic `500`.
- **No `InputError`.** Every valid input has an answer: each ID maps or doesn't. A `NOHIT` is a mapping with `None`, never an error, as cSNP's "Not scored" is a row.
- **Missing data is an error, not `NOHIT`.** A known organism whose file is missing or unreadable raises (a `500` in the job), where the CGI silently returned `NOHIT` for every ID (`REFMAP-9`). It changes nothing for a correctly deployed service, but it is a deliberate difference from `map_panther.pl`, so it's proposed [divergence 9](../../../docs/parity/divergences.md), with the `422` for an unknown organism.
- **`ORGANISM_CODES`** is what the API checks `organism` against, at submit, without the data, as `SPECIES_CODES` is for cSNP. *Alternative:* the engine reads the list from the data's `stats` file, and the API reads it once at startup. Better if the list changes with each release, but the API then needs the data to validate, and to start. The engine developer chooses; the API's check is the same either way. Names, for a selector, can follow as `ORGANISM_NAMES`, as `SPECIES_NAMES` did.
- **The data,** as `core/data.py` lays out each service: `<PANTHER_DATA_DIR>/refmap/19/`, holding the classification files as `panther_classification/<long name>` and `stats` beside them, unchanged. That is the layout the website fetched over HTTP (`/mapping19/panther_classification/<long name>` and `/mapping19/stats`), so the files can be copied as they are. It doesn't follow either CGI's: at `4fc6a09` the CGI read `panther_classification/<long name>` relative to its working directory, and on `master` it reads `<panther_classification_directory>/panther_classification/<long name>`, with the folder from a `config.yaml` that isn't in `panther-workspace`. Which version and folder production used needs team verification, and doesn't change the engine's layout. The engine maps a code to its file through `stats`. The data version is `"19"`, after the site's `mapping19` URLs. Whether this or tech-stack.md's shared `/data/panther/19/` root is right is an open question in the proposal.

### 4. Validation, rule by rule

The website did no normalising for refmap, unlike cSNP: it posted the text box or the file as it was, and the organism its form sent (`GeneListAnalysisAction.java` 633 to 656, `GeneListAnalysisForm.java` 64 to 89). So the rules follow the CGI, and where it had none, are new. Paths are under `../panther-workspace/legacy/`.

| Field | Rule | Legacy evidence |
| ----- | ---- | --------------- |
| `organism` | Required | `GeneListAnalysisAction.java` 634 to 638: no organism, no mapping |
| `organism` | 1 to 5 characters, `A`–`Z` and `0`–`9` | **New shape.** The site sent the long name (`index.jsp` 1343), which the CGI used as a file name in a two-argument `open` (`genericMapping.cgi` 44 to 46, `REFMAP-8`). The code reads the long name's last `_` part as the organism's short name (`MapOrganism.java` 33 to 36); the contract takes that, which has no path or shell characters. Proposal, Open Questions |
| `organism` | One the engine has a file for | Follow-up, when the engine exports `ORGANISM_CODES`. The CGI mapped everything to `NOHIT` for an unknown one (`REFMAP-9`, proposed divergence 9); the site only offered organisms from `stats` (`index.jsp` 1329 to 1350) |
| `ids` | Required, at least one | An empty input gave the site an empty answer, which it reported as an error (`GeneListAnalysisAction.java` 657 to 660) |
| `ids` | At most 100,000 | The site rejected a mapping of more than 100,000 lines (`UploadedFile.java` 338 to 342, `ListAnalysisConstants.java` 101) |
| `ids` | Each 1 to 64 characters | The 64 is **new**. UniProt accessions are 6 or 10 characters; the help says refmap takes only those (`tips_toolsUploadFile.jsp` 27). Empty: an empty line gave a row with an empty ID and `NOHIT` (`REFMAP-10`), which the site then rejected as a line missing data (`UploadedFile.java` 385 to 388) |
| `ids` | Printable ASCII, no whitespace | **New.** The CGI's ID is everything before the first tab (`genericMapping.cgi` 63), so a tab ends it. A space reached the CGI as `+` (`REFMAP-7`), so no ID with a space or around one ever mapped through the site. Rejecting it changes no answer; trimming it would map what the legacy didn't |
| `ids` | Not trimmed, case-changed or de-duplicated; order kept | The lookup is exact and case-sensitive (`REFMAP-1`); one row per input line, duplicates included (`REFMAP-4`) |
| `input` | No other fields | As every input model |

- **Each rule raises its own message,** without the value: for example "Each ID must be 1 to 64 printable ASCII characters, with no spaces." Pydantic's messages for types, lengths and missing fields don't quote the input; tests check each field with a distinctive value.
- **Rejecting an ID the reference would answer `NOHIT`** (empty, with whitespace, non-ASCII, or over 64 characters) is a deliberate difference from `map_panther.pl`, proposed [divergence 10](../../../docs/parity/divergences.md).
- **The schema carries the shapes** as `pattern`s, `^[A-Z0-9]{1,5}$` with `maxLength` 5 on `organism` and `^[!-~]+$` on each of `ids`, so the generated types and any website client learn the rules from the contract, not only from a `422`. They're set only in the schema (`json_schema_extra`): the validators enforce them, with the messages above, which a pattern mismatch wouldn't give.
- *Alternative:* a UniProt accession pattern for each ID, since the help names only those. Rejected: the CGI looks up any string, and whether every key in the files is an accession needs team verification. A pattern can be added later; relaxing a `422` breaks no client, but tightening one can.
- *Alternative:* default `organism`, as the site preselected the first in its list (`OrganismConstants.java` 191 to 197). Rejected: an explicit organism keeps a client bug from silently mapping against the wrong proteome.

### 5. Parity: the goldens and the quirks

For the engine developer's port; this change maps nothing. The reference is `map_panther.pl` (tech-stack.md), whose lookup is the CGI's line for line; only the way each reads its input differs, and neither way reaches the API. RefProteomeMapper is public, so its reference image can clone it at a pinned commit, unlike cSNP's. It needs Perl only.

- **Goldens:** fixed gene lists run through `map_panther.pl` against fixed classification files, saved byte for byte in `engine/tests/golden/refmap/`. The engine's parity test reads each output line's first two fields, with `NOHIT` as `None`, and compares them with `map_ids()`'s mappings for the same IDs. The inputs, and why each is there, are in the legacy behaviour doc, "Proposed Golden Inputs".
- **Every quirk is Match for M1,** following the code: exact, case-sensitive lookup (`REFMAP-1`); the last of a repeated ID in a classification file wins (`REFMAP-2`); one mapping per input ID, duplicates kept (`REFMAP-4`). Each **Decide** in the doc is a keep-or-fix question for the engine developer; a fix is a proposed row in `docs/parity/divergences.md`, never shipped without an approver.
- **Never replicated,** with no row, since it changes no correct request's answer: the unchecked `organism` in a two-argument `open` (`REFMAP-8`), as for cSNP's `CGI-5`.
- **Proposed divergences,** for the engine or API developer to approve: an unknown organism or missing file, which the reference maps to `NOHIT` for every ID (`REFMAP-9`, row 9), and the IDs the API rejects (`REFMAP-10` and the new rules, row 10). Neither changes the answer to a request the API accepts.
- **The reference's version.** RefProteomeMapper's `master` (`649c85f`) changed only the CGI since `4fc6a09`, to read its data folder from `config.yaml`; `map_panther.pl` is the same file in both, so the goldens are the same. Which CGI production ran needs team verification.

### 6. The `501`, and the code

As `add-csnp-job` did it:

```text
api/src/panther_api/jobs/
  refmap.py    RefmapInput (with its validation), IdMapping, RefmapResult. Pydantic only, so a
               worker imports it cheaply
  work.py      RefmapJobRequest joins JobRequest, RefmapResult joins JobResult; run_job's refmap
               case raises NotImplementedError
  models.py    RefmapJob joins Job
api/src/panther_api/routers/jobs.py
               the 501 for a refmap request, before submit, and the 501 documented on POST /jobs
```

- **Validate, then `501`:** clients get the real `422`s now, and the only change when mapping lands is that a valid request gets a `202`.
- **No job:** a job that always fails would look like a fault; a `501` says what's true. The `501`'s description names `refmap` only, since `csnp` runs now.
- **`run_job`'s case** can't be reached, since the router never submits a `refmap` job, but its `match` must cover every member for the strict type check. If one got there, the job would fail with the generic `500`, never a made-up mapping.
- **The frontend** changes only by its regenerated types. `wire.ts` lists each service's job by hand, so the new schema members don't reach its union, and nothing returns a `refmap` job while the `501` stands. The refmap form's change adds `refmap` there, with a results view.

### 7. At most 100 errors in a `422`, for every service

Each bad ID is its own field error, and up to 100,000 IDs are allowed, so one small request could produce a very large `422`: cSNP's 1,000 substitutions had capped the errors at 1,000. `problems._validation_error` now lists the first 100 field errors, each with its `loc`, `msg` and `type` as before. With more than 100, the `detail` says how many there were: "Request validation failed: 100,000 fields are invalid, and the first 100 are listed." With 100 or fewer, the body is unchanged. The rule is a MODIFIED requirement in `api-service` ([specs/api-service/spec.md](specs/api-service/spec.md)).

Measured in-process (`TestClient`, on a Windows developer machine, 2026-10-30), for a refmap request of 100,000 empty-string IDs, a 400 KB body:

| | Response | Time to answer | Of which, the problem handler |
| - | -------- | -------------- | ----------------------------- |
| Before | 11,989,005 bytes, 100,000 errors | 2.6 to 3.2 s | 1.8 s |
| After | 11,864 bytes, 100 errors | 1.1 to 1.2 s | 1 ms |

- **What remains is before the handler,** and the cap can't reach it: Pydantic validating the list (about 0.2 s, as for a valid 100,000-ID request, which answers its `501` in 0.17 s), then building its 100,000 error dicts (`ValidationError.errors()`, about 0.9 s), which FastAPI copies to prefix each `loc`. It runs on the event loop, as all request validation does. A follow-up could stop collecting at 100 bad IDs, with one list-level validator on `ids` that checks each item and raises the first 100 errors itself at their indexes, instead of one validator per item; or limit how often one client can send a request. Not done here: it's a change to how every list is validated, not to this contract.
- **The frontend** reads only `errors` (`inputErrors` in `src/app/api/wire.ts`) and puts each message on its field; it never reads the `detail`. A cSNP request with more than 100 bad substitutions now shows the first 100, which the form's own checks make unlikely.

### 8. Tests

- **The rules,** in `api/tests/test_refmap_input.py`, on `RefmapInput` itself: what reaches the engine is only visible there, since the API returns no job.
- **Through the API,** in `test_jobs.py`: each field with a distinctive invalid value gets a `422` at its `loc`, without the value, and no job; 100,000 empty IDs get the first 100 errors and the count; a valid request gets the `501` and no job; a `tools` job still succeeds afterwards; `run_job` with a `refmap` request raises `NotImplementedError`.
- **The cap,** in `test_problems.py`, on a test route: 1 and 100 errors listed unchanged with the plain `detail`; 101 and 12,345 give the first 100, each with its `loc`, and the count in `detail`.
- **The schema,** in `test_openapi.py`: the `refmap` members and mappings of both unions, the result's required and nullable fields, the `501`, and the `pattern`s, which accept and reject the same values as the validators.
- **No test builds a `RefmapResult` with values.** Its shape is tested through the schema only, so no made-up PANTHER ID exists anywhere.

## Risks / Trade-offs

- **[The organism key is wrong]** → If the long names' last part isn't a unique 1-to-5-character code, the contract's `organism` changes before the port. It's the first open question; relaxing the shape breaks no client.
- **[A rule rejects input the legacy would have mapped]** → Only IDs over 64 characters, or with whitespace or non-ASCII characters. The site's input reached the CGI with spaces as `+`, so none of those mapped through the site. Easy to relax. Proposed divergence 10 records it.
- **[Jobs are the wrong call for a lookup]** → Decision 1's alternative can be added later beside the job, with the same models, without breaking anyone.
- **[The `501` outlives its purpose]** → Tied to the wiring change in the Workflow follow-up, as cSNP's was.
- **[The wiring drops the `501` before the organism check]** → Then any well-shaped code, such as `ZZZZZ`, would reach the engine. A comment beside the `501` in `routers/jobs.py`, and the Workflow follow-up, say the check against `ORGANISM_CODES` lands in the same change.
- **[A large result's size in memory]** → Known issue, for the wiring change to fix; not fixed here, because nothing builds a `refmap` result yet. 100,000 `IdMapping` models take about 59 MB, and the job keeps them, with the 100,000-ID request in `JobRecord.request`, for `job_expiry_seconds` (24 hours by default); nothing caps how many such jobs are kept, and each poll serialises about 5 MB. The wiring change should store a result compactly, for example as its serialised JSON or as parallel lists, and/or cap or shorten how long large results are kept. `id` stays in each mapping (decision 2).
- **[A `422` is slow to build for a large bad list]** → The cap bounds the response, not the 1.1 s Pydantic spends listing 100,000 errors on the event loop (decision 7). A follow-up, if it matters in practice.
- **[Contract drift from the engine's dataclasses]** → The engine developer reviews decision 3 before porting; the wiring's adapter maps the fields one to one, and its tests fail on a mismatch.

## Migration Plan

Nothing to migrate: the contract is additive, and a `refmap` request was a `422` (unknown `service`) before this change. The `422`'s cap changes no body with 100 or fewer errors. Rollback is reverting the commits and regenerating the frontend's types. The wiring change later deletes the `501`, its schema entry and tests, replaces `run_job`'s case with an adapter to `map_ids()`, checks `organism` against `ORGANISM_CODES` in the same change, stores large results compactly (Risks), and adds `refmap`'s data version.
