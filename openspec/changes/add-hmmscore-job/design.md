# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **Jobs, the unions tagged by `service`, `work.py`, and adding a service:** `openspec/specs/scoring-jobs/`, and `api/CLAUDE.md`, "Adding a Service".
- **A contract with a `501` first, then the port, then the wiring:** the archived [add-refmap-job](../archive/2026-10-30-add-refmap-job/design.md) (decision 6, `UNAVAILABLE`), and how [wire-refmap](../archive/2026-11-10-wire-refmap/design.md) removed it.
- **cSNP's sequence rules,** after the website's form: the archived [add-csnp-job design](../archive/2026-10-29-add-csnp-job/design.md), and `scoring-input`.
- **Problem details, `422`s that never echo a value, the committed schema:** `openspec/specs/api-service/` and [docs/design/api-stack.md](../../../docs/design/api-stack.md).
- **The engine is a library; the website moves to the JSON API; scoring goes through jobs:** [docs/design/tech-stack.md](../../../docs/design/tech-stack.md).
- **The library, `pantherScore.pl`'s readings, the best-hit rule, the alignment, and `hmmscan`'s time and memory:** the [hmmscore library survey](../../../docs/parity/hmmscore-library-survey.md). M1 ports `scoreAlignXml.cgi`'s path.

Legacy paths are under `../panther-workspace/legacy/`, with `pantherScoring/` at `89ea0ae`. The behaviour is in [specs/scoring-input/spec.md](specs/scoring-input/spec.md) and [specs/scoring-jobs/spec.md](specs/scoring-jobs/spec.md).

## Goals / Non-Goals

**Goals:** every output field traces to the CGI's XML or is marked new; every input rule traces to the website or is a proposed row; the settings #68 asks for exist before hmmscore is served; the wiring changes the API's code, not its contract.

**Non-Goals:** scoring anything; several sequences per job; all hits; `alignOnTheFly.cgi`; the server's values for the settings (#68); the data check and data version, which are the wiring's; the form and results, which are `add-hmmscore-form`.

## Decisions

### 1. One sequence per job

- **It's what the service did.** The website's form rejected more than one `>` (`SequenceSearchForm.java` 62 to 67), and the CGI reported one hit, from the first line of `pantherScore.pl`'s output (`scoreAlignXml.cgi` 161).
- **It bounds a job,** which the time limit and running cap (decision 5) are set against, and it matches cSNP's input, so the rules and their code are shared.
- *Alternative:* `sequences`, a list, as `pantherScore.pl` takes. Rejected for now: the website never sent more than one, and a client can submit one job per sequence. It can be added later without breaking this field.

### 2. The contract

```text
request: { "service": "hmmscore", "input": { "sequence": string } }
result:  { "hit": { "panther_id": string, "name": string, "evalue": string,
                    "score": string, "alignment": string } | null }
```

The CGI printed `<scores>` holding, for the first line of `pantherScore.pl -D B`'s output, `<id>`, `<eval>` and `<align>` (124 to 158), or nothing. `pantherScore.pl` printed sequence ID, HMM ID, name, E-value, score and range (`printRes`, 275).

| Field | Source | New? |
| ----- | ------ | ---- |
| `hit: null` | An empty `<scores>`: "There were no hits to PANTHER found for the given sequence" (`hmmScoreResults.jsp` 52 to 54). No hit, or the best hit's E-value over 1e-3 (`getBestHit` 338) | No |
| `panther_id` | `<id>`, the HMM ID `runHmmscan` reads (`pantherScore.pl` 387 to 389) | No |
| `evalue` | `<eval>`, the full-sequence E-value as printed; the site's "HMM E-value score" (`HMMScoreXMLParser.java` 100 to 104) | No |
| `alignment` | `<align>`: `hmmsearch` of the hit's model file, from after "Domain annotation for each sequence" to before "Internal pipeline statistics summary:" (`scoreAlignXml.cgi` 133 to 156), unescaped as the site's parser did | No |
| `name` | `names.tab`'s name, always a string: the survey found a line for every model file, and a missing one would read "No name". The CGI ran without `-n` (111), and the site looked names up in its database (`HMMScoreXMLParser.java` 97), with which `names.tab` is in sync (#67) | Yes |
| `score` | The full-sequence bit score, which `getBestHit` ranks by. `pantherScore.pl` printed it; the CGI dropped it | Yes |

