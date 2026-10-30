# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: cSNP scoring not yet available`
- TO: `### Requirement: cSNP job not started`

## MODIFIED Requirements

### Requirement: cSNP job not started

When the API answers a cSNP request with an error other than a 422 validation problem with field errors, the form SHALL say the job couldn't be started, in fixed text with no status code or build details, keep the user's input, stay at `/csnp`, and stay usable. No status, including 501, MUST get a message of its own.

#### Scenario: The API answers 500

- **WHEN** the user submits a valid input and the API answers 500
- **THEN** the form says the job couldn't be started, shows no status code or build details, stays at `/csnp`, and can be submitted again

#### Scenario: The API answers 501

- **WHEN** the user submits a valid input and the API answers 501
- **THEN** the form says the job couldn't be started, as for any other error, the sequence, substitutions and species are unchanged, and the UI stays at `/csnp`

### Requirement: Versions on every page

Every page SHALL show the API version, the engine version, each external tool with its version, and each service's data with the PANTHER release the API names for it, as `GET /api/v1/versions` reports them and in the order reported, so a result can be traced to what produced it. A tool with a `null` version MUST be shown as not available, not left out. If the versions can't be loaded, the page MUST say so instead of showing an empty list, and the rest of the page MUST still work.

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

#### Scenario: Each service's data

- **WHEN** the user opens `/` and the API reports the data `[{"service": "csnp", "panther": "10"}]`
- **THEN** the page shows cSNP's data as PANTHER 10, after the tools, and no other PANTHER release for it

### Requirement: cSNP results on the job page

When a `csnp` job has succeeded, the job page SHALL show its PANTHER family, or say there is no PANTHER family when `family` is `null`, and a table with one row per score, in the order given: the substitution, the age in millions of years, the message, and the pDel, each exactly as the API gives it. A `null` age or pDel MUST be shown as empty, not as zero. The job's versions MUST be shown with it, including the PANTHER release of its data, as the job reports it.

#### Scenario: A scored job

- **WHEN** the user opens the page of a succeeded `csnp` job whose family is `PTHR00000`
- **THEN** the page shows `PTHR00000`, each score's substitution, age, message and pDel in the order given, and the job's API, engine, tool and data versions

#### Scenario: A substitution that wasn't scored

- **WHEN** a score has the message "Not scored: Invalid substitution", a `null` age and a `null` pDel
- **THEN** its row shows the substitution and that message, and shows its age and pDel as empty

#### Scenario: No family

- **WHEN** the user opens the page of a succeeded `csnp` job whose family is `null`
- **THEN** the page says there is no PANTHER family, and still shows the scores

#### Scenario: The job's own data version

- **WHEN** the user opens the page of a succeeded `csnp` job whose versions report cSNP's data as PANTHER 8, while the API now reports PANTHER 9
- **THEN** the job's versions show PANTHER 8, not PANTHER 9

#### Scenario: Real scores

- **WHEN** the user submits the release sample's protein P26439 with the substitutions `A10E G15D S213G` to the API with the cSNP data sample
- **THEN** the job page shows `PTHR10366` and the rows `A10E` 220 "possibly damaging" 0.50, `G15D` 4200 "probably damaging" 0.95 and `S213G` 91 "probably benign" 0.19
