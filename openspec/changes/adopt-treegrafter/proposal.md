# Proposal

**Area:** cross-cutting. The code is in `engine/`. Outside it, the change refreshes `api/uv.lock` for the engine's new dependencies, may extend CI's licence allow-list, and edits docs under `docs/parity/`, `docs/design/` and `docs/testing/`. The API's code and the frontend don't change: `add-treegrafter-job` wires this in later.

**Depends on:**

- **`port-hmmscore` and `wire-hmmscore`** (archived): `core/hmmer.py`'s `hmmsearch`, `run_tool`'s `die_with_parent`, and hmmscore's interface, which treegrafter's mirrors, its own timeout error included.
- **A pull request to `ebi-pf-team/treegrafter` that adds a `pyproject.toml`** (tasks.md, group 0), so the engine can depend on EBI's code pinned by commit. Until EBI merges it, the pin is the pull request's commit (design.md, decision 8).

## Why

The fourth service has no code yet. The team adopts EBI's Python `treegrafter` instead of porting the Perl, and the science owner agreed to that divergence, row 1, on 2026-11-18. A spike on 2026-11-24 ran EBI's code unchanged in the engine image, on the full PANTHER 19 library:

- it agreed with InterPro or PANTHER's own classification for 22 of 24 proteins, and the other two are explained;
- every query took at most about a third of the time limits hmmscore uses.

What's missing is the engine around it: the dependency, the data, the adapter and the goldens.

## What Changes

- **EBI's `treegrafter` becomes a dependency,** pinned by commit, with Biopython 1.88 and NumPy through the lock. They are the engine's first runtime dependencies, which `engine/README.md` says need a proposal. They load only when a protein is grafted.
- **Grafting one protein,** as EBI's `treegrafter.sh search` does:
  - `hmmsearch -Z 65000000 -E 0.001 --domE 1e-8 --incdomE 1e-8 --notextw` against `famhmm/binHmm`, through `core`;
  - EBI's own `parsehmmsearch`, `filter_best_domain`, `filter_evalue_cutoff` at 1e-8, `generate_fasta_for_panthr` and `process_tree`;
  - EPA-ng with EBI's arguments, run by the engine through `run_tool`: with a time limit, its exit status checked and its errors logged. EBI's code ran it with no limit and discarded its errors.

  The result is the best family's graft or no hit: the PANTHER ID (the subfamily, else the family), the graft node, the GO terms and protein class from the active annotation release, and the scores and coordinates. The interface is hmmscore's: `score()`, `check_data()` and `DATA_VERSION`, plus the active annotation release.
- **Single-threaded tools:** `hmmsearch --cpu 0` and EPA-ng `-T 1`. In the spike, more threads slowed `hmmsearch` and didn't speed up EPA-ng for one query, so `score()` takes no thread count.
- **Ten families can't be placed:** each tree has a leaf with no alignment row, and EPA-ng refuses it. The engine checks for that before EPA-ng, and returns the family alone, as EBI's code does, with a warning in the log.
- **Failures are errors:** a tool that fails, or EBI's parser exiting, fails the graft. EBI's code printed the family alone, or exited.
- **Refused sequences:** what hmmscore's engine refuses, plus `~`. EPA-ng aborts on `~` when HMMER aligns it to a match column. That's proposed row 15.
- **The data,** under `treegrafter/19/`:
  - **the library,** `PANTHER19.0_data_trees_hmms_only.tar.gz` (3.07 GB), pinned by sha256. The fetch keeps `famhmm/binHmm` and three of each family's four tree files, about 4.4 GB;
  - **the PAINT annotation releases,** pinned by date and sha256, each with the GO release its README names. `data fetch` takes `current`, which it resolves to the pinned release it is, or a date. It runs EBI's `prepare`, checks that every tree node has an entry, then makes that release the one grafting reads;
  - **`data verify` and `data manifest`,** as hmmscore's.
