# `refmap`: The Legacy Service

What the legacy reference-proteome mapping does, as its code runs it, for the `refmap` port. cSNP has its behaviour spec in `panther-workspace`; `refmap` had none, so this is it. Written for `add-refmap-job` on 2026-10-30, from reading the code, and checked against RefProteomeMapper's `master` the same day. The classification files weren't in `panther-workspace`, so nothing was run then. They are public, and `port-refmap` added what the pinned release holds (The Data), from #52's survey of every file (2026-11-05). The deliberate differences are rows 9 and 10 in [divergences.md](divergences.md).

Paths are relative to `panther-workspace/legacy/`, with line numbers. Where the code doesn't settle something, it says **needs team verification**.

## The Service

`RefProteomeMapper/` (public, `pantherdb/RefProteomeMapper`) has two scripts. Its `master` is at `649c85f`, the merge on 2026-10-27 of four commits from 2020 (`1f965ae` to `64c6c47`) and a doc commit. Of the two scripts, they change only the CGI: it now loads `config.yaml` and opens `<panther_classification_directory>/panther_classification/<organism>` (The Data). `map_panther.pl` is unchanged since `4fc6a09` of 2019-07-26, so it stays the parity reference at that commit. The CGI's line numbers below are `master`'s; at `4fc6a09` they are 3 to 4 lower. Which of the two versions production ran needs team verification. `panther-workspace`'s copy is now at `649c85f`, with the same `map_panther.pl` (sha256 `ee535a9b935f439be29ae2eafda2c9c953b1abf5f4ab5623bcc7da1746919725` at both commits, checked 2026-11-06).

| Script | Role |
| ------ | ---- |
| `genericMapping.cgi` | What the website called. Reads `organism` and `fileContents` from a GET or POST form, loads the organism's classification file, and prints one line per input line |
| `map_panther.pl` | The CLI, with the same lookup: `-i` the classification file, `-g` the gene list. The parity reference (tech-stack.md, Runtime Tools and Milestones) |

The lookup, in both:

1. Read the classification file into a hash: each line's first tab field maps to its second (`map_panther.pl` 27 to 33, `genericMapping.cgi` 43 to 53).
2. For each input line, remove every `\r`, split on tab, and look up the first field (`map_panther.pl` 39 to 44, `genericMapping.cgi` 58 to 65).
3. Print `<id>\t<PANTHER ID>\t<rest of the line>`, or `<id>\tNOHIT\t<rest>` with no match (`map_panther.pl` 47 and 50, `genericMapping.cgi` 69 and 72). The rest is the line's other fields joined by tabs, so a line with only an ID ends in a tab.

The CGI says `Content-Type: text/html` for this tab-separated text (`genericMapping.cgi` 26). The CLI prints its counts of mapped and unmapped IDs to standard error (`map_panther.pl` 55 to 56); the CGI counts them and never prints them.

## What the Website Called

The settings are in `panther-site-java/config/extra.properties.example` 18 to 20, all under `mapping19`, so PANTHER 19:

| Setting | URL | What it returned | Used by |
| ------- | --- | ---------------- | ------- |
| `map_panther_cgi` | `/mapping19/genericMapping.cgi` | The mapping above | `RefProteomeMapping.parseMappingData` (`RefProteomeMapping.java` 31 to 37), from `GeneListAnalysisAction.java` 656, 893 and 1148 and `SelectFilesListsServlet.java` 331 |
| `map_panther_stats` | `/mapping19/stats` | The organisms that can be mapped, one per line: `<long name>\t<genes>\t<genes with a PANTHER ID>` | `OrganismHelper.getMappingOrgs` (`OrganismHelper.java` 59 to 66, 194 to 226), for every page's organism selector (`index.jsp` 1329 to 1350; `uploadFiles.jsp`, `uploadRefFile.jsp`, `distributionForm.jsp`) |
| `map_panther_cls` | `/mapping19/panther_classification/<long name>` | One organism's whole classification file, as it is | `RefProteomeMapping.retrieveMappingsForOrganism` (`RefProteomeMapping.java` 39 to 41), as the reference list for the overrepresentation and enrichment tests (`GeneListAnalysisAction.java` 819 to 838, `SelectFilesListsServlet.java` 510 to 531) |

