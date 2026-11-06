# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **The frontend stack and its conventions:** [docs/design/frontend-stack.md](../../../docs/design/frontend-stack.md) (Accepted) and `frontend/CLAUDE.md`, in particular "No build details on screen", "Colour Mantine through the theme" and "Every colour is defined once, in `@theme`".
- **The findings:** FE-1 and FE-2 in `docs/code-review/2026-10-30-whole-repo-review-64174c9.md`.

The behaviour is in [specs/scoring-ui/spec.md](specs/scoring-ui/spec.md).

## Goals / Non-Goals

**Goals:**

- A render error never shows React Router's developer screen, a stack or the error's text, in any build.
- A page's render error leaves the header, footer and a way home.
- Field errors and descriptions meet WCAG AA.

**Non-Goals:**

- Reporting errors anywhere: there's no error service to send them to.
- Normalising the versions answer in `wire.ts` (FE-17, Low). `VersionList` defaults the two lists itself, which covers the footer and the job page.
- A dark colour scheme. The app has none; the resolver sets only the light one.

## Decisions

### An `errorElement` on each page route and on the root route

React Router renders the nearest route's `errorElement` when a route's element, or anything under it, throws.

- **Page routes** get `ErrorPage`. It replaces the `<Outlet />`, so `AppLayout`'s header and footer stay.
- **The root route** gets `RootError`: the mock data banner when mocked, the header, and `ErrorPage` in a `<main>`. It's used when `AppLayout` itself throws, as it did for FE-1, since the footer is part of the layout. It has no footer, because the footer's fetched versions are the likeliest cause.
- **Alternative:** one pathless route with an `errorElement` wrapping every page. Same result, but the review and the request ask for one on each page route, and five explicit entries make a missing one easy to see.
- **The header moves to `AppHeader`** so `RootError` doesn't copy it.

### Error details only in the console, only in development

`ErrorPage` reads the error with `useRouteError()` and, in an effect, calls `console.warn` when `import.meta.env.DEV` is true. A production build drops the branch. React and React Router also log a caught render error with `console.error`; that's the console, not the screen, and is left alone.

### `VersionList` defaults `tools` and `data` to empty lists

`(versions.tools ?? []).map(...)`. The generated type says both are required, so the defaults document an older API rather than the schema. The lint isn't type-aware, so it doesn't flag the `??` as unnecessary.

### Colours through `cssVariablesResolver`, defined once in `theme.ts`

Mantine reads `--mantine-color-error` for an input's error and `--mantine-color-dimmed` for its description. `cssVariablesResolver` sets them in the light scheme to `var(--color-danger)` and `var(--color-ink-muted)`. Both providers, `src/main.tsx` and `tests/utils/render.tsx`, import the one resolver.

- **Alternative:** override the variables in `index.css`. `frontend/CLAUDE.md` says to colour Mantine through the theme, not stylesheet overrides.

### Testing

- **Vitest** uses the real route table, with `vi.mock` making the home page or the footer's `AppVersions` throw behind a flag, so the same file has the success case beside each failure.
- **Playwright** can't make a page throw in the built app once the footer is fixed, so its check is the original trigger: a versions answer without `tools` or `data`. In mock mode MSW's service worker answers before `page.route` sees a request, so the spec replaces `window.fetch` with `addInitScript`, which works in every mode.
- **Contrast** is measured in Chromium: each text's computed colour is painted on a canvas and read back as sRGB, since the tokens are `oklch()`, and compared with the body's background by WCAG's formula. jsdom computes no colours, so Vitest only checks what the resolver returns.

## Risks / Trade-offs

- **[`ErrorPage`'s link home when the home page is what throws]** → the link leads back to the same error. Reloading or a fixed release is the only way out; the page still has the header and no stack.
- **[A future route without an `errorElement`]** → its errors go to the root's `RootError`, which still hides the stack, but loses the footer. `frontend/CLAUDE.md` says to add one.
