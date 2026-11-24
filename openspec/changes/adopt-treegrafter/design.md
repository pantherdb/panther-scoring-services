# Design

## Context

**The design decisions this change relies on:**

- **[tech-stack.md](../../../docs/design/tech-stack.md):**
  - the `treegrafter` section: adopt EBI's code, don't port the Perl;
  - Engine condition 5: pin EBI's repository by commit, wrap it in an adapter that catches `SystemExit` and checks EPA-ng's result itself, and run `prepare` once per PAINT release;
  - the engine's layout: `treegrafter/` as an adapter over EBI's code, with `hmmsearch` through `core`, whose runner writes the full text report;
  - the pinned tools: HMMER 3.4 and EPA-ng 0.3.8, already in the engine image.
- **[api-stack.md](../../../docs/design/api-stack.md):** the open question whether EBI's code runs on Python 3.13, which this change answers.
- **[engine/README.md](../../../engine/README.md):** a new runtime dependency comes with a proposal. This is that proposal.
- **[divergences.md](../../../docs/parity/divergences.md), row 1:** leaving the Perl. The science owner approved it on 2026-11-18.
- **`port-hmmscore`'s design:** the interface (decision 1), the one deadline for a whole search (decision 4) and `core`'s HMMER runners (decision 5). **`wire-hmmscore`'s design:** a timeout error of the service's own, and search tools that die with their worker.

**What exists:**

- **`treegrafter/__init__.py`** is a docstring only.
- **`core/`** has `run_tool`, with `die_with_parent`; `hmmer.hmmsearch(model, query, *, report, cpu, timeout, cwd)`, which passes only `--cpu`; EPA-ng in `tools.py`'s version report; and the streaming fetch hmmscore's data uses (`download.py`, `archive.py`, `manifest.py`, `data.py`).
- **EBI's repository at `5ef350f`** (2026-08-25) is one module, `treegrafter.py`: 661 lines, sha256 `9741da411ef4ae7c2cf5bf80b133391ee45b78149bc8aa0e2c9143ddd55de44c`, Apache-2.0. Its `requirements.txt` asks for `biopython>=1.86`. It has no `pyproject.toml`, and PyPI has no `treegrafter`.
- **The spike of 2026-11-24** ran it unchanged in the engine image, with Biopython 1.88, on the full library and release 2026-08-28. Its numbers are below where a decision uses them, and in full in the survey doc this change adds (decision 11).

## Goals / Non-Goals

**Goals:**

- Every field of a hit traces to EBI's command line at the pinned commit, or to an approved or proposed row.
- EBI's functions run unmodified. The engine adds only the EPA-ng runner, two checks, and the mapping to typed fields.
- `score()` has hmmscore's shape, so the wiring can follow `wire-hmmscore`.

**Non-Goals:**

- **The wiring:** the job, the form, the API's `422` for `~` and `-`, the limits, the running cap, the versions report, GO term names and the server's data. They're in `add-treegrafter-job`.
- **The two-stage search** (decision 6).
- **Batch grafting.** EBI's code takes many sequences; the service grafts one.
- **Fixing the ten families that can't be placed.** That's the library's build.

## Decisions

### 1. The interface, as hmmscore's

`panther_engine.treegrafter` exports:

- `DATA_VERSION`, `"19"`;
- the frozen dataclasses:
  - `TreegrafterInput(sequence)`;
  - `TreegrafterHit(panther_id, node_id, graft_point, go_terms, protein_class, score, evalue, domain_score, domain_evalue, hmm_from, hmm_to, ali_from, ali_to, env_from, env_to)`;
  - `TreegrafterResult(hit, annotations)`, where `annotations` is the release's date;
  - `AnnotationRelease(date, go_release)`;
- `score(request, *, data_dir=None, timeout=None)`, `check_data(data_dir=None)` and `annotations(data_dir=None)`;
- `TreegrafterError`, and treegrafter's own `TimeLimitError`.

**The order follows hmmscore's `score()`:**

1. a `ValueError` for a sequence the API never sends (decision 5);
2. `check_data()`;
3. reading the active release once;
4. the graft, with that release throughout.

**The fields:**

