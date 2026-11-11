# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **Jobs, the request and job unions tagged by `service`, `work.py` as what the workers run, and adding a service by a request, a result and a `run_job` case:** `openspec/specs/scoring-jobs/` and the archived [add-scoring-jobs design](../archive/2026-10-29-add-scoring-jobs/design.md).
- **A contract with a `501` first, then the port, then the wiring:** the archived [add-refmap-job](../archive/2026-10-30-add-refmap-job/design.md) (decision 6, the `UNAVAILABLE` table) and [add-refmap-form](../archive/2026-10-30-add-refmap-form/design.md), and how [wire-refmap](../wire-refmap/design.md) removed the `501`. `api/CLAUDE.md`, "Adding a Service", lists the four steps.
- **cSNP's sequence rules,** which follow the website's form: the archived [add-csnp-job design](../archive/2026-10-29-add-csnp-job/design.md), and `scoring-input`.
- **Problem details, `422`s that never echo a value, at most 100 errors, the committed schema:** `openspec/specs/api-service/` and [docs/design/api-stack.md](../../../docs/design/api-stack.md).
- **The engine is a library; the website moves to the JSON API with no compatibility endpoints; scoring goes through jobs:** [docs/design/tech-stack.md](../../../docs/design/tech-stack.md), Engine condition 1 and API recommendations 1 and 2.
- **The frontend stack and conventions:** [docs/design/frontend-stack.md](../../../docs/design/frontend-stack.md) and [frontend/CLAUDE.md](../../../frontend/CLAUDE.md).
- **What the library holds, how `pantherScore.pl` reads it, the best-hit rule, the alignment, and the time and memory `hmmscan` takes:** the [hmmscore library survey](../../../docs/parity/hmmscore-library-survey.md), from #67. M1 ports the website's path, `scoreAlignXml.cgi`; `alignOnTheFly.cgi` isn't used (engine developer, 2026-11-09, recorded in #67's proposal).

Paths below are under `../panther-workspace/legacy/`, with `pantherScoring/` at `89ea0ae`. The behaviour is in [specs/scoring-input/spec.md](specs/scoring-input/spec.md), [specs/scoring-jobs/spec.md](specs/scoring-jobs/spec.md) and [specs/scoring-ui/spec.md](specs/scoring-ui/spec.md).

## Goals / Non-Goals

**Goals:**

- The frontend and the website build against the real `hmmscore` request, result and `422`s now.
- The engine developer ports `scoreAlignXml.cgi` against a fixed interface, and the wiring changes the API's code, not its contract.
- Every output field traces to the CGI's XML, or is marked new; every input rule traces to the website's form, or is marked new.
- The settings #68 asks for exist, with defaults and checks, before hmmscore is served.

**Non-Goals:**

- Scoring anything, or importing more of `panther_engine.hmmscore` than exists.
- Several sequences per job, all hits, InterProScan output, or `alignOnTheFly.cgi`'s alignment of a stored sequence.
- Choosing the server's values for the settings (#68).
- The data check at startup and hmmscore's data version in `Versions`: both come with the wiring, as for refmap.
- The site's relatedness icon (proposal, Open Questions).

## Decisions

### 1. One sequence per job

An `hmmscore` input is one protein.

- **It's what the service did.** The website's form rejected more than one `>` (`SequenceSearchForm.java` 177 to 183), and `scoreAlignXml.cgi` reported one hit and one alignment. `pantherScore.pl` batches, but the CGI read only the first line of its output (`scoreAlignXml.cgi` 161), so with several sequences it reported whichever came first in Perl's hash order.
- **It bounds a job.** The survey shows a query's time and memory grow with its length. One sequence, under a residue limit, gives each job a known worst case, which the time limit and the running cap (decision 5) are set against.
- **It matches cSNP's input,** so the sequence rules, their code and the form's check are shared.
- *Alternative:* `sequences`, a list, as `pantherScore.pl` takes a FASTA file. Rejected for now: the website never sent more than one, a batch's worst case is the sum of its sequences, and a client can submit one job per sequence. Several-sequence scoring can be added later as a new field or a new service name, without breaking this one.

