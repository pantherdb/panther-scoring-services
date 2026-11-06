# Spec Delta

## ADDED Requirements

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

#### Scenario: In the schema

- **WHEN** a client reads the OpenAPI schema
- **THEN** every operation with a request body documents a 413 response with a problem-details body
