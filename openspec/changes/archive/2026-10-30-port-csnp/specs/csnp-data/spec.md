# Spec Delta

## MODIFIED Requirements

### Requirement: Data sample contents

The cSNP data sample SHALL hold the `.paml`, `.rst` and `.orig.tree` of each chosen family exactly as in the pinned archive, the PANTHER9 BLAST database's `blast.phr`, `blast.pin` and `blast.psq` exactly as in its pinned archive, `species_pthr8_time.nhx`, and the PSEP release's copyright statement, laid out under the cSNP data folder as the full data is. It MUST include `PTHR10366`, `PTHR15126`, `PTHR11711` and `PTHR19241`, and at least one family for each check the survey found non-zero.

#### Scenario: Golden families

- **WHEN** the sample is unpacked
- **THEN** the sha256 of each `PTHR10366` and `PTHR15126` file starts with the digits in legacy behaviour spec §7.1, and the species tree's sha256 equals the one there

#### Scenario: Every variant

- **WHEN** the survey is run on the sample tarball
- **THEN** every check that is non-zero for the full library is non-zero for the sample

#### Scenario: The whole BLAST database

- **WHEN** the sample is unpacked
- **THEN** each BLAST database file is byte for byte the one in `PANTHER9.blast.tar.gz`, and BLAST+ reports 570,173 sequences in the database

### Requirement: Building the sample

The engine's command line SHALL build the sample tarball from the PAML_RST archive, the PANTHER9 BLAST archive, the species tree and a list of families. The same inputs MUST give a byte-identical tarball. It MUST refuse either archive when its sha256 isn't the one pinned in legacy behaviour spec §7.1, and then write nothing.

#### Scenario: Reproducible

- **WHEN** the sample is built twice from the same inputs
- **THEN** the two tarballs are byte-identical

#### Scenario: Wrong archive

- **WHEN** the build is given a PAML_RST or BLAST archive whose sha256 differs from the pinned one
- **THEN** it exits with a non-zero status naming both checksums, and writes no tarball