- **Left out:** the sequence ID, always `sequence` (decision 3), and the range, which the CGI dropped.
- **`evalue` and `score` are strings,** as printed, as cSNP's `pdel` is (engine developer, 2026-11-11). As numbers, a browser would show `1.2e-05` as `0.000012` and `439.0` as `439`, which `hmmscan` never printed, and goldens compare text. The engine still compares them as numbers to pick the best hit, as `getBestHit`'s `<=>` did. A client that needs a number parses the string.
- **`alignment` is text,** as the site showed it. Parsed fields can be added beside it later.
- **One hit.** On a tie as printed, the subfamily before its family, then the lowest PANTHER ID (decision 9, `HMMSCORE-1`).
- **Every field is required; only `hit` is nullable.** Union order: `tools`, `csnp`, `refmap`, `hmmscore`.

### 3. Validation, rule by rule

The website's form normalised the sequence (`SequenceSearchForm.java` 51 to 89), and then its posting changed it again (`scoreAlignXml.cgi` 79 to 87). The API applies cSNP's normalising, moved to `jobs/fields.py`, then accepts only what 3.1b2 and 3.4 score alike: letters, and a single `*` at the end.

| Rule | The website | Here |
| ---- | ----------- | ---- |
| Required | 55 to 59 | Same |
| At most one `>` | 62 to 67 | Same |
| One header line removed | `^>[^\n]*`, without trimming first (69 to 74) | After trimming. A header after a blank line or spaces was left in, joined to the residues, so the CGI got one header line and no sequence, and answered no hit (`HMMSCORE-6`). Row 12 |
| Whitespace removed | 76 to 79 | Same |
| At most 50,000 residues | 83 to 86 | The configured limit, 10,000 by default and at most, the product owner's (decisions 5 and 7), counting letters only: a final `*` isn't a residue. Row 11 |
| Upper-cased | Not done | New, as cSNP's. HMMER reads either case alike |
| Letters, and one `*` at the end, only | Not checked | New. Measured by the engine developer, 2026-11-11 (below). Row 12 |
| At most 1,000,000 characters before normalising | None | New, as cSNP's |

**The characters** (engine developer, 2026-11-11, one-sequence test model built from APOE):

| In the sequence | 3.1b2 (production, most likely) | 3.4 (the port) |
| --- | --- | --- |
| Letters, either case; `*` at the end | Read | Read |
| `.`, `_`, `~` or `*` inside the sequence | Read, as a position, splitting the hit | Read, one domain |
| `-` | Read, as a position | Refused |
| `>` inside the sequence | Refused | Read |
| Empty | Refused | Read, no hit |
| Digits, `+`, `#`, `!`, `?`, `@` | Refused | Refused |

- **What the reference did with a refused sequence:** answered no hit. `runHmmscan` never checks `hmmscan`'s exit status (`pantherScore.pl` 381), and 3.1b2 leaves an empty `--domtblout`, so `pantherScore.pl` exits 0 and the CGI prints an empty `<scores>` (`HMMSCORE-8`). The API's `422` is row 12. Refusing before a job starts saves a job that reads all of `binHmm.h3f` only to fail.
- **What "as a position" means.** 3.1b2 split the hit at each one: APOE with three inserted scored 667.1 in three domains, against 721.8 in one. 3.4 scored the same insertions 708.5 in one domain. `B`, `J`, `O`, `U`, `X` and `Z` scored alike in both (708.9 to 710.1, and 709.1 to 710.3, in one domain), as did lower case and a final `*`. The 0.2-bit gap on every row comes from pressing the model again in 3.4 (the survey, "The Press Check"); the split doesn't.
- **So the API refuses `-`, `.`, `_`, `~` and any `*` but a final one,** in row 12: neither refusing nor stripping them reproduces 3.1b2, and 3.4 can't. A final `*` is kept, since translated sequences often end with one. `port-hmmscore`'s goldens confirm this on PANTHER's own models.
- **The website's posting** changed the text before `hmmscan` saw it: `&` and `=` cut it short (79, 82), `+` became a space (85), `%xx` was decoded (86) and `<!--…-->` was removed (87). The API refuses all those characters, so they're in row 12 too.
- **The query's name** is `sequence`, as the CGI's (93 to 95), so the alignment text matches.
- **The engine's `InputError`** for an unreadable sequence is then only for a later HMMER that refuses something 3.4 reads.

### 4. The engine interface, proposed

For the engine developer to accept or change before porting. Nothing in this change imports it.

