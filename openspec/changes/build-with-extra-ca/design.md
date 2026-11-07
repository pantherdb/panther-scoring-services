# Design

## Context

The image is the pin ([tech-stack.md, Pinning Tool Versions](../../../docs/design/tech-stack.md#pinning-tool-versions)). The Dockerfile names each base image by digest, and each download by version and sha256. For now the server builds its own image from a tagged commit ([hosting.md, Getting the Image to the Server](../../../docs/design/hosting.md#getting-the-image-to-the-server)). This change keeps both decisions as they are, and lets that build run behind a TLS-inspecting proxy (proposal.md, Why).

These steps download over HTTPS:

| Stage | Step | Tool | Runs as |
| ----- | ---- | ---- | ------- |
| `blast` | BLAST+ tarball, from NCBI | curl | root |
| `hmmer` | HMMER source, from eddylab.org | curl | root |
| `epang` | EPA-ng's explicit lock, from conda.anaconda.org | micromamba 2.10.0 | root |
| `engine` | `uv sync`, twice, from PyPI | uv 0.13.6 | `panther` (uid 1000) |
| `api` | `uv sync`, twice, from PyPI | uv 0.13.6 | `panther` (uid 1000) |
| `refmap-reference-script` | `map_panther.pl`, from raw.githubusercontent.com (test-only, added by `port-refmap`) | curl | root |

The other steps either use apt over plain HTTP (`tools`, `csnp-reference`, `refmap-reference`, and the first half of `blast`, `hmmer` and `refmap-reference-script`) or copy files. The Docker daemon pulls the base images itself, and trusts what the server trusts.

The findings below were checked on 2026-11-03, against the pinned images on an arm64 Mac with Docker 29.0.1.

## Goals / Non-Goals

**Goals:**

- The same Dockerfile builds the same images with or without the proxy, and the proxy's CA appears in neither.
- One definition of the CA setup, used by every step in the table.

**Non-Goals:**

- Proxy settings such as `HTTPS_PROXY`. The server's proxy looks transparent: the failed build reached it without any proxy settings. A proxy that does need them is already covered, since Docker passes its proxy build arguments through to every step.
- A CI job that builds through a proxy. CI covers the default path; the proxy path is checked by hand (tasks 2.2 to 2.4).

## Decisions

### 1. The CA arrives as a BuildKit secret

`docker build --secret id=ca,src=<pem file>`, mounted in each step with `--mount=type=secret,id=ca,mode=0444`. A secret is optional by default: without `--secret`, the mount is skipped and the file is absent. BuildKit keeps secrets out of layers, cache keys, the image history and provenance. The certificate isn't secret, but this is the mount that doesn't persist.

- **`mode=0444`:** a secret is mounted readable by root alone, so the `uv sync` steps, which run as `panther`, couldn't read it.
- **Caching:** a step's output doesn't depend on the CA, since it holds the same downloads with the same sha256s. So BuildKit can share cached layers between builds with and without the secret.
- **Rejected: a build argument.** Its value is recorded in the image's history, and a PEM file is several lines long.
- **Rejected: a named build context** (`--build-context extra-ca=<folder>` over an empty default stage). It works, but the folder's contents enter the cache keys and the provenance record, and the default build would mount it too.
- **Rejected: building the bundle in a stage of its own,** for the steps to copy or mount. A secret isn't part of a cache key, so that stage's layer would be reused even after the CA changes.

### 2. Each step makes a combined bundle, and points its tool at it

When the secret is present, the step writes `/tmp/extra-ca.pem`: the image's Debian roots (`/etc/ssl/certs/ca-certificates.crt`, in both base images) followed by the secret's certificates. It exports one variable per tool, and removes the file when the step's shell exits. Each variable was checked by pointing it at a bundle holding one unrelated root: a variable the tool honours must then make the download fail.

| Tool | Variable | Checked |
| ---- | -------- | ------- |
| curl 8.14.1 (Debian) | `CURL_CA_BUNDLE` | `curl -v` reports it as the `CAfile` |
| micromamba 2.10.0 | `MAMBA_CACERT_PATH` | The lock install fails with the one-root bundle, and succeeds with the combined one. `REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE` are ignored |
| uv 0.13.6 | `SSL_CERT_FILE` | `uv pip compile` fails with `UnknownIssuer`, and succeeds with the combined one |

- **Why combined:** uv's and micromamba's settings replace their roots instead of adding to them, so the bundle has to hold the usual roots too. Debian's curl also still reads `/etc/ssl/certs` as its `CApath`. A combined bundle is right for all three, whatever each does by default.
- **Without the secret, nothing is set,** so each tool keeps its own defaults, as before. uv keeps its bundled Mozilla roots.
- **Rejected: adding the CA to the system store** with `update-ca-certificates`. In `engine` and `api` that writes it into the final image's `/etc/ssl`. And uv and micromamba don't read the system store unless told to.
- **Rejected: `UV_SYSTEM_CERTS=1`.** It reads the container's store, which doesn't have the CA.
- **Rejected: turning verification off** for the proxy's hosts (`--ssl-verify false`, `UV_INSECURE_HOST`, `curl -k`). The sha256 pins would still catch a changed download, but uv's index pages and micromamba's channel requests would be unverified, and the build would never notice a proxy it wasn't told about.

### 3. One script, in a heredoc stage, mounted into each step

```dockerfile
FROM scratch AS extra-ca
COPY <<'EOF' /extra-ca.sh
if [ -e /run/secrets/ca ]; then
    grep -q -e '-----BEGIN CERTIFICATE-----' /run/secrets/ca \
        || { echo "The ca secret holds no PEM certificate" >&2; exit 1; }
    cat /etc/ssl/certs/ca-certificates.crt /run/secrets/ca > /tmp/extra-ca.pem
    export CURL_CA_BUNDLE=/tmp/extra-ca.pem MAMBA_CACERT_PATH=/tmp/extra-ca.pem SSL_CERT_FILE=/tmp/extra-ca.pem
    trap 'rm -f /tmp/extra-ca.pem' EXIT
fi
EOF
```

Each step in the table then starts:

```dockerfile
RUN --mount=type=secret,id=ca,mode=0444 \
    --mount=type=bind,from=extra-ca,source=/extra-ca.sh,target=/run/extra-ca.sh \
    set -eux; . /run/extra-ca.sh; \
    ...
```

- **One definition** instead of the same lines in eight steps.
- **A bind mount, not a `COPY`,** so the script is in no layer. Checked: after a step with both mounts, the next step finds nothing in `/tmp` or `/run`, and `SSL_CERT_FILE` is unset.
- **A heredoc, not a file in the build context.** `.dockerignore` sends only `engine/` and `api/`, and the script belongs with the Dockerfile.
- **No `# syntax=` line.** Docker 23 and later have heredocs in their built-in frontend. A `# syntax=` line would pull an unpinned frontend image at every build.
- **A non-PEM secret fails early,** in the step that would first use it, with a message naming `ca`. `grep` is in both base images. The check is a plain text test, so a DER certificate fails it too. That's the intent: the tools read PEM only. The script tests that the file exists (`-e`), not that it's non-empty (`-s`), so an empty file fails as well. Without `--secret` the file is absent, and with an empty one it's there with size 0 (checked 2026-11-03).
- **`epang` runs its steps through the micromamba image's wrapper,** `_dockerfile_shell.sh`, which runs them with `bash -c`. Sourcing the script and its `EXIT` trap work the same there.

## Risks / Trade-offs

- **[Risk] The first build after the change re-runs every changed step,** because their instructions change. → This happens once per machine.
- **[Risk] A machine with Docker older than 23.** → The build fails on the heredoc with a syntax error, rather than building something different. The hosting server has 29.9.2 (2026-11-03).
- **[Trade-off] The proxy sees the build's traffic in the clear.** → That's the network's policy, not the build's. The sha256 pins in the Dockerfile and in `engine/tools-env/`, and the hashes in both `uv.lock` files, still reject any changed download.
- **[Risk] A wrong file, such as the CA's key or a DER certificate.** → The PEM check fails the build at once. A PEM file with the wrong CA fails as it does today, with the tool's certificate error.
- **[Risk] A step that later adds its own `EXIT` trap would replace the script's.** → No step has one. The Dockerfile comment on the stage says so.

## Migration Plan

Nothing to migrate. Builds without the secret are unchanged, including CI's. Roll back by reverting. A build on the server would then need the image built elsewhere again, as on 2026-11-03.
