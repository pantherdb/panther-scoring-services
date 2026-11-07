# Spec Delta

## ADDED Requirements

### Requirement: The site built in a container

The repository SHALL build the site in a container from `frontend/` alone, on any machine with Docker and no Node. It MUST be the production build, and the build MUST fail if the result contains the API mocking library or the mock data banner. The base path and the API's URL MUST be build arguments with the same defaults as `npm run build`. A CA certificate MAY be given to the build, for a network that re-signs TLS, and MUST NOT be kept in the image.

#### Scenario: The defaults

- **WHEN** the image is built with no build arguments
- **THEN** the site is served at `/`, and calls the relative `/api/v1`

#### Scenario: Behind a network that re-signs TLS

- **WHEN** the image is built on a network that re-signs TLS, with that network's CA certificate given to the build
- **THEN** the dependencies install, and the image holds no copy of the certificate

#### Scenario: A base path

- **WHEN** the image is built with the base path `/scoring/`
- **THEN** the asset URLs in the built `index.html` start with `/scoring/`

### Requirement: The built files without a server

The build SHALL be able to write the built files to a folder on the host, for a web server that's already running, with the same files the web image serves.

#### Scenario: Write the files

- **WHEN** the files are written to a folder with the documented command
- **THEN** the folder holds `index.html`, `404.html` and the `assets` folder, and nothing else from the build

### Requirement: The web image serves the site and forwards the API

The web image SHALL serve the site on port 8080 as a user other than root. A path that isn't a file MUST get `index.html`. Requests under `/api/` MUST be forwarded to the API at an address set when the container starts, `http://api:8000` by default, with bodies up to the API's own limit, and with the host and scheme the request came with. A replaced API container MUST be reached without restarting the web image. Assets MUST be cached for a long time, and `index.html` revalidated on each load.

#### Scenario: A deep link

- **WHEN** a client requests `/jobs/{id}` from the web image
- **THEN** it gets `index.html` with status 200

#### Scenario: The API through the site

- **WHEN** a client requests `/api/v1/health` from the web image
- **THEN** the request reaches the API, and the API's answer comes back

#### Scenario: The API's container replaced

- **WHEN** the API's container is replaced by one with the same name and a new address, while the web image runs
- **THEN** within seconds, requests to `/api/` reach the new container, with no restart of the web image

#### Scenario: Forwarded by a front end

- **WHEN** a front end that ended HTTPS forwards a request under `/api/` with `X-Forwarded-Proto: https`
- **THEN** the API receives `X-Forwarded-Proto: https` and the request's own `Host`

#### Scenario: Caching

- **WHEN** a client requests an asset, then `/`
- **THEN** the asset's response may be cached for a year, and the page's must be revalidated

### Requirement: The site and the API with one command

A developer or the server SHALL be able to start the web image with the API image with one documented command from the repository root. The site MUST then answer at `http://localhost:8080`, and its API calls MUST reach that API.

#### Scenario: Start both

- **WHEN** the documented command is run from a fresh clone
- **THEN** `http://localhost:8080/` serves the site, and `http://localhost:8080/api/v1/health` returns status 200
