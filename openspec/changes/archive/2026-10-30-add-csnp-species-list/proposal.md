# Proposal

**Area:** cross-cutting. The work is in `api/` and `frontend/`; nothing in `engine/`, `compose.yaml` or CI changes. The OpenAPI schema gains an endpoint, so the frontend and API developers both review it (CONTRIBUTING, Review Rules).

## Why

The cSNP form asks the user to type a species code such as `HUMAN`, and only the API can say whether a code is one cSNP scores. The old site offered its 85 organisms by name, and [frontend-stack.md](../../../docs/design/frontend-stack.md#rules-that-come-with-it), rule 4, asks the UI to match its species selector. The engine now publishes each code's name (`add-csnp-species-names`, #27), so the API can serve the list and the form can offer it.

## What Changes

- **The API lists cSNP's species.** `GET /api/v1/csnp/species` answers with every species the `csnp` job accepts, each as `{"code", "name"}`, such as `{"code": "HUMAN", "name": "Homo sapiens"}`, in the engine's order. The list is built once from `panther_engine.csnp.SPECIES_NAMES`, and the response may be cached by the browser for an hour.
- **The request doesn't change.** `species` stays a string, checked against `SPECIES_CODES` by the request model as `wire-csnp-scoring` added. The schema publishes no enum of the codes: the endpoint is the list.
- **The form's species box becomes a searchable dropdown.** Each option reads "Homo sapiens (HUMAN)"; typing part of a name or a code finds it. `HUMAN` is chosen at first, "Use an example" still chooses `HUMAN`, and the request still sends the code.
- **The form checks the species against the list,** once the list has loaded, as the API does.
- **The form stays usable without the list.** While it loads, the dropdown says so. If it can't be loaded, the form shows the code box it has today, with a short note and a button to try again.
- **Mock mode** serves a short list of real species, marked as mock data like everything else there.
- **Tests:** the endpoint's contents, order, headers and schema, and that the `csnp` request accepts every listed code; the dropdown, its search, the default, the example, the loading and failure states and a submit with a chosen species (Vitest); choosing a species by typing part of its name (e2e, mock mode); the real list and a job started with a species chosen from it (e2e, api mode).
- **Docs:** `api/README.md`, `docs/testing/api.md`, `docs/testing/frontend.md` and `docs/manual-qa/02-csnp-form.md`.

No new dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `api-service`: a new requirement, "cSNP species list".
- `scoring-ui`: "cSNP form" offers the species as a searchable list; "cSNP form checks the input before sending" checks the species against the list once it has loaded; a new requirement, "cSNP species list unavailable", keeps the form usable without it.

`scoring-input` doesn't change: its species rule, as `wire-csnp-scoring` modifies it, already lets the form check more than the shape. None of the requirements this change modifies is one `wire-csnp-scoring` modifies.

## Impact

- **API:** a new router, `routers/csnp.py`, included by `create_app()`; `openapi.json`; tests.
- **Frontend:** `schema.d.ts` regenerated; a `speciesApi.ts` endpoint and a species field in `features/csnp/`; `checks.ts`, `CsnpForm.tsx`, the mocks, the unit tests and the e2e specs.
- **The engine interface:** the API imports `SPECIES_NAMES` from `panther_engine.csnp`, which is public. Nothing in the engine changes.
- **Parity with the reference:** not affected, and no divergence row is needed. The species list chooses the same code the user typed before, and the legacy pipeline only ever saw the code: the old site turned the chosen name into a code before calling `snpScore.cgi` (`add-csnp-species-names`, proposal).
- **Order:** this change builds on `wire-csnp-scoring` (#26), which adds the species check and the `data` versions. Merge it after #26.

## Open Questions

`wire-csnp-scoring` asks the frontend developer whether the schema should publish the 85 codes as an enum, so the form can offer a list. This change answers it: **no enum**. The list comes from `GET /api/v1/csnp/species`, with names, and the request keeps its validator. design.md, decision 2, gives the reasons.

For the frontend developer:

- **The order on screen.** The engine gives code order; the form sorts by name, so "Homo sapiens" sits among the H's. The old site listed by a rank from its database, then by name, and that rank isn't in `panther-workspace`. Is name order right, or should common species such as `HUMAN` and `MOUSE` come first? Needs team verification.

For the engine developer:

- **Older names** such as `Canis familiaris` are now on screen. `add-csnp-species-names` left updating them to the science owner; this change shows them as the engine gives them.
