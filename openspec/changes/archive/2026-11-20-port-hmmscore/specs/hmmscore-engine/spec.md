# Spec Delta

## Purpose

Scoring one protein sequence against PANTHER's HMM library, as the legacy `scoreAlignXml.cgi` and the `pantherScore.pl` it ran did. It covers the hit and its alignment, the data check and version, the `hmmscore score` command, and the parity checks that prove the port matches the Perl.

## ADDED Requirements

### Requirement: Scoring one protein

The engine SHALL score one protein against the HMM library in the data folder. It takes the sequence as the API sends it: no header or whitespace, upper-cased, and holding only letters, `.`, `_`, `~` and `*`. It SHALL return the best hit, or no hit. A protein's result MUST NOT depend on anything scored before it.

#### Scenario: The site's example

- **WHEN** the help page's APOE is scored against the data sample
- **THEN** the hit's PANTHER ID is `PTHR18976:SF2` and its score is `439.0`, as the reference gives

#### Scenario: Order of calls

- **WHEN** APOE is scored, then `test.fasta`'s protein, then APOE again
- **THEN** both APOE results are identical

### Requirement: The fields of a hit

A hit SHALL give its PANTHER ID; the name that `names.tab` gives that ID; the full-sequence E-value and bit score, exactly as `hmmscan` printed them; and the alignment. If `names.tab` has no name for the hit's ID, its name SHALL be "No name".

#### Scenario: Values as printed

- **WHEN** APOE is scored against the data sample
- **THEN** the hit's E-value and score are the strings in `hmmscan`'s table for that model, such as `439.0`, not a number reformatted

#### Scenario: Name

- **WHEN** APOE is scored against the data sample
- **THEN** the hit's name is the one `names.tab` gives `PTHR18976:SF2`

#### Scenario: No name

- **WHEN** a protein is scored against a library whose `names.tab` has no line for its best hit's ID
- **THEN** the hit's name is "No name"

#### Scenario: An empty name

- **WHEN** a protein is scored against a library whose `names.tab` line for its best hit's ID has an empty name
- **THEN** the hit's name is "No name"

### Requirement: The search

The engine SHALL search the whole library with `hmmscan`, as `pantherScore.pl` did. The query MUST be named `sequence`, the name the CGI gave a sequence with no header. Each search MUST run in a folder of its own, and the folder MUST be removed when scoring ends, whether it succeeds or fails.

#### Scenario: Two at once

- **WHEN** two different proteins are scored at the same time against the data sample
- **THEN** each gets the result it gets when scored alone

#### Scenario: The query's name

- **WHEN** APOE is scored against the data sample
- **THEN** the alignment names the query `sequence`

### Requirement: The best hit

The best hit SHALL be the model `hmmscan` reports with the highest full-sequence bit score, then, among models with that score, the smallest E-value, both compared as numbers. If that E-value is over 1e-3, there SHALL be no hit, even when a lower-scoring model's E-value is under 1e-3. An E-value of exactly 1e-3 SHALL be kept.

#### Scenario: Score first

- **WHEN** `hmmscan`'s table has one model at 50.1 bits with E-value `2e-05`, and another at 48.0 bits with E-value `1e-06`
- **THEN** the best hit is the 50.1-bit model

#### Scenario: Over the cutoff

- **WHEN** the highest-scoring model's E-value is `0.0011`, and a lower-scoring model's is `1e-05`
- **THEN** there is no hit

#### Scenario: At the cutoff

- **WHEN** the highest-scoring model's E-value is `0.001`
- **THEN** it is the hit

#### Scenario: No model reported

- **WHEN** `hmmscan` reports no model for the protein
- **THEN** there is no hit

### Requirement: Tied best hits

When several PANTHER IDs share the best score and E-value, the engine SHALL report a subfamily before its own family, and otherwise the lowest PANTHER ID, with subfamily numbers compared as numbers. This is divergence 13: the reference showed one of them, in hash order.

#### Scenario: A one-subfamily family

- **WHEN** PTHR35774's consensus is scored against the data sample, and its family and subfamily models tie
- **THEN** the hit is `PTHR35774:SF1`

