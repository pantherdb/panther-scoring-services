# Spec Delta

## Purpose

Behaviour every endpoint of the PANTHER scoring API shares, whichever service it belongs to: the versioned base path, the health check, the error format, and the published OpenAPI schema that is the contract with the frontend.

## ADDED Requirements

### Requirement: Versioned base path

The API SHALL serve every endpoint, including its schema and documentation pages, under the `/api/v1` path prefix. A path outside that prefix MUST get the same not-found response as any other unknown path.

#### Scenario: Endpoint under the prefix

- **WHEN** a client sends `GET /api/v1/health`
- **THEN** the API responds with status 200

#### Scenario: Path outside the prefix

- **WHEN** a client sends `GET /health`
- **THEN** the API responds with status 404 and a problem-details body

### Requirement: Health check

The API SHALL answer `GET /api/v1/health` with status 200 and the JSON body `{"status": "ok"}` whenever the process is able to serve requests. The health check MUST NOT depend on scoring data, external tools or the engine.

#### Scenario: Healthy process

- **WHEN** a client sends `GET /api/v1/health`
- **THEN** the API responds with status 200, content type `application/json` and the body `{"status": "ok"}`

### Requirement: Errors as problem details

Every response with a 4xx or 5xx status SHALL have an RFC 9457 problem-details body with content type `application/problem+json`. The body MUST contain `type`, `title`, `status` and `detail`, and `status` MUST equal the HTTP status code.

#### Scenario: Unknown path

- **WHEN** a client sends `GET /api/v1/does-not-exist`
- **THEN** the API responds with status 404, content type `application/problem+json`, and a body whose `status` is 404 and whose `type`, `title` and `detail` are strings

#### Scenario: Method not allowed

- **WHEN** a client sends `POST /api/v1/health`
- **THEN** the API responds with status 405, an `Allow` header listing `GET`, and a problem-details body whose `status` is 405

### Requirement: Validation errors list the failing fields

When a request fails input validation, the API SHALL respond with status 422 and a problem-details body with an `errors` array. Each item MUST give the field's location (`loc`), a message (`msg`) and an error type (`type`). The body MUST NOT echo the submitted values.

#### Scenario: Invalid input

- **WHEN** a client sends a request whose body fails validation on one field
- **THEN** the API responds with status 422 and a problem-details body whose `errors` array has one item, with that field's `loc`, a `msg` and a `type`

#### Scenario: Submitted values are not echoed

- **WHEN** a client sends a request that fails validation and contains a distinctive value
- **THEN** the response body does not contain that value

### Requirement: Unexpected errors reveal nothing internal

When handling a request fails unexpectedly, the API SHALL respond with status 500 and a problem-details body with a generic `detail`. The response MUST NOT contain the exception message, a traceback, file paths or configuration values.

#### Scenario: Unhandled exception

- **WHEN** an endpoint raises an exception it does not handle, with a message containing a file path
- **THEN** the API responds with status 500 and a problem-details body whose `status` is 500, and the body contains neither the exception message nor the path

### Requirement: Published OpenAPI schema

The API SHALL serve its OpenAPI schema at `/api/v1/openapi.json`. The schema MUST describe every endpoint, and MUST declare the problem-details schema as the body of their error responses.

#### Scenario: Schema describes the health check and errors

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** the schema lists `GET /api/v1/health` and defines a problem-details component schema

### Requirement: Interactive documentation

The API SHALL serve interactive documentation for its endpoints at `/api/v1/docs`, generated from the published schema.

#### Scenario: Open the docs page

- **WHEN** a client opens `/api/v1/docs`
- **THEN** the API responds with status 200 and an HTML page that loads `/api/v1/openapi.json`

### Requirement: Committed schema matches the served schema

The repository SHALL hold a copy of the OpenAPI schema at `api/openapi.json` that is identical to the schema the API serves. The API's checks MUST fail when the two differ, so a contract change can't merge without its schema diff.

#### Scenario: Endpoint changed without regenerating the schema

- **WHEN** an endpoint is added or changed and `api/openapi.json` is not regenerated
- **THEN** the API's test suite fails and names the out-of-date schema

#### Scenario: Schema regenerated

- **WHEN** `api/openapi.json` is regenerated after the change
- **THEN** the API's test suite passes
