# Spec Delta

## MODIFIED Requirements

### Requirement: Data sample contents

The cSNP data sample SHALL hold the `.paml`, `.rst` and `.orig.tree` of each chosen family exactly as in the pinned archive, the PANTHER9 BLAST database's `blast.phr`, `blast.pin` and `blast.psq` exactly as in its pinned archive, `species_pthr8_time.nhx`, and the PSEP release's copyright statement, laid out under the cSNP data folder as the full data is. It MUST include `PTHR10366`, `PTHR15126`, `PTHR11711` and `PTHR19241`, `PTHR18976` (the family of the scoring form's example, human APOE), and at least one family for each check the survey found non-zero.

#### Scenario: Golden families

- **WHEN** the sample is unpacked
- **THEN** the sha256 of each `PTHR10366` and `PTHR15126` file starts with the digits in legacy behaviour spec §7.1, and the species tree's sha256 equals the one there

#### Scenario: Every variant

- **WHEN** the survey is run on the sample tarball
- **THEN** every check that is non-zero for the full library is non-zero for the sample

#### Scenario: The whole BLAST database

- **WHEN** the sample is unpacked
- **THEN** each BLAST database file is byte for byte the one in `PANTHER9.blast.tar.gz`, and BLAST+ reports 570,173 sequences in the database

#### Scenario: The form's example family

- **WHEN** the sample is unpacked
- **THEN** it holds `PTHR18976`'s `.paml`, `.rst` and `.orig.tree`, byte for byte as in the pinned PAML_RST archive
