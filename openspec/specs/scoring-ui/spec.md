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

### Requirement: cSNP form

The UI SHALL offer a cSNP scoring form at `/csnp`, linked from the home page. It MUST have a sequence box that takes plain residues or FASTA with one header, a substitutions box, and a species box that starts as `HUMAN`. An action MUST fill all three with the legacy website's example input.

#### Scenario: Open the form from the home page

- **WHEN** the user opens `/` and follows the link to cSNP scoring
- **THEN** the UI shows `/csnp`, with an empty sequence box, an empty substitutions box and the species `HUMAN`

#### Scenario: Use the example

- **WHEN** the user chooses to use an example on `/csnp`
- **THEN** the sequence box holds the legacy example's APOE sequence, the substitutions box holds `L46P`, `C130R`, `R163C` and `R176C`, and the species is `HUMAN`

### Requirement: cSNP substitutions split on whitespace

The UI SHALL split the substitutions box into the request's list of tokens at every run of whitespace, spaces, tabs and new lines alike, in the order typed, dropping empty tokens. It MUST NOT split at any other character, as the legacy website didn't.

#### Scenario: Spaces, tabs and new lines

- **WHEN** the substitutions box holds `" L46P  C130R\tR163C\r\nR176C\n"`
- **THEN** the request's `substitutions` is `["L46P", "C130R", "R163C", "R176C"]`

#### Scenario: Other separators are part of a token

- **WHEN** the substitutions box holds `"L46P,C130R"`
- **THEN** the request's `substitutions` is `["L46P,C130R"]`

### Requirement: cSNP form checks the input before sending

Before sending, the cSNP form SHALL check the input against `scoring-input`'s cSNP rules: the sequence, the substitutions as split, each in `<residue><position><residue>` form once upper-cased, and the species. Each broken rule MUST be shown on its field, and no request MUST be sent while any is broken. The form MUST NOT reject an input that the rules accept.

#### Scenario: Empty form

- **WHEN** the user clears the species and submits the form with every box empty
- **THEN** the sequence, substitutions and species fields each show an error, and no request is sent

#### Scenario: Two sequences

- **WHEN** the user submits a sequence with two FASTA headers
- **THEN** the sequence field shows an error, and no request is sent

#### Scenario: Too long

- **WHEN** the user submits a sequence of 50,001 residues, or 1,001 substitutions, or a substitution of 33 characters
- **THEN** the field it's in shows an error, and no request is sent

#### Scenario: Tokens that aren't substitutions

- **WHEN** the user submits the substitutions `L46P XYZ C130R G12|`
- **THEN** the substitutions field shows an error that names substitution 2, `XYZ`, and substitution 4, `G12|`, and no request is sent

#### Scenario: Not a species code

- **WHEN** the user submits the species `human` or `HOMOSAPIENS`
- **THEN** the species field shows an error, and no request is sent

#### Scenario: A valid input is sent

- **WHEN** the user submits a FASTA sequence of 50,000 residues, the substitutions `L46P c130r G99999R`, and the species `PLAF7`
- **THEN** no field shows an error, and the request is sent with that sequence, `["L46P", "c130r", "G99999R"]` and `PLAF7`

### Requirement: Server field errors shown on their fields

When the API answers a cSNP request with a 422 validation problem, the form SHALL show each error's `msg` on the field its `loc` names, and keep the user's input. An error about one substitution MUST name it by its place and by the token as sent, taken from the form's own copy. An error whose `loc` names no field of the form MUST be shown with the form. The UI MUST NOT open a job page.

#### Scenario: The API rejects the species

- **WHEN** the user submits the form and the API answers 422 with an error whose `loc` is `["body", "csnp", "input", "species"]`
- **THEN** the species field shows that error's `msg`, the input is unchanged, and the UI stays at `/csnp`

#### Scenario: The API rejects one substitution

- **WHEN** the user submits the substitutions `L4P c13r G12V` and the API answers 422 with an error whose `loc` is `["body", "csnp", "input", "substitutions", 2]`
- **THEN** the substitutions field shows that error's `msg`, saying it's about substitution 3, `G12V`

