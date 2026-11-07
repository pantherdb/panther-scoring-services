# Spec Delta

## ADDED Requirements

### Requirement: Images build behind a TLS-inspecting proxy

The engine and API images SHALL build where HTTPS goes through a proxy that re-signs it with its own certificate authority, when the build is given that CA as the optional build secret `ca`, a PEM file of one or more certificates. Each build step that downloads over HTTPS MUST trust those certificates in addition to its usual roots, and MUST keep verifying certificates. The certificates MUST NOT remain in either image.

#### Scenario: Behind the proxy, with its CA

- **WHEN** the engine and API images are built behind a TLS-inspecting proxy, with the proxy's CA given as `ca`
- **THEN** both builds succeed; `panther-engine tools` in the engine image reports `blastp` 2.17.0, `hmmscan` and `hmmsearch` 3.4 and `epa-ng` 0.3.8, and the API image's `GET /api/v1/versions` reports the same versions

#### Scenario: Behind the proxy, without its CA

- **WHEN** the API image is built behind the same proxy without `ca`
- **THEN** the build fails at its first HTTPS download with a certificate verification error, and nothing is installed from an unverified connection

#### Scenario: Nothing of the CA in the images

- **WHEN** the engine and API images have been built with `ca`
- **THEN** no file in either image contains the CA's certificate, neither image sets an environment variable naming a CA bundle, and neither image's history contains the certificate

#### Scenario: Not a certificate

- **WHEN** an image is built with an `ca` file that holds no PEM certificate
- **THEN** the build fails at its first step that downloads over HTTPS, with a message saying that `ca` holds no PEM certificate

### Requirement: Images build unchanged without an extra CA

Without the `ca` secret, the engine and API images SHALL build as they did before it existed: no build step MUST set a CA bundle, and each download MUST use its tool's own roots.

#### Scenario: Without the secret

- **WHEN** the engine and API images are built without `ca`, as CI builds them on `linux/amd64` and `linux/arm64`
- **THEN** no build step is given a CA bundle, both builds succeed, and each image reports the pinned tool versions
