# The engine and API images: Python, uv and the external tools at pinned versions, for linux/amd64
# and linux/arm64. Stages: blast, hmmer, epang -> tools -> engine, api; and the test-only
# csnp-reference, refmap-reference and hmmscore-reference, from engine, with
# refmap-reference-script and hmmer-3.1b2.
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
# and uv. uv uses the base image's Python 3.13 and never downloads one. BLAST+ sends NCBI no usage
# reports, even when run by hand; the engine's run_tool sets the same variable for every tool.
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
    UV_PYTHON_DOWNLOADS=never \
    BLAST_USAGE_REPORT=false
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

# The cSNP reference, for parity tests only (Engine condition 3 in docs/design/tech-stack.md): the
# engine with Debian's Perl and the legacy scripts at the parity reference, pantherdb/cSNP_analysis
# at cebb5ab. That repository is private, so the scripts come from the named build context
# csnp-reference-scripts, a `git archive cebb5ab` of a developer's checkout. The commands are in
# docs/parity/golden-setup.md. Building `engine` or `api` never needs the context, and CI and
# compose never build this stage.
FROM engine AS csnp-reference
USER root
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends perl; \
    rm -rf /var/lib/apt/lists/*
COPY --from=csnp-reference-scripts run_blastp.pl parse_blastp.pl PANTHER_PSEP1.01.pl \
    /opt/csnp-reference/
# sha256 of each script at cebb5ab, computed on 2026-10-29. A script that differs fails the build,
# naming the file.
RUN set -eux; \
    cd /opt/csnp-reference; \
    printf '%s  %s\n' \
        5368a43cfc1865b33010ce7ff390107947dab678f848605e865a47828df6d0c5 run_blastp.pl \
        e19ecf1a4ad4037a147d1913c649df01e1ee9ea147d7aa451caca2e1179030e4 parse_blastp.pl \
        b931ff6688b3ce7e345a9ab872537c859296a01aa8835d3b529b4aa0b27e1735 PANTHER_PSEP1.01.pl \
        | sha256sum --check --strict; \
    perl -v | sed -n 2p
USER panther
# parse_blastp.pl's `sort` compares whole lines when percent identities tie: byte by byte, in C.
ENV LC_ALL=C

# The refmap reference, for parity tests only (Engine condition 3 in docs/design/tech-stack.md): the
# engine with Debian's Perl and RefProteomeMapper's map_panther.pl at the parity reference, 4fc6a09.
# That repository is public, so this stage downloads the script at the full commit and checks its
# sha256. The script is the same file on master (649c85f) and on data.pantherdb.org (checked
# 2026-11-05 and 2026-11-06). A separate stage, so curl stays out of refmap-reference. A script that
# differs fails the build, naming the file. The commands are in docs/parity/golden-setup.md.
# Building `engine` or `api` never runs these stages, and CI and compose never build them.
FROM ${PYTHON_IMAGE} AS refmap-reference-script
ARG REFMAP_COMMIT=4fc6a0953ecf138d9d716ba2641afa4664796a51
ARG REFMAP_SCRIPT_SHA256=ee535a9b935f439be29ae2eafda2c9c953b1abf5f4ab5623bcc7da1746919725
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl; \
    rm -rf /var/lib/apt/lists/*; \
    mkdir /refmap-reference; \
    cd /refmap-reference; \
    curl -fsSL -o map_panther.pl \
        "https://raw.githubusercontent.com/pantherdb/RefProteomeMapper/${REFMAP_COMMIT}/map_panther.pl"; \
    echo "${REFMAP_SCRIPT_SHA256}  map_panther.pl" | sha256sum --check --strict

FROM engine AS refmap-reference
USER root
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends perl; \
    rm -rf /var/lib/apt/lists/*; \
    perl -v | sed -n 2p
COPY --from=refmap-reference-script /refmap-reference/map_panther.pl /opt/refmap-reference/
USER panther

# HMMER 3.1b2, production's version, for the hmmscore reference only: Bioconda's build, at the
# digest the survey measured and the 2026-11-13 character measurements used
# (docs/parity/hmmscore-library-survey.md, "HMMER 3.1b2 Against 3.4"). The digest is an amd64
# image alone: 3.1b2 has no arm64 build with vector code. Its tools link only glibc's libc, libm
# and libpthread (checked 2026-11-16), so they run on the engine's Debian.
FROM quay.io/biocontainers/hmmer:3.1b2--3@sha256:e7b1a7a131b7acd6546a6a77cfffc3007fc80f74f7b40b5c660fe29fda122158 AS hmmer-3.1b2

# The hmmscore reference, for parity tests only (Engine condition 3 in docs/design/tech-stack.md):
# the engine with Debian's Perl and YAML::XS, which scoreAlignXml.cgi loads its config.yaml with,
# HMMER 3.1b2's tools in /opt/hmmer-3.1b2/bin, and pantherdb/pantherScoring at 89ea0ae:
# scoreAlignXml.cgi, pantherScore.pl and lib/. That repository is private, so the scripts come from
# the named build context hmmscore-reference-scripts, a `git archive 89ea0ae` of a developer's
# checkout. A file that differs fails the build, naming the file. amd64 only, for HMMER 3.1b2. The
# commands are in docs/parity/golden-setup.md. Building `engine` or `api` never needs the context,
# and CI and compose never build this stage.
FROM engine AS hmmscore-reference
ARG TARGETARCH
USER root
RUN set -eux; \
    if [ "$TARGETARCH" != amd64 ]; then \
        echo "hmmscore-reference is amd64 only: build it with --platform linux/amd64" >&2; \
        exit 1; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends perl libyaml-libyaml-perl; \
    rm -rf /var/lib/apt/lists/*; \
    perl -v | sed -n 2p; \
    perl -MYAML::XS -e 'print "YAML::XS $YAML::XS::VERSION\n"'
COPY --from=hmmer-3.1b2 /usr/local/bin/hmmscan /usr/local/bin/hmmsearch /usr/local/bin/hmmpress \
    /usr/local/bin/hmmconvert /opt/hmmer-3.1b2/bin/
RUN set -eux; \
    for tool in hmmscan hmmsearch hmmpress hmmconvert; do \
        "/opt/hmmer-3.1b2/bin/$tool" -h | sed -n 2p | grep '^# HMMER 3\.1b2 (February 2015)'; \
    done
COPY --from=hmmscore-reference-scripts scoreAlignXml.cgi pantherScore.pl /opt/hmmscore-reference/
COPY --from=hmmscore-reference-scripts lib/ /opt/hmmscore-reference/lib/
# sha256 of each file at 89ea0ae, computed on 2026-11-16 from `git archive`. The folder must hold
# these files and no other.
RUN set -eux; \
    cd /opt/hmmscore-reference; \
    printf '%s  %s\n' \
        1650e00d960d31baa6d9779f0eecd57f6f4db73d5f731281daad7b78c1599159 scoreAlignXml.cgi \
        8cd30712fdd93d9e2c2626073adce51321f4ff008fe49ef28a3edf832ea5902f pantherScore.pl \
        69d03cdc76dd5e518ca0db62bbc6ffb5caea54fbcd560a4cbd6e2908aa6da17b lib/Blast.pm \
        bd9a9b4d83a1347aa57b02705b69fe0d3b31e11821d50b1256f3ee74c0b7f46e lib/FamLibBuilder.pm \
        4468c47b3e06255a95741bc231e1aed1ea9c6b701a64a107ff0d5300fe0b7457 lib/FamLibBuilder_build.pm \
        c19e1d1062a52ce04ed1b8d8b67a0cb2a2633569faa67748a3106deb081ec261 lib/FamLibBuilder_prod.pm \
        ba91faaeb110e746fb3c30b89fc959f7ba95f76d585febeb6ce43dd083daca73 lib/FamLibEntry.pm \
        3fb16f4f6b69377834599a24fbef1716ea85ca206368d99d55a293c480a1c25b lib/FamLibEntry_build.pm \
        bdf9e61ab933585be1f144095c53ee44b958e9dfdc0474d0c2496a4d7cfa5fd2 lib/FamLibEntry_prod.pm \
        12af1e1596b999c7066effb653f2c4e9eba77c18ef42640e0f8ab1a2e6be8567 lib/FastaFile.pm \
        9e85c7124125403b64d6d9c3227262f1d2e5fb8551decebe2e97b4bffd1ee386 lib/Hit.pm \
        cf81d14c3467590a4fa2d6fc6defe1a807bc5e93cb2a381844de79800949444c lib/Hsp.pm \
        > /tmp/hmmscore-reference.sha256; \
    sha256sum --check --strict /tmp/hmmscore-reference.sha256; \
    test "$(find . -type f | sort)" = "$(sed 's/^[0-9a-f]*  /.\//' /tmp/hmmscore-reference.sha256 | sort)"; \
    rm /tmp/hmmscore-reference.sha256; \
    test -x scoreAlignXml.cgi; \
    test -x pantherScore.pl
USER panther

# The API: api/ and the engine installed into /opt/venv as regular packages, without the dev group,
# serving on port 8000. The image runs what it was built from; nothing mounted over /work changes
# it. compose.yaml's `api` service runs it for the frontend to call.
FROM tools AS api
USER root
RUN mkdir -p /opt/venv /work/api /work/engine \
    && chown panther:panther /opt/venv /work/api /work/engine
USER panther
WORKDIR /work/api
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"
# The dependencies first, so a change to the source alone doesn't reinstall them. uv reads the
# engine's pyproject.toml to check the lock, but installs nothing from the engine yet.
COPY --chown=panther:panther api/pyproject.toml api/uv.lock api/.python-version ./
COPY --chown=panther:panther engine/pyproject.toml /work/engine/
RUN uv sync --locked --no-dev --no-cache --no-install-project --no-install-package panther-engine
COPY --chown=panther:panther engine/src/ /work/engine/src/
COPY --chown=panther:panther api/ ./
RUN uv sync --locked --no-dev --no-cache --no-editable
EXPOSE 8000
# fastapi run finds the app through [tool.fastapi] in api/pyproject.toml, and listens on 0.0.0.0.
CMD ["fastapi", "run", "--port", "8000"]
