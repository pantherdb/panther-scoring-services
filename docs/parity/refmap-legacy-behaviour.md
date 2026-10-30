# `refmap`: The Legacy Service

What the legacy reference-proteome mapping does, as its code runs it, for the `refmap` port. cSNP has its behaviour spec in `panther-workspace`; `refmap` had none, so this is it. Written for `add-refmap-job` on 2026-10-30, from reading the code: nothing here was run, because the classification files aren't in `panther-workspace`.

Paths are relative to `panther-workspace/legacy/`, with line numbers. Where the code doesn't settle something, it says **needs team verification**.

## The Service

`RefProteomeMapper/` has two scripts, at commit `4fc6a09` of 2019-07-26, its latest (public, `pantherdb/RefProteomeMapper`):

| Script | Role |
| ------ | ---- |
| `genericMapping.cgi` | What the website called. Reads `organism` and `fileContents` from a GET or POST form, loads `panther_classification/<organism>`, and prints one line per input line |
| `map_panther.pl` | The CLI, with the same lookup: `-i` the classification file, `-g` the gene list. The parity reference (tech-stack.md, Runtime Tools and Milestones) |

The lookup, in both:

1. Read the classification file into a hash: each line's first tab field maps to its second (`map_panther.pl` 27 to 33, `genericMapping.cgi` 40 to 49).
2. For each input line, remove every `\r`, split on tab, and look up the first field (`map_panther.pl` 39 to 44, `genericMapping.cgi` 54 to 61).
3. Print `<id>\t<PANTHER ID>\t<rest of the line>`, or `<id>\tNOHIT\t<rest>` with no match (`map_panther.pl` 47 and 50, `genericMapping.cgi` 65 and 68). The rest is the line's other fields joined by tabs, so a line with only an ID ends in a tab.

The CGI says `Content-Type: text/html` for this tab-separated text (`genericMapping.cgi` 23). The CLI prints its counts of mapped and unmapped IDs to standard error (`map_panther.pl` 55 to 56); the CGI counts them and never prints them.

## What the Website Called

The settings are in `panther-site-java/config/extra.properties.example` 18 to 20, all under `mapping19`, so PANTHER 19:

| Setting | URL | What it returned | Used by |
| ------- | --- | ---------------- | ------- |
| `map_panther_cgi` | `/mapping19/genericMapping.cgi` | The mapping above | `RefProteomeMapping.parseMappingData` (`RefProteomeMapping.java` 31 to 37), from `GeneListAnalysisAction.java` 656, 893 and 1148 and `SelectFilesListsServlet.java` 331 |
| `map_panther_stats` | `/mapping19/stats` | The organisms that can be mapped, one per line: `<long name>\t<genes>\t<genes with a PANTHER ID>` | `OrganismHelper.getMappingOrgs` (`OrganismHelper.java` 59 to 66, 194 to 226), for every page's organism selector (`index.jsp` 1329 to 1350; `uploadFiles.jsp`, `uploadRefFile.jsp`, `distributionForm.jsp`) |
| `map_panther_cls` | `/mapping19/panther_classification/<long name>` | One organism's whole classification file, as it is | `RefProteomeMapping.retrieveMappingsForOrganism` (`RefProteomeMapping.java` 39 to 41), as the reference list for the overrepresentation and enrichment tests (`GeneListAnalysisAction.java` 819 to 838, `SelectFilesListsServlet.java` 510 to 531) |

- **`stats`:** lines split on runs of CR and LF; a line without exactly three tab fields, or whose counts aren't integers, is skipped with a log line. The list is sorted by long name, and the first is the default (`OrganismHelper.java` 200 to 245, `OrganismConstants.java` 187 to 200). Whether `stats` is a static file or a script isn't in `panther-workspace`: needs team verification.
- **The long name:** `MapOrganism` splits it on `_`, takes the last part as the short name, and shows the rest joined by spaces with the short name in brackets (`MapOrganism.java` 29 to 50). So the code expects `Genus_species_CODE`, shown as "Genus species (CODE)". Whether every long name ends in a unique UniProt mnemonic: needs team verification.
- **Only the list type "ID's from Reference Proteome Genome"** (`ListConstants.java` 605 to 612, value `15`) called the CGI. "PANTHER Generic Mapping" (`13`) is a file the user maps themselves.
- **The help** says this list type is for genomes that aren't among PANTHER's own, that only UniProtKB IDs are supported, read from the first column, and that a second column can carry an expression value for the enrichment test (`tips_toolsUploadFile.jsp` 26 to 27 and 46). It counts "800+" genomes there and "900+" on line 30; the Phase 1 user guide says 1,533 (`docs/phase1/user-guide/gene-list-analysis.md` 27). Needs team verification against `stats`.

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

- **Where:** `panther_classification/<long name>`, relative to the CGI's working directory (`genericMapping.cgi` 41), served over HTTP too (`map_panther_cls`), and `stats` beside it.
- **Format:** tab-separated; the service reads only the first two fields of each line. The first is the ID, the second the PANTHER ID. The site parses whole files the same way (`GeneListAnalysisAction.java` 828 to 829), and rejects any second field that isn't `PTHR…` or `NOHIT`, so the files' PANTHER IDs are families or subfamilies, such as the help's `PTHR10078:SF1` (`tips_toolsUploadFile.jsp` 32).
- **Release:** PANTHER 19, from the `mapping19` URLs.
- **Needs team verification:** where the files come from (no code or doc in `panther_build` names `panther_classification/`; its `refProteomePANTHERmapping_*` files look like the library build's own mapping, not these), how many there are, their size, any columns after the second, their line endings, whether an ID repeats in one file, whether they have a header line, and whether the PANTHER 19 copy still exists.

## Quirks

Each has a parity call, as cSNP's spec has: **Match** (the port reproduces it), **Decide** (a keep-or-fix question for the engine developer; a fix needs an approved row in [divergences.md](divergences.md)) or **N/A** (doesn't reach the new service).

