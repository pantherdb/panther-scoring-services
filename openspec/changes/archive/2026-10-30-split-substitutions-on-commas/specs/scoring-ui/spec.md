# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: cSNP substitutions split on whitespace`
- TO: `### Requirement: cSNP substitutions split on whitespace and commas`

## MODIFIED Requirements

### Requirement: cSNP substitutions split on whitespace and commas

The UI SHALL split the substitutions box into the request's list of tokens at every run of whitespace and commas, spaces, tabs, new lines and commas alike and in any mix, in the order typed, dropping empty tokens. It MUST NOT split at any other character.

#### Scenario: Spaces, tabs and new lines

- **WHEN** the substitutions box holds `" L46P  C130R\tR163C\r\nR176C\n"`
- **THEN** the request's `substitutions` is `["L46P", "C130R", "R163C", "R176C"]`

#### Scenario: Commas

- **WHEN** the substitutions box holds `"L46P,C130R"`, or `"L46P, C130R,,R163C\n"`
- **THEN** the request's `substitutions` is `["L46P", "C130R"]`, or `["L46P", "C130R", "R163C"]`

#### Scenario: Other separators are part of a token

- **WHEN** the substitutions box holds `"L46P;C130R"`
- **THEN** the request's `substitutions` is `["L46P;C130R"]`
