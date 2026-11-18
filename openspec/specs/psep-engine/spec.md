# psep-engine Specification

## Purpose

cSNP scoring with PANTHER-PSEP: placing one protein in a PANTHER family with BLAST+, mapping each substitution onto the family's tree, and reporting how long the position has been preserved, as the legacy service did, with the parity checks that prove it.

## Requirements

### Requirement: Scoring one protein

The engine SHALL score the substitutions of one protein for one species. It takes the sequence with no header or whitespace, upper-cased, and substitutions written as wild-type residue, position and residue, such as `A10E`. It SHALL return the family the protein was placed in and one score per substitution, in input order. A protein's scores MUST NOT depend on anything scored before it.

#### Scenario: The golden sample

- **WHEN** the three proteins of the legacy behaviour spec's sample are scored with species `HUMAN` against the data sample, one call each: P26439 with the substitutions of `del1` to `del26`, Q9H2F3 with `del27` and `del28`, and P78314 with `del29` to `del35`
- **THEN** each call returns the family and the age, message and pDel of each of its rows in spec §7.3, in order

#### Scenario: Order of calls

- **WHEN** P78314 is scored, then P26439, then P78314 again
- **THEN** both P78314 results are identical, and P26439's equals its rows in spec §7.3

### Requirement: The fields of a score

Each score SHALL give the substitution, the age in millions of years or none, the message, and pDel as the legacy two-decimal string or none. A substitution that isn't scored has no age and no pDel; its message is the legacy text. A scored substitution whose legacy age is empty has no age, with the message and pDel the legacy gave it.

#### Scenario: Not scored

- **WHEN** a substitution comes back as not scored
- **THEN** its message is the legacy text, such as "Not scored: Invalid substitution", and its age and pDel are none

#### Scenario: Two-decimal pDel

- **WHEN** a substitution's pDel is one half
- **THEN** it is the string `0.50`, not a number

### Requirement: Family search with BLAST+

The engine SHALL search the protein against the PANTHER9 BLAST database with BLAST+ `blastp`, with the legacy step 1's options and the query named `P0001`. It MUST NOT use a shell, and MUST NOT share any file between searches.

#### Scenario: Searches at the same time

- **WHEN** two different proteins are scored at the same time, in separate processes
- **THEN** each result has its own protein's family and scores

#### Scenario: No hit

- **WHEN** the search finds no hit for the species
- **THEN** the family is none, and every substitution is "Not scored: No PANTHER family for input sequence"

### Requirement: The best hit

Of the hits whose BLAST output line contains the species code anywhere (`MAP-2`), the engine SHALL take the one with the highest percent identity, to two decimals (`MAP-1`). Hits with equal identity SHALL be ordered by comparing their output lines byte by byte. The hit's subject id gives the family and the gene (`MAP-3`).

#### Scenario: Species filter

- **WHEN** the search returns a 99.00% hit from `MOUSE` and a 95.00% hit from `HUMAN`, and the species is `HUMAN`
- **THEN** the `HUMAN` hit is the best hit

#### Scenario: Tied identity

- **WHEN** two hits for the species have the same percent identity to two decimals
- **THEN** the hit whose output line comes first byte by byte is the best hit

#### Scenario: Step-1 fixture

- **WHEN** the search runs for the sample proteins with species `HUMAN`
- **THEN** the best hit of each has the subject id, start positions and aligned sequences of the first row for that protein in the `HUMAN` fixture

### Requirement: The reported family

The family in the result SHALL be what the legacy service showed: the best hit's family field cut to `PTHR` and its digits, the field as it is when it has no such part, or none when there is no hit.

#### Scenario: Split family

- **WHEN** the best hit's family field is `PTHR23125_2`
- **THEN** the reported family is `PTHR23125`, and the substitutions are scored against `PTHR23125_2`'s files

#### Scenario: Family field that isn't a family

- **WHEN** the best hit's family field is `AN12345`
- **THEN** the reported family is `AN12345`, and every substitution is "Not scored: No PANTHER family for input sequence"

### Requirement: Mapping positions onto the family sequence

The engine SHALL map each substitution's position onto the best hit's subject sequence as the legacy step 2 does, gaps included (`MAP-4`). The residue at the alignment's first query position, and a residue right after a gap in the query, SHALL NOT be mapped.

#### Scenario: Start of the alignment

- **WHEN** the spec §7.5 case `e1` (`M1V`, P26439) is scored
- **THEN** it is "Not scored: Invalid substitution"

#### Scenario: Next residue

