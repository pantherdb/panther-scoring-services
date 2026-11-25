# Spec Delta

## Purpose

The data the treegrafter service grafts with: the pinned PANTHER 19 TreeGrafter library and PAINT annotation releases, fetching, preparing and verifying them, choosing the release grafting reads, and the fixture that developers and CI test against.

## ADDED Requirements

### Requirement: The pinned library

The engine SHALL pin one treegrafter library in a committed manifest. It gives the tarball by URL, size and sha256, its member prefix, its number of families, and the sha256 of `library.sha256`. `library.sha256` MUST list the sha256 of every file the data layout keeps, sorted by path, in `sha256sum`'s format, with paths relative to `treegrafter/19/`.

#### Scenario: Pins

- **WHEN** the manifest is read
- **THEN** it pins `https://data.pantherdb.org/ftp/downloads/TreeGrafter/PANTHER19.0_data_trees_hmms_only.tar.gz` at 3,073,460,727 bytes with sha256 `789c31d7f1e051ae3dfdd4c6c41e97a970395cc490cab52da850d1b5abfd5e4f`, the prefix `PANTHER19.0_data/` and 15,683 families

#### Scenario: Checked by hand

- **WHEN** a user runs `shasum -a 256 -c library.sha256` in `treegrafter/19/` after a fetch
- **THEN** every line reports OK

### Requirement: Data layout

The treegrafter library SHALL be under `treegrafter/19/` in the data folder, at the paths it has in the tarball below the member prefix. It MUST keep only `famhmm/binHmm`, each family's `.AN.fasta`, `.bifurcate.newick` and `.newick` under `Tree_MSF/`, and `library.sha256`. Prepared annotation releases SHALL be under `treegrafter/19/annotations/<date>/`.

#### Scenario: Kept files

- **WHEN** the library is fetched
- **THEN** `treegrafter/19/` holds `famhmm/binHmm`, `library.sha256` and, for each family, such as PTHR10000, `Tree_MSF/PTHR10000.AN.fasta`, `Tree_MSF/PTHR10000.bifurcate.newick` and `Tree_MSF/PTHR10000.newick`

#### Scenario: Skipped files

- **WHEN** the library is fetched
- **THEN** no pressed `binHmm` file, `.tree` file, `PAINT_Annotations_README` or `tmp/` is written

### Requirement: Pinning the library

`panther-engine treegrafter data manifest` SHALL write the library's part of the manifest from its tarball, reading it once as a stream. The same tarball MUST give the same bytes. It MUST write nothing, and name the problem, when the tarball has an unexpected member, a member outside its prefix, or a family that lacks one of its three tree files.

#### Scenario: Reproducible manifest

- **WHEN** the command is run twice on the same tarball with the same URL
- **THEN** the two manifests are byte-identical

#### Scenario: Unexpected member when pinning

- **WHEN** the tarball holds `PANTHER19.0_data/Tree_MSF/notes.txt`
- **THEN** the command writes nothing, and exits with a non-zero status naming the member

### Requirement: Fetching the library

`panther-engine treegrafter data fetch` SHALL stream the pinned tarball, from its URL or a local copy, and keep only the members the data layout lists. It MUST check the tarball's size and sha256, and every kept file, before it moves anything under `treegrafter/19/`. When the folder already matches the pin, it MUST download nothing.

#### Scenario: Fresh fetch of the library

- **WHEN** a user runs the fetch with an empty data folder
- **THEN** every library file under `treegrafter/19/` matches the pin, and the command exits with status 0

#### Scenario: Library already fetched

- **WHEN** the data folder already matches the pin
- **THEN** the command downloads no library, and exits with status 0

#### Scenario: Wrong library checksum

- **WHEN** the tarball's sha256 differs from the pin
- **THEN** nothing is written under `treegrafter/19/`, and the command exits with a non-zero status naming both checksums

#### Scenario: Unsafe member

- **WHEN** the tarball holds a member that isn't in the data layout, or a path with a `..` component
- **THEN** nothing is written under `treegrafter/19/`, and the command exits with a non-zero status naming the member

#### Scenario: Local copy of the library

- **WHEN** a user passes a local copy of the tarball
- **THEN** the command checks and uses it as it would the download, without using the network

### Requirement: Pinned annotation releases

The manifest SHALL pin each PAINT annotation release the engine can fetch, by its date: the URL of its `PAINT_TreeGrafter_Annotations_TOTAL.txt.gz`, its size and sha256, and the GO release date its README states. It SHALL also pin the sha256 of the list of the release's prepared files.

#### Scenario: The current release at the time of writing

- **WHEN** the manifest is read
- **THEN** it pins release 2026-08-28 at `https://data.pantherdb.org/ftp/downloads/paint/19.0/2026-08-28/PAINT_TreeGrafter_Annotations_TOTAL.txt.gz`, 23,980,614 bytes, sha256 `03ad195b42a48ff2fb0caadd337bf2c98464382855618c1f14fe2869b3d6bf3f`, with GO release 2026-08-05

