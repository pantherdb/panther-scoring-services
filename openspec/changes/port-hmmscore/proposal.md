# Proposal

**Area:** cross-cutting. The code is in `engine/`. Outside it, the change adds a test-only stage to the root `Dockerfile`, proposes a divergence row, and edits docs under `docs/parity/`, `docs/testing/` and `docs/design/tech-stack.md`. Nothing in `api/` or `frontend/` changes. The wiring change calls this port later.

**Depends on:**

- **`add-hmmscore-survey-and-sample`** (#67, merged): the library's layout, its fetch and verify, the data sample `hmmscore-sample-1`, and the legacy readers in `hmmscore/legacy.py` and `hmmscore/library.py`. It isn't archived yet. This change adds no requirement to its `hmmscore-data`.
- **`add-hmmscore-job`** (#70 and #76, merged): the contract, and the engine interface it proposed (decision 4), which the engine developer approved on #70. Also the settings the wiring passes to the engine: the time limit and `--cpu` (decision 5).

## Why

The API answers every valid hmmscore request with a `501`, because the engine can't score yet. This change ports the legacy scoring, `scoreAlignXml.cgi` and the `pantherScore.pl` it runs, to the engine. It proves the port with golden files that the Perl makes in a reference image, so the wiring can turn hmmscore on.

## What Changes

- **Scoring one protein** against PANTHER 19's HMM library, as the CGI did:
  - `hmmscan` against `globals/binHmm`;
  - `getBestHit`'s best hit, and its 1e-3 cutoff;
  - `hmmsearch` of the hit's model file, for the alignment.

  It returns the hit's PANTHER ID, name, E-value, bit score and alignment, or no hit, in the shape `add-hmmscore-job` proposed: `DATA_VERSION`, `score()` and `check_data()`.
- **Each search runs in a folder of its own,** with argument lists. A caller can set a time limit for the whole search and a thread count (`--cpu`); once wired, both come from the API's settings. Past the limit, scoring fails with an input error asking for a shorter sequence. A tool that fails is an error, never "no hit".
- **Tied best hits** report the subfamily before its family, then the lowest PANTHER ID. That's the engine developer's rule of 2026-11-11, proposed as a divergence row.
- **The commands:**
  - `panther-engine hmmscore score` scores one protein;
  - `hmmscore parity reference` and `hmmscore parity check` make and check the goldens.
- **A reference image, `hmmscore-reference`.** It's for tests only and runs on amd64 only. It holds:
  - `pantherScoring` at `89ea0ae`, from a developer's checkout, with each script pinned by sha256;
  - Debian's Perl, with YAML::XS;
  - HMMER 3.1b2's tools, from the Bioconda image the survey measured.

  So the goldens are production's answers, from production's HMMER version.
- **Goldens on the data sample,** for the cases `hmmscore-legacy-behaviour.md` proposes and a few more. CI checks them in the existing `engine-image` legs.
- **A staging run of the same cases on the full library,** on an amd64 machine. It also times a 10,000-residue query at `--cpu 0`, to check the time limit's 720 s default.
- **Docs:**
  - the reference image, the cases and the staging run, in `golden-setup.md` and `inputs.md`;
  - the parity tests and the command, in `docs/testing/engine.md`;
  - the quirks the port found, in `hmmscore-legacy-behaviour.md`.

## Capabilities

### New Capabilities

- `hmmscore-engine`: scoring one protein against the HMM library as the legacy CGI did, with the data check and version, the commands, and the parity checks that prove the port matches the Perl.

### Modified Capabilities

None.

## Impact

- **Engine:**
  - `hmmscore/` gains the scoring, the parity runs and the commands, and `hmmscore/__init__.py` exports the interface.
  - `core/` gains thin `hmmscan` and `hmmsearch` runners over `run_tool`, as `tech-stack.md` asks, for `treegrafter` to reuse. `run_tool` can run with no time limit and with extra environment variables, and the one-protein FASTA reader of `csnp score` moves to `core/fasta.py`, for `hmmscore score` too.
  - Tests and goldens are under `engine/tests/`.
- **Docker:** two test-only stages, `hmmer-3.1b2` and `hmmscore-reference`. The `engine` and `api` images don't change, and CI doesn't build the reference.
- **CI:** no new job. The sample goldens run in the `engine-image` legs, which already fetch the sample.
- **API:** none. The wiring change removes the `501`, calls `score()` with the time limit and `--cpu`, and adds the data check and data version.
- **Parity with the reference:**
  - **Row 13, approved: tied best hits (`HMMSCORE-1`).** The reference showed one of the tied models in hash order, at random. The port reports the subfamily before its family, then the lowest PANTHER ID. The engine developer approved the row on this change's pull request, #81, on 2026-11-17.
  - **Rows 11 and 12, approved,** are the API's. The engine never receives those sequences.
  - **HMMER: no row.** On amd64, 3.4 gives 3.1b2's tables and alignments (the survey). The goldens, made with 3.1b2, check that again on every case.
  - **Not replicated, and not rows,** since they don't change a correct request's answer:
    - the shared `/tmp/temp.domtblout` (`HMMSCORE-7`);
    - the CGI's unchecked `hmmsearch`, and the alignment file it never deletes (a new `HMMSCORE-11`).

## Open Questions

- **HMMER's thread count in production:** `pantherScore.pl` passed no `--cpu`, so `hmmscan` used its default. The survey found the tables the same at every `--cpu`, so parity doesn't depend on it. Which count production used needs team verification.
- **The hosting server's values (#68):** this change reports the 10,000-residue query's time and peak memory on the full library, on amd64. The server's own measurements and its four settings come with the deploy and the wiring, with the API developer.
- **Resolved: a best hit over 1e-3 beside a lower-scoring hit under it (`HMMSCORE-5`).** The survey proposed this case "if the library has one". A search of the sample found one, now the golden case `best-over-cutoff` (design.md, decision 7). Hand-written tables test the rule too.