### 2. The contract

The request:

```json
{ "service": "hmmscore", "input": { "sequence": ">sp|P02649|APOE_HUMAN\nMKVLWAALLV..." } }
```

The job, once the engine is wired in. These are types, not values: nothing in this change produces a result.

```text
{
  "id": …, "service": "hmmscore", "status": …, "created_at": …, "started_at": …, "finished_at": …,
  "result": {
    "hit": {
      "panther_id": string,        "PTHR18976:SF2" or "PTHR18976"
      "name": string | null,
      "evalue": string,            as hmmscan printed it, such as "7e-131"
      "score": string,             as hmmscan printed it, such as "439.0"
      "alignment": string          hmmsearch's text, lines and spacing kept
    } | null                       null: no model passed the cutoff
  } | null,
  "error": Problem | null,
  "versions": Versions
}
```

Each field, against what the service returned. `scoreAlignXml.cgi` printed `<scores>` holding, for the first line of `pantherScore.pl -D B`'s output, `<id>`, `<eval>` and `<align>` (124 to 158), and nothing for no line. `pantherScore.pl` printed sequence ID, HMM ID, name, E-value, score and range, tab-separated (`printRes`, 275).

| Field | Source | New? |
| ----- | ------ | ---- |
| `hit: null` | An empty `<scores>`, which the site showed as "There were no hits to PANTHER found for the given sequence" (`hmmScoreResults.jsp` 52 to 54). It happens when `hmmscan` finds nothing, or when the best hit's E-value is over 1e-3 (`getBestHit` 338) | No |
| `panther_id` | `<id>`: the output's second column, the HMM ID `runHmmscan` reads from the model's name (`pantherScore.pl` 387 to 389) | No |
| `evalue` | `<eval>`: the fourth column, the full-sequence E-value as `hmmscan`'s table printed it. The site called it the "HMM E-value score" (`HMMScoreXMLParser.java` 100 to 104, `hmmScoreResults.jsp` 48) | No |
| `alignment` | `<align>`: `hmmsearch` of the best hit's model file against the query, from the line after "Domain annotation for each sequence" to the line before "Internal pipeline statistics summary:" (`scoreAlignXml.cgi` 133 to 156). The CGI escaped `<` and `>` for the XML; the site's parser unescaped them, and its page showed the text as `hmmsearch` wrote it, in a `<pre>` (`hmmScoreResults.jsp` 49) | No |
| `name` | `names.tab`'s name for `panther_id`. **New in the service:** the CGI ran `pantherScore.pl` without `-n` (111), so its name column was empty, and the site looked the name up in its own database (`HMMScoreXMLParser.java` 97). #67 records that `names.tab` is in sync with that database. `null` where `names.tab` has no line, as the site showed "family_not_available" (`HMMHitBean.java` 19) | Yes |
| `score` | The fifth column, the full-sequence bit score, which `getBestHit` ranks by. **New in the contract:** `pantherScore.pl` printed it, and the CGI dropped it. It's what decided the hit, so a client can see why one model won | Yes |

- **Left out:** the output's sequence ID, which is always the CGI's `sequence` (decision 3), and its range, the query positions the hit's domains span, which the CGI dropped. Neither was shown.
- **`evalue` and `score` are strings,** as `hmmscan` printed them. `getBestHit` compares them as printed, and the site showed the E-value's text. A number would turn `7e-131` and `7.0e-131` into one value, and goldens compare text. A job has one hit, so no client sorts them. Proposal, Open Questions.
- **`alignment` is text, not parsed.** The legacy showed `hmmsearch`'s own text. Parsing it into domains and rows would be new behaviour, with its own parity question; a client that needs it can parse the text, and a later change can add parsed fields beside it.
- **One hit.** `getBestHit` can return several models that tie, and the CGI showed the first line, in Perl's hash order (`HMMSCORE-1`, decision 9). Which one the port reports is the engine developer's call (proposal, Open Questions); the contract has one either way.
- **`panther_id`, as in `refmap`'s result,** for the same kind of value, `PTHRnnnnn` or `PTHRnnnnn:SFn`.
- **Every field is required, and nullable where the engine's is,** so the generated TypeScript is `T | null`, never optional.
- **Union order:** `tools`, `csnp`, `refmap`, then `hmmscore`, so the existing members keep their places in the generated types.
- **Schema components:** `HmmscoreJobRequest`, `HmmscoreInput`, `HmmscoreJob`, `HmmscoreResult` and `HmmHit`.

