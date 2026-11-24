# Spec Delta

## Purpose

Grafting one protein sequence onto a PANTHER family tree, as EBI's pinned `treegrafter` does, to infer its subfamily, GO terms and protein class. It covers the graft and its fields, the data check and versions, the `treegrafter score` command, and the parity checks against EBI's own command line.

## ADDED Requirements

### Requirement: Grafting one protein

The engine SHALL graft one protein, given as the API sends it: no header or whitespace, and upper-cased. It SHALL return the graft of the protein's best family, or no hit. A protein's result MUST NOT depend on anything grafted before it.

#### Scenario: The site's example

- **WHEN** APOE is grafted against the fixture
- **THEN** the hit's PANTHER ID is `PTHR18976:SF2` and its graft node is `AN163`, as EBI's command line gives

#### Scenario: Order of calls

- **WHEN** APOE is grafted, then human HBB, then APOE again
- **THEN** both APOE results are identical

### Requirement: The fields of a hit

A hit SHALL give:

- its PANTHER ID: the graft node's subfamily, else the family;
- the graft node, and its graft point's public ID (`PTN…`);
- the GO terms, in the annotation's order, and the protein class;
- the full-sequence bit score and E-value, and the best domain's, as EBI's command line writes them;
- the best domain's model, alignment and envelope coordinates.

#### Scenario: Values as EBI writes them

- **WHEN** APOE is grafted against the fixture
- **THEN** the hit's scores and E-values are `172.6`, `5.7e-47`, `172.4` and `6.8e-47`, its model coordinates 11 to 359, its alignment coordinates 1 to 306 and its envelope 1 to 311

#### Scenario: Annotations

- **WHEN** APOE is grafted against the fixture
- **THEN** the hit's GO terms, protein class `PC00052` and graft point are the active release's entry for `PTHR18976:AN163`

#### Scenario: A node without a subfamily

- **WHEN** a protein's graft node has no subfamily in the active release
- **THEN** the hit's PANTHER ID is the family's

### Requirement: The search

The engine SHALL search the library's family HMMs with `hmmsearch` as EBI's `treegrafter.sh search` does: a search space of 65,000,000 sequences, a sequence reporting threshold of 0.001 and domain thresholds of 1e-8, with no worker threads. Each graft MUST run in a folder of its own, removed when grafting ends, whether it succeeds or fails.

#### Scenario: The fixed search space

- **WHEN** APOE is grafted against the fixture, which holds three family HMMs
- **THEN** its E-value is `5.7e-47`, as against the full library

#### Scenario: Two at once

- **WHEN** two different proteins are grafted at the same time against the fixture
- **THEN** each gets the result it gets when grafted alone

### Requirement: The best family

The best family SHALL be the one EBI's code picks: among the families whose full sequence passes `hmmsearch`'s inclusion threshold, the highest full-sequence score, with that family's best domain. If that family's full-sequence E-value is over 1e-8, there SHALL be no hit, even when a lower-scoring family's is under it.

#### Scenario: Two families

- **WHEN** APOE joined to human HBB is grafted against the fixture
- **THEN** the hit's family is the one with the higher full-sequence score, as EBI's command line gives

#### Scenario: Over the cutoff

- **WHEN** 30 residues of APOE are grafted against the fixture
- **THEN** there is no hit

#### Scenario: No family reported

- **WHEN** a random 300-residue sequence is grafted against the fixture
- **THEN** there is no hit, and EPA-ng doesn't run

### Requirement: The placement

The engine SHALL fit the protein to the family's alignment columns and place it on the family's bifurcating tree with EPA-ng, as EBI's code does: the WAG model, 5% of branches prescored, one thread. The graft node SHALL be the one EBI's code takes: in the family's tree, the common ancestor of every leaf below the placements EPA-ng reports.

#### Scenario: One placement

- **WHEN** APOE is grafted against the fixture
- **THEN** EPA-ng reports one placement, and the graft node is `AN163`

#### Scenario: Several placements

- **WHEN** human HBB is grafted against the fixture
- **THEN** EPA-ng reports several placements, and the graft node is the one EBI's command line gives

### Requirement: The annotation release

The subfamily, graft point, GO terms and protein class SHALL come from the active annotation release, as EBI's `prepare` reads it. The result SHALL name the release it used, and a graft MUST read one release throughout, even when another becomes active while it runs.

