# Spec Delta

## ADDED Requirements

### Requirement: An organism's whole classification

The engine SHALL export `classification_mappings(organism, data_dir=None)`, yielding every line of the organism's classification file as an `IdMapping`, in order, a repeated ID once per line. Lines MUST be read by the reader `map_ids` uses. It MUST raise `ValueError` for an organism refmap doesn't map for, before reading, and `MissingDataError`, naming the file, when the file is missing.

#### Scenario: Every line, in order

- **WHEN** ENDPU's file has the lines `U1G4Q5` and `PTHR10351`, `U1HV42` and `NOHIT`, and `U1G4Q5` and `PTHR10351:SF2`, each pair separated by a tab
- **THEN** `classification_mappings("ENDPU")` yields `IdMapping("U1G4Q5", "PTHR10351")`, `IdMapping("U1HV42", None)` and `IdMapping("U1G4Q5", "PTHR10351:SF2")`

#### Scenario: Read as map_ids reads it

- **WHEN** a file has a carriage return before a line's end, a line with no tab, a line ending in a tab and a line with a third field
- **THEN** each mapping's `panther_id` is the value `map_ids` would give that line: the value with its `\r`, `None`, an empty string and the second field

#### Scenario: The published files

- **WHEN** every organism's mappings, with the release's data, are written back with `render`, one a line
- **THEN** each is the organism's published file byte for byte, and their counts are its `genes` and `genes_with_panther_id`

#### Scenario: An organism refmap doesn't map for

- **WHEN** `classification_mappings` is called with `NOPE1`, `endpu`, `..` or `ENDPU/x`
- **THEN** it raises `ValueError` and reads nothing