```python
# panther_engine.hmmscore
DATA_VERSION: str = "19"                 # as csnp's "9" and refmap's "19"; the API builds DataVersion

@dataclass(frozen=True)
class HmmscoreInput:
    sequence: str                        # normalised and checked by the API

@dataclass(frozen=True)
class HmmHit:
    panther_id: str
    name: str                            # "No name" if names.tab lacks the ID
    evalue: str
    score: str
    alignment: str

@dataclass(frozen=True)
class HmmscoreResult:
    hit: HmmHit | None

def score(request: HmmscoreInput, *, data_dir: Path | str | None = None,
          cpu: int = 0, timeout: float | None = None) -> HmmscoreResult: ...
def check_data(data_dir: Path | str | None = None) -> None: ...
```

- **Steps, as the CGI's:** `hmmscan --domtblout` against `globals/binHmm`, `getBestHit`'s rule, then `hmmsearch` of the model file at the hit's ID, each with an argument list in the job's own folder, never a shared temp file (`HMMSCORE-7`).
- **Running past `timeout`** kills the tool and raises `InputError`: "The search took longer than this service allows. Try a shorter sequence."
- **The data** is `<PANTHER_DATA_DIR>/hmmscore/19/`, as #67 lays it out.

### 5. The settings, and their defaults

| Setting | Default | Allowed | Used from |
| ------- | ------- | ------- | --------- |
| `hmmscore_max_residues` | 10,000 | 1 to 10,000 | This change: the router (decision 7) |
| `hmmscore_time_limit_seconds` | 720 | 1 or more | The wiring: `score(timeout=…)` |
| `hmmscore_max_running` | 1 | 1 or more | This change: the runner (decision 6) |
| `hmmscore_cpu` | 0 | 0 or more | The wiring: `score(cpu=…)` |

