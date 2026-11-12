# Proposal

**Area:** cross-cutting. The code is in `api/`, plus the regenerated `frontend/src/app/api/schema.d.ts`. Nothing in `engine/` changes, but design.md proposes the engine's `hmmscore` interface, so the engine developer approves it, and the frontend developer reviews the contract (CONTRIBUTING.md, Review Rules). The form and results are `add-hmmscore-form`.

**Built on** `wire-refmap`'s archived text: both modify `scoring-jobs`' "Configuration from the environment", and `wire-refmap` was archived in #69.

## Why

`hmmscore` is the third service to port. Issue #42 asks for its contract before the port, as cSNP (#19) and refmap (#30) had theirs, so the frontend builds against the real request, result and `422`s, and the engine developer ports `scoreAlignXml.cgi` against a fixed interface. The [library survey](../../../docs/parity/hmmscore-library-survey.md) showed a long query needs far more time and memory than a typical protein, and #68 asks for limits on both before hmmscore is served. They're settings of the contract, so they come here.

## What Changes

- **An `hmmscore` job request:** `{"service": "hmmscore", "input": {"sequence": "MKVLWAALLV..."}}`. One protein per job, as `scoreAlignXml.cgi` scored one (design.md, decision 1).
- **The sequence is normalised as cSNP's** (trimmed, one FASTA header removed, whitespace removed, upper-cased), and **holds only letters, and a single `*` at the end,** which HMMER 3.1b2 and 3.4 score alike. Anything else is a `422` before any job starts (design.md, decision 3).
- **An `hmmscore` job** with a `result` of `{"hit": null}`, or `{"hit": {"panther_id", "name", "evalue", "score", "alignment"}}`. `panther_id`, `evalue` and `alignment` are what the CGI's XML carried; `name` and `score` are new (design.md, decision 2).
- **Not available yet:** a valid request gets `501`, "HMM scoring isn't available yet.", and no job, through `UNAVAILABLE`, as refmap's did. Validation comes first. The wiring change removes it.
- **Four settings,** read at startup and checked like the others:

  | Variable | Default | What it sets |
  | -------- | ------- | ------------ |
  | `PANTHER_API_HMMSCORE_MAX_RESIDUES` | 50,000, pending the Open Question | The longest sequence hmmscore takes, at most 50,000 |
  | `PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS` | 3,600 | How long one hmmscore job may run |
  | `PANTHER_API_HMMSCORE_MAX_RUNNING` | 1 | hmmscore jobs running at once; more wait, `queued` |
  | `PANTHER_API_HMMSCORE_CPU` | 0 | `hmmscan`'s `--cpu` |

  The server sets its own values once measured there (#68). This change enforces the residue limit and the running cap; the time limit and `--cpu` reach the engine with the wiring (design.md, decision 5).
- **Contract files:** `api/openapi.json` and `frontend/src/app/api/schema.d.ts`, regenerated together.
- **Docs:** `docs/parity/hmmscore-legacy-behaviour.md`, the legacy service with quirk IDs (`HMMSCORE-1`, …); proposed divergence rows 11 and 12; `api/README.md` and `docs/testing/api.md`.

No new dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-input`: the hmmscore `sequence`: its normalising, the characters it may hold, and the residue limit.
- `scoring-jobs`: the `hmmscore` request, its shape, its `501`, and the cap on hmmscore jobs running at once, ADDED. "Configuration from the environment" and "The size of a job's input" are MODIFIED.

## Impact

- **API:** a new `jobs/hmmscore.py`; `jobs/fields.py` (cSNP's normalising, shared); `jobs/work.py`, `jobs/models.py`, `jobs/runner.py`, `routers/jobs.py`, `settings.py`; tests.
- **API contract:** new components `HmmscoreJobRequest`, `HmmscoreInput`, `HmmscoreJob`, `HmmscoreResult` and `HmmHit`, and the `501` on `POST /api/v1/jobs` again, naming `hmmscore`. Existing shapes don't change.
- **Engine:** no code change. The engine developer reviews decision 4 before `port-hmmscore`.
- **Parity with the reference:** this change scores nothing. Where the API answers differently from the reference, it's a proposed row, which may not ship without an approver:
  - **Row 11:** a server's residue limit below the reference's 50,000, approved with that value. If the product owner lowers the limit for hmmscore itself, row 11 records their limit instead.
  - **Row 12:** the sequences the API refuses with a `422` where the reference answered "no hit": an empty sequence, a character `hmmscan` refused, and `-`, `.`, `_`, `~` and a `*` before the end, which 3.1b2 read as positions, splitting the hit, and 3.4 doesn't. With them, what the website's posting changed before the CGI saw it, and a header after a blank line, which the website's form left in (design.md, decision 3).

## Open Questions

For the team and the product owner:

- **Does hmmscore keep the website's 50,000 residues?** `titin-50000` needed 21 GiB at `--cpu 0` (the survey). The engine developer has asked the product owner. The setting stays either way; its default and maximum follow the answer:
  - **If 50,000 stays,** the default is 50,000, the reference's, and a server sets it lower (#68). Row 11 covers only that lower value. This draft assumes this.
  - **If not,** the product owner's limit replaces 50,000 as the most the setting allows, and row 11 records it. The time limit's default then follows the new limit.
- **The server's values** for the four settings come from measuring there with the full library (#68).
- **The website's port to the JSON API:** it reads `panther_id`, `evalue` and `alignment` where it read `<id>`, `<eval>` and `<align>`, and can drop its own name lookup.

For `port-hmmscore`'s goldens to confirm:

- **Upper-casing, and refusing `.`, `_`, `~` and an inner `*`:** measured on a test model built from APOE; the goldens confirm both on PANTHER's own models.

Answered by the engine developer on #70, 2026-11-11:

- **Tied best hits (`HMMSCORE-1`):** the subfamily before its family, then the lowest PANTHER ID. The CGI picked one at random. A proposed row for `port-hmmscore`; the contract keeps one `hit`.
- **`evalue` and `score`:** strings, as printed (design.md, decision 2).
- **`name`:** always a string; "No name" if `names.tab` ever lacks the ID.
