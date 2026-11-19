# hmmscore Test Fixtures

Small HMM library files for the hmmscore readers, survey, pin and sample tests. `hmmscore_fixtures.py` builds test tarballs from them. Every file here is stored byte for byte (`-text` in `.gitattributes`).

## The Clean Library

One family, `PTHR99999`, laid out as the PANTHER 19 library is below its tarball's prefix. The models are real: HMMER 3.4's `hmmbuild` built them from the three-sequence alignments in `alignments/`, so `hmmpress` and `hmmscan` read them.

| File | What it is |
| ---- | ---------- |
| `books/PTHR99999/hmmer.hmm` | The family's model, named `PTHR99999.orig.30.pir`, from `alignments/PTHR99999.afa` |
| `books/PTHR99999/SF1/hmmer.hmm`, `SF2/hmmer.hmm` | Two subfamily models, named `PTHR99999.SF1.pir` and `PTHR99999.SF2.pir`, from `alignments/PTHR99999.SF1.afa` and `PTHR99999.SF2.afa` |
| `books/PTHR99999/SF3/hmmer.hmm` | The family's model, byte for byte, as in PANTHER 19's one-subfamily families |
| `globals/names.tab` | A line for the family and for each subfamily |
| `globals/binHmm` | The flat library: SF2's, the family's and SF1's models, in that order, which isn't sorted. Not SF3's: `hmmpress` refuses a repeated name |
| `globals/binHmm.h3f`, `.h3i`, `.h3m`, `.h3p` | `binHmm`, pressed by `hmmpress` |

## Broken Copies

In `broken/`, each with one defect:

| File | Defect |
| ---- | ------ |
| `names-no-tab.tab` | `names.tab` with a space where line 2's tab should be |
| `names-repeated.tab` | `names.tab` with a 5th line that repeats line 2's key, `PTHR99999.SF1.mod` |
| `names-no-mod.tab` | `names.tab` with line 2's key as `PTHR99999.SF1`, without `.mod` |
| `names-crlf.tab` | `names.tab` with every line ending in CRLF |
| `two-models.hmm` | The family's model, then SF1's |
| `truncated.hmm` | The family's model without its last line, `//` |
| `no-name.hmm` | The family's model without its `NAME` line |

## Tables and a Report, for Scoring

In `tables/`, what fake `hmmscan` and `hmmsearch` give `test_hmmscore_scoring.py`, so each rule of scoring is tested on exactly the rows it needs.

| File | What it is |
| ---- | ---------- |
| `apoe.domtblout` | `hmmscan --domtblout --cpu 0` of the HMM scoring example, `../../golden/hmmscore/example/apoe.fasta` written as the CGI writes it, against the data sample `hmmscore-sample-1`, by the engine image's HMMER 3.4 on `linux/amd64`, with its `#` lines |
| `empty.domtblout` | The same for `>sequence` and 20 `W`s, which no model of the sample reports: its `#` lines alone |
| `apoe.hmmsearch` | `hmmsearch --cpu 0` of the sample's `books/PTHR18976/SF2/hmmer.hmm` against the example, as the CGI runs it, by the same HMMER. Run in a folder holding both files, so the report names them without a path |
| The other `.domtblout` files | Hand-written: `apoe.domtblout`'s `#` lines around rows made up for one rule each, which the file's name gives. Their numbers needn't agree with each other, since scoring reads only the target's name, the full-sequence E-value and the score |

## Rebuilding

The models and the pressed files come from the engine image's HMMER, the pinned 3.4. From the repository's root:

```sh
docker compose run --rm --user "$(id -u):$(id -g)" -w /work/engine/tests/fixtures/hmmscore engine sh -c '
  hmmbuild --amino --informat afa -o /dev/null -n PTHR99999.orig.30.pir books/PTHR99999/hmmer.hmm alignments/PTHR99999.afa &&
  hmmbuild --amino --informat afa -o /dev/null -n PTHR99999.SF1.pir books/PTHR99999/SF1/hmmer.hmm alignments/PTHR99999.SF1.afa &&
  hmmbuild --amino --informat afa -o /dev/null -n PTHR99999.SF2.pir books/PTHR99999/SF2/hmmer.hmm alignments/PTHR99999.SF2.afa &&
  cp books/PTHR99999/hmmer.hmm books/PTHR99999/SF3/hmmer.hmm &&
  cat books/PTHR99999/SF2/hmmer.hmm books/PTHR99999/hmmer.hmm books/PTHR99999/SF1/hmmer.hmm > globals/binHmm &&
  rm -f globals/binHmm.h3f globals/binHmm.h3i globals/binHmm.h3m globals/binHmm.h3p &&
  cd globals && hmmpress binHmm > /dev/null'
```

Then remake the broken copies from the new files, as the table above says. Each model's `DATE` line changes with every build, so the tests never compare a model's bytes with a literal.