#### Scenario: Lowest ID

- **WHEN** `PTHR10000:SF10`, `PTHR10000:SF2` and `PTHR20000` tie in `hmmscan`'s table
- **THEN** the hit is `PTHR10000:SF2`

### Requirement: The reported ID

A model's PANTHER ID SHALL be its name up to the first `.`. If the next part starts with `SF` and a digit, the ID SHALL add `:` and that part, as `pantherScore.pl` read it (387 to 389).

#### Scenario: A subfamily model

- **WHEN** the best model is `PTHR18976.SF2.pir`
- **THEN** the hit's PANTHER ID is `PTHR18976:SF2`

#### Scenario: A family's `..pir` model

- **WHEN** the best model is `PTHR34093..pir`
- **THEN** the hit's PANTHER ID is `PTHR34093`

### Requirement: The alignment

The alignment SHALL be `hmmsearch`'s report of the model file at the hit's PANTHER ID, run against the query, as the CGI took it. It starts at the line after "Domain annotation for each sequence" and ends before "Internal pipeline statistics summary:", without the CGI's `&gt;` and `&lt;` escaping. A model with no file of its own gets the file at its ID, which holds another model (`HMMSCORE-9`), as in the reference.

#### Scenario: The example's alignment

- **WHEN** APOE is scored against the data sample
- **THEN** the alignment equals the reference's, with `>` where the CGI printed `&gt;`

#### Scenario: Another model's file

- **WHEN** a protein whose best model is `PTHR34093..pir` is scored against the data sample
- **THEN** the alignment is `hmmsearch`'s report of PTHR34093's family model file, as the reference's is

### Requirement: Sequences the API wouldn't send

Before running any tool, the engine SHALL refuse a sequence the API never sends: an empty one, one with a character other than an upper-case letter, `.`, `_`, `~` or `*`, or one with no letter. The error MUST NOT be the input error. The residue limit is the API's setting, so the engine MUST NOT apply one.

#### Scenario: Lower case

- **WHEN** `mkvl` is scored
- **THEN** scoring fails with an error that isn't the input error, and no tool runs

#### Scenario: No letter

- **WHEN** `*` is scored
- **THEN** scoring fails with an error that isn't the input error, and no tool runs

#### Scenario: Past the API's limit

- **WHEN** a sequence of 10,001 letters is scored against the data sample
- **THEN** it is scored

### Requirement: The time limit

Given a time limit in seconds, the engine SHALL apply it to the whole search, `hmmscan` and `hmmsearch` together. Past it, the engine SHALL stop the running tool, and raise its input error with the message "The search took longer than this service allows. Try a shorter sequence." With no time limit, scoring isn't limited.

#### Scenario: Too long

- **WHEN** a protein is scored with a time limit shorter than `hmmscan` takes
- **THEN** scoring raises the input error with that message, no tool is left running, and the search's folder is removed

### Requirement: Threads

The engine SHALL pass a caller's thread count to `hmmscan` and `hmmsearch` as `--cpu`. The count is 0 when the caller gives none. The result MUST NOT depend on the count.

#### Scenario: Two counts

- **WHEN** APOE is scored against the data sample with a thread count of 0, then 2
- **THEN** the two results are identical

### Requirement: Tool failures

When `hmmscan` or `hmmsearch` exits with an error status or writes no output, or the hit's model file is missing, the engine SHALL fail with an error that isn't the input error. It MUST NOT report no hit instead. The reference ignored both exit statuses (`HMMSCORE-8`, `HMMSCORE-11`).

#### Scenario: Damaged library

- **WHEN** a protein is scored against a library whose pressed files `hmmscan` can't read
- **THEN** scoring fails with an error that isn't the input error

#### Scenario: Missing model file

- **WHEN** a protein is scored, and the model file at its best hit's ID is missing
- **THEN** scoring fails with an error that isn't the input error, and that names the missing file

### Requirement: Data check

The engine SHALL offer a check that the data folder holds the hmmscore library: `globals/names.tab`, the four pressed files of `globals/binHmm`, and `books/`. The check MUST fail with an error that names what's missing. It MUST NOT read the files' contents. Scoring SHALL run the check first.

