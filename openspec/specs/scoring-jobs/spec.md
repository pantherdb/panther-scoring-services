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

When a job's work raises an error other than an input error, the job SHALL end with status `failed` and an `error` in problem-details form, with a generic `detail`. The job MUST NOT contain the error's message, a traceback, file paths or configuration values. Other jobs MUST be unaffected.

#### Scenario: The work raises

- **WHEN** a job's work raises an error whose message contains a file path
- **THEN** the job ends with status `failed`, a `null` `result` and a problem-details `error` with status 500, and the job contains neither the message nor the path

### Requirement: Recover from a dead worker

When a worker process dies while running a job, that job SHALL end with status `failed` and a problem-details `error`. The API MUST replace the worker pool, so that jobs submitted afterwards run normally. Jobs that were running in the same pool at that moment MAY fail too; jobs still `queued` MUST NOT.

#### Scenario: A worker dies

- **WHEN** a job's worker process exits while running it, and a client then submits another job
- **THEN** the first job ends with status `failed`, and the second reaches `succeeded`

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

The API SHALL read the number of worker processes, the job expiry time, the results budget, the cap on waiting jobs, the request body limit, and hmmscore's residue limit, job time limit, cap on running jobs and `hmmscan` thread count from environment variables when it starts, and use defaults when they are unset. An invalid value MUST stop the API from starting instead of being ignored.

#### Scenario: Defaults

- **WHEN** the API starts with no job settings in the environment
- **THEN** it runs jobs with 2 worker processes, keeps finished jobs for 24 hours within a results budget of 256 MiB, lets 50 jobs wait for a worker, accepts request bodies of up to 16 MiB, takes hmmscore sequences of up to 10,000 residues, gives an hmmscore job 720 seconds, runs 1 hmmscore job at a time, and runs `hmmscan` with `--cpu 0`

#### Scenario: Invalid setting

- **WHEN** the API starts with the worker count set to 0, the cap on waiting jobs set to -1, the body limit set to 0, or the results budget set to 0
- **THEN** the API fails to start

#### Scenario: Invalid hmmscore setting

- **WHEN** the API starts with the hmmscore residue limit set to 0 or to 10,001, the hmmscore time limit set to 0, the cap on running hmmscore jobs set to 0, or the `hmmscan` thread count set to -1
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

### Requirement: cSNP job shape

A `csnp` job SHALL have the shape every job has, with `service` `csnp` and a `result` that is `null` or `{"family", "scores"}`. `family` MUST be a string or `null`. Each item of `scores` MUST have `substitution` (a string), `age` (an integer number of millions of years, or `null`), `message` (a string) and `pdel` (a string, or `null`). Every field MUST be present, even when `null`.

#### Scenario: The result in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** the job union has a `csnp` member whose `result` is the cSNP result or `null`, `family` is a required string or `null`, and each score requires `substitution` and `message` as strings, `age` as an integer or `null`, and `pdel` as a string or `null`

### Requirement: Input errors reach the user

When a job's work reports that its input can't be processed, by raising the engine's input error, the job SHALL end with status `failed`, a `null` `result`, and a problem-details `error` with status 422 whose `detail` is the input error's message. The job MUST NOT contain a traceback. Other jobs MUST be unaffected.

#### Scenario: Unprocessable input

- **WHEN** a job's work raises an input error with the message "Unknown organism."
- **THEN** the job ends with status `failed`, a `null` `result`, and an `error` with status 422 and the `detail` "Unknown organism."

#### Scenario: Other jobs keep running

- **WHEN** one job's work raises an input error while another job runs
- **THEN** the other job still ends with status `succeeded`

### Requirement: cSNP job scores with the engine

A valid `csnp` job request SHALL get status 202 and a job, whose work scores the input with the engine's cSNP scoring, with the sequence, substitutions and species as `scoring-input` normalised them. The job MUST succeed with the engine's family and scores, unchanged and in the order submitted. A substitution the engine doesn't score is a row of the result, not a failure.

#### Scenario: A sample protein

- **WHEN** a client submits a `csnp` job for the release sample's protein P26439, with the substitutions `A10E`, `G15D` and `S213G` and the species `HUMAN`, and polls it until it finishes
- **THEN** the job has status `succeeded`, `family` `PTHR10366`, and the scores `A10E` 220 "possibly damaging" "0.50", `G15D` 4200 "probably damaging" "0.95" and `S213G` 91 "probably benign" "0.19", as spec §7.3 gives them

#### Scenario: Every sample protein matches the goldens

