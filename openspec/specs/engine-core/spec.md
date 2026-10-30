# engine-core Specification

## Purpose

Behaviour every service in the PANTHER scoring engine shares, whichever service it belongs to: the command line, the pinned external tools, and how the engine finds them, reports their versions and runs them safely.

## Requirements

### Requirement: Engine version on the command line

The engine's command line SHALL print the engine's version and exit with status 0 when given `--version`. It MUST do the same whether it is run as the installed `panther-engine` command or as the Python module.

#### Scenario: Installed command

- **WHEN** a user runs `panther-engine --version`
- **THEN** it prints the installed engine version and exits with status 0

#### Scenario: Run as a module

- **WHEN** a user runs `python -m panther_engine --version`
- **THEN** it prints the same version as the installed command and exits with status 0

### Requirement: External tool report

The engine's command line SHALL list each external tool the engine uses (`blastp` from BLAST+, `hmmscan` and `hmmsearch` from HMMER, and `epa-ng`) with the version that tool reports. It MUST exit with status 0 only when every tool is found.

#### Scenario: All tools present

- **WHEN** a user runs `panther-engine tools` where every tool is installed
- **THEN** it prints one line per tool with the tool's name and version, and exits with status 0

#### Scenario: A tool is missing

- **WHEN** a user runs `panther-engine tools` where `epa-ng` is not installed
- **THEN** it reports `epa-ng` as not found, still reports the other tools, and exits with a non-zero status

### Requirement: External tools run without a shell

The engine SHALL start every external tool from its program path with a list of arguments, never through a shell. An argument MUST reach the tool unchanged, as one argument, whatever characters it contains.

#### Scenario: Shell metacharacters in an argument

- **WHEN** the engine runs a tool with an argument containing `; touch marker` and other shell metacharacters
- **THEN** the tool receives that exact text as a single argument, and no file named `marker` is created

### Requirement: Pinned tools in the engine image

The engine image SHALL contain BLAST+ 2.17.0, HMMER 3.4 and EPA-ng 0.3.8, and no other versions of them. The engine's tool report, run inside the image, MUST show exactly these versions.

#### Scenario: Tool report in the image

- **WHEN** `panther-engine tools` runs inside the engine image
- **THEN** it reports `blastp` 2.17.0, `hmmscan` and `hmmsearch` 3.4, and `epa-ng` 0.3.8, and exits with status 0

### Requirement: Image for both CPU architectures

The engine image SHALL build for `linux/amd64` and `linux/arm64`, and run natively on both, with the same tool versions.

#### Scenario: Each architecture

- **WHEN** the engine image is built for `linux/amd64` and for `linux/arm64`
- **THEN** both builds succeed, and the engine's tool tests pass in each, run natively on a machine of that architecture

### Requirement: Engine checks run in the image

A developer SHALL be able to run the engine's lint, format, type and test checks inside the engine image with one documented command from the repository root, on any machine with Docker. Files written by those checks MUST NOT conflict with the developer's own environment for `engine/`.

#### Scenario: Checks in the image

- **WHEN** a developer runs the documented command from a fresh clone
- **THEN** the lint, format, type and test checks run in the engine image against the working copy of `engine/`, and pass

#### Scenario: Local environment untouched

- **WHEN** a developer who also has a local environment for `engine/` runs the checks in the image
- **THEN** their local environment still works afterwards

### Requirement: Tests that need the tools

Tests that need the external tools SHALL be skipped, and reported as skipped, when the tools are not installed. Where the tools are required, as in the engine image, a missing tool MUST fail those tests instead of skipping them.

#### Scenario: Outside the image

- **WHEN** the test suite runs on a machine without the external tools
- **THEN** the tests that need them are reported as skipped and the rest run

#### Scenario: Inside the image with a tool missing

- **WHEN** the test suite runs where the tools are required and one tool cannot be found
- **THEN** the tests that need that tool fail and name the missing tool

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
