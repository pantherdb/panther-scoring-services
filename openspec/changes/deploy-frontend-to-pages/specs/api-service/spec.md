# Spec Delta

## ADDED Requirements

### Requirement: CORS for allowed origins

The API SHALL allow cross-origin calls from exactly the origins listed in a setting, empty by default. With none listed, it MUST add no CORS headers. A listed origin MUST get `Access-Control-Allow-Origin`, `GET` and `POST`, `Content-Type`, the exposed `Location` and `Retry-After`, and never credentials; any other origin MUST NOT get `Access-Control-Allow-Origin`.

#### Scenario: No origins

- **WHEN** the API runs with no origins listed and a client sends a request with an `Origin` header
- **THEN** the response has no CORS headers, and a preflight isn't answered as allowed

#### Scenario: A preflight from an allowed origin

- **WHEN** the API runs with `https://pantherdb.github.io` listed and a browser sends a preflight for `POST /api/v1/jobs` from that origin
- **THEN** the response allows that origin, `GET` and `POST`, and `Content-Type`, and doesn't allow credentials

#### Scenario: A request from an allowed origin

- **WHEN** a client sends `POST /api/v1/jobs` from an allowed origin
- **THEN** the response allows that origin and exposes `Location` and `Retry-After`

#### Scenario: Another origin

- **WHEN** a client sends a request or a preflight from an origin that isn't listed
- **THEN** the response has no `Access-Control-Allow-Origin`

### Requirement: Only exact origins are allowed

Each value in the CORS setting MUST be an exact origin: a scheme of `http` or `https`, a host and an optional port. A value with a path, a wildcard or a trailing slash MUST stop the API from starting.

#### Scenario: Not an origin

- **WHEN** the API starts with the setting `https://pantherdb.github.io/panther-scoring-services/` or `*`
- **THEN** the API fails to start

### Requirement: CORS with the body limit

With origins listed, the request body limit MUST NOT refuse a preflight, and a `413` for a request from an allowed origin MUST carry `Access-Control-Allow-Origin`, so the browser lets the page read it.

#### Scenario: A preflight declaring a large body

- **WHEN** a browser sends a preflight from an allowed origin with a `Content-Length` over the limit
- **THEN** the preflight is answered as allowed, not with a 413

#### Scenario: A 413 for an allowed origin

- **WHEN** a client sends a body over the limit from an allowed origin
- **THEN** the response is a 413 that allows that origin

#### Scenario: A 413 for another origin

- **WHEN** a client sends a body over the limit from an origin that isn't listed
- **THEN** the response is a 413 without `Access-Control-Allow-Origin`
