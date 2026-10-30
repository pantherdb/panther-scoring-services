# csnp-data Specification

## Purpose

The data the cSNP service scores with: reading the frozen PANTHER 9 PAML_RST library and the species tree, the one-time survey of that library, and the data sample that developers and CI test against.

## Requirements

### Requirement: Reading a family's `.paml` file

The engine SHALL read a family's `.paml` file into each column's node number, AN label and parent, and the root. For any site, it MUST return each node's residue and posterior probability. The root is the one column that is its own parent.

#### Scenario: Header rows

- **WHEN** the engine reads a `.paml` file whose first row labels column `k` as `Node<k> AN<n>` and whose second row gives each column's parent as `Node<p>`
- **THEN** it returns every column's node number, AN number and parent node, and the root's node number

#### Scenario: One site

- **WHEN** the engine is asked for site `s` of a `.paml` file
- **THEN** it returns, for each column, the residue from the `Site s` row (`-` for a gap) and the probability from the `Probability of site s` row as a number

#### Scenario: No root

- **WHEN** the engine reads a `.paml` file in which no column is its own parent, as in the truncated `PTHR21493.paml`
- **THEN** it raises a format error naming the file, and returns no data

#### Scenario: Unreconstructed cell

- **WHEN** a column's residue in the `Site s` row is a NUL byte and its probability in the `Probability of site s` row is `-nan` after a space, as at 15 sites of `PTHR10366`
- **THEN** the engine returns no residue and a probability of NaN for that column, and a NUL residue or a `-nan` probability on its own is a format error

#### Scenario: Internal column without an AN

- **WHEN** a column from the root up is labelled `Node<k>` and a space, with no AN, as 812 columns of `PTHR10366` are
- **THEN** the engine returns no AN for that column, and a leaf column without an AN is a format error

### Requirement: Reading a family's `.rst` file

The engine SHALL read, from a family's `.rst` file, the branch list on its 12th line as (parent, child) pairs, the node numbers in their order of appearance in the tree on its 15th line, and each AN's aligned sequence from the list of extant and reconstructed sequences. The list runs to a line containing `Overall`, or to the end of the file, as it does in the library's files. It MUST read those two lines by position, as the legacy scorer does (`SCORE-9`), and check their shape.

#### Scenario: Branch list and tree

- **WHEN** the 12th line of a `.rst` file is `23..24   24..25 …` and its 15th line is a tree such as `((2_AN12, 21_AN13) 34 , …) 23 ;`
- **THEN** the engine returns the pairs (23, 24), (24, 25) and so on, and the node numbers 2, 21, 34, …, 23 in that order

#### Scenario: Sequences

- **WHEN** the sequence list holds a line starting `AN12` followed by the aligned sequence in blocks of 10
- **THEN** the engine returns AN 12's sequence with the label and spaces removed, gaps kept as `-`

#### Scenario: Empty file

- **WHEN** the engine reads an empty `.rst` file, as for `PTHR11711`
- **THEN** it raises a format error naming the file

#### Scenario: Line out of place

- **WHEN** the 12th line of a `.rst` file is not a branch list
- **THEN** the engine raises a format error naming the file and line 12, and doesn't look for the branch list on another line

### Requirement: Reading a family's `.orig.tree` file

The engine SHALL read, from a family's `.orig.tree` file, the AN numbers in their order of appearance on the first line, each internal node's event (`Ev`) and taxon (`S`) from its NHX attributes, and each leaf's gene identifier, `SPECIES|GENE|UniProtKB=ACC`, from the lines that follow.

#### Scenario: Tree line

- **WHEN** the first line holds leaves written `AN<n>:<length>` and internal nodes written `…)<length>[&&NHX:Ev=0>1:S=<taxon>:ID=AN<n>]`
- **THEN** the engine returns every AN in order of appearance, and the event and taxon of each internal node

#### Scenario: Node without an event

- **WHEN** an internal node's NHX attributes have no `Ev`
- **THEN** the engine reports that node's event as absent, without substituting a value

#### Scenario: One unmatched parenthesis

- **WHEN** the tree line ends with one `)` more than it opens, just before its `;`, as in 135 split parts such as `PTHR23125_2`
- **THEN** the engine reads the tree as if that `)` weren't there, and reports that it was there, and any other imbalance is a format error

#### Scenario: Gene lines

