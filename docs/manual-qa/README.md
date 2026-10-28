# Manual QA

Step-by-step checklists that a person (not necessarily a developer) follows in the browser to confirm the scoring UI works. The format follows noctua VPE's `docs/manual-qa/`.

## What Goes Here

- One numbered checklist per area: `01-single-substitution.md`, `02-batch-input.md`, and so on.
- `00-results-sheet.md`: where testers record Pass or Fail for each run.

## How to Write a Checklist

- Label each test case **TC n.m** (for example **TC 1.3**), so failures can be reported by number.
- Write one checkbox per step, each with something the tester can see on screen.
- End each test case with **Pass / Fail** and a **Notes** line.
- Keep each checklist to one 5–15 minute session.

## Areas to Cover

- Single sequence with one substitution
- Batch input (several substitutions)
- Species filter
- Invalid input: bad amino acid, position outside the protein, wrong wild-type
- Results table and CSV export
- Same input on the legacy site and the new UI: do the results match?
