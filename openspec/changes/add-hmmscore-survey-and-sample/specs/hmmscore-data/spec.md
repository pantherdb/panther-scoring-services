# Spec Delta

## Purpose

The data the hmmscore service scores with:

- reading the PANTHER 19 HMM library's names and models;
- the one-time survey of the library's tarball;
- the pinned library, with fetching and verifying it;
- the data sample that developers and CI test against.

## ADDED Requirements

### Requirement: Reading names.tab

The engine SHALL read `globals/names.tab` as lines of an HMM key and a name, separated by one tab:

- `PTHRnnnnn.mag.mod` is a family, read as the HMM ID `PTHRnnnnn`;
- `PTHRnnnnn.SFn.mod` is a subfamily, read as `PTHRnnnnn:SFn`.

Any other line, a repeated ID or a carriage return MUST be a format error that names the file and the 1-based line number.

#### Scenario: Family line

- **WHEN** a line is `PTHR10003.mag.mod`, a tab and `CU/ZN SUPEROXIDE DISMUTASE`
- **THEN** the engine reads the ID `PTHR10003` with the name `CU/ZN SUPEROXIDE DISMUTASE`

#### Scenario: Subfamily line

- **WHEN** a line is `PTHR10003.SF38.mod`, a tab and `EXTRACELLULAR SUPEROXIDE DISMUTASE`
- **THEN** the engine reads the ID `PTHR10003:SF38`

#### Scenario: Malformed line

- **WHEN** line 7 of the file has no tab
- **THEN** the engine raises a format error naming the file and line 7

#### Scenario: Repeated ID

- **WHEN** two lines of the file have the key `PTHR10003.SF38.mod`
- **THEN** the engine raises a format error naming the file and the second line

### Requirement: Reading HMM files

The engine SHALL read an HMMER3 text file as a sequence of models, each from its `HMMER3/` format line to its `//` line. It gives each model's format line, `NAME`, `LENG` and bytes. Each of these MUST be a format error naming the file and line:

- a model without `NAME` or `LENG`;
- text outside a model;
- a missing `//`;
- a carriage return.

A model file in `books/` MUST hold exactly one model.

#### Scenario: A model file

- **WHEN** the engine reads a `books/` model file whose format line is `HMMER3/f [3.1b2 | February 2015]`
- **THEN** it gives one model with that format line, its `NAME` and its `LENG`

#### Scenario: Two models in a model file

- **WHEN** a `books/` model file holds two models
- **THEN** the engine raises a format error naming the file and the second model's first line

#### Scenario: Truncated model

- **WHEN** a file ends before its last model's `//` line
- **THEN** the engine raises a format error naming the file and its last line

### Requirement: The legacy readings

Beside the strict readers, the engine SHALL read names and model names as `pantherScore.pl` does:

- **A `names.tab` line** is keyed by the text before its first `.`, then a `:` and the text between its first and second `.`, unless that is empty or `mag`. The line's tab doesn't stop the split.
- **A model name** maps to its first `.` part, then a `:` and its second part when that starts with `SF` and a digit.

#### Scenario: Subfamily model

- **WHEN** a model is named `PTHR32401.SF33.pir`
- **THEN** its legacy HMM ID is `PTHR32401:SF33`

#### Scenario: Family model

- **WHEN** a model is named `PTHR38402.orig.30.pir`
- **THEN** its legacy HMM ID is `PTHR38402`

#### Scenario: Loose match

- **WHEN** a model is named `PTHR10000.SF5x.pir`
- **THEN** its legacy HMM ID is `PTHR10000:SF5x`

#### Scenario: Key without its suffix

- **WHEN** a `names.tab` line is `PTHR10000.SF55`, a tab and `A NAME`
- **THEN** the strict reader rejects the line, and its legacy key is `PTHR10000:SF55`, a tab and `A NAME`

### Requirement: Library survey

The engine's command line SHALL survey the hmmscore library's tarball, reading it as a stream without unpacking it to disk. It MUST report:

- the tarball's sha256 and size;
- for each check, the count found and up to five examples.

It MUST exit with status 0 when the tarball was read to the end, whatever the checks found.

#### Scenario: Survey a tarball

- **WHEN** a user runs `panther-engine hmmscore survey` on `PANTHER19.0_hmmscoring.tgz`
- **THEN** it prints the tarball's sha256 and size, and each check's count and examples, and exits with status 0