### 3. Validation, rule by rule

The website's HMM scoring form normalised the sequence before the CGI saw it, as cSNP's did, but not quite the same way (`SequenceSearchForm.java` 167 to 205, `HMMSCORE-6`). The API applies cSNP's rules, moved from `jobs/csnp.py` to `jobs/fields.py` and shared, with each service's messages.

| Rule | The website's HMM scoring form | Here |
| ---- | ------------------------------ | ---- |
| Required, not empty | `errors.sequence.not.available` (171 to 175) | Same |
| At most one `>` | `errors.too.many.sequences` (177 to 183) | Same |
| One header line at the start removed | `^>[^\n]*`, without trimming first (186 to 190) | After trimming, as cSNP's. Without the trim, a sequence pasted after a blank line kept its header, which the CGI then read as one header line holding the residues too (`HMMSCORE-6`). Trimming changes only that case |
| All whitespace removed | `\s+` (192 to 195) | Same |
| At most 50,000 residues | `errors.sequence.too.long` (199 to 202) | Same, and the configured residue limit below it (decision 7). **New:** the limit, proposed divergence 11 |
| Upper-cased | Not done | **New,** as cSNP's. HMMER reads residues in either case alike, so no hit or alignment should change; the port's goldens confirm it (proposal, Open Questions) |
| Printable ASCII | Not checked | **New,** as cSNP's. The site posted the text unencoded (`SequenceSearchAction.java` 80), so the CGI decoded `%xx` and `+` in it (`scoreAlignXml.cgi` 85 to 86); a non-ASCII character never reached `hmmscan` as typed |
| At most 1,000,000 characters before normalising | None | **New,** as cSNP's. Bounds the work one request causes |
| No other fields | | As every input model |

- **The query's name.** The form removed the header, so the CGI always added its own, `>sequence` (93 to 95), and `hmmsearch`'s text names the query `sequence`. The engine names it so, and the alignment matches the reference's.
- **A sequence `hmmscan` can't read,** such as one with a digit, passes these rules. The engine raises `InputError`, which fails the job with a `422` and its message, as cSNP's `blastp` does (divergence 8). The CGI died and the site showed its error page (`HMMSCORE-8`). Proposal, Open Questions.
- **Messages** don't quote the sequence. Tests check each rule with a distinctive value.

### 4. The engine interface, proposed

For the engine developer to accept or change before porting, as `score()` and `map_ids()` were. Nothing in this change imports it.

```python
# panther_engine.hmmscore
DATA_VERSION: DataVersion                # {"service": "hmmscore", "panther": "19"}

@dataclass(frozen=True)
class HmmscoreInput:
    sequence: str                        # normalised by the API: upper-case, no header or whitespace

@dataclass(frozen=True)
class HmmHit:
    panther_id: str                      # runHmmscan's HMM ID
    name: str | None                     # names.tab's; None if it has no line for the ID
    evalue: str                          # full-sequence E-value, as hmmscan printed it
    score: str                           # full-sequence bit score, as hmmscan printed it
    alignment: str                       # hmmsearch's text, as scoreAlignXml.cgi cut it

@dataclass(frozen=True)
class HmmscoreResult:
    hit: HmmHit | None                   # None: no hit, or the best hit's E-value is over 1e-3

def score(
    request: HmmscoreInput,
    *,
    data_dir: Path | str | None = None,
    cpu: int = 0,                        # hmmscan's --cpu
    timeout: float | None = None,        # seconds for the whole job: hmmscan, then hmmsearch
) -> HmmscoreResult: ...

def check_data(data_dir: Path | str | None = None) -> None: ...
```

