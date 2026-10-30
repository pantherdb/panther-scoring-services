# Proposal

**Area:** frontend. Outside `frontend/`, it edits `docs/testing/frontend.md` and `docs/manual-qa/02-csnp-form.md`. It changes nothing in `api/` or `engine/`.

## Why

In mock mode (`npm run dev`, and the `build:e2e` build for the e2e tests), every API answer is made up by MSW, including a cSNP result that uses the real APOE example with plausible ages, predictions and pDel values. Nothing on screen says so. In review on #20 the engine developer asked for a visible marker, so a screenshot from mock mode can't pass for a real PANTHER-PSEP result. On #19 the team agreed there are no made-up scores: mocks for building the UI are allowed, but they must be unmistakable. The frontend developer chose a banner on every page.

## What Changes

- **A mock-data banner in the app shell,** on every page, the not-found page included. It says that this is mock data and that nothing on the page comes from the scoring service. It stays in view while the page scrolls, fits a phone's width, and is a named region that screen readers list with the page's landmarks.
- **It shows only on mocks:** in `npm run dev` and the `build:e2e` build. Never with the real API: `npm run dev:api`, `npm run preview` of a `build`, and the production `build`.
- **One flag decides mock mode.** Today `main.tsx` reads `VITE_API_MOCKING` itself to start MSW. That check moves into one function in `src/app/`, which both MSW's start-up and the shell read, so they can't disagree.
- **The production build ships no mock code:** neither the banner's text nor MSW. Its JavaScript already leaves MSW out; MSW's worker script, which Vite copies from `public/` into every build, is now left out of builds without mocking too.
- **Tests:** Vitest for the banner with the flag on and off; Playwright in mock mode on the home page, `/csnp`, a job page and the not-found page, on desktop and mobile; Playwright in api mode for its absence; and a check of the production build's `dist/`.
- **Docs:** `docs/testing/frontend.md` (what mock mode shows) and `docs/manual-qa/02-csnp-form.md` (the banner beside the mock results).

No new dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui`: two ADDED requirements, "Mock data is marked on every page" and "No mock data with the real API". Existing requirements don't change.

`split-substitutions-on-commas` also changes `scoring-ui`, at the same time. Its delta touches only "cSNP substitutions split on whitespace", and this one only adds, so the two can be archived in either order.

## Impact

- **Frontend code:** a new `src/app/mocking.ts` (the flag), `src/main.tsx` (reads it), a new `src/layout/MockDataBanner.tsx`, `src/layout/AppLayout.tsx` (shows it), `vite.config.ts` (leaves the worker script out of builds without mocking); tests in `tests/` and `e2e/`.
- **API contract:** unchanged. `npm run api:types:check` passes with the committed `schema.d.ts`.
- **Parity with any service's reference:** not affected. The banner adds text only in mock mode, which never shows a real result; nothing a real result shows changes. No divergence row is needed.

## Open Questions

None that change what's built. The wording of the banner is the frontend developer's to approve in review.