#### Scenario: Nothing written

- **WHEN** the survey runs
- **THEN** no library file is written to disk; only the report is written, and only where the user asks for one

#### Scenario: Unreadable tarball

- **WHEN** the survey is given a file that isn't a gzipped tar archive, or one that ends early
- **THEN** it reports the problem and exits with a non-zero status

### Requirement: Survey of the tarball's members

The survey SHALL sort every member into a kind:

- the README;
- each `globals/` file;
- family model files and subfamily model files;
- each family's `cluster.pir` and `tree.tree`;
- anything else, as unexpected.

It gives each kind's count and bytes. It MUST report any member outside the tarball's one top folder, and the total bytes of the members fetching keeps.

#### Scenario: Unexpected member

- **WHEN** the tarball holds `books/PTHR10000/notes.txt`
- **THEN** the survey reports it as unexpected

#### Scenario: Kept bytes

- **WHEN** the survey reads a tarball
- **THEN** it reports the bytes of the README, the `globals/` files and the model files together, apart from the bytes of everything else

### Requirement: Survey of names and models

The survey SHALL report:

- each `names.tab` ID without its model file in `books/`, and each model file without its `names.tab` line;
- each model file that doesn't read;
- the count of each format line and each shape of model name;
- each line whose legacy key differs from its strict ID;
- each model file whose legacy ID isn't the ID of its own path.

#### Scenario: Missing model file

- **WHEN** `names.tab` has `PTHR10000.SF5.mod` and the tarball has no `books/PTHR10000/SF5/hmmer.hmm`
- **THEN** the survey reports `PTHR10000:SF5` as having no model file

#### Scenario: A subfamily model named for its family

- **WHEN** `books/PTHR38402/SF1/hmmer.hmm` holds a model named `PTHR38402.orig.30.pir`
- **THEN** the survey reports it among the model files whose legacy ID, `PTHR38402`, isn't their path's, `PTHR38402:SF1`

### Requirement: Survey of one-subfamily families

For each family with exactly one subfamily, the survey SHALL report whether the subfamily's model file is byte for byte the family's.

#### Scenario: A copy

- **WHEN** a family's only subfamily has a model file identical to the family's
- **THEN** the survey counts the family among the copies

#### Scenario: A different model

- **WHEN** a family's only subfamily has a model file that differs from the family's
- **THEN** the survey counts the family among those whose subfamily differs, and gives it as an example

### Requirement: Survey of binHmm

The survey SHALL list `globals/binHmm`'s models by name, in order. It reads them from the flat file when the tarball has one, otherwise from the pressed index. It MUST report:

- the model count and any repeated names;
- each model whose legacy ID has no model file in `books/`;
- each `books/` model name that `binHmm` lacks.

With the flat file, it MUST also report each model whose text differs from the `books/` model of that name.

#### Scenario: No model file for alignment

- **WHEN** `binHmm` holds a model named `PTHR10000.SF9.pir` and the tarball has no `books/PTHR10000/SF9/hmmer.hmm`
- **THEN** the survey reports that model as having no model file

#### Scenario: Repeated name

- **WHEN** `binHmm` holds two models named `PTHR38402.orig.30.pir`
- **THEN** the survey reports the name as repeated

### Requirement: Survey of binHmm's models without a model file

The survey SHALL report each `binHmm` model whose name no `books/` model file holds, with the model file its legacy ID leads to: the file the CGI aligns its hits with.

#### Scenario: A model no model file holds

- **WHEN** `binHmm` holds a model named `PTHR35774.SF1.pir`, and `books/PTHR35774/SF1/hmmer.hmm` holds one named `PTHR35774.orig.30.pir`
- **THEN** the survey reports `PTHR35774.SF1.pir`, with that model file

### Requirement: Survey of the pressed files

The survey SHALL report, for each pressed `binHmm` file in the tarball (`.h3f`, `.h3i`, `.h3m`, `.h3p`), its size and the HMMER format that its first bytes declare.

#### Scenario: Format 3/f

- **WHEN** `globals/binHmm.h3f` starts with HMMER's magic number for format 3/f
- **THEN** the survey reports the file as format 3/f

### Requirement: The pinned library

The engine SHALL pin one hmmscore library in a committed manifest. It gives:

- the tarball, by URL, size and sha256;
- its member prefix and the number of model files;
- the sha256 of the README, each `globals/` file and `books.sha256`.

