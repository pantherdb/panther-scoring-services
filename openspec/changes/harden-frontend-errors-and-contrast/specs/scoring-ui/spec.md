# Spec Delta

## ADDED Requirements

### Requirement: A page that fails to render keeps the shell

When rendering a page throws, the UI SHALL replace only that page with an error page inside the app shell, with fixed text and a link to the home page; the header and footer MUST stay. When the shell itself throws, the UI MUST show the header with the same error page. The error page MUST NOT show the error, its stack, build details, or React Router's own error screen.

#### Scenario: A page throws

- **WHEN** the user opens `/` and rendering the home page throws
- **THEN** the page shows the header, a fixed error message, a link to `/` and the footer's versions, and no error text, stack trace or React Router developer screen

#### Scenario: The shell throws

- **WHEN** the user opens `/` and rendering the footer throws
- **THEN** the page shows the header, a fixed error message and a link to `/`, and no error text, stack trace or React Router developer screen

#### Scenario: Going home from the error page

- **WHEN** a page has failed to render and the user follows the link home, where the home page renders
- **THEN** the UI shows `/` with the home page

### Requirement: Field text meets WCAG AA contrast

A form field's description and its error message SHALL each have a contrast ratio of at least 4.5:1 against the page's background (WCAG 2.1, 1.4.3), and MUST take their colours from the project's colour tokens, not from Mantine's defaults.

#### Scenario: Description and error on the cSNP form

- **WHEN** the user opens `/csnp`, and submits the empty form
- **THEN** the protein sequence field's description and its error each have a contrast ratio of at least 4.5:1 against the page's background

## MODIFIED Requirements

### Requirement: Versions on every page

Every page SHALL show the API version, the engine version, each external tool with its version, and each service's data with the PANTHER release the API names for it, as `GET /api/v1/versions` reports them and in the order reported, so a result can be traced to what produced it. A tool with a `null` version MUST be shown as not available, not left out. If the versions can't be loaded, the page MUST say so instead of showing an empty list, and the rest of the page MUST still work. If the answer leaves out the tools or the data, the page MUST show the rest of the versions, and the rest of the page MUST still work.

#### Scenario: All versions reported

- **WHEN** the user opens `/` and the API reports versions for the API, the engine and every tool
- **THEN** the page shows the API version, the engine version, and `blastp`, `hmmscan`, `hmmsearch` and `epa-ng` each with its version, in that order

#### Scenario: A tool is missing

- **WHEN** the user opens `/` and the API reports `epa-ng` with a `null` version
- **THEN** the page shows `epa-ng` as not available, and still shows the other tools with their versions

#### Scenario: Versions can't be loaded

- **WHEN** the user opens `/` and the versions request fails
- **THEN** the page says the versions are unavailable, shows no version numbers, and still shows the title and the home page content

#### Scenario: The answer has no tools or data

- **WHEN** the user opens `/csnp` and the API answers the versions with 200 and `{"api": "1.2.3", "engine": "4.5.6"}`
- **THEN** the page shows the API and engine versions, and still shows the title and the cSNP form

#### Scenario: On the not-found page

- **WHEN** the user opens a URL that matches no route
- **THEN** the page shows the versions as it does on `/`

#### Scenario: Versions are not build details

- **WHEN** the page shows the versions
- **THEN** the versions text contains no port numbers, environment variable names, shell commands or file paths

#### Scenario: Each service's data

- **WHEN** the user opens `/` and the API reports the data `[{"service": "csnp", "panther": "10"}]`
- **THEN** the page shows cSNP's data as PANTHER 10, after the tools, and no other PANTHER release for it
