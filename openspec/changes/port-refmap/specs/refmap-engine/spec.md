# Spec Delta

## Purpose

Mapping protein IDs to PANTHER families and subfamilies for one Reference Proteome organism, as RefProteomeMapper's `map_panther.pl` did. It covers the organisms the engine publishes, the `map` command, and the parity checks that prove the port matches the Perl.

## ADDED Requirements

### Requirement: Mapping IDs for one organism

The engine SHALL map a list of IDs for one organism, using that organism's classification file. It SHALL return the organism, and one mapping per ID in input order, with a repeated ID mapped each time. Each mapping gives the ID as submitted, and its PANTHER ID (a subfamily such as `PTHR11360:SF130`, or a family such as `PTHR28011`) or none.

#### Scenario: The data's own test

- **WHEN** the README's `test_geneList` is mapped for `ENDPU` against the pinned data
- **THEN** the result's organism is `ENDPU`, and its 450 mappings equal the golden output's first two fields, in order, with none where the golden says `NOHIT`

#### Scenario: Repeated ID

- **WHEN** `U1G4Q5`, `U1GLV9` and `U1G4Q5` are mapped for `ENDPU`
- **THEN** there are three mappings, in that order: `PTHR11360:SF130`, `PTHR28011`, and `PTHR11360:SF130` again

### Requirement: Exact lookup

The engine SHALL look each ID up exactly as given. The lookup is case-sensitive, trims nothing, and strips no isoform or version suffix (`REFMAP-1`).

#### Scenario: Lower case

- **WHEN** `u1g4q5` is mapped for `ENDPU`
- **THEN** it has no PANTHER ID, although `U1G4Q5` maps to `PTHR11360:SF130`

#### Scenario: Isoform and version

- **WHEN** `U1G4Q5-2` and `U1G4Q5.1` are mapped for `ENDPU`
- **THEN** neither has a PANTHER ID

### Requirement: IDs with no PANTHER ID

An ID that isn't in the organism's classification file, and an ID the file gives as `NOHIT`, SHALL both have no PANTHER ID. The legacy printed `NOHIT` for both.

#### Scenario: Stored as NOHIT

- **WHEN** `U1HQ27`, which `ENDPU`'s file gives as `NOHIT`, is mapped for `ENDPU`
- **THEN** its PANTHER ID is none, not the text `NOHIT`

#### Scenario: Another organism's ID

- **WHEN** `A0A4Y2E0M5`, which maps to `PTHR47331` in `ARAVE`'s file, is mapped for `ENDPU`
- **THEN** it has no PANTHER ID

### Requirement: Reading a classification file

The engine SHALL read a classification file as `map_panther.pl` does:

- each line loses its final `\n`, but not a `\r` (`REFMAP-3`);
- the first tab-separated field is the ID, and the second its PANTHER ID;
- a later line for an ID replaces an earlier one (`REFMAP-2`);
- a line with no second field gives its ID no PANTHER ID.

#### Scenario: Repeated ID in a file

- **WHEN** a file holds `A1` with `PTHR00001`, then `A1` with `PTHR00002`
- **THEN** `A1` maps to `PTHR00002`

#### Scenario: CRLF line endings

- **WHEN** a file has CRLF line endings
- **THEN** each PANTHER ID it gives ends in `\r`, as the Perl printed it

#### Scenario: No second field

- **WHEN** a file's last line for `A1` has no tab, after an earlier line gave `A1` a PANTHER ID
- **THEN** `A1` has no PANTHER ID

#### Scenario: More fields

- **WHEN** a line holds an ID, a PANTHER ID and a third field
- **THEN** the ID maps to the second field alone

### Requirement: Requests the API would reject

Before reading any data, the engine SHALL refuse a request in any of these cases:

- its organism isn't one the engine publishes;
- it has no IDs;
- an ID is empty, longer than 64 characters, or has a character outside printable ASCII, including whitespace.

The error MUST NOT be an input error, because callers check first. The engine MUST NOT limit how many IDs a request has.

#### Scenario: Unknown organism

- **WHEN** IDs are mapped for `HUMAN`
- **THEN** mapping fails with an error that isn't an input error, and no file is read

#### Scenario: ID with a space

- **WHEN** one of the IDs is `P04 217`
- **THEN** mapping fails with an error that isn't an input error

#### Scenario: A whole genome

- **WHEN** every ID in `ARAVE`'s file, 246,021 of them, is mapped for `ARAVE`
- **THEN** the result has 246,021 mappings, one for each line of the file

### Requirement: Missing classification file

