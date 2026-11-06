# Tasks

Work test-first. For each task that adds code:

1. write its tests;
2. run them, and see them fail for the right reason;
3. write the code.

Paths under `engine/` are relative to `engine/src/panther_engine/`, unless they start with `tests/`. Run commands from `engine/`, unless a task says otherwise.

## 1. Shared Pieces and Docs

- [x] 1.1 Move `download()` from `csnp/sample.py` to `core/download.py`, unchanged (design.md, decision 1). `csnp/sample.py` then imports it from there. Move its tests into `tests/test_download.py`.

  Verify:
  - `uv run pytest tests/test_download.py tests/test_csnp_sample.py` passes;
  - `grep -rn "def download" src/` finds only `core/download.py`.
- [x] 1.2 In `docs/parity/divergences.md`:
  - set rows 9 and 10's "Approved by" to "Engine developer", and their date to 2026-11-05 (#52);
  - in row 10's Reference output, replace "(needs team verification; the help says the files are UniProt accessions)" with what the survey found: no classification file holds such an ID, because every ID in the pinned release is a UniProt accession of 6 or 10 characters.

  Verify `npx markdownlint-cli2` passes from the repository root.
- [x] 1.3 In `docs/parity/refmap-legacy-behaviour.md`:
  - **The Data:**
    - the pinned release: its URLs, date, PANTHER and Reference Proteome versions, counts and sha256s;
    - the files' format, from the #52 survey;
    - the tarball's plural folder;
    - the ten long names with `:`, and the files saved under their codes;
    - that `stats` isn't sorted;
    - how the website listed organisms: by long name (`OrganismHelper.java` 223), shown as "name (code)" (`MapOrganism.java` 29 to 49), with the first selected by default (`OrganismConstants.java` 187 to 196). With the pinned `stats`, the first is Abrus precatorius (ABRPR).
  - **`REFMAP-2` and `REFMAP-3`:** neither arises in the pinned release. They still Match, and made-up files test them.
  - **A new quirk, `REFMAP-12`:** on stderr, `$count1` counts every ID found in the file, a stored `NOHIT` included. `$count2` prints as nothing when every ID was found, giving " IDs are not mapped.". N/A: the service has no counts.
  - **Stale points:**
    - `panther-workspace`'s copy is now at `649c85f`, with the same `map_panther.pl`;
    - the classification files are public.

  Verify:
  - `npx markdownlint-cli2` passes;
  - `grep -n -i -E "isn't available|not available" docs/parity/refmap-legacy-behaviour.md` finds nothing that says the files are unavailable.
- [x] 1.4 In `CONTRIBUTING.md`'s Spec Layout, add `refmap-data` (the PANTHER 19 classification files: the pinned release, the organism list, fetching and verifying) and `refmap-engine` (mapping IDs as `map_panther.pl` did, the organisms, the `map` command, and parity with the Perl). Verify `npx markdownlint-cli2` passes.

## 2. The Organisms and the Data

- [x] 2.1 Add `refmap/data.py`'s builder and `panther-engine refmap data manifest` (design.md, decision 5). Write tests in `tests/test_refmap_data.py`, on small releases built in `tmp_path`: a tarball of `panther_classifications/<long name>` members, and a `stats` file. The tests cover:
  - the same inputs give the same bytes;
  - a file with one more line than its `stats` line counts: nothing written, and the organism named;
  - two long names ending in the same code: both named;
  - a long name ending in `_CON`, and one ending in a lower-case code: each named;
  - a member with no `stats` line, and a `stats` line with no member: each named.

  Verify that they fail before the code exists and pass after.
- [x] 2.2 Download the pinned tarball and `stats` into a scratch folder outside the repository. Check them against the proposal's sha256s, then run `data manifest` on them to write `refmap/data.json` and `refmap/organisms.json`.

  Verify:
  - `data.json` lists 1,534 files;
  - `organisms.json` lists 1,533 organisms;
  - a second run gives identical bytes;
  - `uv build` gives a wheel that holds both JSON files.
- [x] 2.3 Add `refmap/organisms.py` and the package's exports so far (design.md, decisions 2 and 4): `ORGANISM_NAMES`, `ORGANISM_CODES` and `DATA_VERSION`. Write tests, with no marker, for the spec's Organisms scenarios:
  - 1,533 codes, with `ENDPU`, `ECO57` and `PEA`, and without `HUMAN`, `MOUSE`, `YEAST` or `ECOLI`;
  - the names of `ECO57`, `PEA` and `CAMJE`;
  - `ABRPR` first and `ZYMTI` last;
  - read-only;
  - importable with `PANTHER_DATA_DIR` unset;
  - in a fresh interpreter, `import panther_engine.refmap` leaves `tarfile` and `urllib.request` out of `sys.modules`.

  Verify that the tests pass.
