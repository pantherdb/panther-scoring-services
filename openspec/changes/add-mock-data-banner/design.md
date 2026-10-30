# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **The frontend stack, and building against a mocked API until the contract is agreed:** [docs/design/frontend-stack.md](../../../docs/design/frontend-stack.md), "Not Decided Here".
- **Styling with the `@theme` tokens, no build details on screen, tests by role, mocking at the API boundary:** [frontend/CLAUDE.md](../../../frontend/CLAUDE.md).
- **The modes** (`dev`, `dev:api`, `build`, `build:e2e`, `preview`) and the e2e tags: [docs/testing/frontend.md](../../../docs/testing/frontend.md).

What exists now:

- `VITE_API_MOCKING` is `on` in `.env.development` and `.env.e2e`, and `off` in `.env.api` and `.env.production`. `src/main.tsx` reads it itself, and imports `@/mocks/browser` only when it's `on`, so the production bundle leaves MSW out.
- `public/mockServiceWorker.js` is MSW's worker script. Vite copies `public/` into every build, so `npm run build` puts it in `dist/` although nothing registers it.

The behaviour is in [specs/scoring-ui/spec.md](specs/scoring-ui/spec.md).

## Goals / Non-Goals

**Goals:**

- One place answers "is the API mocked?", and the shell and MSW's start-up both ask it.
- A production build has nothing of mock mode in it.

**Non-Goals:**

- Marking mock data inside a result (a watermark on the scores table, say). The banner is on every page, results included.
- Changing what mock mode mocks, or the `.env.*` files.

## Decisions

### The flag: `isApiMocked()` in `src/app/mocking.ts`

```ts
export function isApiMocked(): boolean {
  return import.meta.env.VITE_API_MOCKING === 'on'
}
```

- **`main.tsx`** starts MSW only when it's true; **`AppLayout`** shows the banner only when it's true.
- **A function, not a module constant,** so a Vitest test can turn the flag on and off with `vi.stubEnv`, without reloading modules. Vite replaces `import.meta.env.VITE_API_MOCKING` with its literal at build time, so in a build the function returns a constant, and Rollup drops the code behind it. The `dist/` check (task 3.2) proves that, rather than trusting it.
- **Alternative:** a `<MockModeProvider>` context. More code for one boolean that never changes while the app runs.

### The banner: a named `<section>` above the header

`src/layout/MockDataBanner.tsx`, shown by `AppLayout` as the shell's first child.

- **Element:** `<section aria-label="Mock data">`, which has the role `region`. A region with a name is a landmark, so a screen reader lists it with the header, main and footer, and a user who jumps between landmarks finds it first. Alternatives:
  - `role="note"`: not a landmark, so it's read only when the reader gets to it.
  - `role="alert"` or `role="status"`: a live region, made to announce changes. The banner doesn't change; an alert would also interrupt on every load.
  - A labelled `<aside>` (`complementary`): it means content beside the main content, which this isn't.
- **Text:** "**Mock data.** Nothing on this page comes from the scoring service: every job, result and version is made up." It names no mode, command or variable, so the "No build details on screen" rule holds.
- **Colours:** `bg-ink` with `text-white`: about 17:1, well over WCAG AA's 4.5:1, and unlike the `primary-700` header, so it reads as something other than the page. No new token. `danger` was ruled out: it means an error.
- **Sticky:** `sticky top-0`, so a screenshot of any part of a long results page shows it. It's one line on desktop and two or three on a phone, which is acceptable in a mode for building the UI.
- **Icon:** Tabler's `IconAlertTriangle`, `aria-hidden`, beside the text.

### Leaving MSW's worker script out of builds without mocking

A plugin in `vite.config.ts`, applied to builds only, deletes `mockServiceWorker.js` from the output directory after writing, unless `VITE_API_MOCKING` is `on` for that mode. It reads the same `.env.*` value as the app, through `loadEnv`.

- **Alternative:** `publicDir: false` for the production mode. It would also drop anything else added to `public/` later, such as a favicon.
- **Alternative:** leave it. It's harmless, since nothing registers it; but the production build would then contain MSW, and the check couldn't be a plain search of `dist/`.

### Tests

| Spec scenario | Test |
| ------------- | ---- |
| Home page on mocks; Not a build detail | Vitest: `AppLayout` with `VITE_API_MOCKING` stubbed `on`; e2e (mock) `mock-data.spec.ts` |
| Form, job and not-found pages on mocks | Vitest: the app's routes at `/does-not-exist`; e2e (mock) `mock-data.spec.ts` on `/`, `/csnp`, a job page and `/does-not-exist` |
| Scrolled to the end of a page | e2e (mock): shorten the window to 400 px, scroll a succeeded cSNP job's page to the end; the region is in the viewport |
| Mobile width | e2e (mock), `mobile` project; no sideways scroll |
| Against the real API | Vitest: `AppLayout` with the flag `off`; e2e (api) `mock-data.spec.ts` |
| The production build | `npm run build`, then a search of `dist/` for the banner's text, `msw` and `mockServiceWorker` |

The e2e tests in mock mode are tagged `@mock`, and the api-mode one `@api`, so neither runs in the other mode.

## Risks / Trade-offs

- **[A screenshot cropped below the banner]** → It stays at the top of the viewport, so a crop has to cut it out on purpose. Nothing in a page can stop that.
- **[The `.env.*` files and the flag drift apart]** → The e2e runs check both ends: `build:e2e` shows the banner, `build` doesn't.
- **[The sticky banner covers content when an in-page link scrolls to it]** → There are no in-page anchors yet. Add `scroll-margin` then.