- **WHEN** a client submits a `csnp` job for each protein of the release sample, with its substitutions from `sample.input`, where `blastp` and the cSNP data sample are available
- **THEN** each job succeeds with the family and the scores of its rows in spec §7.3

#### Scenario: A substitution that isn't scored

- **WHEN** a `csnp` job's substitutions include `M1V` for P26439
- **THEN** the job succeeds, and that score has the message "Not scored: Invalid substitution", a `null` `age` and a `null` `pdel`

#### Scenario: No family

- **WHEN** a client submits a `csnp` job for P26439 with the species `PLAF7`
- **THEN** the job succeeds with a `null` `family`, and each score has the message "Not scored: No PANTHER family for input sequence"

#### Scenario: A sequence the engine can't read

- **WHEN** a client submits a `csnp` job whose sequence is `1234567890`
- **THEN** the job ends with status `failed`, a `null` `result`, and an `error` with status 422 whose `detail` says the sequence can't be read as a protein sequence

#### Scenario: The data isn't there

- **WHEN** the API runs without the cSNP data and a client submits a valid `csnp` job
- **THEN** the job ends with status `failed` and an `error` with status 500 and the generic `detail`

### Requirement: refmap job request

The API SHALL accept a `refmap` job request, `{"service": "refmap", "input": {"organism": ..., "ids": [...]}}`, whose input follows `scoring-input`'s refmap rules. An input that breaks one of them, or has a field it doesn't take, MUST get status 422 and the validation problem that `api-service` defines, with the failing field in `loc`, and MUST NOT create a job.

#### Scenario: Invalid organism

- **WHEN** a client sends `POST /api/v1/jobs` with a `refmap` request whose `organism` is `xyzzy|`
- **THEN** the API responds with status 422, one error whose `loc` is `["body", "refmap", "input", "organism"]`, no job is created, and the body doesn't contain `xyzzy`

#### Scenario: Every invalid refmap field is listed

- **WHEN** a client sends `POST /api/v1/jobs` with a `refmap` request whose `ids` is `[]` and which has no `organism`
- **THEN** the API responds with status 422 and one error for each of `organism` and `ids`

#### Scenario: A field the refmap input doesn't take

- **WHEN** a client sends a `refmap` request whose `input` also has `"fileContents": "P04217"`
- **THEN** the API responds with status 422 and an error whose `loc` names `fileContents`

### Requirement: refmap job shape

A `refmap` job SHALL have the shape every job has, with `service` `refmap` and a `result` that is `null` or `{"organism", "mappings"}`. `organism` MUST be the organism code the IDs were mapped against. Each item of `mappings` MUST have `id` (a string) and `panther_id` (a string, or `null` for an identifier with no PANTHER ID). Every field MUST be present, even when `null`.

#### Scenario: The refmap result in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** the job union has a `refmap` member whose `result` is the refmap result or `null`, `organism` is a required string, `mappings` is a required list, and each mapping requires `id` as a string and `panther_id` as a string or `null`

#### Scenario: A large result

- **WHEN** a `refmap` job of 100,000 IDs has succeeded and a client polls it
- **THEN** the response has the same JSON shape as for a small job, with 100,000 mappings in the order submitted

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

### Requirement: One line for each finished job

When a job finishes, the API SHALL log one line with the job's id, its service, the size of its input, its status, the error's HTTP status if it failed, how long it waited for a worker and how long it ran, in seconds. The line MUST be `INFO` for a job that succeeded or failed on its input, and `ERROR` otherwise.

#### Scenario: A job that succeeds

- **WHEN** a `csnp` job for `HUMAN` with a sequence of 347 residues and 3 substitutions runs and succeeds
- **THEN** the log has one `INFO` line with the job's id, `csnp`, `HUMAN`, 347 residues, 3 substitutions, `succeeded`, its wait and its run time

#### Scenario: A job that fails on its input

- **WHEN** a job fails because the engine can't process its input
- **THEN** the log has one `INFO` line with the job's id, `failed`, `422`, its wait and its run time, and neither the engine's message nor a traceback

#### Scenario: A job that fails unexpectedly

- **WHEN** a job's work raises an unexpected exception
- **THEN** the log has one `ERROR` line with the job's id, `failed`, `500`, its wait and its run time

#### Scenario: A worker dies, in the log

- **WHEN** the worker process running a job dies
- **THEN** the log has one `ERROR` line with the job's id, `failed` and `500`, and says the worker stopped

### Requirement: The size of a job's input

