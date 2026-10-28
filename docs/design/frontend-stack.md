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
| Unit and component tests | Vitest, React Testing Library, `user-event`, jsdom | Tests what the user sees and does |
| End-to-end tests | Playwright, desktop and mobile projects | Runs against a built app, not the dev server |
| Lint and format | ESLint 9 (flat config) with `typescript-eslint`, `react`, `react-hooks` 7, `jsx-a11y`; Prettier 3 with the Tailwind plugin | `react-hooks` 7 also enforces what the React Compiler needs; `jsx-a11y` catches accessibility mistakes |

The conventions for using this stack are in [frontend/CLAUDE.md](../../frontend/CLAUDE.md).

## Rules That Come With It

1. **Nothing outside the stack.** No other UI kit (MUI, Chakra, Ant Design, Radix), no CSS-in-JS or CSS Modules, and none of the graph-editor dependencies (`jointjs`, `reactflow`, `dagre`, Apollo/GraphQL, `socket.io`).
2. **Keep state light.** RTK Query holds everything that comes from the API. Add a slice only for client state that several features share.
3. **Generate API types.** Generate TypeScript types from FastAPI's OpenAPI schema in CI. Then a change to the API can't silently break the frontend.
4. **Match the legacy features:** species selector, example input, results table, CSV export (`csnpScoreResExport.jsp`) and help text (`tips_csnpScores_content.jsp`).

## Not Decided Here

The **frontend ↔ api contract** (the job endpoints, request and result shapes, polling) is shared with the API developer and is still Proposed in [tech-stack.md](tech-stack.md). Until it's agreed, the frontend builds against a mocked API.

## Review

| Reviewer | Covers | Status |
| -------- | ------ | ------ |
| Frontend developer | The whole frontend stack | Accepted, 2026-10-28 |