#### Scenario: The release named

- **WHEN** a protein is grafted with the 2026-08-28 release active
- **THEN** the result names release 2026-08-28

### Requirement: Families that can't be placed

When the family's tree has a leaf that its alignment lacks, the engine SHALL NOT run EPA-ng. It SHALL return the family as the hit, with the scores and coordinates, and no graft node, graft point, GO terms or protein class, as EBI's command line prints it. It SHALL log a warning that names the family.

#### Scenario: A member of PTHR11034

- **WHEN** a member of PTHR11034, whose tree has leaf `AN186` and whose alignment doesn't, is grafted against the fixture
- **THEN** the hit's PANTHER ID is `PTHR11034`, it has no graft node, EPA-ng doesn't run, and the log names PTHR11034

### Requirement: Sequences the API wouldn't send

Before running any tool, the engine SHALL refuse a sequence the API never sends: an empty one, one with a character other than an upper-case letter, `.`, `_` or `*`, or one with no letter. So `~` and `-` are refused: divergence 15. The error MUST NOT be the input error. The residue limit is the API's setting, so the engine MUST NOT apply one.

#### Scenario: A tilde

- **WHEN** APOE with a `~` is grafted
- **THEN** grafting fails with an error that isn't the input error, and no tool runs

#### Scenario: Lower case

- **WHEN** `mkvl` is grafted
- **THEN** grafting fails with an error that isn't the input error, and no tool runs

#### Scenario: Characters the engine takes

- **WHEN** APOE with a final `*`, and APOE with a `.` and a `_`, are grafted against the fixture
- **THEN** each gets the result EBI's command line gives it

#### Scenario: Past the API's limit

- **WHEN** a sequence of 10,001 letters is grafted against the fixture
- **THEN** it is grafted

### Requirement: The time limit

Given a time limit in seconds, the engine SHALL apply it to the whole graft: `hmmsearch` gets it, then EPA-ng what's left. Past it, the engine SHALL stop the running tool and raise treegrafter's timeout error. That error MUST NOT be the input error, nor a subclass of it, and MUST keep its type when passed from a worker process. With no time limit, grafting isn't limited.

#### Scenario: Too long

- **WHEN** a protein is grafted with a time limit shorter than `hmmsearch` takes
- **THEN** grafting raises the timeout error, not the input error, no tool is left running, and the graft's folder is removed

#### Scenario: EPA-ng past the limit

- **WHEN** a protein is grafted, and EPA-ng is still running when the time limit is reached
- **THEN** EPA-ng is stopped, and grafting raises the timeout error

#### Scenario: Past the limit in a worker process

- **WHEN** a protein is grafted in a worker process with a time limit shorter than `hmmsearch` takes
- **THEN** the process that started the work receives the timeout error

### Requirement: Tool failures

When `hmmsearch` or EPA-ng exits with an error status or writes no output, or EBI's code rejects `hmmsearch`'s report, the engine SHALL fail with an error that isn't the input error. The error keeps the end of the tool's standard error for the log. The engine MUST NOT report no hit, or the family alone, instead.

#### Scenario: EPA-ng fails

- **WHEN** a protein is grafted, and EPA-ng exits with an error status on a family whose tree and alignment match
- **THEN** grafting fails with an error that isn't the input error, and that holds the end of EPA-ng's standard error

#### Scenario: A report EBI's code rejects

- **WHEN** a protein is grafted, and `hmmsearch`'s report is one EBI's parser exits on
- **THEN** grafting fails with an error that isn't the input error, and the process doesn't exit

### Requirement: Data check

The engine SHALL offer a check that the data folder holds the treegrafter data: `famhmm/binHmm`, `Tree_MSF/` and an active annotation release with its folder. The check MUST fail with an error that names what's missing. It MUST NOT read the files' contents. Grafting SHALL run the check first.

#### Scenario: Data in place

- **WHEN** the check runs on a data folder holding the prepared fixture
- **THEN** it passes

#### Scenario: No active release

- **WHEN** the check runs on a data folder whose library is in place but no annotation release is active
- **THEN** it fails, and names the missing release

### Requirement: Data version

