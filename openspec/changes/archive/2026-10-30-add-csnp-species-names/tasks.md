# Tasks

## 1. The Names

- [x] 1.1 In `engine/src/panther_engine/csnp/codes.py`, write `SPECIES_NAMES` from the 85 entries of `CSNP_SHORT_LONG_ORG_LIST` (`OrganismConstants.java` line 79), each split at its first hyphen, in code order, as a `MappingProxyType` typed `Mapping[str, str]` (design.md, decisions 1 to 4). Make `SPECIES_CODES = frozenset(SPECIES_NAMES)`, say in the module docstring where the names come from and that they are in code order, and export `SPECIES_NAMES` from `panther_engine.csnp` (`__all__` and its docstring). Verify that `ruff check`, `ruff format --check` and `basedpyright` pass, and that `uv run pytest tests/test_csnp_scoring.py` passes unchanged
- [x] 1.2 In `engine/tests/test_csnp_scoring.py`, beside the codes' tests, test the spec's three scenarios, importing `SPECIES_NAMES` from `panther_engine.csnp`: a name for each of the 85 codes and no other; the names of `HUMAN`, `PLAF7`, `SYNY3` and `CANFA`; and that changing or adding a name raises `TypeError` and leaves the names unchanged. Verify they pass
- [x] 1.3 Pin the checksum (design.md, decision 5): compute the sha256 of the list's entries, `CODE-Name`, one per line, in the list's order, from `OrganismConstants.java`, and record `panther-workspace`'s commit and whether the list is in code order in the Notes. Add a test that builds the same text from `SPECIES_NAMES` and compares its sha256 with the pinned one. Verify it passes, and that it fails with one letter of one name changed, then restore the name

## 2. Final Check

- [x] 2.1 From a copy of the files git would commit, verify that everything passes, and record the counts in the Notes:
  - in `engine/`: `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright` and `PANTHER_REQUIRE_DATA=1 uv run pytest`;
  - `docker compose run --rm --build engine`, which runs `test_the_species_codes_are_the_blast_databases` with `blastdbcmd`, so the derived codes are checked against the sample's database;
  - in `api/`, which imports the engine: `uv sync --locked` and `uv run pytest`;
  - `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive`.

## Workflow follow-up

- Open the pull request against `main`. The API developer reviews it, since it adds to the engine's interface.
- After the merge, tell the API developer that `SPECIES_NAMES` is in, for serving the list to the form.
- Archive with `/opsx:archive`.

## Notes

### Next action

None: the change is merged (#27, `ce48464`) and archived (2026-10-30).

- tmushayahama approved #27 from the API and frontend side, and merged it. Their review agreed to copying the 85 names from `panther-site-java`, the proposal's question for review. The form will show "Homo sapiens (HUMAN)", in the order the API serves them.
- CI on `7090c87` passed (run 41134147982): `engine` 391 passed, `engine-image` 410 on both architectures, `api` 147.
- `SPECIES_NAMES` is on `main`, as #26's answers told the API developer. Next on their side: serving the codes with their names, and the form's species selector.
- The lesson learned is now in `docs/testing/engine.md`, under Natively.
- The proposal's open questions stay open: which names production showed, and the older names.

### Blockers

None. #25 merged on 2026-10-30 (`d47f672`), so the `psep-engine` main spec is on `main`, and this branch was fast-forwarded onto it. That merge changed no files.

### Progress

- **The list's codes (2026-10-30):** the 85 codes of `CSNP_SHORT_LONG_ORG_LIST` are exactly `SPECIES_CODES`, compared code by code while drafting this change.
- **The list (tasks 1.1 and 1.3), 2026-10-30:** `OrganismConstants.java` line 79 at panther-workspace `ba373a3`, with no local changes. Its 85 entries are unique and already in code order; no name has a hyphen, extra spaces or a non-ASCII character. `codes.py`'s literal was generated from that line by a script, not typed.
- **The checksum (task 1.3):** the sha256 of the entries, each `CODE-Name` followed by a newline, is `a48cb191…381d`, computed twice from the Java file. Since the list is in code order, the test builds the text from `SPECIES_NAMES` in its own order, with no sort. With `Homo sapiens` changed to `Homo sapienz` it fails, and passes again once restored.
- **Final check (task 2.1), 2026-10-30,** from `git checkout-index` of the staged files, with the data sample cloned in and confirmed by `sample fetch` ("already there: nothing to fetch"):
  - in `engine/`: `uv sync --locked`, `ruff check`, `ruff format --check`, `basedpyright` and `PANTHER_REQUIRE_DATA=1 uv run pytest` pass; 391 passed, and only the 19 `tools` tests skipped;
  - `docker compose run --rm --build engine` passes: 410 passed, none skipped, so `test_the_species_codes_are_the_blast_databases` checked the derived codes with `blastdbcmd`;
  - in `api/`: `uv sync --locked`, `uv run pytest` (147 passed) and `uv lock --check` pass;
  - `npx markdownlint-cli2` (103 files, no issues) and `npx openspec validate --all --no-interactive` (12 passed) pass.
- **Started before review (2026-10-30):** the engine developer ran apply before the proposal was reviewed, so the pull request carries the proposal and the implementation together, as `port-csnp`'s did.

### Failed approaches

None.

### Lessons learned

- **A same-size edit undone within a second leaves stale bytecode.** Python's `.pyc` check compares the source's size and its mtime in whole seconds. Task 1.3's check changed one letter of `codes.py` and restored it in the same second, so the next run still imported "Homo sapienz" and failed two tests, though the source was right. Deleting `__pycache__/codes.cpython-313.pyc` fixed it. When a task breaks a file on purpose to see a test fail, run that check with `PYTHONDONTWRITEBYTECODE=1`, or delete the module's `.pyc` after restoring it. pytest's `-p no:cacheprovider` doesn't help: that is pytest's cache, not Python's bytecode.
