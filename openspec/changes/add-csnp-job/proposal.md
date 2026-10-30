# Proposal

**Area:** api. Outside `api/` and this change, it touches only the generated `frontend/src/app/api/schema.d.ts` and the docs `docs/testing/api.md`.

## Why

`csnp` is the first scoring service to be ported, and the frontend's cSNP form needs the job contract to build against. The engine's `panther_engine.csnp.score()` is several engine changes away. Its interface was agreed with the engine developer on 2026-10-29: `score(CsnpInput) -> CsnpResult`, one protein per call. Settling the request, the result and the input validation now lets the frontend and the website build against the real contract and the real `422`s, while the engine is ported.

## What Changes

- **A `csnp` job request** joins the request union: `{"service": "csnp", "input": {"sequence": ..., "substitutions": [...], "species": ...}}`.
- **A `csnp` job** joins the job union. Its `result` is `{"family": string | null, "scores": [{"substitution", "age": integer | null, "message", "pdel": string | null}]}`. `message` is the legacy text, such as "probably damaging" or "Not scored: Invalid substitution", and `pdel` stays the legacy two-decimal string, because parity is byte for byte.
- **Input validation at submit time,** as the legacy website's form did it (`CsnpScoreForm.java`), with a `422` validation problem that never echoes a value:
  - `sequence`: a FASTA header line, whitespace and case are normalised away; empty, more than one sequence, more than 50,000 residues, or characters outside printable ASCII are rejected.
  - `substitutions`: a list of 1 to 1,000 tokens, each 1 to 32 printable characters, upper-cased, and in the legacy CGI's form `[A-Z][0-9]+[A-Z]`. A token not in that form is rejected; the legacy dropped it without a row, so no score is lost. One in the form that can't be mapped is scored as "Not scored: Invalid substitution" in the result.
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

Answered by the engine developer on #19 (2026-10-30), from the legacy behaviour spec, the parity review, the PANTHER9 BLAST database and `blastp` 2.17.0 from the engine image:

- **Tokens the legacy CGI drops** are rejected with a `422`, by the CGI's own rule after upper-casing, `[A-Z][0-9]+[A-Z]`. No score is lost: a dropped token was never scored. Parity doesn't decide it, because through the website the CGI scored nothing (`CGI-2`) or dropped tokens with `2` or `B` (`CGI-3`), and the goldens start after tokenizing. No divergence row is needed. `|` as the mutant residue and `*` (`A10*`) aren't accepted; `*` is to revisit once cSNP is live.
- **Case:** once upper-cased, nothing depends on it. `blastp` reads lower case.
- **Sequence characters:** keep the printable-ASCII rule and add no alphabet check. `blastp` reads or ignores every printable character, and GenBank-style pastes rely on it ignoring digits. The engine will raise `InputError` when `blastp` exits with status 1 (a query it can't read), with a proposed divergence row, since the legacy returned rows there.
- **`species` is required:** every website request had one.
- **The species list:** the PANTHER9 BLAST database has the same 85 codes as the website's list, all matching `[A-Z0-9]{1,5}`. The engine will export them and the API will check exact membership, with the port.
- **Size limits:** fine from the engine side. None changes a score.
- **`score()` expects the normalised sequence:** no header, no whitespace, upper case, with digits and other printable characters left for BLAST to ignore. Input that breaks the API's rules can only reach it through a bug, so it raises `ValueError` (a `500`), not `InputError`.
