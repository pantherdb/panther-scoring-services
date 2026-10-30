# Proposal

**Area:** api. Outside `api/` and this change, it touches only the generated `frontend/src/app/api/schema.d.ts` and the docs `docs/testing/api.md`.

## Why

`csnp` is the first scoring service to be ported, and the frontend's cSNP form needs the job contract to build against. The engine's `panther_engine.csnp.score()` is several engine changes away. Its interface was agreed with the engine developer on 2026-10-29: `score(CsnpInput) -> CsnpResult`, one protein per call. Settling the request, the result and the input validation now lets the frontend and the website build against the real contract and the real `422`s, while the engine is ported.

## What Changes

- **A `csnp` job request** joins the request union: `{"service": "csnp", "input": {"sequence": ..., "substitutions": [...], "species": ...}}`.
- **A `csnp` job** joins the job union. Its `result` is `{"family": string | null, "scores": [{"substitution", "age": integer | null, "message", "pdel": string | null}]}`. `message` is the legacy text, such as "probably damaging" or "Not scored: Invalid substitution", and `pdel` stays the legacy two-decimal string, because parity is byte for byte.
- **Input validation at submit time,** as the legacy website's form did it (`CsnpScoreForm.java`), with a `422` validation problem that never echoes a value:
  - `sequence`: a FASTA header line, whitespace and case are normalised away; empty, more than one sequence, more than 50,000 residues, or characters outside printable ASCII are rejected.
  - `substitutions`: a list of 1 to 1,000 tokens, each 1 to 32 printable characters without whitespace, upper-cased. A token that isn't in `<residue><position><residue>` form is **kept**, not rejected: what the port does with it is the engine's to decide (Open Questions).
  - `species`: required, 1 to 5 upper-case letters or digits, the shape of a PANTHER mnemonic such as `HUMAN`. Whether the engine knows the code is checked when the port lands.
- **Not available yet:** a valid `csnp` request gets `501 Not Implemented` as problem details, "cSNP scoring isn't available yet.", and no job is created. The `501` is documented in the OpenAPI schema. The change that wires the engine in removes it, adds the worker's case and the adapter, and handles the engine's `InputError` (`add-job-input-errors`, task group 2).
- **No scores are made up anywhere,** in the code or the tests: nothing returns an age, a message or a pDel until the engine does.
- **Contract files:** `api/openapi.json` and the frontend's generated `schema.d.ts` are regenerated. Nothing else in `frontend/` changes; the form is a separate change.
- **Docs:** `docs/testing/api.md` gains a cSNP subsection (a valid request and its `501`, an invalid one and its `422`); `api/README.md` gains a line for the `csnp` job.

## Capabilities

### New Capabilities

- `scoring-input`: the rules for a cSNP input's sequence, substitutions and species, shared by the UI and the API (CONTRIBUTING.md, Spec Layout). Other services add their input rules here when they're ported.

### Modified Capabilities

- `scoring-jobs`: new requirements for the `csnp` job request, the `csnp` job's result shape, and the `501` while scoring isn't available. Only ADDED requirements, so it doesn't conflict with `add-job-input-errors`, which modifies "A failing job reveals nothing internal" in the same capability. Either can archive first.

## Impact

- **Code:** a new `api/src/panther_api/jobs/csnp.py` (the input, result and score models); `jobs/work.py` (the request union, the result union, and a `run_job` case that refuses to run); `jobs/models.py` (`CsnpJob`); `routers/jobs.py` (the `501`, documented in the schema); tests.
- **API contract:** new schema components `CsnpJobRequest`, `CsnpInput`, `CsnpJob`, `CsnpResult` and `SubstitutionScore`, and a `501` response on `POST /api/v1/jobs`. The frontend developer reviews them. Existing shapes don't change.
- **Frontend:** only the regenerated `src/app/api/schema.d.ts`.
- **Engine:** no changes, and no dependency on `panther_engine.csnp`, which doesn't exist yet.
- **Dependencies:** none.
- **Parity with the legacy service:** this change scores nothing, so no output changes and no divergence row is needed. Its validation must not reject any input the legacy service would score; design.md lists each rule with its legacy evidence. Where the API's validation differs from the legacy (rejecting what the legacy silently mishandled, such as a second sequence or a missing species, or keeping tokens the legacy CGI silently dropped), it's listed under Open Questions and needs team verification.

## Open Questions

Each needs team verification. Most are for the engine developer, who has the legacy behaviour spec and the parity review that would settle them; they aren't on the API developer's machine.

- **Tokens the legacy CGI drops.** `snpScore.cgi` keeps only tokens matching `(^[A-Z]|a-z)([0-9]+)([A-Z|a-z]$)` and drops the rest without a row (`snpScore.cgi`, line 212). So `XYZ` or `G129` gets no row at all, while `G99999R` or a wrong reference residue gets "Not scored: Invalid substitution" (`PANTHER_PSEP1.01.pl`, lines 74 to 86). The API keeps every token. Should the port drop such tokens silently (parity), report them as "Not scored: Invalid substitution" (a divergence, needing a row), or should the API reject them at submit (`422`)?
- **Upper-casing the substitutions.** The website upper-cased the whole substitutions text before sending it (`CsnpScoreForm.java`, lines 28 to 34); the CGI alone accepts a lower-case alternate residue but not a lower-case reference one. The API upper-cases each token, as the website did. Does the legacy behaviour spec record anything that depends on case?
- **Which sequence characters BLAST+ scores.** The website stripped the header and whitespace, upper-cased, and checked the length, but checked no alphabet (`CsnpScoreForm.java`, lines 62 to 95). The API also rejects non-ASCII and control characters, which no protein sequence contains. What does `blastp` do with digits, `*`, `-` or `X` in the query, and should the engine raise `InputError` for a sequence BLAST rejects?
- **Is `species` required?** The CGI defaults an empty species to `HUMAN` (`snpScore.cgi`, lines 72 to 77), but the website always sent one: it rejected a missing or unknown organism (`CsnpScoreForm.java`, lines 101 to 107) and preselected the session's default organism. The API requires it. The frontend can preselect `HUMAN`.
- **Which species codes the engine accepts.** The website's cSNP list has 85 mnemonics (`OrganismConstants.java`, line 79). The CGI uses `species` as a `grep` pattern over the BLAST output (`parse_blastp.pl`, line 42), so a substring such as `HUM` would also have matched. Membership against the engine's exported list comes with the port.
- **Size limits** (tech-stack.md, Input size): 50,000 residues is the website's limit (`CsnpScoreForm.java`, lines 89 to 94). 1,000 substitutions per request and 32 characters per token are proposals: the legacy had no limit, and its sample has 35 substitutions. The raw `sequence` field is also capped at 1,000,000 characters, before normalising, to bound the work a single request can cause.
- **Does the engine expect the normalised sequence?** The API sends residues only: no header, no whitespace, upper case. The engine's `CsnpInput` then writes its own FASTA, as `snpScore.cgi` did with `>P0001` (line 188).
