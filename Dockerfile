# The engine image: Python, uv and the external tools at pinned versions, for linux/amd64 and
# linux/arm64. Stages: blast, hmmer, epang -> tools -> engine.
#
# Every base image is pinned by digest and every download by version and sha256. Changing a pin
# is a pull request that changes this file; Dependabot doesn't update them. The versions are
# decided in docs/design/tech-stack.md ("Pinning Tool Versions").

# Multi-platform index digests, read with `docker buildx imagetools inspect` on 2026-10-29.
ARG PYTHON_IMAGE=python:3.13-slim-trixie@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb
ARG MICROMAMBA_IMAGE=mambaorg/micromamba:2.10.0-debian13-slim@sha256:e1476182cd40eb1f7c0cfae4adec9bfd78f3d7f05c61368306abfdc8939c1198
# Keep the uv version in step with required-version in engine/pyproject.toml and with ci.yml.
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0

# BLAST+: NCBI's prebuilt binaries. We keep blastp and blastdbcmd. They need libgomp1, which the
# slim base lacks (the only library `ldd` reported missing, on both architectures).
FROM ${PYTHON_IMAGE} AS blast
ARG TARGETARCH
ARG BLAST_VERSION=2.17.0
# sha256 of NCBI's tarballs, computed on 2026-10-29 after checking each against the .md5 file
# NCBI publishes beside it, in https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/2.17.0/.
ARG BLAST_SHA256_AMD64=3888112d8207831aa47371d93583c601f058f88b5db22dc782438b039a3a411b
ARG BLAST_SHA256_ARM64=cb9ac252a1ac8767d90b0bf0a38486f3cb94f71ef9b6b8d194ded19b30250daf
RUN set -eux; \
    case "$TARGETARCH" in \
        amd64) arch=x64-linux; sha256="$BLAST_SHA256_AMD64" ;; \
        arm64) arch=aarch64-linux; sha256="$BLAST_SHA256_ARM64" ;; \
        *) echo "No BLAST+ tarball for TARGETARCH '$TARGETARCH'" >&2; exit 1 ;; \
    esac; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl libgomp1; \
    rm -rf /var/lib/apt/lists/*; \
    name="ncbi-blast-${BLAST_VERSION}+"; \
    curl -fsSL -o /tmp/blast.tar.gz \
        "https://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/${BLAST_VERSION}/${name}-${arch}.tar.gz"; \
    echo "${sha256}  /tmp/blast.tar.gz" | sha256sum --check --strict; \
    mkdir -p /opt/tools/blast/bin; \
    tar -xzf /tmp/blast.tar.gz -C /opt/tools/blast/bin --strip-components=2 --no-same-owner \
        "${name}/bin/blastp" "${name}/bin/blastdbcmd"; \
    rm /tmp/blast.tar.gz; \
    /opt/tools/blast/bin/blastp -version

# HMMER: built from source. Bioconda's package pulls in OpenMPI, which we don't use.
FROM ${PYTHON_IMAGE} AS hmmer
ARG HMMER_VERSION=3.4
# sha256 of the source tarball, computed on 2026-10-29. It matches the sha256 in Bioconda's
# hmmer 3.4 recipe (bioconda-recipes, recipes/hmmer/meta.yaml).
ARG HMMER_SHA256=ca70d94fd0cf271bd7063423aabb116d42de533117343a9b27a65c17ff06fbf3
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl gcc libc6-dev make; \
    rm -rf /var/lib/apt/lists/*; \
    curl -fsSL -o /tmp/hmmer.tar.gz \
        "https://eddylab.org/software/hmmer/hmmer-${HMMER_VERSION}.tar.gz"; \
    echo "${HMMER_SHA256}  /tmp/hmmer.tar.gz" | sha256sum --check --strict; \
    mkdir /tmp/hmmer; \
    tar -xzf /tmp/hmmer.tar.gz -C /tmp/hmmer --strip-components=1 --no-same-owner; \
    cd /tmp/hmmer; \
    ./configure --prefix=/opt/tools/hmmer; \
    make -j"$(nproc)"; \
    make install; \
    cd /; \
    rm -rf /tmp/hmmer /tmp/hmmer.tar.gz; \
    /opt/tools/hmmer/bin/hmmscan -h | head -n 2

# EPA-ng: Bioconda's build, from an explicit lock with a sha256 per package. Conda fixes paths at
# install time, so the environment keeps the prefix /opt/tools/conda in the tools stage too.
FROM ${MICROMAMBA_IMAGE} AS epang
ARG TARGETARCH
USER root
COPY engine/tools-env/ /tmp/tools-env/
RUN set -eux; \
    case "$TARGETARCH" in \
        amd64) subdir=linux-64 ;; \
        arm64) subdir=linux-aarch64 ;; \
        *) echo "No EPA-ng lock for TARGETARCH '$TARGETARCH'" >&2; exit 1 ;; \
    esac; \
    micromamba create -y -p /opt/tools/conda -f "/tmp/tools-env/epa-ng-${subdir}.lock"; \
    micromamba clean -a -y; \
    rm -rf /tmp/tools-env; \
    /opt/tools/conda/bin/epa-ng --version

# COPY --from can't take an ARG, so the uv image gets a stage name.
FROM ${UV_IMAGE} AS uv

# The tools image: the Python base, the three tools at the paths their stages installed them to,
# and uv. uv uses the base image's Python 3.13 and never downloads one.
FROM ${PYTHON_IMAGE} AS tools
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends libgomp1; \
    rm -rf /var/lib/apt/lists/*
COPY --from=blast /opt/tools/blast /opt/tools/blast
COPY --from=hmmer /opt/tools/hmmer /opt/tools/hmmer
COPY --from=epang /opt/tools/conda /opt/tools/conda
COPY --from=uv /uv /uvx /usr/local/bin/
ENV PATH="/opt/tools/blast/bin:/opt/tools/hmmer/bin:/opt/tools/conda/bin:${PATH}" \
    UV_PYTHON_DOWNLOADS=never
RUN useradd --create-home --uid 1000 --user-group panther
USER panther

# The engine: engine/ at /work/engine, installed into /opt/venv with its dev group, for the tests
# and the CLI. compose.yaml mounts the working copy over /work/engine. The venv belongs to the
# non-root user, so `uv run` can update it in a container if engine/uv.lock changes.
FROM tools AS engine
USER root
RUN mkdir -p /opt/venv /work/engine && chown panther:panther /opt/venv /work/engine
USER panther
WORKDIR /work/engine
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PANTHER_REQUIRE_TOOLS=1
# The dependencies first, so a change to the source alone doesn't reinstall them.
COPY --chown=panther:panther engine/pyproject.toml engine/uv.lock engine/.python-version ./
RUN uv sync --locked --no-cache --no-install-project
COPY --chown=panther:panther engine/ ./
RUN uv sync --locked --no-cache