A job's lines SHALL give the size of its input: for `csnp`, the species code, the sequence's length in residues and the number of substitutions; for `refmap`, the organism code and the number of IDs; for `hmmscore`, the sequence's length in residues. They MUST NOT contain the submitted sequence, substitutions or IDs.

#### Scenario: A cSNP job's size

- **WHEN** a `csnp` job for `HUMAN` with a sequence of 347 residues and 3 substitutions finishes
- **THEN** its line has `HUMAN`, 347 residues and 3 substitutions, and neither the sequence nor any substitution

#### Scenario: An hmmscore job's size

- **WHEN** an `hmmscore` job with a sequence of 317 residues finishes
- **THEN** its line has 317 residues, and not the sequence

### Requirement: A job's submission is logged at DEBUG

When the API accepts a job, it SHALL log one `DEBUG` line with the job's id, its service and the size of its input, once the job has started. A request that creates no job MUST NOT log a submission line, and a failure while writing the line MUST NOT stop the job from running.

#### Scenario: Submitted at DEBUG

- **WHEN** the log level is `DEBUG` and a client submits a valid job
- **THEN** the log has one `DEBUG` line with the job's id, its service and the size of its input, before the job's finish line

#### Scenario: Not at INFO

- **WHEN** the log level is `INFO` and a client submits a valid job that succeeds
- **THEN** the job's only line is its finish line

#### Scenario: A request that creates no job

- **WHEN** the log level is `DEBUG` and a client submits a request that gets a `422` or a `503`
- **THEN** no submission line is logged

### Requirement: An unexpected error's traceback is logged once in ten minutes

For a job that fails unexpectedly, the API SHALL log the exception's traceback with the finish line the first time that error is seen in ten minutes. An error is the same when its type and the place it was raised are, whatever its message. A repeat within ten minutes MUST log the finish line without the traceback, naming the job whose line has it and how many times the error was seen since.

#### Scenario: The same error twice

- **WHEN** two jobs fail one after the other with the same exception type, raised from the same place
- **THEN** the first job's line has the traceback, and the second job's line has none and names the first job

#### Scenario: A message that varies

- **WHEN** two jobs fail one after the other from the same place with the same exception type, and messages that differ, such as a time limit that scales with the input
- **THEN** the second job's line has no traceback and names the first job

#### Scenario: A different error

- **WHEN** a job fails with an error, and the next job fails with the same type and message raised from another place
- **THEN** both jobs' lines have their traceback

#### Scenario: After ten minutes

- **WHEN** a job fails with an error first seen more than ten minutes before
- **THEN** its line has the traceback again, and later repeats name this job

### Requirement: A refused submission is logged

When the API refuses a valid job request because the queue is full, it SHALL log a `WARNING` line with the service, the number of jobs running and waiting, and the cap, at most once a minute. A refusal in the minute after a line MUST be counted, and the next line MUST give the number of refusals since the previous line.

#### Scenario: Queue full

- **WHEN** `PANTHER_API_MAX_QUEUED_JOBS` jobs are waiting and a client submits a valid job
- **THEN** the client gets a `503`, and the log has one `WARNING` line naming the service and the cap

#### Scenario: A client retrying against a full queue

- **WHEN** the queue is full, and a client submits three valid jobs within a minute, then another a minute after the first
- **THEN** the first and the last get a `WARNING` line, and the last line says three jobs were refused since the first line

### Requirement: refmap job maps with the engine

A valid `refmap` job request SHALL get status 202 and a job, whose work maps the input's IDs with the engine's refmap mapping, for the input's organism. The job MUST succeed with the organism and one mapping per submitted ID, as the engine gives them, in the order submitted, repeated IDs included. An ID with no PANTHER ID is a mapping with a `null` `panther_id`, not a failure.

#### Scenario: The form's example

- **WHEN** a client submits a `refmap` job for `ENDPU` with the IDs `U1G4Q5`, `U1GCA1`, `U1HRR6`, `U1GLV9`, `U1GJ40` and `U1HQ27`, where the refmap data is available, and polls it until it finishes
- **THEN** the job has status `succeeded`, `organism` `ENDPU`, and the mappings `PTHR11360:SF130`, `PTHR21058:SF0`, `PTHR42765:SF2`, `PTHR28011`, `PTHR13401` and `null`, in that order, as `map_panther.pl` gives them

#### Scenario: Repeated and unknown IDs