### Requirement: Fetching a release by date

`panther-engine treegrafter data fetch --annotations <date>` SHALL fetch that pinned release, from its URL or a local copy, check its size and sha256, prepare it, and make it the active release. It MUST refuse a date the manifest doesn't pin, and write nothing.

#### Scenario: A pinned date

- **WHEN** a user fetches release 2026-08-28 into a data folder that holds the library
- **THEN** `treegrafter/19/annotations/2026-08-28/` holds its prepared files, and it is the active release

#### Scenario: Wrong release checksum

- **WHEN** the downloaded file's sha256 differs from the release's pin
- **THEN** nothing changes under `treegrafter/19/annotations/`, and the command exits with a non-zero status naming both checksums

#### Scenario: An unpinned date

- **WHEN** a user asks for a date the manifest doesn't pin
- **THEN** nothing is downloaded or written, and the command exits with a non-zero status listing the pinned dates

### Requirement: Fetching the current release

With `--annotations current`, or no `--annotations`, the fetch SHALL download the file under `paint/current/` and resolve it to the pinned release with the same sha256, which it then fetches as by date. When no pinned release matches, it MUST write nothing, and name the file's sha256 and the GO release that `paint/current/README` states.

#### Scenario: The current release is pinned

- **WHEN** `paint/current/` holds the file pinned as release 2026-08-28
- **THEN** the fetch prepares release 2026-08-28, makes it active, and says that `current` is 2026-08-28

#### Scenario: The current release has moved on

- **WHEN** `paint/current/` holds a file whose sha256 no pinned release has
- **THEN** nothing changes under `treegrafter/19/annotations/`, and the command exits with a non-zero status naming the file's sha256 and its GO release

### Requirement: Preparing a release

Preparing a release SHALL run EBI's `prepare` on it, and keep its per-family files and a sha256 list of them under `annotations/<date>/`. Before the release becomes active, the engine MUST check that every node of every tree in the library has an entry, and that the list matches the release's pin. On a failure, nothing changes, and the missing nodes or differing files are named.

#### Scenario: Every node covered

- **WHEN** release 2026-08-28 is prepared against the full library
- **THEN** all 3,564,945 tree nodes have an entry, and the release becomes active

#### Scenario: A missing node

- **WHEN** a release without an entry for one tree node is prepared
- **THEN** it doesn't become active, and the command exits with a non-zero status naming that node

### Requirement: The active release

Grafting SHALL read the release that the last successful fetch made active. Making a release active MUST be atomic: a graft reads either the old release or the new one. Fetching a release that's already prepared and verified MUST make it active without downloading it again.

#### Scenario: Switching releases

- **WHEN** release 2026-08-28 is active, and a user fetches another pinned release
- **THEN** the other release becomes active, and both stay prepared under `annotations/`

#### Scenario: Back to a prepared release

- **WHEN** a user fetches release 2026-08-28 again, and it's still prepared and verified
- **THEN** nothing is downloaded, and release 2026-08-28 becomes active

### Requirement: Verifying the data

`panther-engine treegrafter data verify` SHALL check the library against the pin, every file included through `library.sha256`, and the active release's prepared files against their list. It lists each file that is missing or differs, and MUST exit with a non-zero status if there is any.

#### Scenario: Changed alignment

- **WHEN** one byte of `Tree_MSF/PTHR10000.AN.fasta` has changed
- **THEN** the command lists that file, and exits with a non-zero status

#### Scenario: Changed prepared file

- **WHEN** one prepared file of the active release has changed
- **THEN** the command lists that file, and exits with a non-zero status

### Requirement: The fixture

The engine's tests SHALL have a committed fixture of three whole families cut from the pinned library and release: PTHR18976, PTHR11442 and PTHR11034. It holds their HMMs in `famhmm/binHmm`, their tree files, and their lines of the release's annotation file, with each file's source and sha256 in its README. Tests prepare it with EBI's `prepare`.

#### Scenario: The same graft as the full library

- **WHEN** APOE is grafted against the prepared fixture, and against the full library with the same release
- **THEN** the two results are identical

#### Scenario: Prepared in a test

- **WHEN** a test prepares the fixture's annotation lines into a temporary data folder
- **THEN** the data check passes there

### Requirement: Building the fixture

`panther-engine treegrafter data fixture` SHALL cut the fixture from a fetched library and a fetched release, for the families it's given. The same library, release and families MUST give the same bytes.

#### Scenario: Rebuilt fixture

- **WHEN** the fixture is rebuilt from the pinned library and release 2026-08-28
- **THEN** every file is byte-identical to the committed fixture