- **`stats`:** lines split on runs of CR and LF; a line without exactly three tab fields, or whose counts aren't integers, is skipped with a log line. The list is sorted by long name, and the first is the default (`OrganismHelper.java` 200 to 245, `OrganismConstants.java` 187 to 200). On the data server, `stats` is a static file beside the classification files (The Data).
- **The long name:** `MapOrganism` splits it on `_`, takes the last part as the short name, and shows the rest joined by spaces with the short name in brackets (`MapOrganism.java` 29 to 50). So the code expects `Genus_species_CODE`, shown as "Genus species (CODE)". In the pinned release, every long name ends in a unique code (The Data).
- **Only the list type "ID's from Reference Proteome Genome"** (`ListConstants.java` 605 to 612, value `15`) called the CGI. "PANTHER Generic Mapping" (`13`) is a file the user maps themselves.
- **The help** says this list type is for genomes that aren't among PANTHER's own, that only UniProtKB IDs are supported, read from the first column, and that a second column can carry an expression value for the enrichment test (`tips_toolsUploadFile.jsp` 26 to 27 and 46). It counts "800+" genomes there and "900+" on line 30; the Phase 1 user guide says 1,533 (`docs/phase1/user-guide/gene-list-analysis.md` 27). The pinned `stats` lists 1,533 (The Data).

### What the Website Did to the Input

Nothing, unlike cSNP's `CsnpScoreForm.java`. `GeneListAnalysisAction` posted the text box or the uploaded file as it was, with the organism its form sent (`GeneListAnalysisAction.java` 633 to 656). `GeneListAnalysisForm.validate` checks only the result type (`GeneListAnalysisForm.java` 64 to 89), and the organism is checked only for being present (`GeneListAnalysisAction.java` 634 to 638), not against the list.

### What the Website Did With the Answer

The site parsed the CGI's output as a "PANTHER Generic Mapping File" (`UploadedFile.parseIdFamId`, `UploadedFile.java` 320 to 420). This is the site, not the service, but the site's port to the JSON API should know it:

- More than 100,000 lines: the whole analysis is rejected (338 to 342; `ListAnalysisConstants.java` 101).
- The first line is skipped as a header when its PANTHER ID doesn't start with `PTHR` (380 to 383). **So a list whose first ID is `NOHIT` loses that ID.**
- An ID that appears twice with the same PANTHER ID fails the whole analysis, "Arbitrary sequence ID maps to the same PANTHER ID multiple times." (401 to 406; error `13`). **So a list with a repeated ID that maps can't be analysed.** A repeated `NOHIT` ID fails the same way.
- A value that is neither `PTHR…` nor `NOHIT` fails it too (395 to 398), as does an empty ID (385 to 388).
- The enrichment test reads the third column, the first column the user gave after the ID, as the value (`GeneListAnalysisAction.java` 936 to 937, `parseIdFamIdValue(0, 1, 2)`).
- An empty answer is reported as no mapping for the input and organism (`GeneListAnalysisAction.java` 657 to 660).

## The Data

- **Where:** on `master`, `<panther_classification_directory>/panther_classification/<long name>`. The CGI loads `config.yaml` from its working directory, and reads `panther_classification_directory` from it (`genericMapping.cgi` 20 and 44 to 46). `config.example.yaml` sets it to `panther_classification`, which would make the path `panther_classification/panther_classification/<long name>`; production's `config.yaml` isn't in `panther-workspace`. At `4fc6a09`, the CGI read `panther_classification/<long name>` relative to its working directory. `map_panther.pl` takes the file's path as `-i`. The site also fetched the files over HTTP (`map_panther_cls`, `/mapping19/panther_classification/<long name>`), with `stats` beside them, so the folder holding `panther_classification/` was served at `/mapping19/`. Which CGI version and settings production ran needs team verification. `master`'s README says the data can be obtained from `ftp://ftp.pantherdb.org/generic_mapping`.
- **Where it's published:** [`https://data.pantherdb.org/ftp/generic_mapping/`](https://data.pantherdb.org/ftp/generic_mapping/), the HTTPS side of that FTP folder. The files are public. The folder serves `panther_classification/<long name>`, `stats`, `genericMapping.cgi`, `map_panther.pl`, a README, the test lists `test_geneList` and `test_geneList_values`, a tarball of the classification files, and `archive/2024-06-20/`. Its `genericMapping.cgi` is byte for byte `4fc6a09`'s, and its `map_panther.pl` is the parity reference's (checked 2026-11-06).
- **Release:** PANTHER 19, from the `mapping19` URLs. The README says PANTHER v.19.0 and Reference Proteome 2024-02.
- **Needs team verification:** whether production ran exactly these files. The folder holds them, `stats` and that CGI side by side, the layout the website's `/mapping19/` URLs read. The goldens don't depend on it. How PANTHER builds the files isn't in `panther-workspace`: no code or doc in `panther_build` names `panther_classification/`.

