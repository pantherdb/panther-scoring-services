# Proposal

**Area:** cross-cutting. The work is in `engine/`, but the change also adds a test-only stage to the root `Dockerfile`, a divergence row, and edits to `docs/design/tech-stack.md`, which all three developers own.

## Why

cSNP is the first service to go live, and the engine's scoring is the one piece still missing. The API validates cSNP requests and answers `501` until the engine can score (#19). The frontend's form and results page are built (#20). This change ports the legacy pipeline's three steps behind the interface agreed on #19, with the parity tests Engine condition 3 asks for. The engine developer asked for as much as one pull request can hold, to get cSNP live sooner (2026-10-29).

## What Changes

- **Parity tests first** (Engine condition 3):
  - **The goldens in legacy behaviour spec §7:** the 35-row sample (§7.3) and the edge cases (§7.5), in `engine/tests/golden/csnp/`. Their inputs, `HUMAN`, `sample.input` and `sample.fasta`, come from the public PSEP 1.01 release, which has the same `HUMAN` as `cebb5ab`.
  - **A Perl reference image,** a test-only `csnp-reference` stage of the root `Dockerfile`. It holds Perl, and `run_blastp.pl`, `parse_blastp.pl` and `PANTHER_PSEP1.01.pl` at `cebb5ab`, each checked against a pinned sha256.
    - `pantherdb/cSNP_analysis` is private, so the scripts come from a developer's local checkout, through `git archive cebb5ab` and a named build context, not a clone (engine developer, 2026-10-29).
    - The runtime `api` image never contains the scripts or Debian's `perl` package. It keeps the minimal `perl-base` that Debian, its base image, can't do without (engine developer, 2026-10-30).
  - **`panther-engine csnp parity`:**
    - generates step-2 and step-3 cases, seeded, with the standard library only;
    - runs them through the Perl in that image, one process per family;
    - checks the Python against the results.

    Its goldens for all 15 sample families are committed, and CI checks them without Perl. The same command, given the full library on staging, is M1's acceptance run.
- **The port, behind `panther_engine.csnp.score(CsnpInput) -> CsnpResult`,** one protein per call, as agreed on #19:
  - **Step 1:** `blastp` with the legacy options, the query named `P0001`, through stdin and stdout. There's no temporary file to share (`CGI-6`) and no shell (`CGI-5`).
  - **Step 2:** the best hit by percent identity (`MAP-1`), the species filter (`MAP-2`), the family and gene (`MAP-3`), and the position mapping, keeping `MAP-4`.
  - **Step 3:** the gene's sequence and column, the trace-back from the last header match (`SCORE-2`), node ages, message and pDel. It keeps the code's 180 / 380 Mya and `age < bound` (`SCORE-5`, `SCORE-6`).
- **The species codes** the engine accepts are exported for the API's membership check: the 85 codes in the PANTHER9 BLAST database.
- **One cSNP input error.**
  - When `blastp` can't read the query (exit status 1), `score()` raises `InputError`, which the API will report as a `422`.
  - So it does, before searching, for a sequence that starts with `!`, `#` or `;`: BLAST+ reads that line as a comment, finds no sequence and exits with status 3, an engine error (engine developer, 2026-10-30).
  - The legacy reported "Not scored: No PANTHER family for input sequence" for every substitution. That difference is divergence row 8, which the engine developer approves in this change (decided 2026-10-29).
  - Every other legacy condition stays a per-substitution result, as `add-job-input-errors` records.
- **`InputError` itself,** `add-job-input-errors` task group 1, lands here, as that change planned.
- **`csnp-sample-2`:**
  - The data sample gains the PANTHER9 BLAST database (`blast.phr`, `.pin` and `.psq`), so CI can run `score()` end to end. The 326 MB FASTA stays out: `blastp` doesn't read it.
  - `sample build` takes the BLAST archive too, checked against spec §7.1.
  - It ships as a new pre-release, with a new manifest.
- **A step-1 golden:** the BLAST+ 2.17.0 output for the three sample proteins. `tech-stack.md` asks for one once BLAST+ is pinned.
- **`panther-engine csnp score`,** for checks by hand and staging smoke tests.
- **Docs:**
  - **New `docs/parity/golden-setup.md` and `docs/parity/inputs.md`,** which `docs/parity/README.md` already plans.
  - **`divergences.md`:** row 8. A note that `SCORE-7` and `SCORE-8` don't arise in the service, which scores one protein per call, as the CGI did.
  - **`tech-stack.md`:**
    - Engine condition 3: the scripts come from a local checkout, for now;
    - the step-1 golden;
    - a new open question on making the original repositories public.
  - **`docs/testing/engine.md`:** the parity check, the reference image and the new sample.

Not in this change:

- **Wiring the engine into the API** (API developer): removing the `501`, the adapter, `add-job-input-errors` group 2, the species membership check, and the `api` service's data mount. The frontend's `501` branch goes with it. All of it can be drafted now, against the agreed signature.
- **Staging, the M1 acceptance run on the full library, and deploying.**
- **Fixing any legacy defect.** Rows 2, 3, 4, 5 and 7 stay proposals.
- **Property-based testing** with a new dependency such as Hypothesis. The cases are generated with the standard library.

## Capabilities

### New Capabilities

- `psep-engine`: cSNP scoring, as CONTRIBUTING's Spec Layout names it. It covers the three pipeline steps behind `score()`, the result, the species codes, the input error, the `score` command, and parity with the Perl through the reference image. Its folder holds only a `.gitkeep` today.

### Modified Capabilities

- `csnp-data`: the sample's contents, and building it, gain the PANTHER9 BLAST database.

## Impact

- **Code:**
  - new `csnp/` modules for the three steps, `score()` and its types, the species codes, and the parity cases and checks. `csnp/cli.py` gains `score` and `parity`;
  - `core/process.py`: `run_tool()` can pass text to the program's stdin;
  - new `core/errors.py` (`InputError`, from `add-job-input-errors`);
  - `csnp/sample.py` and `sample.json`: the BLAST database.
- **Tests:**
  - unit tests on hand-written fixtures;
  - golden tests on the sample, marked `data`;
  - end-to-end tests marked `tools` and `data`, which need `blastp` and the sample, and run in CI's `engine-image` job.
- **Root `Dockerfile`:** a new `csnp-reference` stage after `engine`. The `engine` and `api` stages don't change, and CI never builds the new stage.
- **GitHub:** a new pre-release, `csnp-sample-2`. Creating it needs write access.
- **API contract:** not affected. The result types are the ones agreed on #19, field for field, and nothing in `api/` changes here.
- **Dependencies:** none new, in Python or in CI. The reference image adds Debian's `perl` package, test-only.
- **Parity with the reference:** this change is the proof.
  - The Python matches the §7 goldens and the reference image's goldens for every sample family, defects included: `SCORE-2`, `MAP-4`, `SCORE-5` and `SCORE-6`.
  - Row 8 is the one divergence, approved here.
  - `SCORE-7` and `SCORE-8` don't arise. One protein per call means one family, and that reproduces every §7.3 row: §7.4 shows that the PTHR15126 rows don't depend on order.
- **Size:** far over the 400-line norm, by the engine developer's choice (Why). The pull request description walks through it in task order.

## Open Questions

Each needs team verification:

- **Ties in the best hit (`MAP-1`).** Equal percent identity falls back to `sort`'s whole-line comparison, which depends on the locale. Production's locale is unknown. The port compares bytes, as the C locale does, which a CGI under Apache usually has.
- **Licence.**
  - The PSEP 1.01 release is GPLv2, copyright 2016 Paul Thomas, and this public repository has no licence. A port is arguably a derivative work.
  - Does the repository need a licence, and which one?
- **Making the original repositories public.**
  - `pantherdb/cSNP_analysis` and `pantherdb/pantherScoring` are private; `RefProteomeMapper` is public. So the reference images for `csnp` and `hmmscore` build from a local checkout.
  - Making them public would let the images clone at build time, as condition 3 first said, and let CI build them.
  - To consider eventually (engine developer, 2026-10-29).

For review, proposed but not yet confirmed by the engine developer:

- **`family` in the result** is what the CGI showed as `hmm_acc`:
  - the BLAST hit's family cut to `PTHR` and its digits, so `PTHR23125_2` gives `PTHR23125`;
  - the raw field where that doesn't match, such as `AN12345` for the 81,323 BLAST entries with an AN in the family field;
  - `null` with no hit.
- **`blastp` failing any other way** (exit status 2 or more, or a timeout) fails the job with the generic `500`. The legacy ignored the failure and reported "No PANTHER family" (`RUN-3`). A correct deployment never hits it, so it needs no divergence row.
- **An unknown species code** raises `ValueError`, a `500`. The API rejects one before the job starts (`add-job-input-errors`), so it can only arrive through a bug.
- **The fixtures from the 2016 release** are committed under `engine/tests/golden/csnp/`, with the release's copyright statement.