- **WHEN** the spec §7.5 case `e2` (`G2V`, P26439) is scored
- **THEN** it is `PTHR10366`, age 910, "probably damaging", `0.85`

#### Scenario: After a gap in the query

- **WHEN** the query side of the alignment is `AB-CD`, the subject side `ABXCD`, both starting at 1
- **THEN** query residue 3 isn't mapped, and query residue 4 maps to subject position 5

### Requirement: Substitutions that can't be scored

The engine SHALL check, in the legacy order (`SCORE-1`), that the hit's family has library files, else "Not scored: No PANTHER family for input sequence". Then it SHALL check that the position was mapped and that the gene's sequence has the wild-type residue there, else "Not scored: Invalid substitution". A family whose library files are broken MUST give "Not scored: Invalid substitution", not an error.

#### Scenario: Mutant residue first

- **WHEN** the spec §7.5 case `e3` (`E10A`, P26439, where the residue is `A`) is scored
- **THEN** it is "Not scored: Invalid substitution"

#### Scenario: Wrong wild type

- **WHEN** the spec §7.5 case `e9` (`X373R`) is scored
- **THEN** it is "Not scored: Invalid substitution"

#### Scenario: Broken library files

- **WHEN** a substitution is scored against `PTHR11711`, whose `.rst` is empty and whose `.paml` has only `0` sites
- **THEN** it is "Not scored: Invalid substitution", and scoring doesn't fail

### Requirement: Trace-back

The engine SHALL start at the last `.paml` header column labelled with the gene's AN (`SCORE-2`). It SHALL move towards the root while each node's reconstructed residue is the wild type with a posterior probability above 0.99. It SHALL report the age of the first node that fails, or the root's if none fails (`SCORE-3`).

#### Scenario: Colliding labels

- **WHEN** `del28` (`E147K`, Q9H2F3, AN 911 in `PTHR10366`) is scored
- **THEN** the walk starts at column 1380, not the leaf's column 1238, and the result is age 470, "probably damaging", `0.57`

#### Scenario: Unreconstructed cell

- **WHEN** the walk reaches a node whose cell has no reconstructed residue and a `-nan` probability
- **THEN** the walk stops there, and reports that node's age

### Requirement: Node ages

The engine SHALL age a leaf 0, and a speciation node by its taxon's age in the species tree. It SHALL age a duplication, or a node whose taxon the species tree lacks (`DATA-3`), as one more than the oldest of its children, at most 4200, or no age if it has no child. Any other node SHALL get the age the reference gives it, as recorded in the goldens.

#### Scenario: Duplications above a speciation

- **WHEN** the walk stops at a duplication whose oldest child is a 750 Mya speciation
- **THEN** the age is 751

#### Scenario: Cap

- **WHEN** the spec §7.3 case `del3` (`G15D`, P26439) is scored
- **THEN** its age is 4200

#### Scenario: Taxon missing from the species tree

- **WHEN** the walk stops at a speciation node whose taxon is Sauria, which the species tree lacks
- **THEN** the node is aged as a duplication

### Requirement: Message and pDel

The engine SHALL give the message "probably benign" below 180 Mya, "possibly damaging" from 180 to 379, and "probably damaging" from 380 (`SCORE-5`). pDel SHALL come from the legacy table, testing `age < bound` (`SCORE-6`). An empty age SHALL count as 0.

#### Scenario: Euarchontoglires

- **WHEN** the age is 91
- **THEN** the message is "probably benign" and pDel is `0.19`

#### Scenario: Threshold

- **WHEN** the age is 380
- **THEN** the message is "probably damaging" and pDel is `0.50`

#### Scenario: Empty age

- **WHEN** the walk stops at a duplication with no child
- **THEN** the age is none, the message "probably benign" and pDel `0.02`

### Requirement: The substitution as submitted

Each score SHALL carry the substitution as submitted, with the submitted position, whatever position it maps to in the family's sequence (`SCORE-10`). The mutant residue MUST NOT change the score (`SCORE-12`).

#### Scenario: Mutant residue

- **WHEN** `A10E` and `A10V` are scored for P26439
- **THEN** both have age 220, "possibly damaging" and `0.50`

#### Scenario: Leading zero

- **WHEN** `A010E` is scored for P26439
- **THEN** its substitution is `A010E`, and it is scored as position 10

### Requirement: Species codes

The engine SHALL publish the species codes it scores against: the species in the PANTHER9 BLAST database. Scoring with any other code MUST fail with an error that isn't an input error, because callers check the code first.

#### Scenario: Codes match the database

