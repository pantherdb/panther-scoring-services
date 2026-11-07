# Spec Delta

## ADDED Requirements

### Requirement: refmap organism list

The API SHALL answer `GET /api/v1/refmap/organisms` with status 200 and a JSON array of the organisms a `refmap` request's `organism` may name, and no other, in the engine's order. Each entry MUST have its `code`, its `name`, the number of `genes` in its classification file, and how many of them have a PANTHER ID (`genes_with_panther_id`). The list MUST come from the engine, and MUST NOT need the refmap data. A browser MUST be allowed to cache it for an hour.

#### Scenario: The organisms

- **WHEN** a client sends `GET /api/v1/refmap/organisms`
- **THEN** the API responds with status 200 and an array of 1,533 entries, among them one whose `code` is `ENDPU` and `name` is `Endocarpon pusillum`, with its gene counts, in the engine's order

#### Scenario: Every listed code is accepted

- **WHEN** a `refmap` job request names any code from the list as its `organism`
- **THEN** the organism check accepts it

#### Scenario: Without the data

- **WHEN** the API runs without the refmap data and a client sends `GET /api/v1/refmap/organisms`
- **THEN** the API responds with status 200 and the same list

#### Scenario: Cached

- **WHEN** a client sends `GET /api/v1/refmap/organisms`
- **THEN** the response has the header `Cache-Control: public, max-age=3600`

#### Scenario: The organism list in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** the schema lists `GET /api/v1/refmap/organisms`, with a 200 response that is an array of entries, each with a required string `code`, a required string `name`, and required integers `genes` and `genes_with_panther_id`

## MODIFIED Requirements

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
- **THEN** the first request's 422 takes no more than twice as long as the second's, measured in the same process
