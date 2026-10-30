# Proposal

**Area:** frontend. Outside `frontend/`, it edits `docs/manual-qa/02-csnp-form.md`. It changes nothing in `api/` or `engine/`.

## Why

The cSNP form splits the substitutions box only at whitespace, as the legacy website did, so a pasted `L46P,C130R` is one token, which the form then rejects as not a substitution. Lists copied from papers and spreadsheets are often comma-separated. In review on #20 the engine developer left it to the frontend developer, who decided that commas separate substitutions as well as whitespace (`add-csnp-form`'s proposal, Open Questions, answered 2026-10-30).

A comma can never be part of a valid token (`[A-Z][0-9]+[A-Z]` once upper-cased, `scoring-input`), so no input the form accepted before is read differently, except that one it rejected is now two substitutions. The API takes a list, so nothing the API or the engine sees changes.

## What Changes

- **The substitutions box splits at any run of whitespace and commas,** in the order typed, dropping empty pieces: `"L46P, C130R,,R163C\n"` is `L46P`, `C130R`, `R163C`. No other character separates: `L46P;C130R` is still one token, which the form rejects and names.
- **The form's help text** says "separated by spaces, commas or new lines".
- **Tests:** unit tests for the splitter (commas, mixed separators, repeated commas, a trailing comma, commas with spaces) and a form test that `L46P,C130R` is sent as two substitutions.
- **Docs:** `docs/manual-qa/02-csnp-form.md` gets a step that pastes comma-separated substitutions.

No new dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `scoring-ui`: "cSNP substitutions split on whitespace" is renamed "cSNP substitutions split on whitespace and commas", and its text and scenarios change: commas separate tokens, and a new scenario covers them.

`add-mock-data-banner` also changes `scoring-ui`, at the same time. It only adds requirements, so the two can be archived in either order.

## Impact

- **Frontend code:** `src/features/csnp/substitutions.ts` (the split) and `CsnpForm.tsx` (the help text); tests in `tests/features/csnp/`.
- **API contract:** unchanged. The request's `substitutions` is still a list, and `npm run api:types:check` passes with the committed `schema.d.ts`.
- **Parity with the legacy cSNP service:** the engine's output for a given list doesn't change. The legacy website read `L46P,C130R` as one token and dropped it, since it doesn't match its token rule; this form sends two. That's a difference in how the form reads what's typed, not in a service's output, so no divergence row is proposed: `docs/parity/divergences.md` row 6, about parsing the legacy form's input, was withdrawn because no endpoint parses that input any more.

## Open Questions

- **Is a divergence row needed?** As above, we think not, because the difference is in the form, not in what the engine scores. Needs team verification by the engine developer.