The engine SHALL publish the PANTHER release of the library treegrafter reads, as `DATA_VERSION` from `panther_engine.treegrafter`, without needing the data folder. It SHALL also offer the active annotation release, its date and its GO release, read from the data folder.

#### Scenario: The library's release

- **WHEN** a caller reads `DATA_VERSION` from `panther_engine.treegrafter`, with `PANTHER_DATA_DIR` unset
- **THEN** it is `"19"`, the release of the `treegrafter/19/` folder grafting reads

#### Scenario: The active release

- **WHEN** a caller asks for the active annotation release of a data folder where 2026-08-28 is active
- **THEN** it gets 2026-08-28, with GO release 2026-08-05

### Requirement: Loading EBI's code

Importing `panther_engine.treegrafter` SHALL NOT load EBI's code or Biopython. They SHALL load only when a protein is grafted or a release is prepared, so a process that only imports the engine stays light.

#### Scenario: Importing the engine

- **WHEN** a fresh Python process imports `panther_engine.treegrafter`
- **THEN** neither EBI's `treegrafter` module nor Biopython is loaded

### Requirement: The adopted code

The engine SHALL graft with EBI's `treegrafter` at the pinned commit, installed from that commit's archive and locked by its checksum. Its `treegrafter.py` MUST be the pinned commit's, byte for byte.

#### Scenario: The installed module

- **WHEN** the engine's dependencies are installed from the lock
- **THEN** the installed `treegrafter.py` has the sha256 of the pinned commit's file

### Requirement: Grafting from the command line

`panther-engine treegrafter score` SHALL graft one protein, given as a FASTA file or on standard input. It normalises the protein as the API does, then prints the hit's fields, or says there's no hit. `--json` prints the result as JSON, and `--timeout` sets the time limit. An error MUST go to standard error, with a non-zero exit status.

#### Scenario: The example

- **WHEN** `panther-engine treegrafter score` is run on `example/apoe.fasta` with the fixture's data
- **THEN** it prints `PTHR18976:SF2`, the graft node `AN163`, the GO terms, the protein class and the scores, and exits with status 0

#### Scenario: JSON

- **WHEN** the same command is run with `--json`
- **THEN** it prints one JSON object, with the annotation release and a `hit` holding the hit's fields

#### Scenario: A refused sequence

- **WHEN** the command is run on a FASTA file whose sequence holds a `~`
- **THEN** it prints an error to standard error and exits with a non-zero status

### Requirement: Parity with the reference

The engine's tests SHALL check grafting against golden files that EBI's own command line, at the pinned commit and with the engine's tools, made on the fixture for every case in the golden set. Each result MUST equal its golden row field for field, with EBI's `-` as no value. A difference MUST fail the tests, unless `docs/parity/divergences.md` has an approved row for it.

#### Scenario: The goldens

- **WHEN** the tests run with the fixture, HMMER 3.4 and EPA-ng 0.3.8 on amd64
- **THEN** every golden case gives exactly its golden result

#### Scenario: A difference

- **WHEN** one golden's graft node is changed by hand
- **THEN** the tests fail and name that case

#### Scenario: A family that can't be placed

- **WHEN** the golden row for the PTHR11034 case has `-` for its node, GO terms and protein class
- **THEN** the engine's hit for that case has no graft node, GO terms or protein class

### Requirement: Reference run

`panther-engine treegrafter parity reference` SHALL run EBI's command line at the pinned commit for every case in the golden set against a data folder, as `treegrafter.sh search` does: `hmmsearch` with its flags, then `treegrafter.py run -e 1e-8 --print-go`. It SHALL save each case's output, one case at a time.

#### Scenario: On the fixture

- **WHEN** the reference run is given the prepared fixture
- **THEN** it writes each case's output, and the APOE case's row names `PTHR18976:SF2` and `AN163`

### Requirement: Parity run

`panther-engine treegrafter parity check` SHALL graft every case of the golden set against a data folder, such as the full library, and compare each result with the reference's output made on that data folder. It SHALL report every case that differs and each case's time, and exit with a non-zero status if any case differs.

#### Scenario: The full library

- **WHEN** the parity run is given the full library and the reference's output made on it
- **THEN** it reports each case's time and no differences, and exits with status 0

#### Scenario: Missing outputs

- **WHEN** the parity run is given a case with no reference output
- **THEN** it names that case and exits with a non-zero status
