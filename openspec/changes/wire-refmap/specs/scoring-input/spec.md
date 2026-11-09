# Spec Delta

## MODIFIED Requirements

### Requirement: refmap organism is an organism code

A refmap input SHALL have an `organism` that is one of the codes the engine maps for: the UniProt species mnemonic ending one of its organisms' long names, such as `ENDPU` for `Endocarpon_pusillum_ENDPU`. There MUST be no default: an input without one is rejected. Any other value MUST be rejected, whatever its shape, so that it never reaches a file name, a command or a pattern. The error MUST NOT contain the value.

#### Scenario: An organism code

- **WHEN** a refmap input's `organism` is `ENDPU`, `ARAVE` or `ECO57`
- **THEN** it is accepted

#### Scenario: A code the engine doesn't map for

- **WHEN** a refmap input's `organism` is `HUMAN`, `ECOLI` or `ZZZZZ`, codes of the right shape that aren't among the engine's organisms
- **THEN** it is rejected, with an error on `organism`, and the error doesn't contain the value

#### Scenario: Not an organism code

- **WHEN** a refmap input's `organism` is `endpu`, `../../etc/passwd`, `ENDPU|`, `Endocarpon_pusillum_ENDPU` or an empty string
- **THEN** it is rejected, with an error on `organism`, and the error doesn't contain the value

#### Scenario: No organism

- **WHEN** a refmap input has no `organism`
- **THEN** it is rejected, with an error on `organism`