| ID | Quirk | Evidence | Parity |
| -- | ----- | -------- | ------ |
| `REFMAP-1` | The lookup is exact and case-sensitive, on the whole first field: no trimming, case folding, or stripping of an isoform (`-2`) or version (`.1`). `p04217`, or `P04217` with a trailing space, doesn't match `P04217` | `map_panther.pl` 42 to 44, `genericMapping.cgi` 59 to 61 | Match. Decide whether lower case should map |
| `REFMAP-2` | An ID that repeats in a classification file maps to its last line's PANTHER ID | `map_panther.pl` 31 to 32, `genericMapping.cgi` 46 to 47 | Match. Whether any file has one: needs team verification |
| `REFMAP-3` | A classification line loses its `\n` but not a `\r`. If a file has CRLF endings and two fields, every PANTHER ID ends in `\r` | `map_panther.pl` 30, `genericMapping.cgi` 44 | Match, if any file has CRLF. Needs team verification |
| `REFMAP-4` | One output line per input line, in order, a repeated ID on each | `map_panther.pl` 39 to 51, `genericMapping.cgi` 55 to 69 | Match |
| `REFMAP-5` | The fields after the ID are printed after the PANTHER ID | `map_panther.pl` 42 to 43, `genericMapping.cgi` 59 to 60 | N/A: the API takes IDs only, and a client re-attaches its own columns by position |
| `REFMAP-6` | An ID with no match is printed with `NOHIT` | `map_panther.pl` 50, `genericMapping.cgi` 68 | Match, as `null` in the API and `None` in the engine |
| `REFMAP-7` | The CGI decodes `%XX` in `fileContents` but not `+`, and doesn't decode `organism` at all. The site posts a URL-encoded form (`Utils.java` 545 to 586, commons-httpclient's `PostMethod.setRequestBody`), which writes a space as `+`, so a space in the site's input reached the CGI as `+`: a line of space-separated IDs was one ID, `NOHIT` | `genericMapping.cgi` 14 to 21. The encoding is commons-httpclient 3's form encoding, not run here | N/A: no compatibility endpoint. The API rejects an ID with whitespace, so no answer changes |
| `REFMAP-8` | `organism` goes unchecked into a two-argument `open`: `../` reads any file the web server can, and a value ending in `\|` runs a command. Whether the CGI was reachable from outside the site's server needs team verification: the site's settings use `localhost`, with a public host commented out (`extra.properties.example` 18 to 23) | `genericMapping.cgi` 19, 41 to 42 | Never replicated. The API takes a 1-to-5-character code and the engine maps it to its file |
| `REFMAP-9` | An unknown organism, or a missing or unreadable file, maps every ID to `NOHIT`, with no error: `open`'s failure isn't checked | `genericMapping.cgi` 42; `map_panther.pl` 28 | Not replicated, with no row: an unknown organism is a `422`, and missing data fails the job. Neither changes a correctly deployed service's answer |
| `REFMAP-10` | An empty input line gives a line with an empty ID and `NOHIT` (and a Perl warning). The CGI drops trailing empty lines (`split`); the CLI doesn't | `genericMapping.cgi` 54 to 68, `map_panther.pl` 39 to 51 | N/A: the API rejects an empty ID |
| `REFMAP-11` | `map_panther.pl` calls an undefined `usage` on `-h` or a bad option, and never uses `-o` | `map_panther.pl` 18 to 20 | N/A |

## Proposed Golden Inputs

For the engine developer's port; none exist yet. Run through `map_panther.pl` at `4fc6a09`, saved byte for byte in `engine/tests/golden/refmap/`, and described in [inputs.md](inputs.md) when they exist.

| Input | Against | Shows |
| ----- | ------- | ----- |
| A list of IDs that map, and IDs that don't | A real PANTHER 19 file for one or two organisms | The lookup, and `NOHIT` (`REFMAP-6`) |
| The same ID twice, mapped and unmapped | The same | One line each, in order (`REFMAP-4`) |
| A mapped ID in lower case, with `-2`, and with `.1` | The same | No folding or stripping (`REFMAP-1`) |
| A first ID that doesn't map | The same | The service answers it; only the site dropped it as a header |
| IDs with punctuation (`+`, `,`, `\|`, `;`) | The same | Looked up as they are |
| One ID twice in the file, with different PANTHER IDs | A small made-up file | The last wins (`REFMAP-2`) |
| A file with CRLF endings | A small made-up file | `REFMAP-3`, if the real files can have it |
| An ID line with more fields | A small made-up file | The CLI echoes them (`REFMAP-5`); the parity test compares only the first two fields |

The parity test compares each output line's first two fields with `map_ids()`'s mapping for the same ID, reading `NOHIT` as `None`. The reference image needs only Perl and the public repository at the pinned commit.
