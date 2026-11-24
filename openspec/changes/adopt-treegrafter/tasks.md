# Tasks

Work test-first: write each group's tests, see them fail, then make them pass. Paths in `engine/` are relative to `engine/src/panther_engine/` unless they start with `engine/`. The engine's checks run in the engine image (`docker compose run --rm engine`), with data in `.data/`.

Groups 1, 3.1 and 3.2 don't need EBI's code, so they can start while group 0 waits on EBI.

## 0. Upstream: a `pyproject.toml` for EBI's `treegrafter`

- [ ] 0.1 Draft a pull request against `ebi-pf-team/treegrafter`, from the engine developer's fork, that adds only a `pyproject.toml` (design.md, decision 8):
  - the module `treegrafter.py`;
  - `biopython>=1.86`, as `requirements.txt` asks;
  - a `treegrafter` console script for `main`;
  - the Apache-2.0 licence.

  Show the pull request's text to the engine developer before opening it, since it's public. Verify on the branch:
  - in a clean Python 3.13 environment, installing the branch's commit archive gives an importable `treegrafter` and a working `treegrafter --help`;
  - `treegrafter.py`'s sha256 is still `9741da411ef4ae7c2cf5bf80b133391ee45b78149bc8aa0e2c9143ddd55de44c`;
  - EBI's own `tests/` pass.

  Record the pull request and its head commit in Notes.
- [ ] 0.2 Before the final check, if EBI has merged 0.1, move the pin (task 2.1) to EBI's merge commit and check that `treegrafter.py` has the same sha256. If EBI hasn't merged, record in Notes that the pin stays on 0.1's head commit, with the engine developer's agreement (proposal, Open Questions). Verify the pin in `engine/pyproject.toml` is the commit Notes names.

## 1. Shared Pieces and Docs

- [ ] 1.1 In `docs/parity/divergences.md`:
  - **row 1:** "Approved by" is "Science owner", and "Date" is 2026-11-18;
  - **add row 15,** treegrafter's refused sequences, `~` and `-` (design.md, decision 5).
    - Its reference output: EBI's code grafts `-` as a gap, and `~` in an insert column, and returns the family alone, with node `-`, when `~` lands in a match column.
    - Its Python output: refused, with the engine's `ValueError`. The API's `422` comes with `add-treegrafter-job`.
    - Its why: EPA-ng aborts on `~`, and `-` follows hmmscore's rule (row 12).

    Leave "Approved by" empty until the engine developer approves this change's pull request;
  - **in the "Not listed" paragraph,** add treegrafter's: a failing tool, or EBI's parser exiting, fails the graft, where EBI's code printed the family alone or exited.

  Verify `npx markdownlint-cli2` passes.