- **WHEN** the published codes are compared with the species of every entry in the data sample's BLAST database
- **THEN** they are the same 85 codes, including `HUMAN`, `PLAF7` and `SYNY3`

#### Scenario: Unknown code

- **WHEN** a protein is scored with the species `XXXXX`
- **THEN** scoring fails with an error that isn't an input error, and nothing is searched

### Requirement: Species names

The engine SHALL publish a name for each species code it scores against: the name the old site's cSNP list gives that code (`CSNP_SHORT_LONG_ORG_LIST` in `panther-site-java`'s `OrganismConstants.java`), as written there. It MUST publish a name for exactly the codes it scores against, and a caller MUST NOT be able to change the names.

#### Scenario: A name for every code

- **WHEN** the published names are compared with the published species codes
- **THEN** there is one name for each of the 85 codes, and no name for any other code

#### Scenario: The old site's names

- **WHEN** the names of `HUMAN`, `PLAF7`, `SYNY3` and `CANFA` are looked up
- **THEN** they are `Homo sapiens`, `Plasmodium falciparum`, `Synechocystis` and `Canis familiaris`, as the old site's list has them

#### Scenario: Read-only

- **WHEN** a caller tries to change a name, or to add one
- **THEN** it fails, and the names are unchanged

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

### Requirement: Scoring from the command line

`panther-engine csnp score` SHALL score one protein from a FASTA file of one sequence, a list of substitutions and a species code, and print the family and each score, as the scoring interface returns them.

#### Scenario: Golden protein

- **WHEN** a user scores P26439 from the PSEP release's `sample.fasta` with `A10E` and `G15D`, species `HUMAN`
- **THEN** it prints `PTHR10366` and the two rows of spec §7.3, and exits with status 0

#### Scenario: More than one sequence

- **WHEN** the FASTA file holds two sequences
- **THEN** it exits with a non-zero status and scores nothing

### Requirement: Parity with the reference

The engine's tests SHALL check scoring against golden files made by the reference: spec §7.3 and §7.5, the step-1 output of BLAST+ 2.17.0, the reference image's output for generated cases in every data-sample family, and the reference image's output for the scoring form's example. A difference MUST fail the tests, unless `docs/parity/divergences.md` has an approved row for it.

#### Scenario: The sample's goldens

- **WHEN** the tests run with the data sample
- **THEN** every golden case gives exactly the golden output

#### Scenario: A difference

- **WHEN** one golden row is changed by hand
- **THEN** the tests fail and name that case

#### Scenario: The form's example

- **WHEN** the form's example, the legacy site's human APOE with `L46P`, `C130R`, `R163C` and `R176C` for `HUMAN`, is scored with the data sample
- **THEN** the family is `PTHR18976`, and each substitution's age, message and pDel are exactly the reference image's output for it

### Requirement: Reference image

A test-only image SHALL run the legacy cSNP scripts at the parity reference, `cebb5ab` of `pantherdb/cSNP_analysis`, from a developer's local checkout. Each script MUST match its pinned sha256, or the image fails to build. The runtime image MUST NOT contain the scripts, or any Perl beyond the minimal one its base system requires.

#### Scenario: Changed script

- **WHEN** the image is built from a checkout where `PANTHER_PSEP1.01.pl` differs from `cebb5ab`
- **THEN** the build fails, naming the file

#### Scenario: Runtime image

- **WHEN** the API image is built
- **THEN** it has none of the legacy scripts, and no Perl but Debian's Essential `perl-base`

### Requirement: Parity run

`panther-engine csnp parity` SHALL generate cases for each family in a data folder from a seed, run them through the legacy scripts in the reference image, one process per family, and compare the engine's results. It SHALL report every case that differs, and exit with a non-zero status if any does.

#### Scenario: Sample

- **WHEN** the parity run is given the data sample and a seed
- **THEN** it reports the number of cases per family, no differences, and exits with status 0

#### Scenario: Same seed

- **WHEN** the parity run generates cases twice from the same data and seed
- **THEN** the cases are identical

### Requirement: Data version

The engine SHALL publish the PANTHER release of the data cSNP scoring reads, as `DATA_VERSION` from `panther_engine.csnp`. It MUST be the release whose folder scoring reads, `csnp/<release>/` under the data folder, so the two can't disagree. Reading it MUST NOT need the data folder.

#### Scenario: cSNP's release

- **WHEN** a caller reads `DATA_VERSION` from `panther_engine.csnp`, with `PANTHER_DATA_DIR` unset
- **THEN** it is `"9"`, the release of the `csnp/9/` folder scoring reads

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