- **Values as EBI writes them.** `score` and `evalue` are the strings EBI's code writes, from floats it parsed: `172.6` and `5.7e-47`. `domain_score` and `domain_evalue` are `hmmsearch`'s strings, which EBI keeps: `172.4` and `6.8e-47`. The coordinates are integers.
- **`go_terms`** is a tuple, from EBI's comma-joined column. It's empty where EBI writes `-`.
- **`graft_point`** is the node's public ID (`PTN…`): the fourth value of EBI's prepared entry, which its `process_tree` reads and drops. The legacy site showed the graft point's public ID, so the engine keeps it. It's an extra field, not a changed one, so it needs no row.
- **No thread count** (decision 6), and no residue limit, which is the API's.

*Alternative:* return EBI's row as text. Rejected: the API's contract wants typed fields, with no value where EBI writes `-`.

### 2. The steps, against EBI's code

| Step | EBI: `treegrafter.sh search` and `treegrafter.py run` | Engine |
| ---- | ---------------------------------------------------- | ------ |
| Query | The caller's FASTA | `>query`, then the sequence, in the graft's folder. The name reaches EBI's output as `query_id` |
| Search | `hmmsearch -Z 65000000 -E 0.001 --domE 0.00000001 --incdomE 0.00000001 --notextw <lib>/famhmm/binHmm <fasta>`, with no `--cpu` | `core.hmmer.hmmsearch` with the same options and `--cpu 0` (decision 6), the report to a file, its status checked |
| Parse | `parsehmmsearch`, which calls `sys.exit(1)` on a report it can't read | The same function. `SystemExit` becomes `TreegrafterError` (decision 3) |
| Filter | `filter_best_domain`, then `filter_evalue_cutoff` at 1e-8 (`run -e 0.00000001`) | The same functions, in that order |
| No family | The header only | `hit` is None |
| Query alignment | `generate_fasta_for_panthr` | The same function, into the graft's folder |
| Placeable? | Nothing checks. EPA-ng fails, and the row keeps `-` | Decision 4's check, before EPA-ng |
| Placement | `_run_epang`: `epa-ng -G 0.05 -m WAG -T 1 -t <fam>.bifurcate.newick -s <fam>.AN.fasta -q <query> -w <dir>` by `sp.call`, output discarded, no time limit | `core.epang.place` with the same arguments, through `run_tool`: the time limit, `die_with_parent`, the status and `epa_result.jplace` checked, and the end of standard error in the error |
| Graft node | `process_tree(..., print_go=True)` | The same function, with the release's folder |
| Result | The TSV row | The row's fields, as decision 1 says |

**EBI's `run` and `process_matches_epang` aren't called,** since they run EPA-ng themselves. The engine repeats their dozen lines of orchestration, for one query and one family, with EPA-ng swapped. The goldens prove it matches theirs.

### 3. Containing EBI's code

