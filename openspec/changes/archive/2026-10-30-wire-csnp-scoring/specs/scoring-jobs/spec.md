# Spec Delta

## ADDED Requirements

### Requirement: cSNP job scores with the engine

A valid `csnp` job request SHALL get status 202 and a job, whose work scores the input with the engine's cSNP scoring, with the sequence, substitutions and species as `scoring-input` normalised them. The job MUST succeed with the engine's family and scores, unchanged and in the order submitted. A substitution the engine doesn't score is a row of the result, not a failure.

#### Scenario: A sample protein

- **WHEN** a client submits a `csnp` job for the release sample's protein P26439, with the substitutions `A10E`, `G15D` and `S213G` and the species `HUMAN`, and polls it until it finishes
- **THEN** the job has status `succeeded`, `family` `PTHR10366`, and the scores `A10E` 220 "possibly damaging" "0.50", `G15D` 4200 "probably damaging" "0.95" and `S213G` 91 "probably benign" "0.19", as spec §7.3 gives them

#### Scenario: Every sample protein matches the goldens

- **WHEN** a client submits a `csnp` job for each protein of the release sample, with its substitutions from `sample.input`, where `blastp` and the cSNP data sample are available
- **THEN** each job succeeds with the family and the scores of its rows in spec §7.3

#### Scenario: A substitution that isn't scored

- **WHEN** a `csnp` job's substitutions include `M1V` for P26439
- **THEN** the job succeeds, and that score has the message "Not scored: Invalid substitution", a `null` `age` and a `null` `pdel`

#### Scenario: No family

- **WHEN** a client submits a `csnp` job for P26439 with the species `PLAF7`
- **THEN** the job succeeds with a `null` `family`, and each score has the message "Not scored: No PANTHER family for input sequence"

#### Scenario: A sequence the engine can't read

- **WHEN** a client submits a `csnp` job whose sequence is `1234567890`
- **THEN** the job ends with status `failed`, a `null` `result`, and an `error` with status 422 whose `detail` says the sequence can't be read as a protein sequence

#### Scenario: The data isn't there

- **WHEN** the API runs without the cSNP data and a client submits a valid `csnp` job
- **THEN** the job ends with status `failed` and an `error` with status 500 and the generic `detail`

## REMOVED Requirements

### Requirement: cSNP scoring not available yet

**Reason**: The engine scores cSNP now (`port-csnp`), and the API calls it: a valid `csnp` request starts a job instead of getting a 501.

**Migration**: Submit a `csnp` job and poll it, as for every job. A client that handled the 501 drops that case; the frontend's form has. The schema no longer lists a 501 on `POST /api/v1/jobs`.
