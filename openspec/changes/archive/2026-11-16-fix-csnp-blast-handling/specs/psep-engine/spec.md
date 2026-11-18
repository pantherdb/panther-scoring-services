# Spec Delta

## ADDED Requirements

### Requirement: BLAST+ 2.17.0's identities

The engine SHALL read every percent identity BLAST+ 2.17.0 writes. It SHALL compute each line's identity from its alignment length, mismatches and gaps in the order BLAST+ computes it, `(length − mismatch − gaps) / length × 100`, and rank hits by that value to two decimals. A line whose written identity doesn't round to the computed value MUST fail scoring with an error that isn't an input error.

#### Scenario: A tie at three decimals

- **WHEN** the search returns a line of 201 identities over 320 columns, which BLAST+ 2.17.0 writes as `62.813`
- **THEN** the line is read with no error, and ranked at `62.81`

#### Scenario: Ties from BLAST+ itself

- **WHEN** BLAST+ 2.17.0 aligns each of the ungapped tie pairs 161/320, 199/320, 201/320, 402/640, 603/960, 804/1280, 1005/1600 and 1021/1600, and step 2 reads its output
- **THEN** every line is read with no error

#### Scenario: A line that contradicts itself

- **WHEN** a line's written identity is `90.000`, and its length, mismatches and gaps give `62.813`
- **THEN** scoring fails with an error that isn't an input error

### Requirement: BLAST+ time limit

The engine SHALL give each search a time limit that grows with the sequence: a fixed base plus a fixed time per residue, multiplied by `PANTHER_CSNP_BLAST_TIME_SCALE` when that is set. A search that runs past its limit MUST fail with an error that isn't an input error. A scale that isn't a positive number MUST fail scoring before BLAST+ runs, with an error that names the variable.

#### Scenario: Titin

- **WHEN** the limit is computed for titin's 34,350 residues, with no scale set
- **THEN** it is at least 2.5 times titin's search time in the engine image, as `docs/testing/engine.md` records it

#### Scenario: An ordinary protein

- **WHEN** the limit is computed for a sequence of 400 residues, with no scale set
- **THEN** it is at least 60 seconds and under 2 minutes

#### Scenario: A slower machine

- **WHEN** `PANTHER_CSNP_BLAST_TIME_SCALE` is `2`
- **THEN** the limit for every length is twice its default

#### Scenario: An invalid scale

- **WHEN** `PANTHER_CSNP_BLAST_TIME_SCALE` is `0`, `-1` or `fast`, and a protein is scored
- **THEN** scoring fails with an error that isn't an input error and names `PANTHER_CSNP_BLAST_TIME_SCALE`, and BLAST+ isn't run

#### Scenario: Past the limit

- **WHEN** BLAST+ is still running when the search's limit passes
- **THEN** BLAST+ is stopped, and scoring fails with an error that isn't an input error

### Requirement: Missing cSNP data

Before it searches, the engine SHALL check that the cSNP data folder holds the BLAST database's files, a `PAML_RST/` folder that isn't empty, and the species tree. When any is missing, scoring MUST fail with an error that isn't an input error and names each missing path, and BLAST+ MUST NOT run. A family without a `.paml` in a folder that passes the check MUST still be "Not scored: No PANTHER family for input sequence", as in the reference.

#### Scenario: Only the BLAST database

- **WHEN** P26439 is scored with `A10E`, with a data folder that holds only `csnp/9/blast/`
- **THEN** scoring fails with an error that isn't an input error and names `PAML_RST` and `species_pthr8_time.nhx`, and BLAST+ isn't run

#### Scenario: An empty library folder

- **WHEN** a protein is scored with a data folder whose `PAML_RST/` folder is empty
- **THEN** scoring fails with an error that isn't an input error and names `PAML_RST`

#### Scenario: No data at all

- **WHEN** a protein is scored with an empty data folder
- **THEN** scoring fails with an error that isn't an input error and names the BLAST database, `PAML_RST` and the species tree, and BLAST+ isn't run

#### Scenario: A family the library doesn't have

- **WHEN** the data folder passes the check, and the best hit's family has no `.paml`
- **THEN** every substitution is "Not scored: No PANTHER family for input sequence"

### Requirement: Data folder paths

The engine SHALL search the BLAST database wherever the data folder is, whatever characters its path contains, such as a space or a double quote, and MUST give the same hits as for the same data at any other path.

#### Scenario: A space in the path

- **WHEN** the form's example is scored with the data folder at a path that contains a space
- **THEN** the family and the scores are those in `apoe.out`

#### Scenario: A double quote in the path

- **WHEN** the form's example is scored with the data folder at a path that contains `"`
- **THEN** the family and the scores are those in `apoe.out`

## MODIFIED Requirements

### Requirement: A query BLAST+ can't read

When BLAST+ exits with status 1 and reports a query error (a line starting `BLAST query error:` on its standard error), or the sequence starts with a character BLAST+ reads as the start of a comment (`!`, `#` or `;`), the engine SHALL raise its input error, with a message written for the submitter that contains no tool output. This is divergence 8: the reference reported every substitution as "Not scored: No PANTHER family for input sequence".

#### Scenario: Unreadable query

- **WHEN** a protein is scored whose sequence BLAST+ rejects as a query, such as `1234567890`
- **THEN** scoring raises the input error, and its message contains no BLAST+ output, file path or database name

#### Scenario: Sequence read as a comment

- **WHEN** a protein is scored whose sequence starts with `#`
- **THEN** scoring raises the same input error, and BLAST+ isn't run

### Requirement: Other BLAST+ failures

When BLAST+ exits with status 1 without reporting a query error, fails with any other exit status, or runs past its time limit, the engine SHALL fail with an error that isn't an input error. The error's message SHALL include the last lines of BLAST+'s standard error, so the log shows why.

#### Scenario: Database missing

- **WHEN** a protein is scored with a data folder that has no BLAST database
- **THEN** scoring fails with an error that isn't an input error

#### Scenario: An argument BLAST+ rejects

- **WHEN** BLAST+ exits with status 1, and writes its usage text followed by `Error: Unknown argument: "bogus_option"`
- **THEN** scoring fails with an error that isn't an input error, and its message includes that line

#### Scenario: Status 1 with nothing on standard error

- **WHEN** BLAST+ exits with status 1 and writes nothing to standard error
- **THEN** scoring fails with an error that isn't an input error
