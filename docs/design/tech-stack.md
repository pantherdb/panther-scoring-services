# Tech Stack Proposal

**Status:** Proposed, 2026-10-27; revised 2026-10-28 for four services. Not final until the [open questions](#open-questions) are answered and the [reviewers](#review) sign off. The frontend part was split out and accepted on 2026-10-28: see [frontend-stack.md](frontend-stack.md). The API's tooling (uv, Python version, lint, types, tests, error format) was split out and accepted on 2026-10-28: see [api-stack.md](api-stack.md); the API's architecture stays here. Revised 2026-10-29: [pinned tool versions](#pinning-tool-versions) in the container image (BLAST+ 2.17.0 tested against the PANTHER9 database), worker processes (API recommendation 1), the site moving to the JSON API (API recommendation 2), the parity oracle image (Engine condition 3), cSNP data regeneration as a separate project, and the environments and cSNP data sample (Shared Concerns). Revised again 2026-10-29 (`add-csnp-survey-and-sample`): the service priority, with `csnp` first; the origin of `PAML_RST.tar.gz`, production's library build; and following the legacy code where it and its docs disagree, which keeps the code's cSNP thresholds and pDel bounds for M1 (Engine condition 7). Also the cSNP data sample's storage, a release asset unpacked under `PANTHER_DATA_DIR` (Shared Concerns, Data). Revised 2026-10-29 (`port-csnp`): the cSNP reference image takes the legacy scripts from a developer's checkout, because the repository is private (Engine condition 3); two new open questions, on making the original repositories public and on a licence.

## Summary

| Part | Folder | Proposed | Verdict |
| ---- | ------ | -------- | ------- |
| Frontend | `frontend/` | React 19 + Vite + TypeScript, Mantine + Tailwind, RTK Query | Accepted, in [frontend-stack.md](frontend-stack.md) |
| API | `api/` | FastAPI (Python), one app for all four services | Agree, built around jobs. Tooling accepted in [api-stack.md](api-stack.md) |
| Engine | `engine/` | One Python package: shared `core/` plus one submodule per service | Agree, as a library with parity tests |
| Runtime tools | — | BLAST+, HMMER3, EPA-ng | Per service, pinned to exact versions: see [Runtime Tools and Milestones](#runtime-tools-and-milestones) |

## Scope: Four Services

Revised on 2026-10-28. The repo was first scoped to cSNP scoring only. It replaces four legacy PANTHER services. The priority order was revised on 2026-10-29, putting `csnp` first:

| Service | Replaces (in `panther-workspace/legacy/`) | Approach | Priority |
| ------- | ----------------------------------------- | -------- | -------- |
| `csnp` | `cSNP_analysis/`: `snpScore.cgi` and the scripts it runs | Port the Perl | 1 |
| `refmap` | `RefProteomeMapper/` | Port the Perl | 2 |
| `hmmscore` | `pantherScoring/` | Port the Perl | 3 |
| `treegrafter` | `TreeGrafter/` (Perl 1.01) | **Adopt** EBI's Python [`treegrafter`](https://github.com/ebi-pf-team/treegrafter) | 4 |

The team stays split by layer: one owner each for `frontend/`, `api/` and `engine/`, each covering all four services.

## What We're Replacing

`panther-site-java` calls each service over HTTP. The settings are in its `config/extra.properties.example`:

| Service | Website setting | What it calls | Java caller |
| ------- | --------------- | ------------- | ----------- |
| `hmmscore` | `score_cgi` | `/sequence19/scoreAlignXml.cgi` | `SequenceSearchAction` |
| `hmmscore` | `align_cgi` | `/sequence2/alignOnTheFly.cgi` | `HMMAlignAction` |
| `csnp` | `snpScore_cgi` | `/cgi-bin/snpScore.cgi` | `CsnpScoreAction` |
| `refmap` | `map_panther_cgi` | `/mapping19/genericMapping.cgi` | `RefProteomeMapping` (used by `GeneListAnalysisAction`) |
| `refmap` | `map_panther_stats` | `/mapping19/stats` | `OrganismHelper` (organisms available for mapping) |
| `refmap` | `map_panther_cls` | `/mapping19/panther_classification/<organism>` | `RefProteomeMapping` |
| `treegrafter` | `tree_grafter_url` | `/treegrafting19/treeGrafter.cgi` | `TreeGrafterHelper`, from `SequenceSearchAction` |

### `hmmscore`: pantherScoring

Scores protein sequences against the PANTHER HMM library with HMMER3 (`hmmscan` or `hmmsearch`).

- **Entry points:**
  - `pantherScore.pl`: the batch CLI, with best-hit, all-hits and InterProScan output
  - `scoreAlignXml.cgi`: scores and aligns, returns XML
  - `alignOnTheFly.cgi`: one alignment, returns HTML
- **Library:** about 8,000 lines in `lib/`. Most of it is the `FamLibBuilder`/`FamLibEntry` classes in prod and build variants. `Blast.pm`, `Hit.pm` and `Hsp.pm` appear unused.
- **Data:** the HMM library (`books/`, `globals/`, the concatenated `binHmm`) and a FASTA file with a DBM index.

Sources: `legacy/pantherScoring/` and `docs/phase1/developer-guide/panther-scoring.md`.

### `refmap`: RefProteomeMapper

Maps protein IDs (for example, UniProt accessions) to PANTHER family IDs with a hash lookup. Unmatched IDs return `NOHIT`.

- **Entry points:** `map_panther.pl` (CLI) and `genericMapping.cgi` (`organism`, `fileContents`). The website also fetches `stats` and the raw classification file for each organism.
- **Data:** one tab-delimited classification file per organism.

Sources: `legacy/RefProteomeMapper/` and `docs/phase1/developer-guide/refproteome-mapper.md`.

### `csnp`: PANTHER-PSEP

The service is `snpScore.cgi`. It reads the form, then shells out to three Perl scripts in sequence:

```text
snpScore.cgi ─► run_blastp.pl ─► parse_blastp.pl ─► PANTHER_PSEP1.01.pl ─► XML
                (BLAST+ search)   (best family hit,    (trace back through the tree,
                                   map SNP position)    age in Mya, prediction)
```

- **Size:** under 1,000 lines of Perl.
- **Runtime:** one external tool, NCBI BLAST+.
- **Output:** the age, a message (`probably benign` / `possibly damaging` / `probably damaging`) and `pDel`, a probability of a deleterious effect.
- **Data:** frozen PANTHER 9 files:
  - the PANTHER9 BLAST database
  - the per-family PAML library (`.paml`, `.orig.tree`, `.rst`)
  - `species_pthr8_time.nhx`

Not part of the service:

- `controller.pl` and `BlastpExisit.pl` are alternative CLI entry points. `controller.pl` can't run BLAST at all.
- `HUMAN` is the sample's step-1 BLAST output. "HUMAN" is only the default value of the `species` form field.

**The reference is described in detail.** `legacy/cSNP_analysis/` is a git repository; its `main` at `cebb5ab` is the parity reference.

- **[Legacy behaviour spec](#csnp-reference-documents):** the data contracts, the algorithm as implemented, a quirk catalog with IDs (`SCORE-2`, `CGI-5`, …), pinned checksums and golden outputs.
- **Parity review:** what the spec means for the port. It found that the legacy output is not a safe ground truth. Several defects silently change scores, so matching the goldens byte for byte would reproduce them:

| ID | Defect | Effect |
| -- | ------ | ------ |
| `SCORE-2` | The trace-back starts from the *last* `.paml` header match, and internal-node labels collide with leaf labels | Wrong start node for 17.4% of leaves; 17.1% of human BLAST DB entries |
| `SCORE-7`, `SCORE-8` | State leaks between SNPs (no `use strict`, globals never reset) | CLI batch results depend on input order; the CGI (one protein per request) is unaffected |
| `CGI-2`, `CGI-3` | Neither CGI copy parses what the website sends (`+`-joined substitutions) | `main`'s copy scores nothing; the site's copy drops any token containing `2` or `B` |
| `CGI-5`, `CGI-6` | `species` goes unquoted into a shell; concurrent requests share a temp file and query id | Command injection; one user can get another's results |
| `MAP-4` | The residue at the alignment start, and one after a query-side gap, are never mapped | Every `M1x` comes back "Invalid substitution" |
| `SCORE-5`, `SCORE-6` | Thresholds 180/380 vs 200/450 in the docs; pDel tests `age < bound` vs the PI's inclusive bounds | Different messages and pDel values, depending on which is right |
| `DATA-3` | The species file lacks Perissodactyla, Artiodactyla and Sauria | 40,506 speciation nodes aged as duplications |

#### `csnp` reference documents

Paths are relative to `panther-workspace/legacy/cSNP_analysis/`:

- `.specs/2026-10-28-legacy-behavior-spec.md`: what `main` does, confirmed by running it.
- `docs/2026-10-28-parity-review.md`: the defects, their measured impact, and the keep-or-fix decisions.
- `CLAUDE.md`: how to run the scripts safely.

These correct `docs/phase1/developer-guide/csnp-analysis.md` in several places. Where they disagree, trust them.

### `treegrafter`: TreeGrafter

Places a protein sequence in a PANTHER family tree and infers its subfamily and GO terms from its neighbours.

- **Legacy:** `treeGrafter.pl` 1.01 uses HMMER, then RAxML 8.2.4, and has the PANTHER 12 directory names hardcoded.
- **Replacement:** we adopt EBI's Python `treegrafter` instead of porting the Perl.

What the EBI version does differently:

- It reads `hmmsearch` text output (with alignments) that the caller produces.
- It places sequences with EPA-ng instead of RAxML.
- It targets PANTHER 19 and PAINT 19.
- Its `prepare` step, run once per PAINT release, writes JSON for each family.
- Its output is a TSV of up to 15 columns.
- It's licensed Apache-2.0.

Its core functions take explicit arguments and can be imported. But it calls `sys.exit()` on bad input, and it discards EPA-ng's stderr.

The website's `treeGrafter.cgi` isn't in `panther-workspace`. Needs team verification.

Sources: `legacy/TreeGrafter/`, `docs/phase1/developer-guide/treegrafter.md` and the EBI repository.

## Frontend (`frontend/`): Accepted

Decided on 2026-10-28 and moved to its own doc: [frontend-stack.md](frontend-stack.md). The frontend ↔ api contract is still open here, under [Shared Concerns](#shared-concerns).

## API (`api/`): Agree, Built Around Jobs

FastAPI is the right choice. It's the same language as the engine, and it produces OpenAPI docs automatically. Pydantic validates the inputs, replacing the CGIs' hand-written form parsing (which is where the `tr/%2B/ /` bug lives).

One FastAPI app serves all four services. Its tooling (uv, Python 3.13, Ruff, basedpyright, pytest), its error format and how the OpenAPI schema reaches the frontend are in [api-stack.md](api-stack.md).

Recommendations:

1. **Make scoring a job, not a blocking request.** BLAST and HMMER searches, and tree placement in particular, take seconds to minutes, and batch input takes longer.
   - Contract: `POST /api/v1/jobs` returns `202` with an `id`. `GET /api/v1/jobs/{id}` returns the status, then the results.
   - Start with a worker pool inside the API, of **processes, not threads** (`ProcessPoolExecutor`). Move to a Redis-backed queue (RQ or arq) once jobs must survive restarts or we run more than one API instance. The contract stays the same, so the frontend doesn't change.
   - **Why processes:** the external tools run as subprocesses and don't hold the GIL, but the Python around them does. cSNP's trace-back is pure Python and CPU-bound: the Perl takes about 10 s for step 3 of the 35-SNP sample. In a thread, it would stall the event loop and every other request.
   - **Set the workers' start method explicitly to `spawn`** (the pool's `mp_context`). The default differs by platform: `spawn` on Windows and macOS, `fork` on Linux in Python 3.13 and `forkserver` from 3.14. Code that works under one can fail under another, for example with job functions that can't be pickled, or state set up at import time. `spawn` is the one method every platform has.
   - **Size the pool by memory as well as CPU.** The cSNP PAML library is 19.2 GB unpacked. Its `.paml` files average 2 MB but reach 136 MB (`PTHR11695`); the sample's family, `PTHR10366`, is 69 MB. The engine should read only the rows a SNP needs rather than load a whole `.paml` in each worker.
   - Any synchronous endpoint uses the same pool. Engine code never runs on the event loop.
   - `refmap` is a lookup that takes milliseconds. Whether it also goes through jobs is an open question.
2. **`panther-site-java` moves to the JSON API; no compatibility endpoints.** Decided 2026-10-29. Instead of this API imitating the legacy URLs in [What We're Replacing](#what-were-replacing) and their XML, HTML and text responses, the site is changed to call `/api/v1` and read JSON, for all four services. That change is made in `panther-site-java`, not here.
   - The OpenAPI schema then has two consumers, `frontend/` and the site. A breaking change to `/api/v1` needs both updated.
   - **XML is deferred, not ruled out.** It can be added per service as an optional format for a finished result (`Accept: application/xml`, with errors as `application/problem+xml`), if something other than the site turns out to call the legacy URLs. The engine returns typed results and the API renders them, so adding it later changes nothing that exists.
   - Whether the site polls jobs or waits on a synchronous call is open; it's the API developer's decision.
3. **Report versions in every response:** the PANTHER data version, the external tool versions and the engine version. Then a result can always be traced back to the data that produced it.

## Engine (`engine/`): Agree, With Conditions

Porting the Perl to Python removes the last Perl from these services. The cSNP and refmap ports are small; pantherScoring is larger mainly because of its library classes.

Conditions:

1. **Build a library, not a second web service.** Make it a Python package with a CLI, and have the FastAPI app import it. The boundary between `api/` and `engine/` is then a typed function call rather than HTTP, which saves a network hop, a deployment and a second contract.
   - Renamed from `backend/` to `engine/` on 2026-10-28. FastAPI is also backend code, so "api" vs "backend" would have caused confusion about who owns what.
   - The Python package is `panther_engine` (distribution `panther-engine`, command `panther-engine`), in a `src/` layout. Named by the engine developer on 2026-10-29 (`scaffold-engine`).
2. **One package, shared `core/`, one submodule per service:**

   ```text
   engine/src/panther_engine/
     core/          versioned data paths, external tool runners (blastp, hmmscan/hmmsearch,
                    epa-ng), FASTA parsing, one work directory per job
     csnp/          BLAST+ -> family -> PAML trace-back -> age -> prediction
     hmmscore/      HMMER3 -> best / all / InterProScan hits, alignments
     refmap/        ID -> PANTHER family lookup
     treegrafter/   adapter over EBI treegrafter: hmmsearch via core, then placement
     cli.py         one CLI, a subcommand per service
   ```

   - **`core/` comes first,** and every service uses it. Otherwise each port repeats the same legacy faults: hardcoded `/usr/tmp/`, relative data paths, temp files named by PID.
   - **`core`'s HMMER runner must produce full text output with alignments,** for `treegrafter`, as well as the `--domtblout` table `hmmscore` reads.
3. **Write parity tests before porting.** See [docs/parity/](../parity/README.md).
   - For each ported service, run the Perl in a container on a fixed set of inputs, and save the outputs as golden files.
   - The Python output must match them, except for divergences we've deliberately chosen and written down.
   - **Keep the reference container as a test oracle.** For `csnp`:
     - It holds Perl 5, the legacy code at the parity reference (`pantherdb/cSNP_analysis` at `cebb5ab`, not copied into this repo) and the same BLAST+ as the runtime image. It mounts the cSNP data read-only.
     - **The scripts come from a developer's checkout, for now.** `pantherdb/cSNP_analysis` is private, so the image can't clone it. A developer runs `git archive cebb5ab` on their own checkout and passes the result to the build as a named build context; each script is checked against a pinned sha256 (engine developer, 2026-10-29). The commands are in [golden-setup.md](../parity/golden-setup.md). CI doesn't build this image.
     - It's for tests only. Perl never goes into the runtime image, beyond the minimal `perl-base` that Debian, its base image, can't do without (engine developer, 2026-10-30).
     - Beyond the fixed goldens, tests can run generated inputs through both the Perl and the Python and compare them. The goldens in the legacy behaviour spec §7 cover 2 of the 8,607 families, which is thin for the trace-back. Run each generated case in a fresh Perl process, so leaked batch state (`SCORE-7`, `SCORE-8`) doesn't carry between cases. A property-based test tool such as Hypothesis is a new dependency, so it comes with its own proposal.
     - The comparison applies only approved divergences. Until a row is approved, the Python must match the Perl, defects included.
4. **Keep external tools as binaries,** called with `subprocess`.
5. **Adopt `treegrafter`, don't port it.**
   - Pin EBI's repository by git commit. It doesn't appear to be on PyPI; needs team verification.
   - Wrap it in our adapter. The adapter catches `SystemExit` and checks EPA-ng's result itself.
   - Run its `prepare` step as part of data provisioning for each PAINT release, not per request.
6. **Fix legacy bugs on purpose, and record each one as a divergence.** For cSNP:
   - **Never replicate** the command injection (`CGI-5`) or the shared temp file and query id (`CGI-6`). Neither changes a correct single request's output, so neither needs a divergence row.
   - **Decide keep or fix** for each defect that changes results: `SCORE-2`, `SCORE-7`/`SCORE-8` and `MAP-4`. (`CGI-2`/`CGI-3` no longer apply: there is no legacy endpoint to parse the site's form input.) Each fix is a proposed row in [divergences.md](../parity/divergences.md) until the science owner approves it, and it needs updated goldens.
   - **`SCORE-6` is kept for M1:** pDel tests `age < bound`, as the code does (condition 7).
   - **Plumbing to fix freely,** with no output change: read the species tree path from config instead of a relative path; give each job its own temp directory and delete it afterwards; move the `.rst` parsing (fixed 0-based lines 11 and 14, `SCORE-9`) into one module with its own tests.
7. **Keep the code's cSNP thresholds and pDel bounds for M1** (`SCORE-5`, `SCORE-6`). `PANTHER_PSEP1.01.pl` classifies at **180 / 380 Mya**, as does the 2016 README, and pDel tests `age < bound`. The website help page and the science owner's 2021 ticket say **200 / 450 Mya**, and the ticket's pDel table has inclusive bounds.
   - **Decided by the engine developer on 2026-10-29:** where the legacy code and its docs disagree, follow the code, so M1 reproduces what ran in production.
   - **The docs' values are proposed rows 4 and 7** in [divergences.md](../parity/divergences.md), deferred until cSNP is live on production. Then the science owner is asked which values are correct.

## Runtime Tools and Milestones

Each service uses its own legacy toolchain. Changing any service's scientific method needs the science owner's sign-off.

| Service | External tools | M1 acceptance (parity target) |
| ------- | -------------- | ----------------------------- |
| `hmmscore` | HMMER3 | Matches the legacy Perl `pantherScore.pl` golden files |
| `refmap` | none | Matches the legacy Perl `map_panther.pl` golden files |
| `csnp` | BLAST+ | Matches the legacy Perl PSEP golden files on the frozen data |
| `treegrafter` | HMMER3, EPA-ng | Matches the pinned EBI `treegrafter` on fixed inputs. Leaving the Perl 1.01 is one [divergence](../parity/divergences.md) |

**RAxML is not used.** It was the legacy TreeGrafter's placement tool. The EBI version uses EPA-ng.

### Pinning Tool Versions

A tool's version is part of each service's reference, like the data version: a different BLAST+ or HMMER can return different hits for the same input.

- **The container image is the pin.** Its Dockerfile names the base image by digest and each tool by exact version and sha256. The image digest then fixes every tool for the runtime, the parity tests and CI. Production's new server will run containers (decided 2026-10-29).
- **Developers run the tools in the same image,** through `docker compose`. A local install, through Homebrew or conda, is a convenience and doesn't count for parity.
- **Where each tool comes from is a Dockerfile detail,** chosen per tool: Bioconda (micromamba), or the upstream release (NCBI's BLAST+ tarballs; HMMER and EPA-ng from source). Checked 2026-10-29:

  | Source | BLAST+ | HMMER | EPA-ng |
  | ------ | ------ | ----- | ------ |
  | Bioconda `linux-64` | 2.2.31 to 2.17.0, with gaps; 160 MB compressed, plus Perl, `entrez-direct` and `ncbi-vdb` | 3.4 and older; 9 MB | 0.3.8 and older; 1.4 MB |
  | Bioconda `linux-aarch64` / `osx-arm64` | 2.16.0 / 2.16.0, 2.17.0 | 3.4 | 0.3.8 |
  | Upstream | Every release, 2.2.18 to 2.17.0; 2.17.0 as x64 (296 MB) and aarch64 (243 MB) Linux tarballs | Source, 20 MB | Source, cmake |
  | PyPI | No | `hmmer` 3.4.0.2, binary wheels published by one EBI developer | No |

  - A multi-stage build can copy just the binaries we call (`blastp`, `hmmscan`, `hmmsearch`, `epa-ng`). Either way, the tools are small next to the data.
  - Build the image for `linux/amd64` and `linux/arm64`, so Apple Silicon machines don't emulate BLAST.
  - **uv stays the Python manager** ([api-stack.md](api-stack.md)). Only HMMER is on PyPI, so uv can't pin the tools. *Rejected:* pixi, which locks conda and PyPI packages in one file but would replace uv; distro packages (`apt`), whose versions follow the distro release.
- **Choose BLAST+ for compatibility, not to reproduce old production.** The legacy production server is gone, so its BLAST+ version can't be recovered. (`panther_build` uses 2.11.0 on the cluster; matching it isn't required.) The criteria, and how 2.17.0 did when tested on 2026-10-29 with the official `ncbi/blast:2.17.0` image and the release's `sample.fasta`:

  | Criterion | 2.17.0 |
  | --------- | ------ |
  | Reads the PANTHER9 database: BLAST database format v4 (`.phr`, `.pin`, `.psq`), 570,173 sequences, built 2015-04-19 | Yes |
  | Reports `sseqid` as the first word of each FASTA header (`HUMAN\|Ensembl=…\|UniProtKB=P26439:PTHR10366:SF296`). The database was built without `-parse_seqids`, and step 2 parses the family and gene out of `sseqid` | Yes |
  | Accepts the legacy command line: `-outfmt 10` with `qseq` and `sseq`, `-best_hit_overhang 0.1`, `-best_hit_score_edge 0.1` | Yes |
  | Returns the `HUMAN` fixture's hits | Yes. After step 2's sort and species filter: the same 4 rows, in the same order, with identical `qseq` and `sseq` |
  | Has Linux builds for x64 and aarch64 | Yes, as NCBI tarballs. The official `ncbi/blast` image is amd64 only, so the arm64 image installs the tarball |

  **2.17.0 passes, so it's the proposed pin.** Its output differs from the fixture only in formatting:
  - **`pident` has 3 decimals** (`93.801`) where the fixture has 2 (`93.80`). Step 2 ranks hits by `pident` (`MAP-1`), so hits that tied at 2 decimals no longer tie. The port should round `pident` to 2 decimals before ranking, so ties fall back as in the legacy sort.
  - **`bitscore` has no leading space** below 1000: the fixture pads `769` to four characters. Step 2 doesn't read it.

  `PANTHER9.blast.tar.gz` also ships the FASTA the database was built from (`blast/blast.fasta`). If a later BLAST+ drops format v4, `makeblastdb` can rebuild the database. A rebuilt database no longer matches the archive pinned in spec §7.1, so then pin the FASTA's checksum too.
- **cSNP's BLAST step has a golden made with 2.17.0** (`port-csnp`): `engine/tests/golden/csnp/blast/`, the output for the three sample proteins against the data sample's database, the same on arm64 and amd64. Each protein's best hit matches its first row in the legacy `HUMAN` fixture in subject id, starts and aligned sequences. With the old version unknown, that golden can't prove parity with old production. It guards against later version changes picking a different best hit ([golden-setup.md](../parity/golden-setup.md#the-step-1-golden)).
- **Report each tool's version in responses** (API recommendation 3).

### cSNP's M2: HMMER or Grafting for PSEP

The legacy cSNP code assigns the family by best BLAST+ hit. It gets evolutionary history from PAML ancestral reconstructions that the library build computed in advance. Using HMMER or tree grafting for cSNP would change the scientific method, so it isn't part of a port:

- **HMMER family assignment** can pick a different family than the best BLAST hit, which changes scores.
- **Grafting the query into the tree** changes where the trace-back starts. PSEP reads PAML-reconstructed states at existing tree nodes, so how a grafted position maps onto those is a science question, not an engineering one.

| Milestone | Scope | Acceptance |
| --------- | ----- | ---------- |
| M1 | Faithful port. BLAST+ only | Matches the Perl golden files |
| M2 (optional) | Method change with HMMER and/or grafting | Science owner signs off. Validated on a benchmark of known pathogenic and benign variants, not on Perl parity |

The other three services have no M2 defined.

## Shared Concerns

- **Data.** Large external files, mounted read-only from two versioned roots:

  | Root | Contents | Used by |
  | ---- | -------- | ------- |
  | `/data/panther/<version>/` | The current PANTHER release (19 today): HMM library, family MSAs and trees, PAINT annotations, per-organism classification files, and treegrafter's `prepare` output | `hmmscore`, `refmap`, `treegrafter` |
  | `/data/csnp/<version>/` | Frozen precomputed data from PANTHER 9: BLAST database, PAML library, species tree (checksums pinned in the legacy behaviour spec §7.1) | `csnp` |

  - **cSNP's BLAST database must stay matched to its PAML library.** It can't use the current release's sequences, or the family and node IDs won't line up.
  - **Regenerating the cSNP data is out of scope here.** Rebuilding PAML_RST for newer PANTHER libraries is a separate project, once the service is up. Until then, the frozen files are used as they are, including the two empty `.rst` files (`PTHR11711`, `PTHR19241`).
  - **The cSNP PAML library is 2.35 GB compressed and 19.2 GB unpacked:** 8,607 families, three files each. The developer copy, `panther_build/PAML_RST.tar.gz` beside `panther-workspace`, matches the checksum pinned in spec §7.1 (checked 2026-10-29). It was tarballed from the legacy production server before that was shut down, so it is the library build production ran (engine developer, 2026-10-29).
  - **Developers and CI use a sample of the cSNP data.** The full set lives on staging and production (Environments, below).
    - **Pick the sample from a one-time library survey,** before porting. Done on 2026-10-29: [csnp-library-survey.md](../parity/csnp-library-survey.md). Parse every family with the new parser, sort the file variants, and check what should hold: every `.paml` has its `.rst` and `.orig.tree`, the fixed `.rst` lines 11 and 14 (`SCORE-9`) have the expected shape, and so on. Then include one family per variant. The survey is Python only, and runs wherever the archive is.
    - **Start from** `PTHR10366` and `PTHR15126` (the goldens in spec §7) and `PTHR11711` and `PTHR19241` (empty `.rst`). Variants known so far: internal-node labels that collide with leaf labels (`SCORE-2`), split families (`DATA-1`), taxa missing from the species file and `Ev=0>0` nodes (`DATA-3`), and very large `.paml` files.
    - **Use the PANTHER9 BLAST database whole** (690 MB unpacked). A cut-down database changes e-values, which scale with database size, and so can change which hits pass the cutoff; it would need the full size passed with `-dbsize`.
    - **The sample is a public release asset of this repository,** decided and approved for publishing by the engine developer on 2026-10-29. The release `csnp-sample-1` held 15 families, the species tree and the PSEP copyright statement: 26 MB, 260 MB unpacked. `csnp-sample-2` adds the whole PANTHER9 BLAST database (`port-csnp`), so CI can run `blastp` end to end: 157 MB, 622 MB unpacked. `engine/src/panther_engine/csnp/sample.json` pins the current sample. It unpacks under `PANTHER_DATA_DIR` at `csnp/9/`, in the layout of the full library, so code never needs to know which it has. Fetching it, and publishing a new one, are in [engine.md](../testing/engine.md#the-csnp-data-sample). Git LFS and an extract-only script were rejected (`add-csnp-survey-and-sample`, design decision 4).
- **Containers:** one image for the API plus engine (Python, BLAST+, HMMER3, EPA-ng, [pinned](#pinning-tool-versions)), and a static build for the frontend. Production runs these containers. A test-only image runs the legacy Perl references (Engine condition 3). A `docker compose` setup for local development lets all three developers run the same stack.
- **Developer platforms.** Everything that calls the engine's tools runs in the containers, so no machine needs native BLAST+, HMMER or EPA-ng. HMMER and EPA-ng have no Windows builds at all.
  - **Windows:** Docker Desktop with WSL2. Clone the repo, and `panther-workspace` beside it, inside the WSL2 filesystem (for example `~/panther/`), and run git, npm, uv and `docker compose` from the WSL2 shell. Bind mounts from `C:\` cross a slow file-sharing bridge, and file watching (Vite, server reload) misses changes made across it. x86-64 laptops run the amd64 image natively. The engine's compose checks were run this way on 2026-10-29, and pass (`scaffold-engine`).
  - **Apple Silicon and Windows on Arm:** the `linux/arm64` image ([Pinning Tool Versions](#pinning-tool-versions)). CI builds and tests it natively on GitHub's `ubuntu-24.04-arm` runners, which this repository can use.
  - **Data:** developers use the sample of the cSNP data (Data, above), not the full 19.2 GB PAML library (decided 2026-10-29).
- **Environments.** Decided 2026-10-29:

  | Environment | cSNP data | Runs |
  | ----------- | --------- | ---- |
  | Developer machines | The sample | `docker compose`; unit tests; parity on the sample |
  | GitHub CI | The sample | Every pull request: unit tests and parity on the sample |
  | Staging | A full copy, checked against pinned checksums | By hand: the full Perl-vs-Python comparison, on the image digest that will ship |
  | Production | The full data | The same image digest, promoted from staging |

  - **Our team maintains staging,** likely on an existing server in our infrastructure. Its runs are started by hand, never by pull requests: the repo is public, and code from a fork's pull request mustn't run on a machine that holds the data.
  - **The full comparison runs once for M1 acceptance,** and again before a release that changes how cSNP parses the PAML files or traces back. It feeds a few generated SNPs per family straight into step 3, so BLAST isn't needed. The data is frozen, so between such changes it would only repeat the same answer. Record each run's result in [docs/parity/](../parity/README.md).
  - **Every deploy,** to staging and to production, checks the data against a pinned checksum manifest, then smoke-tests the deployed service with the golden requests. A wrong mount or a mismatched data copy is a likelier production fault than a code path only the full library reaches.
- **Contracts that let the three developers work in parallel:**

| Between | Contract | Agree on it |
| ------- | -------- | ----------- |
| frontend ↔ api | OpenAPI schema | First. The frontend can build against a mocked API in the meantime |
| api ↔ engine | Typed Python interface (input and result dataclasses), per service | Before each service's port starts |

## Process Note

This project doesn't follow the `panther-workspace` SDLC strictly, which would put tech-stack decisions after requirements. Each service is small and well bounded, so choosing the stack now is low risk. Even so, treat this doc as **Proposed** until the open questions are answered.

## Open Questions

Each needs team verification.

### All services

- **Transition:** the site moves to the JSON API ([API recommendation 2](#api-api-agree-built-around-jobs)). Does anything other than the site call the legacy URLs? Access logs, if they still exist, would show this, and whether any service needs XML.
- **Input size:** what is the largest request we accept for each service? This decides how soon we need a real queue.
- **Jobs vs synchronous:** does `refmap` go through jobs, or get a synchronous endpoint?
- **Who builds the data for each release:** the HMM library, the classification files, the treegrafter `prepare` output?
- **Staging server:** which existing server, and does it have room for the full data of all four services (cSNP's alone is 19.2 GB unpacked) and the Perl reference image?
- **Making the original repositories public:** `pantherdb/cSNP_analysis` and `pantherdb/pantherScoring` are private; `RefProteomeMapper` is public. So the reference images for `csnp` and `hmmscore` build from a developer's checkout. Public repositories would let the images clone at build time, as Engine condition 3 first said, and let CI build them. To consider eventually (engine developer, 2026-10-29).
- **Licence:** the PSEP 1.01 release is GPLv2, copyright 2016 Paul Thomas, and this repository has no licence. A port is arguably a derivative work. Does this repository need a licence, and which one?

### `csnp`

The legacy behaviour spec's §8 lists these in full.

- **Thresholds and pDel, after production:** M1 keeps the code's 180 / 380 Mya and `age < bound` ([Engine condition 7](#engine-engine-agree-with-conditions)). Once cSNP is live on production, ask the science owner which is correct: those, or 200 / 450 Mya (help page, the science owner's 2021 ticket) with the table's inclusive pDel bounds (divergence rows 4 and 7).
- **The PSEP definition:** is reporting the first *failing* ancestor's age, rather than the last preserved one's, what the paper intends (`SCORE-3`)?
- **Keep or fix:** for each defect in the parity review's "Decisions needed" table.
- **Production CGI:** can't be checked any more. The legacy cSNP production server is gone, so which `snpScore.cgi` copy it ran is unknown. That doesn't block the port: the site moves to the JSON API, so no CGI copy is imitated. The library build is known: the pinned `PAML_RST.tar.gz` (checksum in spec §7.1) was tarballed from the production server before it was shut down (Data, under [Shared Concerns](#shared-concerns)).
- **Species:** which species must the species filter support? Should the species file gain Perissodactyla, Artiodactyla and Sauria (`DATA-3`)?
- **Split families:** should the 410 families that exist only as split parts (`PTHRnnnnn_N`) be reachable (`DATA-1`)?

### `hmmscore`

- **Production CGIs:** which copy of `scoreAlignXml.cgi` and `alignOnTheFly.cgi` runs? The copies in `pantherScoring/` and `panther-site-java/scoring/` differ, by 55 and 109 lines even ignoring whitespace.
- **Library modes:** how do the prod and build library variants (`FamLibBuilder_prod` vs `_build`) differ, and do we need both?

### `refmap`

- **Stats:** what exactly does the website's `stats` URL return? `OrganismHelper` reads it as the list of organisms available for mapping. The source isn't in `RefProteomeMapper/`.

### `treegrafter`

- **Website CGI:** where is the source of `treeGrafter.cgi`, and what does it return?
- **Packaging:** is EBI's `treegrafter` on PyPI, or do we pin a git commit? Do we call its functions in-process, or run its CLI?

## Review

| Reviewer | Covers | Status |
| -------- | ------ | ------ |
| Frontend developer | Frontend ↔ api contract (the frontend stack is accepted in [frontend-stack.md](frontend-stack.md)) | Pending |
| API developer | API section; both contracts | Pending |
| Engine developer | Engine section; M1 scope for each service | Pending |
| Science owner (`thomaspd`) | cSNP thresholds, after production; cSNP's M2; the TreeGrafter divergence | Pending |

Once everyone has signed off and the open questions are answered, change the status at the top to **Accepted**.
