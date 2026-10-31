# Spec Delta

## MODIFIED Requirements

### Requirement: Validation errors list the failing fields

When a request fails input validation, the API SHALL respond with status 422 and a problem-details body with an `errors` array. Each item MUST give the field's location (`loc`), a message (`msg`) and an error type (`type`). The body MUST NOT echo the submitted values. The `errors` array MUST list at most the first 100 field errors, in the order validation found them. When there are more than 100, the `detail` MUST say how many fields failed in all.

#### Scenario: Invalid input

- **WHEN** a client sends a request whose body fails validation on one field
- **THEN** the API responds with status 422 and a problem-details body whose `errors` array has one item, with that field's `loc`, a `msg` and a `type`

#### Scenario: Submitted values are not echoed

- **WHEN** a client sends a request that fails validation and contains a distinctive value
- **THEN** the response body does not contain that value

#### Scenario: At most 100 errors

- **WHEN** a client sends a refmap request whose `ids` are 100,000 empty strings
- **THEN** the API responds with status 422, the `errors` array has 100 items, the errors on `ids` items 0 to 99, each with its `loc`, and the `detail` says that 100,000 fields are invalid and the first 100 are listed

#### Scenario: Up to 100 errors are all listed

- **WHEN** a client sends a request with 100 or fewer invalid fields
- **THEN** the `errors` array lists every one, and the `detail` is "Request validation failed"
