# Spec Delta

## ADDED Requirements

### Requirement: hmmscore sequence normalised as cSNP's is

An hmmscore input's `sequence` SHALL be normalised before scoring as a cSNP input's is: leading and trailing whitespace removed, then one FASTA header line at the start removed, then all remaining whitespace removed, then letters upper-cased. Scoring MUST receive the normalised sequence.

#### Scenario: An hmmscore FASTA sequence

- **WHEN** an hmmscore input's `sequence` is `">sp|P02649|APOE_HUMAN Apolipoprotein E\nMKVLWAALLV\nTFLAGCQAKV\n"`
- **THEN** it is accepted, and the sequence scored is `MKVLWAALLVTFLAGCQAKV`

#### Scenario: An hmmscore sequence in lower case with spaces

- **WHEN** an hmmscore input's `sequence` is `"  mkvl waal\r\n"`
- **THEN** it is accepted, and the sequence scored is `MKVLWAAL`

### Requirement: hmmscore sequence rejected when it can't be one protein

An hmmscore input SHALL be rejected when its `sequence`, after normalising, is empty, is longer than 50,000 residues, or contains a character outside printable ASCII. It MUST also be rejected when the submitted `sequence` contains more than one `>`, or is longer than 1,000,000 characters before normalising. Each error is on `sequence`, and doesn't contain the sequence.

#### Scenario: An hmmscore header with no residues

- **WHEN** an hmmscore input's `sequence` is `">only a header"`
- **THEN** it is rejected, with an error on `sequence`

#### Scenario: Two sequences for hmmscore

- **WHEN** an hmmscore input's `sequence` is `">one\nMKV\n>two\nMKV"`
- **THEN** it is rejected, with an error on `sequence`

#### Scenario: An hmmscore sequence with a character outside printable ASCII

- **WHEN** an hmmscore input's `sequence` is `"MKVÄL"`, or `"MKV\u0000L"` with a control character inside it
- **THEN** it is rejected, with an error on `sequence`

#### Scenario: An hmmscore sequence past the website's limit

- **WHEN** an hmmscore input's `sequence` has 50,001 residues after normalising
- **THEN** it is rejected, with an error on `sequence`, whatever the configured residue limit

### Requirement: hmmscore residue limit

An hmmscore input SHALL be rejected when its normalised `sequence` is longer than the residue limit the API is configured with, 5,000 by default and never more than 50,000. The API MUST check it before any job starts, and answer with status 422 and an error on `sequence` that names the limit and doesn't contain the sequence.

#### Scenario: At the default residue limit

- **WHEN** the API runs with the default settings and an hmmscore request's `sequence` has 5,000 residues after normalising
- **THEN** the request passes validation

#### Scenario: Past the default residue limit

- **WHEN** the API runs with the default settings and an hmmscore request's `sequence` has 5,001 residues after normalising
- **THEN** the API responds with status 422, one error whose `loc` is `["body", "hmmscore", "input", "sequence"]` and whose message names 5,000 residues, and no job is created

#### Scenario: A residue limit the server sets

- **WHEN** the API runs with the hmmscore residue limit set to 20,000 and an hmmscore request's `sequence` has 20,000 residues
- **THEN** the request passes validation, and one of 20,001 residues gets the 422