`books.sha256` MUST list the sha256 of every model file, sorted by path, in `sha256sum`'s format, with paths relative to `hmmscore/19/`.

#### Scenario: Pins

- **WHEN** the manifest is read
- **THEN** it pins `https://data.pantherdb.org/ftp/hmm_scoring/19.0/PANTHER19.0_hmmscoring.tgz` at 18,494,793,691 bytes with the sha256 the survey reported, and the prefix `target/famlib/rel/PANTHER19.0_altVersion/hmmscoring/PANTHER19.0/`

#### Scenario: Checked by hand

- **WHEN** a user runs `shasum -a 256 -c books.sha256` in `hmmscore/19/` after a fetch
- **THEN** every line reports OK

### Requirement: Data layout

The hmmscore library SHALL be under `hmmscore/19/` in the data folder, at the paths it has in the tarball below the member prefix. It MUST keep only:

- the README;
- the `globals/` files;
- the model files;
- `books.sha256`.

#### Scenario: Kept files

- **WHEN** the library is fetched
- **THEN** `hmmscore/19/` holds the README, `books.sha256`, the `globals/` files and every model file, such as `books/PTHR10000/SF55/hmmer.hmm`

#### Scenario: Skipped files

- **WHEN** the library is fetched
- **THEN** no `cluster.pir` or `tree.tree` is written

### Requirement: Pinning the library

`panther-engine hmmscore data manifest` SHALL write the manifest from the library's tarball, reading it once as a stream. The same tarball MUST give the same bytes. It MUST write nothing, and name the problem, when the tarball has any of these:

- an unexpected member;
- a member outside its prefix;
- a model file that doesn't read.

#### Scenario: Reproducible manifest

- **WHEN** the command is run twice on the same tarball with the same URL
- **THEN** the two manifests are byte-identical

#### Scenario: Unexpected member when pinning

- **WHEN** the tarball holds `books/PTHR10000/notes.txt`
- **THEN** the command writes nothing, and exits with a non-zero status naming the member

### Requirement: Fetching the library

`panther-engine hmmscore data fetch` SHALL stream the pinned tarball, from its URL or a local copy, and keep only the members the data layout lists. It MUST check these before it moves anything under `hmmscore/19/`:

- the tarball's size and sha256;
- every kept file.

When the folder already matches the pin, it MUST download nothing.

#### Scenario: Fresh fetch of the library

- **WHEN** a user runs the fetch with an empty data folder
- **THEN** every file under `hmmscore/19/` matches the pin, and the command exits with status 0

#### Scenario: Library already fetched

- **WHEN** the data folder already matches the pin
- **THEN** the command downloads nothing, and exits with status 0

#### Scenario: Wrong library checksum

- **WHEN** the tarball's sha256 differs from the pin
- **THEN** nothing is written under `hmmscore/19/`, and the command exits with a non-zero status naming both checksums

#### Scenario: Unexpected or unsafe member

- **WHEN** the tarball holds a member that isn't in the data layout, such as `books/PTHR10000/notes.txt` or a path with a `..` component
- **THEN** nothing is written under `hmmscore/19/`, and the command exits with a non-zero status naming the member

#### Scenario: Local copy of the library

- **WHEN** a user passes a local copy of the tarball
- **THEN** the command checks and uses it as it would the download, without using the network

### Requirement: Verifying the library

`panther-engine hmmscore data verify` SHALL check a data folder against the pin, every model file included through `books.sha256`. It lists each file that is missing or differs, and MUST exit with a non-zero status if there is any.

#### Scenario: Changed model file

- **WHEN** one byte of `books/PTHR10000/hmmer.hmm` has changed
- **THEN** the command lists that file, and exits with a non-zero status

#### Scenario: Changed list

- **WHEN** `books.sha256` differs from its pin
- **THEN** the command lists `books.sha256`, and exits with a non-zero status

### Requirement: Data sample contents

The data sample SHALL hold, under `hmmscore/19/` and laid out as the full library:

- the README;
- each chosen family's model files, byte for byte;
- their `names.tab` lines, in the full file's order;
- four pressed files, made by the pinned HMMER, of the models the full `binHmm` holds for those families, in its order.

#### Scenario: The library's files

- **WHEN** the sample is unpacked
- **THEN** each model file's sha256 is its line in the pinned `books.sha256`, and the README's sha256 is the pin's

#### Scenario: Every variant

