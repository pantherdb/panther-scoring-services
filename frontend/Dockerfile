# The site, built and served with Docker, so a server needs no Node. Build context: frontend/.
# Stages, from one build:
#   build  npm ci and npm run build: the production build, never mock data
#   site   only the built files: `docker build --target site --output type=local,dest=<folder>`
#   web    nginx serving them on port 8080, forwarding /api/ to the API (the default target)
# How the server uses them is in docs/deployment/runbook-server.md.
#
# Base images are pinned by digest, as in the root Dockerfile: changing a pin is a pull request
# that changes this file. Multi-platform index digests, read with `docker buildx imagetools
# inspect` on 2026-11-04.
ARG NODE_IMAGE=node:24.22.2-slim@sha256:c86ecead9e55a5210ac1727de38a4ca840bf03dcaf34dc9749addbf383b1920c
ARG NGINX_IMAGE=nginxinc/nginx-unprivileged:1.30.1-alpine@sha256:acc3239879a65d9e3d250b21847ec3f34f33367017394d22830242af15cf1cb0

# The built files are the same on every platform, so build on the machine's own.
FROM --platform=$BUILDPLATFORM ${NODE_IMAGE} AS build
WORKDIR /work
# The dependencies first, so a change to the source alone doesn't reinstall them.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
# The build settings (docs/testing/frontend.md, "Build Settings"). The defaults serve the site at
# the root of its address, calling the API at /api/v1 on that same address.
ARG BASE_PATH=/
ARG VITE_API_BASE_URL=
# .env.production keeps mocking off. MSW's worker and its start-up both name mockServiceWorker;
# the check is the same as the Pages workflow's.
RUN npm run build \
    && if grep -rli -e mockServiceWorker -e "mock data" dist; then \
        echo "The build contains the API mocking library or the mock data banner." >&2; \
        exit 1; \
    fi

FROM scratch AS site
COPY --from=build /work/dist/ /

# nginx as a user other than root, on port 8080. Its entrypoint fills templates/*.template from
# the environment, replacing only the variables that are set, so nginx's own $host and the like
# stay. API_UPSTREAM is where /api/ goes: compose's api service by default. The site has a folder
# of its own, not nginx's html/ with its sample pages, so copying /srv/site out of the image gives
# exactly the build.
FROM ${NGINX_IMAGE} AS web
ENV API_UPSTREAM=http://api:8000
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /work/dist/ /srv/site/
EXPOSE 8080
