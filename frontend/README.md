# frontend

The web UI for PANTHER's four scoring services (`hmmscore`, `refmap`, `csnp`, `treegrafter`): for each, a form, a job status and a results table. It uses React 19, TypeScript, Vite, Mantine, Tailwind v4 and Redux Toolkit with RTK Query, and calls the API in [`api/`](../api/README.md) at `/api/v1`.

## Quick Start

From `frontend/`, with the Node version in [`.nvmrc`](../.nvmrc):

```sh
npm ci
npm run dev                            # http://localhost:5173, with the API mocked by MSW
```

To use the real API instead, start it first, either with `docker compose up --build api` from the repository root or natively from `api/`. Then run `npm run dev:api`, which sends `/api` to `localhost:8000`.

## Layout

```text
src/
  app/          the store, router, theme, and the RTK Query API in app/api/
  features/     one folder per feature, each adding its own endpoints
  layout/       the app shell
  components/   shared components
  mocks/        MSW handlers, used by the dev server, Vitest and Playwright
tests/          Vitest and React Testing Library
e2e/            Playwright, in mock, api and site modes
```

## Working on It

- **Read [CLAUDE.md](CLAUDE.md) before writing code.** It has the conventions: where state goes, how to mock, and what's outside the stack.
- **API types come from the OpenAPI schema,** never by hand. After `api/openapi.json` changes, run `npm run api:types` and commit `src/app/api/schema.d.ts`. CI fails while they differ.
- **Before a pull request:** `npm run type-check && npm run lint && npm test`, then `npm run test:e2e`.

## More

- [docs/testing/frontend.md](../docs/testing/frontend.md): every script, and the three e2e modes.
- [docs/design/frontend-stack.md](../docs/design/frontend-stack.md): the stack, and why (Accepted).
- [openspec/specs/scoring-ui/spec.md](../openspec/specs/scoring-ui/spec.md): what the UI must do.