- **WHEN** a following line is `AN12:HUMAN|Ensembl=ENSG00000203859|UniProtKB=P26439;`
- **THEN** the engine returns `HUMAN|Ensembl=ENSG00000203859|UniProtKB=P26439` as AN 12's gene identifier

### Requirement: Reading the species tree

The engine SHALL read the species tree file into a map from each taxon (`S`) to its age in millions of years (`A`).

#### Scenario: Ages

- **WHEN** the engine reads `species_pthr8_time.nhx`
- **THEN** it returns each taxon's age, with LUCA at 4200

#### Scenario: Misspelt tag

- **WHEN** a node's attributes are written `[&&NXH:S=<taxon>:A=<age>]`, as one node in `species_pthr8_time.nhx` is
- **THEN** the engine still reads that taxon's age

### Requirement: Library files are read strictly

A library file whose content doesn't have the expected shape SHALL be a format error that names the file and the 1-based line number. The engine MUST NOT return partial data from such a file. A carriage return anywhere in a library file is a format error.

#### Scenario: Bad probability

- **WHEN** a `Probability of site 3` row in a `.paml` file holds `abc` in one column
- **THEN** the engine raises a format error naming the file and that row's line number

#### Scenario: CRLF line endings

- **WHEN** a library file's lines end in CRLF
- **THEN** the engine raises a format error naming the file and the first such line

### Requirement: Library survey

The engine's command line SHALL survey a gzipped tar archive of the PAML_RST library, reading it as a stream without unpacking it to disk. It MUST report the archive's sha256, the number of families, and for each check the number of families affected with up to five examples, smallest first. It MUST exit with status 0 when the archive was read to the end, whatever the checks found.

#### Scenario: Survey an archive

- **WHEN** a user runs `panther-engine csnp survey` on `PAML_RST.tar.gz`
- **THEN** it prints the archive's sha256, the family count, and each check's count and examples, and exits with status 0

#### Scenario: Nothing written

- **WHEN** the survey runs
- **THEN** no library file is written to disk; only the report is written, and only where the user asks for one

#### Scenario: Unreadable archive

- **WHEN** the survey is given a file that isn't a gzipped tar archive, or one that ends early
- **THEN** it reports the problem and exits with a non-zero status

### Requirement: Survey of files and parsing

The survey SHALL report each family that lacks one of its three files, each split part (`PTHRnnnnn_N`) whose base family has no files, and each file the strict reader rejects, with the reader's error. It MUST also count the families whose `.paml` has unreconstructed cells, those with internal columns that have no AN, and those whose tree line has one unmatched parenthesis.

#### Scenario: Missing file

- **WHEN** the archive has a family's `.paml` and `.orig.tree` but no `.rst`
- **THEN** the survey reports that family as missing its `.rst`

#### Scenario: Known broken files

- **WHEN** the survey reads the pinned archive
- **THEN** it reports `PTHR11711` and `PTHR19241` as having an empty `.rst`, and `PTHR21493` and `PTHR23125_2` as having a `.paml` with no root

### Requirement: Survey of agreement between a family's files

For each family whose three files read, the survey SHALL report where they disagree: the `.paml` parents against the `.rst` branch list, the `.paml` leaf labels against the `.orig.tree` leaves, the node count in the `.rst` tree against the AN count in the `.orig.tree`, and each AN's `.rst` sequence length against the `.paml` site count.

#### Scenario: Parents disagree

- **WHEN** a family's `.paml` gives node 24's parent as 23 but its `.rst` branch list pairs 24 with 25
- **THEN** the survey reports that family under the parent check

#### Scenario: Files agree

- **WHEN** every family's three files agree
- **THEN** the survey reports zero families for each agreement check

### Requirement: Survey of the legacy readings

For each value the legacy scorer reads with a loose pattern or a fixed position, the survey SHALL report the families where that reading differs from the strict reader's. That covers the start column (last label match vs the leaf's own column, `SCORE-2`), the root, the `.rst` branch tokens, the pairing of nodes with ANs, events and taxa, species ages and carriage returns.

#### Scenario: Colliding labels

- **WHEN** a leaf's AN label also appears on a later, internal column of the `.paml` header
- **THEN** the survey counts that leaf, and its family, under the start-column check

#### Scenario: Event the pattern misses

