# Spec Delta

## ADDED Requirements

### Requirement: hmmscore job scores with the engine

A valid `hmmscore` job request SHALL get status 202 and a job, whose work scores the input's sequence, as `scoring-input` normalised it, with the engine's hmmscore scoring. The job MUST succeed with the engine's hit, unchanged, or with a `null` `hit` when the engine finds none. A sequence that matches no family is a success with no hit, not a failure.

#### Scenario: The form's example

- **WHEN** a client submits an `hmmscore` job for human APOE, the form's example, where `hmmscan`, `hmmsearch` and the hmmscore data sample are available, and polls it until it finishes
- **THEN** the job has status `succeeded` and a hit with `panther_id` `PTHR18976:SF2`, `name` "APOLIPOPROTEIN E", `score` `439.0`, `evalue` `2.2e-133`, and the alignment of the engine's golden for that case

#### Scenario: No hit

- **WHEN** a client submits an `hmmscore` job for the engine's golden case `no-hit`, where the tools and the data sample are available
- **THEN** the job has status `succeeded` and the result `{"hit": null}`

#### Scenario: Tied best hits

- **WHEN** a client submits an `hmmscore` job for the consensus of PTHR35774, the engine's golden case `tie-pthr35774`, whose family and subfamily models tie
- **THEN** the job succeeds with the hit `PTHR35774:SF1`, as divergence row 13 gives it

#### Scenario: The hmmscore data isn't there

- **WHEN** the API runs without the hmmscore data and a client submits a valid `hmmscore` job
- **THEN** the job ends with status `failed` and an `error` with status 500 and the generic `detail`

#### Scenario: A tool fails

- **WHEN** an `hmmscore` job's search fails because a tool exits with an error whose message names a file path
- **THEN** the job ends with status `failed` and an `error` with status 500 and the generic `detail`, and the job contains neither the message nor the path

#### Scenario: Other jobs still run beside hmmscore

- **WHEN** an `hmmscore` job and a `csnp` job are submitted one after the other
- **THEN** each reaches its own final status, and neither's result holds the other's

### Requirement: hmmscore job time limit and threads

Each `hmmscore` job's search SHALL run with the configured `hmmscan` thread count, and with its time limit as "hmmscore time limit by length" gives it. The time limit MUST count from when the search starts, not from when the job was submitted, so a job that waited for a worker or for the running cap has all of it. A search that runs past the limit MUST be stopped, and the job MUST fail with an input error, whose message tells the user to try a shorter sequence.

#### Scenario: Past the time limit

- **WHEN** an `hmmscore` job's search runs past the time limit
- **THEN** the job ends with status `failed`, a `null` `result`, and an `error` with status 422 whose `detail` is "The search took longer than this service allows. Try a shorter sequence."

#### Scenario: The settings reach the search

- **WHEN** the API starts with `PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS` set to 600, `PANTHER_API_HMMSCORE_MIN_TIME_LIMIT_SECONDS` set to 600 and `PANTHER_API_HMMSCORE_CPU` set to 2, and an `hmmscore` job runs
- **THEN** its search is given a time limit of 600 seconds and a thread count of 2

#### Scenario: The default settings reach the search

- **WHEN** the API starts with no hmmscore settings in the environment, and an `hmmscore` job runs with 10,000 residues
- **THEN** its search is given a time limit of 720 seconds and a thread count of 0

### Requirement: hmmscore time limit by length

An `hmmscore` job's time limit SHALL grow with its residues: the minimum time limit, plus the difference between the time limit and the minimum times the residues divided by the residue limit, rounded to the nearest second. It MUST never be more than the time limit. The API MUST refuse to start when the minimum is over the time limit.

#### Scenario: A short sequence gets a shorter limit

- **WHEN** the API starts with no hmmscore settings in the environment, and an `hmmscore` job runs with APOE's 317 residues
- **THEN** its search is given a time limit of 139 seconds

#### Scenario: A minimum above the time limit

- **WHEN** the API starts with `PANTHER_API_HMMSCORE_MIN_TIME_LIMIT_SECONDS` set to 800 and `PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS` left at 720
- **THEN** it refuses to start, naming both settings

### Requirement: Startup check of the hmmscore data

When it starts, the API SHALL check the hmmscore data folder with the engine's data check, as it checks the cSNP and refmap data. If the folder isn't set, or lacks a part every search needs, the API MUST log an error that says `hmmscore` jobs will fail, with the engine's message, and MUST still start. The checks MUST be independent: missing hmmscore data MUST NOT stop other services' jobs, nor the reverse.

#### Scenario: No hmmscore data

- **WHEN** the API starts with `PANTHER_DATA_DIR` naming a folder that holds the cSNP and refmap data but no hmmscore data
- **THEN** it logs an error saying `hmmscore` jobs will fail, logs none about the cSNP or refmap data, and `GET /api/v1/health` responds with status 200

#### Scenario: Complete hmmscore data

- **WHEN** the API starts and the engine's hmmscore data check passes, as it does for the data sample
- **THEN** it logs no error about the hmmscore data

## MODIFIED Requirements

### Requirement: Job shape

A job SHALL have an `id`, its `service`, a `status` of `queued`, `running`, `succeeded` or `failed`, `created_at`, `started_at` and `finished_at` (UTC timestamps, `null` until reached), a `result`, an `error` and `versions`. The `result` MUST be `null` unless the job succeeded, and the `error` MUST be `null` unless it failed. `versions` MUST be the API, engine and tool versions that the versions report gives, and, of its `data`, only the entry for the job's own service, so a result can be traced to the release that made it. A `tools` job reads no data, so its `data` MUST be empty.

#### Scenario: A finished job

- **WHEN** a client polls a `tools` job until its status is `succeeded`
- **THEN** the job has `created_at` ≤ `started_at` ≤ `finished_at`, a non-null `result`, a `null` `error`, and the same `versions` as `GET /api/v1/versions`, except that its `data` is empty

#### Scenario: A job's own data version

- **WHEN** a client polls a `refmap` job and a `csnp` job
- **THEN** the `refmap` job's `versions.data` is `[{"service": "refmap", "panther": "19"}]`, and the `csnp` job's is `[{"service": "csnp", "panther": "9"}]`

#### Scenario: An hmmscore job's data version

- **WHEN** a client polls an `hmmscore` job
- **THEN** its `versions.data` is `[{"service": "hmmscore", "panther": "19"}]`

## REMOVED Requirements

### Requirement: hmmscore not available yet

**Reason**: The engine scores since `port-hmmscore` (#81), so a valid `hmmscore` request starts a job instead of getting a `501`.

**Migration**: A client gets `202` and a job, as for `csnp` and `refmap` (hmmscore job scores with the engine). The `501` is no longer in the schema for `POST /api/v1/jobs`. Validation still comes first: an invalid request, the residue limit included, is a `422`.