- [x] 2.4 Add fetch and verify, `panther-engine refmap data fetch` and `data verify` (design.md, decision 6). Test them on a small built release, with its pins passed in, for the spec's scenarios:
  - **fresh fetch;**
  - **already fetched:** a download that fails if it's called;
  - **a wrong sha256, and a wrong size:** nothing under `refmap/19/`, and both values named;
  - **an unexpected member:** a link, and a name not in the list;
  - **local copies:** with no network;
  - **a long name with `:`:** saved under its code, with no `:` in any file name;
  - **`data verify`:** lists a changed file and exits with 1.

  Verify that the tests fail before the code exists and pass after.
- [x] 2.5 Fetch the pinned release with `uv run panther-engine refmap data fetch --data-dir ../.data`. Record the time it takes in the Notes.

  Verify:
  - `data verify` passes;
  - after one byte of `ENDPU`'s file is changed, it lists `refmap/19/panther_classification/ENDPU` and exits with 1;
  - a second fetch restores the file and downloads nothing else.
- [x] 2.6 Add the data tests and CI's data step (design.md, decision 10):
  - in `conftest.py`, `DATA_MANIFESTS["refmap"]` and the `refmap_data` fixture;
  - tests marked `data("refmap")`: the folder against its manifest, and the organism list regenerated from the folder's `stats` against the committed one;
  - in `ci.yml`, the cache and fetch steps for the `engine` and `engine-image` jobs.

  Verify:
  - `PANTHER_REQUIRE_DATA=1 uv run pytest -m data` passes;
  - with `.data/refmap` renamed, the refmap data tests are skipped, with a reason naming the data;
  - `docker compose run --rm engine` passes from the repository root.

  CI itself is checked on the pull request (Workflow follow-up).
- [x] 2.7 Update two docs:
  - **`docs/testing/engine.md`, Test Data:** a "The refmap Data" section, covering:
    - the fetch command, where the data goes, and its size;
    - `data verify`;
    - why the files are named by code;
    - pinning a new release with `data manifest`.

    Add `data("refmap")` to Tests That Need the Data.
  - **`docs/design/tech-stack.md`, Shared Concerns:**
    - a `refmap/<version>/` root row;
    - refmap and the classification files removed from the `/data/panther/` row;
    - a note that developers and CI use the whole refmap release;
    - the Status line's revision.

  Verify:
  - `npx markdownlint-cli2` passes;
  - the documented commands run as written.

## 3. The Reference Image and the Goldens

- [x] 3.1 Add the `refmap-reference-script` and `refmap-reference` stages to the root `Dockerfile` (design.md, decision 8). If `build-with-extra-ca` has merged, give the download step its CA mount, as every other download step has.

  Verify:
  - `docker buildx build --load --target refmap-reference -t panther-refmap-reference .` builds;
  - with one digit of the pin changed, the build fails, naming the script;
  - `docker run --rm panther-refmap-reference perl -v` prints the Perl version (record it in the Notes);
  - `--target engine` and `--target api` still build;
  - `docker run --rm <api image> sh -c 'dpkg -l perl; ls /opt/refmap-reference'` finds neither the Debian `perl` package nor the script.
- [x] 3.2 Create `tests/golden/refmap/` (design.md, decision 9):
  - `release/`: `test_geneList` and `test_geneList_values`, downloaded from `https://data.pantherdb.org/ftp/generic_mapping/`;
  - `cases/`: the hand-made lists and the made-up files, including the divergence cases;
  - `cases.json`;
  - a `README.md` with each file's source and sha256, and how to regenerate.

  Verify:
  - after `git add`, `git ls-files --eol tests/golden/refmap/` shows the CRLF file stored with CRLF;
  - `npx markdownlint-cli2` passes.
- [x] 3.3 Add `refmap/parity.py`'s Perl runner and `panther-engine refmap parity reference`. Run it in the image to write `out/`, with `.data/` mounted read-only.

  Verify:
  - a second run gives identical files;
  - the `test_geneList` case has 450 lines and the `test_geneList_values` case has 9,228;
  - the CRLF case's lines end in `\r\t\n`.
