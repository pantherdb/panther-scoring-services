# Proposal

**Area:** cross-cutting. The work is in `engine/`, but the change also:

- adds a test-only stage to the root `Dockerfile`;
- adds a data step to CI's engine jobs;
- approves two rows in `docs/parity/divergences.md`;
- edits `docs/design/tech-stack.md` and `CONTRIBUTING.md`.

All three developers own those.

## Why

`refmap` is the second service to port. Its contract (#30) and form (#35) are merged, and the API answers a valid request with `501` until the engine can map IDs. The engine questions on #52 are answered (2026-11-05, with an update on 2026-11-06) from a survey of every published PANTHER 19 classification file, so the port can start. This change ports `map_panther.pl`, the parity reference, behind the interface `add-refmap-job` proposed. It pins the data, and adds the goldens that prove parity.

## What Changes

- **Parity first:**
  - **A Perl reference image,** a test-only `refmap-reference` stage of the root `Dockerfile`: Debian's `perl`, and `map_panther.pl` at `4fc6a09`. `pantherdb/RefProteomeMapper` is public, so the build downloads the script at that commit and checks its pinned sha256. No local checkout is needed, unlike cSNP's.
  - **Goldens made by that image,** in `engine/tests/golden/refmap/`:
    - the data's own test: the README's `test_geneList` against `Endocarpon_pusillum_ENDPU`;
    - every ENDPU ID, through the data folder's `test_geneList_values`;
    - hand-made lists: repeats, lower case, `-2` and `.1`, IDs that aren't in the file, and an ID from another organism;
    - small made-up classification files, for what the pinned data never has: a repeated ID (`REFMAP-2`), CRLF endings (`REFMAP-3`), a line with no second field, and extra columns.
  - **`panther-engine refmap parity full`,** run in the reference image. It passes every ID of every organism in a data folder, with generated extras, through the Perl and the port, and compares them. On the pinned data, that's M1's acceptance run. It fits on a developer machine: the whole release is 157 MB.
- **The port, `panther_engine.refmap.map_ids(RefmapInput) -> RefmapResult`,** as `add-refmap-job` design decision 3 proposed. `RefmapResult` gains `organism` (#52, question 7).
  - The lookup is `map_panther.pl`'s:
    - exact and case-sensitive on the first field;
    - the last line for an ID wins;
    - a `\r` in a classification line is kept.
  - It returns one mapping per ID, in order, repeats included.
  - The PANTHER ID is `None` both for an ID that isn't in the file and for one stored as `NOHIT`. The Perl printed `NOHIT` for both.
  - It raises `ValueError` for input the API rejects.
  - A missing or unreadable file raises an error, rather than giving `NOHIT` for every ID (divergence 9).
- **The organisms:**
  - **`organisms.json`,** committed in the package and generated from the pinned `stats` (#52, question 3). It lists each organism's code, long name and gene counts, in the website's order.
  - **The engine exports `ORGANISM_CODES`, `ORGANISM_NAMES` and `ORGANISM_GENES`.** The names are what the website showed before the code, such as "Escherichia coli O157:H7" for `ECO57`, as `SPECIES_NAMES` does for cSNP. The gene counts are each organism's genes and those with a PANTHER ID, from `stats`.
- **The data:**
  - **A committed manifest** pins the 2024-06-20 release on `data.pantherdb.org`: the tarball, `stats`, and every file's sha256.
  - **`panther-engine refmap data fetch`** downloads the release and checks it. It saves each classification file under its organism code, as `refmap/19/panther_classification/ECO57` (#52, update to question 4), because ten long names contain `:`, which Windows can't use in a file name.
  - **`panther-engine refmap data verify`,** and `check_data()` for the API's startup check.
  - **`DATA_VERSION`** is `"19"`.
- **`panther-engine refmap map`,** for checks by hand.
- **CI fetches the refmap data,** cached, so the tests that need it run, as they do for the cSNP sample.
- **Docs:**
  - **`divergences.md`:**
    - rows 9 and 10 are approved by the engine developer, dated 2026-11-05 (#52);
    - the data settles row 10's "needs team verification".
  - **`refmap-legacy-behaviour.md`:**
    - what the data holds;
    - that `REFMAP-2` and `REFMAP-3` don't arise;
    - the stale points corrected;
    - a new quirk, `REFMAP-12`: the Perl's counts on stderr count a stored `NOHIT` as mapped. N/A, since the service has no counts.
  - **`golden-setup.md` and `inputs.md`:** the refmap reference image, the goldens and the full run.
  - **`tech-stack.md`:**
    - the Shared Concerns row puts refmap's data under `refmap/19/`, not the shared `/data/panther/19/`;
    - Engine condition 3: the refmap image downloads its public script.
  - **`docs/testing/engine.md`:** fetching the refmap data, mapping from the command line, and the parity tests.
  - **`CONTRIBUTING.md`:** the Spec Layout gains `refmap-data` and `refmap-engine`.

Not in this change:

- **Wiring the engine into the API** (#40, the API and frontend developers):
  - removing the `501`;
  - checking `organism` against `ORGANISM_CODES`;
  - `organism` in the API's result;
  - compact storage for large results;
  - an organism-list endpoint;
  - `Versions.data`;
  - the `api` service's data;
  - the frontend's organism selector and example.

  `HUMAN` isn't a refmap organism (#52, question 1). The form's example, the `scoring-ui` requirement that it be human, and "such as HUMAN" in messages and docs change there.
- **Putting the data on the hosting server,** and deploying.
- **The team's questions on #52:**
  - jobs or synchronous (the job stays);
  - what replaces `map_panther_cls`;
  - re-attaching extra columns (`REFMAP-5`);
  - whether the CGI was reachable from outside (`REFMAP-8`).
- **Renaming the files upstream.** The published names stay as they are (#52, update to question 4).

## Capabilities

### New Capabilities

- `refmap-engine`: mapping IDs to PANTHER families as `map_panther.pl` does. It covers the result, the organism list the engine publishes, the `map` command, and parity with the Perl through the reference image.
- `refmap-data`: the pinned PANTHER 19 classification files. It covers the manifest, generating the organism list from `stats`, fetching with each file saved under its code, verifying, and the data CI has.

### Modified Capabilities

None. `engine-core`'s data folder, checksum manifest and data-marked tests already cover a second service.

## Impact

- **Code:**
  - new `refmap/` modules: the dataclasses and `map_ids()`, reading a classification file, the organism list and its JSON, the data manifest with fetch and verify, and the parity run;
  - `refmap/cli.py`, registered in `cli.py`.
- **Tests:**
  - unit tests on made-up files;
  - golden tests, and the organism list checked against `stats`, marked `data("refmap")`;
  - command-line tests.
- **Root `Dockerfile`:** a new `refmap-reference` stage after `engine`. The `engine` and `api` stages don't change, and CI doesn't build the new stage.
- **CI:** the engine jobs fetch the refmap data: 157 MB on a cache miss, 523 MB unpacked.
- **API contract:** not affected here. The API's `RefmapResult` gains `organism` in #40, when the API first builds a result.
- **Dependencies:** none new in Python. The reference image adds Debian's `perl` package, test-only.
- **Parity with the reference:** this change is the proof.
  - The port matches the first two fields of `map_panther.pl`'s output on every golden, and on every ID of every organism in the full run.
  - Rows 9 and 10 are the only divergences, approved here. Neither changes an answer when the data is in place and the input is valid.
  - `REFMAP-2` and `REFMAP-3` don't arise in the pinned data. The port matches them on made-up files.
- **Size:** likely over the 400-line norm with its tests and docs. Goldens and generated JSON don't count. If reviewers prefer, it splits in two: the data and organisms, then the mapping, goldens and parity.

## Open Questions

Needs team verification:

- **Whether production ran exactly these files.** The data server's folder serves the classification files, `stats` and `genericMapping.cgi` side by side, the layout the website's `/mapping19/` URLs read. That CGI is byte for byte `4fc6a09`'s. The goldens don't depend on it.

For review, proposed but not yet confirmed by the engine developer:

- **The engine doesn't cap the number of IDs.** The API's 100,000 is a limit on a job's work. The engine maps any number, so the full run can pass a whole genome. `ValueError` covers the API's other rules.
- **`organisms.json` holds the code, the long name and the gene counts.** The display name is derived as the website did (`MapOrganism.java`). The counts were left out at first, since nothing shows them; #63's review asked for them, for the overrepresentation and enrichment tests on a generic mapping file. Those tests run outside refmap, and the website read the counts from refmap's deployment (`/mapping19/stats`, `OrganismHelper.java`). They stay in refmap, beside the files they count.
- **The test lists from the data server,** `test_geneList` and `test_geneList_values`, are committed as golden inputs, with their source and sha256.
- **The reference image downloads `map_panther.pl` from GitHub when it's built.** That needs the network at build time, and the extra CA wherever a proxy re-signs TLS (`build-with-extra-ca`).
- **CI downloads the release from `data.pantherdb.org` on a cache miss,** with no mirror. If that server is down, the engine job fails until it's back, or until someone mirrors the release as a GitHub release asset.
- **The full run's extras.** For each organism, besides every ID in its file, it adds a seeded sample of its IDs that are:
  - repeated;
  - lower-cased;
  - given `-2` or `.1`;
  - taken from another organism's file.
