# CLAUDE.md

## Project

`panther-scoring-services` covers PANTHER's coding-SNP (cSNP) impact scoring, the PANTHER-PSEP method (Tang & Thomas 2016, PMID 27193693). For a given amino-acid substitution, it estimates how long that position has been preserved in evolution (in millions of years) and classifies it:

| Prediction          | Preservation age |
| ------------------- | ---------------- |
| probably damaging   | ≥ 380 Mya        |
| possibly damaging   | 180–380 Mya      |
| probably benign     | < 180 Mya        |

**Scope is cSNP only.** Don't bring in HMM scoring, TreeGrafter or other PANTHER tools.

## Layout and Team

Three developers, one per folder. There is no code yet. `frontend/` has its conventions in `frontend/CLAUDE.md`; `api/` and `engine/` hold only a `.gitkeep`.

| Folder     | Owner                 | Stack |
| ---------- | --------------------- | ----- |
| `frontend/` | Frontend developer   | **Accepted:** React 19, TypeScript, Vite, Mantine, Tailwind v4, RTK Query. Conventions in `frontend/CLAUDE.md` |
| `api/`     | API developer         | Proposed: FastAPI (Python) |
| `engine/` | Engine developer      | Proposed: Python port of the Perl scoring pipeline |

The frontend stack is **Accepted** (`docs/design/frontend-stack.md`). The API and engine stacks are **Proposed**, not final: the reasoning, critique and open questions are in `docs/design/tech-stack.md`. Read both before making structural decisions.

### Working Rules

- **The engine is a library, not a web service.** `engine/` is a Python package with a CLI, and `api/` imports it. Don't add HTTP between them.
- **Score through jobs.** `POST /api/v1/jobs` starts a job; `GET /api/v1/jobs/{id}` polls it. The only exception is the synchronous legacy-XML compatibility endpoint, which keeps `panther-site-java` working.
- **The OpenAPI schema is the contract between frontend and api.** Generate the frontend's TypeScript types from it; don't write them by hand.
- **Prove parity with the Perl.** Python output must match golden files produced by the legacy pipeline. Record every deliberate difference in the docs.
- **Only BLAST+ for now.** The legacy cSNP code uses BLAST+ only. Don't add HMMER or RAxML until the team approves a change to the scientific method (milestone M2 in the design doc).
- **Keep the frontend to its stack.** No other UI kit or CSS-in-JS, and none of the graph-editor dependencies (`jointjs`, `reactflow`, `dagre`, Apollo/GraphQL, `socket.io`).

## Development Workflow

We don't follow the five-phase PANTHER SDLC strictly: it was written for all of PANTHER, and this project covers cSNP scoring only. OpenSpec is the process: plan every non-trivial change in `openspec/`. The CLI is pinned in `package.json`; run it with `npx openspec`. Project constraints for OpenSpec artifacts live in `openspec/config.yaml`. The full guide for people, with conventions and the spec layout, is [CONTRIBUTING.md](CONTRIBUTING.md).

1. **Propose.** `/opsx:propose <change-name>` creates `openspec/changes/<change-name>/` with `proposal.md`, `design.md`, `tasks.md` and spec deltas. The proposal states its **Area** (`frontend`, `api`, `engine` or `cross-cutting`).
2. **Review.** Open a PR with the change's artifacts. The owner of every affected area approves it before any code is written.
3. **Apply.** `/opsx:apply` works through `tasks.md`. Tick tasks as they're done, and keep the **Notes** section at the end of `tasks.md` current (next action, blockers, failed approaches, lessons learned): that is how work resumes after a lost session.
4. **Archive.** `/opsx:archive` merges the spec deltas into `openspec/specs/` and moves the change to `openspec/changes/archive/`. Before archiving, move any lesson that applies beyond this change into `CLAUDE.md` or `docs/`.

Rules:

