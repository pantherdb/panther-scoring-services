# Spec Delta

## ADDED Requirements

### Requirement: hmmscore job request

The API SHALL accept an `hmmscore` job request, `{"service": "hmmscore", "input": {"sequence": ...}}`, whose input follows `scoring-input`'s hmmscore rules. An input that breaks one of them, or has a field it doesn't take, MUST get status 422 and the validation problem that `api-service` defines, with the failing field in `loc`, and MUST NOT create a job.

#### Scenario: Two sequences in an hmmscore request

- **WHEN** a client sends `POST /api/v1/jobs` with an `hmmscore` request whose `sequence` is `">one\nMKVQWERTY\n>two\nMKV"`
- **THEN** the API responds with status 422, one error whose `loc` is `["body", "hmmscore", "input", "sequence"]`, no job is created, and the body doesn't contain `MKVQWERTY`

#### Scenario: A field the hmmscore input doesn't take

- **WHEN** a client sends an `hmmscore` request whose `input` also has `"opType": "hmm"`, as the website's form sent
- **THEN** the API responds with status 422 and an error whose `loc` names `opType`

### Requirement: hmmscore not available yet

Until the engine's hmmscore scoring is wired in, the API SHALL answer a valid `hmmscore` job request with status 501 and a problem-details body whose `detail` is "HMM scoring isn't available yet.", and MUST NOT create a job. Validation comes first: an invalid `hmmscore` request, the residue limit included, gets the 422. The schema MUST document the 501 on `POST /api/v1/jobs`. A response MUST NOT contain a hit.

#### Scenario: A valid hmmscore request

- **WHEN** a client sends `POST /api/v1/jobs` with `{"service": "hmmscore", "input": {"sequence": "MKVLWAALLVTFLAGCQAKV"}}`
- **THEN** the API responds with status 501, content type `application/problem+json`, `detail` "HMM scoring isn't available yet.", no `Location` header, and no job is created

#### Scenario: The hmmscore 501 in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** `POST /api/v1/jobs` lists a 501 response whose body is the problem-details schema and whose description names `hmmscore`

### Requirement: hmmscore job shape

An `hmmscore` job SHALL have the shape every job has, with `service` `hmmscore` and a `result` that is `null` or `{"hit"}`. `hit` MUST be `null` when no model passes the cutoff, or have `panther_id`, `name`, `evalue`, `score` and `alignment`, each a string. `hit` MUST be present, even when `null`.

#### Scenario: The hmmscore result in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** the job union has an `hmmscore` member whose `result` is the hmmscore result or `null`, `hit` is required and is the hit or `null`, and the hit requires `panther_id`, `name`, `evalue`, `score` and `alignment`, each a string

### Requirement: A cap on hmmscore jobs running at once

The API SHALL run at most a configured number of `hmmscore` jobs at once, 1 by default. An `hmmscore` job past that number MUST wait with status `queued`, without holding a worker, and run when a running `hmmscore` job finishes. Jobs of other services MUST NOT wait for it.

#### Scenario: Two hmmscore jobs with a cap of one

- **WHEN** the API runs with 2 workers and a cap of 1 running `hmmscore` job, and two `hmmscore` jobs start
- **THEN** the second is `queued` while the first runs, and runs once the first finishes

#### Scenario: Another service beside a waiting hmmscore job

- **WHEN** the API runs with 2 workers and a cap of 1 running `hmmscore` job, one `hmmscore` job is running and a second is waiting for the cap, and a client submits a `tools` job
- **THEN** the `tools` job runs on the free worker and reaches `succeeded` while the second `hmmscore` job still waits

#### Scenario: A failed hmmscore job frees its place

- **WHEN** a running `hmmscore` job fails, and another is waiting for the cap
- **THEN** the waiting job starts

## MODIFIED Requirements

### Requirement: Configuration from the environment

The API SHALL read the number of worker processes, the job expiry time, the results budget, the cap on waiting jobs, the request body limit, and hmmscore's residue limit, job time limit, cap on running jobs and `hmmscan` thread count from environment variables when it starts, and use defaults when they are unset. An invalid value MUST stop the API from starting instead of being ignored.

#### Scenario: Defaults

- **WHEN** the API starts with no job settings in the environment
- **THEN** it runs jobs with 2 worker processes, keeps finished jobs for 24 hours within a results budget of 256 MiB, lets 50 jobs wait for a worker, accepts request bodies of up to 16 MiB, takes hmmscore sequences of up to 50,000 residues, gives an hmmscore job 3,600 seconds, runs 1 hmmscore job at a time, and runs `hmmscan` with `--cpu 0`

#### Scenario: Invalid setting

- **WHEN** the API starts with the worker count set to 0, the cap on waiting jobs set to -1, the body limit set to 0, or the results budget set to 0
- **THEN** the API fails to start

#### Scenario: Invalid hmmscore setting

- **WHEN** the API starts with the hmmscore residue limit set to 0 or to 50,001, the hmmscore time limit set to 0, the cap on running hmmscore jobs set to 0, or the `hmmscan` thread count set to -1
- **THEN** the API fails to start

### Requirement: The size of a job's input

A job's lines SHALL give the size of its input: for `csnp`, the species code, the sequence's length in residues and the number of substitutions; for `refmap`, the organism code and the number of IDs; for `hmmscore`, the sequence's length in residues. They MUST NOT contain the submitted sequence, substitutions or IDs.

#### Scenario: A cSNP job's size

- **WHEN** a `csnp` job for `HUMAN` with a sequence of 347 residues and 3 substitutions finishes
- **THEN** its line has `HUMAN`, 347 residues and 3 substitutions, and neither the sequence nor any substitution

#### Scenario: An hmmscore job's size

- **WHEN** an `hmmscore` job with a sequence of 317 residues finishes
- **THEN** its line has 317 residues, and not the sequence