- **Steps, as the CGI's:** `hmmscan --domtblout` of the query, named `sequence`, against `globals/binHmm`; `getBestHit`'s rule ([the survey](../../../docs/parity/hmmscore-library-survey.md#what-it-means-for-port-hmmscore)); then `hmmsearch` of the model file at the hit's HMM ID against the query, cut as the CGI cut it. Each tool runs with an argument list, in the job's own work folder, never a shared temp file (`HMMSCORE-7`).
- **`cpu` and `timeout` come from the API's settings** (decision 5), with each job. Running past `timeout` kills the tool and raises `InputError` with a fixed message, such as "The search took longer than this service allows. Try a shorter sequence.", so the user learns what to change, instead of the generic `500`. Proposal, Open Questions.
- **The API validates first.** `score()` may raise `ValueError` for a sequence the API can't send; that's a bug and a generic `500`.
- **Missing data is an error,** as for refmap: `check_data()` names what's missing, and the API logs it at startup.
- **The data** is `<PANTHER_DATA_DIR>/hmmscore/19/`, as #67 lays it out.

### 5. The settings, and their defaults

Four new fields on `Settings`, read once at startup with the others, each with a `Field` constraint, so an invalid value stops the API:

| Setting | Default | Allowed | Used from |
| ------- | ------- | ------- | --------- |
| `hmmscore_max_residues` | 5,000 | 1 to 50,000 | This change: the router's check (decision 7) |
| `hmmscore_time_limit_seconds` | 300 | 1 or more | The wiring: passed to `score()` as `timeout` |
| `hmmscore_max_running` | 1 | 1 or more | This change: the runner (decision 6) |
| `hmmscore_cpu` | 0 | 0 or more | The wiring: passed to `score()` as `cpu` |

**The defaults are placeholders,** reasoned only from the survey's measurements on the full library ([hmmscan on the Full Library](../../../docs/parity/hmmscore-library-survey.md#hmmscan-on-the-full-library)). The server sets its own values once they're measured there (#68). No server's hardware is assumed here.

- **5,000 residues.** The survey measured four queries: 317, 381 and 4,646 residues, and 50,000. At `--cpu 0`, the 4,646-residue Q14204 took about 0.5 GiB and 53 s warm, 93 s cold; `titin-50000` took 21 GiB and about 20 minutes. Nothing in between was measured, and the survey notes titin's own long models make it a hard case. So the default stays just above the longest query measured to be cheap. A server raises it after measuring longer queries on its own disk. It may never exceed the website's 50,000.
- **300 seconds.** About three times the slowest run measured at or under 5,000 residues and `--cpu 0` (Q14204, 93 s cold), leaving room for the `hmmsearch` step, a slower disk and a busier machine. The short queries took 9 to 16 s. A server that raises the residue limit raises this with it: `titin-50000` took 1,153 to 1,186 s at `--cpu 0`.
- **One running at once.** Every `hmmscan` reads all of `binHmm.h3f`, 5.3 GB, and the memory a query needs grows with its length. The survey's runs at once were slowed by a shared file system and can't size anything. One is the cautious start, and leaves the other workers to `csnp` and `refmap`.
- **`--cpu 0`.** Each query's tables were the same at every `--cpu`, so it's free to choose. At `--cpu 0` a query uses the least memory (Q14204: 512 MiB, against 1,503 MiB at `--cpu 2` and 2,857 MiB at `--cpu 4`) and one CPU, with the same CPU time. More threads shorten a long query but multiply its memory. A server with spare cores raises it. `pantherScore.pl` passes no `--cpu` to `hmmscan` (377), so production ran HMMER's default; which that was, on production's build, needs team verification, and changes no table.
- **Names** follow the existing ones: `PANTHER_API_HMMSCORE_MAX_RESIDUES`, `PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS`, `PANTHER_API_HMMSCORE_MAX_RUNNING`, `PANTHER_API_HMMSCORE_CPU`. `docs/testing/api.md` lists them with the others.
- *Alternative:* a time limit that grows with the sequence, as cSNP's `blastp` limit does (base plus seconds per residue). Rejected for now: with only four measured queries the slope is a guess, and one number is easier for a server to set. The engine can scale it later inside `timeout`.
- *Alternative:* decide the values in `port-hmmscore`, as #68 first suggested. The settings are the API's, read at its startup, so they're built here; their server values still wait for measurements.

### 6. The running cap

`JobRunner` gets `hmmscore_max_running`, and a semaphore of that size. An `hmmscore` job's task takes it **before** a worker slot, so a job waiting for the cap holds no worker, stays `queued`, and lets a job of another service run on the free worker.

- **Per service, in the runner,** keyed by `service`, so treegrafter can have one later. Only `hmmscore` has one now.
- **The waiting cap still counts unfinished jobs past one per worker** (`submit`). A job waiting for the hmmscore cap counts there as one that may hold a worker. With the default of 50 waiting, that never refuses a request a worker could take; with a cap of 0 waiting, a tools job can get a `503` while an hmmscore job waits and a worker is free. Recorded, not fixed: counting by service would need the runner to know each job's place in two queues.
- **Tested in the runner,** with a stand-in `run_job` from `tests/job_helpers.py` that waits on an event: while the router answers `501`, no `hmmscore` job reaches the runner through the API.

### 7. The configured residue limit is a `422`

The request model enforces the fixed rules, including the website's 50,000. The configured limit can't be in the model: it's read at startup, and the committed schema must equal the served one whatever the server sets. So the router checks it, after the model and before the `501`, and raises a `RequestValidationError` with one error at `["body", "hmmscore", "input", "sequence"]`. The existing handler (`problems.py`) gives it the same shape as any `422`. Its message names the limit, which is configuration, not the user's data: "The sequence has more than 5,000 residues, the most HMM scoring takes."

- **The schema** documents a `maxLength` of 1,000,000 on `sequence`, as cSNP's, and describes the residue limit in words, without a number.
- **The form checks the website's 50,000,** a rule that holds on every server, and shows the API's `422` for the server's own limit on the field. *Alternative:* an endpoint, such as `GET /api/v1/hmmscore/limits`, so the form can say the limit before submitting. Not now: it's one more endpoint before the server's values are known. Proposal, Open Questions.

### 8. The `501`, and the code

As `add-refmap-job` did it:

```text
api/src/panther_api/jobs/
  hmmscore.py  HmmscoreInput (with log_summary), HmmHit, HmmscoreResult. Pydantic only
  fields.py    the sequence normalising, moved from csnp.py, with the messages as arguments
  work.py      HmmscoreJobRequest joins JobRequest, HmmscoreResult joins JobResult; hmmscore's
               row in UNAVAILABLE; run_job's hmmscore case raises NotImplementedError
  models.py    HmmscoreJob joins Job, as a JobFields with its service and result
  runner.py    the running cap (decision 6)
api/src/panther_api/routers/jobs.py
               the configured residue limit (decision 7); the 501 from UNAVAILABLE, unchanged
api/src/panther_api/settings.py
               the four settings (decision 5)
```

- **Validate, then `501`:** clients get the real `422`s now. The `501` description names `hmmscore`, "until the engine scores it".
- **The comment on hmmscore's `UNAVAILABLE` row** says what the wiring must add with its removal: `score()` with the time limit and `--cpu`, the data check, and the data version.
- **The result is small,** one hit with an alignment of a few kB, so it stays a model, not a `SerializedResult` (`wire-refmap`, decision 4).

### 9. The legacy behaviour, recorded

A new `docs/parity/hmmscore-legacy-behaviour.md`, as `refmap-legacy-behaviour.md` is, records the CGI and the site as the code runs them, with quirk IDs and a parity call each. The survey stays the record of the library and of `pantherScore.pl`'s readings; this doc links to it.

| ID | Quirk | Where | Call |
| -- | ----- | ----- | ---- |
| `HMMSCORE-1` | Tied best hits: `getBestHit` returns all models with the best score and E-value as printed; `pantherScore.pl` prints them in hash order, and the CGI shows the first. The 5,450 one-subfamily families can tie as printed | `pantherScore.pl` 225 to 233, 337; `scoreAlignXml.cgi` 161 | **Decide** (proposal, Open Questions) |
| `HMMSCORE-2` | The XML carries no name and no bit score; the site looked the name up in its database | `scoreAlignXml.cgi` 111, 124 to 127; `HMMScoreXMLParser.java` 97 | New fields `name` and `score` |
| `HMMSCORE-3` | The site's "score" is the E-value | `HMMScoreXMLParser.java` 100 to 104; `hmmScoreResults.jsp` 48 | The contract names it `evalue` |
| `HMMSCORE-4` | The results page says no hit is reported when the E-value is *less* than 1e-3; the code reports none when it's greater | `hmmScoreResults.jsp` 38; `getBestHit` 338 | Follow the code. The new page doesn't repeat the sentence |
| `HMMSCORE-5` | The cutoff applies to the best hit only, and a failed best hit leaves the sequence with no result | `getBestHit` 338 | Match (the survey) |
| `HMMSCORE-6` | The form doesn't trim or upper-case, and removes a header only at the very first character | `SequenceSearchForm.java` 186 to 195 | Decision 3 |
| `HMMSCORE-7` | `hmmscan`'s table goes to a fixed `/tmp/temp.domtblout`, so concurrent requests overwrite each other's | `pantherScore.pl` 376; the CGI passes no `-T` (111) | Never replicated, as cSNP's `CGI-6` |
| `HMMSCORE-8` | A sequence `hmmscan` can't read: `pantherScore.pl` dies, the CGI dies after its header, and the site shows its error page | `pantherScore.pl` 382; `scoreAlignXml.cgi` 113 to 115 | `InputError`, a `422` in the job: a divergence row for `port-hmmscore` |
| `HMMSCORE-9` | The alignment is of the model file at the hit's HMM ID, which for 839 `binHmm` models is a different model from the one that scored | `scoreAlignXml.cgi` 133 to 140 | Match (the survey) |

The doc also lists what the site called (`score_cgi` at `/sequence19/scoreAlignXml.cgi`) and how it used the answer, and proposed golden inputs: the site's example, `test.fasta`, a sequence with no hit, a one-subfamily family's member, and a `..pir` model's hit.

### 10. The frontend

As the refmap and cSNP forms are built:

- **`src/features/hmmscore/`:** `HmmscorePage`, `HmmscoreForm`, `useSubmitHmmscore`, `SubmitAlert`, `example.ts` and `index.ts`. One box, so the draft is component state, not a reducer. `/hmmscore` in `router.tsx` renders the page, with `errorElement: <ErrorPage />`.
- **The sequence check is shared.** cSNP's `checkSequence` moves out of `features/csnp/checks.ts` to `src/components/sequence.ts`, with the limit as an argument, since features don't import each other. cSNP's behaviour and messages don't change.
- **The example** is the help page's APOE (`tips_exampleHmmScoreInput_content.jsp` 9 to 20): the 317 residues in its lines of 35, no header. It's cSNP's example sequence, so both import one constant.
- **`services.ts`:** HMM scoring gains `action`, "Score a protein sequence", and keeps `comingSoon: true` until the wiring, as ID mapping did. `formFields.ts` gains `HMMSCORE_FIELDS = ['sequence']`, so "Edit and resubmit" works.
- **Results on the job page,** in `src/features/jobs/`: `HmmscoreHit` shows the PANTHER ID as a link to `https://www.pantherdb.org/panther/family.do?clsAccession=<id>`, opening in a new tab, as the site linked to its own family page (`HMMHitBean.java` 47 to 49); the name; the E-value and the score, as text; and `AlignmentText`, a `<pre>` in an `overflow-x-auto` box, with no wrapping. With no hit, it says there were no hits to PANTHER for the sequence. The job is titled "HMM scoring", and its next step links to an empty form.
- **No thresholds in the UI.** The page shows the E-value as the API gives it, and doesn't repeat the site's sentence about the cutoff (`HMMSCORE-4`) or its relatedness icon (proposal, Open Questions).
- **`wire.ts`** gains the `hmmscore` job and request, with types from the schema only.
- **Mocks:** an `hmmscore` `POST` returns a queued job that succeeds with an obviously made-up hit, `PTHR00000:SF1`, named as mock data, with a short alignment text marked as mock. Tests reproduce the real `501` with `server.use`.
- **No new dependency.** Mantine and Tailwind cover every part.

### 11. Tests

- **API, the rules,** in `api/tests/test_hmmscore_input.py`, on `HmmscoreInput`: each scenario of `scoring-input`'s hmmscore requirements, each rejection with its `loc` and without a distinctive part of the value. cSNP's tests still pass after the move to `fields.py`.
- **API, the jobs,** in `test_jobs.py`: the `422`s, the configured limit at its edge and with a setting changed, a valid request's `501` with no job, a `tools` job after it, `run_job` refusing.
- **API, the settings,** in `test_settings.py`: the defaults and each invalid value.
- **API, the runner:** the running cap's three scenarios in `test_jobs.py`, on a `JobRunner` with a stand-in `run_job`, and an hmmscore job's log line in `test_job_logs.py`.
- **API, the schema,** in `test_openapi.py`: the members of both unions, the result's required and nullable fields, the `501` naming `hmmscore`.
- **No test builds an `HmmHit` with real-looking values.** Its shape is tested through the schema; the frontend's mock is marked as mock.
- **Frontend:** Vitest for the shared sequence check (cSNP's cases still pass), the form (example, checks, `422`, `501`, `500`, network, each beside a success), the results (hit, no hit, running, the alignment kept) and the mocks; Playwright, mock mode on desktop and mobile (the alignment box scrolls, the page doesn't), and api mode against the real `501` and a `422` past the default limit.

## Risks / Trade-offs

- **[The defaults are wrong for the server]** → They are settings, and the server sets them after measuring (#68). The residue limit can't be raised past 50,000 by mistake.
- **[The residue limit rejects input the site accepted]** → Proposed divergence row 11, for an approver before it ships. A server can raise it to 50,000.
- **[The `501` outlives its purpose]** → Tied to the wiring change, as refmap's was. The comment on the `UNAVAILABLE` row lists what the wiring adds.
- **[Settings that do nothing yet]** → The time limit and `--cpu` are read and checked now, but reach the engine only with the wiring. `docs/testing/api.md` says so, so nobody tunes them expecting an effect.
- **[Ties make the reported hit unstable]** → An open question for the engine developer; the contract carries one hit, and any rule the port picks is a divergence row.
- **[`hmmsearch`'s text changes with HMMER's version]** → The engine pins 3.4, and the survey found 3.1b2 and 3.4 give identical alignments on amd64. On arm64 some numbers differ in the last digit; the goldens keep a version per architecture.
- **[A waiting hmmscore job counts towards the waiting cap]** → Decision 6; harmless at the default cap.
- **[Contract drift from the engine's dataclasses]** → The engine developer reviews decision 4 before porting; the wiring's adapter maps the fields one to one, and its tests fail on a mismatch.

## Migration Plan

Nothing to migrate: the contract is additive, and an `hmmscore` request was a `422` (unknown `service`) before this change. The new settings have defaults. Rollback is reverting the commits and regenerating the frontend's types.

The wiring change later deletes hmmscore's `UNAVAILABLE` row, which takes the `501` and its schema entry with it; replaces `run_job`'s case with an adapter to `score()`, passing the time limit and `--cpu`; adds hmmscore's data check at startup and its data version; REMOVES "hmmscore not available yet" from `scoring-jobs` and adds the time limit's behaviour; and turns HMM scoring's "coming soon" off.
