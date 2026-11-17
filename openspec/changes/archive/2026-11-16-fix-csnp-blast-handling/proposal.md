# Proposal

**Area:** engine. Everything changed is in `engine/`, apart from one `ENV` line in the root `Dockerfile`'s `tools` stage. The engine owns that stage, but the `api` image inherits it, so blastp runs started by the API stop reporting usage too. No API or frontend code changes.

## Why

The cSNP API is about to go public (`docs/design/hosting.md`, #34). The whole-repository review at `64174c9` (`docs/code-review/2026-10-30-whole-repo-review-64174c9.md`) found six engine faults that a public deployment would hit:

- **ENG-1:** every `blastp` run, `-version` included, sends a usage report to NCBI. Where outbound traffic is dropped, each job takes about 10 s longer. Where it isn't, the server reports every user's job to a third party.
- **CSNP-1:** step 2 recomputes each line's identity in a different order from BLAST+ 2.17.0. At an exact three-decimal tie the two disagree, and one such line fails the whole job with a 500.
- **CSNP-3:** a data folder whose library or species file is missing, such as a volume that didn't mount or a copy of the 19.2 GB library that stopped halfway, gives plausible answers: a family, with every substitution "Not scored: No PANTHER family for input sequence". Nothing reports an error. There's also no checksum manifest for the full data, though [tech-stack.md](../../../docs/design/tech-stack.md) (Environments) wants every deploy checked against one.
- **CSNP-4:** the BLAST+ time limit is a fixed 300 s, and titin (Q8WZ42, 34,350 residues) takes 272 s on one Apple Silicon core. On a slower server core, every titin job would fail with a 500.
- **CSNP-5:** `blastp` exits with status 1 both for a query it can't read and for an argument it rejects, and the engine blames every 1 on the user's sequence. After a BLAST+ upgrade or an edit to the options, every job would be a 422 telling users to fix their sequence. BLAST+'s message is dropped, so no log would say why.
- **CSNP-6:** BLAST+ reads `-db` as a list of names separated by spaces. With the data at a path that contains a space, every search fails with a 500.

## What Changes

- **No usage reports (ENG-1):**
  - the engine's tool runner sets `BLAST_USAGE_REPORT=false` for every tool it starts, whatever the caller's environment says;
  - the image's `tools` stage sets it too, so a `blastp` run by hand in any image doesn't report either.
- **BLAST+ 2.17.0's identity formula (CSNP-1):**
  - step 2 computes `(length − mismatch − gaps) / length × 100`, in BLAST+'s order, both to check BLAST+'s three-decimal value and for the two-decimal value it ranks by;
  - the parity case generator builds identities the same way;
  - new tests use real BLAST+ 2.17.0 tie lines.
- **Missing data is an error (CSNP-3):**
  - before searching, `score()` checks that the cSNP data folder has the BLAST database files, a `PAML_RST/` folder that isn't empty, and the species file;
  - if any is missing, it raises an engine error that isn't an input error and names what's missing, so the job fails with a 500 and the log says why.
- **A checksum manifest of the full data (CSNP-3):**
  - `panther-engine csnp data manifest` builds it from the pinned archives, the species file and the release README. It checks each against its pinned sha256, and gives the same bytes every time;
  - the manifest is committed beside `sample.json`;
  - `panther-engine csnp data verify` checks a data folder against it, so a deploy can prove the full data is complete and unchanged before it takes traffic.
- **A BLAST+ time limit that scales with the query (CSNP-4):**
  - the limit is a fixed base plus a time per residue, so titin and the API's longest accepted sequence (50,000 residues) get several times their measured search time, and an ordinary protein still gets about a minute;
  - `PANTHER_CSNP_BLAST_TIME_SCALE` multiplies it on a slower machine.
- **Exit status 1 told apart (CSNP-5):**
  - status 1 is the input error only when BLAST+'s standard error has a `BLAST query error:` line, as 2.17.0 writes for `1234567890` or `MK(VL`;
  - any other status 1, such as an argument BLAST+ rejects, fails with an engine error whose message includes the end of BLAST+'s standard error, so the API's log shows it;
  - divergence row 8 doesn't change.
- **Any data folder path (CSNP-6):** `blastp` runs in the database's folder, with the database named `blast`, so the folder's path never reaches BLAST+'s argument parsing.
- **Docs:** `docs/testing/engine.md` (verifying the full library, and the new variable) and `engine/README.md`.

Not in this change:

- **CSNP-2,** the species filter. Parity holds there, so it's the science owner's call.
- **CSNP-7 to CSNP-11:** the untested paths and the nits, left for a follow-up. CSNP-7's real BLAST+ tie line is the exception: this change's tie tests cover it (design.md, decision 3).
- **The rest of the tool runner** (ENG-2, ENG-3 and ENG-16): an explicit environment, `stdin`, a process-group kill and an output cap. The suggested follow-up is `harden-engine-tooling`.
- **The images and the API** (REPO-4 to REPO-8, API-1 and API-2), including an API readiness check that uses the new data check. Those are the `harden-images` and `bound-api-load` follow-ups, and the API developer's call.
- **The deploy runbook.** It belongs to #34, which will run `csnp data verify` and measure titin on the server.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `engine-core`: a new requirement that external tools run with BLAST+'s usage reporting off, both through the engine and in the image.
- `psep-engine`:
  - new requirements for reading BLAST+ 2.17.0's identities, the BLAST+ time limit, missing cSNP data and data folder paths;
  - "A query BLAST+ can't read" and "Other BLAST+ failures" are modified, so that only a query error BLAST+ reports is the input's fault, and the error for any other failure carries BLAST+'s message.
- `csnp-data`: new requirements for the full data's checksum manifest, and for verifying a data folder against it.

## Impact

- **Code:**
  - `engine/src/panther_engine/core/process.py` (the environment) and `core/data.py` (a missing-data error);
  - `csnp/hits.py` (the formula), `csnp/parity.py` (the generator) and `csnp/scoring.py` (the data check);
  - `csnp/blast.py`: the time limit, telling status 1 apart, and the working folder;
  - `csnp/cli.py` and a new `csnp/full.py` for the manifest commands;
  - the root `Dockerfile` (one `ENV` line).
- **Data:** a new committed manifest, `engine/src/panther_engine/csnp/full.json`, of about 25,800 files and 2.6 MB. It's generated, so `.gitattributes` marks it `linguist-generated`. No new release, and the sample doesn't change.
- **Tests:**
  - unit tests for the environment, the formula, the time limit and the data check;
  - a `tools("blastp")` test that runs real BLAST+ 2.17.0 tie alignments through step 2;
  - unit tests with a fake `blastp` for each kind of status 1;
  - `tools("blastp")` tests that the real BLAST+ rejecting an argument is an engine error, and that the form's example scores as `apoe.out` from a data folder whose path has a space or a `"`;
  - manifest tests on a small built archive;
  - the existing goldens and `parity check`, unchanged;
  - by hand: a `verify` of the full library, a titin search and a 50,000-residue search in the engine image, and the NCBI-unreachable check from the review.
- **API contract:** not affected. The OpenAPI schema doesn't change. One response does: a job whose `blastp` exits with status 1 without a query error now fails with a 500, where it was a 422. No correct request reaches that path.
- **Dependencies:** none.
- **Parity with the reference:** no golden changes, and no divergence row is needed. Under the new formula, all 109 BLAST lines in the goldens keep their written identity and their two-decimal value: the four step-1 goldens, `release/HUMAN` and the generated step-2 inputs. At two decimals the two formulas differ only at alignment lengths that are multiples of 160, such as 23 identities over 160 columns (14.37 against 14.38). Which the legacy BLAST+ printed is an open question below. The other fixes change no correct request's output. They turn a timeout, a report to NCBI, a misleading answer, a blame on the user's input or a failed search into a result or a clear error. Divergence row 8 still describes what's an input error: a query BLAST+'s FASTA reader rejects.
- **Size:** estimated at about 500 changed lines. As built, it's about 1,180, over CONTRIBUTING.md's 400-line norm: 441 of source, the `Dockerfile` and `.gitattributes`; 657 of tests; 35 of fixtures; and 50 of docs. On top of that come these artifacts (659) and the generated `full.json` (25,842). Each of the six fixes is small and lands with its tests. Splitting them would mean six pull requests over the same three files, `blast.py`, `scoring.py` and `test_csnp_blast.py`.

## Open Questions

Each needs team verification:

- **The legacy BLAST+'s identity formula.** Its version is unknown (`BLAST-1`). The design assumes later BLAST+ releases changed how many decimals `pident` has, not how it's computed. If the legacy BLAST+ computed `100 × n / L`, the new two-decimal value differs from what it printed at the lengths above. That changes a best hit only when two candidate lines for the species round across each other, which no golden has.
- **The time limit's defaults** are set from this machine's measurements (tasks 4.1). The production server's cores may be slower, so #34 measures titin there and sets `PANTHER_CSNP_BLAST_TIME_SCALE` if it needs to.
- **Is a job of up to about 18 minutes acceptable** for a 50,000-residue query on a public API? That's the scaled limit for the API's longest accepted sequence. Whether to accept shorter sequences instead is the API developer's call (`scoring-input`, and the review's API-2).

For review: the full manifest is committed in the package, so `verify` works offline on the server. The alternative is a release asset, as the sample is (design.md, decision 6).
