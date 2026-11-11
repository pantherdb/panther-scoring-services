# refmap-data Specification

## Purpose

The PANTHER 19 classification files that refmap maps against. It covers the pinned release, the organism list generated from it, fetching it with each file saved under its organism code, and checking a data folder against it.

## Requirements

### Requirement: The pinned release

The engine SHALL pin one release of the refmap data in a committed manifest. The manifest gives:

- the 2024-06-20 tarball and its `stats` on `data.pantherdb.org`, each by URL, size and sha256;
- the sha256 of each file as laid out in the data folder.

#### Scenario: Pins

- **WHEN** the manifest is read
- **THEN** the tarball's sha256 is `74821b948aaae9482a36dea76595fd0233b3bdfc981fbf39890e0d9f515637af`, `stats`'s is `c48ae2f57cd2ea1d31467dd0516e55b764ff5a327ff5187265ba95c87e4b612e`, and it lists 1,534 files: `stats`, and one classification file per organism

### Requirement: Data layout

The refmap data SHALL be under `refmap/19/` in the data folder:

- `stats`, as published;
- each organism's classification file, byte for byte as published, at `panther_classification/<code>`.

No file name MUST contain a character that Windows refuses in a file name.

#### Scenario: A long name with a colon

- **WHEN** the data is fetched
- **THEN** `Escherichia_coli_O157:H7_ECO57`'s classification file is at `refmap/19/panther_classification/ECO57`, byte for byte the tarball's member

#### Scenario: Names Windows accepts

- **WHEN** the files under `refmap/19/` are listed after a fetch
- **THEN** no file name contains `:`, or any other character Windows refuses

### Requirement: Fetching the data

`panther-engine refmap data fetch` SHALL:

- download the pinned tarball and `stats`, and check each one's sha256 before using it;
- save each classification file under its organism's code;
- check every file against the manifest.

When the folder already matches the manifest, it MUST download nothing.

#### Scenario: Fresh fetch

- **WHEN** a user runs the fetch with an empty data folder
- **THEN** every file under `refmap/19/` matches the manifest, and the command exits with status 0

#### Scenario: Already fetched

- **WHEN** the data folder already matches the manifest
- **THEN** the command downloads nothing, and exits with status 0

#### Scenario: Wrong checksum

- **WHEN** the downloaded tarball's sha256 differs from the manifest's
- **THEN** nothing is written under `refmap/19/`, and the command exits with a non-zero status naming both checksums

#### Scenario: Unexpected member

- **WHEN** the tarball holds a member that isn't a regular file, or whose name isn't the long name of an organism in the list
- **THEN** nothing is written under `refmap/19/`, and the command exits with a non-zero status naming the member

#### Scenario: Local copies

- **WHEN** a user passes local copies of the tarball and `stats`
- **THEN** the command checks and uses them as it would downloads, without using the network

### Requirement: Verifying the data

`panther-engine refmap data verify` SHALL check a data folder against the manifest, list each file that is missing or differs, and exit with a non-zero status if there is any.

#### Scenario: Changed file

- **WHEN** one byte of `ENDPU`'s classification file has changed
- **THEN** the command lists `refmap/19/panther_classification/ENDPU`, and exits with a non-zero status

### Requirement: The organism list

The organisms the engine publishes SHALL be generated from the pinned `stats`, and committed:

- one organism per line;
- its code is the last `_` part of its long name;
- its gene counts are its `stats` line's, which equal its file's lines and those with a PANTHER ID;
- the list is in long-name order.

A test with the data MUST fail when the data folder's `stats` gives a different list.

#### Scenario: Matches the data

- **WHEN** the organism list is generated from the `stats` in a data folder with the pinned data
- **THEN** it equals the committed list

### Requirement: Pinning a release

`panther-engine refmap data manifest` SHALL write the manifest and the organism list from a release's tarball and `stats`. It reads the tarball as a stream, without unpacking it. It MUST write nothing, and name the problem, when any of these holds:

- an organism in `stats` has no file, or a file has no line in `stats`;
- a file's line counts differ from its `stats` line;
- the codes aren't unique;
- a code isn't 1 to 5 upper-case letters or digits, or is a Windows device name.

#### Scenario: Reproducible

- **WHEN** the command is given the pinned tarball and `stats`, with their URLs
- **THEN** it writes the committed manifest and organism list, byte for byte

#### Scenario: Counts disagree

- **WHEN** a file has one more line than its `stats` line counts
- **THEN** the command writes nothing, and exits with a non-zero status naming the organism

#### Scenario: Repeated code

- **WHEN** two long names in `stats` end in the same code
- **THEN** the command writes nothing, and exits with a non-zero status naming both

#### Scenario: Device name

- **WHEN** a long name in `stats` ends in `_CON`
- **THEN** the command writes nothing, and exits with a non-zero status naming it

### Requirement: The refmap data in CI

CI SHALL fetch the pinned refmap data, and run the engine's tests with data required, both natively and in the engine image, so that no test that needs the data is skipped. It SHALL download the release only when the manifest has changed since its last download.

#### Scenario: In CI

- **WHEN** CI runs the engine's tests
- **THEN** the refmap data is in the data folder, data is required, and no test that needs it is skipped

#### Scenario: Unchanged manifest

- **WHEN** CI runs again with the same manifest
- **THEN** it doesn't download the release from `data.pantherdb.org`
