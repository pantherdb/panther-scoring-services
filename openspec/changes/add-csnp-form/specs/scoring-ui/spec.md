# Spec Delta

## ADDED Requirements

### Requirement: cSNP form

The UI SHALL offer a cSNP scoring form at `/csnp`, linked from the home page. It MUST have a sequence box that takes plain residues or FASTA with one header, a substitutions box, and a species box that starts as `HUMAN`. An action MUST fill all three with the legacy website's example input.

#### Scenario: Open the form from the home page

- **WHEN** the user opens `/` and follows the link to cSNP scoring
- **THEN** the UI shows `/csnp`, with an empty sequence box, an empty substitutions box and the species `HUMAN`

#### Scenario: Use the example

- **WHEN** the user chooses to use an example on `/csnp`
- **THEN** the sequence box holds the legacy example's APOE sequence, the substitutions box holds `L46P`, `C130R`, `R163C` and `R176C`, and the species is `HUMAN`

### Requirement: cSNP substitutions split on whitespace

The UI SHALL split the substitutions box into the request's list of tokens at every run of whitespace, spaces, tabs and new lines alike, in the order typed, dropping empty tokens. It MUST NOT split at any other character, as the legacy website didn't.

#### Scenario: Spaces, tabs and new lines

- **WHEN** the substitutions box holds `" L46P  C130R\tR163C\r\nR176C\n"`
- **THEN** the request's `substitutions` is `["L46P", "C130R", "R163C", "R176C"]`

#### Scenario: Other separators are part of a token

- **WHEN** the substitutions box holds `"L46P,C130R"`
- **THEN** the request's `substitutions` is `["L46P,C130R"]`

### Requirement: cSNP form checks the input before sending

Before sending, the cSNP form SHALL check the input against `scoring-input`'s cSNP rules: the sequence, the substitutions as split, each in `<residue><position><residue>` form once upper-cased, and the species. Each broken rule MUST be shown on its field, and no request MUST be sent while any is broken. The form MUST NOT reject an input that the rules accept.

#### Scenario: Empty form

- **WHEN** the user clears the species and submits the form with every box empty
- **THEN** the sequence, substitutions and species fields each show an error, and no request is sent

#### Scenario: Two sequences

- **WHEN** the user submits a sequence with two FASTA headers
- **THEN** the sequence field shows an error, and no request is sent

#### Scenario: Too long

- **WHEN** the user submits a sequence of 50,001 residues, or 1,001 substitutions, or a substitution of 33 characters
- **THEN** the field it's in shows an error, and no request is sent

#### Scenario: Tokens that aren't substitutions

- **WHEN** the user submits the substitutions `L46P XYZ C130R G12|`
- **THEN** the substitutions field shows an error that names substitution 2, `XYZ`, and substitution 4, `G12|`, and no request is sent

#### Scenario: Not a species code

- **WHEN** the user submits the species `human` or `HOMOSAPIENS`
- **THEN** the species field shows an error, and no request is sent

#### Scenario: A valid input is sent

- **WHEN** the user submits a FASTA sequence of 50,000 residues, the substitutions `L46P c130r G99999R`, and the species `PLAF7`
- **THEN** no field shows an error, and the request is sent with that sequence, `["L46P", "c130r", "G99999R"]` and `PLAF7`

### Requirement: Server field errors shown on their fields

When the API answers a cSNP request with a 422 validation problem, the form SHALL show each error's `msg` on the field its `loc` names, and keep the user's input. An error about one substitution MUST name it by its place and by the token as sent, taken from the form's own copy. An error whose `loc` names no field of the form MUST be shown with the form. The UI MUST NOT open a job page.

#### Scenario: The API rejects the species

- **WHEN** the user submits the form and the API answers 422 with an error whose `loc` is `["body", "csnp", "input", "species"]`
- **THEN** the species field shows that error's `msg`, the input is unchanged, and the UI stays at `/csnp`

#### Scenario: The API rejects one substitution

- **WHEN** the user submits the substitutions `L4P c13r G12V` and the API answers 422 with an error whose `loc` is `["body", "csnp", "input", "substitutions", 2]`
- **THEN** the substitutions field shows that error's `msg`, saying it's about substitution 3, `G12V`

#### Scenario: An error on no field

- **WHEN** the API answers 422 with an error whose `loc` is `["body", "csnp", "input", "organism"]`
- **THEN** the form shows that error's `msg` with the form

#### Scenario: Correcting a field

- **WHEN** a field shows an error from the API and the user edits that field
- **THEN** the field no longer shows the error

### Requirement: cSNP scoring not yet available

When the API answers a cSNP request with 501, the form SHALL say that cSNP scoring isn't available yet, in fixed text, keep the user's input, and stay at `/csnp`. When it answers with any other error, the form MUST say the job couldn't be started, in fixed text with no status code or build details, and stay usable.

#### Scenario: The API answers 501

- **WHEN** the user submits a valid input and the API answers 501
- **THEN** the form says cSNP scoring isn't available yet, the sequence, substitutions and species are unchanged, and the UI stays at `/csnp`

#### Scenario: The API answers 500

- **WHEN** the user submits a valid input and the API answers 500
- **THEN** the form says the job couldn't be started, shows no status code or build details, stays at `/csnp`, and can be submitted again

### Requirement: Submitting a cSNP request opens its job

When the API accepts a cSNP request with 202, the UI SHALL open `/jobs/{id}` for the new job. While the request is in flight, the submit action MUST be disabled.

#### Scenario: The API accepts the request

- **WHEN** the user submits a valid input and the API answers 202 with a `csnp` job
- **THEN** the UI shows `/jobs/{id}` for that job

#### Scenario: While submitting

- **WHEN** the user has submitted a valid input and the API hasn't answered yet
- **THEN** the submit action is disabled

### Requirement: cSNP results on the job page

When a `csnp` job has succeeded, the job page SHALL show its PANTHER family, or say there is no PANTHER family when `family` is `null`, and a table with one row per score, in the order given: the substitution, the age in millions of years, the message, and the pDel, each exactly as the API gives it. A `null` age or pDel MUST be shown as empty, not as zero. The job's versions MUST be shown with it.

#### Scenario: A scored job

- **WHEN** the user opens the page of a succeeded `csnp` job whose family is `PTHR00000`
- **THEN** the page shows `PTHR00000`, each score's substitution, age, message and pDel in the order given, and the job's API, engine and tool versions

#### Scenario: A substitution that wasn't scored

- **WHEN** a score has the message "Not scored: Invalid substitution", a `null` age and a `null` pDel
- **THEN** its row shows the substitution and that message, and shows its age and pDel as empty

#### Scenario: No family

- **WHEN** the user opens the page of a succeeded `csnp` job whose family is `null`
- **THEN** the page says there is no PANTHER family, and still shows the scores
