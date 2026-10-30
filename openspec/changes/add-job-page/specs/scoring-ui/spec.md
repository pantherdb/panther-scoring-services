# Spec Delta

## ADDED Requirements

### Requirement: Job page at its own URL

The UI SHALL show a job at `/jobs/{id}`, loaded from `GET /api/v1/jobs/{id}`, so a reload or a shared link shows the same job. While the job is loading, the page MUST say so instead of showing an empty page.

#### Scenario: Open a job's page

- **WHEN** the user opens `/jobs/{id}` for an existing job
- **THEN** the page first says the job is loading, then shows the job's service and status inside the app shell

#### Scenario: Reload a finished job

- **WHEN** the user reloads `/jobs/{id}` after the job has succeeded, before it expires
- **THEN** the page shows the same job, with the same result

### Requirement: Job status updates until the job finishes

While a job's status is `queued` or `running`, the job page SHALL show that status and keep checking the job, so the status shown follows the job without a reload. It MUST stop checking once the job has `succeeded` or `failed`.

#### Scenario: A job moves forward

- **WHEN** the user opens the page of a job that is `queued`, and the job then becomes `running`, then `succeeded`
- **THEN** the page shows each of those statuses in turn, and then the result, without a reload

#### Scenario: Checking stops when the job finishes

- **WHEN** the job page shows a job that has `succeeded` or `failed`
- **THEN** the UI makes no further requests for that job while the page stays open

### Requirement: Succeeded job shows its result with its versions

When a job has `succeeded`, the job page SHALL show its result in the form for its service, and the API, engine and tool versions the job reports, so the result can be traced to what produced it. For a `tools` job, the result is each tool with its version, in the order reported, and a tool with a `null` version MUST be shown as not available.

#### Scenario: A tools job succeeded

- **WHEN** the user opens the page of a `tools` job that has succeeded
- **THEN** the page shows each tool in the result with its version, in the order reported, and the job's API, engine and tool versions

#### Scenario: A tool is missing from the result

- **WHEN** the result of a succeeded `tools` job reports `epa-ng` with a `null` version
- **THEN** the page shows `epa-ng` as not available, and the other tools with their versions

### Requirement: Failed job shows its error

When a job has `failed`, the job page SHALL say that it failed and show the `detail` of the job's error. It MUST NOT show a result.

#### Scenario: A job failed

- **WHEN** the user opens the page of a job that has failed with an error whose `detail` is "The job failed."
- **THEN** the page says the job failed, shows "The job failed.", and shows no result

### Requirement: Job not found or expired

When `GET /api/v1/jobs/{id}` answers 404, because the id is unknown, malformed or the job has expired, the job page SHALL say the job wasn't found and may have expired, and offer a link to the home page. It MUST NOT keep checking the job.

#### Scenario: Unknown or malformed id

- **WHEN** the user opens `/jobs/not-a-job`
- **THEN** the page says the job wasn't found or has expired, and offers a link to `/`

#### Scenario: No further checks

- **WHEN** the job page has shown that a job wasn't found
- **THEN** the UI makes no further requests for that job while the page stays open

### Requirement: Job request failure

When a request for the job fails for any reason other than 404, the job page SHALL say the job couldn't be loaded and offer to try again. It MUST NOT show a status, a result, or build details such as ports, environment variable names, commands or file paths.

#### Scenario: The request fails

- **WHEN** the user opens a job's page and the API answers 500
- **THEN** the page says the job couldn't be loaded, offers to try again, and shows no status, result or build details

#### Scenario: Try again

- **WHEN** the request has failed, the API then answers normally, and the user chooses to try again
- **THEN** the page shows the job

### Requirement: Start a tools check from the home page

The home page SHALL offer an action, secondary to the page's main content, that starts a `tools` job and opens that job's page. While the request to start it is in flight, the action MUST be disabled. If starting fails, the home page MUST say so, with no build details, and stay usable.

#### Scenario: Start a tools check

- **WHEN** the user chooses to check the scoring tools on the home page
- **THEN** a `tools` job is started and the UI shows `/jobs/{id}` for the new job

#### Scenario: While starting

- **WHEN** the user has chosen to check the scoring tools and the API hasn't answered yet
- **THEN** the action is disabled

#### Scenario: Starting fails

- **WHEN** the user chooses to check the scoring tools and the API answers with an error
- **THEN** the home page says the check couldn't be started, shows no build details, stays at `/`, and the action can be chosen again
