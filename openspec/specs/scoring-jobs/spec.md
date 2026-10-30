# scoring-jobs Specification

## Purpose

The lifecycle of a scoring job in the API: submitting one with `POST /api/v1/jobs`, polling it with `GET /api/v1/jobs/{id}`, how jobs run in worker processes, how they fail and when they expire. Every scoring service runs through it.

## Requirements

### Requirement: Submit a job

The API SHALL accept `POST /api/v1/jobs` with a JSON body `{"service": ..., "input": {...}}`, where `service` names the job type and selects which input is valid. It MUST respond with status 202, a `Location` header giving the job's path, and the job, with status `queued` or `running`. The job MUST run without the client keeping the connection open.

#### Scenario: Submit a tools job

- **WHEN** a client sends `POST /api/v1/jobs` with `{"service": "tools", "input": {}}`
- **THEN** the API responds with status 202, a `Location` header of `/api/v1/jobs/{id}` for the returned job's `id`, and a job whose `service` is `tools` and whose `status` is `queued` or `running`

### Requirement: Reject an invalid job request

When the body names an unknown `service`, or its `input` isn't valid for the named service, the API SHALL respond with status 422 and the validation problem that `api-service` defines, and MUST NOT create a job.

#### Scenario: Unknown service

- **WHEN** a client sends `POST /api/v1/jobs` with `{"service": "no-such-service", "input": {}}`
- **THEN** the API responds with status 422 and a validation problem whose `errors` locate the problem in the body, and the body doesn't contain `no-such-service`

#### Scenario: Invalid input

- **WHEN** a client sends `POST /api/v1/jobs` with `{"service": "tools", "input": {"unexpected": 1}}`
- **THEN** the API responds with status 422 and a validation problem whose `errors` name the `input` field

#### Scenario: Missing input

- **WHEN** a client sends `POST /api/v1/jobs` with `{"service": "tools"}`
- **THEN** the API responds with status 422

### Requirement: Job shape

A job SHALL have an `id`, its `service`, a `status` of `queued`, `running`, `succeeded` or `failed`, `created_at`, `started_at` and `finished_at` (UTC timestamps, `null` until reached), a `result`, an `error` and `versions`. The `result` MUST be `null` unless the job succeeded, and the `error` MUST be `null` unless it failed. `versions` MUST be the API, engine and tool versions that the versions report gives.

#### Scenario: A finished job

- **WHEN** a client polls a `tools` job until its status is `succeeded`
- **THEN** the job has `created_at` ≤ `started_at` ≤ `finished_at`, a non-null `result`, a `null` `error`, and the same `versions` as `GET /api/v1/versions`

### Requirement: Unguessable job ids

Each job id SHALL be a random version 4 UUID, so that knowing one job's id gives no way to find another's. The API MUST NOT offer a way to list jobs.

#### Scenario: Two jobs

- **WHEN** a client submits two jobs
- **THEN** their ids are different, and each is a version 4 UUID

### Requirement: Poll a job

The API SHALL answer `GET /api/v1/jobs/{id}` with status 200 and the job's current state, for as long as the job exists. An id that never existed, isn't a valid id, or belongs to an expired job MUST get status 404 with a problem-details body.

#### Scenario: Poll until done

- **WHEN** a client submits a `tools` job and polls its `Location`
- **THEN** each response has status 200, and the status moves only forward from `queued` through `running` to `succeeded`

#### Scenario: Unknown id

- **WHEN** a client sends `GET /api/v1/jobs/{id}` with a random UUID that no job has, or with `not-a-uuid`
- **THEN** the API responds with status 404 and a problem-details body

### Requirement: Tools job

The `tools` job SHALL take an empty `input` and run the engine's external tool report in a worker process. Its `result` MUST list each tool the engine uses, in the engine's order, with its version, or `null` when the tool is missing or its version can't be read. The result MUST NOT contain file paths.

#### Scenario: Tools in the image

- **WHEN** a client submits a `tools` job to the API image and polls it until it finishes
- **THEN** the job has status `succeeded` and its `result` lists `blastp` 2.17.0, `hmmscan` 3.4, `hmmsearch` 3.4 and `epa-ng` 0.3.8, with no file paths

### Requirement: Work runs in worker processes

The API SHALL run every job's work in a pool of worker processes, never on the process that serves requests, so that a job can't delay another request. The number of workers MUST be configurable. When every worker is busy, a new job MUST wait with status `queued` and run when a worker frees up.

#### Scenario: More jobs than workers

- **WHEN** the API has one worker, a job is running, and a client submits a second job
- **THEN** the second job's status is `queued` while the first runs, and both reach `succeeded`

#### Scenario: Requests while a job runs

- **WHEN** a job is running
- **THEN** `GET /api/v1/health` still responds with status 200

### Requirement: A failing job reveals nothing internal

