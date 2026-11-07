# Spec Delta

## ADDED Requirements

### Requirement: A cap on waiting jobs

The API SHALL limit how many jobs wait for a worker to a configurable number. A job that would wait when that many already do MUST get status 503, a `Retry-After` header and a fixed problem-details body, and MUST NOT be created. A job waits only while every worker has another unfinished job.

#### Scenario: Past the cap

- **WHEN** the API runs with 1 worker and a cap of 2, one job is running and 2 are waiting, and a client submits a valid job
- **THEN** the API responds with status 503, a `Retry-After` header, and a problem-details body, without a `Location` header, and the number of stored jobs is still 3

#### Scenario: Free workers

- **WHEN** the API runs with 2 workers and a cap of 0, and a client submits three jobs back to back while the first two run
- **THEN** the first two get status 202, and the third gets status 503

#### Scenario: After the queue drains

- **WHEN** a submission has been refused for the cap, and the waiting jobs then finish
- **THEN** the next valid submission gets status 202, and its job runs

#### Scenario: Finished jobs free their place

- **WHEN** the API runs with 1 worker and a cap of 0, and a client submits a job that fails, waits for it to finish, and does that three times
- **THEN** every submission gets status 202

#### Scenario: An invalid request past the cap

- **WHEN** the cap is reached and a client submits an invalid job
- **THEN** the API responds with status 422, as it would below the cap

#### Scenario: In the schema

- **WHEN** a client reads the OpenAPI schema
- **THEN** `POST /api/v1/jobs` documents a 503 response with a problem-details body and a `Retry-After` header

### Requirement: Startup check of the cSNP data

When it starts, the API SHALL check the cSNP data folder with the engine's data check. If the folder isn't set, or lacks a part every search needs, the API MUST log an error that says `csnp` jobs will fail and includes the engine's message, and MUST still start and serve requests. When the data is complete, it MUST log no such error.

#### Scenario: No data

- **WHEN** the API starts with `PANTHER_DATA_DIR` naming an empty folder
- **THEN** it logs an error naming the folder, and `GET /api/v1/health` responds with status 200

#### Scenario: No data folder set

- **WHEN** the API starts with `PANTHER_DATA_DIR` unset
- **THEN** it logs an error naming `PANTHER_DATA_DIR`, and `GET /api/v1/health` responds with status 200

#### Scenario: Complete data

- **WHEN** the API starts and the engine's data check passes
- **THEN** it logs no error about the cSNP data

## MODIFIED Requirements

### Requirement: Configuration from the environment

The API SHALL read the number of worker processes, the job expiry time, the cap on waiting jobs and the request body limit from environment variables when it starts, and use defaults when they are unset. An invalid value MUST stop the API from starting instead of being ignored.

#### Scenario: Defaults

- **WHEN** the API starts with no job settings in the environment
- **THEN** it runs jobs with 2 worker processes, keeps finished jobs for 24 hours, lets 50 jobs wait for a worker, and accepts request bodies of up to 16 MiB

#### Scenario: Invalid setting

- **WHEN** the API starts with the worker count set to 0, the cap on waiting jobs set to -1, or the body limit set to 0
- **THEN** the API fails to start
