# CLAUDE.md

## Project

`panther-scoring-services` replaces four legacy PANTHER services, in this priority order (revised on 2026-10-29):

| Priority | Service | What it does | Replaces |
| -------- | ------- | ------------ | -------- |
| 1 | `csnp` | Coding-SNP impact scoring, the PANTHER-PSEP method | `cSNP_analysis/` (Perl, via `snpScore.cgi`) |
| 2 | `refmap` | Maps protein IDs, such as UniProt accessions, to PANTHER families | `RefProteomeMapper/` (Perl) |
| 3 | `hmmscore` | Scores protein sequences against the PANTHER HMM library (HMMER3) | `pantherScoring/` (Perl) |
| 4 | `treegrafter` | Places a sequence in a PANTHER family tree; infers subfamily and GO terms | `TreeGrafter/` (Perl 1.01). We **adopt** EBI's Python [`treegrafter`](https://github.com/ebi-pf-team/treegrafter) instead of porting it |

PANTHER-PSEP (Tang & Thomas 2016, PMID 27193693) estimates how long a substituted position has been preserved in evolution, in millions of years. It classifies the age, and reports a probability of a deleterious effect (`pDel`) from a step table. As coded (the help page and the PI's table disagree, see Gotchas):

| Prediction          | Preservation age |
| ------------------- | ---------------- |
| probably damaging   | ≥ 380 Mya        |
| possibly damaging   | 180–380 Mya      |
| probably benign     | < 180 Mya        |

**Scope is these four services.** Don't bring in other PANTHER tools. The scope was revised on 2026-10-28; the reasoning is in `docs/design/tech-stack.md`.

## Layout and Team

Three developers, one per folder. Each folder covers all four services. `frontend/` has its conventions in `frontend/CLAUDE.md`. `api/` is the FastAPI app (`panther_api`), with its conventions in `api/CLAUDE.md`, and imports the engine as a path dependency. `engine/` is the `panther_engine` package with its CLI. The root `Dockerfile` builds the pinned tools, then an `engine` stage for the engine's checks and an `api` stage that serves the API; `compose.yaml` runs both. How to run each is in `docs/testing/`.

| Folder | Owner | Stack |
| ------ | ----- | ----- |
| `frontend/` | Frontend developer | **Accepted:** React 19, TypeScript, Vite, Mantine, Tailwind v4, RTK Query. Conventions in `frontend/CLAUDE.md` |
| `api/` | API developer | Proposed: FastAPI (Python), one app for all four services |
| `engine/` | Engine developer | Proposed: one Python package, a shared `core/` plus a submodule per service (`csnp`, `hmmscore`, `refmap`, `treegrafter`) |

The frontend stack is **Accepted** (`docs/design/frontend-stack.md`). The API and engine stacks are **Proposed**, not final: the reasoning, critique and open questions are in `docs/design/tech-stack.md`. Read both before making structural decisions.

### Working Rules

- **The engine is a library, not a web service.** `engine/` is a Python package with a CLI, and `api/` imports it. Don't add HTTP between them.
- **Shared code goes in `core/`.** Data paths, external tool runners, FASTA parsing and per-job work directories are written once and used by every service.
- **Score through jobs.** `POST /api/v1/jobs` starts a job; `GET /api/v1/jobs/{id}` polls it. `panther-site-java` moves to this JSON API too; there are no compatibility endpoints imitating the legacy URLs (`docs/design/tech-stack.md`, API recommendation 2). Whether `refmap` lookups also go through jobs is an open question.
- **Never pass request data through a shell.** Run external tools with argument lists, and validate inputs such as species codes against a known list. The legacy cSNP CGI has a command injection this way (`CGI-5`).
- **The OpenAPI schema is the contract between frontend and api.** Generate the frontend's TypeScript types from it; don't write them by hand.
- **Prove parity with each service's reference.** That's the legacy Perl for `csnp`, `hmmscore` and `refmap`, and the pinned EBI version for `treegrafter`. Output must match golden files produced by the reference. Record every deliberate difference in the docs.
- **Each service keeps its own toolchain.** `csnp` uses BLAST+, `hmmscore` HMMER3, `treegrafter` HMMER3 and EPA-ng, and `refmap` nothing. Don't add a tool to a service, or change its scientific method, without the science owner's sign-off. For `csnp`, HMMER or tree grafting is milestone M2. The table is in `docs/design/tech-stack.md`.
- **Keep the frontend to its stack.** No other UI kit or CSS-in-JS, and none of the graph-editor dependencies (`jointjs`, `reactflow`, `dagre`, Apollo/GraphQL, `socket.io`).

## Development Workflow

We don't follow the five-phase PANTHER SDLC strictly: it was written for all of PANTHER, and this project covers four scoring services. OpenSpec is the process: plan every non-trivial change in `openspec/`. The CLI is pinned in `package.json`; run it with `npx openspec`. Project constraints for OpenSpec artifacts live in `openspec/config.yaml`. The full guide for people, with conventions and the spec layout, is [CONTRIBUTING.md](CONTRIBUTING.md).

1. **Propose.** `/opsx:propose <change-name>` creates `openspec/changes/<change-name>/` with `proposal.md`, `design.md`, `tasks.md` and spec deltas. The proposal states its **Area** (`frontend`, `api`, `engine` or `cross-cutting`).
2. **Review.** Open a PR with the change's artifacts. The owner of every affected area approves it before any code is written.
3. **Apply.** `/opsx:apply` works through `tasks.md`. Tick tasks as they're done, and keep the **Notes** section at the end of `tasks.md` current (next action, blockers, failed approaches, lessons learned): that is how work resumes after a lost session.
4. **Archive.** `/opsx:archive` merges the spec deltas into `openspec/specs/` and moves the change to `openspec/changes/archive/`. Before archiving, move any lesson that applies beyond this change into `CLAUDE.md` or `docs/`.

Rules:

- **OpenSpec is the only place for plans.** Don't create `.plans/`, TODO files or other task trackers.
- **Claude drafts, the team decides.** Every artifact is reviewed and owned by a person before the next step.
- **OpenSpec doesn't approve science.** A change can propose a difference from a service's reference, but it ships only with an approved row in `docs/parity/divergences.md`.
- **Pull requests and CI are the enforceable gates.** The `main` ruleset requires a pull request, a code owner's approval and a passing `ci-passed` check (`.github/workflows/ci.yml`). Instructions here and in `openspec/config.yaml` are guidance, not enforcement.

## Docs

Each `docs/` folder has a `README.md` with its rules: what belongs there, how to name files, and the format to follow. **Read that folder's README before adding or changing a doc there.** The index is `docs/README.md`.

| Folder | What goes there |
| ------ | --------------- |
| `docs/design/` | Architecture and tech decisions. Each has a status (Proposed / Accepted / Superseded) and a Review table. Never delete a doc: supersede it |
| `docs/parity/` | Proof that each service matches its reference: golden-file setup, test inputs, and `divergences.md`. The golden files themselves live in `engine/` tests |
| `docs/testing/` | Test strategy and how to run each suite |
| `docs/manual-qa/` | Manual UI checklists for testers (`NN-<area>.md`, test cases labelled `TC n.m`) |
| `docs/code-review/` | Review notes worth keeping, `YYYY-MM-DD-<topic>.md` |
| `docs/deployment/` | `runbook-<topic>.md` (kept current) and `YYYY-MM-DD-<environment>.md` records. Never put secrets here |

Rules Claude should follow:

- **Parity is the M1 acceptance test.** When porting, the Python must match the golden files. A difference is allowed only when `docs/parity/divergences.md` has a row for it with an approver. Without an approver, it's a proposal; flag it, don't ship it.
- **Changes and docs are different.** A change's proposal, design and tasks go in `openspec/changes/`. Lasting decisions that need named sign-off (tech stack, scope, thresholds, M2) and reference material go in `docs/`; a change's `design.md` links to them rather than repeating them.
- **Empty folders keep a `.gitkeep`** so git tracks them. Delete it once the folder has a real file.

## External Context: `panther-workspace`

The legacy code and Phase 1 docs live in `panther-workspace`, a sibling of this repo. Look for it in the parent directory, at `../panther-workspace` (relative to this repo's root). Don't assume an absolute path: each developer's checkout location differs. If `../panther-workspace` isn't there, ask the developer where it is rather than searching the disk.

Use it **only** for the four services, and treat it as **read-only**: never edit, create or delete files there.

- Don't assume the legacy docs are complete or scientifically verified. Check claims against the code.
- Record findings in this repo (`openspec/` or `docs/`), not there.
- Port the Perl; don't copy legacy source into this repo without a team decision.

Paths below are relative to `../panther-workspace`.

### Read these first

| Service | Developer guide | User guide | Legacy code |
| ------- | --------------- | ---------- | ----------- |
| `hmmscore` | `docs/phase1/developer-guide/panther-scoring.md` | `docs/phase1/user-guide/sequence-search.md` | `legacy/pantherScoring/` (has `CLAUDE.md`) |
| `refmap` | `docs/phase1/developer-guide/refproteome-mapper.md` | `docs/phase1/user-guide/gene-list-analysis.md` ("Generic Mapping / Reference Proteome Datasets") | `legacy/RefProteomeMapper/` (has `CLAUDE.md`) |
| `csnp` | `legacy/cSNP_analysis/.specs/2026-10-28-legacy-behavior-spec.md` and `docs/2026-10-28-parity-review.md` first; then `docs/phase1/developer-guide/csnp-analysis.md`, which they correct in places | `docs/phase1/user-guide/genetic-variant-analysis.md` ("Coding SNP Impact Scoring (PANTHER-PSEP)") | `legacy/cSNP_analysis/` (has `CLAUDE.md`, `README.txt`) |
| `treegrafter` | `docs/phase1/developer-guide/treegrafter.md` | `docs/phase1/user-guide/sequence-search.md` ("Tree Grafting Results") | `legacy/TreeGrafter/`: reference only, since we adopt EBI's version. Read EBI's [`treegrafter`](https://github.com/ebi-pf-team/treegrafter) for the code we use |

### `hmmscore`: `legacy/pantherScoring/`

| File | Role |
| ---- | ---- |
| `pantherScore.pl` | Batch CLI: HMMER3 `hmmscan` or `hmmsearch`; best-hit, all-hits or InterProScan output |
| `scoreAlignXml.cgi` | Web entry point: scores and aligns one sequence, returns XML |
| `alignOnTheFly.cgi` | Web entry point: one alignment, returns HTML |
| `lib/` | `FamLibBuilder*`, `FamLibEntry*` (prod and build library variants), `FastaFile.pm`. `Blast.pm`, `Hit.pm` and `Hsp.pm` appear unused |
| `config.example.yaml` | `library_directory`, `binHmm_library_directory`, `fasta_file`, `fasta_idx`, `tmp_directory`, `hmmer_bin_directory` |

Data it needs: the PANTHER HMM library (`books/`, `globals/`, `binHmm`) and a FASTA file with a DBM index.

### `refmap`: `legacy/RefProteomeMapper/`

| File | Role |
| ---- | ---- |
| `map_panther.pl` | CLI: maps each ID in a gene list to a PANTHER family, or `NOHIT` |
| `genericMapping.cgi` | Web entry point: `organism`, `fileContents`; returns tab-delimited text |

Data it needs: one tab-delimited classification file per organism (`panther_classification/`).

### `csnp`: `legacy/cSNP_analysis/`

It's a git repository of its own.

- **Parity reference:** `main` at `cebb5ab`.
- **Behaviour spec:** `.specs/2026-10-28-legacy-behavior-spec.md` records what `main` does. Its quirk IDs (`SCORE-2`, `CGI-5`, …) are what this repo uses to refer to legacy behaviour. Its §7 pins the input checksums and gives the golden outputs.
- **Parity review:** `docs/2026-10-28-parity-review.md` lists the defects and the keep-or-fix decisions still open.

The service is `snpScore.cgi` and what it runs:

| File | Role |
| ---- | ---- |
| `snpScore.cgi` | Web entry point. Writes the inputs to temp files, runs the three scripts below, returns XML |
| `run_blastp.pl` | Step 1: NCBI BLAST+ blastp against the PANTHER sequence database |
| `parse_blastp.pl` | Step 2: picks the best PANTHER family hit, maps the SNP position onto it |
| `PANTHER_PSEP1.01.pl` | Step 3: traces the position through the family tree, computes age and prediction |
| `species_pthr8_time.nhx` | Species tree with divergence times (Mya), read by step 3 |
| `config.example.yaml` | CGI config: `blast_bin_directory`, `blast_database`, `paml_data_directory`, `tmp_directory` |

Not part of the service:

- `controller.pl` and `BlastpExisit.pl`: alternative CLI entry points. `controller.pl` can't run BLAST at all (`RUN-2`).
- `HUMAN`: the sample's step-1 BLAST output, used as a golden fixture.
- `csnp_analysis.pl` (untracked): a dead older variant.

Data it needs: a PANTHER BLAST database and the per-family PAML library (`.paml`, `.orig.tree`, `.rst`). Both are frozen precomputed data from PANTHER 9, and must stay matched to each other.

- **Pinned copies:** the PANTHER9 BLAST DB and `../panther_build/PAML_RST.tar.gz` (files dated 2015). Their ids agree, and spec §7.1 pins their checksums.
- **Production:** `PAML_RST.tar.gz` was tarballed from the production server before it was shut down, so the pinned copy is production's library build (engine developer, 2026-10-29). This answers legacy behaviour spec §8, question 4. The port uses the pinned copies.

### `treegrafter`: `legacy/TreeGrafter/`

`treeGrafter.pl` (HMMER, then RAxML) and `Test/` (sample input, expected output, a one-family `PANTHER_mini`). Use them to understand the legacy behaviour, not as the parity target. Data it needs: the current PANTHER release's HMMs, family MSAs and trees, and PAINT annotations.

### Website integration: `legacy/panther-site-java/`

The site calls each service by URL. The settings are in `config/extra.properties.example`, and the full table is in `docs/design/tech-stack.md`.

```text
Browser ─► /tools/csnpScore  (Struts action CsnpScoreAction)
        ─► HTTP POST http://{psep_scoring_host}:{scoring_port}{snpScore_cgi}
             params: sequence, substitutions, species
        ─► snpScore.cgi ─► run_blastp.pl ─► parse_blastp.pl ─► PANTHER_PSEP1.01.pl
        ◄─ XML ─► CsnpScoreXMLParser ─► csnpScoreResults.jsp
```

| Service | Paths | Role |
| ------- | ----- | ---- |
| `hmmscore` | `src/com/ab/scienceSite/webapp/SequenceSearchAction.java`, `HMMAlignAction.java` | Calls `score_cgi` and `align_cgi` |
| `hmmscore` | `wwwroot/tools/sequenceSearchForm.jsp`, `hmmScoreForm.jsp`, `hmmScoreResults.jsp`; `wwwroot/tips/tips_exampleHmmScoreInput*.jsp` | Form, results, help |
| `hmmscore` | `scoring/scoreAlignXml.cgi`, `scoring/alignOnTheFly.cgi` | Site's copies of the CGIs (see Gotchas) |
| `refmap` | `src/com/ab/scienceSite/logic/RefProteomeMapping.java`, `src/com/ab/scienceSite/dao/jdbc/OrganismHelper.java` | Calls `map_panther_cgi`, `map_panther_cls` and `map_panther_stats` |
| `csnp` | `src/com/ab/scienceSite/webapp/CsnpScoreAction.java`, `CsnpScoreForm.java` | Form handling, POST to the scoring CGI |
| `csnp` | `src/com/ab/scienceSite/panther/csnpScore/` | `CsnpScoreXMLParser`, `CsnpScoreBean`, `CsnpAnalysisBean` |
| `csnp` | `wwwroot/tools/csnpScoreForm.jsp`, `csnpScoreResults.jsp`, `csnpScoreResExport.jsp`; `wwwroot/tips/tips_csnpScores*.jsp`, `tips_exampleCsnpInput*.jsp` | Form, results, export, help |
| `csnp` | `scoring/snpScore.cgi` | Site's copy of the CGI (see Gotchas) |
| `treegrafter` | `src/edu/usc/ksom/pm/panther/pantherdb/tools/TreeGrafterHelper.java` | Calls `tree_grafter_url`, from `SequenceSearchAction` |
| `treegrafter` | `wwwroot/tools/graftSearchResults.jsp`; `wwwroot/tips/tips_graft_sequence*.jsp` | Results, help |
| all | `config/extra.properties.example` | The URL setting for each service |
| all | `config/struts-config.xml` | `/tools/sequenceSearch`, `/tools/hmmAlign` and `/tools/csnpScore` actions |

### Other docs

These docs mention the services in passing. Use only those passages: `docs/phase1/developer-guide/panther-site-java.md`, `docs/phase1/developer-guide/panther-build.md` (where each service's input data comes from), `docs/phase1/user-guide/downloads.md`.

### Out of scope

Don't read or reuse these:

- Every other folder under `legacy/`: `db-PAINT`, `fullgo_paint_update`, `paint_unirule`, `panTree-java`, `panther_build` (except to learn where input data comes from), `panther_build_dashboard`, `pantherapi-pyclient`, `pantherdb_server_info`.
- `legacy/panther-site-java/scoring/` files for the old 2007 SNP method: `README_snp`, `grabSnpScoringFiles.pl` (see Gotchas).
- The rest of `docs/`.

## Gotchas in the Legacy Code

- **Two copies of `snpScore.cgi`, and neither reads the website's input correctly.**
  - **The site's copy:** `legacy/panther-site-java/scoring/snpScore.cgi` matches the unmerged branch `origin/dustine32-patch-1` in `cSNP_analysis`. It adds `$value =~ tr/%2B/ /;`. Perl's `tr` maps characters, not strings, so this turns every `%`, `2` and `B` in each form value into a space: `G129R` becomes `G1 9R` and is dropped (`CGI-3`).
  - **`main`'s copy:** it splits only on tab, spaces and LF, so it scores nothing when the website sends `+`-joined substitutions (`CGI-2`).
  - **Production:** the legacy production server is gone, so which copy ran there can't be checked. It doesn't matter for the port: the site moves to the JSON API, so neither copy is imitated.
- **Command injection and a temp-file race in the cSNP CGI.** `species` goes unquoted into shell commands (`CGI-5`). Concurrent requests share `./<SPECIES>` and the query id `P0001`, so they can read each other's BLAST hits (`CGI-6`). Never replicate either.
- **Wrong start node for about 17% of genes (`SCORE-2`).** `PANTHER_PSEP1.01.pl` takes the *last* `.paml` header match. Internal-node labels collide with leaf labels, so the trace-back often starts from an unrelated node. Matching the goldens byte for byte reproduces this; it's a keep-or-fix decision.
- **Batch results depend on input order (`SCORE-7`, `SCORE-8`).** There's no `use strict`, the state is package globals that are never reset, and `getYear` keeps the first family's `$i`. The CGI scores one protein per request, so it's unaffected; CLI batches spanning families are not.
- **Some residues are never mapped (`MAP-4`).** The residue at the alignment start (every `M1x`) and the one right after a query-side gap come back "Invalid substitution".
- **Two copies of the HMM scoring CGIs that differ too.** `scoreAlignXml.cgi` and `alignOnTheFly.cgi` exist in `legacy/pantherScoring/` and in `legacy/panther-site-java/scoring/`, and differ by 55 and 109 lines even ignoring whitespace. Which copies run in production needs team verification.
- **`treeGrafter.cgi` is missing.** The site calls `tree_grafter_url` (`/treegrafting19/treeGrafter.cgi`), but its source isn't in `panther-workspace`. Needs team verification.
- **Two PANTHER versions.** The site's URLs for `hmmscore`, `refmap` and `treegrafter` use PANTHER 19. `csnp` runs on frozen PANTHER 9 data. Its species tree (`species_pthr8_time.nhx`) is older still and lacks Perissodactyla, Artiodactyla and Sauria, so 40,506 speciation nodes are aged as duplications (`DATA-3`).
- **`README_snp` describes the old method.** `legacy/panther-site-java/scoring/README_snp` and `grabSnpScoringFiles.pl` are for the 2007 subPSEC/HMM tool (`snp_analysis.pl`, `pantherScore.pl`), not PSEP. Don't use them as a spec for `csnp`.
- **Wrong file name in the site's CLAUDE.md.** `legacy/panther-site-java/CLAUDE.md` lists `scoring/csnp_score.pl`, which doesn't exist.
- **The `HUMAN` file is sample BLAST output, not a species config.** It's the release sample's species-filtered step-1 output, and the fixture for the goldens. `snpScore.cgi` never reads it. "HUMAN" is only the default `species` form value (`DATA-5`).
- **The website, not the CGI, cleaned up cSNP input.** `CsnpScoreForm.java` trimmed and upper-cased the input, removed one FASTA header and all whitespace, and enforced 50,000 residues and at most one `>`, before `snpScore.cgi` saw it. The API's `scoring-input` rules do the same, so the engine receives what the legacy scripts received. The CGI on its own silently drops tokens that don't match its pattern (`snpScore.cgi` 212), which also accepts a lower-case mutant residue and `|`, as in `A10v` and `G12|`. The API instead rejects any token that isn't `[A-Z][0-9]+[A-Z]` once upper-cased (decided on #19).
- **Run the legacy cSNP scripts only in a scratch copy.** `parse_blastp.pl -s HUMAN` writes `./HUMAN`, overwriting the tracked file, and sorts its BLAST input in place. Spec §7.2 has the commands.
- **Relative path.** `PANTHER_PSEP1.01.pl` opens `species_pthr8_time.nhx` by relative path, so it only works when run from the `cSNP_analysis/` directory.
- **Fixed line numbers.** `.rst` parsing reads 0-based lines 11 (the branch list) and 14 (the tree), that is, the 12th and 15th lines (`SCORE-9`).
- **The thresholds and the pDel bounds disagree with the docs.** `PANTHER_PSEP1.01.pl` classifies at 180 / 380 Mya. The help page (`tips_csnpScores_content.jsp`) and the PI's 2021 ticket say 200 / 450 (`SCORE-5`). pDel tests `age < bound`, but the PI's table has inclusive bounds, so for example age 91 gets 0.19 instead of 0.17 (`SCORE-6`). The port follows the code: 180 / 380 and `age < bound` (engine developer, 2026-10-29). The docs' values are proposed divergence rows 4 and 7, deferred until cSNP is live on production.
- **The 2016 release's `sample.out` doesn't reproduce** against the current library (`DATA-4`). Use the goldens in spec §7.
- **Hardcoded paths and versions elsewhere.** `alignOnTheFly.cgi` writes to `/usr/tmp/`. `treeGrafter.pl` hardcodes PANTHER 12 directory names. `genericMapping.cgi` reads `panther_classification/` relative to its working directory.
- Each service's developer guide lists more under "Issues and Observations". For `csnp`, the full quirk catalog is §6 of the legacy behaviour spec.

When something isn't clear from the legacy code, say "needs team verification" rather than guessing.

When the legacy code and its docs disagree, follow the code, so M1 reproduces what ran in production. Log the docs' version as a proposed row in `docs/parity/divergences.md`, deferred until the service is live on production, and revisit it then (engine developer, 2026-10-29).
