# `hmmscore`: The Legacy Service

What the legacy HMM scoring does, as its code runs it, for the `hmmscore` port. `refmap` has [its own](refmap-legacy-behaviour.md); `hmmscore` had none, so this is it. Written for `add-hmmscore-job` on 2026-11-13, from reading the code, with the engine developer's measurements of 2026-11-11 for what `hmmscan` does with each character. What the library holds, how `pantherScore.pl` reads it, and `hmmscan`'s time and memory are in the [library survey](hmmscore-library-survey.md), and not repeated here. The deliberate differences are rows 11 and 12 in [divergences.md](divergences.md).

Paths are relative to `panther-workspace/legacy/`, with line numbers: `pantherScoring/` at `89ea0ae` (its two scripts unchanged since `d7b28ee`), and `panther-site-java/` at `c0031ce`. Where the code doesn't settle something, it says **needs team verification**.

## The Service

| Script | Role |
| ------ | ---- |
| `pantherScoring/scoreAlignXml.cgi` | What the website called. Writes the posted sequence to a FASTA file, runs `pantherScore.pl` for the best hit, aligns the first line of its output with `hmmsearch`, and prints XML |
| `pantherScoring/pantherScore.pl` | Runs `hmmscan` against the library's `binHmm`, and prints each sequence's best hit, all hits, or InterProScan's form (`-D`). The parity reference (parity [README](README.md)) |

`panther-site-java/scoring/scoreAlignXml.cgi` is an older copy: it reads `./PANTHER7.2` (17) and aligns with HMMER2's `Algs::Hmmer` (14, 117), so it's most likely not what the site's PANTHER 19 URL ran. `pantherScoring/`'s copy is the HMMER3 one. Which copy production ran needs team verification.

What the CGI does, for one request:

1. Reads the form from the query string or the posted body, splits it on `&` and `=`, and decodes it (`scoreAlignXml.cgi` 73 to 89; `HMMSCORE-10`).
2. Prepends `>sequence\n` unless the value starts with `>` (93 to 95), so the query is named `sequence`. The `die` for a missing sequence after it (96) never fires: the value is never empty by then.
3. Writes it to `<tmp_directory>/scoreOnFly.<pid>.fasta` (100 to 105) and runs `pantherScore.pl -l <binHmm library> -D B -i <fasta> -o <out> -H <HMMER bin>` (111). It passes no `-n`, so no names, and no `-T`, so `pantherScore.pl` uses `/tmp` (`HMMSCORE-7`). It dies if the command's exit status isn't 0 (113 to 115), after printing the `Content-type` header (66).
4. Prints `<scores>`, and for the first line of the output only (161), `<id>` (the HMM ID, the line's second field) and `<eval>` (its fourth) (122 to 127).
5. Runs `hmmsearch` of the model file the HMM ID leads to against the same FASTA file (133 to 141), and prints its output from after "Domain annotation for each sequence" to before "Internal pipeline statistics summary:", with `>` and `<` escaped, inside `<align>` (143 to 158).
6. Prints `</scores>` (164). With no output line, `<scores>` is empty.

What `pantherScore.pl` does with `-D B`:

- **Runs `hmmscan --domtblout /tmp/temp.domtblout <binHmm> <fasta>`** (`runHmmscan`, 372 to 403), with no `--cpu` (377). Its `-c` option is read (84) and never used. So `hmmscan` ran with its own default thread count; which one production's build had needs team verification. The exit status isn't checked (381; `HMMSCORE-8`).
- **Reads each domain line's HMM ID** from the model's name: the part before the first `.`, with `:` and the second part added when that starts with `SF` and a digit (387 to 389). The survey's [Legacy Readings](hmmscore-library-survey.md#the-legacy-readings) give what that does to the library's models.
- **Picks the best hit** in `getBestHit` (316 to 340): the highest full-sequence bit score, then the smallest E-value with that score, then every model with both (`HMMSCORE-1`). Only then does the cutoff apply, 1e-3 (`$distantHmmCutoff`, 51), and to the best hit alone (338; `HMMSCORE-5`). The survey's [What It Means for port-hmmscore](hmmscore-library-survey.md#what-it-means-for-port-hmmscore) has the rule in full.
- **Prints one line per best model** (221 to 233): sequence ID, HMM ID, name, E-value, score and range, tab-separated (`printRes`, 275). Without `-n`, the name is empty. The E-value and score are printed as `hmmscan` wrote them.

## What the Website Sent

The form (`panther-site-java/wwwroot/tools/sequenceSearchForm.jsp` 44 to 51) has a text box, `sequence`, and a choice, `opType`: `hmm` for HMM scoring, `graft` for tree grafting. Struts validates the form (`config/struts-config.xml` 379 to 389, `validate="true"`) with `SequenceSearchForm.validate` (`src/com/ab/scienceSite/servlet/SequenceSearchForm.java` 51 to 89):

| Rule | Lines | What it does |
| ---- | ----- | ------------ |
| Required | 55 to 59 | Null or empty is an error, `errors.sequence.not.available`. Checked before normalising, so a sequence of only spaces, or only a header, passes |
| At most one `>` | 62 to 67 | A second `>` anywhere is an error, `errors.too.many.sequences` |
| One header removed | 69 to 74 | `^>[^\n]*`, with no `MULTILINE`, so only at the very start. The value isn't trimmed first (`HMMSCORE-6`) |
| Whitespace removed | 76 to 79 | Java's `\s+` |
| At most 50,000 | 81 to 86 | The length after the two steps above, whatever its characters, `errors.sequence.too.long` |

Nothing else: no trim, no upper-casing, no check of the characters. A sequence of only a header normalises to nothing and passes.

`SequenceSearchAction` then posts it to `score_cgi` (`SequenceSearchAction.java` 68 to 87): `http://{scoring_host}:{scoring_port}/{score_cgi}`, with `score_cgi=/sequence19/scoreAlignXml.cgi`, PANTHER 19 (`config/extra.properties.example` 7 to 15). The body is `out.println("sequence=" + sequence)` (80): not URL-encoded, and with a line break at the end (`HMMSCORE-10`).

## What the Website Showed

`HMMScoreXMLParser` reads the XML into one `HMMHitBean` (`src/com/ab/scienceSite/panther/hmmscore/HMMScoreXMLParser.java` 74 to 110):

- `<id>` is the accession, and the family or subfamily name comes from the site's database, `PantherFamilyNameRetriever` (95 to 99), not from the CGI (`HMMSCORE-2`).
- `<eval>` is stored as the bean's "score" (100 to 104), with an image for its size (`HMMSCORE-3`).
- `<align>` is the alignment text, its `&gt;` and `&lt;` read back as `>` and `<` (105 to 106).

`hmmScoreResults.jsp` shows "PANTHER Hit:" with the name, linked, and the accession, then "HMM E-value score:" with the E-value, then the alignment in a `<pre>` (`wwwroot/tools/hmmScoreResults.jsp` 45 to 50). With no accession, it shows "There were no hits to PANTHER found for the given sequence." (52 to 54). Its text says no hit is reported when the E-value is *less* than 1e-3 (38; `HMMSCORE-4`).

## The Characters

What `hmmscan` does with each character in a query, measured by the engine developer on 2026-11-11 with a one-sequence test model built from APOE, in HMMER 3.1b2 (production's, most likely) and 3.4 (the port's):

| In the sequence | 3.1b2 | 3.4 |
| --------------- | ----- | --- |
| Letters, either case; `*` at the end | Read | Read |
| `.`, `_`, `~` or `*` inside the sequence | Read, as a position, splitting the hit | Read, one domain |
| `-` | Read, as a position | Refused |
| `>` inside the sequence | Refused | Read |
| Empty | Refused | Read, no hit |
| Digits, `+`, `#`, `!`, `?`, `@` | Refused | Refused |

- **"As a position"** means 3.1b2 split the hit there: APOE with three such characters inserted scored 667.1 bits in three domains, against 721.8 in one. 3.4 scored the same insertions 708.5 in one domain.
- **`B`, `J`, `O`, `U`, `X` and `Z`** scored alike in both (708.9 to 710.1 bits in 3.1b2, 709.1 to 710.3 in 3.4, in one domain), as did lower case and a final `*`. The 0.2-bit gap on every row comes from pressing the model again in 3.4 (the survey's [Press Check](hmmscore-library-survey.md#the-press-check)), not from the character.
- **A refused sequence:** 3.1b2 leaves an empty `--domtblout`, and `pantherScore.pl` exits 0, so the CGI answers no hit (`HMMSCORE-8`).

So the API accepts only letters and a single final `*`, which both versions read alike, and refuses everything else with a `422` ([divergence 12](divergences.md)). `port-hmmscore`'s goldens confirm upper-casing, and refusing `.`, `_`, `~` and an inner `*`, on PANTHER's own models.

## Quirks

Each has a parity call, as cSNP's spec and `refmap`'s doc have: **Match** (the port reproduces it), **Decide** (a keep-or-fix question for the engine developer; a fix needs an approved row in [divergences.md](divergences.md)) or **N/A** (doesn't reach the new service).

| ID | Quirk | Evidence | Parity |
| -- | ----- | -------- | ------ |
| `HMMSCORE-1` | Tied best hits are printed in hash order, and the CGI shows the first. Ties come from up to 5,279 one-subfamily families, where the subfamily's model is the family's up to rounding: 324 whose two models differ only in their header always tie, and 4,955 differing in the fifth decimal often tie as printed. 114 differ more, and 57 in length (the survey's [binHmm as Text](hmmscore-library-survey.md#binhmm-as-text)). With the data sample, PTHR35774's consensus gave `PTHR35774:SF1` five times in ten and `PTHR35774` five times | `pantherScore.pl` 225 to 233, 337; `scoreAlignXml.cgi` 161 | Decide. The port reports the subfamily before its family, then the lowest PANTHER ID (engine developer, 2026-11-11): a proposed row for `port-hmmscore` |
| `HMMSCORE-2` | The XML has no name and no bit score: the CGI runs `pantherScore.pl` without `-n` and reads only the HMM ID and E-value. The site looked the name up in its own database | `scoreAlignXml.cgi` 111, 124 to 127; `HMMScoreXMLParser.java` 97 | N/A: the API's `hit` adds `name`, from `names.tab`, and `score` |
| `HMMSCORE-3` | The site's "score" is the E-value: the bean's `score` holds `<eval>`, shown as "HMM E-value score" | `HMMScoreXMLParser.java` 100 to 104; `hmmScoreResults.jsp` 48 | N/A: the API names it `evalue`, beside the bit score as `score` |
| `HMMSCORE-4` | The results page says no hit is reported when the E-value is *less* than 1e-3; the code reports none when it's greater | `hmmScoreResults.jsp` 38; `pantherScore.pl` 338 | Match: the port follows the code |
| `HMMSCORE-5` | The cutoff applies to the best hit only. A best hit over 1e-3 gives no result, even when a lower-scoring hit passes: `next` in `getBestHit` leaves the subroutine and moves the caller's loop to the next sequence | `pantherScore.pl` 338 | Match |
| `HMMSCORE-6` | The website neither trimmed nor upper-cased, and removed a header only at the first character. So a header after a blank line or spaces stayed in, and whitespace removal joined it to the residues: the CGI got one header line and no sequence, and answered no hit | `SequenceSearchForm.java` 69 to 79 | Not replicated: [divergence 12](divergences.md). The API trims first, as cSNP's input does, and scores the residues |
| `HMMSCORE-7` | `hmmscan`'s table is written to a fixed `/tmp/temp.domtblout`, shared by concurrent requests, which can read each other's hits. The CGI passes no `-T` | `pantherScore.pl` 54, 376; `scoreAlignXml.cgi` 111 | Never replicated. The port runs each tool in the job's own folder |
| `HMMSCORE-8` | A sequence `hmmscan` refuses, or an empty one, gives no hit: the exit status is ignored, 3.1b2 leaves an empty table, and `pantherScore.pl` exits 0 (The Characters). Had no table been written, `open … or die` would have stopped `pantherScore.pl`, and the CGI died with an empty page | `pantherScore.pl` 381 to 382; `scoreAlignXml.cgi` 113 to 115 | Not replicated: [divergence 12](divergences.md). The API refuses such a sequence with a `422` before any job |
| `HMMSCORE-9` | The alignment is `hmmsearch` of the model file at the best hit's HMM ID. For 839 of `binHmm`'s models, every `..pir` model among them, that file holds a different model from the one that scored | `scoreAlignXml.cgi` 133 to 140 | Match. The survey's [binHmm as Text](hmmscore-library-survey.md#binhmm-as-text) has the counts |
| `HMMSCORE-10` | The posting changed the text before `hmmscan` saw it. The site sent `sequence=<text>` unencoded, so: `&` ended the value (79), and `=` cut it at the next `=` (82); `+` became a space (85); `%xx` was decoded (86); and `<!--…-->` was removed (87). The line break `println` adds reached the FASTA file | `scoreAlignXml.cgi` 79 to 87; `SequenceSearchAction.java` 80 | Not replicated: [divergence 12](divergences.md). The site moves to the JSON API, and the API refuses all those characters |

Not listed, because they change no answer: the CGI's `print TO` to a file handle it never opens (112, 155, 159), and its reuse of `FH` for the alignment inside the loop over the score file, which `last` (161) makes harmless.

## Golden Inputs

Proposed for `port-hmmscore`, which makes them with `pantherScore.pl -D B` and the CGI's `hmmsearch` step in a reference image:

| Input | Why |
| ----- | --- |
| The site's example, `engine/tests/golden/hmmscore/example/apoe.fasta`, 317 residues | The help page's example, with one best hit, `PTHR18976:SF2` on the full library (the survey's [Sample](hmmscore-library-survey.md#the-sample)) |
| `test.fasta`, 381 residues | The release's own test query, hitting 773 models in 56 families |
| PTHR35774's consensus | A tie between a one-subfamily family and its subfamily (`HMMSCORE-1`) |
| A sequence with no hit, such as a short repeat of one letter | An empty `<scores>`, so `hit: null` |
| The example in lower case, with a final `*`, and with `B`, `J`, `O`, `U`, `X` and `Z` substituted | The characters both versions read alike (The Characters) |
| A best hit over 1e-3 beside a lower-scoring one under it, if the library has one | `HMMSCORE-5` |
| A model whose alignment comes from another model, such as a `..pir` hit in PTHR34093 | `HMMSCORE-9` |
| A query of 10,000 residues | The residue limit ([divergence 11](divergences.md)): its time and memory check the time limit's default (`add-hmmscore-job`, design.md, decision 5) |

The goldens on the sample are for the sample, and on amd64; the survey's [What It Means for port-hmmscore](hmmscore-library-survey.md#what-it-means-for-port-hmmscore) says why.
