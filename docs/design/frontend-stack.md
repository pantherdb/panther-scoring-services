# Frontend Stack

**Status:** Accepted, 2026-10-28. Split out of [tech-stack.md](tech-stack.md), which stays Proposed for the API and the engine.

## Decision

React + Tailwind is a good fit, and it is the stack the frontend developer already ships, which keeps the team's projects consistent.

| Concern | Choice | Why |
| ------- | ------ | --- |
| Framework | React 19, TypeScript 5 (strict), Vite 7 | Current React, fast dev server and build |
| Compiler | React Compiler (`babel-plugin-react-compiler`) | Memoizes for us, so components don't carry hand-written `useMemo` / `useCallback` |
| Components | Mantine 9 (`core`, `hooks`, `notifications`), Tabler icons | Accessible, behaviour-rich controls: inputs, selects, modals, tables, notifications |
| Styling | Tailwind v4 (`@tailwindcss/vite`), design tokens in one `@theme` block | Layout, spacing, typography and surfaces. Mantine does controls, Tailwind does the rest |
| Server state | Redux Toolkit 2 with RTK Query | One place for every API call. Its polling covers job status |
| Client state | Component state first; a Redux slice only for state several features share | The UI is a form, a job status and a results table, so there is little of it |
| Routing | React Router 7 | A job's results get their own URL, so they can be bookmarked and shared |
| API types | `openapi-typescript`, generated from FastAPI's schema | The contract is the schema; types are never written by hand |
| API mocking | Mock Service Worker (MSW) | The UI is built before the API exists. MSW answers real requests at the network layer, so switching to the real API changes only the base URL. The same handlers serve Vitest and Playwright |
| Unit and component tests | Vitest, React Testing Library, `user-event`, jsdom | Tests what the user sees and does |
| End-to-end tests | Playwright, desktop and mobile projects | Runs against a built app, not the dev server |
| Lint and format | ESLint 9 (flat config) with `typescript-eslint`, `react`, `react-hooks` 7, `jsx-a11y`; Prettier 3 with the Tailwind plugin | `react-hooks` 7 also enforces what the React Compiler needs; `jsx-a11y` catches accessibility mistakes |

The conventions for using this stack are in [frontend/CLAUDE.md](../../frontend/CLAUDE.md).

## Why the Whole Stack From Day One

The first release is the input form on its own, as a standalone tool to check that the code works. The job status, results table and export come later. The store, RTK Query and the router are set up anyway, before the features that need them, because:

- **Adding state management later is expensive.** Once components fetch and hold their own data, moving them onto a store means touching each one. Wired from the start, each new feature plugs into what is already there.
- **The form already uses the API.** Submitting the form is the first RTK Query call. When the results table arrives, it reads from the same store and needs no changes to the form.
- **It matches the team's other projects.** The same stack means the same patterns, lint rules and tests across repos.

## How the Pieces Fit

**Each kind of state has one home.**

```text
Mantine useForm (draft) --submit--> RTK Query mutation --> store (job, results)
                                                             |
                                    later: results table, job status read from here
```

- What the user is typing stays in Mantine `useForm`, not in Redux.
- What the API returns goes through RTK Query and lives in the store.
- A Redux slice is added only for client state that several features share.

**Mantine and Tailwind share one set of colours.** Each colour is defined in one place, and the other library reads it from there; never define it twice. Mantine computes its colour shades in JavaScript, so it needs real colour values. Which side is the source is set when the theme is first built, and recorded in [frontend/CLAUDE.md](../../frontend/CLAUDE.md).

**CSS layers load in a fixed order.** Load Mantine's styles as a cascade layer (`@mantine/core/styles.layer.css`), ordered against Tailwind's layers. Otherwise Tailwind's base reset and Mantine's component styles override each other depending on import order.

## Rules That Come With It

1. **Nothing outside the stack.** No other UI kit (MUI, Chakra, Ant Design, Radix), no CSS-in-JS or CSS Modules, and none of the graph-editor dependencies (`jointjs`, `reactflow`, `dagre`, Apollo/GraphQL, `socket.io`).
2. **Keep state light.** RTK Query holds everything that comes from the API. Add a slice only for client state that several features share.
3. **Generate API types.** Generate TypeScript types from FastAPI's OpenAPI schema in CI. Then a change to the API can't silently break the frontend.
4. **Match the legacy features:** species selector, example input, results table, CSV export (`csnpScoreResExport.jsp`) and help text (`tips_csnpScores_content.jsp`).

## Not Decided Here

The **frontend ↔ api contract** (the job endpoints, request and result shapes, polling) is shared with the API developer and is still Proposed in [tech-stack.md](tech-stack.md). Until it's agreed, the frontend builds against a mocked API.

**ESLint 10.** The stack names ESLint 9, and npm now warns that ESLint 9 is end-of-life. The other newer majors (TypeScript 7, Vite 8, React Router 8) aren't adopted either: the scaffold pins the newest release of each major named above. Moving to any of them is a change to this doc, made through a proposal.

## Review

| Reviewer | Covers | Status |
| -------- | ------ | ------ |
| Frontend developer | The whole frontend stack | Accepted, 2026-10-28 |
| Frontend developer | Additions on 2026-10-28: MSW, Why the Whole Stack From Day One, How the Pieces Fit | Pending |
