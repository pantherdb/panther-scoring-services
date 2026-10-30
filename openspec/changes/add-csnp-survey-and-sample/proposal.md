# Proposal

**Area:** cross-cutting. The work is in `engine/`, but the change also records three decisions in `CLAUDE.md`, `CONTRIBUTING.md`, `tech-stack.md`, `divergences.md` and `openspec/config.yaml`, which all three developers own.

## Why

The cSNP port can't start until we know what the PAML library really contains, and until developers and CI have data to test against. [tech-stack.md](../../../docs/design/tech-stack.md) (Shared Concerns, Data) settles both. First, survey the whole library once with the new parser. Then pick a sample, one family per file variant, for developers and CI. The full library is 19.2 GB unpacked, too big for a laptop or a CI runner.

`scaffold-engine` named this as the next engine change. On 2026-10-29, cSNP became the first of the four services, ahead of `refmap`, `hmmscore` and `treegrafter`, so its data work comes first. The same day, the engine developer chose a GitHub release asset to store the sample, a decision tech-stack.md left to them.

The shared docs still give the old order, and still say that production's library build can't be known. In fact, `PAML_RST.tar.gz` was tarballed from the production server before it was shut down. They also say the cSNP thresholds must be settled before porting. Instead, the engine developer decided on 2026-10-29 to follow the code wherever it and its docs disagree, and to revisit the docs' version once cSNP is live on production. This change records all three.

## What Changes

- **Readers for the cSNP data,** in `panther_engine.csnp`: the `.paml`, `.rst` and `.orig.tree` files of the PAML_RST library, and the species tree `species_pthr8_time.nhx`.
  - **They're strict.** A file that doesn't have the shape the legacy behaviour spec §3.5 describes is an error that names the file and line, never a silent misread.
  - **They're the first piece of the port.** Step 3 will use them.
- **A library survey,** `panther-engine csnp survey`. It reads `PAML_RST.tar.gz` as a stream, without unpacking it to disk, and checks every family:
  - every family has its three files; split parts and their base families (`DATA-1`);
  - each file parses, including the empty `.rst` and truncated `.paml` files already known (`DATA-1`);
  - the three files agree with each other: node counts, parents, leaf ANs and sequence lengths;
  - **where the Perl's reading differs from the strict one.** The Perl finds things with unanchored patterns and fixed line numbers. The survey counts the families where its reading would differ from the strict reader's: the start column (`SCORE-2`), the root, the `.rst` branch list (`SCORE-9`), the pairing of nodes with ANs, the events and taxa that the `Ev=…:S=…:ID=…` pattern misses, and line endings;
  - taxa missing from the species tree, and each `Ev` value (`DATA-3`);
  - optionally, given the PANTHER9 BLAST archive: every BLAST entry whose family has a `.paml` is found in that family's `.orig.tree`, and the Perl's gene lookup finds the same AN as an exact one (`DATA-2`, `SCORE-8`).

  It reports counts, and the smallest example families of each variant. The results, and the sample chosen from them, are recorded in a new `docs/parity/csnp-library-survey.md`.
- **The cSNP data sample.** One tarball, attached to a GitHub release of this repo, holds the chosen families, `species_pthr8_time.nhx` and the PSEP release's copyright statement. A committed manifest pins the tarball's sha256 and each file's.
  - `panther-engine csnp sample build` makes the tarball from `PAML_RST.tar.gz`, byte for byte the same each time. It first checks the archive against the checksum in spec §7.1.
  - `panther-engine csnp sample fetch` downloads the tarball, checks it and unpacks it into the data folder. It does nothing when the folder already matches the manifest.
  - `panther-engine csnp sample verify` checks a data folder against the manifest.
- **A data folder, in `core/`.** The engine reads its data from the folder named by `PANTHER_DATA_DIR`. cSNP's frozen PANTHER 9 data goes under `csnp/9/`, following tech-stack.md's Data table. `core/` also gets a checksum-manifest reader, which the deploy-time data check in tech-stack.md can reuse.
- **Tests that need data,** marked `data("csnp")`. They're skipped when the data isn't there, and fail when `PANTHER_REQUIRE_DATA=1`, as the `tools` marker does. They check the sample against its manifest, parse every sample family, and reproduce examples from the spec with the new readers, such as `del28`'s start column (`SCORE-2`).
- **Developers and CI get the sample:**
  - `fetch` puts it in `.data/` at the repo root, which git ignores. `compose.yaml` mounts that folder read-only at `/data`.
  - CI's `engine` and `engine-image` jobs restore it from the Actions cache, keyed on the manifest, and fetch it on a miss. They run the tests with `PANTHER_REQUIRE_DATA=1`.
