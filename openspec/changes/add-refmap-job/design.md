# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **Jobs, the request union tagged by `service`, the job union, `work.py` as what the workers run, and adding a service by adding a request, a result and a `run_job` case:** `openspec/specs/scoring-jobs/` and the archived [add-scoring-jobs design](../archive/2026-10-29-add-scoring-jobs/design.md).
- **A contract with a `501` first, then the port:** the archived [add-csnp-job design](../archive/2026-10-29-add-csnp-job/design.md), "Not available yet: a `501` at submit", and how [wire-csnp-scoring](../wire-csnp-scoring/design.md) removed it. This change reuses that shape for `refmap` only.
- **Problem details, `422`s that never echo a value, and the committed schema:** `openspec/specs/api-service/` and [docs/design/api-stack.md](../../../docs/design/api-stack.md).
- **The engine is a library the API imports; the website moves to the JSON API with no compatibility endpoints; scoring goes through jobs, and engine code never runs on the event loop:** [docs/design/tech-stack.md](../../../docs/design/tech-stack.md), Engine condition 1 and API recommendations 1 and 2. So the website's form-encoded `fileContents` (`REFMAP-7`) never reaches this API.
- **Input errors:** an engine `InputError` fails the job with a `422` and its message (`add-job-input-errors`, implemented by `wire-csnp-scoring`).
- **`refmap` uses no external tool,** and its parity reference is `map_panther.pl` (tech-stack.md, Runtime Tools and Milestones).

The legacy service, with the evidence for every statement below, is in [docs/parity/refmap-legacy-behaviour.md](../../../docs/parity/refmap-legacy-behaviour.md). Its quirk IDs (`REFMAP-1`, …) are used here. In short: `genericMapping.cgi` loads `panther_classification/<organism>` into a hash of first column to second column, and prints, for each input line, the line's first tab field, its PANTHER ID or `NOHIT`, and the rest of the line. The website sent the raw text box or file, unnormalised, and the organism's long name from its `stats` list.

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
- **IDs only, no extra columns.** The legacy echoed the rest of each line after the PANTHER ID (`REFMAP-5`), and the website's enrichment test read its value from there. Here a mapping per ID, in order, duplicates kept, lets a client re-attach its own columns by position. *Alternative:* an `extra` list of strings per ID, echoed back. Rejected: the API would carry data it doesn't read, up to 100,000 times, and the job would echo input, which no job does (add-scoring-jobs design).
- **`id` is in each mapping** although the order already says which ID it is, as cSNP's `substitution` is: a row can be read on its own, and a client that sorts or filters keeps it.
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
- **Missing data is an error, not `NOHIT`.** A known organism whose file is missing or unreadable raises (a `500` in the job), where the CGI silently returned `NOHIT` for every ID (`REFMAP-9`). It changes nothing for a correctly deployed service, so it needs no divergence row, as cSNP's missing data didn't.
- **`ORGANISM_CODES`** is what the API checks `organism` against, at submit, without the data, as `SPECIES_CODES` is for cSNP. *Alternative:* the engine reads the list from the data's `stats` file, and the API reads it once at startup. Better if the list changes with each release, but the API then needs the data to validate, and to start. The engine developer chooses; the API's check is the same either way. Names, for a selector, can follow as `ORGANISM_NAMES`, as `SPECIES_NAMES` did.
- **The data,** as `core/data.py` lays out each service: `<PANTHER_DATA_DIR>/refmap/19/`, holding the legacy `panther_classification/<long name>` files and `stats` unchanged, so they can be copied from the old server as they are. The engine maps a code to its file through `stats`. The data version is `"19"`, after the site's `mapping19` URLs. Whether this or tech-stack.md's shared `/data/panther/19/` root is right is an open question in the proposal.

### 4. Validation, rule by rule

The website did no normalising for refmap, unlike cSNP: it posted the text box or the file as it was, and the organism its form sent (`GeneListAnalysisAction.java` 633 to 656, `GeneListAnalysisForm.java` 64 to 89). So the rules follow the CGI, and where it had none, are new. Paths are under `../panther-workspace/legacy/`.

