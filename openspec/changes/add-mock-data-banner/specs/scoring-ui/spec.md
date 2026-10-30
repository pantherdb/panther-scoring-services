# Spec Delta

## ADDED Requirements

### Requirement: Mock data is marked on every page

When the UI runs on mocked API answers instead of the scoring service, every page SHALL show, in the app shell, a banner saying that the data is mock data and that nothing on the page comes from the scoring service. The banner MUST stay in view while the page scrolls, MUST be a named region that assistive technologies list with the page's landmarks, and MUST fit mobile widths with no horizontal scrolling of the page.

#### Scenario: Home page on mocks

- **WHEN** the UI runs on mocked answers and the user opens `/`
- **THEN** the page shows a region named as mock data, whose text says the data is mock data and doesn't come from the scoring service

#### Scenario: Form, job and not-found pages on mocks

- **WHEN** the UI runs on mocked answers and the user opens `/csnp`, a job's page at `/jobs/{id}`, or a URL that matches no route
- **THEN** each page shows the mock data region

#### Scenario: Scrolled to the end of a page

- **WHEN** the UI runs on mocked answers and the user scrolls to the end of a job's page
- **THEN** the mock data region is still in view

#### Scenario: Mobile width

- **WHEN** the UI runs on mocked answers and the user opens `/` on a mobile-width viewport
- **THEN** the mock data region is visible and the page does not scroll horizontally

#### Scenario: Not a build detail

- **WHEN** the page shows the mock data region
- **THEN** its text contains no port numbers, environment variable names, shell commands or file paths

### Requirement: No mock data with the real API

When the UI calls the scoring service, it MUST NOT show the mock data banner on any page. A production build MUST contain neither the banner's text nor the code that mocks the API.

#### Scenario: Against the real API

- **WHEN** the UI calls the scoring service and the user opens `/`, `/csnp` or a URL that matches no route
- **THEN** no page shows the mock data region

#### Scenario: The production build

- **WHEN** the production build is made
- **THEN** none of its files contains the banner's text or the API mocking library
