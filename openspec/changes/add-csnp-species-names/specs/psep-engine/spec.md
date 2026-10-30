# Spec Delta

## ADDED Requirements

### Requirement: Species names

The engine SHALL publish a name for each species code it scores against: the name the old site's cSNP list gives that code (`CSNP_SHORT_LONG_ORG_LIST` in `panther-site-java`'s `OrganismConstants.java`), as written there. It MUST publish a name for exactly the codes it scores against, and a caller MUST NOT be able to change the names.

#### Scenario: A name for every code

- **WHEN** the published names are compared with the published species codes
- **THEN** there is one name for each of the 85 codes, and no name for any other code

#### Scenario: The old site's names

- **WHEN** the names of `HUMAN`, `PLAF7`, `SYNY3` and `CANFA` are looked up
- **THEN** they are `Homo sapiens`, `Plasmodium falciparum`, `Synechocystis` and `Canis familiaris`, as the old site's list has them

#### Scenario: Read-only

- **WHEN** a caller tries to change a name, or to add one
- **THEN** it fails, and the names are unchanged
