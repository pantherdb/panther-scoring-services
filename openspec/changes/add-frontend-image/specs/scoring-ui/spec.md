# Spec Delta

## ADDED Requirements

### Requirement: The site built in a container

The repository SHALL build the site in a container from `frontend/` alone, on any machine with Docker and no Node. It MUST be the production build, and the build MUST fail if the result contains the API mocking library or the mock data banner. The base path and the API's URL MUST be build arguments with the same defaults as `npm run build`.

#### Scenario: The defaults

- **WHEN** the image is built with no build arguments
- **THEN** the site is served at `/`, and calls the relative `/api/v1`

#### Scenario: A base path

- **WHEN** the image is built with the base path `/scoring/`
- **THEN** the asset URLs in the built `index.html` start with `/scoring/`

### Requirement: The built files without a server

The build SHALL be able to write the built files to a folder on the host, for a web server that's already running, with the same files the web image serves.

#### Scenario: Write the files

- **WHEN** the files are written to a folder with the documented command
- **THEN** the folder holds `index.html`, `404.html` and the `assets` folder, and nothing else from the build

### Requirement: The web image serves the site and forwards the API

The web image SHALL serve the site on port 8080 as a user other than root. A path that isn't a file MUST get `index.html`. Requests under `/api/` MUST be forwarded to the API at an address set when the container starts, `http://api:8000` by default, with bodies up to the API's own limit. Assets MUST be cached for a long time, and `index.html` revalidated on each load.

#### Scenario: A deep link

- **WHEN** a client requests `/jobs/{id}` from the web image
- **THEN** it gets `index.html` with status 200

#### Scenario: The API through the site

- **WHEN** a client requests `/api/v1/health` from the web image
- **THEN** the request reaches the API, and the API's answer comes back

#### Scenario: Caching

- **WHEN** a client requests an asset, then `/`
- **THEN** the asset's response may be cached for a year, and the page's must be revalidated

### Requirement: The site and the API with one command

A developer or the server SHALL be able to start the web image with the API image with one documented command from the repository root. The site MUST then answer at `http://localhost:8080`, and its API calls MUST reach that API.

#### Scenario: Start both

- **WHEN** the documented command is run from a fresh clone
- **THEN** `http://localhost:8080/` serves the site, and `http://localhost:8080/api/v1/health` returns status 200

### Requirement: The web image published after each change

After a push to `main` that changes `frontend/`, and once the web image's checks pass, CI SHALL publish the web image to GitHub's container registry for `linux/amd64`, tagged `main` and with the commit's SHA. A pull request MUST NOT publish. The files in the published image MUST be the same as the ones the documented command writes to a folder.

#### Scenario: A merge that changes the site

- **WHEN** a pull request that changes `frontend/` merges, and the checks pass on `main`
- **THEN** `ghcr.io/pantherdb/panther-web:main` and the tag with the merge's SHA are that commit's image

#### Scenario: A merge that doesn't

- **WHEN** a push to `main` changes nothing in `frontend/`
- **THEN** nothing is published, and the `main` tag stays where it was

#### Scenario: A pull request

- **WHEN** CI runs on a pull request
- **THEN** the web image is built and checked, and nothing is published
