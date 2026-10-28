# Tech Stack Proposal

**Status:** Proposed, 2026-10-27. Not final until the [open questions](#open-questions) are answered and the [reviewers](#review) sign off.

## Summary

| Part | Folder | Proposed | Verdict |
| ---- | ------ | -------- | ------- |
| Frontend | `frontend/` | React + Tailwind, same toolchain as `noctua-visual-pathway-editor` | Agree |
| API | `api/` | FastAPI (Python) | Agree, built around jobs |
| Scoring engine | `backend/` | Rewrite the Perl into Python | Agree, as a library with parity tests |
| Runtime tools | — | HMMER, RAxML | Not yet: the legacy cSNP code uses neither |

## What We're Replacing

The legacy service is small. `snpScore.cgi` reads the form, then shells out to three Perl scripts in sequence:

```text
snpScore.cgi ─► run_blastp.pl ─► parse_blastp.pl ─► PANTHER_PSEP1.01.pl ─► XML
                (BLAST+ search)   (best family hit,    (trace back through the tree,
                                   map SNP position)    age in Mya, prediction)
```

That's under 1,000 lines of Perl in total. At runtime it needs one external tool (NCBI BLAST+) and three sets of data files: the PANTHER BLAST database, the per-family PAML library (`.paml`, `.orig.tree`, `.rst`), and `species_pthr8_time.nhx`.

The website (`panther-site-java`) calls it with an HTTP POST (`sequence`, `substitutions`, `species`) and parses the XML in `CsnpScoreXMLParser`.

Sources: `panther-workspace/legacy/cSNP_analysis/` and `panther-workspace/docs/phase1/developer-guide/csnp-analysis.md`.

## Frontend (`frontend/`): Agree

React + Tailwind is a good fit, and reusing the stack the frontend developer already ships in `noctua-visual-pathway-editor` keeps the team's projects consistent.

Recommendations:

1. **Copy the toolchain, not the app.** Take Vite, React 19, TypeScript, Tailwind v4, Mantine, the ESLint/Prettier config, Vitest and Playwright. Leave out the graph-editor dependencies (`jointjs`, `reactflow`, `dagre`, Apollo/GraphQL, `socket.io`).
2. **Keep state light.** This UI is a form, a job status and a results table. RTK Query is enough, and its polling covers job status. A Redux store with feature slices probably isn't needed.
3. **Generate API types.** Generate TypeScript types from FastAPI's OpenAPI schema (for example with `openapi-typescript`) in CI. Then a change to the API can't silently break the frontend.
4. **Match the legacy features:** species selector, example input, results table, CSV export (`csnpScoreResExport.jsp`) and help text (`tips_csnpScores_content.jsp`).

## API (`api/`): Agree, Built Around Jobs

FastAPI is the right choice. It's the same language as the engine, and it produces OpenAPI docs automatically. Pydantic validates the sequence and substitution formats, replacing the CGI's hand-written form parsing (which is where the `tr/%2B/ /` bug lives).

Recommendations:

1. **Make scoring a job, not a blocking request.** Every score runs a BLAST search against the full PANTHER sequence database, and batch input can take a long time.
   - Contract: `POST /api/v1/jobs` returns `202` with an `id`. `GET /api/v1/jobs/{id}` returns the status, then the results.
   - Start with an in-process worker pool. Move to a Redis-backed queue (RQ or arq) once jobs must survive restarts or we run more than one API instance. The contract stays the same, so the frontend doesn't change.
2. **Add a compatibility endpoint for the old site.** It accepts the same form POST and returns the same XML that `CsnpScoreXMLParser` reads. `panther-site-java` can then switch over by changing `psep_scoring_host`, `scoring_port` and `snpScore_cgi` in its config, with no Java changes. Keep it synchronous, because the old site waits for the response. Retire it once `frontend/` replaces the JSP page.
3. **Report versions in every response:** PANTHER library version, BLAST+ version and engine version. Then a score can always be traced back to the data that produced it.

## Scoring Engine (`backend/`): Agree, With Conditions

Porting under 1,000 lines of Perl to Python is a sensible size of job, and it removes the last Perl from this service.

Conditions:

1. **Build a library, not a second web service.** Make it a Python package with a CLI, and have the FastAPI app import it. The boundary between `api/` and `backend/` is then a typed function call rather than HTTP, which saves a network hop, a deployment and a second contract.
   - Consider renaming `backend/` (for example to `psep/`). FastAPI is also backend, so "api" vs "backend" will cause confusion about who owns what.
2. **Write parity tests before porting.**
   - Run the Perl pipeline in a container (Perl + BLAST+ + the same data) on a fixed set of inputs, and save the outputs as golden files.
   - The Python output must match them, except for divergences we've deliberately chosen and written down.
3. **Keep BLAST+ as an external binary**, called with `subprocess`.
4. **Fix legacy bugs on purpose, and record each one as a divergence:**
   - Drop the `tr/%2B/ /` line. In the site's copy of `snpScore.cgi`, it turns every `2` into a space.
   - Read the species tree path from config instead of a relative path.
   - Give each job its own temp directory and delete it afterwards.
   - Move the RST parsing, which assumes fixed line numbers (11 and 14), into one module with its own tests.
5. **Settle the thresholds before porting.** `PANTHER_PSEP1.01.pl` classifies at **180 / 380 Mya**, but the website help page says **200 / 450 Mya**. One of them is wrong.

## HMMER and RAxML: Not Agreed Yet

What the legacy code shows:

- The cSNP code (`cSNP_analysis/` and `snpScore.cgi`) uses neither tool. It assigns the family by best BLAST+ hit, and gets evolutionary history from PAML ancestral reconstructions computed in advance by the library build.
- HMMER and RAxML are TreeGrafter's runtime tools (`docs/phase1/developer-guide/index.md`). HMMER is also used by `pantherScoring` and the library build.

If the plan is to use them for cSNP scoring, that changes the scientific method. It's not part of a port:

- **HMMER family assignment** can pick a different family than the best BLAST hit, which changes scores.
- **Grafting the query into the tree with RAxML** changes where the trace-back starts. PSEP reads PAML-reconstructed states at existing tree nodes, so how a grafted position maps onto those is a science question, not an engineering one.

Recommendation: split the work into two milestones.

| Milestone | Scope | Acceptance |
| --------- | ----- | ---------- |
| M1 | Faithful port. BLAST+ only. | Matches the Perl golden files |
| M2 (optional) | Method change with HMMER and/or RAxML | Science owner signs off. Validated on a benchmark of known pathogenic and benign variants, not on Perl parity |

Don't add either tool to the images until M2 is approved. If RAxML is adopted, also evaluate RAxML-NG and EPA-ng; the RAxML authors point new users to these successors.

## Shared Concerns

- **Data:** the BLAST database, PAML library and species tree are large external files, tied to a PANTHER release. Mount them read-only at a versioned path (for example `/data/panther/<version>/`).
- **Containers:** one image for the API plus engine (Python + BLAST+), and a static build for the frontend. A `docker compose` setup for local development lets all three developers run the same stack.
- **Contracts that let the three developers work in parallel:**

| Between | Contract | Agree on it |
| ------- | -------- | ----------- |
| frontend ↔ api | OpenAPI schema | First. The frontend can build against a mocked API in the meantime |
| api ↔ engine | Typed Python interface (input and result dataclasses) | Before the port starts |

## Process Note

The `panther-workspace` SDLC puts tech-stack decisions in Phase 4, after requirements. This service is small and well bounded, so choosing the stack now is low risk. Even so, treat this doc as **Proposed** until the open questions are answered.

## Open Questions

1. **HMMER and RAxML:** what are they for? Is this a method change, and who signs off on it?
2. **Thresholds:** which is correct, 180 / 380 Mya (code) or 200 / 450 Mya (help page)?
3. **Transition:** must the old site keep working during the move? Does anything outside `panther-site-java` call `snpScore.cgi` directly? Access logs would show this.
4. **Data:** which PANTHER release do we target? Who builds the BLAST database and PAML library for each release?
5. **Input size:** what is the largest request we accept (sequences and substitutions per request)? This decides how soon we need a real queue.
6. **Production CGI:** which `snpScore.cgi` copy runs in production?
7. **Species:** which species must the species filter support?

## Review

| Reviewer | Covers | Status |
| -------- | ------ | ------ |
| Frontend developer | Frontend section; frontend ↔ api contract | Pending |
| API developer | API section; both contracts | Pending |
| Engine developer | Scoring engine section; M1 scope | Pending |
| Science owner | Thresholds; HMMER and RAxML (M2) | Pending |

Once everyone has signed off and the open questions are answered, change the status at the top to **Accepted**.
