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

When a request fails input validation, the API SHALL respond with status 422 and a problem-details body with an `errors` array. Each item MUST give the field's location (`loc`), a message (`msg`) and an error type (`type`). The body MUST NOT echo the submitted values. The `errors` array MUST list at most the first 100 field errors, in the order validation found them. When there are more than 100, the `detail` MUST say how many fields failed in all. A list of many invalid items MUST be answered in about the time a valid list of the same size takes, so that one request can't hold the API for longer than a valid one.

#### Scenario: Invalid input

- **WHEN** a client sends a request whose body fails validation on one field
- **THEN** the API responds with status 422 and a problem-details body whose `errors` array has one item, with that field's `loc`, a `msg` and a `type`

#### Scenario: Submitted values are not echoed

- **WHEN** a client sends a request that fails validation and contains a distinctive value
- **THEN** the response body does not contain that value

#### Scenario: At most 100 errors

- **WHEN** a client sends a refmap request whose `ids` are 100,000 empty strings
- **THEN** the API responds with status 422, the `errors` array has 100 items, the errors on `ids` items 0 to 99, each with its `loc`, and the `detail` says that 100,000 fields are invalid and the first 100 are listed

#### Scenario: Up to 100 errors are all listed

- **WHEN** a client sends a request with 100 or fewer invalid fields
- **THEN** the `errors` array lists every one, and the `detail` is "Request validation failed"

#### Scenario: Many invalid IDs answered as fast as valid ones

- **WHEN** a client sends a refmap request whose `ids` are 100,000 empty strings, and another whose `ids` are 100,000 valid IDs for an unknown organism
- **THEN** the first request's 422 takes no more than three times as long as the second's plus a tenth of a second, measured in the same process, where checking each item on its own took about seven times as long

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

The API SHALL answer `GET /api/v1/versions` with status 200 and a JSON body giving the API's version, the engine's version, and each external tool the engine uses (`blastp`, `hmmscan`, `hmmsearch`, `epa-ng`) with its version. A tool that is missing, or whose version can't be read, MUST be listed with a `null` version instead of being left out or failing the request. The body MUST also list, for each ported scoring service, the PANTHER release its data comes from, as the engine reports it, whether or not the data is installed. The body MUST NOT contain file paths.

#### Scenario: All tools present

- **WHEN** a client sends `GET /api/v1/versions` and every external tool is installed
- **THEN** the API responds with status 200 and a body with the API version, the engine version, and the four tools in the order `blastp`, `hmmscan`, `hmmsearch`, `epa-ng`, each with its version as a string

#### Scenario: A tool is missing

- **WHEN** a client sends `GET /api/v1/versions` and `epa-ng` is not installed
- **THEN** the API responds with status 200, lists `epa-ng` with a `null` version, and still lists the other three tools with their versions

#### Scenario: No file paths

- **WHEN** a client sends `GET /api/v1/versions`
- **THEN** the body contains no file system path, including the paths at which the tools were found

#### Scenario: cSNP's data

- **WHEN** a client sends `GET /api/v1/versions`, with or without the cSNP data installed
- **THEN** the body's `data` lists `{"service": "csnp", "panther": "9"}` first, cSNP's frozen PANTHER 9 data, and a `csnp` job's `versions.data` is that entry alone

#### Scenario: refmap's data

- **WHEN** a client sends `GET /api/v1/versions`, with or without the refmap data installed
- **THEN** the body's `data` is `[{"service": "csnp", "panther": "9"}, {"service": "refmap", "panther": "19"}]`, in the order the services were ported, and a `refmap` job's `versions.data` is `[{"service": "refmap", "panther": "19"}]`

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

### Requirement: cSNP species list

The API SHALL answer `GET /api/v1/csnp/species` with status 200 and a JSON array of the species a `csnp` request's `species` may name, and no other, each with its `code` and `name`, in the engine's order. The list MUST come from the engine, and MUST NOT need the cSNP data. A browser MUST be allowed to cache it for an hour.

#### Scenario: The species

- **WHEN** a client sends `GET /api/v1/csnp/species`
- **THEN** the API responds with status 200 and an array of 85 entries, among them `{"code": "HUMAN", "name": "Homo sapiens"}` and `{"code": "PLAF7", "name": "Plasmodium falciparum"}`, in the engine's order

#### Scenario: Every listed code is accepted

- **WHEN** a `csnp` job request names any code from the list as its `species`
- **THEN** the species check accepts it

#### Scenario: A code not in the list

- **WHEN** a `csnp` job request's `species` is `XENLA`, a PANTHER species that isn't in the list
- **THEN** the API rejects it with the `422` validation problem on `species`, as for any species the engine doesn't score

#### Scenario: Without the data

- **WHEN** the API runs without the cSNP data and a client sends `GET /api/v1/csnp/species`
- **THEN** the API responds with status 200 and the same list

#### Scenario: Cached

- **WHEN** a client sends `GET /api/v1/csnp/species`
- **THEN** the response has the header `Cache-Control: public, max-age=3600`

