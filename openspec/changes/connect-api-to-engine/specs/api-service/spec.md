# Spec Delta

## ADDED Requirements

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
