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

#### Scenario: An hmmscore header after a blank line

- **WHEN** an hmmscore input's `sequence` is `"\n  >sp|P02649|APOE_HUMAN\nMKVLWAALLV\n"`
- **THEN** it is accepted, and the sequence scored is `MKVLWAALLV`

### Requirement: hmmscore sequence holds only letters, dots, underscores, tildes and stops

An hmmscore input SHALL be rejected when its `sequence`, after normalising, holds a character other than a letter, `.`, `_`, `~` or `*`, or has no letters. A sequence of only `.`, `_`, `~` and `*`, with no letter, MUST get the error "The sequence has no residues." It MUST also be rejected when the submitted `sequence` contains more than one `>`, or is longer than 1,000,000 characters before normalising. Each error is on `sequence`, doesn't contain the sequence, and comes before any job starts.

#### Scenario: An hmmscore header with no residues

- **WHEN** an hmmscore input's `sequence` is `">only a header"`
- **THEN** it is rejected, with an error on `sequence`

#### Scenario: No letters

- **WHEN** an hmmscore input's `sequence` is `*`, `.`, `~` or `">only a header\n*"`
- **THEN** it is rejected, with the error "The sequence has no residues." on `sequence`

#### Scenario: Two sequences for hmmscore

- **WHEN** an hmmscore input's `sequence` is `">one\nMKV\n>two\nMKV"`
- **THEN** it is rejected, with an error on `sequence`

#### Scenario: A character hmmscan doesn't read

- **WHEN** an hmmscore input's `sequence` is `MKV1L`, `MKV-L`, `MKV+L`, `MKV>LW` or `MKVÄL`
- **THEN** it is rejected, with an error on `sequence` that doesn't contain the sequence

#### Scenario: Characters the two HMMER versions score alike

- **WHEN** an hmmscore input's `sequence` is `MKV*L`, `mkv.l`, `MKV_L`, `MKV~L` or `MKVL**`
- **THEN** it is accepted, and the sequence scored is `MKV*L`, `MKV.L`, `MKV_L`, `MKV~L` or `MKVL**`

#### Scenario: A stop at the end, and the uncommon letters

- **WHEN** an hmmscore input's `sequence` is `"mkvbjouxz*\n"`
- **THEN** it is accepted, and the sequence scored is `MKVBJOUXZ*`

#### Scenario: Too long before normalising

- **WHEN** an hmmscore input's `sequence` is 1,000,001 characters, `M` followed by 1,000,000 spaces, which would normalise to one residue
- **THEN** it is rejected, with an error on `sequence`, and the residue limit isn't what rejects it

### Requirement: hmmscore residue limit

An hmmscore input SHALL be rejected when its normalised `sequence` has more residues than the limit the API is configured with, 10,000 by default and never more. Residues are every position `hmmscan` reads: its letters, `.`, `_`, `~` and `*`, except a final `*`, which isn't counted. The API MUST check it before any job starts, and answer with status 422 and an error on `sequence` that names the limit and doesn't contain the sequence.

#### Scenario: At the default residue limit

- **WHEN** the API runs with the default settings and an hmmscore request's `sequence` has 10,000 residues after normalising
- **THEN** the request passes validation

#### Scenario: A stop after the last residue

- **WHEN** the API runs with the default settings and an hmmscore request's `sequence` is 10,000 letters and a final `*` after normalising
- **THEN** the request passes validation

#### Scenario: Dots and inner stops count

- **WHEN** the API runs with the default settings and an hmmscore request's `sequence` is 9,998 letters followed by `.*~` after normalising, 10,001 residues
- **THEN** the API responds with status 422, with an error on `sequence` whose message names 10,000 residues, and no job is created

#### Scenario: Past the default residue limit

- **WHEN** the API runs with the default settings and an hmmscore request's `sequence` has 10,001 residues after normalising
- **THEN** the API responds with status 422, one error whose `loc` is `["body", "hmmscore", "input", "sequence"]` and whose message names 10,000 residues, and no job is created

#### Scenario: A lower residue limit the server sets

- **WHEN** the API runs with the hmmscore residue limit set to 5,000 and an hmmscore request's `sequence` has 5,000 residues
- **THEN** the request passes validation, and one of 5,001 residues gets the 422, naming 5,000
