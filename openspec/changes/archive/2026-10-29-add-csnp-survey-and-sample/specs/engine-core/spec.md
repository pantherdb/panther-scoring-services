# Spec Delta

## ADDED Requirements

### Requirement: Data folder

The engine SHALL read its data from the folder named by `PANTHER_DATA_DIR`, with each service's data under `<service>/<version>/`. cSNP's frozen PANTHER 9 data is under `csnp/9/`. When `PANTHER_DATA_DIR` isn't set, an engine command that needs data MUST stop with an error that names the variable.

#### Scenario: Folder set

- **WHEN** `PANTHER_DATA_DIR` is `/data` and an engine command reads cSNP data
- **THEN** it reads it from `/data/csnp/9/`

#### Scenario: Folder not set

- **WHEN** `PANTHER_DATA_DIR` isn't set and a user runs an engine command that needs data
- **THEN** it exits with a non-zero status and a message naming `PANTHER_DATA_DIR`

### Requirement: Data checked against a checksum manifest

Given a manifest of relative file paths and their sha256 checksums, the engine SHALL report each listed file that is missing from a data folder or whose checksum differs, and MUST pass only when there is none. Files the manifest doesn't list are ignored.

#### Scenario: All files match

- **WHEN** every file in the manifest is present with its checksum
- **THEN** the check passes

#### Scenario: A file differs

- **WHEN** one listed file is missing and another has a different checksum
- **THEN** the check fails and names both files

#### Scenario: Extra files

- **WHEN** the data folder holds the full library and the manifest lists only the sample
- **THEN** the check passes if the listed files match

### Requirement: Tests that need data

Tests that need a service's data SHALL be skipped, and reported as skipped, when the data isn't in the data folder. Where data is required (`PANTHER_REQUIRE_DATA=1`, as in CI), missing data MUST fail those tests instead.

#### Scenario: Without the data

- **WHEN** the test suite runs on a machine without the cSNP data sample
- **THEN** the tests that need it are reported as skipped, with a reason naming the data and `PANTHER_DATA_DIR`, and the rest run

#### Scenario: Data required but missing

- **WHEN** the test suite runs with `PANTHER_REQUIRE_DATA=1` and the cSNP data sample isn't in the data folder
- **THEN** the tests that need it fail and name the missing data

#### Scenario: In CI

- **WHEN** CI runs the engine's tests, natively and in the engine image
- **THEN** the cSNP data sample is in the data folder, data is required, and no test that needs it is skipped

### Requirement: Data in the engine image

The engine's checks run in the engine image with the documented command SHALL see the developer's data folder, `.data/` at the repository root, read-only at `/data`, with `PANTHER_DATA_DIR` set to it.

#### Scenario: Sample fetched

- **WHEN** a developer has fetched the cSNP data sample into `.data/` and runs the documented command from the repository root
- **THEN** the tests that need the sample run against it in the image, and nothing is written to `.data/`