- **One module, `treegrafter/ebi.py`,** imports EBI's `treegrafter` inside its functions, never at import time, so neither EBI's code nor Biopython loads until a graft or a `prepare` (spec: Loading EBI's code). The API's process imports the engine and never grafts.
- **It gives each function it calls a typed signature,** and casts at its boundary. basedpyright's strict mode can't see EBI's types, so this module alone relaxes the rules on unknown types.
- **`SystemExit` from EBI's code becomes `TreegrafterError`.** EBI writes its reason to standard error first, which the module captures with `contextlib.redirect_stderr` and puts in the error, for the log.
- **What EBI's code reads is pinned:** the library and the prepared release. Its `json` and Biopython parsers never see a request's text, only the query alignment its own function wrote.

### 4. Families that can't be placed

**Before EPA-ng, the engine compares the leaves of `<fam>.bifurcate.newick` with the rows of `<fam>.AN.fasta`.** If a leaf has no row, EPA-ng would abort with "Bad tree/ref msa combination". So the engine:

- returns EBI's family-only row: the scores and coordinates, with no node, graft point, GO terms or protein class;
- logs a warning naming the family and the missing leaves.

**The spike found ten such families:** PTHR11034, PTHR11134, PTHR11387, PTHR11489, PTHR11824, PTHR13104, PTHR23404, PTHR23411, PTHR43511 and PTHR46115.

- In each, one leaf has no row in the alignment, and no branch length in the bifurcating tree. In PTHR11034, for example, that's AN186, a dog protein.
- The check costs a few milliseconds, even for the largest family. EBI's code reads the alignment anyway, for its width.

*Alternatives:*

- **Parse EPA-ng's message.** Rejected: it ties the engine to EPA-ng's wording.
- **List the ten families in the manifest.** Rejected: that's a second source of truth to keep in step with the library. The check derives the list from the data.
- **Fail the graft.** Rejected: the family assignment is still right, and EBI's code returns it.

### 5. Refused characters

The engine takes upper-case letters, `.`, `_` and `*`: hmmscore's set without `~`.

- **`~`:** EPA-ng aborts with "Set tip states during placement failed!" when HMMER aligns a `~` to a match column. In an insert column, it never reaches EPA-ng. Refusing it gives one answer, wherever HMMER aligns it.
- **What the spike found:** `*`, `.` and `X` place, and HMMER turns `.` and `_` into gaps. APOE with `.`, `_`, `~` and `*` inside still grafted to AN163, because the `~` and `*` fell in insert columns, but at an E-value of 4.5e-35 instead of 6.8e-47.
- **`-`:** hmmscore's rules already refuse it (row 12), and treegrafter refuses it too, for one rule across the sequence forms.
- **Proposed row 15** (proposal, Parity). The API's matching `422` comes with `add-treegrafter-job`.

*Alternative:* turn `~` into `X` in the query alignment. Rejected: it changes what EBI's function wrote.

### 6. One thread

`hmmsearch --cpu 0` and EPA-ng `-T 1`, and `score()` takes no count. The spike measured this on an M1 Pro, under Docker Desktop, one job at a time:

| Query | `hmmsearch --cpu 0` | `--cpu 4` | `hmmscan --cpu 4` |
| ----- | ------------------: | --------: | ----------------: |
| APOE, 317 residues | 9.8 s | 14.2 s | 1.4 s |
| DYNC1H1, 4,646 residues | 45.5 s | 48.5 s | 12.9 s |
| Titin's first 10,000 residues | 64.0 s | 68.7 s | 16.0 s |

- **`hmmsearch` splits target sequences among its threads,** and a graft has one. Its reports were byte-identical at both counts. They were also identical with the pressed `binHmm.h3m` in place of the text file, which was no faster.
- **EPA-ng on actin's family:** 10.95 s at `-T 1`, and 11.92 s at `-T 4`.

*Alternative:* a two-stage search, `hmmscan --cpu 4` on the pressed files to pick the families, then EBI's `hmmsearch` on those alone. In the spike, `hmmscan` gave the same best family, score and E-value. Held back: it adds a step EBI doesn't have, for speed the limits don't need yet. It's the first lever if the server is slow.

### 7. The time limit

There's one deadline, from the start of `score()`, as in hmmscore's.

- **The tools:** `hmmsearch` gets the deadline, then EPA-ng gets what's left. `run_tool`'s timeout kills a tool that runs past it, and `TimeLimitError` follows.
- **EBI's in-process steps can't be stopped:** the parsing and `process_tree`. The deadline is checked after each one. They took up to about 20 s in the spike, on CFTR's family. There, the graft node sits high, and `process_tree` asks Biopython for the common ancestor of every leaf below it.
- **The API sets the limit,** with hmmscore's values (`add-treegrafter-job`). In the spike, every query took at most about a third of it: CFTR's 68 s against 209 s.

### 8. The dependency

- **Upstream first.** A pull request to `ebi-pf-team/treegrafter` adds a `pyproject.toml`:
  - one module, `treegrafter.py`;
  - `biopython>=1.86` as its dependency;
  - a `treegrafter` console script for `main`;
  - the Apache-2.0 licence.

  Nothing else changes, so `treegrafter.py` keeps its sha256.
- **The pin is a commit archive:** `treegrafter @ https://github.com/ebi-pf-team/treegrafter/archive/<commit>.tar.gz` in `engine/pyproject.toml`, with its sha256 in `uv.lock`.
  - The images need no `git`, which a git dependency's `uv sync` would. Their slim base has none.
  - Until EBI merges, `<commit>` is the pull request's head commit, on its fork. After, it's EBI's merge commit.
- **Biopython 1.88 and NumPy come through the lock.** Biopython 1.88 has CPython 3.13 wheels for amd64 and arm64. The spike installed it with NumPy 2.5.5 in the engine image: about 98 MB.
- **The API's lock gains them,** since the API takes the engine as a path dependency. The API's process doesn't load them (decision 3).
- **Engine condition 5 holds:** the archive is the pinned commit's tree. It also answers tech-stack's packaging question: not PyPI, a pinned commit, and in-process functions, with EPA-ng run by the engine.

*Alternatives:*

- **A git dependency**, `git+https://…@<commit>`: it needs `git` in every stage that runs `uv sync`.
- **Copying `treegrafter.py` into the engine:** it needs a team decision (CLAUDE.md), and drifts from upstream.
- **Downloading the script in the Dockerfile,** as `refmap-reference-script` does: then the engine's tests can't import it outside the image.

### 9. The data

The layout is in the `treegrafter-data` spec.

- **The library tarball** is `PANTHER19.0_data_trees_hmms_only.tar.gz`, 8.2 GB unpacked.
  - The fetch keeps `famhmm/binHmm` (3.40 GB) and three tree files per family (0.98 GB).
  - It skips the pressed files (3.6 GB), the `.tree` files (0.21 GB), the PAINT README and `tmp/`.
  - EBI's README downloads `PANTHER19.0_data.tar.gz` instead, which adds an older annotation file the engine doesn't use.
- **It reuses `core/`'s streaming fetch,** as hmmscore's does, with `library.sha256` (47,050 lines) in the role of `books.sha256`.
- **Annotation releases are pinned separately, by date:** URL, size, sha256, and the GO release from line 2 of the release's README.
  - The URLs are under `paint/19.0/<date>/`.
  - Not `pango/`: the library's README lists it first, but it holds a third, older file.
- **`current` is resolved by sha256.** `paint/current/`'s file has the same ETag and sha256 as the dated release's, 2026-08-28 today. The server has no other marker of which release `current` is.
- **The pinned releases are 2026-08-28,** and each older 19.0 release whose file is in the TreeGrafter format and covers every tree node, checked when pinning. In the spike, 2026-01-05 read as three columns. Its 1,090 extra lines are nodes no tree has, which EBI's code never looks up.
- **Preparing a release:**
  1. EBI's `prepare` writes into a temporary folder under `annotations/`. It took 45 s and 1.4 GB in the spike.
  2. The node check runs: all 3,564,945 nodes had an entry for 2026-08-28.
  3. The prepared files' sha256 list is checked against the pin.
  4. The folder is renamed into place.
- **The active release** is the date in `annotations/active`, replaced atomically: a temporary file, then `os.replace`.
- **`check_data`** reads only names: `famhmm/binHmm`, `Tree_MSF/`, `annotations/active` and the folder it names.
- **The data root is `treegrafter/19/`,** per service, as `hmmscore/19/` and `refmap/19/` are. Tech-stack's data table names `/data/panther/<version>/` for treegrafter, so this change updates that row to match the others.

### 10. The fixture and the goldens

**The fixture, `engine/tests/fixtures/treegrafter/`,** holds three families, about 0.9 MB in all:

| Family | Leaves | Why |
| ------ | -----: | --- |
| PTHR18976 | 123 | APOE's: one confident placement |
| PTHR11442 | 231 | The globins: five to seven placements |
| PTHR11034 | 295 | One of the ten that can't be placed |

- **What it holds:** the three HMMs in `famhmm/binHmm`, their three tree files each, and their lines of release 2026-08-28's annotation file, which the tests prepare with EBI's `prepare`.
- **`data fixture` cuts it,** and its README records each file's source and sha256.
- **With `-Z` fixed, E-values don't depend on how many HMMs the file holds.** So a case gets the full library's numbers whenever its best family is one of the three.

**The cases,** in `engine/tests/golden/treegrafter/cases.json` and `inputs/`:

| Case | Why |
| ---- | --- |
| `apoe` | The site's example: one placement |
| `hbb`, `hba` | Several placements |
| `pthr11034` | A family that can't be placed |
| `apoe-hbb` | Two families: EBI's code keeps the higher score |
| `apoe-peptide30` | Over the 1e-8 cutoff: no hit |
| `random300` | Nothing reported: no hit |
| `apoe-stop`, `apoe-dot`, `apoe-underscore`, `apoe-star` | The characters the engine takes |
| `apoe-uncommon` | `B`, `J`, `O`, `U`, `X` and `Z`: EBI's code turns `U` and `O` into `X` |

- **The reference is EBI's command line at the pinned commit, in the engine image.** `hmmsearch` runs with `treegrafter.sh`'s flags, then EBI's console script from the upstream `pyproject.toml`. No reference image is needed, since EBI's code and the tools are already in the engine image.
- **Each case keeps `result.tsv`,** EBI's `--print-go` output. The `hmmsearch` report isn't kept, since it ends with CPU times (port-hmmscore's lesson).
- **The check** maps each row to a hit: `-` to no value, and the GO column split on `,`.
- **Architectures:** amd64 is the target, as for hmmscore. EPA-ng's likelihoods may differ in their last digits on arm64, which can move a near-tie. A case whose arm64 result differs gets an arm64 copy, listed in the README.
- **EBI's published image, once:** the cases run in `interpro/treegrafter`, with HMMER 3.3.1 and EPA-ng 0.3.7, pinned by digest. If its rows equal the goldens, golden-setup says so. If not, a row is proposed.

### 11. The full-library check and the survey doc

- **On a machine with the full library and release 2026-08-28:** `parity reference`, then `parity check`, for the cases, and for the spike's 33 queries as a second set, `full/`.
- **The spike's findings go into `docs/parity/treegrafter-library-survey.md`:**
  - the library's checks: HMM length equals alignment width in every family, every node is annotated, and ten families can't be placed;
  - the annotation releases;
  - the timings;
  - the comparison with InterPro 111.0 and PANTHER's own classification.

  The spike's scratch scripts aren't committed: the commands replace them.

### 12. `core/`

- **`core/hmmer.py`'s `hmmsearch`** takes `options: Sequence[str] = ()`, passed before the model and the query. hmmscore's calls don't change.
- **A new `core/epang.py`:** `place(tree, msa, query, outdir, *, threads=1, timeout, cwd=None)`, over `run_tool` with `die_with_parent=True` (the engine-core delta). It returns the finished process, as the HMMER runners do.

## Risks / Trade-offs

- **[EBI doesn't merge the `pyproject.toml`]** → The fork commit's pin works the same way. Copying the module in is a team decision (proposal, Open Questions).
- **[GitHub regenerates a commit archive, and its sha256 changes]** → `uv sync --locked` fails loudly. Then switch to the git form, and install `git` in the build stages.
- **[Biopython and NumPy add about 100 MB to both images, and CI's licence check may reject them]** → Task 2.3 runs the dependency review.
  - Biopython's licence is its own agreement or BSD-3-Clause.
  - NumPy's wheels bundle code under further licences.
  - An entry in the allow-list, with a comment, is the fix the review already uses for two packages.
- **[A near-tie moves between architectures or versions]** → amd64 is the target, with arm64 copies. The fixture's multi-placement cases are the globins', whose best placement weighs 17% to 27%.
- **[EPA-ng peaks at 2.3 GB on the largest tree]** → `add-treegrafter-job` sets the running cap, measured on the server.
- **[EBI's in-process steps can't be stopped]** → They took up to about 20 s in the spike, and the deadline is checked after them.
- **[`current` moves monthly, and fetching it fails until the release is pinned]** → That's deliberate. The message names the file's sha256 and its GO release, and a pin-bump pull request adds it (proposal, Open Questions).
- **[A subfamily at the root]** → The engine reports what EBI's code reports. Whether that's intended is the proposal's first open question.

## Migration Plan

This is additive: nothing calls `score()` until `add-treegrafter-job` does. Rollback is a revert. The wiring then:

- adds the job and the form, and the API's `422` for `~` and `-`, citing row 15;
- calls `score()` with hmmscore's time limit, and sets a running cap;
- adds `check_data()` to the API's startup checks, and `DATA_VERSION` with the active release to its versions;
- shows GO term names, and fetches the data on the server.

## Open Questions

- **Which older releases pass the pinning checks:** settled when pinning (task 3.4). It doesn't change the approach.
- **Showing placement confidence:** EPA-ng's best placement weight would mark a near-tie such as actin's (3%). It isn't in EBI's output, and can be added later without changing this design.