The residue limit is the product owner's; the other defaults come only from the survey's measurements on the full library. The server sets its own (#68).

- **10,000 residues, the product owner's** (2026-11-12): a starting limit, in place of the website's 50,000, expected to cover 99% of queries. It's the default and the most allowed, and row 11 records it, approved. A server may set it lower (#68), and records that value in row 11. Raising it is the product owner's call, and the time limit's default moves with it.
- **720 seconds.** The time limit has to cover the residue limit, or a sequence the API accepted fails with "Try a shorter sequence". No 10,000-residue query was measured, so this is scaled. Per residue at `--cpu 0`, `titin-50000` took 24 ms (1,186 s warm) and Q14204 20 ms (93 s cold for 4,646), so 10,000 residues should take about 240 s. About three times that, for a slower disk, a busier machine and the `hmmsearch` step, as 3,600 s was for 50,000, is 720 s. `port-hmmscore` or the server's measuring (#68) checks it with a 10,000-residue query. A server that lowers the residue limit lowers this with it.
- **One running at once.** Every `hmmscan` reads all of `binHmm.h3f`, 5.3 GB, and memory grows with length. The survey's runs at once came from a shared file system and can't size this.
- **`--cpu 0`.** The tables were the same at every `--cpu`. At 0 a query uses the least memory (Q14204: 512 MiB, against 1,503 MiB at `--cpu 2` and 2,857 MiB at `--cpu 4`; `titin-50000`: 21 GiB, against 42 GiB at `--cpu 2`). `pantherScore.pl` passed none (377); which default production's build used needs team verification.
- *Alternative:* a time limit that grows with length, as cSNP's `blastp` limit does. Not now: four measured queries make the slope a guess.

### 6. The running cap

`JobRunner` gets a semaphore per capped service, `hmmscore` only for now. An `hmmscore` job takes it **before** a worker slot, so a waiting job holds no worker and stays `queued`, and another service's job runs on the free worker. The waiting cap still counts unfinished jobs past one per worker, so with a waiting cap of 0 a tools job can get a `503` while an hmmscore job waits; harmless at the default of 50. Tested on a `JobRunner` with a stand-in `run_job`, since the router answers `501`.

### 7. The configured residue limit is a `422`

The setting is read at startup, and the committed schema must equal the served one, so the model can't hold it. The router checks it after the model and before the `501`, raising a `RequestValidationError` at `["body", "hmmscore", "input", "sequence"]`, which `problems.py` shapes as any `422`. Its message names the limit, which is configuration, not the user's data. The schema describes the limit in words.

### 8. The `501`, and the code

As `add-refmap-job`: `jobs/hmmscore.py` (Pydantic only, with `log_summary()` giving the residues), the unions in `work.py`, a row in `UNAVAILABLE` whose comment lists what the wiring adds, a `run_job` case raising `NotImplementedError`, and `HmmscoreJob` in `models.py`. The result is small, so it stays a model.

### 9. The legacy behaviour, recorded

`docs/parity/hmmscore-legacy-behaviour.md`, as `refmap-legacy-behaviour.md`, links to the survey for the library:

| ID | Quirk | Where | Call |
| -- | ----- | ----- | ---- |
| `HMMSCORE-1` | Tied best hits in hash order; the CGI shows the first. Up to 5,279 one-subfamily families: 324 whose two models differ only in their header always tie, 4,955 differing in the fifth decimal often tie as printed; 114 differ more and 57 in length | `pantherScore.pl` 225 to 233, 337; `scoreAlignXml.cgi` 161 | The subfamily before its family, then the lowest ID: a proposed row for `port-hmmscore` |
| `HMMSCORE-2` | No name or bit score in the XML | `scoreAlignXml.cgi` 111, 124 to 127; `HMMScoreXMLParser.java` 97 | New fields |
| `HMMSCORE-3` | The site's "score" is the E-value | `HMMScoreXMLParser.java` 100 to 104; `hmmScoreResults.jsp` 48 | Named `evalue` |
| `HMMSCORE-4` | The page says no hit when the E-value is *less* than 1e-3; the code, when greater | `hmmScoreResults.jsp` 38; `getBestHit` 338 | Follow the code |
| `HMMSCORE-5` | The cutoff applies to the best hit only | `getBestHit` 338 | Match |
| `HMMSCORE-6` | No trim or upper-case; a header only at the first character, so one after a blank line stayed in and the CGI answered no hit | `SequenceSearchForm.java` 69 to 79 | Row 12 |
| `HMMSCORE-7` | `hmmscan`'s table at a fixed `/tmp/temp.domtblout`, shared by concurrent requests | `pantherScore.pl` 376; no `-T` (`scoreAlignXml.cgi` 111) | Never replicated |
| `HMMSCORE-8` | A sequence `hmmscan` refuses, or an empty one: exit status ignored, empty table, no hit | `pantherScore.pl` 381 | Row 12 |
| `HMMSCORE-9` | The alignment's model file holds a different model for 839 `binHmm` models | `scoreAlignXml.cgi` 133 to 140 | Match |
| `HMMSCORE-10` | The posting: `&` and `=` cut the text, `+` became a space, `%xx` decoded, `<!--…-->` removed | `scoreAlignXml.cgi` 79 to 87; `SequenceSearchAction.java` 80 | Row 12 |

### 10. Tests

`test_hmmscore_input.py` for every `scoring-input` scenario, each rejection without a distinctive part of the value; `test_jobs.py` for the `422`s, the configured limit, the `501`, `run_job` refusing, and the running cap on a `JobRunner`; `test_settings.py`; `test_job_logs.py`; `test_openapi.py` for the unions, the result's fields and the `501`. No test builds an `HmmHit` with real-looking values.

## Risks / Trade-offs

- **[A 10,000-residue job may need more memory than a server has]** → Not measured: at `--cpu 0`, Q14204's 4,646 residues needed 0.5 GiB and `titin-50000` 21 GiB, and the hosting server has 5 GiB available (the survey). The server measures it and sets a lower limit if it must (#68), recorded in row 11.
- **[The time limit's default is scaled, not measured]** → 720 s is three times an estimate (decision 5). A 10,000-residue query in `port-hmmscore` or #68 checks it before the wiring makes it take effect.
- **[Settings that do nothing yet]** → The time limit and `--cpu` reach the engine with the wiring; `docs/testing/api.md` says so.
- **[The busy `503` is sized for cSNP]** → Its `Retry-After` is a fixed 30 s, about a cSNP job (`routers/jobs.py` 21), and the waiting cap of 50 is shared, so a backlog of `hmmscore` jobs gets cSNP and refmap refused too (decision 6). An hmmscore `Retry-After`, sized by `port-hmmscore`'s 10,000-residue timing, and whether hmmscore needs its own waiting cap, are for the wiring.
- **[Ties made the reported hit unstable]** → The port reports the subfamily first, then the lowest ID. With the data sample, `pantherScore.pl -D B` on PTHR35774's consensus gave `PTHR35774:SF1` five times in ten and `PTHR35774` five times, at the same E-value and score; the subfamily's model file is a copy of the family's, so only the ID changes, and the subfamily's ID carries the family's.

## Migration Plan

Additive: an `hmmscore` request was a `422` before. Rollback is reverting and regenerating the frontend's types. The wiring later removes the `UNAVAILABLE` row, calls `score()` with the time limit and `--cpu`, adds the data check and version, REMOVES "hmmscore not available yet", and adds the time limit's behaviour.
