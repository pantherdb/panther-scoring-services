# frontend/

The web UI for PANTHER's scoring services (`hmmscore`, `refmap`, `csnp`, `treegrafter`): for each, a form, a job status and a results table. The stack and why it was chosen are in [docs/design/frontend-stack.md](../docs/design/frontend-stack.md); this file is how we use it. The project-wide rules in [../CLAUDE.md](../CLAUDE.md) still apply.

## Before Claiming Anything Works

```bash
npm run type-check && npm run lint && npm test
npm run test:e2e        # Playwright, against a built app
```

## Folders: by Feature, Not by File Kind

```text
src/
├── app/            store, typed hooks, theme, router, API client. Wiring only, no feature UI
│   └── api/        RTK Query API, generated schema types, the wire module
├── layout/         the shell: header, footer, page frame
├── components/     shared UI used by more than one feature
└── features/
    └── <feature>/  its components, hooks, slice and selectors, together
tests/              mirrors src/ path for path; tests/setup.ts is Vitest's setup
e2e/                Playwright specs and fixtures
```

- A feature owns its components, hooks, slice and selectors. Its tests live at the mirrored path under `tests/`.
- A feature's `index.ts` exports only what other features need.
- Features don't import from each other's internals. Shared code moves to `components/` or `app/`.
- Make a feature folder when there is state, UI and logic that belong together. A single shared component goes in `components/`.
- Import with the `@/` alias (`@/features/...`), not long `../../` paths.

## Components

- **Function components with named exports.** No default exports.
- **Props as a local `type Props = { ... }`** above the component, destructured in the signature.
- **One concern per component.** If one fetches, computes and renders, split it. Past about 100 lines, something wants extracting: a hook, a subcomponent or a selector.
- **Stateful logic goes in a `useX.ts` hook** next to the component that uses it.
- **Show real loading and error states.** Never render "no data" when the request failed.

## React Compiler and the Rules of React

The app builds with the React Compiler, and `react-hooks` 7 fails the lint on what the compiler can't handle.

- **Don't hand-write `useMemo` / `useCallback` for performance.** The compiler does it. Keep them only where identity is part of the behaviour.
- **Don't read refs while rendering.** Read them in effects and handlers.
- **Don't set state in an effect to follow a prop.** Derive the value while rendering, or set it while rendering behind a guard.
- **Don't read the clock while rendering.** Take the time from a hook, so the render is pure.
- **Don't define components inside components.**
- **Effects must be idempotent.** StrictMode runs them twice in development and tests.
- **When a lint rule is wrong**, disable it on that line with a comment saying why. Never disable it for a file.

## Styling: Mantine for Controls, Tailwind for the Rest

**Mantine** for components with real behaviour:

- Controls: `Button`, `ActionIcon`, `TextInput`, `Textarea`, `Select`, `MultiSelect`, `Checkbox`, `Switch`, `SegmentedControl`, `Tooltip`
- Structure: `AppShell`, `Modal`, `Drawer`, `Menu`, `Popover`, `Tabs`, `Accordion`, `Table`
- Forms and feedback: `useForm`, `notifications`, `Loader`, `Alert`, `Badge`, `Progress`

**Tailwind** for layout, spacing, text and surfaces. Don't use Mantine's styled wrappers:

| Don't use | Use instead |
| --------- | ----------- |
| `<Group>` | `<div className="flex items-center gap-2">` |
| `<Stack>` | `<div className="flex flex-col gap-2">` |
| `<Text>` | `<p>` or `<span>` with Tailwind text classes |
| `<Card>`, `<Paper>` | `<div className="rounded-xl bg-white p-6 shadow-sm">` |
| `<Divider>` | `<hr className="border-hairline" />` |

- **Use the scale and the tokens.** Tailwind's steps and the tokens in the `@theme` block are the vocabulary: `text-sm`, not `text-[13px]`. If you need a value twice, add a token.
- **Name colours by their job, not their hue.** `text-primary-700` or `text-danger`, not `text-blue-700`. Every colour is defined once, in `@theme`.
- **Colour Mantine through the theme** (`src/app/theme.ts`), not through stylesheet overrides or `!important`. The theme reads the `@theme` colours as CSS variables (`var(--color-primary-600)`). `@theme static` makes Tailwind emit every token, even ones no class uses. Mantine can't compute contrast for `var()` colours, so don't rely on `autoContrast`.
- **No inline `style={{}}`** except for values computed at runtime.

## State and Data

