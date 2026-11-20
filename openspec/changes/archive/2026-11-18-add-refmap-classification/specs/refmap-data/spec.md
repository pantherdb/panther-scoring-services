# Spec Delta

## ADDED Requirements

### Requirement: Building the classification JSON

`panther-engine refmap data build-json` SHALL write each listed organism's `classification_mappings` as gzipped JSON, `{"organism", "mappings"}`, at `refmap/19/classification_json/<code>.json.gz`. Memory MUST NOT grow with the file's size. Each file MUST be moved into place complete and readable by every user, and the same source MUST give the same bytes. `--missing-only` MUST skip organisms whose JSON is there. `fetch` MUST NOT run it.

#### Scenario: Every mapping

- **WHEN** `build-json` runs on a data folder holding ENDPU's classification file
- **THEN** `classification_json/ENDPU.json.gz` decompresses to ENDPU's code and every mapping of its file, in order

#### Scenario: The same bytes

- **WHEN** `build-json` runs twice on the same file
- **THEN** both runs write the same bytes, with mode 0644, and leave no partial file

#### Scenario: A missing classification file

- **WHEN** `build-json` runs for an organism whose classification file isn't there
- **THEN** it exits with status 1, naming the file, without a traceback, and writes nothing for that organism

#### Scenario: The release

- **WHEN** `build-json` builds ENDPU, ABSGL and ARAVE from the release's files
- **THEN** each file holds the organism's `classification_mappings`