- **A committed fixture** of three real families, under 1 MB: APOE's, the globins', and one that can't be placed. Goldens from EBI's own CLI at the pinned commit run on it in CI.
- **The commands:** `treegrafter score`, `treegrafter data fetch|verify|manifest|fixture`, and `treegrafter parity reference|check`.
- **A full-library check:** the goldens' cases and the spike's 33 queries, against EBI's CLI on the full library. The spike's findings, with its comparison against InterPro and PANTHER, go into a new `docs/parity/treegrafter-library-survey.md`.
- **Docs:**
  - row 1's approval;
  - the answers to tech-stack's two treegrafter questions, and to api-stack's Python 3.13 question;
  - the engine README's dependencies and services.
- **Not in this change:** the job, the form, GO term names, the residue and time limits and the running cap. Those come in `add-treegrafter-job`.

## Capabilities

### New Capabilities

- `treegrafter-engine`: grafting one protein as EBI's pinned `treegrafter` does, with the data check and versions, the command, and the parity checks against EBI's CLI.
- `treegrafter-data`: the pinned library and annotation releases, fetching, preparing and verifying them, and the test fixture.

### Modified Capabilities

- `engine-core`: EPA-ng joins the search tools that don't outlive the process that started them.

## Parity

The reference is EBI's `treegrafter` at the pinned commit (CLAUDE.md). The goldens are its own CLI's output on the fixture, so a dropped flag, filters in the wrong order or the wrong release fail them.

- **Row 1, the whole implementation:** approved by the science owner on 2026-11-18. This change records it.
- **Row 15, proposed: the sequences treegrafter refuses,** `~` and `-`. EBI's code grafts a sequence with `-`, a gap to HMMER, and one with `~` in an insert column. When `~` lands in a match column, it returns the family alone. The engine developer approves the row before the code ships.
- **Not rows,** since they don't change a correct request's answer, as for `HMMSCORE-11`:
  - a failing tool, or EBI's parser exiting, fails the graft;
  - `--cpu 0` and `-T 1`: the spike found byte-identical reports at other counts;
  - the ten families that can't be placed get what EBI's code gives them, the family alone.
- **Tool versions:** the engine has HMMER 3.4 and EPA-ng 0.3.8, where EBI's Dockerfile builds 3.3.1 and 0.3.7. The spike's E-values equal InterPro's. Group 7 runs the fixture's cases once in EBI's published image, and proposes a row if anything differs.

## Impact

- **Engine:**
  - `treegrafter/` gains the adapter, the data code, the fixture, the parity runs and the commands;
  - `core/hmmer.py`'s `hmmsearch` takes extra options, and a new `core/epang.py` runs EPA-ng;
  - `pyproject.toml` and `uv.lock` gain the dependency;
  - tests and goldens go under `engine/tests/`.
- **Images:** the engine and API images grow by about 100 MB, for Biopython and NumPy. They need no `git`, since the pin is a commit archive (design.md, decision 8).
- **API:** only `api/uv.lock`, for the path dependency's new packages.
- **CI:** no new job, since the fixture is committed. The licence allow-list may need entries for Biopython and NumPy (task 2.3).
- **Data on the hosting server:** about 4.4 GB, plus 320 MB per prepared release, once `add-treegrafter-job` needs it.
- **Unchanged:** csnp, refmap and hmmscore.

## Open Questions

- **Subfamilies at the root:** 13,550 of the 15,683 family roots carry a subfamily in the annotation file (actin's AN0 is SF274). So EBI's code names a subfamily for almost any graft, even one at the family root. Whether that's intended needs team verification: the science owner, or whoever builds the PAINT TreeGrafter file.
- **InterPro's family-only answers:** InterPro shows no subfamily for 5 of the spike's 24 proteins, and 4 of our answers for them match PANTHER's own classification. InterPro's reason needs team verification. It doesn't block this change.
- **The ten families that can't be placed:** whether the next library build fixes them, and who does it, needs team verification.
- **Monthly releases:** this change pins each release, so a new one ships as a pin-bump pull request, and `current` fails to fetch until then. The alternative is to record an unpinned release's checksum at fetch time. The team decides.
- **If EBI doesn't merge the `pyproject.toml`:** either the pin stays on the pull request's commit in a fork, or the team decides to copy `treegrafter.py` into the engine. CLAUDE.md asks for a team decision before copying source.
- **The hosting server:** its timings and memory come with `add-treegrafter-job` and the deploy, as hmmscore's did (#68). EPA-ng peaked at 2.3 GB on the largest tree in the spike.