| Field | Rule | Legacy evidence |
| ----- | ---- | --------------- |
| `organism` | Required | `GeneListAnalysisAction.java` 634 to 638: no organism, no mapping |
| `organism` | 1 to 5 characters, `A`–`Z` and `0`–`9` | **New shape.** The site sent the long name (`index.jsp` 1343), which the CGI used as a file name in a two-argument `open` (`genericMapping.cgi` 41 to 42, `REFMAP-8`). The code reads the long name's last `_` part as the organism's short name (`MapOrganism.java` 33 to 36); the contract takes that, which has no path or shell characters. Proposal, Open Questions |
| `organism` | One the engine has a file for | Follow-up, when the engine exports `ORGANISM_CODES`. The CGI mapped everything to `NOHIT` for an unknown one (`REFMAP-9`); the site only offered organisms from `stats` (`index.jsp` 1329 to 1350) |
| `ids` | Required, at least one | An empty input gave the site an empty answer, which it reported as an error (`GeneListAnalysisAction.java` 657 to 660) |
| `ids` | At most 100,000 | The site rejected a mapping of more than 100,000 lines (`UploadedFile.java` 338 to 342, `ListAnalysisConstants.java` 101) |
| `ids` | Each 1 to 64 characters | The 64 is **new**. UniProt accessions are 6 or 10 characters; the help says refmap takes only those (`tips_toolsUploadFile.jsp` 27). Empty: an empty line gave a row with an empty ID and `NOHIT` (`REFMAP-10`), which the site then rejected as a line missing data (`UploadedFile.java` 385 to 388) |
| `ids` | Printable ASCII, no whitespace | **New.** The CGI's ID is everything before the first tab (`genericMapping.cgi` 59), so a tab ends it. A space reached the CGI as `+` (`REFMAP-7`), so no ID with a space or around one ever mapped through the site. Rejecting it changes no answer; trimming it would map what the legacy didn't |
| `ids` | Not trimmed, case-changed or de-duplicated; order kept | The lookup is exact and case-sensitive (`REFMAP-1`); one row per input line, duplicates included (`REFMAP-4`) |
| `input` | No other fields | As every input model |

- **Each rule raises its own message,** without the value: for example "Each ID must be 1 to 64 printable ASCII characters, with no spaces." Pydantic's messages for types, lengths and missing fields don't quote the input; tests check each field with a distinctive value.
- *Alternative:* a UniProt accession pattern for each ID, since the help names only those. Rejected: the CGI looks up any string, and whether every key in the files is an accession needs team verification. A pattern can be added later; relaxing a `422` breaks no client, but tightening one can.
- *Alternative:* default `organism`, as the site preselected the first in its list (`OrganismConstants.java` 191 to 197). Rejected: an explicit organism keeps a client bug from silently mapping against the wrong proteome.

### 5. Parity: the goldens and the quirks

For the engine developer's port; this change maps nothing. The reference is `map_panther.pl` (tech-stack.md), whose lookup is the CGI's line for line; only the way each reads its input differs, and neither way reaches the API. RefProteomeMapper is public, so its reference image can clone it at a pinned commit, unlike cSNP's. It needs Perl only.

- **Goldens:** fixed gene lists run through `map_panther.pl` against fixed classification files, saved byte for byte in `engine/tests/golden/refmap/`. The engine's parity test reads each output line's first two fields, with `NOHIT` as `None`, and compares them with `map_ids()`'s mappings for the same IDs. The inputs, and why each is there, are in the legacy behaviour doc, "Proposed Golden Inputs".
- **Every quirk is Match for M1,** following the code: exact, case-sensitive lookup (`REFMAP-1`); the last of a repeated ID in a classification file wins (`REFMAP-2`); one mapping per input ID, duplicates kept (`REFMAP-4`). Each **Decide** in the doc is a keep-or-fix question for the engine developer; a fix is a proposed row in `docs/parity/divergences.md`, never shipped without an approver.
- **Never replicated,** with no row, since neither changes a correct request's answer: the unchecked `organism` in a two-argument `open` (`REFMAP-8`), and an unknown organism or missing file mapping everything to `NOHIT` (`REFMAP-9`).

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

### 7. Tests

- **The rules,** in `api/tests/test_refmap_input.py`, on `RefmapInput` itself: what reaches the engine is only visible there, since the API returns no job.
- **Through the API,** in `test_jobs.py`: each field with a distinctive invalid value gets a `422` at its `loc`, without the value, and no job; a valid request gets the `501` and no job; a `tools` job still succeeds afterwards; `run_job` with a `refmap` request raises `NotImplementedError`.
- **The schema,** in `test_openapi.py`: the `refmap` members and mappings of both unions, the result's required and nullable fields, and the `501`.
- **No test builds a `RefmapResult` with values.** Its shape is tested through the schema only, so no made-up PANTHER ID exists anywhere.

## Risks / Trade-offs

- **[The organism key is wrong]** → If the long names' last part isn't a unique 1-to-5-character code, the contract's `organism` changes before the port. It's the first open question; relaxing the shape breaks no client.
- **[A rule rejects input the legacy would have mapped]** → Only IDs over 64 characters, or with whitespace or non-ASCII characters. The site's input reached the CGI with spaces as `+`, so none of those mapped through the site. Easy to relax.
- **[Jobs are the wrong call for a lookup]** → Decision 1's alternative can be added later beside the job, with the same models, without breaking anyone.
- **[The `501` outlives its purpose]** → Tied to the wiring change in the Workflow follow-up, as cSNP's was.
- **[Contract drift from the engine's dataclasses]** → The engine developer reviews decision 3 before porting; the wiring's adapter maps the fields one to one, and its tests fail on a mismatch.

## Migration Plan

Nothing to migrate: the contract is additive, and a `refmap` request was a `422` (unknown `service`) before this change. Rollback is reverting the commit and regenerating the frontend's types. The wiring change later deletes the `501`, its schema entry and tests, replaces `run_job`'s case with an adapter to `map_ids()`, checks `organism` against `ORGANISM_CODES`, and adds `refmap`'s data version.
