# Tasks

## 1. The Dockerfile

- [x] 1.1 Add the `extra-ca` stage before `blast`: `FROM scratch AS extra-ca`, and a heredoc `COPY` of `/extra-ca.sh` (design.md, decision 3). Give it a comment covering three things: what the secret is for, the `docker build --secret` command, and that no step that sources the script may set its own `EXIT` trap. Verify that `docker build --target extra-ca .` succeeds with Docker 29, without a `# syntax=` line
- [x] 1.2 Add the secret mount (`mode=0444`) and the script's bind mount to each step in design.md's table, and source the script first:
  - the `blast` and `hmmer` downloads;
  - the `epang` lock install;
  - the two `uv sync` steps in `engine`, and the two in `api`;
  - the `refmap-reference-script` download, which `port-refmap` added.

  Leave the `tools`, `csnp-reference` and `refmap-reference` stages alone. Verify with `git diff Dockerfile`: eight steps gain the mounts, and no other instruction, pin or sha256 changes
- [x] 1.3 Build the default path on this machine (arm64), without the secret: `docker buildx build --load --target engine -t panther-engine:extra-ca-none .`, and the same for `api` (`panther-api:extra-ca-none`). Verify three things (spec, Without the secret):
  - the build log's `+` trace for each changed step shows no `export` of a CA variable;
  - `panther-engine tools` in the engine image reports the pinned versions;
  - the API image, started on a spare port such as 8003 (never 8000), reports them from `GET /api/v1/versions`.

## 2. Behind a Proxy

- [x] 2.1 Stand in for the proxy with mitmproxy. Run `mitmdump` from `mitmproxy/mitmproxy`, pinned by the digest read that day, on `127.0.0.1:8081`. Copy its CA, `~/.mitmproxy/mitmproxy-ca-cert.pem`, into the scratchpad, never into the repository. Then build `api` without the secret, sending the proxy settings as build arguments: `HTTP_PROXY`, `HTTPS_PROXY` and their lower-case forms, `http://host.docker.internal:8081`, with `--no-cache`. Verify that the build fails at its first HTTPS download with a certificate error, and that mitmdump logged the requests (spec, Behind the proxy, without its CA)
- [x] 2.2 Build `engine` and `api` the same way, with `--secret id=extra-ca,src=<the mitmproxy CA>`, tagged `extra-ca-mitm`. Verify that both succeed, and that mitmdump logged requests to NCBI, eddylab.org, conda.anaconda.org, pypi.org and files.pythonhosted.org. Then check the pinned versions in both images, as in 1.3 (spec, Behind the proxy, with its CA)
- [x] 2.3 In both images from 2.2, verify that nothing of the CA is left (spec, Nothing of the CA in the images):
  - searching the filesystem for the CA's second line, outside `/proc` and `/sys`, finds nothing;
  - `docker history --no-trunc` doesn't contain that line;
  - `docker inspect`'s `Config.Env` has none of `CURL_CA_BUNDLE`, `MAMBA_CACERT_PATH` and `SSL_CERT_FILE`;
  - `/tmp/extra-ca.pem` and `/run/extra-ca.sh` don't exist.
- [x] 2.4 Build `api` with `--secret id=extra-ca,src=<a text file with no certificate>`. Verify that it fails at its first download step with "The extra-ca secret holds no PEM certificate" (spec, Not a certificate)
- [ ] 2.5 On the hosting server (Docker 29.9.2, recorded 2026-11-03), behind its real proxy, build with `sudo docker build --target api -t panther-api:<tag> --secret id=ca,src=/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem .`. Verify that the build succeeds, apt steps included, and that the image reports the pinned versions on `GET /api/v1/versions`. The server's developer runs this, and records the result in Notes without the server's hostname (spec, Behind the proxy, with its CA)
- [x] 2.6 Check the `refmap-reference-script` download the same way, each build with `--no-cache` and `--target refmap-reference-script`. Verify four things:
  - through the proxy without the secret, curl fails with a certificate error;
  - through the proxy with `--secret id=ca,src=<the mitmproxy CA>`, the build succeeds, and `sha256sum` reports `map_panther.pl: OK`;
  - with a text file as the secret, it fails with "The ca secret holds no PEM certificate";
  - without the proxy or the secret, it succeeds, and the trace shows no `export` of a CA variable.

## 3. Docs

