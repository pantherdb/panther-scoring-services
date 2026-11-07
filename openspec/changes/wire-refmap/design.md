# Design

## Context

- **The contract is in place.** `add-refmap-job` (#30) defined the request, the result and the `501`; `add-refmap-form` (#35) built the form and the results view against it. Its design.md, decisions 6 and 7 and Risks, named this change's work: drop the `501` with the organism check, store large results compactly, and make a large bad list cheap to reject.
- **The engine maps IDs** since `port-refmap` (#63). `panther_engine.refmap` exports `map_ids(RefmapInput) -> RefmapResult` (`organism`, then `mappings` of `id` and `panther_id`), `check_data()`, and `ORGANISM_CODES`, `ORGANISM_NAMES` and `ORGANISM_GENES`, read from a committed `organisms.json` with no data folder. `map_ids` raises `ValueError` for input the API should have rejected, and `MissingDataError` for a missing file (divergence 9). Its data is 1,534 files, 523 MB, under `refmap/19/` in `PANTHER_DATA_DIR`, named by organism code.
- **The API runs jobs** in worker processes (`docs/design/tech-stack.md`, API recommendation 2), keeps them in memory for 24 hours (`JobStore`), and builds each poll's response by validating the stored result into the `Job` union (`routers/jobs.py`, `_job`), which FastAPI serialises again.
- **cSNP is the pattern:** `jobs/csnp.py` calls the engine in the worker, `routers/csnp.py` serves the species list, `main.py` checks the data at startup, and the form's `SpeciesField` is a searchable `Select` with a typed fallback.

## Goals / Non-Goals

**Goals:**

- A valid `refmap` request maps with the engine, end to end, in the API and the form.
- Only the engine's organisms reach it, checked in the API, and offered by name in the form.
- A 100,000-ID job doesn't cost 59 MB to keep, or a re-validation of 100,000 models on the event loop to poll.
- A 100,000-item bad list costs about what a valid one does (#41).

**Non-Goals:**

- Changing the input rules for `ids`, or the mapping itself: the engine's parity stands.
- A synchronous endpoint beside the job (`add-refmap-job`, decision 1).
- The website's port (#44), and what replaces `map_panther_cls`: the organism list carries the gene counts it needs, nothing more.

## Decisions

### 1. The job calls `map_ids` in the worker, as `csnp` calls `score`

`jobs/refmap.py` gains `run_refmap(RefmapInput) -> RefmapResult`, called from `run_job`'s refmap case in the worker. It passes `organism` and `tuple(ids)` to the engine unchanged, and lets its exceptions through: the runner already turns an `InputError` into a 422 and anything else, `MissingDataError` and the engine's `ValueError` included, into the generic 500. The engine raises no `InputError` for refmap: the API rejects everything it would refuse first, so reaching it with one is a bug, and a 500 is right.

- **`UNAVAILABLE` keeps its mechanism** with no rows: `hmmscore` and `treegrafter` may use it for their contracts. With no row, the router never answers 501 and the schema drops the 501, as `add-refmap-job` decision 6 planned.
- **The worker imports the engine's refmap module lazily** inside `run_refmap`, as `run_csnp` does, so the API process only pays for `organisms.json` where it validates.

### 2. `organism` is checked against `ORGANISM_CODES`

The `Organism` validator in `jobs/refmap.py` checks membership after the shape, with one message for both: "The organism must be the code of an organism refmap maps for, such as ENDPU. GET /api/v1/refmap/organisms lists them." It doesn't quote the value, as every message here doesn't. The schema keeps the shape's `pattern` and `maxLength`; it doesn't list 1,533 codes as an `enum`, which would bloat the schema and the generated types for no check the form can't do from the endpoint.

- **The import cost** is reading a 200 KB JSON file once, in the API process. `ORGANISM_CODES` needs no data folder, so validation works without the data, as cSNP's `SPECIES_CODES` does.

### 3. The organism list: `GET /api/v1/refmap/organisms`

A new `routers/refmap.py`, shaped like `routers/csnp.py`: `RefmapOrganism` (`code`, `name`, `genes`, `genes_with_panther_id`), built once from `ORGANISM_NAMES` and `ORGANISM_GENES` in the engine's order (by code), with `Cache-Control: public, max-age=3600`. About 110 KB of JSON, 20 KB compressed.

- **The gene counts** are what the website read from `stats` (`map_panther_stats`, `OrganismHelper.getMappingOrgs`) for its enrichment tests. The engine exports them for that (#63, second review). They cost nothing here, and save the website's port another source. Whether it uses them is an open question.
- **Alternative: names only,** as cSNP's list. Rejected: a second endpoint for the counts later would duplicate this one.

### 4. A finished refmap result is kept as JSON, built in the worker

The worker returns the result already serialised: `run_refmap` builds the `RefmapResult` model and returns its JSON bytes, wrapped in a small `SerializedResult` type that the store keeps as is. `get_job` builds the job's JSON around those bytes and returns it as a `Response`, without validating the result again. The route keeps `Job` as its documented response model, so the schema and the generated types don't change.

- **Memory:** about 5 MB of bytes for 100,000 mappings instead of about 59 MB of models (`add-refmap-job`, Risks). The finished job also drops its request's IDs, keeping only the request's log summary, which is all that's read once the job has finished; that's another 6 MB.
- **Polling:** each poll of a finished large job copies 5 MB instead of validating and serialising 100,000 models on the event loop.
- **In the worker,** not the API process: serialising 100,000 models takes about 0.1 s, which the event loop shouldn't pay, and bytes cross the process boundary cheaper than 100,000 pickled objects.
- **A results budget** bounds the total: the team server has 8 GB, shared with the BLAST workers and the site, so the finished jobs' results may take 256 MiB by default (`PANTHER_API_RESULTS_BUDGET_MIB`), counted by each result's JSON size, measured once when the job finishes. Over it, the oldest finished jobs expire first, before their 24 hours. That's about 50 jobs of 100,000 IDs, or tens of thousands of cSNP jobs. A result larger than the budget on its own is still kept, after expiring every older one, so its user can read it. The sweep runs when a job finishes, as expiry already runs in the store, so no background task is needed.
- **Only refmap's result** is kept this way. cSNP's and tools' results are small, so they keep the plain path; the store and the router handle both.
- **Alternatives:** parallel tuples (`organism`, a tuple of `panther_id`s aligned with the request's IDs) halve the memory but still cost a full serialisation per poll; a shorter expiry for large jobs bounds the total but not each job's size. Either can be added later.
- **The test:** a 100,000-ID result polled through the API validates against the `Job` union, and is equal to the engine's result field for field.

### 5. A bad list is rejected in one pass (#41)

Pydantic spends about 0.9 s building 100,000 error dicts before the 100-error cap can apply (`add-refmap-job`, decision 7). The `ids` items lose their per-item validator; one validator on the list checks every item with the compiled `PRINTABLE` pattern and length, counts the bad ones, and raises the first 100 at their indexes, with the total, so the problem handler's `detail` still says how many there were. The body is unchanged: the same `loc`s, `msg`s and `type`s, and the same `detail`.

- **The schema keeps each item's `pattern`, `minLength` and `maxLength`,** from `json_schema_extra`, so the contract and the generated types don't change.
- **How the total reaches the handler,** and how the validator raises errors at item `loc`s, is settled first in a short spike (tasks 2.1), against Pydantic's behaviour: raising a `ValidationError` built with `from_exception_data` from a list validator, or validating `ids` with a `TypeAdapter` and re-raising. The fallback is to leave the per-item path for small lists and take the fast path only when the list is long.
- **Acceptance:** 100,000 empty IDs answer their 422 in no more than twice the time of 100,000 valid IDs for an unknown organism, measured in the same test run, and the body matches today's byte for byte.

### 6. Startup: one check per service

`main.py`'s `check_csnp_data` becomes a loop over each service's engine check, `csnp` and `refmap`, each logging its own error ("refmap jobs will fail until the refmap data is in place: …"), so one missing service doesn't hide or stop the other. The check costs 1,534 `stat`s, in the threadpool, as today's does.

### 7. The form: a shared code selector, the ENDPU example

- **One field for both lists.** `SpeciesField`'s three states (loaded: a searchable `Select`; loading; failed: a typed box and a retry) become a shared `CodeListField` in `src/components/`, given its labels and texts, used by cSNP for species and by refmap for organisms. The cSNP tests keep it honest. `useRefmapOrganisms` mirrors `useCsnpSpecies`, over a new RTK Query endpoint `getRefmapOrganisms`.
- **1,533 options:** Mantine's `Select` renders every matching option, so the field passes `limit` (50) to render only the first matches while typing, and sorts the options by name, which is how users look for an organism. `comboboxProps={{ floatingStrategy: 'fixed' }}`, as `frontend/CLAUDE.md` requires.
- **The example** is six IDs from the data's own ENDPU test list (`test_geneList`, which #63 commits as a golden input): `U1G4Q5`, `U1GCA1` and `U1HRR6` map to subfamilies, `U1GLV9` and `U1GJ40` to families, and `U1HQ27` to no PANTHER ID. So the example shows every kind of answer, and its expected mappings come from `map_panther.pl`, not from us.
- **The 501 path goes:** `useSubmitRefmap`'s `unavailable` problem, its alert and the e2e spec that expected it. A 501 from an older API gets "couldn't be started", as any other error.
- **`services.ts`:** refmap's `comingSoon` becomes `false`, so its tab and card drop the mark.
- **The job page** reads `result.organism`, and shows "Mapped against Endocarpon pusillum (ENDPU)", using the cached organism list, or the code alone when it can't load.
- **The mocks** serve a short organism list of real entries (ENDPU, ARAVE, ECO57 and a few more, with their real names and counts) and map the example's IDs to the golden's values, so the mocked build shows real answers. Other IDs keep `refmapResult`'s mock behaviour.

### 8. Tests and data

- **Without the data** (CI's `api` job, any developer): the request rules, the organism check (`HUMAN` rejected, every listed code accepted), the endpoint, the schema, the 422 timing, and real jobs against a made-up data folder: a test writes `refmap/19/panther_classification/ENDPU` from the golden output in `engine/tests/golden/refmap/out/test_geneList.out` into a temporary `PANTHER_DATA_DIR`, so a job runs the real engine on real values without the 523 MB release. Read-only use of `engine/tests`, which this change doesn't modify.
- **With the data** (marked `data("refmap")`): the example job against the real release, and a 100,000-ID job's memory and poll time. The `refmap` entry joins the API's `DATA_MANIFESTS`. CI's `api-image` job mounts the refmap data, from the cache the engine jobs fill.
- **Frontend:** unit tests for the field's three states, the example, the organism on the job page, and the removed 501 path; e2e mocked specs for the selector and the example; the `@api` refmap spec submits the example and checks its six mappings.

## Risks / Trade-offs

- **[A busy day expires jobs early]** → With the budget full, a user's job may be gone before 24 hours: its page says the job expired, as it would at 24 hours. 256 MiB holds about 50 of the largest jobs; most are far smaller. The budget is a setting, so the server can raise it.
- **[The splice drifts from the model]** → `get_job` writes JSON around stored bytes, which could disagree with the `Job` schema. A test validates a polled large job against `JOB_ADAPTER`, and the bytes come from the same `RefmapResult` model.
- **[The fast list validator changes an error]** → Its errors must match today's `loc`, `msg` and `type`. The existing 422 tests for `ids` stay as they are and must pass unchanged.
- **[The data isn't on the server]** → `refmap` jobs fail with the generic 500, and the startup log says why. `docs/deployment/runbook-server.md` gains the fetch step, beside what `docs/design/hosting.md` says the server holds; doing it is the engine developer's.
- **[A user wanted `HUMAN`]** → It never had refmap data (#52). The form only offers what the engine maps for; a typed `HUMAN` gets the organism error, which points to the list.
- **[The shared field breaks cSNP]** → cSNP's form tests and e2e specs run unchanged against the shared component.
