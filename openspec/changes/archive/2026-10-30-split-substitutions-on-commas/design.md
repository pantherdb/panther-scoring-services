# Design

## Context

This change relies on these decisions and doesn't repeat them:

- **The cSNP form, its client checks and where splitting lives:** the archived [add-csnp-form design](../archive/2026-10-29-add-csnp-form/design.md), "Layout" and "Splitting the substitutions". Splitting is one function, `splitSubstitutions` in `src/features/csnp/substitutions.ts`; the checks then run on its list.
- **The token rule** (`[A-Z][0-9]+[A-Z]` once upper-cased): `openspec/specs/scoring-input/spec.md`, "cSNP substitutions are a list of tokens".

The behaviour is in [specs/scoring-ui/spec.md](specs/scoring-ui/spec.md).

## Goals / Non-Goals

**Goals:**

- A comma-separated list, with or without spaces, is read as the user meant it.

**Non-Goals:**

- Other separators, such as `;`, `|` or `+`. None was asked for, and each stays part of a token, so the form names it as not a substitution instead of guessing.
- Changing the checks. A token with a comma in it can't come out of the splitter any more, but `checkSubstitutions` still rejects one, since its tests check the rule, not the splitter.

## Decisions

### Split at `/[\s,]+/`, then drop empty pieces

`text.split(/[\s,]+/).filter(token => token !== '')`. One pattern for whitespace and commas in any mix, so `", "`, `",,"` and `",\n"` each separate once, and the filter drops the empty piece a leading or trailing separator leaves.

- **`\s`** is JavaScript's whitespace, as before: spaces, tabs, new lines and the other Unicode spaces.
- **Alternative:** split at commas first, then at whitespace. Two passes for the same result.

## Risks / Trade-offs

- **[A comma inside something that isn't a substitution]** → `L46P,XYZ` becomes `L46P` and `XYZ`, and the form names `XYZ` as substitution 2. Before, it named the whole `L46P,XYZ`. Either way nothing is sent.
