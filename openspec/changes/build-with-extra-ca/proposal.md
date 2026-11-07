# Proposal

**Area:** cross-cutting. The root `Dockerfile` is shared, and the change touches the stages that both the engine and the API images are built from. The docs change in `docs/testing/`, `docs/parity/golden-setup.md`, `docs/deployment/runbook-server.md` and `docs/design/hosting.md`. No code in `engine/`, `api/` or `frontend/` changes.

## Why

The server chosen for the API ([hosting.md](../../../docs/design/hosting.md), #34) reaches the internet through a TLS-inspecting proxy, which re-signs every HTTPS connection with its own certificate authority. IT installed that CA on the server, so the server's own tools and `docker pull` work. The build steps don't. Each runs in a fresh container that trusts only Debian's roots (curl) or the roots its tool bundles (uv, micromamba). So `docker build --target api` fails at its first HTTPS download, EPA-ng's micromamba step, with "unable to get local issuer certificate".

On 2026-11-03 the image was built on another machine and copied over. That works, but has to be repeated for every release.

## What Changes

- **An optional build secret, `ca`:** a PEM file of one or more CA certificates, given with `docker build --secret id=ca,src=<file>`. Every build step that downloads over HTTPS trusts those certificates as well as its usual roots:
  - curl, for BLAST+ and HMMER, and for `map_panther.pl` in the test-only `refmap-reference-script` stage;
  - micromamba, for EPA-ng;
  - uv, for the engine's and the API's Python packages.
- **Nothing of it stays in the images.** The certificates are read during each step and never written to a layer, to an environment variable the image keeps, or to the image's history. An image built with the secret holds the same files as one built without it.
- **Without the secret, the build is unchanged.** Each tool uses its own roots, as today, and CI doesn't pass the secret.
- **TLS verification stays on, and every pin is still checked.** The secret only adds trusted CAs. Nothing turns verification off. The base image digests and every download's sha256 are checked as before.
- **A secret that holds no PEM certificate fails the build,** with a message naming `ca`, instead of a certificate error later.
- **Docs:** a section in `docs/testing/engine.md` on building behind such a proxy. Pointers to it from `docs/testing/api.md`'s image build and `docs/parity/golden-setup.md`'s refmap reference. hosting.md's "Getting the Image to the Server" and `docs/deployment/runbook-server.md` stop saying the root `Dockerfile` doesn't take the CA.

Not in this change:

- **`compose.yaml`.** `docker compose build` doesn't pass the secret. No developer machine is known to need it (open question).
- **apt.** The Debian images fetch packages over plain HTTP, which a CA doesn't affect.
- **Publishing the image from CI** to GitHub's container registry, hosting.md's "Later". The server would then pull images instead of building them, so it wouldn't need this. But that's a bigger change, with a registry, credentials and a release workflow.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `engine-core`: two new requirements. The engine and API images build behind a TLS-inspecting proxy when given its CA; without one, they build as before.

## Impact

- **Code:** the root `Dockerfile` only:
  - a small stage holding one shared setup script;
  - a secret mount on each of the eight steps that download over HTTPS: the `blast`, `hmmer`, `epang` and `refmap-reference-script` stages' downloads, and the two `uv sync` steps in each of `engine` and `api`.
- **Behaviour:** none without the secret. The changed steps' instructions change, so the first build after the change can't reuse cached layers for them.
- **CI:** no workflow change. The `engine-image` and `api-image` jobs build without the secret, which covers the default path on both architectures.
- **Dependencies:** none. `RUN --mount` and a heredoc in `COPY` need BuildKit's Dockerfile 1.4 syntax, which Docker 23 and later have by default.
- **Parity with the reference:** not affected. The images hold the same tools from the same pinned downloads, checked against the same sha256s. No divergence row is needed.

## Open Questions

Each needs team verification:

- **Whether apt works through the server's proxy.** The failed build was cancelled before its apt steps finished. apt uses plain HTTP, so it should, but the first build with the secret will show it.
- **Whether developers need the secret in compose.** If a developer machine sits behind such a proxy, `compose.yaml` can pass the secret too. None is known to.
- **Whether to keep this once CI publishes images.** When the server pulls images from GitHub's registry (hosting.md, "Later"), it no longer builds them, and only developers behind a proxy would use the secret.

Answered:

- **The server's Docker version:** 29.9.2 (the server's developer, 2026-11-03). The secret mount and the heredoc need 23 or later.