- **Every API call goes through RTK Query** in `src/app/api/`. No `fetch` or `axios` in components.
- **Types come from the OpenAPI schema.** Run `npm run api:types` after the API changes; a renamed field then fails `tsc` instead of failing in the browser. Never hand-write a type the schema already has.
- **One module converts between the API's shapes and the app's.** If the API speaks snake_case, only that module renames fields. It's `src/app/api/wire.ts`.
- **Poll job status with RTK Query's `pollingInterval`**, and stop when the job finishes or fails.
- **Show "loading" when there's no data, not from `isLoading`.** While a request is retried after an error, RTK Query reports `isError` and `isLoading` both false, so a page that keys on them shows nothing.
- **Read the store only through the typed hooks** in `src/app/hooks.ts` (`useAppSelector`, `useAppDispatch`). The lint refuses the plain `react-redux` hooks.
- **Put state in the smallest place that works.** Form drafts and open/closed toggles live in component state. A slice is for state that several features share.
- **Don't store derived data.** Compute it with a selector; use `createSelector` when it builds new arrays or objects.
- **A form whose inputs depend on each other keeps its draft in a reducer**, tested on its own.

## cSNP-Specific Rules

- **Never hard-code the thresholds, the prediction labels or the pDel values.** Which thresholds and pDel bounds are right (180/380 vs 200/450 Mya, exclusive vs inclusive) is still an open question; show what the API returns.
- **A job's results have their own URL** (`/jobs/:id`), so a reload or a shared link shows the same results.
- **Show the versions the API reports** (PANTHER library, BLAST+, engine) with the results, so a score can be traced to the data behind it.
- **No build details on screen.** No ports, environment variables or commands in anything a user reads, error pages included. Log them with `console.warn` behind `import.meta.env.DEV`.

## TypeScript

- Strict mode, plus `noUnusedLocals`, `noUnusedParameters` and `noFallthroughCasesInSwitch`.
- `import type` for type-only imports (the lint enforces it).
- No `any`, `@ts-ignore` or `as unknown as T` without a comment saying why. Use `unknown` at boundaries and narrow it.
- Prefer `type` to `interface` unless you need declaration merging.
- Unused names are allowed only with a leading underscore (`_event`).

## Tests

- **Tests live in `tests/`, never in `src/`.** Vitest only collects `tests/**/*.test.{ts,tsx}`, so a test left in `src/` shows up as missing rather than running from the wrong place.
- **Test what the user sees and does.** Query by role and label, interact with `user-event`, assert on visible output. No snapshots of every `div`, no asserting on class names.
- **Test reducers and selectors directly**, without rendering.
- **Mock at the API boundary**, not deep inside components.
- **Keep a success test beside every test of a failure state.** A test that expects an error message also passes when every request fails for some other reason. One did, before `tests/setup.ts` made relative URLs work under Vitest.
- **Tests run with reduced motion.** `tests/setup.ts` reports reduced motion to every `matchMedia` query, so Mantine transitions take no time and can't fire after a test has finished.
- **In tests, import `RouterProvider` from `react-router`, not `react-router/dom`.** Under Vitest, `react-router/dom` loads React Router's CommonJS build, which doesn't share context with the ESM build that `Outlet` and `Link` use. The layout renders, but `<Outlet />` stays empty, with no error. `tests/utils/render.tsx` already does this; `src/main.tsx` keeps `react-router/dom`, which is right in the browser.

### End-to-end

- **Run against a built app served statically**, not the Vite dev server. The dev server compiles modules on first request, and that makes specs flaky under load.
- **Two projects: desktop and mobile**, because layouts differ by width.
- **Assert on behaviour, not on copy.** Wording changes; rules don't.
- **Don't wait for `networkidle`.** Wait for the element you need.
- **Files a spec imports from `src/`, such as mock data, import each other with relative paths.** Playwright doesn't resolve the `@/` alias.

## Lint and Format

- ESLint 9 flat config: `@eslint/js`, `typescript-eslint`, `eslint-plugin-react`, `react-hooks` (recommended-latest), `jsx-a11y`, then `eslint-config-prettier` last.
- Prettier owns layout: no semicolons, single quotes, `printWidth` 100, `arrowParens: "avoid"`, `trailingComma: "es5"`, LF line endings, `prettier-plugin-tailwindcss` to sort classes.
- Don't fight the formatter, and don't reformat files you aren't otherwise changing.

## Anti-patterns

- Fetching in leaf components; fetch once higher up and pass data down.
- One giant `App.tsx` or page component.
- Redux for transient UI, or component state for something several features need.
- Reaching into another feature's internals.
- `useMemo` on a module-level constant.
- Adding a UI library, CSS-in-JS or CSS Modules.