- [x] 3.4 Update the docs for the image and the goldens:
  - **`docs/parity/golden-setup.md`:** a `refmap` section on building the image, running it and regenerating the goldens. Line 3 then names both services.
  - **`docs/parity/inputs.md`:** a `refmap` section on each case and why it's in the set.
  - **`refmap-legacy-behaviour.md`:** Proposed Golden Inputs now points to `inputs.md`.
  - **`tech-stack.md`, Engine condition 3:** a `refmap` bullet. It says the image downloads the public script at `4fc6a09` and checks its pinned sha256, that CI doesn't build it, and that the full run compares every ID.

  Verify:
  - `npx markdownlint-cli2` passes;
  - the commands in `golden-setup.md` run as written.

## 4. Mapping IDs

- [x] 4.1 Add the reading of a classification file to `refmap/mapping.py` (design.md, decision 3). Write tests, with no marker, on made-up files:
  - `REFMAP-2`;
  - `REFMAP-3`;
  - `A1` alone, and `A1\t`, each after a line that gave `A1` a value;
  - an empty second field gives `""`;
  - a third field;
  - a stored `NOHIT` gives none;
  - Latin-1 bytes are kept;
  - no line after a final `\n`.

  Verify that they fail first, then pass.
- [x] 4.2 Add the dataclasses, the input checks and `map_ids()` (design.md, decision 2). Write tests, with no marker:
  - **`ValueError`, with no file opened, for:**
    - `HUMAN`;
    - no IDs;
    - an empty ID, and one of 65 characters;
    - an ID with a space, one with a tab, and one with a non-ASCII character.
  - **`MissingDataError` naming the file,** for a missing file and for a folder in its place.
  - **The result:** the organism, the order and repeats.
  - **No cap:** 150,000 IDs against a made-up `ENDPU` file in a temporary data folder.

  Write these tests marked `data("refmap")`:
  - the spec's `ENDPU` scenarios (`U1G4Q5`, `U1GLV9`, `U1HQ27`, `A0A4Y2E0M5`, lower case, `-2` and `.1`);
  - the whole of `ARAVE` (246,021 mappings).

  Verify that they fail first, then pass.
- [x] 4.3 Add `check_data()` (design.md, decision 7). Test it on a temporary folder holding `stats` and 1,533 empty files:
  - it passes;
  - with one file missing, it names that file;
  - with `stats` missing, it names `stats`;
  - with `PANTHER_DATA_DIR` unset, it raises `DataFolderError`.

  Mark one test `data("refmap")`: it passes on the fetched data. Verify that the tests pass.
- [x] 4.4 Add `panther-engine refmap parity check` and `tests/test_refmap_golden.py` (design.md, decision 9):
  - the made-up and divergence cases, with no marker;
  - the `ENDPU` cases, marked `data("refmap")`;
  - a test that edits a copy of a golden, and expects exactly one difference, naming the case and the line.

  Verify that every case matches.
- [x] 4.5 Add `panther-engine refmap map` (design.md, decision 11). Write tests in `tests/test_refmap_cli.py`:
  - **Marked `data("refmap")`:**
    - `--file` with `test_geneList` for `ENDPU` prints the golden's first two fields;
    - `--json` prints the result.
  - **No marker:**
    - `HUMAN` exits with 1, names the organism, and prints nothing on stdout;
    - a missing data folder exits with 1, with the message and no traceback;
    - `--help` lists the options.

  Verify that the tests pass.
- [x] 4.6 Document the mapping:
  - **`docs/testing/engine.md`:**
    - a "Mapping IDs From the Command Line" section;
    - the refmap golden tests and `parity check`, in Parity Tests.
  - **`docs/testing/README.md`:** if its Engine row of Kinds of Test names cSNP's parity tests only, name refmap's too.

  Verify:
  - `npx markdownlint-cli2` passes;
  - the documented commands run as written.

## 5. The Full Run

- [x] 5.1 Add `panther-engine refmap parity full` (design.md, decision 9). Test the extras with no data:
  - the same seed gives identical lists;
  - a different seed gives different ones;
  - each kind of extra is there.

  Test the run itself on a temporary data folder with two made-up organisms, and a fake Perl from `make_tool`: one difference is reported, and the run exits with 1. Verify that the tests pass.
- [x] 5.2 Run `parity full` on the pinned data, in the image. Record the organisms, the IDs compared and the time in the Notes. Record the result in `docs/parity/inputs.md`: it's M1's acceptance for refmap's engine.

  Verify:
  - it reports no differences, and exits with 0;
  - `npx markdownlint-cli2` passes.

## 6. Final Check