- **WHEN** the survey is run on the sample tarball
- **THEN** every check on families or models that is non-zero for the full library is non-zero for the sample

#### Scenario: The example's best hit

- **WHEN** `hmmscan` runs the site's example, human APOE, against the sample
- **THEN** its highest-scoring model is the one it is against the full library

### Requirement: The sample's models as shipped

The sample's pressed files SHALL be pressed from the library's own models. When the library has a flat `globals/binHmm`, they're pressed from its text, which the sample then holds too. When it has none, they're pressed from those models' records in `binHmm.h3m`, as they are.

#### Scenario: The models as shipped

- **WHEN** the sample is built from a library without a flat `binHmm`
- **THEN** the sample's `binHmm.h3m` is the chosen families' records from the library's `binHmm.h3m`, byte for byte, and the sample holds no `globals/binHmm`

### Requirement: Building the sample

The engine's command line SHALL build the sample tarball from the pinned library tarball and a list of families, pressing the sample's `binHmm` with the pinned HMMER. The same inputs MUST give a byte-identical tarball. It MUST write nothing when given either of these:

- a library tarball whose sha256 isn't the pin;
- an `hmmpress` that isn't the pinned version.

#### Scenario: Reproducible sample

- **WHEN** the sample is built twice from the same inputs on the same machine
- **THEN** the two tarballs are byte-identical

#### Scenario: Wrong tarball

- **WHEN** the build is given a tarball whose sha256 differs from the pin
- **THEN** it exits with a non-zero status naming both checksums, and writes no tarball

#### Scenario: Wrong HMMER

- **WHEN** the `hmmpress` found reports a version other than the pinned one
- **THEN** the build exits with a non-zero status naming both versions, and writes no tarball

### Requirement: Fetching the sample

The engine's command line SHALL fetch the sample tarball named in the committed manifest. It checks the tarball's sha256 before unpacking, unpacks it into the data folder, and checks every file against the manifest. When the folder already matches the manifest, it MUST download nothing.

#### Scenario: Fresh fetch of the sample

- **WHEN** a user runs `panther-engine hmmscore sample fetch` with an empty data folder
- **THEN** the sample's files are under `hmmscore/19/`, each matches the manifest, and the command exits with status 0

#### Scenario: Sample already fetched

- **WHEN** the data folder already matches the manifest
- **THEN** the command downloads nothing, and exits with status 0

#### Scenario: Wrong sample checksum

- **WHEN** the downloaded tarball's sha256 differs from the manifest's
- **THEN** nothing is unpacked, and the command exits with a non-zero status naming both checksums

#### Scenario: Unsafe paths

- **WHEN** the tarball holds a member with an absolute path, a `..` component or a link
- **THEN** nothing is unpacked, and the command exits with a non-zero status naming the member

#### Scenario: Local copy of the sample

- **WHEN** a user passes a local copy of the tarball
- **THEN** the command checks and unpacks it as it would a download, without using the network

### Requirement: Verifying the sample

The engine's command line SHALL check a data folder against the sample manifest, list each file that is missing or differs, and exit with a non-zero status if there is any.

#### Scenario: Changed file

- **WHEN** one byte of a sample model file has changed
- **THEN** `panther-engine hmmscore sample verify` lists that file, and exits with a non-zero status

### Requirement: The sample's pressed files on both architectures

`hmmscan` from the pinned HMMER SHALL search the sample's pressed files on `linux/amd64` and on `linux/arm64`. On each, its table for the site's example, without the table's `#` lines, MUST equal the committed table for that architecture. The two tables can differ: HMMER 3.4 computes a few scores differently on each.

#### Scenario: Each architecture

- **WHEN** the engine's tests run in the engine image on `linux/amd64` and on `linux/arm64`, with the sample in the data folder
- **THEN** `hmmscan`'s table for the site's example against the sample equals that architecture's committed table

### Requirement: The hmmscore sample in CI

CI SHALL fetch the hmmscore data sample, and run the engine's tests with data required, natively and in the engine image on both architectures. No test that needs the sample MUST be skipped. CI SHALL download the sample only when its manifest has changed since its last download.

#### Scenario: In CI

- **WHEN** CI runs the engine's tests
- **THEN** the hmmscore sample is in the data folder, data is required, and no test that needs it is skipped

#### Scenario: Unchanged manifest

- **WHEN** CI runs again with the same sample manifest
- **THEN** it doesn't download the sample