#### Scenario: An error on no field

- **WHEN** the API answers 422 with an error whose `loc` is `["body", "csnp", "input", "organism"]`
- **THEN** the form shows that error's `msg` with the form

#### Scenario: Correcting a field

- **WHEN** a field shows an error from the API and the user edits that field
- **THEN** the field no longer shows the error

### Requirement: cSNP scoring not yet available

When the API answers a cSNP request with 501, the form SHALL say that cSNP scoring isn't available yet, in fixed text, keep the user's input, and stay at `/csnp`. When it answers with any other error, the form MUST say the job couldn't be started, in fixed text with no status code or build details, and stay usable.

#### Scenario: The API answers 501

- **WHEN** the user submits a valid input and the API answers 501
- **THEN** the form says cSNP scoring isn't available yet, the sequence, substitutions and species are unchanged, and the UI stays at `/csnp`

#### Scenario: The API answers 500

- **WHEN** the user submits a valid input and the API answers 500
- **THEN** the form says the job couldn't be started, shows no status code or build details, stays at `/csnp`, and can be submitted again

### Requirement: An unreachable scoring service is named as such

When a request to start or load a job gets no answer from the API (the network fails, or what answers isn't the API: the development proxy with no API behind it, or a server answering 502, 503 or 504), the cSNP form, the tools check and the job page SHALL say that the scoring service can't be reached, in fixed text with no status code or build details, instead of the message for an error from the API. The user's input MUST be kept, and the action MUST be possible to try again.

#### Scenario: The network fails while submitting the cSNP form

- **WHEN** the user submits a valid cSNP input and the request fails with a network error
- **THEN** the form says the scoring service can't be reached, keeps the input, stays at `/csnp`, and can be submitted again

#### Scenario: The development proxy has no API behind it

- **WHEN** the user clicks the tools check and the answer is a 500 without problem details
- **THEN** the home page says the scoring service can't be reached, and the button can be clicked again

#### Scenario: The job page can't reach the API

- **WHEN** the job page loads a job and the request fails with a network error
- **THEN** the page says the scoring service can't be reached, shows no status code or build details, and offers to try again

#### Scenario: An error from the API is not called unreachable

- **WHEN** the API itself answers 500 with problem details
- **THEN** the UI says the job couldn't be started or loaded, not that the service can't be reached

### Requirement: Submitting a cSNP request opens its job

When the API accepts a cSNP request with 202, the UI SHALL open `/jobs/{id}` for the new job. While the request is in flight, the submit action MUST be disabled.

#### Scenario: The API accepts the request

- **WHEN** the user submits a valid input and the API answers 202 with a `csnp` job
- **THEN** the UI shows `/jobs/{id}` for that job

#### Scenario: While submitting

- **WHEN** the user has submitted a valid input and the API hasn't answered yet
- **THEN** the submit action is disabled

### Requirement: cSNP results on the job page

When a `csnp` job has succeeded, the job page SHALL show its PANTHER family, or say there is no PANTHER family when `family` is `null`, and a table with one row per score, in the order given: the substitution, the age in millions of years, the message, and the pDel, each exactly as the API gives it. A `null` age or pDel MUST be shown as empty, not as zero. The job's versions MUST be shown with it.

#### Scenario: A scored job

- **WHEN** the user opens the page of a succeeded `csnp` job whose family is `PTHR00000`
- **THEN** the page shows `PTHR00000`, each score's substitution, age, message and pDel in the order given, and the job's API, engine and tool versions

#### Scenario: A substitution that wasn't scored

- **WHEN** a score has the message "Not scored: Invalid substitution", a `null` age and a `null` pDel
- **THEN** its row shows the substitution and that message, and shows its age and pDel as empty

#### Scenario: No family

- **WHEN** the user opens the page of a succeeded `csnp` job whose family is `null`
- **THEN** the page says there is no PANTHER family, and still shows the scores
