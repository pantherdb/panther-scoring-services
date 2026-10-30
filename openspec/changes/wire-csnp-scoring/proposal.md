# Proposal

**Area:** cross-cutting. The work is in `api/` and `frontend/`, plus the root `compose.yaml` and `.github/workflows/ci.yml`, which all three developers own. In `engine/`, only the two-line `DATA_VERSION` export, which the engine developer asked for on #26. The contract changes too: the OpenAPI schema (frontend and API developers) and how the API reads the engine (API and engine developers).

## Why

The engine scores cSNP now (`port-csnp`, #24), but the API still answers a valid `csnp` request with `501`, so the form can't show a real score. This change connects the two, so cSNP can go live. It also lands `add-job-input-errors` group 2, which waited for the engine's `InputError` and this change.

## What Changes

- **A `csnp` job scores with the engine.** The `501` and its text go, from the router, the schema and the specs. A valid request gets `202` and a job; its worker calls `panther_engine.csnp.score()` through a small adapter, between the API's models and the engine's frozen dataclasses. The job succeeds with the engine's family and scores.
- **Input errors in failed jobs** (`add-job-input-errors` groups 2 and 3). When the work raises the engine's `InputError`, the job fails with a `422` problem whose `detail` is the engine's message. For `csnp`, that's a sequence `blastp` can't read (divergence row 8). Every other error stays the generic `500`, with the message only in the log.
- **The species must be one the engine scores.** After the shape check, the API's request model checks the species against `panther_engine.csnp.SPECIES_CODES`, the 85 species of the PANTHER9 BLAST database. A species of the right shape that isn't one of them, such as `ZZZZZ`, gets the `422` validation problem on `species`, without the value, and no job.
- **The versions name each service's data.** `Versions` gains `data`, a list of `{service, panther}`: `[{"service": "csnp", "panther": "9"}]`. `GET /api/v1/versions` and every job carry it, so a cSNP score names the frozen PANTHER 9 data behind it. The API reads it from the engine at startup. The UI shows it with the other versions, as "csnp data: PANTHER 9", never written in the frontend.
- **The API image reads the data folder.** The compose `api` service mounts `.data/` read-only at `/data` with `PANTHER_DATA_DIR=/data`, as the `engine` service does. No new API setting: the engine's `PANTHER_DATA_DIR` reaches the `spawn` workers through the environment.
- **CI runs a real `csnp` job.** The `api-image` job fetches the cSNP data sample, from the engine jobs' cache, starts the image with it, and checks that a job for the release sample's P26439 succeeds with family `PTHR10366` and the spec §7.3 scores.
- **API tests:** the adapter with a fake `score()`; a `csnp` job's success path through a real worker; the species check; group 2's tests through a real worker; and real end-to-end jobs, marked `tools("blastp")` and `data("csnp")` as in the engine, that check the release sample's three proteins against the engine's goldens. They run where `blastp` and the sample are, such as the API image.
- **Frontend:** the types regenerated; the `501` branch (`'unavailable'` and its alert), its mock body and its tests removed; the data versions shown; the api-mode e2e test scores a protein the sample covers and checks its scores. Mock mode is unchanged, apart from the mocked versions naming the data.
- **Docs:** `docs/testing/api.md` (the data sample, a `csnp` job by hand, a failed job's `422` and `500`, the real tests), `api/README.md`, `docs/testing/frontend.md`, `docs/testing/README.md`, `frontend/README.md`, and `docs/manual-qa/02-csnp-form.md` (TC 2.4 now scores for real).

No new dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-jobs`: "cSNP scoring not available yet" is removed. A new requirement says a `csnp` job scores with the engine and succeeds with its result.
- `scoring-input`: "cSNP species is a species code" also requires one of the engine's species codes.
- `api-service`: "Versions report" adds each service's data version.
- `scoring-ui`: "cSNP scoring not yet available" becomes "cSNP job not started", with no `501`. "Versions on every page" and "cSNP results on the job page" show the data versions.
- `psep-engine`: a new requirement, "Data version": the engine exports cSNP's data release as `DATA_VERSION`, at the engine developer's request on #26.

## Impact

- **API:** `jobs/csnp.py` (the species check and the adapter), `jobs/work.py`, `jobs/runner.py`, `jobs/models.py`, `routers/jobs.py`, `versions.py`, `openapi.json`, `pyproject.toml` (the two pytest markers), and `tests/`.
- **Frontend:** `schema.d.ts`, `useSubmitCsnp.ts`, `SubmitAlert.tsx`, `VersionList.tsx`, the mocks, the unit tests and the e2e specs.
- **Root:** `compose.yaml` and `.github/workflows/ci.yml`.
- **The engine interface:** the API imports `SPECIES_CODES`, `CsnpInput`, `CsnpResult` and `score` from `panther_engine.csnp`, and `InputError` from `panther_engine.core.errors`, all public. It also imports `DATA_VERSION`, which `panther_engine.csnp` now exports (`psep-engine`, "Data version"), as the engine developer asked on #26.
- **Running the API:** `csnp` jobs need `blastp` and the cSNP data. In the image, `blastp` is there; the data is the developer's `.data/`, fetched once. Without it, every `csnp` job fails with the generic `500`. Api-mode e2e needs the sample too.
- **Parity with the reference:** this change computes no score; the engine's port does, and its goldens prove it. The API returns the engine's family and scores unchanged, and the end-to-end tests check them against spec §7.3. The one difference from the legacy service is divergence row 8, approved with `port-csnp`, which this change reports as a `422`. No new divergence.
- **Two active changes touch `scoring-jobs`:** this one and `add-job-input-errors`, on different requirements. Archive `add-job-input-errors` first, since this change completes it.

## Open Questions

For the engine developer:

- **The data version's name** *(answered on #26, 2026-10-30)*. The engine exports it as `panther_engine.csnp.DATA_VERSION`, added in this change at the engine developer's request: `scoring.VERSION` re-exported and listed in `__all__`. The API imports it from there. The value stays `"9"`.
- **The APOE example against the sample.** The form's example, human APOE, is the legacy website's. Its family, `PTHR18976`, isn't among the data sample's 15 families, so against the sample its job succeeds with family `PTHR18976` and every substitution "Not scored: No PANTHER family for input sequence". The docs and the tests use P26439 instead. Should the sample gain `PTHR18976`, so the example scores in development and CI? And is `PTHR18976` in the full PAML_RST library, so the example scores on staging? *(Answered on #26, 2026-10-30: yes to both.)* `PTHR18976`'s `.paml`, `.rst` and `.orig.tree` are in the full library, and it isn't one of the seven broken families, so the example scores on staging. The engine developer adds it to the sample as `csnp-sample-3`, in an engine change of their own, with parity cases through the Perl reference image. Once that lands, the api-mode e2e test can score the form's own example; this change doesn't wait for it, since P26439 already gives CI a real job.

For the frontend developer:

- **A species list in the form.** The form checks the species' shape; the API checks membership, and the form shows its `422` on the field. Should the schema publish the 85 codes, as an enum, so the form can offer a list? Not needed to go live. The engine developer will export the species' names as `SPECIES_NAMES`, in a change of its own (#25), so a list can show names; the selector is a follow-up to that.

Needs team verification:

- **Where an input error is logged.** The runner logs it at `INFO`, as `add-job-input-errors` decided. Uvicorn's default logging shows only its own loggers, so the line doesn't reach `docker logs`. Errors still do, through Python's last-resort handler. Configuring the API's logging is for the deployment runbook.
