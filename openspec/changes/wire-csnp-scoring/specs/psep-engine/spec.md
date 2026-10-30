# Spec Delta

## ADDED Requirements

### Requirement: Data version

The engine SHALL publish the PANTHER release of the data cSNP scoring reads, as `DATA_VERSION` from `panther_engine.csnp`. It MUST be the release whose folder scoring reads, `csnp/<release>/` under the data folder, so the two can't disagree. Reading it MUST NOT need the data folder.

#### Scenario: cSNP's release

- **WHEN** a caller reads `DATA_VERSION` from `panther_engine.csnp`, with `PANTHER_DATA_DIR` unset
- **THEN** it is `"9"`, the release of the `csnp/9/` folder scoring reads
