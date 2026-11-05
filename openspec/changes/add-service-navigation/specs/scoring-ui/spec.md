# Spec Delta

## ADDED Requirements

### Requirement: The title links home

The application title in the header SHALL be a link to the home page, on every page.

#### Scenario: From a form

- **WHEN** the user is on `/csnp` and follows the title
- **THEN** the home page is shown

### Requirement: Service tabs

The header SHALL list the four services on every page, in this order: cSNP scoring, ID mapping, HMM scoring, TreeGrafter. Each MUST link to its service's page. The tab of the page being shown MUST be marked as current, and on a job's page the tab of that job's service. On a phone-width screen the tabs MUST NOT make the page scroll sideways.

#### Scenario: On a form

- **WHEN** the user opens `/csnp`
- **THEN** the header lists the four services in order, and cSNP scoring is marked as current

#### Scenario: On a job's page

- **WHEN** the user opens the page of a `csnp` job
- **THEN** cSNP scoring is marked as current

#### Scenario: Following a tab

- **WHEN** the user follows the ID mapping tab
- **THEN** the refmap form is shown, and ID mapping is marked as current

### Requirement: Services that aren't available yet

Every service the API can't score yet SHALL be marked "coming soon", in its tab and on the home page: today ID mapping, HMM scoring and TreeGrafter. ID mapping's tab MUST still open its form. HMM scoring and TreeGrafter MUST each open a page that says what the service will do, that it's coming soon, and links home.

#### Scenario: The marks

- **WHEN** the user opens any page
- **THEN** the ID mapping, HMM scoring and TreeGrafter tabs say they're coming soon, and cSNP scoring doesn't

#### Scenario: A service without a form

- **WHEN** the user follows the HMM scoring tab
- **THEN** a page says HMM scoring is coming soon, says what it will do, and links home

### Requirement: The home page shows every service

The home page SHALL show the four services, in the tabs' order, each with what it does and the same "coming soon" mark. A service with a form MUST link to it.

#### Scenario: The four services

- **WHEN** the user opens `/`
- **THEN** the page shows cSNP scoring, ID mapping, HMM scoring and TreeGrafter, with links to the cSNP and refmap forms, and the last three marked coming soon

### Requirement: The next step from a job's page

A job's page SHALL offer the next step, whatever the job's status: for a `csnp` job, a link to an empty cSNP form; for a `refmap` job, a link to an empty refmap form; for the tools check, a link home.

#### Scenario: A cSNP job

- **WHEN** the user opens the page of a `csnp` job and follows "New cSNP search"
- **THEN** the cSNP form is shown, empty

#### Scenario: The tools check

- **WHEN** the user opens the page of a tools job
- **THEN** the page links home

### Requirement: Edit and resubmit

When a job was submitted from the same browser tab, its page SHALL offer to edit and resubmit it: the service's form opens filled in with the input as it was typed, says so, and starts a new job when submitted. The input MUST be kept only in that tab, and a job opened from a shared link or another tab MUST NOT offer it.

#### Scenario: Edit a cSNP job

- **WHEN** the user submits the cSNP form, then follows "Edit and resubmit" on the job's page
- **THEN** the cSNP form shows the same sequence, substitutions and species as typed, and says it was filled in from the earlier job

#### Scenario: A shared link

- **WHEN** the user opens a job's page that wasn't submitted from this tab
- **THEN** the page offers no "Edit and resubmit"

### Requirement: The API docs open in a new tab

The footer's link to the API's docs SHALL open in a new tab, without giving the docs a reference back to the app's page, and its accessible name MUST say that it opens in a new tab.

#### Scenario: The link

- **WHEN** the UI calls the scoring service and shows the footer
- **THEN** the API docs link opens in a new tab, and its accessible name says so