When the organism is one the engine publishes, but its classification file is missing or can't be read, the engine SHALL fail with an error that isn't an input error and that names the file. It MUST NOT return mappings. This is divergence 9: the reference mapped every ID to `NOHIT` (`REFMAP-9`).

#### Scenario: File missing

- **WHEN** IDs are mapped for `ENDPU` with a data folder that has no file for it
- **THEN** mapping fails with an error that isn't an input error and names the missing file

### Requirement: Organisms

The engine SHALL publish each organism it maps for, without needing the data folder:

- its code;
- its name as the website showed it, before the code in brackets: the long name's parts but the last, joined with spaces.

It SHALL list them in the order of their long names, as the website did.

#### Scenario: Codes

- **WHEN** the published organisms are read
- **THEN** there are 1,533, including `ENDPU`, `ECO57` and `PEA`, and not `HUMAN`, `MOUSE`, `YEAST` or `ECOLI`

#### Scenario: Names

- **WHEN** the names of `ECO57`, `PEA` and `CAMJE` are read
- **THEN** they are "Escherichia coli O157:H7", "Pisum sativum" and "Campylobacter jejuni subsp jejuni serotype O:2"

#### Scenario: Order

- **WHEN** the published organisms are listed
- **THEN** the first is `ABRPR` (`Abrus_precatorius_ABRPR`), and the last is `ZYMTI` (`Zymoseptoria_tritici_ZYMTI`)

#### Scenario: Without data

- **WHEN** `PANTHER_DATA_DIR` isn't set
- **THEN** the organisms can still be read

### Requirement: Data check

The engine SHALL offer a check that the data folder holds the refmap data: `stats`, and a classification file for every organism it publishes. The check MUST fail with an error that names what is missing, and MUST NOT read the files' contents.

#### Scenario: Data in place

- **WHEN** the check runs on a data folder with the pinned data fetched
- **THEN** it passes

#### Scenario: One file missing

- **WHEN** `ENDPU`'s file is removed from the data folder and the check runs
- **THEN** it fails and names `ENDPU`'s file

### Requirement: Mapping from the command line

`panther-engine refmap map` SHALL map IDs for one organism, taken from its arguments or from a file. In a file, each line's first tab-separated field is the ID, as the Perl read it. It SHALL print one line per ID, in order: the ID and its PANTHER ID, or `NOHIT`, separated by a tab. With `--json`, it SHALL print the result instead.

#### Scenario: Golden list

- **WHEN** a user maps the file `test_geneList` for `ENDPU`
- **THEN** the lines printed equal the golden output's first two fields, and it exits with status 0

#### Scenario: Organism not published

- **WHEN** a user maps IDs for `HUMAN`
- **THEN** it exits with a non-zero status, names the organism, and prints no mappings

### Requirement: Parity with the reference

The engine's tests SHALL check mapping against golden files made by the reference image:

- the data's test lists against `ENDPU`;
- the hand-made lists;
- the made-up classification files.

Each mapping MUST equal the first two fields of its golden line, with none as `NOHIT`. A difference MUST fail the tests, unless `docs/parity/divergences.md` has an approved row for it.

#### Scenario: The goldens

- **WHEN** the tests run with the refmap data
- **THEN** every golden case gives exactly its golden output

#### Scenario: A difference

- **WHEN** one golden line is changed by hand
- **THEN** the tests fail and name that case

### Requirement: Reference image

A test-only image SHALL run `map_panther.pl` at the parity reference: `4fc6a09` of `pantherdb/RefProteomeMapper`, downloaded when the image is built. The script MUST match its pinned sha256, or the image fails to build. The runtime image MUST NOT contain the script, or Debian's `perl` package.

#### Scenario: Changed script

- **WHEN** the image is built with a pinned sha256 that doesn't match the downloaded script
- **THEN** the build fails, naming the script

#### Scenario: Runtime image

- **WHEN** the API image is built
- **THEN** it has no `map_panther.pl` and no Debian `perl` package

### Requirement: Parity run

`panther-engine refmap parity full` SHALL run, in the reference image, every ID of every organism in a data folder through both the Perl and the engine, with extra IDs generated from a seed. It SHALL report every line that differs, and exit with a non-zero status if any does.

#### Scenario: The pinned data

- **WHEN** the parity run is given the pinned data and a seed
- **THEN** it reports how many IDs it compared for each organism, reports no differences, and exits with status 0

#### Scenario: Same seed

- **WHEN** the extra IDs are generated twice from the same data and seed
- **THEN** they are identical
