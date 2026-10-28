# Tech Stack Proposal

**Status:** Proposed, 2026-10-27; revised 2026-10-28 for four services. Not final until the [open questions](#open-questions) are answered and the [reviewers](#review) sign off. The frontend part was split out and accepted on 2026-10-28: see [frontend-stack.md](frontend-stack.md).

## Summary

| Part | Folder | Proposed | Verdict |
| ---- | ------ | -------- | ------- |
| Frontend | `frontend/` | React 19 + Vite + TypeScript, Mantine + Tailwind, RTK Query | Accepted, in [frontend-stack.md](frontend-stack.md) |
| API | `api/` | FastAPI (Python), one app for all four services | Agree, built around jobs |
| Engine | `engine/` | One Python package: shared `core/` plus one submodule per service | Agree, as a library with parity tests |
| Runtime tools | — | BLAST+, HMMER3, EPA-ng | Per service: see [Runtime Tools and Milestones](#runtime-tools-and-milestones) |

## Scope: Four Services

Revised on 2026-10-28. The repo was first scoped to cSNP scoring only. It replaces four legacy PANTHER services:

| Service | Replaces (in `panther-workspace/legacy/`) | Approach | Priority |
| ------- | ----------------------------------------- | -------- | -------- |
| `hmmscore` | `pantherScoring/` | Port the Perl | 1 |
| `refmap` | `RefProteomeMapper/` | Port the Perl | 1 |
| `csnp` | `cSNP_analysis/`: `snpScore.cgi` and the scripts it runs | Port the Perl | 2 |
| `treegrafter` | `TreeGrafter/` (Perl 1.01) | **Adopt** EBI's Python [`treegrafter`](https://github.com/ebi-pf-team/treegrafter) | 3 |

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

One FastAPI app serves all four services.

Recommendations:

1. **Make scoring a job, not a blocking request.** BLAST and HMMER searches, and tree placement in particular, take seconds to minutes, and batch input takes longer.
   - Contract: `POST /api/v1/jobs` returns `202` with an `id`. `GET /api/v1/jobs/{id}` returns the status, then the results.
   - Start with an in-process worker pool. Move to a Redis-backed queue (RQ or arq) once jobs must survive restarts or we run more than one API instance. The contract stays the same, so the frontend doesn't change.
   - `refmap` is a lookup that takes milliseconds. Whether it also goes through jobs is an open question.
2. **Add compatibility endpoints for the old site.** Each one accepts the same request and returns the same response as the legacy URL in [What We're Replacing](#what-were-replacing). `panther-site-java` can then switch over by changing a setting, with no Java changes. Keep them synchronous, because the old site waits for the response. Retire each one once `frontend/` replaces its JSP page. Which ones are needed is an open question.
3. **Report versions in every response:** the PANTHER data version, the external tool versions and the engine version. Then a result can always be traced back to the data that produced it.

## Engine (`engine/`): Agree, With Conditions

Porting the Perl to Python removes the last Perl from these services. The cSNP and refmap ports are small; pantherScoring is larger mainly because of its library classes.

Conditions:

1. **Build a library, not a second web service.** Make it a Python package with a CLI, and have the FastAPI app import it. The boundary between `api/` and `engine/` is then a typed function call rather than HTTP, which saves a network hop, a deployment and a second contract.
   - Renamed from `backend/` to `engine/` on 2026-10-28. FastAPI is also backend code, so "api" vs "backend" would have caused confusion about who owns what. The engine developer names the Python package inside it.
2. **One package, shared `core/`, one submodule per service:**

   ```text
   engine/<package>/
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
4. **Keep external tools as binaries,** called with `subprocess`.
5. **Adopt `treegrafter`, don't port it.**
   - Pin EBI's repository by git commit. It doesn't appear to be on PyPI; needs team verification.
   - Wrap it in our adapter. The adapter catches `SystemExit` and checks EPA-ng's result itself.
   - Run its `prepare` step as part of data provisioning for each PAINT release, not per request.
6. **Fix legacy bugs on purpose, and record each one as a divergence.** For cSNP:
   - **Never replicate** the command injection (`CGI-5`) or the shared temp file and query id (`CGI-6`). Neither changes a correct single request's output, so neither needs a divergence row.
   - **Decide keep or fix** for each defect that changes results: `SCORE-2`, `SCORE-7`/`SCORE-8`, `SCORE-6`, `MAP-4` and `CGI-2`/`CGI-3`. Each fix is a proposed row in [divergences.md](../parity/divergences.md) until the science owner approves it, and it needs updated goldens.
   - **Plumbing to fix freely,** with no output change: read the species tree path from config instead of a relative path; give each job its own temp directory and delete it afterwards; move the `.rst` parsing (fixed 0-based lines 11 and 14, `SCORE-9`) into one module with its own tests.
7. **Settle the cSNP thresholds and pDel bounds before porting it** (`SCORE-5`, `SCORE-6`). `PANTHER_PSEP1.01.pl` classifies at **180 / 380 Mya**, as does the 2016 README. The website help page and the PI's 2021 ticket say **200 / 450 Mya**. pDel uses exclusive bounds where the PI's table has inclusive ones.

## Runtime Tools and Milestones

Each service uses its own legacy toolchain. Changing any service's scientific method needs the science owner's sign-off.

| Service | External tools | M1 acceptance (parity target) |
| ------- | -------------- | ----------------------------- |
| `hmmscore` | HMMER3 | Matches the legacy Perl `pantherScore.pl` golden files |
| `refmap` | none | Matches the legacy Perl `map_panther.pl` golden files |
| `csnp` | BLAST+ | Matches the legacy Perl PSEP golden files on the frozen data |
| `treegrafter` | HMMER3, EPA-ng | Matches the pinned EBI `treegrafter` on fixed inputs. Leaving the Perl 1.01 is one [divergence](../parity/divergences.md) |

**RAxML is not used.** It was the legacy TreeGrafter's placement tool. The EBI version uses EPA-ng.

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
  - **Refreshing the cSNP data is a later, lower-priority milestone.**
- **Containers:** one image for the API plus engine (Python, BLAST+, HMMER3, EPA-ng), and a static build for the frontend. A `docker compose` setup for local development lets all three developers run the same stack.
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

- **Transition:** must the old site keep working during the move? Which of the website settings in [What We're Replacing](#what-were-replacing) does production use, and does anything else call the legacy URLs? Access logs would show this.
- **Input size:** what is the largest request we accept for each service? This decides how soon we need a real queue.
- **Jobs vs synchronous:** does `refmap` go through jobs, or get a synchronous endpoint?
- **Who builds the data for each release:** the HMM library, the classification files, the treegrafter `prepare` output?

### `csnp`

The legacy behaviour spec's §8 lists these in full.

- **Thresholds and pDel:** which is correct, 180 / 380 Mya (code, 2016 README) or 200 / 450 Mya (help page, PI's 2021 ticket)? Should pDel use the table's inclusive bounds?
- **The PSEP definition:** is reporting the first *failing* ancestor's age, rather than the last preserved one's, what the paper intends (`SCORE-3`)?
- **Keep or fix:** for each defect in the parity review's "Decisions needed" table.
- **Production CGI:** which `snpScore.cgi` copy runs in production? The site's copy matches the unmerged `origin/dustine32-patch-1`. Can the CGI's host and port be reached from outside the website (`CGI-5`)?
- **Library build:** which PAML_RST build does production use? Is it the pinned `../panther_build/PAML_RST.tar.gz` (files dated 2015, ids consistent with the PANTHER9 BLAST DB), whose origin is unrecorded?
- **BLAST+ version:** which one does production run?
- **Species:** which species must the species filter support? Should the species file gain Perissodactyla, Artiodactyla and Sauria (`DATA-3`)?
- **Split families:** should the 410 families that exist only as split parts (`PTHRnnnnn_N`) be reachable (`DATA-1`)?
- **Refreshing the data:** does `panther_build` still produce the per-family PAML files (`.paml`, `.orig.tree`, `.rst`)?

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
| Science owner | cSNP thresholds; cSNP's M2; the TreeGrafter divergence | Pending |

Once everyone has signed off and the open questions are answered, change the status at the top to **Accepted**.
