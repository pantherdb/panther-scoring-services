# Proposal

**Area:** cross-cutting. The work is in `engine/`, but the change also:

- adds the hmmscore data sample to CI's engine jobs;
- records the engine developer's answers of 2026-11-09 in `CLAUDE.md` and `docs/design/tech-stack.md`;
- edits `CONTRIBUTING.md` and `docs/testing/`.

All three developers own those.

## Why

`hmmscore` is the third service to port. As with cSNP (`add-csnp-survey-and-sample`), its port can't start until two things are true:

- we know what the PANTHER 19 HMM library holds;
- developers and CI have data to test against.

The library is one tarball on `data.pantherdb.org`, `hmm_scoring/19.0/PANTHER19.0_hmmscoring.tgz`. It's 18,494,793,691 bytes compressed, far too big for a laptop or a CI runner.

A first look on 2026-11-09 listed only the start of it:

- the README, which counts 15,683 family and 128,012 subfamily HMMs;
- in `globals/`, the pressed `binHmm.h3f` (5.3 GB), `names.tab`, `binHmm.h3i` and `binHmm.h3p` (15.8 GB).

What follows, the books and whatever else is in `globals/`, hasn't been read.

The engine developer settled the source and the port's scope on 2026-11-09:

- **The data is this tarball alone.** It holds everything scoring needs.
- **Its `globals/names.tab` is in sync with the PANTHER database,** so the engine can return the names the website showed.
- **`binHmm` and the books are one release.** `binHmm` had its own folder in production only to put the big files on another volume.
- **Production most likely ran HMMER 3.1b2.** The engine pins 3.4.
- **M1 ports the website's path,** `scoreAlignXml.cgi`:
  - one sequence goes in;
  - the best hit and its alignment come out.
- **`alignOnTheFly.cgi` isn't used any more.**

This change surveys the tarball once and pins it. It adds fetching and verifying the full library, and publishes a sample for developers and CI. It also measures what the port and the server need to know.

## What Changes

- **Readers, in `panther_engine.hmmscore`:**
  - **`globals/names.tab`:** each line is `PTHRnnnnn.mag.mod` or `PTHRnnnnn.SFn.mod`, a tab, then the name. It gives the HMM ID `PTHRnnnnn` or `PTHRnnnnn:SFn`.
  - **HMMER3 text models:** the format line, `NAME`, `LENG` and each model's extent.
  - **They're strict.** A line or model of any other shape is an error that names the file and line.
  - **Beside them, `pantherScore.pl`'s own readings** (`legacy.py`):
    - `getHmmNames`'s key for a `names.tab` line;
    - `runHmmscan`'s rule from a model name to an HMM ID. It splits the name on `.`, and adds `:SFn` when the second part starts with `SF` and digits.
  - **They're the first piece of the port.**
- **A library survey, `panther-engine hmmscore survey`.** It makes one streamed pass over the tarball, and gets the tarball's sha256 from the same pass. It never unpacks to disk. It reports:
  - **every member:** its kind and size, any unexpected member, and the unpacked size of what scoring reads;
  - **`names.tab`:**
    - its families and subfamilies;
    - every ID with its books file, and every books file with its line;
    - any line `getHmmNames` keys differently from the strict reader;
  - **the books' models:**
    - each reads as one model;
    - the `HMMER3/f` format lines;
    - the shapes of model names;
    - each model whose legacy ID isn't its own path's ID.

    A first look at PANTHER 19's files on 2026-11-09 found 5,450 families with one subfamily. In each of the five checked, that subfamily's file is a byte-for-byte copy of the family's model, named `PTHRnnnnn.orig.30.pir`. So the legacy rule reports such a hit as the family.
  - **`binHmm`:**
    - its model count and duplicate names;
    - every model has the books file the CGI aligns with (`scoreAlignXml.cgi:137` dies without one);
    - each model is the same as its books file;
    - which books models it leaves out;
    - the format of each pressed file.
- **The pinned library:**
  - **`hmmscore/data.json`** pins:
    - the tarball, by URL, size and sha256;
    - its member prefix;
    - the sha256 of the README, each `globals/` file and `books.sha256`.
  - **`books.sha256`** lists every books model's sha256 in `sha256sum`'s format. It's about 144,000 lines, which keeps a 15 MB manifest out of the package.
  - **`data manifest`** writes both from the tarball.
  - **`data fetch`** streams the download, or a local copy. It keeps only what scoring reads:
    - the README;
    - `globals/`;
    - every `hmmer.hmm`.

    It skips each family's alignment and tree. It checks everything before moving it under `hmmscore/19/`.
  - **`data verify`** checks a data folder against the pin, every books model included.
- **The hmmscore data sample.**
  - **What it holds:**
    - chosen families' models;
    - their `names.tab` lines;
    - their `binHmm` models, pressed with the pinned `hmmpress`;
    - the library's README, whose copyright statement must go with each copy.
  - **Where it's published:** as a pre-release asset of this repository, `hmmscore-sample-<n>`, pinned by a committed `sample.json`.
  - **Commands:** `sample build`, `fetch` and `verify`, as for cSNP's sample.
  - **The sample on both architectures:** a test runs `hmmscan` on the site's example against the sample. Its table must equal a committed one on amd64 and on arm64.
- **Measurements, recorded in a new `docs/parity/hmmscore-library-survey.md`:**
  - the size unpacked, and how long fetching takes;
  - `hmmscan`'s time and memory per query on the full library;
  - whether HMMER 3.4's `hmmpress` reproduces the shipped pressed files;
  - whether HMMER 3.1b2 and 3.4 give the same tables and alignments.
