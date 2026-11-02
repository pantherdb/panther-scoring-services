# Spec Delta

## ADDED Requirements

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

### Requirement: refmap not available yet

Until the engine's refmap mapping is wired in, the API SHALL answer a valid `refmap` job request with status 501 and a problem-details body whose `detail` is "refmap ID mapping isn't available yet.", and MUST NOT create a job. Validation comes first: an invalid `refmap` request gets the 422. The schema MUST document the 501 on `POST /api/v1/jobs`. A response MUST NOT contain a mapping.

#### Scenario: A valid refmap request

- **WHEN** a client sends `POST /api/v1/jobs` with `{"service": "refmap", "input": {"organism": "HUMAN", "ids": ["P04217", "P01023"]}}`
- **THEN** the API responds with status 501, content type `application/problem+json`, `detail` "refmap ID mapping isn't available yet.", and no job is created

#### Scenario: The 501 is documented in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** `POST /api/v1/jobs` lists a 501 response whose body is the problem-details schema

#### Scenario: Other jobs still run after a refmap 501

- **WHEN** a client has had a 501 for a `refmap` request and then submits a `tools` job
- **THEN** the `tools` job reaches `succeeded`

### Requirement: refmap job shape

A `refmap` job SHALL have the shape every job has, with `service` `refmap` and a `result` that is `null` or `{"mappings"}`. Each item of `mappings` MUST have `id` (a string) and `panther_id` (a string, or `null` for an identifier with no PANTHER ID). Every field MUST be present, even when `null`.

#### Scenario: The refmap result in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** the job union has a `refmap` member whose `result` is the refmap result or `null`, `mappings` is a required list, and each mapping requires `id` as a string and `panther_id` as a string or `null`
