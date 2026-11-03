# Spec Delta

## ADDED Requirements

### Requirement: The API's address set at build time

The UI SHALL call the scoring service at the API URL set when it's built, followed by `/api/v1`. When no API URL is set, it MUST call the relative `/api/v1` on its own origin.

#### Scenario: No API URL

- **WHEN** the UI is built with no API URL, or an empty one
- **THEN** every API call goes to `/api/v1` on the UI's own origin

#### Scenario: An API URL

- **WHEN** the UI is built with the API URL `https://api.example.org`
- **THEN** every API call goes to `https://api.example.org/api/v1`

#### Scenario: A trailing slash

- **WHEN** the UI is built with the API URL `https://api.example.org/`
- **THEN** every API call goes to `https://api.example.org/api/v1`

### Requirement: Served under a base path

The UI SHALL work when served under a base path set when it's built, such as `/panther-scoring-services/`: its assets, its routes and its links MUST all include that path. With no base path set, it MUST be served at `/`.

#### Scenario: The home page

- **WHEN** the UI is built with the base path `/panther-scoring-services/` and the user opens `/panther-scoring-services/`
- **THEN** the home page is shown, and its assets load from under `/panther-scoring-services/`

#### Scenario: A page under the base path

- **WHEN** the user opens `/panther-scoring-services/csnp`
- **THEN** the cSNP form is shown, not the not-found page

#### Scenario: The not-found page links home

- **WHEN** the user opens `/panther-scoring-services/does-not-exist` and follows its link home
- **THEN** the link points at `/panther-scoring-services/`, and the home page is shown

### Requirement: Deep links survive a reload on a static host

Every build SHALL include a `404.html` identical to its `index.html`, so a static host that serves `404.html` for an unknown path, such as GitHub Pages, starts the app at any of its URLs.

#### Scenario: A reload of a job's page

- **WHEN** the user reloads `/panther-scoring-services/jobs/{id}` on GitHub Pages
- **THEN** the app starts and shows that job's page

### Requirement: API docs link

When the UI calls the scoring service, the footer SHALL show a link to the API's interactive docs, at the API's address followed by `/api/v1/docs`. On mocked API answers it MUST NOT show the link.

#### Scenario: Docs with no API URL

- **WHEN** the UI is built with no API URL and calls the scoring service
- **THEN** the footer links to `/api/v1/docs`

#### Scenario: Docs with an API URL

- **WHEN** the UI is built with the API URL `https://api.example.org`
- **THEN** the footer links to `https://api.example.org/api/v1/docs`

#### Scenario: Mocked answers

- **WHEN** the API is mocked
- **THEN** the footer shows no API docs link

### Requirement: No mock mode in a deployed build

A build with API mocking on MUST NOT also name an API URL, and the deployed site MUST NOT contain the API mocking library or the mock data banner.

#### Scenario: Mocking with an API URL

- **WHEN** a build is made with API mocking on and an API URL set
- **THEN** the build fails

#### Scenario: The deployed build

- **WHEN** the deploy workflow builds the site
- **THEN** it fails, and deploys nothing, if any file in the build contains the API mocking library's worker or the mock data banner's text
