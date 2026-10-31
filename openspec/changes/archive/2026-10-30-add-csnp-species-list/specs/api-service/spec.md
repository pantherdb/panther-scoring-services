# Spec Delta

## ADDED Requirements

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
