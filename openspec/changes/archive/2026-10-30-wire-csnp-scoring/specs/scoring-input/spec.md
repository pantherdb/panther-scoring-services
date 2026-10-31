# Spec Delta

## MODIFIED Requirements

### Requirement: cSNP species is a species code

A cSNP input SHALL have a `species` of 1 to 5 upper-case letters or digits, the shape of a PANTHER species mnemonic such as `HUMAN`. There MUST be no default: an input without one is rejected. A `species` of any other shape MUST be rejected, so that it never reaches a file name, a command or a pattern. A `species` of that shape MUST also be one of the species the engine scores against, the species of the PANTHER9 BLAST database; any other is rejected, with an error on `species` that doesn't repeat the value. The API checks this before any job starts; the form may check only the shape, and show the API's error on `species`.

#### Scenario: A species code

- **WHEN** a cSNP input's `species` is `HUMAN`, `RAT` or `PLAF7`
- **THEN** it is accepted

#### Scenario: Not a species code

- **WHEN** a cSNP input's `species` is `human`, `HUMAN; rm -rf /`, `HOMOSAPIENS` or an empty string
- **THEN** it is rejected, with an error on `species`

#### Scenario: No species

- **WHEN** a cSNP input has no `species`
- **THEN** it is rejected, with an error on `species`

#### Scenario: A species the engine doesn't score

- **WHEN** a cSNP input's `species` is `ZZZZZ`, or `XENLA`, a PANTHER species that isn't in the PANTHER9 BLAST database
- **THEN** it is rejected, with one error on `species` that doesn't contain the value

#### Scenario: Rejected before a job starts

- **WHEN** a client sends a `csnp` job request whose `species` is `ZZZZZ`
- **THEN** the API responds with status 422 and one error whose `loc` is `["body", "csnp", "input", "species"]`, no job is created, and the body doesn't contain `ZZZZZ`
