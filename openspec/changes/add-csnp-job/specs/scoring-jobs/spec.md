# Spec Delta

## ADDED Requirements

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