- **OpenSpec is the only place for plans.** Don't create `.plans/`, TODO files or other task trackers.
- **Claude drafts, the team decides.** Every artifact is reviewed and owned by a person before the next step.
- **OpenSpec doesn't approve science.** A change can propose a difference from the Perl, but it ships only with an approved row in `docs/parity/divergences.md`.
- **Pull requests and CI are the enforceable gates.** Instructions here and in `openspec/config.yaml` are guidance, not enforcement.

## Docs

Each `docs/` folder has a `README.md` with its rules: what belongs there, how to name files, and the format to follow. **Read that folder's README before adding or changing a doc there.** The index is `docs/README.md`.

| Folder | What goes there |
| ------ | --------------- |
| `docs/design/` | Architecture and tech decisions. Each has a status (Proposed / Accepted / Superseded) and a Review table. Never delete a doc: supersede it |
| `docs/parity/` | Proof that Python matches the Perl: golden-file setup, test inputs, and `divergences.md`. The golden files themselves live in `engine/` tests |
| `docs/testing/` | Test strategy and how to run each suite |
| `docs/manual-qa/` | Manual UI checklists for testers (`NN-<area>.md`, test cases labelled `TC n.m`) |
| `docs/code-review/` | Review notes worth keeping, `YYYY-MM-DD-<topic>.md` |
| `docs/deployment/` | `runbook-<topic>.md` (kept current) and `YYYY-MM-DD-<environment>.md` records. Never put secrets here |

Rules Claude should follow:

- **Parity is the M1 acceptance test.** When porting Perl, the Python must match the golden files. A difference is allowed only when `docs/parity/divergences.md` has a row for it with an approver. Without an approver, it's a proposal; flag it, don't ship it.
- **Changes and docs are different.** A change's proposal, design and tasks go in `openspec/changes/`. Lasting decisions that need named sign-off (tech stack, thresholds, M2) and reference material go in `docs/`; a change's `design.md` links to them rather than repeating them.
- **Empty folders keep a `.gitkeep`** so git tracks them. Delete it once the folder has a real file.

## External Context: `panther-workspace` (cSNP only)