When a job's work raises an error, the job SHALL end with status `failed` and an `error` in problem-details form, with a generic `detail`. The job MUST NOT contain the error's message, a traceback, file paths or configuration values. Other jobs MUST be unaffected.

#### Scenario: The work raises

- **WHEN** a job's work raises an error whose message contains a file path
- **THEN** the job ends with status `failed`, a `null` `result` and a problem-details `error` with status 500, and the job contains neither the message nor the path

### Requirement: Recover from a dead worker

When a worker process dies while running a job, that job SHALL end with status `failed` and a problem-details `error`. The API MUST replace the worker pool, so that jobs submitted afterwards run normally. Jobs that were running in the same pool at that moment MAY fail too; jobs still `queued` MUST NOT.

#### Scenario: A worker dies

- **WHEN** a job's worker process exits while running it, and a client then submits another job
- **THEN** the first job ends with status `failed`, and the second reaches `succeeded`

### Requirement: Jobs expire

A finished job SHALL be kept for a configurable time, 24 hours by default, measured from its `finished_at`. After that, polling it MUST get status 404, and the API MUST release the memory it held. A job that hasn't finished MUST NOT expire. Jobs MUST NOT survive a restart of the API.

#### Scenario: Before expiry

- **WHEN** a client polls a finished job just before its expiry time
- **THEN** the API responds with status 200 and the job

#### Scenario: After expiry

- **WHEN** a client polls a finished job after its expiry time
- **THEN** the API responds with status 404 and a problem-details body

### Requirement: Configuration from the environment

The API SHALL read the number of worker processes and the job expiry time from environment variables when it starts, and use defaults when they are unset. An invalid value MUST stop the API from starting instead of being ignored.

#### Scenario: Defaults

- **WHEN** the API starts with no job settings in the environment
- **THEN** it runs jobs with 2 worker processes and keeps finished jobs for 24 hours

#### Scenario: Invalid setting

- **WHEN** the API starts with the worker count set to 0
- **THEN** the API fails to start

### Requirement: cSNP job request

The API SHALL accept a `csnp` job request, `{"service": "csnp", "input": {"sequence": ..., "substitutions": [...], "species": ...}}`, whose input follows `scoring-input`'s cSNP rules. An input that breaks one of them, or has a field it doesn't take, MUST get status 422 and the validation problem that `api-service` defines, with the failing field in `loc`, and MUST NOT create a job.

#### Scenario: Invalid species

- **WHEN** a client sends `POST /api/v1/jobs` with a `csnp` request whose `species` is `xyzzy;id`
- **THEN** the API responds with status 422, one error whose `loc` is `["body", "csnp", "input", "species"]`, no job is created, and the body doesn't contain `xyzzy`

#### Scenario: Every invalid field is listed

- **WHEN** a client sends `POST /api/v1/jobs` with a `csnp` request whose `sequence` is empty, whose `substitutions` is `[]` and which has no `species`
- **THEN** the API responds with status 422 and one error for each of `sequence`, `substitutions` and `species`

#### Scenario: A field the input doesn't take

- **WHEN** a client sends a `csnp` request whose `input` also has `"organism": "HUMAN"`
- **THEN** the API responds with status 422 and an error whose `loc` names `organism`

### Requirement: cSNP scoring not available yet

Until the engine's cSNP scoring is wired in, the API SHALL answer a valid `csnp` job request with status 501 and a problem-details body whose `detail` is "cSNP scoring isn't available yet.", and MUST NOT create a job. Validation comes first: an invalid `csnp` request gets the 422. The schema MUST document the 501 on `POST /api/v1/jobs`. A response MUST NOT contain a score.

#### Scenario: A valid cSNP request

- **WHEN** a client sends `POST /api/v1/jobs` with `{"service": "csnp", "input": {"sequence": "MKVLWAALLV", "substitutions": ["L4P"], "species": "HUMAN"}}`
- **THEN** the API responds with status 501, content type `application/problem+json`, `detail` "cSNP scoring isn't available yet.", and no job is created

#### Scenario: Documented in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** `POST /api/v1/jobs` lists a 501 response whose body is the problem-details schema

#### Scenario: Tools jobs still run

- **WHEN** a client has had a 501 for a `csnp` request and then submits a `tools` job
- **THEN** the `tools` job reaches `succeeded`

### Requirement: cSNP job shape

A `csnp` job SHALL have the shape every job has, with `service` `csnp` and a `result` that is `null` or `{"family", "scores"}`. `family` MUST be a string or `null`. Each item of `scores` MUST have `substitution` (a string), `age` (an integer number of millions of years, or `null`), `message` (a string) and `pdel` (a string, or `null`). Every field MUST be present, even when `null`.

#### Scenario: The result in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** the job union has a `csnp` member whose `result` is the cSNP result or `null`, `family` is a required string or `null`, and each score requires `substitution` and `message` as strings, `age` as an integer or `null`, and `pdel` as a string or `null`