- [ ] 1.2 Answer the open questions in place, as hmmscore's were answered:
  - **`docs/design/tech-stack.md`:**
    - the treegrafter section's line on the website's CGI, and Open Questions' "Website CGI": answered. The site moves to the JSON API, and EBI's `--print-go` output has every field the site showed: the graft node, the subfamily, the GO terms and the protein class;
    - Open Questions' "Packaging", and Engine condition 5's PyPI check: answered. PyPI has no `treegrafter`; the pin is a commit archive; the engine calls EBI's functions in-process and runs EPA-ng itself (design.md, decision 8);
    - the data table's treegrafter row: `/data/treegrafter/<version>/`, with the library and the prepared releases (design.md, decision 9);
    - "Who builds the data", for treegrafter: the PANTHER team publishes the library and the releases on `data.pantherdb.org`, and the engine's fetch runs `prepare`;
    - the Review table's science owner row: the TreeGrafter divergence was approved on 2026-11-18.
  - **`docs/design/api-stack.md`'s Python 3.13 question:** answered. Biopython 1.88 has CPython 3.13 wheels for both architectures, and EBI's code ran in the engine image on 2026-11-24.
  - **`engine/README.md`:** the runtime dependencies (EBI's `treegrafter` by commit, with Biopython 1.88 and NumPy, for `treegrafter` only, and loaded only when grafting); and the services table and line 5, brought up to date for all four services.

  Verify `npx markdownlint-cli2` passes.
- [ ] 1.3 Give `core/hmmer.py`'s `hmmsearch` its `options` (design.md, decision 12). Extend `engine/tests/test_core_hmmer.py` with `make_tool` fakes:
  - the options reach the tool before the model and the query, each as one argument;
  - without options, the arguments are what hmmscore's calls send today.

  Verify `pytest engine/tests/test_core_hmmer.py` passes.
- [ ] 1.4 Add `core/epang.py` (design.md, decision 12), with `die_with_parent=True` (the engine-core delta). Write `engine/tests/test_core_epang.py` first:
  - with `make_tool` fakes: EBI's arguments as a list, with no shell; a non-zero status returned, not raised; `subprocess.TimeoutExpired` passed through;
  - on Linux, EPA-ng is killed when its parent is, extending `test_process.py`'s die-with-parent test;
  - with `tools("epa-ng")`: the real EPA-ng places a query on a four-leaf tree and alignment that the test writes itself.

  Verify the tests pass natively and in the image.

## 2. The Dependency

- [ ] 2.1 In `engine/pyproject.toml`, add `treegrafter @ https://github.com/<owner>/treegrafter/archive/<commit>.tar.gz`, with 0.1's head commit, and run `uv lock`. Refresh `api/uv.lock`, since the API takes the engine as a path dependency. Verify:
  - `uv sync --locked` passes in `engine/` and `api/`;
  - `engine/uv.lock` records the archive's sha256, Biopython 1.88 and NumPy;
  - in `api/`, only `uv.lock` changed.
- [ ] 2.2 Build the `engine` and `api` images on both architectures. Verify:
  - neither image has `git`;
  - in both, `python -c "import treegrafter, Bio; print(Bio.__version__)"` prints `1.88`;
  - each image's size before and after is in Notes. About 100 MB more is expected.
- [ ] 2.3 Open this change's pull request early enough to see CI's `dependency-review` on the new packages. If it rejects Biopython or NumPy for a licence it misreads, add them to `allow-dependencies-licenses` in `.github/workflows/ci.yml`, each with a comment like the two already there:
  - Biopython's licence is its own agreement, or BSD-3-Clause;
  - NumPy's wheels bundle code under further licences.

  Verify the `dependency-review` job passes.
- [ ] 2.4 Add `treegrafter/ebi.py` (design.md, decision 3): typed wrappers for the EBI functions that decision 2 names, imported inside the functions. Write the tests first:
  - a fresh Python process that imports `panther_engine.treegrafter` has neither `treegrafter` nor `Bio` in `sys.modules` (spec: Loading EBI's code);
  - the installed `treegrafter.py` has the pinned sha256 (spec: The adopted code);
  - a hand-written report that `parsehmmsearch` exits on gives `TreegrafterError` with EBI's message, and the test process doesn't exit.

  Verify the tests pass, and `ruff` and `basedpyright` are clean.

## 3. The Data

- [ ] 3.1 Add `treegrafter/data.py` and `treegrafter/data.json` with the library's pin (design.md, decision 9; spec: The pinned library, Data layout, Pinning the library). Add `panther-engine treegrafter data manifest`, on `core/`'s streaming tarball reader, and mark `data.json` `linguist-generated` in `.gitattributes`, as refmap's is. Write `engine/tests/test_treegrafter_data.py` first, with small synthetic tarballs:
  - the layout's members are kept, and `library.sha256` lists them, sorted;
  - the pressed files, `.tree` files, the PAINT README and `tmp/` are skipped;
  - an unexpected member, a member outside the prefix, and a family missing one of its three tree files are each refused, and named;
  - the same tarball twice gives byte-identical manifests.

  Verify they pass.
- [ ] 3.2 Add the library's fetch (spec: Fetching the library): from the URL or `--library FILE`, with the size, sha256 and each kept file checked before anything moves into place, and no download when the folder matches. Test it with the synthetic tarballs: a fresh fetch, one already fetched, a wrong checksum with both named, an unsafe member, and a local copy without the network. Verify they pass.
- [ ] 3.3 Add the annotation releases (design.md, decision 9; spec: Pinned annotation releases, Fetching a release by date, Preparing a release, The active release):
  - the release pins in `data.json`, written by `data manifest --release <date> FILE`, with the GO release from the release's README;
  - `--annotations <date>`, and `--annotation-file FILE` for a local copy;
  - EBI's `prepare` into a temporary folder, the node check, the prepared files' sha256 list checked against the pin, then the rename;
  - `annotations/active`, replaced with `os.replace`.

  Test it with a hand-made three-family library and annotation file:
  - a pinned date ends prepared and active;
  - a wrong checksum is refused, with both checksums named;
  - an unpinned date is refused, listing the pinned dates;
  - a release missing a node is refused, naming it;
  - another release becomes active, with both kept;
  - fetching a prepared release again makes it active without a download.

  Verify they pass.
- [ ] 3.4 Pin the real data:
  1. run `data manifest` on the library's tarball;
  2. pin and fetch release 2026-08-28;
  3. check each older 19.0 release, and pin those in the TreeGrafter format that cover every node.

  Record which releases passed, and why the others didn't, in Notes and the survey doc (7.7). Verify the library's pin is `789c31d7f1e051ae3dfdd4c6c41e97a970395cc490cab52da850d1b5abfd5e4f` at 3,073,460,727 bytes, and 2026-08-28's is `03ad195b42a48ff2fb0caadd337bf2c98464382855618c1f14fe2869b3d6bf3f` at 23,980,614 bytes, with GO release 2026-08-05.
- [ ] 3.5 Add `current` (spec: Fetching the current release). The fetch downloads `paint/current/`'s file and README, resolves the file by sha256, and refuses one no release pins, naming its sha256 and the README's GO release. Test it against a local HTTP server: a pinned `current` resolves and says which date it is; one that has moved on writes nothing and names both. Verify the tests pass, and the real fetch says that `current` is 2026-08-28.
- [ ] 3.6 Add `data verify` and `check_data()` (spec: Verifying the data, Data check). Tests:
  - a changed alignment byte, and a changed prepared file, are each listed, with a non-zero exit;
  - `check_data()` names a missing `famhmm/binHmm`, a missing `annotations/active`, and a missing release folder, without reading any file's contents.

  Verify they pass, and `data verify` on the real fetch reports nothing.
- [ ] 3.7 In `docs/testing/engine.md`, add "The treegrafter Data":
  - the library and the releases;
  - fetching `current` or a date, and going back to a prepared release;
  - `data verify`;
  - the disk it takes: about 4.4 GB, plus 320 MB per prepared release.

  Verify `npx markdownlint-cli2` passes, and the documented commands run as written.

## 4. The Fixture

- [ ] 4.1 Add `panther-engine treegrafter data fixture` (spec: Building the fixture; design.md, decision 10). Test it on 3.3's hand-made library: the same input gives the same bytes. Verify it passes.
- [ ] 4.2 Cut the fixture from the real fetch: PTHR18976, PTHR11442 and PTHR11034, with release 2026-08-28's lines.
  - Commit it under `engine/tests/fixtures/treegrafter/`, with a README giving each file's source and sha256.
  - Add `engine/tests/fixtures/treegrafter/** -text` to `.gitattributes`.
  - Add a test that prepares it into a temporary data folder, where `check_data()` passes (spec: The fixture).

  Verify that the fixture is under 1 MB, that rebuilding it is byte-identical, and that the test passes.

## 5. Grafting

- [ ] 5.1 Write `engine/tests/test_treegrafter_scoring.py` from the spec's scenarios, before the code. Use saved `hmmsearch` reports and `make_tool` fakes. Cover:
  - no family reported;
  - the best family and its cutoff, from hand-written reports: two families, and one over 1e-8;
  - the fields mapped from EBI's row: `-` to no value, the GO terms split, and the graft point from the prepared entry;
  - a family that can't be placed: EPA-ng not run, and a warning naming the family;
  - refused sequences, with no tool run: `~`, `-`, lower case, and no letter. A sequence of 10,001 letters is accepted;
  - the time limit, in `hmmsearch`, and in EPA-ng with what's left;
  - tool failures: either tool's non-zero exit, no `epa_result.jplace`, and EBI's parser exiting;
  - one release read throughout a graft, even when `annotations/active` changes during it.

  Verify they fail for want of the code.
- [ ] 5.2 Add `treegrafter/scoring.py` (design.md, decisions 1, 2, 4, 5 and 7), and export the interface from `treegrafter/__init__.py`. Make 5.1 pass. Verify also:
  - `TimeLimitError` and `TreegrafterError` pickle with their messages;
  - `DATA_VERSION` is `"19"` with `PANTHER_DATA_DIR` unset;
  - `annotations()` gives the active release and its GO release.
- [ ] 5.3 Add end-to-end tests with `tools("hmmsearch", "epa-ng")` on the prepared fixture:
  - APOE gives `PTHR18976:SF2`, `AN163`, `PC00052`, and the spec's scores and coordinates;
  - human HBB gets several placements;
  - the PTHR11034 member gives the family alone;
  - two proteins grafted at once each get their result alone;
  - APOE, then HBB, then APOE, gives identical APOE results;
  - a time limit reached in a worker process reaches the caller as `TimeLimitError`.

  Verify they pass in the engine image.

## 6. The Command Line

- [ ] 6.1 Add `panther-engine treegrafter score [FILE|-] [--timeout S] [--json] [--usage]` in `treegrafter/cli.py`, as hmmscore's is. `--usage` adds the wall time and the tools' peak memory, on standard error. Extend `engine/tests/test_treegrafter_cli.py` with the spec's three scenarios. Verify they pass.
- [ ] 6.2 In `docs/testing/engine.md`, document `treegrafter score`. Verify `npx markdownlint-cli2` passes, and the documented command runs as written.

## 7. The Goldens and the Full Library

- [ ] 7.1 Write `engine/tests/golden/treegrafter/cases.json` and `inputs/` (design.md, decision 10), with each input's source and sha256 in the goldens' README. `apoe-hbb` is APOE followed by HBB, and `random300` comes from a recorded seed. Verify that `cases.json` lists every input file, and that every input holds only what the engine takes.
- [ ] 7.2 Add `panther-engine treegrafter parity reference` (spec: Reference run). For each case, it runs `hmmsearch` with `treegrafter.sh`'s flags, then EBI's console script, `run -e 0.00000001 --print-go`, one case at a time into a temporary folder, then moves the output into place. Unit-test the arguments without the tools. Run it on the fixture in the image, on amd64, and commit `parity/fixture/`. Verify the APOE row names `PTHR18976:SF2` and `AN163`, and the PTHR11034 row has `-` for its node.
- [ ] 7.3 Add `panther-engine treegrafter parity check` and `engine/tests/test_treegrafter_parity.py` (spec: Parity with the reference, Parity run):
  - every fixture case equals its golden;
  - a hand-changed graft node fails, naming the case;
  - a case with no output is named.

  Run them on both `engine-image` legs. Add an arm64 copy only for a case whose result differs there, and list it in the README. Verify CI's `engine-image` legs pass.
- [ ] 7.4 Run the cases once in EBI's published `interpro/treegrafter` image, pinned by digest, on amd64, with the fixture, through its `treegrafter.sh search`. Compare its rows with the goldens. Verify: if they're equal, golden-setup says so, with the digest. If not, the differences are listed, and a row proposed, or Notes say why none is needed.
- [ ] 7.5 In `docs/parity/golden-setup.md`, add a `treegrafter` section: the reference, which is EBI's command line at the pinned commit, in the engine image; regenerating the goldens; 7.4's cross-check; and the full-library run. In `docs/parity/inputs.md`, add a `treegrafter` section: each case, and why it's there. Verify `npx markdownlint-cli2` passes.
- [ ] 7.6 On a machine with the full library and release 2026-08-28, and `data verify` clean, run `parity reference` and `parity check` for the cases, and for the spike's 33 queries as a second set, `full/`. Commit `full/`. Verify `parity check` exits 0 for both sets, and record the machine, the date and the times in `inputs.md`.
- [ ] 7.7 Add `docs/parity/treegrafter-library-survey.md` (design.md, decision 11), from Notes' record of the spike and from 3.4 and 7.6:
  - the library's checks, and the ten families that can't be placed;
  - the annotation releases, and the subfamilies at the root;
  - the timings;
  - the comparison with InterPro 111.0 and PANTHER's own classification.

  Add its row to `docs/parity/README.md`'s table. Verify `npx markdownlint-cli2` passes, and every number in it traces to Notes, 3.4 or 7.6.

## 8. Final Check

- [ ] 8.1 Run the engine's checks in the image, with tools and data required: `ruff check`, `ruff format --check`, `basedpyright` and `pytest`. From the root, run `npx markdownlint-cli2`, `npx openspec validate adopt-treegrafter --strict --no-interactive` and `npx openspec validate --all --no-interactive`. Verify all pass, and record the results in Notes. Verify CI is green on the pull request, with both `engine-image` legs and `dependency-review`.

## Workflow follow-up

- The engine developer approves the pull request, and with it row 15. The API developer checks that `score()`'s shape suits the wiring.
- Archive this change with `/opsx:archive`. Move the lessons that last beyond it into `docs/` or `CLAUDE.md` first.
- Next, `add-treegrafter-job`:
  - the job and the form;
  - the `422` for `~` and `-`, citing row 15;
  - hmmscore's residue limit and time limit, and a running cap;
  - the startup check, and `DATA_VERSION` with the active release in the versions;
  - GO term names;
  - the data on the hosting server, and its timings and memory there.
- Ask whoever builds the library about the ten families, and the science owner about subfamilies at the root (proposal, Open Questions).

## Notes

### Next action

Start group 0: draft the `pyproject.toml` pull request for EBI, and show it to the engine developer before opening it. Meanwhile, groups 1, 3.1 and 3.2 can start.

### The spike, 2026-11-24

This record is kept here so it lasts: the spike's own files were in a scratch folder.

- **Setup:**
  - an M1 Pro, with Docker Desktop's 10 CPUs and 12.5 GB;
  - the engine image: HMMER 3.4, EPA-ng 0.3.8 and Python 3.13.18;
  - Biopython 1.88 and NumPy 2.5.5, in a throwaway environment;
  - EBI's `treegrafter.py` at `5ef350f`, run as `treegrafter.sh search` runs it, one job at a time.
- **The library:**
  - sha256 `789c31d7…`; 8.21 GB unpacked;
  - 15,683 families. Each HMM's length equals its alignment's width;
  - 3,564,945 tree nodes, 2,017,190 of them leaves, all annotated by 2026-08-28;
  - the ten families that can't be placed: PTHR11034, PTHR11134, PTHR11387, PTHR11489, PTHR11824, PTHR13104, PTHR23404, PTHR23411, PTHR43511 and PTHR46115.
- **The annotations:**
  - `current` is 2026-08-28: sha256 `03ad195b…`, 23,980,614 bytes, ETag `"16dea46-65a2436625380"`, GO release 2026-08-05;
  - `prepare` took 45 s and 1.4 GB, and wrote 320 MB;
  - 13,550 of 15,683 roots carry a subfamily. 2,235 nodes have none, 2,133 of them roots;
  - 84 nodes changed subfamily since 2026-01-05, whose file has 1,090 lines for nodes no tree has;
  - `pango/` holds another file: 23,942,358 bytes, dated 2026-03-11;
  - the 10,500 distinct GO IDs are all in the 2026-08-05 `go.obo`, and none is obsolete.
- **Against InterPro 111.0, on PANTHER 19.0:**
  - 17 of 24 proteins have the same subfamily;
  - 4 that InterPro gives only a family match PANTHER's own classification: OR1A1 SF50, MAPK1 SF584, H3.1 SF242 and GroEL SF3;
  - actin is SF575 where PANTHER says SF414: a near-tie, with 7 placements of 3% each;
  - titin's first 10,000 residues miss the region InterPro places full titin by;
  - the SARS-CoV-2 spike has no hit in either;
  - E-values equal InterPro's in all 13 cases where InterPro's isn't 0;
  - calmodulin is PTHR23048:SF0 here and in InterPro, but PTHR23050:SF531 in PANTHER's tree.
- **Times,** as `hmmsearch` plus EBI's step, with EPA-ng's share of it in brackets:

  | Query | Time |
  | ----- | ---- |
  | APOE | 10 s + 1.7 s (0.6 s) |
  | A leaf of the largest tree | 9 s + 26 s (26 s) |
  | CFTR | 20 s + 48 s (29 s) |
  | DYNC1H1 | 51 s + 4 s |
  | Titin's first 10,000 residues | 63 s + 2 s |
  | A 7,243-residue leaf | 142 s + 1 s |

  The 7,243-residue leaf passes the first filter for 5,978 HMMs.
- **Peak memory:** EPA-ng 2.3 GB, on PTHR11654; `hmmsearch` 1.26 GB, on the 7,243-residue leaf.
- **Characters:** EPA-ng places `*`, `.` and `X`, and aborts on `~`. HMMER turns `.` and `_` into gaps.

### Blockers

- **EBI's merge of 0.1.** It doesn't block: the pin on 0.1's head commit works meanwhile (0.2).

### Failed approaches

None yet.

### Lessons learned

- **From the spike:** for a one-sequence search, `hmmsearch --cpu 4` is slower than `--cpu 0`, `binHmm.h3m` is no faster than the text file, and EPA-ng's threads don't help.
- **EBI's code hides two EPA-ng aborts as a family-only row:** a tree leaf missing from its alignment, and a `~` in a match column of the query alignment.
- **`process_tree` can take about 20 s** on a big family whose graft node sits high in the tree.
- **With `-Z` fixed, a file of a few family HMMs gives the full library's E-values,** so a small fixture is enough for the goldens.
