# Spec Delta

## ADDED Requirements

### Requirement: refmap organism classification

The API SHALL answer `GET /api/v1/refmap/organisms/{code}/classification`, for a `code` in the refmap organism list, with status 200 and a JSON body in the shape of a `refmap` job's result: the `organism`'s code and its `mappings`, one for each line of the organism's classification file, in the file's order, a repeated ID each time. Each line MUST be read as a `refmap` job reads it.

#### Scenario: Every gene, in the file's order

- **WHEN** a client sends `GET /api/v1/refmap/organisms/ENDPU/classification`, and ENDPU's file has four lines: `U1G4Q5` and `PTHR10351`, `U1HV42` and `NOHIT`, `U1G4Q5` and `PTHR10351:SF2`, each pair separated by a tab, and `U1NOTAB` with no tab
- **THEN** the API responds with status 200 and `{"organism": "ENDPU", "mappings": [{"id": "U1G4Q5", "panther_id": "PTHR10351"}, {"id": "U1HV42", "panther_id": null}, {"id": "U1G4Q5", "panther_id": "PTHR10351:SF2"}, {"id": "U1NOTAB", "panther_id": null}]}`

#### Scenario: A third field

- **WHEN** a line of the organism's file has a third tab-separated field
- **THEN** its mapping's `panther_id` is the second field only

#### Scenario: The published file, rebuilt

- **WHEN** a client fetches the classification of each organism in the list, with the release's data
- **THEN** its mappings, written back as the `id`, a tab and the `panther_id` or `NOHIT`, one a line, are the organism's file byte for byte, and their counts are the list's `genes` and `genes_with_panther_id`

#### Scenario: The classification in the schema

- **WHEN** a client fetches `/api/v1/openapi.json`
- **THEN** the schema lists `GET /api/v1/refmap/organisms/{code}/classification`, with a 200 response that is a `RefmapResult` and a 404 response

### Requirement: refmap classification is not kept

The API MUST NOT keep an organism's classification, or its file, in memory after the response is sent, and MUST NOT send a `Cache-Control` header with it.

#### Scenario: Not cached

- **WHEN** a client fetches an organism's classification
- **THEN** the response has no `Cache-Control` header

### Requirement: refmap classification of an unlisted organism

The API MUST check the `code` of `GET /api/v1/refmap/organisms/{code}/classification` against the refmap organism list before reading anything, and MUST answer any code not in it with status 404 and a problem-details body.

#### Scenario: An organism refmap doesn't map for

- **WHEN** a client sends `GET /api/v1/refmap/organisms/{code}/classification` with a code that isn't in the list, such as `NOPE1`, `endpu`, `ENDPUX`, or `..` encoded or not
- **THEN** the API responds with status 404 and a problem-details body, and reads no file

### Requirement: refmap classification without its file

A request for a listed organism's classification whose file is missing from the data folder MUST fail with the generic 500, which names no path.

#### Scenario: The organism's file is missing

- **WHEN** a client asks for a listed organism whose classification file isn't in the data folder
- **THEN** the API responds with the generic 500, whose body names neither the organism's file nor its folder
