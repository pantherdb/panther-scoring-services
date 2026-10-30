# scoring-input Specification

## Purpose

The rules a scoring service's input must meet before any scoring starts: which values are accepted, how they are normalised, and which are rejected. The UI and the API share them, so the form rejects what the API would, and each service adds its own rules when it's ported.

## Requirements

### Requirement: cSNP sequence normalised as the website did

A cSNP input's `sequence` SHALL be normalised before scoring, as the legacy PANTHER website's form did: leading and trailing whitespace removed, then one FASTA header line at the start removed, then all remaining whitespace removed, then letters upper-cased. Scoring MUST receive the normalised sequence.

#### Scenario: FASTA header and line breaks

- **WHEN** a cSNP input's `sequence` is `">sp|P02649|APOE_HUMAN Apolipoprotein E\nMKVLWAALLV\nTFLAGCQAKV\n"`
- **THEN** it is accepted, and the sequence scored is `MKVLWAALLVTFLAGCQAKV`

#### Scenario: Lower case and spaces

- **WHEN** a cSNP input's `sequence` is `"  mkvl waal\r\n"`
- **THEN** it is accepted, and the sequence scored is `MKVLWAAL`

### Requirement: cSNP sequence rejected when it can't be one protein

A cSNP input SHALL be rejected when its `sequence`, after normalising, is empty, is longer than 50,000 residues, or contains a character outside printable ASCII. It MUST also be rejected when the submitted `sequence` contains more than one `>`, since that is more than one sequence, or is longer than 1,000,000 characters before normalising.

#### Scenario: Only a header

- **WHEN** a cSNP input's `sequence` is `">only a header"`
- **THEN** it is rejected, with an error on `sequence`

#### Scenario: Two sequences

- **WHEN** a cSNP input's `sequence` is `">one\nMKV\n>two\nMKV"`
- **THEN** it is rejected, with an error on `sequence`

#### Scenario: Longest sequence

- **WHEN** a cSNP input's `sequence` has 50,000 residues after normalising
- **THEN** it is accepted

#### Scenario: Too long

- **WHEN** a cSNP input's `sequence` has 50,001 residues after normalising
- **THEN** it is rejected, with an error on `sequence`

#### Scenario: Not printable ASCII

- **WHEN** a cSNP input's `sequence` is `"MKVÄL"`, or `"MKV\u0000L"` with a control character inside it
- **THEN** it is rejected, with an error on `sequence`

### Requirement: cSNP substitutions are a list of tokens

A cSNP input's `substitutions` SHALL be a list of 1 to 1,000 tokens. Each token MUST be 1 to 32 printable ASCII characters and, once upper-cased, MUST be a residue letter, a position and a residue letter (`[A-Z][0-9]+[A-Z]`). A token in that form MUST NOT be rejected because it can't be mapped onto the sequence: that is decided per substitution in the result.

#### Scenario: Valid tokens, upper-cased

- **WHEN** a cSNP input's `substitutions` is `["L46P", "c130r"]`
- **THEN** it is accepted, and the substitutions scored are `L46P` and `C130R`, in that order

#### Scenario: Tokens that aren't substitutions are rejected

- **WHEN** a cSNP input's `substitutions` is `["L46P", "XYZ"]`
- **THEN** it is rejected, with an error on the second item of `substitutions`, and the error doesn't contain `XYZ`

#### Scenario: Substitutions that can't be mapped are accepted

- **WHEN** a cSNP input's `substitutions` is `["G99999R", "M1P"]`
- **THEN** it is accepted, and both are scored, in that order

#### Scenario: No substitutions

- **WHEN** a cSNP input's `substitutions` is `[]`
- **THEN** it is rejected, with an error on `substitutions`

#### Scenario: Too many substitutions

- **WHEN** a cSNP input's `substitutions` has 1,001 tokens
- **THEN** it is rejected, with an error on `substitutions`

#### Scenario: A token that isn't one token

- **WHEN** a cSNP input's `substitutions` is `["L46P C130R"]`, `[""]`, or a token of 33 characters
- **THEN** it is rejected, with an error on that token of `substitutions`

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
