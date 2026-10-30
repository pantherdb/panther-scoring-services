# Spec Delta

## MODIFIED Requirements

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
- **THEN** the body's `data` is `[{"service": "csnp", "panther": "9"}]`, cSNP's frozen PANTHER 9 data, and every job's `versions` has the same `data`