- **WHEN** a client submits a `refmap` job for `ENDPU` with the IDs `U1G4Q5`, `P04217` and `U1G4Q5`
- **THEN** the job succeeds with three mappings: `U1G4Q5` to `PTHR11360:SF130`, `P04217` to `null`, and `U1G4Q5` to `PTHR11360:SF130`

#### Scenario: The refmap data isn't there

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

### Requirement: hmmscore job request

The API SHALL accept an `hmmscore` job request, `{"service": "hmmscore", "input": {"sequence": ...}}`, whose input follows `scoring-input`'s hmmscore rules. An input that breaks one of them, or has a field it doesn't take, MUST get status 422 and the validation problem that `api-service` defines, with the failing field in `loc`, and MUST NOT create a job.

#### Scenario: Two sequences in an hmmscore request

- **WHEN** a client sends `POST /api/v1/jobs` with an `hmmscore` request whose `sequence` is `">one\nMKVQWERTY\n>two\nMKV"`
- **THEN** the API responds with status 422, one error whose `loc` is `["body", "hmmscore", "input", "sequence"]`, no job is created, and the body doesn't contain `MKVQWERTY`

#### Scenario: A field the hmmscore input doesn't take

- **WHEN** a client sends an `hmmscore` request whose `input` also has `"opType": "hmm"`, as the website's form sent
- **THEN** the API responds with status 422 and an error whose `loc` names `opType`

### Requirement: hmmscore job shape

An `hmmscore` job SHALL have the shape every job has, with `service` `hmmscore` and a `result` that is `null` or `{"hit"}`. `hit` MUST be `null` when no model passes the cutoff, or have `panther_id`, `name`, `evalue`, `score` and `alignment`, each a string. `hit` MUST be present, even when `null`.

#### Scenario: The hmmscore result in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** the job union has an `hmmscore` member whose `result` is the hmmscore result or `null`, `hit` is required and is the hit or `null`, and the hit requires `panther_id`, `name`, `evalue`, `score` and `alignment`, each a string

### Requirement: A cap on hmmscore jobs running at once

The API SHALL run at most a configured number of `hmmscore` jobs at once, 1 by default. An `hmmscore` job past that number MUST wait with status `queued`, without holding a worker, and run when a running `hmmscore` job finishes. Jobs of other services MUST NOT wait for it. A job waiting for the cap MUST count as waiting toward the cap on waiting jobs, and a job that would run at once on a free worker MUST NOT be refused for that cap.

#### Scenario: Two hmmscore jobs with a cap of one

- **WHEN** the API runs with 2 workers and a cap of 1 running `hmmscore` job, and two `hmmscore` jobs start
- **THEN** the second is `queued` while the first runs, and runs once the first finishes

#### Scenario: Another service beside a waiting hmmscore job

- **WHEN** the API runs with 2 workers and a cap of 1 running `hmmscore` job, one `hmmscore` job is running and a second is waiting for the cap, and a client submits a `tools` job
- **THEN** the `tools` job runs on the free worker and reaches `succeeded` while the second `hmmscore` job still waits

#### Scenario: hmmscore jobs waiting for the cap fill the queue

- **WHEN** the API runs with 2 workers, a cap of 1 running `hmmscore` job and a cap of 3 waiting jobs, one `hmmscore` job is running and 3 are waiting for the cap, and a client submits another `hmmscore` job
- **THEN** it is refused with status 503, and no job is created

#### Scenario: Another service beside a full queue of hmmscore jobs

- **WHEN** the API runs with 2 workers, a cap of 1 running `hmmscore` job and a cap of 3 waiting jobs, one `hmmscore` job is running and 3 are waiting for the cap, and a client submits a `tools` job, then a second one while the first is unfinished
- **THEN** the first `tools` job runs on the free worker and reaches `succeeded`, and the second is refused with status 503, since it would wait

#### Scenario: No waiting with a cap of one

- **WHEN** the API runs with 2 workers, a cap of 1 running `hmmscore` job and a cap of 0 waiting jobs, one `hmmscore` job is running, and a client submits a second `hmmscore` job
- **THEN** it is refused with status 503, and a `tools` job submitted next still runs

#### Scenario: A failed hmmscore job frees its place

- **WHEN** a running `hmmscore` job fails, and another is waiting for the cap
- **THEN** the waiting job starts

### Requirement: hmmscore job scores with the engine

A valid `hmmscore` job request SHALL get status 202 and a job, whose work scores the input's sequence, as `scoring-input` normalised it, with the engine's hmmscore scoring. The job MUST succeed with the engine's hit, unchanged, or with a `null` `hit` when the engine finds none. A sequence that matches no family is a success with no hit, not a failure.