- **Byte-exact test files.** `.gitattributes` gains `-text` for `engine/tests/fixtures/csnp/` (hand-written library files, some with CRLF on purpose) and `engine/tests/golden/`, the golden-files folder the parity harness will fill.
- **Three decisions, in the shared docs:**
  - the order is `csnp`, `refmap`, `hmmscore`, `treegrafter`: in `CLAUDE.md`'s Project table, `tech-stack.md`'s Scope table and the context in `openspec/config.yaml`;
  - `PAML_RST.tar.gz` is production's library build, tarballed from the production server before it was shut down. That goes in `CLAUDE.md`'s `csnp` section and in `tech-stack.md`, whose open question on the library build it answers. It also answers legacy behaviour spec §8, question 4;
  - **where the legacy code and its docs disagree, follow the code,** so M1 reproduces what ran in production, and log the docs' version to revisit after the service is live. The rule goes beside the "needs team verification" rule in `CLAUDE.md`, `CONTRIBUTING.md` and `openspec/config.yaml`.
    - **For cSNP's thresholds and pDel bounds** (`SCORE-5`, `SCORE-6`), the port keeps the code's 180 / 380 Mya and `age < bound`, not the 200 / 450 Mya and inclusive bounds of the help page and the science owner's 2021 ticket.
    - **In `divergences.md`,** the ticket's version becomes proposed row 7 (`SCORE-5`), beside the existing proposed row 4 (`SCORE-6`). Both are deferred until cSNP is live on production.
    - **In `tech-stack.md`,** Engine condition 7 and the thresholds question say so, and the Review table names `thomaspd` as the science owner.
- **Docs:**
  - new `docs/parity/csnp-library-survey.md`, listed in `docs/parity/README.md`;
  - `docs/testing/engine.md`: getting the sample, the `data` marker, and publishing a new sample;
  - `docs/testing/README.md`: the CI rows;
  - `CONTRIBUTING.md`: `csnp-data` in the Spec Layout;
  - `tech-stack.md`: the storage decision and the data folder.

New dependencies: none in Python. The readers, survey and sample commands use only the standard library. CI adds `actions/cache`, pinned to a commit SHA.

Not in this change:

- **Scoring.** No pipeline step is ported: no start-column rule, trace-back or ages. The readers expose what the files hold. Which reading step 3 uses is the port's decision, made with the survey's counts in hand.
- **The PANTHER9 BLAST database in the sample.** Nothing here runs BLAST. It joins the sample, through the same manifest and release, with the change that ports step 1.
- **The parity harness, the Perl reference image (Engine condition 3) and golden files.** This change only names the golden-files folder.
- **A checksum manifest of the full library** for deploys.
- **Regenerating the cSNP data,** which tech-stack.md puts out of scope.
- **The engine's cSNP interface for the API:** the `score` function with its input and result types, an `InputError` the API can show, and the data version. These are agreed with the API developer in a change of their own, before step 3 is ported.

## Capabilities

### New Capabilities

- `csnp-data`: the cSNP service's data. Reading the PAML_RST library and the species tree, the one-time library survey, and the data sample that developers and CI use. The scoring that reads the data belongs to `psep-engine`.

### Modified Capabilities

- `engine-core`: adds where the engine finds its data (`PANTHER_DATA_DIR`), checking data against a checksum manifest, and tests that need data, beside the existing tests that need the tools.

## Impact

- **Code:**
  - new `core/data.py` and `core/manifest.py`;
  - new `csnp/` modules for the readers, the survey and the sample, the sample manifest, and a `csnp/cli.py` for the subcommands;
  - `cli.py` gains the `csnp` subcommand;
  - `tests/conftest.py` gains the `data` marker.
- **Shared files:**
  - `CLAUDE.md`, `CONTRIBUTING.md`, `docs/design/tech-stack.md`, `docs/parity/divergences.md` and `openspec/config.yaml`: the three decisions. All three developers approve this change for that reason;
  - `.gitattributes`: the two `-text` rules;
  - `.gitignore`: `.data/`, except a new `.data/.gitkeep`;
  - `compose.yaml`: the `/data` mount and `PANTHER_DATA_DIR`;
  - `.github/workflows/ci.yml`: the cache, the fetch and `PANTHER_REQUIRE_DATA` in both engine jobs.
- **Docs:** as listed above.
- **GitHub:** a new release in this repo, tagged `csnp-sample-1`, with the sample tarball. It isn't marked latest. Creating it needs write access.
- **Publishing the sample:** the repository is public, so the release asset is too. The engine developer approved publishing it on 2026-10-29.
  - The archive is production's library build.
  - The PSEP 1.01 README allows copying and redistribution, provided its copyright statement goes with each copy. The sample carries that statement.
- **Size:** well over the 400-line norm. The engine developer chose one pull request (2026-10-29). The sample is chosen from the survey's results, and the survey is the readers' library-wide test, so the parts don't stand alone.
- **Parity with the reference:** not affected. There is no scoring output. The survey compares the readers with the Perl's readings on every family. It reports the differences for the port to decide, so no divergence row is needed here. Row 7 is added only as a proposal, deferred until after production, so it changes nothing the port must match.
- **API contract:** not affected.
  - The API imports the engine (`connect-api-to-engine`), but nothing it uses changes: `report_tools()`, `ToolReport`, `TOOLS` and the `tools` stage.
  - The engine gains no runtime dependency, so `api/uv.lock` doesn't change.
  - The `engine` compose service gains the read-only data mount. The API developer asked to hear about changes to that service first.

## Open Questions

None. The engine developer settled these on 2026-10-29:

- **Publishing the sample:** approved (see Impact).
- **Service order:** `csnp` first, then `refmap`, `hmmscore` and `treegrafter`.
- **The cSNP thresholds and pDel bounds:** the code's, for now. The science owner's 2021 values are revisited in a separate issue, after cSNP is live on production.