- **WHEN** an internal node's attributes give its event and taxon in a form the legacy pattern `Ev=…:S=…:ID=AN…` doesn't match
- **THEN** the survey counts that node, and its family, under the event check

### Requirement: Survey of events and taxa

The survey SHALL count internal nodes by event (`0>1`, `1>0`, `0>0`, other, absent), and count speciation nodes whose taxon is missing from the species tree, reporting the missing taxa (`DATA-3`).

#### Scenario: Taxon missing from the species tree

- **WHEN** a speciation node's taxon is `Artiodactyla` and the species tree has no `Artiodactyla`
- **THEN** the survey counts that node under the missing-taxon check and lists `Artiodactyla`

### Requirement: Survey of the BLAST database against the library

When given the PANTHER9 BLAST archive as well, the survey SHALL read each entry's family and gene identifier from its FASTA header. It MUST report the entries whose family has no `.paml`, the entries whose gene isn't on a gene line of that family's `.orig.tree`, and the entries for which the legacy lookup (an unescaped pattern, first match wins) finds a different AN than an exact match (`DATA-2`, `SCORE-8`).

#### Scenario: Family without a `.paml`

- **WHEN** a BLAST entry's family has no `.paml` in the library archive
- **THEN** the survey counts that entry under the no-family check

#### Scenario: Prefix match

- **WHEN** a BLAST entry's gene identifier is a prefix of another gene line in the same `.orig.tree`, and that line comes first
- **THEN** the survey counts that entry under the lookup check

### Requirement: Data sample contents

The cSNP data sample SHALL hold the `.paml`, `.rst` and `.orig.tree` of each chosen family exactly as in the pinned archive, `species_pthr8_time.nhx`, and the PSEP release's copyright statement, laid out under the cSNP data folder as the full data is. It MUST include `PTHR10366`, `PTHR15126`, `PTHR11711` and `PTHR19241`, and at least one family for each check the survey found non-zero.

#### Scenario: Golden families

- **WHEN** the sample is unpacked
- **THEN** the sha256 of each `PTHR10366` and `PTHR15126` file starts with the digits in legacy behaviour spec §7.1, and the species tree's sha256 equals the one there

#### Scenario: Every variant

- **WHEN** the survey is run on the sample tarball
- **THEN** every check that is non-zero for the full library is non-zero for the sample

### Requirement: Building the sample

The engine's command line SHALL build the sample tarball from the PAML_RST archive, the species tree and a list of families. The same inputs MUST give a byte-identical tarball. It MUST refuse an archive whose sha256 isn't the one pinned in legacy behaviour spec §7.1, and then write nothing.

#### Scenario: Reproducible

- **WHEN** the sample is built twice from the same inputs
- **THEN** the two tarballs are byte-identical

#### Scenario: Wrong archive

- **WHEN** the build is given an archive whose sha256 differs from the pinned one
- **THEN** it exits with a non-zero status naming both checksums, and writes no tarball

### Requirement: Fetching the sample

The engine's command line SHALL fetch the sample tarball named in the committed manifest, check its sha256 before unpacking, unpack it into the data folder and check every file against the manifest. When the folder already matches the manifest, it MUST download nothing.

#### Scenario: Fresh fetch

- **WHEN** a user runs `panther-engine csnp sample fetch` with an empty data folder
- **THEN** the sample's files are in the cSNP data folder, each matches the manifest, and the command exits with status 0

#### Scenario: Already fetched

- **WHEN** the data folder already matches the manifest
- **THEN** the command downloads nothing and exits with status 0

#### Scenario: Wrong checksum

- **WHEN** the downloaded tarball's sha256 differs from the manifest's
- **THEN** nothing is unpacked, and the command exits with a non-zero status naming both checksums

#### Scenario: Unsafe paths

- **WHEN** the tarball holds a member with an absolute path, a `..` component or a link
- **THEN** nothing is unpacked, and the command exits with a non-zero status naming the member

#### Scenario: Local copy

- **WHEN** a user passes a local copy of the tarball
- **THEN** the command checks and unpacks it as it would a download, without using the network

### Requirement: Verifying the sample

The engine's command line SHALL check a data folder against the sample manifest, list each file that is missing or differs, and exit with a non-zero status if there is any.

#### Scenario: Changed file

- **WHEN** one byte of a sample `.paml` file has changed
- **THEN** `panther-engine csnp sample verify` lists that file and exits with a non-zero status
