# Spec Delta

## MODIFIED Requirements

### Requirement: cSNP form

The UI SHALL offer a cSNP scoring form at `/csnp`, linked from the home page. It MUST have a sequence box that takes plain residues or FASTA with one header, a substitutions box, and a species selector that starts as `HUMAN`. The selector MUST offer the species the API lists for cSNP, each shown by its name and its code, such as "Homo sapiens (HUMAN)", and none it doesn't list. Typing part of a name or of a code MUST narrow the options to the species that match, in any letter case. The selector MUST have a label, and MUST be usable with the keyboard alone. Whatever the selector shows, the request MUST send the species' code. An action MUST fill all three with the legacy website's example input.

#### Scenario: Open the form from the home page

- **WHEN** the user opens `/` and follows the link to cSNP scoring
- **THEN** the UI shows `/csnp`, with an empty sequence box, an empty substitutions box and the species "Homo sapiens (HUMAN)"

#### Scenario: Use the example

- **WHEN** the user has chosen another species and chooses to use an example on `/csnp`
- **THEN** the sequence box holds the legacy example's APOE sequence, the substitutions box holds `L46P`, `C130R`, `R163C` and `R176C`, and the species is "Homo sapiens (HUMAN)"

#### Scenario: The species the API lists

- **WHEN** the user opens the species selector
- **THEN** it offers each species the API lists, by name and code, and no other

#### Scenario: Search by name

- **WHEN** the user types `muscul` in the species selector and chooses the one option left
- **THEN** the species is "Mus musculus (MOUSE)"

#### Scenario: Search by code

- **WHEN** the user types `plaf7` in the species selector
- **THEN** the selector offers "Plasmodium falciparum (PLAF7)", and no species whose name or code doesn't contain `plaf7`

#### Scenario: With the keyboard

- **WHEN** the user moves to the species selector with Tab, types part of a name, picks an option with the arrow keys and confirms with Enter
- **THEN** the species is the one picked

#### Scenario: The code is sent

- **WHEN** the user chooses "Mus musculus (MOUSE)" and submits a valid input
- **THEN** the request's `species` is `MOUSE`

### Requirement: cSNP form checks the input before sending

Before sending, the cSNP form SHALL check the input against `scoring-input`'s cSNP rules: the sequence, the substitutions as split, each in `<residue><position><residue>` form once upper-cased, and the species. Once the species list has loaded, the species MUST be one of its codes; before then, or when the list couldn't be loaded, the form checks the species' shape only, and the API checks the rest. Each broken rule MUST be shown on its field, and no request MUST be sent while any is broken. The form MUST NOT reject an input that the rules accept.

#### Scenario: Empty form

- **WHEN** the user submits the form with the sequence and substitutions boxes empty
- **THEN** the sequence and substitutions fields each show an error, and no request is sent

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

- **WHEN** the species list couldn't be loaded, and the user submits the species `human`, `HOMOSAPIENS` or an empty species
- **THEN** the species field shows an error, and no request is sent

#### Scenario: A species not in the list

- **WHEN** the species list couldn't be loaded, the user types the species `ZZZZZ`, the list then loads, and the user submits
- **THEN** the species field shows an error asking for a species from the list, and no request is sent

#### Scenario: A valid input is sent

- **WHEN** the user submits a FASTA sequence of 50,000 residues, the substitutions `L46P c130r G99999R`, and the species "Plasmodium falciparum (PLAF7)"
- **THEN** no field shows an error, and the request is sent with that sequence, `["L46P", "c130r", "G99999R"]` and `PLAF7`

## ADDED Requirements

### Requirement: cSNP species list unavailable

While the species list loads, the cSNP form SHALL say so in the species field. If the list can't be loaded, the form MUST stay usable: it MUST offer a box for a species code instead, keeping the species chosen so far, say in fixed text that the list couldn't be loaded, with no status code or build details, and offer to load the list again. When the list then loads, the form MUST offer the selector, keeping the species if it is in the list.

#### Scenario: Loading

- **WHEN** the user opens `/csnp` and the species list hasn't loaded yet
- **THEN** the species field says the species are loading, and the sequence and substitutions boxes can be filled

#### Scenario: The list fails to load

- **WHEN** the user opens `/csnp` and the API answers the species list with an error
- **THEN** the species field is a box holding `HUMAN`, the form says the species list couldn't be loaded, shows no status code or build details, and offers to try again

#### Scenario: Submitting without the list

- **WHEN** the species list couldn't be loaded, and the user types the species `MOUSE` and submits a valid input
- **THEN** the request is sent with the species `MOUSE`

#### Scenario: Trying again

- **WHEN** the species list couldn't be loaded, the user typed `MOUSE`, and chooses to try again, and the list now loads
- **THEN** the species field is the selector, showing "Mus musculus (MOUSE)"