- **Shared code into `core/`:**
  - `open_stream` and `member_lines`, from `csnp/survey.py`;
  - `write_tarball` and the safe `unpack`, from `csnp/sample.py`.

  They move to `core/archive.py` with their tests. `core/download.py` gains a streamed HTTPS read for fetching without saving the tarball.
- **CI** caches and fetches the hmmscore sample in the `engine` job and both `engine-image` legs, and requires it.
- **Docs and decisions:**
  - **the survey doc above;**
  - **`docs/testing/engine.md`:**
    - the sample;
    - the full library;
    - publishing a new sample;
  - **`docs/testing/README.md`;**
  - **`CONTRIBUTING.md`:** `hmmscore-data` in the Spec Layout;
  - **`tech-stack.md`:**
    - hmmscore's data under `hmmscore/19/`, not the shared `/data/panther/19/`;
    - the sample;
    - its two `hmmscore` open questions, answered: which CGI copy production ran, and library modes, where only prod is used;
  - **`CLAUDE.md`:**
    - the CGI-copies gotcha, answered;
    - hmmscore's data, which no longer includes the FASTA file and its DBM index. They were only for `alignOnTheFly.cgi`.

Not in this change:

- **Scoring:**
  - `score()`;
  - the best hit;
  - the alignment;
  - `check_data()`;
  - the time limit for `hmmscan`, which this change's measurements inform.
- **The Perl reference image, the goldens and divergence rows.** Those are `port-hmmscore`'s.
- **The engine's hmmscore interface for the API,** agreed with the API developer first, as for cSNP and refmap.
- **Putting the full library on the hosting server,** and deploying.
- **All-hits output** and `pantherScore.pl`'s other modes.

## Capabilities

### New Capabilities

- `hmmscore-data`: the hmmscore service's data. It covers:
  - reading the PANTHER 19 HMM library's `names.tab` and models;
  - the one-time library survey;
  - the pinned library, with fetching and verifying it;
  - the data sample that developers and CI test against.

  Scoring, which reads the data, belongs to the port.

### Modified Capabilities

None. `engine-core`'s data folder, checksum manifests and data-marked tests already cover another service, as they did for refmap.

## Impact

- **Code:**
  - new `hmmscore/` modules: the readers, the legacy readings, the survey, the pin with fetch and verify, and the sample, with `data.json` and `sample.json` as package data;
  - `hmmscore/cli.py`, registered in `cli.py`;
  - new `core/archive.py`; `core/download.py` gains a function;
  - `csnp/` imports the moved helpers from `core/`;
  - `tests/conftest.py` gains `DATA_MANIFESTS["hmmscore"]` and an `hmmscore_data` fixture.
- **Tests:**
  - unit tests on hand-written files and small archives built in `tmp_path`;
  - the sample, marked `data("hmmscore")`;
  - the cross-architecture `hmmscan` check, marked `tools("hmmscan")` and `data("hmmscore")`.
- **CI:** the engine jobs fetch the sample on a cache miss. Its size is set when the families are chosen, and is expected to be tens of MB.
- **GitHub:** a new pre-release, `hmmscore-sample-1`. Creating it needs write access.
- **Publishing the sample:** the repository is public, so the release asset is too. The engine developer approved publishing it on 2026-11-09.
  - The library's README lets the models be "copied and redistributed freely", provided its copyright statement is reproduced with each copy.
  - The sample carries the README.
- **The developer's machine for the survey:**
  - the tarball, 18.5 GB, downloaded once;
  - the full library unpacked, for the measurements. Its size is one of the survey's findings.
- **Dependencies:** none new in Python. The engine image already has `hmmpress`. The 3.1b2 comparison runs in a throwaway container, not in the `Dockerfile`.
- **Parity with the reference:** not affected. There is no scoring output.
  - The survey measures how `pantherScore.pl` reads the files, for the port to match.
  - If HMMER 3.1b2 and 3.4 differ, the difference goes in the survey doc. `port-hmmscore` then proposes it as a divergence row.
- **API contract:** not affected. The `engine` compose service already mounts `.data/`.
- **Size:** well over the 400-line norm, as cSNP's survey change was. If reviewers prefer, it splits in two:
  - the readers, the survey and the moves to `core/`;
  - the pin, the sample, CI and the measurements.

## Open Questions

Needs team verification:

- **Whether production served exactly this build.** The engine developer expects the same release (2026-11-09). The tarball's paths start `target/famlib/rel/PANTHER19.0_altVersion/`, read here as just the build folder's name. Nothing from production is left to compare against.

Settled by the engine developer on 2026-11-09:

- **Publishing the sample:** approved (see Impact).

For review, proposed but not yet confirmed by the engine developer:

- **Pin `hmm_scoring/19.0/`, not `current_release/`.** The latter will change with the next release.
- **`books.sha256` beside a small `data.json`,** instead of a 15 MB per-file manifest in the package.
- **Fetch keeps only what scoring reads.** It skips each family's `cluster.pir` and `tree.tree`.
- **Which pressed files each copy uses:**
  - the full library uses the shipped ones, unless the press check finds a difference;
  - the sample's are pressed by HMMER 3.4.
- **The sample's families,** chosen in apply from:
  - the survey's variants;
  - the families the site's example (human APOE) hits on the full library;
  - the families hit by `test.fasta`, the sample input published with `pantherScore2.2`.
