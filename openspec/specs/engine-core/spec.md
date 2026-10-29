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