#### Scenario: Data in place

- **WHEN** the check runs on a data folder with the data sample fetched
- **THEN** it passes

#### Scenario: One file missing

- **WHEN** `globals/binHmm.h3p` is removed from the data folder and the check runs
- **THEN** it fails and names `globals/binHmm.h3p`

### Requirement: Data version

The engine SHALL publish the PANTHER release of the library hmmscore reads, as `DATA_VERSION` from `panther_engine.hmmscore`. It MUST be the release whose folder scoring reads, `hmmscore/<release>/` under the data folder. Reading it MUST NOT need the data folder.

#### Scenario: hmmscore's release

- **WHEN** a caller reads `DATA_VERSION` from `panther_engine.hmmscore`, with `PANTHER_DATA_DIR` unset
- **THEN** it is `"19"`, the release of the `hmmscore/19/` folder scoring reads

### Requirement: Scoring from the command line

`panther-engine hmmscore score` SHALL score one protein, given as a FASTA file or on standard input. It normalises the protein as the API does, then prints the hit's fields, or says there's no hit. `--json` prints the result as JSON. `--cpu` and `--timeout` set the thread count and the time limit. An error MUST go to standard error, with a non-zero exit status.

#### Scenario: The example

- **WHEN** `panther-engine hmmscore score` is run on `example/apoe.fasta` with the data sample
- **THEN** it prints `PTHR18976:SF2`, its name, E-value and score, and the alignment, and exits with status 0

#### Scenario: JSON

- **WHEN** the same command is run with `--json`
- **THEN** it prints one JSON object with a `hit` holding `panther_id`, `name`, `evalue`, `score` and `alignment`

#### Scenario: A sequence the API would refuse

- **WHEN** the command is run on a FASTA file whose sequence holds a digit
- **THEN** it prints an error to standard error and exits with a non-zero status

### Requirement: Parity with the reference

The engine's tests SHALL check scoring against golden files that the reference image made on the data sample, for every case in the golden set. Each result MUST equal the one the reference's best-hit lines and `hmmsearch` reports give, with ties resolved as divergence 13 says. A difference MUST fail the tests, unless `docs/parity/divergences.md` has an approved row for it.

#### Scenario: The goldens

- **WHEN** the tests run with the data sample and HMMER 3.4 on amd64
- **THEN** every golden case gives exactly its golden result

#### Scenario: A difference

- **WHEN** one golden's E-value is changed by hand
- **THEN** the tests fail and name that case

#### Scenario: A tie

- **WHEN** a golden case's best-hit lines list several tied PANTHER IDs
- **THEN** the engine's hit is the one divergence 13 picks among them

### Requirement: Reference image

A test-only image SHALL run `scoreAlignXml.cgi` and `pantherScore.pl` at the parity reference, `89ea0ae` of `pantherdb/pantherScoring`, with HMMER 3.1b2, production's version. Each script MUST match its pinned sha256, or the image fails to build. The runtime images MUST NOT contain the scripts, HMMER 3.1b2 or Debian's `perl` package.

#### Scenario: Changed script

- **WHEN** the image is built from a checkout whose `pantherScore.pl` doesn't match its pinned sha256
- **THEN** the build fails, naming `pantherScore.pl`

#### Scenario: Runtime image

- **WHEN** the API image is built
- **THEN** it holds no `pantherScore.pl`, no HMMER 3.1b2 and no Debian `perl` package

### Requirement: Parity run

`panther-engine hmmscore parity check` SHALL score every case of the golden set against a data folder, and compare each result with the reference's outputs made on that data folder, such as the full library. It SHALL report every case that differs and each case's time, and exit with a non-zero status if any case differs.

#### Scenario: The full library

- **WHEN** the parity run is given the full library and the reference's outputs made on it
- **THEN** it reports each case's time and no differences, and exits with status 0

#### Scenario: Missing outputs

- **WHEN** the parity run is given a case with no reference outputs
- **THEN** it names that case and exits with a non-zero status