### The Pinned Release

The port pins the dated copy in `archive/2024-06-20/` (#52, question 2). The folder's current tarball and `stats` are the same bytes.

| File | URL | Bytes | sha256 |
| ---- | --- | ----- | ------ |
| The tarball | `https://data.pantherdb.org/ftp/generic_mapping/archive/2024-06-20/panther_classifications.tar.gz` | 156,535,594 | `74821b948aaae9482a36dea76595fd0233b3bdfc981fbf39890e0d9f515637af` |
| `stats` | `https://data.pantherdb.org/ftp/generic_mapping/archive/2024-06-20/stats` | 59,577 | `c48ae2f57cd2ea1d31467dd0516e55b764ff5a327ff5187265ba95c87e4b612e` |

- **Counts:** 1,533 organisms in `stats`, and 1,533 classification files in the tarball, with the same names and counts. 22,961,201 lines, and 523,291,643 bytes unpacked. The largest file, `Araneus_ventricosus_ARAVE`, has 246,021 lines. The README's 1,531 is out of date.
- **Format,** from #52's survey of every file:
  - every line is `ID<TAB>value`: two fields, ASCII, ending in LF, with no header and no blank lines;
  - every ID is a UniProt accession of 6 or 10 characters;
  - the value is a subfamily (`PTHR10078:SF1`), a family (`PTHR10078`), or the text `NOHIT`, on 3,708,372 lines (16%);
  - no ID repeats within a file, or across files.

  The service reads only the first two fields of each line. The site parses whole files the same way (`GeneListAnalysisAction.java` 828 to 829), and rejects any second field that isn't `PTHR…` or `NOHIT`.
- **The tarball's folder is plural:** its members are `panther_classifications/<long name>`, after a folder member of that name. The published folder and the website's URLs use `panther_classification/`.
- **Ten long names contain `:`,** the serotype notation:
  - `Campylobacter_jejuni_subsp_jejuni_serotype_O:2_CAMJE`
  - `Escherichia_coli_O127:H6_ECO27`
  - `Escherichia_coli_O139:H28_ECO24`
  - `Escherichia_coli_O157:H7_ECO57`
  - `Escherichia_coli_O1:K1_ECOK1`
  - `Escherichia_coli_O45:K1_ECO45`
  - `Escherichia_coli_O6:H1_ECOL6`
  - `Escherichia_coli_O83:H1_ECO8N`
  - `Escherichia_coli_O9:H4_ECOHS`
  - `Vibrio_parahaemolyticus_serotype_O3:K6_VIBPA`

  Windows can't use `:` in a file name. So the port saves each classification file under its organism's code, as `refmap/19/panther_classification/ECO57` (#52, update to question 4). `stats` and the engine's organism list keep the long names as published.
- **The codes:** the last `_` part of each long name. All 1,533 are unique, and match `[A-Z0-9]{1,5}`. All but `Pisum_sativum_PEA` have five characters.
- **`stats` isn't sorted.** Its first line is `Cephalotus_follicularis_CEPFO`. Each line is `<long name>\t<genes>\t<genes with a PANTHER ID>`, ending in LF.
- **How the website listed the organisms:** sorted by long name (`OrganismHelper.java` 223, with Java's `String.compareTo`), shown as "name (code)" (`MapOrganism.java` 29 to 49), with the first selected by default (`OrganismConstants.java` 187 to 196). With the pinned `stats`, the first is Abrus precatorius (ABRPR).

## Quirks

Each has a parity call, as cSNP's spec has: **Match** (the port reproduces it), **Decide** (a keep-or-fix question for the engine developer; a fix needs an approved row in [divergences.md](divergences.md)) or **N/A** (doesn't reach the new service).

| ID | Quirk | Evidence | Parity |
| -- | ----- | -------- | ------ |
| `REFMAP-1` | The lookup is exact and case-sensitive, on the whole first field: no trimming, case folding, or stripping of an isoform (`-2`) or version (`.1`). `p04217`, or `P04217` with a trailing space, doesn't match `P04217` | `map_panther.pl` 42 to 44, `genericMapping.cgi` 63 to 65 | Match. Decided on #52: no folding. Every ID in the pinned release is upper case |
| `REFMAP-2` | An ID that repeats in a classification file maps to its last line's PANTHER ID | `map_panther.pl` 31 to 32, `genericMapping.cgi` 50 to 51 | Match. It doesn't arise in the pinned release, where no ID repeats, so made-up files test it |
| `REFMAP-3` | A classification line loses its `\n` but not a `\r`. If a file has CRLF endings and two fields, every PANTHER ID ends in `\r` | `map_panther.pl` 30, `genericMapping.cgi` 48 | Match. It doesn't arise in the pinned release, where every line ends in LF, so made-up files test it |
| `REFMAP-4` | One output line per input line, in order, a repeated ID on each | `map_panther.pl` 39 to 51, `genericMapping.cgi` 59 to 73 | Match |
| `REFMAP-5` | The fields after the ID are printed after the PANTHER ID | `map_panther.pl` 42 to 43, `genericMapping.cgi` 63 to 64 | N/A: the API takes IDs only, and a client re-attaches its own columns by position |
| `REFMAP-6` | An ID with no match is printed with `NOHIT` | `map_panther.pl` 50, `genericMapping.cgi` 72 | Match, as `null` in the API and `None` in the engine |
| `REFMAP-7` | The CGI decodes `%XX` in `fileContents` but not `+`, and doesn't decode `organism` at all. The site posts a URL-encoded form (`Utils.java` 545 to 586, commons-httpclient's `PostMethod.setRequestBody`), which writes a space as `+`, so a space in the site's input reached the CGI as `+`: a line of space-separated IDs was one ID, `NOHIT` | `genericMapping.cgi` 15 to 24. The encoding is commons-httpclient 3's form encoding, not run here | N/A: no compatibility endpoint. The API rejects an ID with whitespace, so no answer changes |
| `REFMAP-8` | `organism` goes unchecked into a two-argument `open`: `../` reads any file the web server can, and a value ending in `\|` runs a command. Whether the CGI was reachable from outside the site's server needs team verification: the site's settings use `localhost`, with a public host commented out (`extra.properties.example` 18 to 23) | `genericMapping.cgi` 22, 44 to 46 | Never replicated. The API takes a 1-to-5-character code and the engine maps it to its file |
| `REFMAP-9` | An unknown organism, or a missing or unreadable file, maps every ID to `NOHIT`, with no error: `open`'s failure isn't checked | `genericMapping.cgi` 46; `map_panther.pl` 28 | Not replicated: [divergence 9](divergences.md), approved 2026-11-05. An unknown organism is a `422`, and missing data fails the job |
| `REFMAP-10` | An empty input line gives a line with an empty ID and `NOHIT` (and, from the CGI, a Perl warning). The CGI drops trailing empty lines (`split`); the CLI doesn't | `genericMapping.cgi` 58 to 72, `map_panther.pl` 39 to 51 | Not replicated: [divergence 10](divergences.md), approved 2026-11-05, with the API's other ID rules. The API rejects an empty ID with a `422` |
| `REFMAP-11` | `map_panther.pl` calls an undefined `usage` on `-h` or a bad option, and never uses `-o` | `map_panther.pl` 18 to 20 | N/A |
| `REFMAP-12` | The counts on standard error: `$count1` counts every ID found in the file, a stored `NOHIT` included, so an ID printed with `NOHIT` can count as mapped. A count that is never incremented prints as nothing: when every ID was found, the second line is " IDs are not mapped." | `map_panther.pl` 36 to 37, 44 to 45, 49 and 55 to 56 | N/A: the service has no counts |

## Golden Inputs

The goldens proposed here exist now, run through `map_panther.pl` at `4fc6a09` in the `refmap-reference` image, and saved byte for byte in `engine/tests/golden/refmap/`. Each case, and why it's in the set, is in [inputs.md](inputs.md#refmap). The parity tests compare each output line's first two fields with `map_ids()`'s mapping for the same ID, reading `NOHIT` as `None`.
