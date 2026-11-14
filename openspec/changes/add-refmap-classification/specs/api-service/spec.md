# Spec Delta

## ADDED Requirements

### Requirement: refmap organism classification

The API SHALL answer `GET /api/v1/refmap/organisms/{code}/classification`, for a `code` in the refmap organism list, with status 200 and a JSON body in the shape of a `refmap` job's result: the `organism`'s code and its `mappings`, one for each line of the organism's classification file, in the file's order, as the engine's `classification_mappings` reads them. A repeated ID MUST appear once for each of its lines.

#### Scenario: Every gene, in the file's order

- **WHEN** a client sends `GET /api/v1/refmap/organisms/ENDPU/classification`, and ENDPU's file has three lines: `U1G4Q5` and `PTHR10351`, `U1HV42` and `NOHIT`, `U1G4Q5` and `PTHR10351:SF2`, each pair separated by a tab
- **THEN** the API responds with status 200 and `{"organism": "ENDPU", "mappings": [{"id": "U1G4Q5", "panther_id": "PTHR10351"}, {"id": "U1HV42", "panther_id": null}, {"id": "U1G4Q5", "panther_id": "PTHR10351:SF2"}]}`

#### Scenario: Every organism, as the engine reads it

- **WHEN** a client fetches the classification of each organism in the list, with the release's data and its classification JSON built
- **THEN** each response's mappings are the engine's `classification_mappings` of that organism's file

#### Scenario: The classification in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** the schema lists `GET /api/v1/refmap/organisms/{code}/classification`, with a 200 response that is a `RefmapResult`, a 404 response that is a `Problem`, and no 422 response

### Requirement: refmap classification sent from its built file

The API SHALL send an organism's classification from the gzipped JSON built ahead of time (`refmap data build-json`). A request whose `Accept-Encoding` accepts gzip MUST get the file as it is, with `Content-Encoding: gzip`; any other MUST get it decompressed. The response MUST NOT carry `Cache-Control`, `ETag` or `Last-Modified`.

#### Scenario: A client that accepts gzip

- **WHEN** a client sends `Accept-Encoding: gzip` and fetches ENDPU's classification
- **THEN** the response has `Content-Encoding: gzip` and the file's length, and decompresses to the classification

#### Scenario: A client that doesn't

- **WHEN** a client sends `Accept-Encoding: identity`, or none, and fetches ENDPU's classification
- **THEN** the response has no `Content-Encoding`, and its body is the classification's JSON

#### Scenario: Not cached

- **WHEN** a client fetches an organism's classification
- **THEN** the response has no `Cache-Control`, `ETag` or `Last-Modified` header, and has `Vary: Accept-Encoding`

### Requirement: refmap classification of an unlisted organism

The API MUST check the `code` of `GET /api/v1/refmap/organisms/{code}/classification` against the refmap organism list before building any path from it, and MUST answer any code not in it with status 404 and a problem-details body.

#### Scenario: An organism refmap doesn't map for

- **WHEN** a client sends `GET /api/v1/refmap/organisms/{code}/classification` with a code that isn't in the list, such as `NOPE1`, `endpu`, `ENDPUX`, `HUMAN` or `%2E%2E`
- **THEN** the API responds with status 404 and a problem-details body saying refmap doesn't map for an organism with that code and naming the organism list, and builds no path from the code

### Requirement: refmap classification without its file

A request for a listed organism's classification whose built file is missing, or with no data folder set, MUST fail with the generic 500, which names no path. The cause MUST be logged at most once in ten minutes. At startup, once the refmap data is in place, the API MUST log an error naming how many classification files are missing, and start anyway.

#### Scenario: The organism's file is missing

- **WHEN** a client asks twice for a listed organism whose classification JSON isn't in the data folder
- **THEN** the API responds both times with the generic 500, whose body names neither the organism's file nor its folder, and logs the cause once

#### Scenario: The startup check

- **WHEN** the API starts with the refmap data in place and no classification JSON
- **THEN** it logs one error, that refmap classifications will fail until the classification JSON is built, naming how many files are missing, and health is 200
