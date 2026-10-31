# Spec Delta

## MODIFIED Requirements

### Requirement: Parity with the reference

The engine's tests SHALL check scoring against golden files made by the reference: spec §7.3 and §7.5, the step-1 output of BLAST+ 2.17.0, the reference image's output for generated cases in every data-sample family, and the reference image's output for the scoring form's example. A difference MUST fail the tests, unless `docs/parity/divergences.md` has an approved row for it.

#### Scenario: The sample's goldens

- **WHEN** the tests run with the data sample
- **THEN** every golden case gives exactly the golden output

#### Scenario: A difference

- **WHEN** one golden row is changed by hand
- **THEN** the tests fail and name that case

#### Scenario: The form's example

- **WHEN** the form's example, the legacy site's human APOE with `L46P`, `C130R`, `R163C` and `R176C` for `HUMAN`, is scored with the data sample
- **THEN** the family is `PTHR18976`, and each substitution's age, message and pDel are exactly the reference image's output for it
