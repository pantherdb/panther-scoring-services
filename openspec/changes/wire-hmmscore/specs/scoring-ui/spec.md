# Spec Delta

## ADDED Requirements

### Requirement: An hmmscore job past its time limit on the job page

When an `hmmscore` job has failed past its time limit, with an `error` of status 503, the job page SHALL show the error's `detail` and no result, as for any failed job, and MUST NOT say that the scoring service can't be reached, nor show a status code.

#### Scenario: A job past its time limit

- **WHEN** the user opens the page of an `hmmscore` job that failed with status 503 and the `detail` "The search took longer than this service allows. The server may be busy: try again later, or with a shorter sequence."
- **THEN** the page says the job failed, shows that `detail`, shows no hit or alignment, and doesn't say the scoring service can't be reached

### Requirement: Services marked coming soon

Every service the API can't score yet SHALL be marked "coming soon", in its tab and on the home page: today TreeGrafter. TreeGrafter MUST open a page that says what the service will do, that it's coming soon, and links home.

#### Scenario: The marks

- **WHEN** the user opens any page
- **THEN** the TreeGrafter tab says it's coming soon, and the cSNP scoring, ID mapping and HMM scoring tabs don't

#### Scenario: A service without a form

- **WHEN** the user follows the TreeGrafter tab
- **THEN** a page says TreeGrafter is coming soon, says what it will do, and links home

#### Scenario: HMM scoring's form

- **WHEN** the user follows the HMM scoring tab
- **THEN** the HMM scoring form is shown, HMM scoring is marked as current, and the page has no "coming soon" mark and no notice that HMM scoring isn't available

## MODIFIED Requirements

### Requirement: The home page shows every service

The home page SHALL show the four services, in the tabs' order, each with what it does and the same "coming soon" mark. A service with a form MUST link to it.

#### Scenario: The four services

- **WHEN** the user opens `/`
- **THEN** the page shows cSNP scoring, ID mapping, HMM scoring and TreeGrafter, with links to the cSNP, refmap and HMM scoring forms, and only TreeGrafter marked coming soon

### Requirement: hmmscore submit failures

When the API answers an HMM scoring request with 503 and problem details, the form SHALL say HMM scoring is busy, and when to try again from `Retry-After`, or in a few minutes without it. When the API can't be reached, it MUST say so; for any other error but a 422 or 503, that the job couldn't be started. No message MUST show a status code or build details. The form MUST keep the sequence, stay at `/hmmscore`, and stay usable.

#### Scenario: The API is busy (hmmscore)

- **WHEN** the user submits a valid sequence and the API answers 503 with problem details and `Retry-After: 30`
- **THEN** the form says HMM scoring is busy and to try again in about 30 seconds, with no status code, and the sequence is unchanged

#### Scenario: The API answers 500 (hmmscore)

- **WHEN** the user submits a valid sequence and the API answers 500 with problem details
- **THEN** the form says the job couldn't be started, with no status code or build details

#### Scenario: The API answers 501 (hmmscore)

- **WHEN** the user submits a valid sequence and the API answers 501 with problem details, as an API from before this change did
- **THEN** the form says the job couldn't be started, with no status code, and keeps the sequence

#### Scenario: A 501 from something in between (hmmscore)

- **WHEN** the user submits a valid sequence and the answer is 501 with no problem-details body
- **THEN** the form says the scoring service can't be reached, and keeps the sequence

#### Scenario: The network fails (hmmscore)

- **WHEN** the user submits a valid sequence and the request fails with a network error
- **THEN** the form says the scoring service can't be reached, and keeps the sequence

### Requirement: hmmscore results on the job page

When an `hmmscore` job has succeeded with a hit, the job page SHALL show the hit's PANTHER ID, linking to its page on pantherdb.org, its name, its E-value and its bit score, each exactly as the API gives it, and the alignment. With a `null` hit, the page MUST say there were no hits to PANTHER for the sequence. The job's versions MUST be shown with it, its hmmscore data among them.

#### Scenario: A job with a hit

- **WHEN** the user opens the page of a succeeded `hmmscore` job whose hit is `PTHR00000:SF1`, named "MOCK FAMILY", with E-value `7e-131` and score `439.0`
- **THEN** the page shows `PTHR00000:SF1`, "MOCK FAMILY", `7e-131` and `439.0`, the alignment, and the job's API, engine and tool versions, and its hmmscore data as PANTHER 19

#### Scenario: A job with no hit

- **WHEN** the user opens the page of a succeeded `hmmscore` job whose `hit` is `null`
- **THEN** the page says there were no hits to PANTHER for the sequence, and shows no alignment

#### Scenario: A running hmmscore job

- **WHEN** the user opens the page of a running `hmmscore` job
- **THEN** the page shows no hit and no alignment

## REMOVED Requirements

### Requirement: Services that aren't available yet

**Reason**: HMM scoring is available, so only TreeGrafter is marked, and HMM scoring's scenario changes from "HMM scoring's form while coming soon" to a form with no mark or notice. A MODIFIED block can't drop a scenario, so the requirement is replaced by "Services marked coming soon".

**Migration**: None. "Services marked coming soon" keeps the marks and TreeGrafter's page, and its "HMM scoring's form" scenario replaces "HMM scoring's form while coming soon".

### Requirement: HMM scoring form says it isn't available yet

**Reason**: The API scores HMM scoring requests, so HMM scoring is no longer marked "coming soon", and the form has no notice to show.

**Migration**: None. The form, its checks and its results are unchanged; a submitted sequence now starts a job.

### Requirement: HMM scoring not yet available

**Reason**: The API no longer answers a valid HMM scoring request with `501`, so the form has no "not available yet" message to show.

**Migration**: A `501` with problem details gets the "couldn't be started" message, and one without them the "can't be reached" message, both under "hmmscore submit failures".
