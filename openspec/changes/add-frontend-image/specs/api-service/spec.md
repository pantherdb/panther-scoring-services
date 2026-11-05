# Spec Delta

## ADDED Requirements

### Requirement: The API image published after each change

After a push to `main` that changes what the API image is built from, and once the API's checks and the API image's checks pass, CI SHALL publish the API image to GitHub's container registry for `linux/amd64`, tagged `main` and with the commit's SHA. A pull request MUST NOT publish.

#### Scenario: A merge that changes the API

- **WHEN** a push to `main` changes `api/` or the engine's source, and the checks pass
- **THEN** `ghcr.io/pantherdb/panther-api:main` and the tag with the push's SHA are that commit's API image

#### Scenario: A merge that doesn't

- **WHEN** a push to `main` changes only `frontend/` or the docs
- **THEN** no API image is published

#### Scenario: A failing check

- **WHEN** the API image's checks fail on `main`
- **THEN** nothing is published, and the `main` tag stays on the last image that passed
