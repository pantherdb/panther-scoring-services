# Proposal

**Area:** frontend

## Why

`frontend/` has conventions (`frontend/CLAUDE.md`) and an accepted stack (`docs/design/frontend-stack.md`), but no code. The first feature, the scoring form, needs a working app to land in: one where the store, the API layer, routing, theming, lint and both test suites are already wired. Setting them up now means each feature plugs into what is there instead of retrofitting state management later.

## What Changes

- New Vite + React 19 + TypeScript project in `frontend/`, with its own `package.json`.
- App shell: a header with the app title and a page frame, using Mantine for controls and Tailwind for layout.
- One route (`/`, a placeholder home page) and a not-found page for every other URL.
- An empty Redux store holding an RTK Query API that has no endpoints yet. Features add their own endpoints to it later.
- MSW set up with an empty list of handlers, shared by the dev server, Vitest and Playwright.
- Three ways to run the app and the e2e suite: against mocks, against a real API, and against an already-running site at any URL with no build or mocks.
- Mantine theme and Tailwind `@theme` tokens, with Mantine's styles loaded as a CSS layer in a fixed order.
- Tooling: ESLint (flat config), Prettier, strict TypeScript, React Compiler.
- Tests in their own folders, not next to the code: `tests/` (Vitest + React Testing Library, mirroring `src/`) and `e2e/` (Playwright, desktop and mobile projects, against the built app).
- `docs/testing/frontend.md`: how to run each frontend suite.

Not in this change: the scoring form, job status, results table, CSV export, help content, and `api:types` generation (there is no OpenAPI schema to generate from yet).

## Capabilities

### New Capabilities

- `scoring-ui`: the web UI for cSNP scoring. This change adds only its shell: the title, the home route and the not-found page. Later changes add the form, job status, results table, export and help content to the same capability.

### Modified Capabilities

None.

## Impact

- **Code:** new files under `frontend/` only. `frontend/CLAUDE.md` is unchanged unless setup shows that a convention there doesn't work.
- **Dependencies:** the npm packages listed in `docs/design/frontend-stack.md`, plus MSW. Playwright browsers are installed with `npx playwright install`.
- **Docs:** new `docs/testing/frontend.md`. `docs/testing/README.md` says e2e runs "against a running API"; it's updated to name all three modes. If the theme setup settles which library holds the colours (Mantine or Tailwind), that goes in `frontend/CLAUDE.md`.
- **Parity with the Perl:** not affected. This change has no scoring logic and needs no divergences.
- **API contract:** not affected. No endpoints are called yet.

## Open Questions

- **Which library holds the colours.** `frontend/CLAUDE.md` says Tailwind's `@theme`, but Mantine computes its shades in JavaScript and may need real colour values. Decide during setup; check whether Mantine 9 accepts CSS variables as theme colours.
- **The title text.** The working default is "PANTHER cSNP Scoring". Confirm in review.
