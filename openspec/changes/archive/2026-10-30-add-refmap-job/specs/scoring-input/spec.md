# Spec Delta

## ADDED Requirements

### Requirement: refmap organism is an organism code

A refmap input SHALL have an `organism` of 1 to 5 upper-case letters or digits, the shape of a UniProt species mnemonic such as `HUMAN`. There MUST be no default: an input without one is rejected. An `organism` of any other shape MUST be rejected, so that it never reaches a file name, a command or a pattern.

#### Scenario: An organism code

- **WHEN** a refmap input's `organism` is `HUMAN`, `ECOLI` or `9BACT`
- **THEN** it is accepted

#### Scenario: Not an organism code

- **WHEN** a refmap input's `organism` is `human`, `../../etc/passwd`, `HUMAN|`, `Homo_sapiens_HUMAN` or an empty string
- **THEN** it is rejected, with an error on `organism`, and the error doesn't contain the value

#### Scenario: No organism

- **WHEN** a refmap input has no `organism`
- **THEN** it is rejected, with an error on `organism`

### Requirement: refmap IDs are a list of identifiers

A refmap input's `ids` SHALL be a list of 1 to 100,000 identifiers. Each MUST be 1 to 64 printable ASCII characters without whitespace. The identifiers MUST reach the mapping as submitted: not trimmed, not case-changed, not de-duplicated and in the order given.

#### Scenario: Identifiers kept as submitted

- **WHEN** a refmap input's `ids` is `["P04217", "p04217", "P04217", "P04217-2"]`
- **THEN** it is accepted, and the identifiers mapped are those four, unchanged and in that order

#### Scenario: Most identifiers

- **WHEN** a refmap input's `ids` has 100,000 identifiers
- **THEN** it is accepted

#### Scenario: Too many identifiers

- **WHEN** a refmap input's `ids` has 100,001 identifiers
- **THEN** it is rejected, with an error on `ids`

#### Scenario: No identifiers

- **WHEN** a refmap input's `ids` is `[]`
- **THEN** it is rejected, with an error on `ids`

#### Scenario: An identifier that isn't one identifier

- **WHEN** a refmap input's `ids` is `["P04217", "P04217 P01023"]`, or has an empty string, an identifier with a tab or a trailing space, one of 65 characters, or one with a character outside printable ASCII
- **THEN** it is rejected, with an error on that item of `ids`, and the error doesn't contain the identifier
