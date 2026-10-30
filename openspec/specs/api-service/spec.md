# api-service Specification

## Purpose

Behaviour every endpoint of the PANTHER scoring API shares, whichever service it belongs to: the versioned base path, the health check, the error format, and the published OpenAPI schema that is the contract with the frontend.

## Requirements

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

### Requirement: Versions report

The API SHALL answer `GET /api/v1/versions` with status 200 and a JSON body giving the API's version, the engine's version, and each external tool the engine uses (`blastp`, `hmmscan`, `hmmsearch`, `epa-ng`) with its version. A tool that is missing, or whose version can't be read, MUST be listed with a `null` version instead of being left out or failing the request. The body MUST NOT contain file paths.

#### Scenario: All tools present

- **WHEN** a client sends `GET /api/v1/versions` and every external tool is installed
- **THEN** the API responds with status 200 and a body with the API version, the engine version, and the four tools in the order `blastp`, `hmmscan`, `hmmsearch`, `epa-ng`, each with its version as a string

#### Scenario: A tool is missing

- **WHEN** a client sends `GET /api/v1/versions` and `epa-ng` is not installed
- **THEN** the API responds with status 200, lists `epa-ng` with a `null` version, and still lists the other three tools with their versions

#### Scenario: No file paths

- **WHEN** a client sends `GET /api/v1/versions`
- **THEN** the body contains no file system path, including the paths at which the tools were found

### Requirement: Versions read once at startup

The API SHALL read the engine and tool versions once, when it starts, and answer every versions request from what it read then. A versions request MUST NOT run any external tool.

#### Scenario: Repeated requests

- **WHEN** the API has started and a client sends `GET /api/v1/versions` several times
- **THEN** every response has the same body, and no external tool runs after startup

### Requirement: API image with the pinned tools

The repository SHALL build an image that serves the API on port 8000, with the engine and the pinned external tools installed, for `linux/amd64` and `linux/arm64`. In that image the versions report MUST show `blastp` 2.17.0, `hmmscan` and `hmmsearch` 3.4, and `epa-ng` 0.3.8.

#### Scenario: Versions in the image

- **WHEN** the API image is started and a client sends `GET /api/v1/versions` to port 8000
- **THEN** the API responds with status 200 and reports `blastp` 2.17.0, `hmmscan` 3.4, `hmmsearch` 3.4 and `epa-ng` 0.3.8

#### Scenario: Each architecture

- **WHEN** the API image is built for `linux/amd64` and for `linux/arm64`
- **THEN** both builds succeed, and each, run natively on a machine of that architecture, reports every tool with a version

### Requirement: API on a developer machine with one command

A developer SHALL be able to start the API image with one documented command from the repository root, on any machine with Docker. The API MUST then answer at `http://localhost:8000/api/v1`, where the frontend's development proxy sends `/api` requests.

#### Scenario: Start the API

- **WHEN** a developer runs the documented command from a fresh clone
- **THEN** `GET http://localhost:8000/api/v1/health` returns status 200, and `GET http://localhost:8000/api/v1/versions` reports every tool with a version
