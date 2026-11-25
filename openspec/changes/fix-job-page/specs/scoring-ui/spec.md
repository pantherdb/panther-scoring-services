# Spec Delta

## ADDED Requirements

### Requirement: A job the page can't show

When `GET /api/v1/jobs/{id}` answers with a job whose `service` or `status` this build of the UI doesn't know, as an API newer than the site can, the job page SHALL say it can't show the job and suggest reloading the site to get its latest version. It MUST NOT keep checking the job, and MUST NOT show a status, a result, or the unknown value.

#### Scenario: A job of a service the page doesn't know

- **WHEN** the user opens a job's page and the API answers with a job whose `service` is `"future"`
- **THEN** the page says it can't show the job and suggests reloading the site, shows no status or result, and doesn't show "future"

#### Scenario: A status the page doesn't know

- **WHEN** the user opens a `csnp` job's page and the API answers with its `status` as `"paused"`
- **THEN** the page says it can't show the job and suggests reloading the site, and shows no status, result or "paused"

#### Scenario: No further checks of a job the page can't show

- **WHEN** the job page has said it can't show a job
- **THEN** the UI makes no further requests for that job while the page stays open

## MODIFIED Requirements

### Requirement: Job page at its own URL

The UI SHALL show a job at `/jobs/{id}`, loaded from `GET /api/v1/jobs/{id}`, so a reload or a shared link shows the same job. While the job is loading, the page MUST say so instead of showing an empty page. When the address changes from one job's page to another's, the page MUST start again from loading, and MUST NOT show anything of the previous job.

#### Scenario: Open a job's page

- **WHEN** the user opens `/jobs/{id}` for an existing job
- **THEN** the page first says the job is loading, then shows the job's service and status inside the app shell

#### Scenario: Reload a finished job

- **WHEN** the user reloads `/jobs/{id}` after the job has succeeded, before it expires
- **THEN** the page shows the same job, with the same result

#### Scenario: From one job's page to another's

- **WHEN** the page shows a succeeded `csnp` job at `/jobs/{a}`, and the address changes to `/jobs/{b}`, a `refmap` job, before the API has answered for `{b}`
- **THEN** the page says the job is loading, shows nothing of the `csnp` job, and then shows the `refmap` job

### Requirement: Start a tools check from the home page

The home page SHALL offer an action, secondary to the page's main content, that starts a `tools` job and opens that job's page. While the request to start it is in flight, the action MUST be disabled. If starting fails, the home page MUST say so, with no build details, and stay usable. If the user has left the home page by the time the job is accepted, the UI MUST stay where the user went.

#### Scenario: Start a tools check

- **WHEN** the user chooses to check the scoring tools on the home page
- **THEN** a `tools` job is started and the UI shows `/jobs/{id}` for the new job

#### Scenario: While starting

- **WHEN** the user has chosen to check the scoring tools and the API hasn't answered yet
- **THEN** the action is disabled

#### Scenario: Starting fails

- **WHEN** the user chooses to check the scoring tools and the API answers with an error
- **THEN** the home page says the check couldn't be started, shows no build details, stays at `/`, and the action can be chosen again

#### Scenario: Leaving while the check starts

- **WHEN** the user chooses to check the scoring tools, opens `/csnp` before the API answers, and the API then answers 202
- **THEN** the UI stays at `/csnp`

### Requirement: Submitting a cSNP request opens its job

When the API accepts a cSNP request with 202, the UI SHALL open `/jobs/{id}` for the new job. While the request is in flight, the submit action MUST be disabled. If the user has left the form's page by the time the request is accepted, the UI MUST stay where the user went.

#### Scenario: The API accepts the request

- **WHEN** the user submits a valid input and the API answers 202 with a `csnp` job
- **THEN** the UI shows `/jobs/{id}` for that job

#### Scenario: While submitting

- **WHEN** the user has submitted a valid input and the API hasn't answered yet
- **THEN** the submit action is disabled

#### Scenario: Leaving the cSNP form while the job starts

- **WHEN** the user submits a valid input, opens `/refmap` before the API answers, and the API then answers 202
- **THEN** the UI stays at `/refmap`

### Requirement: Submitting a refmap request opens its job

When the API accepts a refmap request with 202, the UI SHALL open `/jobs/{id}` for the new job. While the request is in flight, the submit action MUST be disabled. If the user has left the form's page by the time the request is accepted, the UI MUST stay where the user went.

#### Scenario: The API accepts the request (refmap)

- **WHEN** the user submits a valid input and the API answers 202 with a `refmap` job
- **THEN** the UI shows `/jobs/{id}` for that job, headed as protein ID mapping

#### Scenario: While submitting the IDs

- **WHEN** the user has submitted a valid input and the API hasn't answered yet
- **THEN** the submit action is disabled

#### Scenario: Leaving the refmap form while the job starts

- **WHEN** the user submits a valid input, opens `/` before the API answers, and the API then answers 202
- **THEN** the UI stays at `/`

### Requirement: Submitting an hmmscore request opens its job

When the API accepts an HMM scoring request with 202, the UI SHALL open `/jobs/{id}` for the new job. While the request is in flight, the submit action MUST be disabled. If the user has left the form's page by the time the request is accepted, the UI MUST stay where the user went.

#### Scenario: The API accepts the request (hmmscore)

- **WHEN** the user submits a valid sequence and the API answers 202 with an `hmmscore` job
- **THEN** the UI shows `/jobs/{id}` for that job, headed as HMM scoring

#### Scenario: While submitting the sequence

- **WHEN** the user has submitted a valid sequence and the API hasn't answered yet
- **THEN** the submit action is disabled

#### Scenario: Leaving the HMM scoring form while the job starts

- **WHEN** the user submits a valid sequence, opens `/refmap` before the API answers, and the API then answers 202
- **THEN** the UI stays at `/refmap`
