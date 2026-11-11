# Spec Delta

## ADDED Requirements

### Requirement: refmap job maps with the engine

A valid `refmap` job request SHALL get status 202 and a job, whose work maps the input's IDs with the engine's refmap mapping, for the input's organism. The job MUST succeed with the organism and one mapping per submitted ID, as the engine gives them, in the order submitted, repeated IDs included. An ID with no PANTHER ID is a mapping with a `null` `panther_id`, not a failure.

#### Scenario: The form's example

- **WHEN** a client submits a `refmap` job for `ENDPU` with the IDs `U1G4Q5`, `U1GCA1`, `U1HRR6`, `U1GLV9`, `U1GJ40` and `U1HQ27`, where the refmap data is available, and polls it until it finishes
- **THEN** the job has status `succeeded`, `organism` `ENDPU`, and the mappings `PTHR11360:SF130`, `PTHR21058:SF0`, `PTHR42765:SF2`, `PTHR28011`, `PTHR13401` and `null`, in that order, as `map_panther.pl` gives them

#### Scenario: Repeated and unknown IDs

- **WHEN** a client submits a `refmap` job for `ENDPU` with the IDs `U1G4Q5`, `P04217` and `U1G4Q5`
- **THEN** the job succeeds with three mappings: `U1G4Q5` to `PTHR11360:SF130`, `P04217` to `null`, and `U1G4Q5` to `PTHR11360:SF130`

#### Scenario: The data isn't there

- **WHEN** the API runs without the refmap data and a client submits a valid `refmap` job
- **THEN** the job ends with status `failed` and an `error` with status 500 and the generic `detail`

#### Scenario: Other jobs still run

- **WHEN** a `refmap` job and a `csnp` job are submitted one after the other
- **THEN** each reaches its own final status, and neither's result holds the other's

### Requirement: Startup check of the refmap data

When it starts, the API SHALL check the refmap data folder with the engine's data check, as it checks the cSNP data. If the folder isn't set, or lacks a file the mapping needs, the API MUST log an error that says `refmap` jobs will fail and includes the engine's message, and MUST still start and serve requests. When the data is complete, it MUST log no such error. Each service's check MUST be independent: missing refmap data MUST NOT stop `csnp` jobs, nor the reverse.

#### Scenario: No refmap data

- **WHEN** the API starts with `PANTHER_DATA_DIR` naming a folder that holds the cSNP data but no refmap data
- **THEN** it logs an error saying `refmap` jobs will fail, logs none about the cSNP data, and `GET /api/v1/health` responds with status 200

#### Scenario: Complete refmap data

- **WHEN** the API starts and the engine's refmap data check passes
- **THEN** it logs no error about the refmap data

## MODIFIED Requirements

### Requirement: Job shape

A job SHALL have an `id`, its `service`, a `status` of `queued`, `running`, `succeeded` or `failed`, `created_at`, `started_at` and `finished_at` (UTC timestamps, `null` until reached), a `result`, an `error` and `versions`. The `result` MUST be `null` unless the job succeeded, and the `error` MUST be `null` unless it failed. `versions` MUST be the API, engine and tool versions that the versions report gives, and, of its `data`, only the entry for the job's own service, so a result can be traced to the release that made it. A `tools` job reads no data, so its `data` MUST be empty.

#### Scenario: A finished job

- **WHEN** a client polls a `tools` job until its status is `succeeded`
- **THEN** the job has `created_at` ≤ `started_at` ≤ `finished_at`, a non-null `result`, a `null` `error`, and the same `versions` as `GET /api/v1/versions`, except that its `data` is empty

#### Scenario: A job's own data version

- **WHEN** a client polls a `refmap` job and a `csnp` job
- **THEN** the `refmap` job's `versions.data` is `[{"service": "refmap", "panther": "19"}]`, and the `csnp` job's is `[{"service": "csnp", "panther": "9"}]`

### Requirement: Jobs expire