- [ ] 3.1 In `docs/testing/engine.md`, add "Building Behind a TLS-Inspecting Proxy" after "In the Image". It covers:
  - the symptom: "unable to get local issuer certificate", or uv's `UnknownIssuer`;
  - the secret, and the host bundle to give it: `/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem` on RHEL and Fedora, `/etc/ssl/certs/ca-certificates.crt` on Debian and Ubuntu;
  - that the certificates stay out of the images;
  - not turning verification off;
  - the Docker 23 minimum.

  Verify that the command in it is the one 2.5 ran
- [x] 3.2 Point to that section from `docs/testing/api.md`, after the `docker build --target api` command in "Tests With the Tools and Data". In `docs/design/hosting.md`'s "Getting the Image to the Server", update the CA bullet that #61 added: the root `Dockerfile` takes the CA too, with a link to that section, and both images take it as `--secret id=ca`. Drop the clause of hosting.md's open question that asks whether it should. Point to the section from `docs/parity/golden-setup.md`'s refmap reference too. In `docs/deployment/runbook-server.md`, replace the sentence saying the API image doesn't take the CA yet with one saying it takes the same secret, linking the section. No server hostname. Verify that every link resolves to the heading
- [x] 3.3 From the repository root, run `npx markdownlint-cli2` and `npx openspec validate --all --no-interactive`, and verify both pass

## 4. Integration

- [ ] 4.1 Open the pull request against `main`, from a branch of the current `origin/main`. Verify that CI's `engine-image` and `api-image` jobs pass on both architectures, building without the secret, and that `ci-passed` is green

## Notes

### Next action

The developer commits the branch `feat/build-with-extra-ca` and pushes it. Then 2.5: on the hosting server, check out that branch and build `api` with the secret, using 3.1's command. Then tick 3.1, whose check is that the docs' command is the one 2.5 ran, and open the pull request (4.1).

### Blockers

2.5 needs the branch pushed, the hosting server, and the server's developer to run it. 4.1 needs the developer to commit and open the pull request.

### Progress (2026-11-03, arm64 Mac, Docker 29.0.1)

- **1.1 and 1.2:** the `extra-ca` stage, and the mounts on seven steps. `git diff Dockerfile` changes no pin or sha256.
- **The script tests `-e`, not `-s`,** unlike the first draft of design.md (now updated). Without `--secret` the file is absent, and with an empty file it's there with size 0. So `-e` makes an empty secret fail with the PEM message, as the spec's Not a certificate scenario asks.
- **1.3:** without the secret, the engine and API images built. The script's trace in each step that ran stopped at the existence check, with no `export`. Both images report blastp 2.17.0, hmmscan and hmmsearch 3.4, and epa-ng 0.3.8; the API was checked on port 8003.
- **2.1:** mitmproxy 12.3.1 (`mitmproxy/mitmproxy@sha256:2711066c855659b5af8b1dbb84494ed3eff69b42ece439c60b4fe09a2db829d4`), run with `mitmdump --set flow_detail=1` on `127.0.0.1:8081`. The proxy build arguments were `http://host.docker.internal:8081`. Without the secret, `api` failed at `epang` with "unable to get local issuer certificate", the error the hosting server shows. mitmdump logged apt's plain-HTTP requests passing through, and a failed TLS handshake for conda.anaconda.org.
- **2.2:** with the mitmproxy CA as the secret and `--no-cache`, both images built through the proxy, with no failed handshake. mitmdump intercepted GETs to `files.pythonhosted.org` (61), `conda.anaconda.org` (14), `ftp.ncbi.nlm.nih.gov` and `www.ncbi.nlm.nih.gov` (2 each), and `eddylab.org` (2). Both images report the pinned versions.
  - **No request went to pypi.org, though the task listed it.** With `--locked`, uv downloads from the file URLs in `uv.lock`, on files.pythonhosted.org, and never reads the index.
- **2.3:** the CA's second line wasn't found in any image file outside `/proc` and `/sys`: 15,366 files in the engine image and 7,212 in the API image. A control run, with the CA mounted, found it. It's not in either image's history or `Config.Env`, and `/tmp/extra-ca.pem`, `/run/extra-ca.sh` and `/run/secrets/extra-ca` are absent.
- **2.4:** with `--no-cache`, a text file and an empty file each failed `api` with "The extra-ca secret holds no PEM certificate", in all three first download steps (`blast`, `hmmer` and `epang` run in parallel).
- **3.1 to 3.3:** the docs section and its two pointers. `npx markdownlint-cli2` reports no issues, and `npx openspec validate --all --no-interactive` passes 14 of 14, with two old warnings in `scoring-ui`. 3.1 stays open until 2.5 has run its command.

### Progress (2026-11-05, after #61)

