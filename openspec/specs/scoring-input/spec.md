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

### Requirement: refmap IDs are a list of identifiers

A refmap input's `ids` SHALL be a list of 1 to 100,000 identifiers. Each MUST be 1 to 64 printable ASCII characters without whitespace. The identifiers MUST reach the mapping as submitted: not trimmed, not case-changed, not de-duplicated and in the order given.

#### Scenario: Identifiers kept as submitted

- **WHEN** a refmap input's `ids` is `["P04217", "p04217", "P04217", "P04217-2"]`
- **THEN** it is accepted, and the identifiers mapped are those four, unchanged and in that order

#### Scenario: Most identifiers

- **WHEN** a refmap input's `ids` has 100,000 identifiers
- **THEN** it is accepted

#### Scenario: Too many identifiers

- **WHEN** a refmap input's `ids` has 100,001 identifiers
- **THEN** it is rejected, with an error on `ids`

#### Scenario: No identifiers

- **WHEN** a refmap input's `ids` is `[]`
- **THEN** it is rejected, with an error on `ids`

#### Scenario: An identifier that isn't one identifier

- **WHEN** a refmap input's `ids` is `["P04217", "P04217 P01023"]`, or has an empty string, an identifier with a tab or a trailing space, one of 65 characters, or one with a character outside printable ASCII
- **THEN** it is rejected, with an error on that item of `ids`, and the error doesn't contain the identifier

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