A finished job SHALL be kept for a configurable time, 24 hours by default, measured from its `finished_at`. After that, polling it MUST get status 404, and the API MUST release the memory it held. The finished jobs' results MUST also fit a configurable memory budget, 256 MiB by default, counting each result by the size of its JSON: when a newly finished job's result would exceed it, the API MUST expire the finished jobs that hold the largest results first, the oldest first among equal sizes, until it fits, even before their time, so that a burst of large jobs doesn't expire everyone's smaller results. A job without a result, such as a failed job, frees nothing, so it MUST be kept until its time. A job that hasn't finished MUST NOT expire. Jobs MUST NOT survive a restart of the API.

#### Scenario: Before expiry

- **WHEN** a client polls a finished job just before its expiry time, and the results budget hasn't been exceeded
- **THEN** the API responds with status 200 and the job

#### Scenario: After expiry

- **WHEN** a client polls a finished job after its expiry time
- **THEN** the API responds with status 404 and a problem-details body

#### Scenario: Over the results budget

- **WHEN** the budget is 10 MiB, two finished jobs with results of 4 MiB each are kept, and a third with a 4 MiB result finishes
- **THEN** polling the oldest of the three gets status 404, and the two newest are kept

#### Scenario: The largest result expires first

- **WHEN** the budget is 10 MiB, finished jobs with results of 1 MiB, 5 MiB and 3 MiB are kept, in that order, and a fourth with a 2 MiB result finishes
- **THEN** polling the job with the 5 MiB result gets status 404, and the other three are kept

#### Scenario: A burst of large results

- **WHEN** the budget is 10 MiB, a job with a 1 MiB result has finished, and then ten jobs with results of 4 MiB each finish
- **THEN** the job with the 1 MiB result is still kept, and the two newest large jobs are kept

#### Scenario: A result larger than the budget

- **WHEN** a job finishes whose result alone is larger than the budget
- **THEN** every older finished job with a result expires, failed jobs are kept, and the new job is kept until its time, so its user can still read it

### Requirement: Configuration from the environment

The API SHALL read the number of worker processes, the job expiry time, the results budget, the cap on waiting jobs and the request body limit from environment variables when it starts, and use defaults when they are unset. An invalid value MUST stop the API from starting instead of being ignored.

#### Scenario: Defaults

- **WHEN** the API starts with no job settings in the environment
- **THEN** it runs jobs with 2 worker processes, keeps finished jobs for 24 hours within a results budget of 256 MiB, lets 50 jobs wait for a worker, and accepts request bodies of up to 16 MiB

#### Scenario: Invalid setting

- **WHEN** the API starts with the worker count set to 0, the cap on waiting jobs set to -1, the body limit set to 0, or the results budget set to 0
- **THEN** the API fails to start

### Requirement: refmap job shape

A `refmap` job SHALL have the shape every job has, with `service` `refmap` and a `result` that is `null` or `{"organism", "mappings"}`. `organism` MUST be the organism code the IDs were mapped against. Each item of `mappings` MUST have `id` (a string) and `panther_id` (a string, or `null` for an identifier with no PANTHER ID). Every field MUST be present, even when `null`.

#### Scenario: The refmap result in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** the job union has a `refmap` member whose `result` is the refmap result or `null`, `organism` is a required string, `mappings` is a required list, and each mapping requires `id` as a string and `panther_id` as a string or `null`

#### Scenario: A large result

- **WHEN** a `refmap` job of 100,000 IDs has succeeded and a client polls it
- **THEN** the response has the same JSON shape as for a small job, with 100,000 mappings in the order submitted

## REMOVED Requirements

### Requirement: refmap not available yet

**Reason**: The engine maps IDs since `port-refmap` (#63), so a valid `refmap` request starts a job instead of getting a `501`.

**Migration**: A client gets `202` and a job, as for `csnp` (refmap job maps with the engine). The `501` is no longer in the schema for `POST /api/v1/jobs`.
