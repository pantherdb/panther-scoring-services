# scoring-ui Specification

## Purpose

The web UI for PANTHER's scoring services (`hmmscore`, `refmap`, `csnp` and `treegrafter`): the app shell and pages through which users submit their input and read their results.

## Requirements

### Requirement: App shell with title

Every page SHALL be shown inside a shared app shell whose header displays the application title as a top-level heading.

#### Scenario: Title on the home page

- **WHEN** the user opens `/`
- **THEN** the header shows the application title as a heading

#### Scenario: Title on an unknown page

- **WHEN** the user opens a URL that matches no route
- **THEN** the header still shows the application title

### Requirement: Home page

The UI SHALL serve a home page at `/`.

#### Scenario: Open the home page

- **WHEN** the user opens `/`
- **THEN** the home page content is shown inside the app shell

### Requirement: Not-found page

The UI SHALL show a not-found page, with a link back to the home page, for any URL that matches no route. It MUST NOT show a blank page or an error.

#### Scenario: Unknown URL

- **WHEN** the user opens `/does-not-exist`
- **THEN** the page says it was not found and offers a link to `/`

#### Scenario: Back to home

- **WHEN** the user follows the link on the not-found page
- **THEN** the home page is shown

### Requirement: Usable on desktop and mobile widths

The app shell SHALL be usable at desktop and mobile viewport widths, with no horizontal scrolling of the page.

#### Scenario: Mobile viewport

- **WHEN** the user opens `/` on a mobile-width viewport
- **THEN** the title is visible and the page does not scroll horizontally

### Requirement: No build details on screen

The UI MUST NOT show build or environment details, such as ports, environment variables or commands, in any user-facing text, including the not-found page.

#### Scenario: Not-found page text

- **WHEN** the user opens a URL that matches no route
- **THEN** the page shows no port numbers, environment variable names or shell commands

### Requirement: Versions on every page

Every page SHALL show the API version, the engine version and each external tool with its version, as `GET /api/v1/versions` reports them and in the order reported, so a result can be traced to what produced it. A tool with a `null` version MUST be shown as not available, not left out. If the versions can't be loaded, the page MUST say so instead of showing an empty list, and the rest of the page MUST still work.

#### Scenario: All versions reported

- **WHEN** the user opens `/` and the API reports versions for the API, the engine and every tool
- **THEN** the page shows the API version, the engine version, and `blastp`, `hmmscan`, `hmmsearch` and `epa-ng` each with its version, in that order

#### Scenario: A tool is missing

- **WHEN** the user opens `/` and the API reports `epa-ng` with a `null` version
- **THEN** the page shows `epa-ng` as not available, and still shows the other tools with their versions

#### Scenario: Versions can't be loaded

- **WHEN** the user opens `/` and the versions request fails
- **THEN** the page says the versions are unavailable, shows no version numbers, and still shows the title and the home page content

#### Scenario: On the not-found page

- **WHEN** the user opens a URL that matches no route
- **THEN** the page shows the versions as it does on `/`

#### Scenario: Versions are not build details

- **WHEN** the page shows the versions
- **THEN** the versions text contains no port numbers, environment variable names, shell commands or file paths