- [x] 6.1 Run these from a copy of the files git would commit:
  - **in `engine/`,** with both the cSNP sample and the refmap release in `../.data`:
    - `uv sync --locked`, `ruff check`, `ruff format --check` and `basedpyright` pass;
    - `PANTHER_REQUIRE_DATA=1 uv run pytest` passes, with only the `tools` tests skipped.
  - **from the root:** `docker compose run --rm engine` passes.
  - **in `api/`,** which imports the engine: `uv sync --locked` and `uv run pytest` pass, and `uv lock --check` reports no change.
  - **docs and specs:** `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive`, and `npx openspec validate port-refmap --strict --no-interactive` pass.

## Workflow follow-up

- **One pull request, cross-cutting.**
  - **Approvals:** all three developers. The change edits the root `Dockerfile`, `ci.yml`, `tech-stack.md`, `divergences.md` and `CONTRIBUTING.md`.
  - **The engine developer's approval** also settles the proposal's "For review" items.
  - **On the pull request, confirm in the logs, not just the results:**
    - the `engine` job fetches the refmap release on a cache miss and saves it;
    - both `engine-image` legs run the refmap data tests with none skipped;
    - the `api` jobs pass.
- **#40, by the API and frontend developers:** the wiring listed in the proposal's "Not in this change", including replacing the `HUMAN` example.
- **Hosting:** with #40, fetch and verify the refmap release on the server, and give the `api` service the data.
- **After the merge,** archive with `/opsx:archive`. That creates `openspec/specs/refmap-engine/spec.md` and `openspec/specs/refmap-data/spec.md`.
- **Open an issue:** `panther-engine csnp score` prints a traceback on `MissingDataError`, found while surveying cSNP's command line for this change.
- **Comment on #52** with the pull request's link. Its team questions stay open.

## Notes

### Next action

Every task is done. The engine developer reviews the code, and the corrected design decision 3. Then one pull request, as Workflow follow-up says.

### Blockers

None.

### Progress (2026-11-06, arm64 Mac, Docker 29.9.2)

- **1.1:** `download()` and its timeout moved to `core/download.py`. It raises `DownloadError`, since `core/` can't raise cSNP's `SampleError`, and `csnp sample fetch` catches it. No test called `download()` directly, so `tests/test_download.py` is new: HTTPS only, a redirect to HTTP refused, the User-Agent and the timeout, with `urlopen` replaced. cSNP's fetch-level test of an HTTP URL stays in `test_csnp_sample.py`, since it checks the fetch's cleanup too.
- **1.3:** REFMAP-12 checked with the Perl on a two-line file: a stored `NOHIT` counts as mapped, and the second line is " IDs are not mapped.". Beyond the task's list, settled by #52: REFMAP-1's Decide (no folding), rows 9 and 10 now approved, and three "needs team verification" in What the Website Called (`stats` is a static file, the codes are unique, 1,533 organisms).
- **The tarball has a folder member,** `panther_classifications`, before its 1,533 files. `data manifest` and `data fetch` accept that one folder, and refuse any other folder, link or path.
- **2.2:** the pinned tarball and `stats` downloaded in 2 s, and matched the proposal's sha256s. `data manifest` took 6 s. Every check passed: `stats` and the tarball agree on every organism's lines and lines with a PANTHER ID. 1,534 files, 1,533 organisms, the same bytes on a second run, and both JSON files in the wheel. `.gitattributes` marks both as generated, as `full.json` is.
- **2.4:** fetch replaces only the files that are missing or differ, so 2.5's "a second fetch restores the file and downloads nothing else" is read as: the release is downloaded again, ENDPU alone is replaced (the other 1,533 files keep their inodes), and the fetch after that downloads nothing.
- **2.5:** a fresh fetch took 32 s, almost all of it the download; `data verify` 1.8 s. 502 MiB on disk.
- **2.6:** the data marker's message now says "data", not "data sample", since the refmap data is a whole release; two marker tests expect the new text. `PANTHER_REQUIRE_DATA=1 uv run pytest -m data`: 81 passed, 22 skipped, all of them `tools`. With `.data/refmap` renamed, both refmap data tests skip, naming "the refmap data". `docker compose run --rm engine`: 517 passed, none skipped, in 2 min 43 s.
- **For 3.3: `run_tool()` captured text, and Python's text mode reads `\r\n` and `\r` as `\n`,** so the Perl's output couldn't be kept byte for byte (the CRLF case's `\r\t\n`). `run_tool()` now takes an optional `stdout` file, written byte for byte, as the README's `> output` does. Tested in `test_process.py`. It changes no existing caller.

