# Hosting

**Status:** Proposed, 2026-10-30.

## Proposal

The frontend is published to GitHub Pages as static files. The API runs on a server of ours, reachable over HTTPS at a public hostname, and the frontend calls it there.

```text
Browser ──> GitHub Pages: the built frontend, static files only
   │
   └──> https://<API hostname>/api/v1 ──> HTTPS front end on our server
                                            └──> the api image
                                                   └── the full cSNP data, read-only
```

## Why

- **GitHub Pages fits the frontend.** The frontend builds to static files, and Pages serves them free for a public repository, deployed from CI. There's no server to run for it.
- **The API needs a real machine.** It runs BLAST+ in worker processes, and reads the full cSNP data (about 20 GB), and later the PANTHER 19 data for the other services. A static host can't run it.

## What the Server Provides

These are requirements, not instructions. The server already runs other things, so how each is met is the engine developer's call.

- **HTTPS at a public hostname.** The Pages site is HTTPS, and browsers block an HTTPS page's calls to an HTTP API (mixed content).
- **The API isn't exposed directly.** Requests reach it only through the HTTPS front end.
- **Nothing else on the server is disturbed:** no clash with its ports, its users or its resources.
- **The `api` image, run with Docker.** It restarts on its own, with `PANTHER_API_JOB_WORKERS` set for the machine. Each running job uses one worker process.
- **The full cSNP data,** mounted read-only, with `PANTHER_DATA_DIR` naming it ([engine.md, "Using the Full Library"](../testing/engine.md#using-the-full-library)).
- **A way to see that it's up:** `GET /api/v1/health`, and the API's logs.

### Options for the HTTPS Front End

- **A reverse proxy the server already runs,** given a new hostname or path for the API. If there is one, this is likely the simplest.
- **A new reverse proxy:** Caddy, which gets and renews certificates on its own, or nginx with certbot.

A hostname of its own and a path on an existing hostname both work. The frontend's API URL is set when it's built, so it can include a path.

## What the Frontend and API Need

These are tracked as an OpenSpec change, separate from the server work. The two meet at the API's hostname.

- **Frontend:**
  - the API's URL, set at build time (today it calls `/api/v1` on its own origin);
  - Vite's base path, if the site is a project page under `/panther-scoring-services/`;
  - a `404.html` fallback, so that a link such as `/jobs/<id>` survives a reload;
  - a workflow that builds the site and deploys it to Pages, never in mock mode.
- **API:** CORS allowing the Pages origin, as a setting.

## Getting the Image to the Server

- **For now:** built on the server from a tagged commit of `main` (`docker build --target api`).
- **Later:** CI publishes the image to GitHub's container registry, and the server pulls a tag. That keeps the image the server runs the same as the one CI tested.

## A Public API

- **Running jobs are bounded** by the number of workers, but waiting jobs aren't: they queue in memory. Options are a cap on waiting jobs in the API, a rate limit at the front end, or both.
- **Jobs are kept in memory,** so a restart loses them, and their links stop working. That's the current design (`scoring-jobs`); whether it's acceptable for a public site needs team verification.

## Records

Deployments are recorded in `docs/deployment/`: a `runbook-deploy.md` and a dated record for each deployment, as [its README](../deployment/README.md) says. This repository is public, so they hold no secrets, IP addresses or private hostnames.

## Open Questions

Each needs team verification.

- **The API's public hostname,** and who manages its DNS.
- **The Pages address:** `https://pantherdb.github.io/panther-scoring-services/`, or a custom domain.
- **How the API fits beside what already runs on the server.**
- **Limits for a public API,** as above.
- **When CI should start publishing the image.**

## Review

| Reviewer | Covers | Status |
| -------- | ------ | ------ |
| Engine developer | The server: what it provides, and the HTTPS front end | Pending |
| Frontend developer | GitHub Pages and the frontend's build | Pending |
| API developer | CORS, and the limits for a public API | Pending |