#### Scenario: In the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** the schema lists `GET /api/v1/csnp/species`, with a 200 response that is an array of entries, each with a required string `code` and a required string `name`

### Requirement: Request body limit

The API SHALL refuse a request whose body is over a configurable limit, 16 MiB by default, with status 413 and a fixed problem-details body, before the body is parsed. It MUST stop reading as soon as the declared length or the bytes received pass the limit. The default MUST fit the largest request the input rules allow.

#### Scenario: Over the limit by its length

- **WHEN** a client sends `POST /api/v1/jobs` with a body one byte over the limit, with its `Content-Length`
- **THEN** the API responds with status 413 and a problem-details body that doesn't contain the body's text, and no job is created

#### Scenario: Over the limit without a length

- **WHEN** a client sends `POST /api/v1/jobs` with a chunked body, without a `Content-Length`, that is over the limit
- **THEN** the API responds with status 413 and a problem-details body, and no job is created

#### Scenario: Streamed past the limit

- **WHEN** a body arrives in many chunks and passes the limit on the third
- **THEN** the API reads no further chunk, and answers status 413 without passing the request on

#### Scenario: At the limit

- **WHEN** a client sends a valid job whose body is exactly the limit
- **THEN** the API responds with status 202

#### Scenario: The largest valid request

- **WHEN** a client sends a `refmap` job of 100,000 IDs of 64 characters, each one escaped in the JSON, under the default limit
- **THEN** the body is read and validated, and the response isn't a 413

#### Scenario: The 413 in the schema

- **WHEN** a client reads the OpenAPI schema
- **THEN** every operation with a request body documents a 413 response with a problem-details body

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

At `INFO` and above, the API SHALL leave out of its request log a `GET /api/v1/health` and a `GET /api/v1/jobs/{id}` answered with a 2xx status. Every other request MUST be logged, including every `POST /api/v1/jobs`, with the client's address. At `DEBUG`, every request MUST be logged. If the server is started without a request log, the API MUST NOT turn it on.

#### Scenario: A successful poll

- **WHEN** the log level is `INFO` and a client polls an existing job
- **THEN** no request line is written for the poll

#### Scenario: A poll for an unknown job

- **WHEN** the log level is `INFO` and a client polls a job id that doesn't exist
- **THEN** a request line is written with the status `404`

#### Scenario: A health check

- **WHEN** the log level is `INFO` and a client sends `GET /api/v1/health`, and it's answered with `200`
- **THEN** no request line is written

#### Scenario: A failed health check

- **WHEN** the log level is `INFO` and `GET /api/v1/health` is answered with a `5xx` status
- **THEN** a request line is written with that status

#### Scenario: An accepted submission

- **WHEN** the log level is `INFO` and a client submits a valid job
- **THEN** a request line is written with the client's address, `POST /api/v1/jobs` and the status `202`

#### Scenario: A refused submission

- **WHEN** the log level is `INFO` and a client submits a job request that fails validation
- **THEN** a request line is written with `POST /api/v1/jobs` and the status `422`

#### Scenario: The request log turned off

- **WHEN** Uvicorn is started without its access log and a client sends `GET /api/v1/versions`
- **THEN** no request line is written, and the API's own lines still are

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

### Requirement: The engine's messages in the log

A job that fails on its input MUST be logged without the engine's message, which is written for the user. An unexpected error's traceback MAY carry the exception's message as the engine raised it; keeping submitted values out of those messages is the engine's contract.

#### Scenario: A job that fails on its input

- **WHEN** a job fails because the engine can't process its input, with a message for the user
- **THEN** the job's `detail` has the message, and the log does not

### Requirement: refmap organism list

The API SHALL answer `GET /api/v1/refmap/organisms` with status 200 and a JSON array of the organisms a `refmap` request's `organism` may name, and no other, in the engine's order. Each entry MUST have its `code`, its `name`, the number of `genes` in its classification file, and how many of them have a PANTHER ID (`genes_with_panther_id`). The list MUST come from the engine, and MUST NOT need the refmap data. A browser MUST be allowed to cache it for an hour.

#### Scenario: The organisms

- **WHEN** a client sends `GET /api/v1/refmap/organisms`
- **THEN** the API responds with status 200 and an array of 1,533 entries, among them one whose `code` is `ENDPU` and `name` is `Endocarpon pusillum`, with its gene counts, in the engine's order

#### Scenario: Every listed organism is accepted

- **WHEN** a `refmap` job request names any code from the list as its `organism`
- **THEN** the organism check accepts it

#### Scenario: The organism list without the data

- **WHEN** the API runs without the refmap data and a client sends `GET /api/v1/refmap/organisms`
- **THEN** the API responds with status 200 and the same list

#### Scenario: The organism list cached

- **WHEN** a client sends `GET /api/v1/refmap/organisms`
- **THEN** the response has the header `Cache-Control: public, max-age=3600`

#### Scenario: The organism list in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** the schema lists `GET /api/v1/refmap/organisms`, with a 200 response that is an array of entries, each with a required string `code`, a required string `name`, and required integers `genes` and `genes_with_panther_id`
