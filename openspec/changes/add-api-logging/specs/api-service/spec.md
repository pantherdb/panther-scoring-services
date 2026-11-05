# Spec Delta

## ADDED Requirements

### Requirement: One log format

The API SHALL write its log to standard error, one line per record, each starting with a UTC timestamp to the millisecond, then the level, then the logger's name, then the message. Its request log and its own messages MUST share that format from the time the API has started.

#### Scenario: A message from the API

- **WHEN** the API logs a message after it has started
- **THEN** standard error gets one line such as `2026-11-04T17:02:13.415Z INFO panther_api.jobs.runner: Job … succeeded …`

#### Scenario: A request

- **WHEN** a client sends `GET /api/v1/versions` after the API has started
- **THEN** the request's line has the same timestamp, level and logger fields, with the method, the path and the status `200`

### Requirement: Log level from the environment

The API SHALL read its log level from `PANTHER_API_LOG_LEVEL` when it starts: `DEBUG`, `INFO`, `WARNING` or `ERROR`, in any case, and `INFO` when unset. Records below the level MUST NOT be written. An invalid value MUST stop the API from starting.

#### Scenario: Default level

- **WHEN** the API starts without `PANTHER_API_LOG_LEVEL`
- **THEN** it writes `INFO` records and above, and no `DEBUG` records

#### Scenario: A higher level

- **WHEN** the API starts with `PANTHER_API_LOG_LEVEL=warning`
- **THEN** it writes no `INFO` records, its request log included, and still writes `WARNING` and `ERROR` records

#### Scenario: Invalid level

- **WHEN** the API starts with `PANTHER_API_LOG_LEVEL=LOUD`
- **THEN** the API fails to start

### Requirement: Routine requests are left out of the request log

At `INFO` and above, the API SHALL leave out of its request log a `GET /api/v1/health`, a `GET /api/v1/jobs/{id}` answered with a 2xx status, and a `POST /api/v1/jobs` answered with `202`, whose job gets its own line. Every other request MUST be logged. At `DEBUG`, every request MUST be logged.

#### Scenario: A successful poll

- **WHEN** the log level is `INFO` and a client polls an existing job
- **THEN** no request line is written for the poll

#### Scenario: A poll for an unknown job

- **WHEN** the log level is `INFO` and a client polls a job id that doesn't exist
- **THEN** a request line is written with the status `404`

#### Scenario: A health check

- **WHEN** the log level is `INFO` and a client sends `GET /api/v1/health`
- **THEN** no request line is written

#### Scenario: An accepted submission

- **WHEN** the log level is `INFO` and a client submits a valid job
- **THEN** no request line is written for the `202`

#### Scenario: A refused submission

- **WHEN** the log level is `INFO` and a client submits a job request that fails validation
- **THEN** a request line is written with `POST /api/v1/jobs` and the status `422`

#### Scenario: Every request at DEBUG

- **WHEN** the log level is `DEBUG` and a client submits a job, polls it and sends a health check
- **THEN** a request line is written for each

### Requirement: No user data in the log

The API's log MUST NOT contain the data a user submits: a protein sequence, a substitution, an ID to map, or any other submitted value except a short code the API has validated, such as a species code. It MAY contain sizes, such as a sequence's length or how many IDs were submitted.

#### Scenario: A cSNP job

- **WHEN** a client submits a `csnp` job with a distinctive sequence and substitutions, and the job runs to the end
- **THEN** the log contains neither the sequence nor any of the substitutions

#### Scenario: A rejected request

- **WHEN** a client submits a request that fails validation and contains a distinctive value
- **THEN** the log does not contain that value
