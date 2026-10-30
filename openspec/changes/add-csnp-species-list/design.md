# Design

## Context

See proposal.md, Why. This change relies on these decisions and doesn't repeat them:

- **The engine is a library the API imports,** with no HTTP between them: [tech-stack.md](../../../docs/design/tech-stack.md), "Engine (`engine/`)" and "API (`api/`)".
- **The species names,** their source and their order: [add-csnp-species-names' design](../add-csnp-species-names/design.md). `SPECIES_NAMES` is a read-only `Mapping[str, str]` in code order, and `SPECIES_CODES = frozenset(SPECIES_NAMES)`.
- **The species check in the request model:** [wire-csnp-scoring's design](../wire-csnp-scoring/design.md), decision 3.
- **The frontend stack and its conventions:** [frontend-stack.md](../../../docs/design/frontend-stack.md) (rule 4 asks for the species selector) and `frontend/CLAUDE.md`.
- **Errors as problem details:** [api-stack.md](../../../docs/design/api-stack.md).

What exists now:

- The API has three routers, `health`, `versions` and `jobs`, each a module in `routers/` with its own tag, included under `/api/v1` by `create_app()`. Each response is a Pydantic model, so the schema describes it.
- The form's species is a `TextInput` holding the code, `HUMAN` at first. The client checks its shape; the API checks its membership, and the form shows the API's `422` on the field.

The behaviour is in the spec deltas under `specs/`.

## Goals / Non-Goals

**Goals:**

- One source for the species: the engine's `SPECIES_NAMES`, read by the API, served to the form. Nothing in the API or the frontend writes a code or a name, apart from the default `HUMAN` and the mock data.
- The form works when the list doesn't load.

**Non-Goals:**

- Names in a job's request or result. A score is for a species code, as the legacy service's was.
- Lists for the other services. `refmap` will need its own organism list; it can follow this endpoint's pattern then.
- Updating any name, or choosing the order on screen for good (proposal, Open Questions).

## Decisions

### 1. `GET /api/v1/csnp/species`, a list of `{code, name}`

- **Path:** a new router, `routers/csnp.py`, with the prefix `/csnp` and the tag `csnp`, included after `jobs`. The species are cSNP's, not every service's: `refmap` and `treegrafter` read the current PANTHER release, whose organisms differ. A per-service prefix leaves room for each service's own reference lists, as `/jobs` holds every service's jobs.
- **Shape:** a JSON array of `CsnpSpecies`, `{"code": str, "name": str}`, in the engine's order. An array, like `tools` and `data` in the versions, keeps an order and needs no wrapper; nothing else belongs in the body.
  - *Alternative:* an object keyed by code, `{"HUMAN": "Homo sapiens", …}`. Rejected: the schema can't name the keys, the generated type would be `Record<string, string>`, and JSON object order isn't a contract.
  - *Alternative:* `{"species": [...]}`. Rejected: nothing to put beside the list. A later field would be a new endpoint or a new version of this one.
- **Built once:** the router module builds the list from `SPECIES_NAMES` when it's imported, as a tuple of frozen models, and every request returns that tuple. Serialising 85 short entries is cheaper than anything that would save it.
- **The model** lives in the router module, as `Health` does in `routers/health.py`. Workers import `jobs/csnp.py`, so it stays out of there.

### 2. No enum in the schema

`wire-csnp-scoring` asked whether the request's `species` should be an enum of the 85 codes. It shouldn't:

- **The endpoint is the list,** with the names an enum can't carry. The form needs those, so it would call the endpoint anyway.
- **An enum puts 85 codes in every client's types,** and in the request's schema, where `panther-site-java` and any other client would read them. A change to the species would then be a schema change for every client, though the request's shape doesn't change.
- **Pydantic's message for a failed enum lists every value,** where the validator's message is one sentence and doesn't repeat the value (`api/README.md`, "Never echo submitted values").
- **The request keeps its validator,** so the rule is still the API's, and the endpoint's tests check that every listed code passes it.

### 3. Cached by the browser for an hour

The response carries `Cache-Control: public, max-age=3600`. The list is fixed by the image, so it changes only with a deploy.

- **Why an hour:** each visit to the form within the hour reuses it, and after a deploy that changes the list, a browser shows the old one for an hour at most. Then the API's check is still the authority: a species that's gone gets the `422` on the field.
- *Alternative:* a day, or `immutable`. Rejected: a deploy that adds a species would leave it missing from the form for a day. The response is 4 KB, so caching longer saves little.
- *Alternative:* an `ETag`. Rejected for now: it saves the body, not the request, and nothing else in the API has one.

### 4. The frontend: an endpoint, a hook, a field

- **The endpoint,** `getCsnpSpecies`, is injected into the one RTK Query API from `features/csnp/speciesApi.ts`, as `versionsApi` and `jobsApi` are from their features (`src/app/api/api.ts` says features add their endpoints this way). Its type, `CsnpSpecies`, is exported from `wire.ts` from the generated schema; nothing is renamed.
- **`useCsnpSpecies()`** turns the query into `{ status: 'loading' | 'loaded' | 'failed', species, codes, retry }`. `species` is sorted by name for display (proposal, Open Questions); `codes` is the set the checks read. "Loading" is when there's no data and no error, so a retry after an error shows as loading (`frontend/CLAUDE.md`, State and Data).
- **`CsnpForm` calls the hook,** passes the codes to the checks and the rest to **`SpeciesField`**, which renders one of three states:
  - **Loaded:** a Mantine `Select`, `searchable`, with each option's value the code and its label "`<name> (<code>)`". Mantine's default filter matches any part of the label, case-insensitively, so a code or part of a name finds the species. `allowDeselect={false}` and no clear button: the species can't be emptied, only changed. Its dropdown is placed with `floatingStrategy: 'fixed'`: on opening, Mantine scrolls the chosen option into view before the dropdown is placed, and an absolutely placed dropdown is still at the top of the page then, so on a phone, where the field is below the fold, the page jumped to the top and the dropdown was hidden with the field.
  - **Loading:** the same `Select`, disabled, with the placeholder "Loading species…" and a `Loader`.
  - **Failed:** the `TextInput` the form has now, with a fixed note that the list couldn't be loaded and a code is still accepted, and a button to load it again. Nothing from the error is shown.
- **The draft keeps the code** in `values.species`, whichever control shows it, so switching from the text box to the list after a retry keeps the user's choice when it's in the list.
- *Alternative:* a native `<select>`. Rejected: 85 options with no search, and `frontend/CLAUDE.md` names Mantine's `Select`.
- *Alternative:* a `Select` that shows the codes while the list loads or after it fails. Rejected: a dropdown of bare codes is the text box with extra steps, and typing a code the list doesn't have would still need the text box.

### 5. The client checks, with the list when there is one

`checkSpecies(text, codes)` keeps the shape check, then, when `codes` is given, requires a code from it: "Choose a species from the list." While the list loads or after it fails, `codes` is undefined and only the shape is checked, as now; the API checks membership either way. The list and the API's check are the same set, so the form rejects nothing the API accepts.

### 6. Mock data: eight real species

`src/mocks/data/species.ts` holds eight entries, with real codes and names, such as `HUMAN` and `MOUSE`, and no runtime imports, so the e2e spec can read it.

- *Alternative:* all 85, copied from the engine. Rejected: a second copy of the names that could drift, in a file whose banner says nothing comes from the scoring service. The names can't be imported from the engine or the schema, since the schema has no enum (decision 2).

## Risks / Trade-offs

- [The list and the API's check differ after a deploy, within the cache's hour] → The API still decides; the form shows its `422` on the species field, as it does now.
- [Mantine's `Select` misbehaves under jsdom, as `Textarea`'s autosize does] → It does: `tests/setup.ts` stubs `ResizeObserver` and `scrollIntoView`, and the tests render with `MantineProvider env="test"`, without which the dropdown is hidden for having no layout. `frontend/CLAUDE.md` says so.
- [A user can't empty the dropdown, so the "every field empty" check no longer reaches the species] → The species is never empty while the list shows; the text box fallback still checks for an empty species.
- [Older names on screen, such as `Canis familiaris`] → Shown with the code, so the species is clear; renaming is the science owner's call.

## Migration Plan

- Merge after `wire-csnp-scoring` (#26), with the frontend and API developers' approvals. The API and the frontend deploy together: a frontend with the dropdown and an older API falls back to the code box, which still works.
- Archive after `wire-csnp-scoring`.
- Rollback: revert the commit. The form goes back to the code box, and nothing persisted changes.