- **#61 merged a bullet into hosting.md** on building with the server's CA, and gave `frontend/Dockerfile` an optional build secret named `ca`. 3.2's sentence on hosting.md's "For now" line would have repeated it, so it's gone. Instead, that bullet now says the root `Dockerfile` takes the CA too, and the open question no longer asks whether it should.
- **The secret is renamed from `extra-ca` to `ca`,** so both images take the same secret (agreed in the approval of #61). Renamed: the seven mounts, `/run/secrets/ca`, the error message ("The ca secret holds no PEM certificate"), engine.md, and the proposal, design and spec. The stage, `/extra-ca.sh` and `/tmp/extra-ca.pem` keep their names, as does this change. 1.3 and 2.2 to 2.4 ran with `id=extra-ca`, as written above; 2.5 runs with `id=ca`, so it tests the rename.
- **2.4 again, with `id=ca` (arm64 Mac, Docker 29.9.2):** `docker build --no-cache --target blast --secret id=ca,src=<a text file> .` failed in `blast`'s download step with "The ca secret holds no PEM certificate".

### Progress (2026-11-06, set aside for `port-refmap`)

- **This change's uncommitted edits are in `working-tree.patch`,** in this folder, so `port-refmap` could be committed and reviewed alone. The engine developer made `port-refmap` the priority. The edits were taken out of the working copy: the `Dockerfile`, `docs/design/hosting.md`, `docs/testing/api.md` and `docs/testing/engine.md` are as `port-refmap` leaves them. The patch is a diff against that state, and restores those four files, and `docs/parity/golden-setup.md`, byte for byte (checked with `git apply` on a copy).
- **The patch has two more things than this change had:**
  - **an eighth mount,** on `port-refmap`'s new `refmap-reference-script` stage, which downloads `map_panther.pl` with curl. Update the "seven steps" in the proposal, design and Notes when this resumes;
  - **a pointer from `docs/parity/golden-setup.md`'s refmap section** to "Building Behind a TLS-Inspecting Proxy".
- **The patch applies only on top of `port-refmap`.** If this change goes first after all, apply it to a checkout of the `port-refmap` branch, or apply the hunks by hand.

### Progress (2026-11-06, resumed after #63)

- **Restored.** `port-refmap` merged (#63). The branch `feat/build-with-extra-ca` was made from `origin/main` at `3f65ba3`. `working-tree.patch` applied cleanly there, and was deleted. The Dockerfile has eight secret mounts.
- **2.6, the eighth step, `refmap-reference-script` (arm64 Mac, Docker 29.9.2):** through mitmproxy without the secret, curl failed with "(60) SSL certificate problem: unable to get local issuer certificate", and mitmdump logged the refused handshake for raw.githubusercontent.com. With the mitmproxy CA as `ca`, mitmdump intercepted the GET, and the build passed with `map_panther.pl: OK`. A text file as the secret failed with "The ca secret holds no PEM certificate". Without the proxy or the secret, the build passed with no `export` in the trace.
- **The steps are counted as eight now** in the proposal, design and tasks, and design.md's table has the `refmap-reference-script` row.
- **`docs/deployment/runbook-server.md`,** from #61, said the API image doesn't take the CA yet. It now says the API image takes the same secret, with a link to the engine.md section, which now names `refmap-reference` and `map_panther.pl` too.

### Failed approaches

- **`mitmdump --set flow_detail=0` (2026-11-03)** printed no requests, so the first run of 2.1 had no proxy log to check. `flow_detail=1` prints one line per request. mitmproxy's CA folder is now mounted from the scratchpad, so the CA stays the same across restarts.

### Lessons learned

- **A step reused from the build cache doesn't read the secret.** A wrong or missing secret is noticed only by steps that run. Test the secret with `--no-cache` (2.1, 2.2, 2.4). The docs say this too.
- **mitmproxy is a good stand-in for a TLS-inspecting proxy.** Its error is the one the hosting server shows, and its log names each host the build contacts.

- **A build secret is readable only by root by default.** The `uv sync` steps run as `panther`, so the mount needs `mode=0444` (checked 2026-11-03).
- **Each tool takes its CA from a different variable, and most replace their roots.** curl reads `CURL_CA_BUNDLE`, micromamba 2.10.0 `MAMBA_CACERT_PATH`, and uv 0.13.6 `SSL_CERT_FILE`. micromamba ignores `REQUESTS_CA_BUNDLE` and `SSL_CERT_FILE`. uv 0.13.6 has `--system-certs`, not `--native-tls`.
