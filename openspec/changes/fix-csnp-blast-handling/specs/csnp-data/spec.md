# Spec Delta

## ADDED Requirements

### Requirement: Full data manifest

The engine's command line SHALL build a checksum manifest of the full cSNP data from the pinned PAML_RST archive, the pinned BLAST archive, the species tree and the PSEP release's README, and MUST refuse any of them whose sha256 isn't the pinned one. A build MUST give the same bytes every time. The manifest is committed with the engine.

#### Scenario: Reproducible

- **WHEN** the manifest is built twice from the pinned inputs
- **THEN** the two are byte for byte the same, and the same as the committed manifest

#### Scenario: What it lists

- **WHEN** the manifest is built
- **THEN** it lists, at their paths under the cSNP data folder, every regular file in the PAML_RST archive, the BLAST database's `blast.phr`, `blast.pin` and `blast.psq`, `species_pthr8_time.nhx` and `PSEP-COPYRIGHT.txt`, and it doesn't list `blast.fasta`

#### Scenario: It agrees with the sample

- **WHEN** the committed full manifest is compared with the sample's manifest
- **THEN** every file the sample lists is in the full manifest, with the same sha256

#### Scenario: An archive that isn't pinned

- **WHEN** the build is given a PAML_RST archive whose sha256 differs from the pinned one
- **THEN** nothing is written, and the command exits with a non-zero status naming both checksums

### Requirement: Verifying the full data

`panther-engine csnp data verify` SHALL check the cSNP data folder against the committed full manifest. It MUST print how many listed files are missing and how many differ, name the first 20 of each, and exit with a non-zero status if there is any. Files the manifest doesn't list are ignored.

#### Scenario: The full data

- **WHEN** the full data is installed as `docs/testing/engine.md` says, and the command runs
- **THEN** it reports no missing or differing file, and exits with status 0

#### Scenario: A copy that stopped halfway

- **WHEN** one `.paml` file has been deleted from a full copy and one `.rst` file truncated
- **THEN** the command names both files, and exits with a non-zero status

#### Scenario: Only the sample

- **WHEN** the data folder holds only the sample
- **THEN** the command reports the number of missing files, names only the first 20, and exits with a non-zero status

#### Scenario: Files it doesn't list

- **WHEN** the full data's folder also holds `blast/blast.fasta`
- **THEN** the command ignores it