- **3.1:** the image has Perl 5.40.1 (`perl 5.40.1-6+deb13u1`). It built in 15 s with the engine stage cached. With the pin's last digit changed, the build failed with `map_panther.pl: FAILED`. `engine` and `api` still build, and the API image has neither Debian's `perl` package (`dpkg -l` shows `un`) nor `/opt/refmap-reference`. The download stage has no CA mount: `build-with-extra-ca` hasn't merged, so task 3.1's condition doesn't hold. Its uncommitted changes shared the working copy with this one's; on 2026-11-06 they were moved into `openspec/changes/build-with-extra-ca/working-tree.patch`, so this change commits alone. The images were rebuilt from the `Dockerfile` without them, and the goldens came out the same.
- **3.2 and 3.3:** 21 cases: the two release lists, six hand-made lists on ENDPU, seven made-up files, and six divergence cases (four for row 10, two for row 9). `parity reference` takes about 2 s; a second run gave the same bytes. `git ls-files --eol` shows `cases/crlf.classification` as `i/crlf`.
- **The reference corrected design decision 3.** `my ($id, $pthr) = split(/\t/, $line)` assigns to two scalars, so Perl gives `split` an implicit limit of 3, and a trailing empty field is kept: `A1\t` gives `A1` an empty PANTHER ID, not none (the `no-second-field` golden; checked with `perl -e` too). design.md decision 3 now says so. The spec already agreed: "no second field" means no tab. The tests in 4.1 follow the reference.
- **4.2:** `map_ids` for ARAVE's 246,021 IDs takes about 0.5 s through `refmap map`, process start included.
- **4.4:** every golden case matches: 15 by their lines, and 6 refused with the errors their divergence rows name.
- **4.5:** the line rendering, `render()`, moved to `mapping.py`, so `refmap map` and `parity check` print a mapping the same way.
- **6.1, early:** natively, `PANTHER_REQUIRE_DATA=1 uv run pytest` passed 584, with 31 skipped, all `tools`. In `api/`, `uv sync --locked`, `uv lock --check` and `uv run pytest` (339 passed, 6 `blastp` skips) passed.

- **5.2, M1's acceptance:** `parity full` in the image, on the pinned release with seed `port-refmap`: 1,533 organisms, 23,114,501 IDs compared (the release's 22,961,201 and 100 extras each), no differences, exit status 0, in 81 s. Run again with the command as `golden-setup.md` documents it, without `--user`: the same result. This answers design.md's open question on the run's time. Whether CI should run it, for example weekly, is for the team.
- **6.1,** from a copy of the files git would commit (tracked, and untracked but not ignored, without the unrelated `panther-api-044eb0c.tar.gz`), with both data sets cloned into its `.data/`:
  - in `engine/`: `uv sync --locked`, `ruff check`, `ruff format --check` and `basedpyright` pass; `PANTHER_REQUIRE_DATA=1 uv run pytest` passed 584, with 31 skipped, all `tools`;
  - from the root: `docker compose run --rm --build engine` passed 615, none skipped;
  - in `api/`: `uv sync --locked`, `uv run pytest` (339 passed, 6 `blastp` skips) and `uv lock --check` pass;
  - `npx markdownlint-cli2`, `npx openspec validate --all --no-interactive` (18 passed) and `npx openspec validate port-refmap --strict --no-interactive` pass.

- **CI on #63 (2026-11-06): the `repo` job's gitleaks scan failed** on two lines of `refmap/data.json`. Every other job passed. The paths end in the organism codes `APICC` and `APIME`, so the `generic-api-key` rule read the "api" in the key and the sha256 beside it as a secret. Reproduced with gitleaks 8.30.1, CI's pinned version. `.gitleaks.toml` now keeps the default rules and allows that rule's findings only in that file, and only for a 64-character hex value. The scan then reports no leaks. In a scratch folder, a key that isn't a sha256 in the same file was still reported, and so was a sha256 under an `API…` key in another file. `docs/testing/README.md` names the file.

### Failed approaches

- **A link from the copy's `.data` to the real one (6.1).** The copy already has `.data/` as a folder, for its tracked `.gitkeep`, so `ln -s` put the link inside it, and 103 data tests failed. A link to a host path wouldn't work in a container either. `cp -cR` of `csnp/` and `refmap/` clones them on APFS, instantly.

### Lessons learned

- **Assigned to scalars, Perl's `split` keeps a trailing empty field.** `my ($id, $pthr) = split(/\t/, $line)` has an implicit limit of 3; `my ($id, @rest) = split(...)` has none. Read the left side before describing a `split`. Worth keeping for the `hmmscore` port.
- **Python's text-mode capture changes line endings.** `subprocess` reads `\r\n` and `\r` as `\n`, so a reference's output must go to a file, through `run_tool(stdout=...)`, to be kept byte for byte. Worth keeping for every Perl reference.