#### Scenario: The hmmscore form's example

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

Each `hmmscore` job's search SHALL run with the configured thread count, passed to both `hmmscan` and `hmmsearch`, and with its time limit as "hmmscore time limit by length" gives it. The time limit MUST count from when the search starts, not from when the job was submitted, so a job that waited for a worker or for the running cap has all of it.

#### Scenario: The settings reach the search

- **WHEN** the API starts with `PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS` set to 600, `PANTHER_API_HMMSCORE_MIN_TIME_LIMIT_SECONDS` set to 600 and `PANTHER_API_HMMSCORE_CPU` set to 2, and an `hmmscore` job runs
- **THEN** its search is given a time limit of 600 seconds and a thread count of 2, for both tools

#### Scenario: The default settings reach the search

- **WHEN** the API starts with no hmmscore settings in the environment, and an `hmmscore` job runs with 10,000 residues
- **THEN** its search is given a time limit of 720 seconds and a thread count of 0

### Requirement: hmmscore time limit by length

An `hmmscore` job's time limit SHALL grow with its residues: the minimum time limit, plus the difference between the time limit and the minimum, times the residues divided by 10,000, the most residues the API ever takes, rounded to the nearest second. It MUST NOT depend on the configured residue limit. The API MUST refuse to start when the minimum is over the time limit.

#### Scenario: A short sequence gets a shorter limit

- **WHEN** the API starts with no hmmscore settings in the environment, and an `hmmscore` job runs with APOE's 317 residues
- **THEN** its search is given a time limit of 139 seconds

#### Scenario: A lowered residue limit

- **WHEN** the API starts with `PANTHER_API_HMMSCORE_MAX_RESIDUES` set to 5,000 and no other hmmscore settings, and `hmmscore` jobs run with 317 and with 5,000 residues
- **THEN** their searches are given time limits of 139 and 420 seconds, as with the default residue limit

#### Scenario: A minimum above the time limit

- **WHEN** the API starts with `PANTHER_API_HMMSCORE_MIN_TIME_LIMIT_SECONDS` set to 800 and `PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS` left at 720
- **THEN** it refuses to start, naming both settings

### Requirement: An hmmscore job past its time limit

A search that runs past its time limit SHALL be stopped, and the job MUST fail with status 503 and a `detail` that says the server may be busy, and to try again later or with a shorter sequence. A short query reaches its limit only on a busy server, so this MUST NOT be reported as an input error. Other jobs MUST be unaffected.

#### Scenario: Past the time limit

- **WHEN** an `hmmscore` job's search runs past its time limit
- **THEN** the job ends with status `failed`, a `null` `result`, and an `error` with status 503 whose `detail` is "The search took longer than this service allows. The server may be busy: try again later, or with a shorter sequence."

#### Scenario: Other jobs beside a job past its limit

- **WHEN** one `hmmscore` job runs past its time limit while a `tools` job runs
- **THEN** the `tools` job still ends with status `succeeded`

### Requirement: A job past its time limit is logged as such

When an `hmmscore` job fails past its time limit, its finish line SHALL be a `WARNING` that says so, with the job's residues, its time limit and how long it ran, and no traceback. The line MUST NOT contain the sequence.

#### Scenario: The line

- **WHEN** an `hmmscore` job of 317 residues runs past its time limit of 139 seconds
- **THEN** the log has one `WARNING` finish line for it, naming 317 residues, the limit of 139 s and its run time, with no traceback and no residue of the sequence

### Requirement: Startup check of the hmmscore data

When it starts, the API SHALL check the hmmscore data folder with the engine's data check, as it checks the cSNP and refmap data. If the folder isn't set, or lacks a part every search needs, the API MUST log an error that says `hmmscore` jobs will fail, with the engine's message, and MUST still start. The checks MUST be independent: missing hmmscore data MUST NOT stop other services' jobs, nor the reverse.

#### Scenario: No hmmscore data

- **WHEN** the API starts with `PANTHER_DATA_DIR` naming a folder that holds the cSNP and refmap data but no hmmscore data
- **THEN** it logs an error saying `hmmscore` jobs will fail, logs none about the cSNP or refmap data, and `GET /api/v1/health` responds with status 200

#### Scenario: Complete hmmscore data

- **WHEN** the API starts and the engine's hmmscore data check passes, as it does for the data sample
- **THEN** it logs no error about the hmmscore data