The legacy code and Phase 1 docs live in `panther-workspace`, a sibling of this repo. Look for it in the parent directory, at `../panther-workspace` (relative to this repo's root). Don't assume an absolute path: each developer's checkout location differs. If `../panther-workspace` isn't there, ask the developer where it is rather than searching the disk.

Use it **only** for cSNP material, and treat it as **read-only**: never edit, create or delete files there.

- Don't assume the legacy docs are complete or scientifically verified. Check claims against the code.
- Record findings in this repo (`openspec/` or `docs/`), not there.
- Port the Perl; don't copy legacy source into this repo without a team decision.

Paths below are relative to `../panther-workspace`.

### Read these first

| Path | What it is |
| ---- | ---------- |
| `docs/phase1/developer-guide/csnp-analysis.md` | Developer guide: pipeline, CLI flags, config, hardcoded values, open questions |
| `docs/phase1/user-guide/genetic-variant-analysis.md` | User-facing workflow (section "Coding SNP Impact Scoring (PANTHER-PSEP)") |
| `legacy/cSNP_analysis/` | The tool itself (Perl). Has its own `CLAUDE.md`, `README.txt` |

### Legacy tool: `legacy/cSNP_analysis/`

| File | Role |
| ---- | ---- |
| `controller.pl` | CLI entry point; chains the three steps below |
| `BlastpExisit.pl` | Alternative CLI entry point that skips BLAST when output is cached |
| `run_blastp.pl` | Step 1: NCBI BLAST+ blastp against the PANTHER sequence database |
| `parse_blastp.pl` | Step 2: picks the best PANTHER family hit, maps the SNP position onto it |
| `PANTHER_PSEP1.01.pl` | Step 3: traces the position through the family tree, computes age and prediction |
| `snpScore.cgi` | Web entry point: same three steps, returns XML |
| `config.example.yaml` | CGI config: `blast_bin_directory`, `blast_database`, `paml_data_directory`, `tmp_directory` |
| `species_pthr8_time.nhx` | Species tree with divergence times (Mya) |

Data it needs (not in the repo): a PANTHER BLAST database, and the per-family PAML library (`.paml`, `.orig.tree`, `.rst`). Both come from the PANTHER library build.

### Website integration: `legacy/panther-site-java/` (cSNP files only)

```text
Browser ─► /tools/csnpScore  (Struts action CsnpScoreAction)
        ─► HTTP POST http://{psep_scoring_host}:{scoring_port}{snpScore_cgi}
             params: sequence, substitutions, species
        ─► snpScore.cgi ─► run_blastp.pl ─► parse_blastp.pl ─► PANTHER_PSEP1.01.pl
        ◄─ XML ─► CsnpScoreXMLParser ─► csnpScoreResults.jsp
```

| Path | Role |
| ---- | ---- |
| `src/com/ab/scienceSite/webapp/CsnpScoreAction.java`, `CsnpScoreForm.java` | Form handling, POST to the scoring CGI |
| `src/com/ab/scienceSite/panther/csnpScore/` | `CsnpScoreXMLParser`, `CsnpScoreBean`, `CsnpAnalysisBean` |
| `wwwroot/tools/csnpScoreForm.jsp`, `csnpScoreResults.jsp`, `csnpScoreResExport.jsp` | Input form, results page, export |
| `wwwroot/tips/tips_csnpScores*.jsp`, `tips_exampleCsnpInput*.jsp` | Help pages |
| `scoring/snpScore.cgi` | Site's copy of the CGI (see Gotchas) |
| `config/extra.properties.example` | `psep_scoring_host`, `scoring_port`, `snpScore_cgi` |
| `config/struts-config.xml` | `/tools/csnpScore` action and `csnpScoreForm` bean |

### Other docs

These docs mention cSNP in passing. Use only the cSNP passages: `docs/phase1/developer-guide/panther-site-java.md`, `docs/phase1/developer-guide/panther-build.md` (where the input data comes from), `docs/phase1/user-guide/downloads.md`.

### Out of scope

Don't read or reuse these, even where they say "scoring":

- `legacy/pantherScoring/` (HMM scoring)
- `legacy/TreeGrafter/`
- The HMM parts of `legacy/panther-site-java/scoring/`: `scoreAlignXml.cgi`, `alignOnTheFly.cgi`, `grabScoringFiles.pl`, `README_scoring`, `README_library`
- Every other folder under `legacy/`, and the rest of `docs/`

## Gotchas in the Legacy Code

- **Two copies of `snpScore.cgi` that differ.** `legacy/panther-site-java/scoring/snpScore.cgi` adds the line `$value =~ tr/%2B/ /;`. Perl's `tr` maps characters, not strings, so this turns every `%`, `2` and `B` in each form value into a space. For example, `A12P` arrives as `A1 P`. Which copy runs in production needs team verification.
- **`README_snp` describes the old method.** `legacy/panther-site-java/scoring/README_snp` and `grabSnpScoringFiles.pl` are for the 2007 subPSEC/HMM tool (`snp_analysis.pl`, `pantherScore.pl`), not PSEP. Don't use them as a spec.
- **Wrong file name in the site's CLAUDE.md.** `legacy/panther-site-java/CLAUDE.md` lists `scoring/csnp_score.pl`, which doesn't exist.
- **The `HUMAN` file is described two ways.** `legacy/cSNP_analysis/CLAUDE.md` calls it a species config; `csnp-analysis.md` calls it sample BLAST output. Needs team verification.
- **Relative path.** `PANTHER_PSEP1.01.pl` opens `species_pthr8_time.nhx` by relative path, so it only works when run from the `cSNP_analysis/` directory.
- **Fixed line numbers.** RST parsing assumes line 11 is the root and line 14 is the tree.
- **The thresholds disagree.** `PANTHER_PSEP1.01.pl` classifies at 180 / 380 Mya, but the help page (`tips_csnpScores_content.jsp`) says 200 / 450 Mya. Which is correct needs team verification before porting.
- The full list is in `csnp-analysis.md` under "Issues and Observations".

When something isn't clear from the legacy code, say "needs team verification" rather than guessing.
