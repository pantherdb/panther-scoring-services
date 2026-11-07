# Runbook: the Frontend on Our Server

How to build the site on the server with Docker, and serve it beside the API at one address, so its calls to `/api/v1` need no CORS. It's an alternative to [GitHub Pages](runbook-pages.md), using the same build. The image is `frontend/Dockerfile`; the change that added it is `add-frontend-image`.

The server needs Docker and a checkout of this repository, but no Node. HTTPS, the hostname and which ports are open are the server's front end, as [hosting.md](../design/hosting.md) says; this runbook covers what runs behind it, and what the front end must pass on.

## Two Ways, One Build

Both run `npm ci` and `npm run build` in a container. The build fails if it contains the API mocking library or the mock data banner (`npm run check:no-mocks`).

| | A: the `web` container | B: the built files |
| --- | --- | --- |
| What runs | nginx in a container, on port 8080, serving the site and forwarding `/api/` to the API | Nothing new: the server's web server serves a folder |
| The server's web server | Forwards the site's address to the container | Serves the folder, and forwards `/api/` to the API itself |
| Updating | Like the API: rebuild the image, restart the container | Build into a new folder, swap it in |
| A path such as `/scoring/` | Only if the front end strips it (below) | Yes |

Pick one. The server keeps working as it does today until someone switches.

## Building on the Server

### The server's CA certificate

The server re-signs TLS, so a download during the build fails unless it trusts the server's CA: `npm ci` stops with `SELF_SIGNED_CERT_IN_CHAIN` or "unable to get local issuer certificate". Node doesn't use the system's certificates, so pass the CA to the build as a secret, on every build command below:

```bash
docker build --secret id=ca,src=<the CA certificate, .pem> ...
```

The certificate is used only by `npm ci`, and isn't kept in the image or its layers. Without the secret, the build is the same as anywhere else.

The API image, from the root `Dockerfile`, doesn't take the CA yet: its downloads fail the same way. That's an open question in [hosting.md](../design/hosting.md#getting-the-image-to-the-server).

### Build settings

The defaults suit a site at the root of its address, with the API at `/api/` on the same address. Change them with `--build-arg` only if that isn't so.

| Build argument | Default | What it sets |
| -------------- | ------- | ------------ |
| `BASE_PATH` | `/` | The path the site is served under, such as `/scoring/` |
| `VITE_API_BASE_URL` | empty: the relative `/api/v1` | The API's URL, without `/api/v1`, if the API is at another address |

More on both in [frontend.md, Build Settings](../testing/frontend.md#build-settings).

## A: The `web` Container

### Put it on the API's network, once

The `web` container finds the API by its container name. Docker resolves names only on a network someone created, not on its default one. If the API container isn't on one yet:

```bash
docker network create panther
docker network connect panther <the API container's name>
```

`docker inspect -f '{{json .NetworkSettings.Networks}}' <the API container's name>` shows the networks it's on: `bridge` alone is the default one. Connecting doesn't restart the API, and its published ports keep working.

### Build and start it

From the repository's root, on the commit to deploy:

```bash
git pull
docker build --secret id=ca,src=<the CA certificate> -t panther-web frontend
docker run -d --name panther-web --restart unless-stopped \
  --network panther \
  -e API_UPSTREAM=http://<the API container's name>:8000 \
  -p 127.0.0.1:<host port>:8080 panther-web
```

- **`API_UPSTREAM`** is the API's address on the network, without a path: `http://api:8000` unless set, the API's service name in `compose.yaml`. The port is the API's inside its container, 8000, whatever port the API has on the server. A trailing slash is dropped.
- **nginx looks the API's name up again** every 10 seconds, so the site keeps working when the API's container is replaced. The API must be running when `panther-web` starts.
- **`<host port>`** is any free port on the server. The container always listens on 8080 inside; only the host side changes, with no rebuild. `127.0.0.1:` makes it reachable from the server alone, so the public reaches the site only through the server's front end.

### What the server's front end needs

- **Forward the site's address to `http://127.0.0.1:<host port>`,** `/api/` included: the container forwards that to the API.
- **A body limit of at least 17 MiB** for it, such as nginx's `client_max_body_size 17m;`. nginx's default is 1 MiB: a larger job, such as a long `refmap` list, would get the front end's own `413` page before it reaches the API's 16 MiB limit and its error message.
- **Its forwarded headers:** the container passes on the `Host` and `X-Forwarded-Proto` it receives, so the API sees the address and the `https` the user used. The front end should set `X-Forwarded-Proto` when it ends HTTPS, as nginx does with `proxy_set_header X-Forwarded-Proto $scheme;`.
- **A path such as `/scoring/`:** build with `--build-arg BASE_PATH=/scoring/`, and have the front end strip the path when it forwards, as nginx does with `location /scoring/ { proxy_pass http://127.0.0.1:<host port>/; }`, the trailing slash included. The container serves the site at its own `/`; forwarded with the path, its pages load blank. Or use B, which serves a path directly.

### Update it

```bash
git pull
docker tag panther-web panther-web:previous      # keep the running build, to roll back
docker build --secret id=ca,src=<the CA certificate> -t panther-web frontend
docker rm -f panther-web
docker run ...                                     # the same command as above
```

**To roll back,** remove the container and run the same command with `panther-web:previous`.

**When the API's container is replaced,** start the new one with `--network panther` and the same name. `panther-web` finds it without a restart.

## B: The Built Files

### Build them

From the repository's root, write the files to a new folder next to the one the web server serves:

```bash
git pull
docker build --secret id=ca,src=<the CA certificate> \
  --target site --output type=local,dest=<web root>.new frontend
```

The folder holds `index.html`, `404.html` and `assets/`.

### Swap them in

```bash
mv <web root> <web root>.previous
mv <web root>.new <web root>
```

**To roll back,** swap the folders back. Remove `<web root>.previous` before the next update.

### What the web server needs

The same as the `web` image's nginx config, `frontend/nginx/default.conf.template`:

- **Deep links:** a path that isn't a file gets `index.html`, such as nginx's `try_files $uri $uri/ /index.html;`. Without it, reloading `/jobs/<id>` gives a 404.
- **`/api/` forwarded to the API,** with a body limit of at least 17 MiB, a little over the API's 16 MiB: nginx's default is 1 MiB.
- **Caching:** files under `/assets/` can be cached for a year; `index.html` should be revalidated (`Cache-Control: no-cache`), so a new build shows at once.

## The API's Data

The API reads each service's data from the folder `PANTHER_DATA_DIR` names, mounted read-only into its container: the cSNP data under `csnp/`, and, for ID mapping, the refmap data under `refmap/19/`, PANTHER 19's generic mapping release. Until the refmap data is there, every `refmap` job fails with the generic error, and the API's log says at startup which files are missing (`refmap jobs will fail until the refmap data is in place: …`); everything else works.

Fetch it into the same folder once, before or with the deploy that wires `refmap` in, with the engine's CLI in the API image, as the user who owns the folder:

```bash
docker run --rm --user "$(id -u):$(id -g)" -v <the data folder>:/fetch <the API image> \
  panther-engine refmap data fetch --data-dir /fetch
```

It downloads the release from `data.pantherdb.org`, checks it against the pinned manifest, and writes nothing under `refmap/19/` unless every file matches. Run again, it downloads nothing and checks the files. The API reads the data when a job runs, so it needs no restart, though its startup line keeps saying the data is missing until the next one. The data changes only with a new manifest in the engine; [api.md, The refmap Data](../testing/api.md#the-refmap-data) has the details.

`PANTHER_API_RESULTS_BUDGET_MIB` caps the memory the finished jobs' results may take; set it to suit the server ([api.md, Settings](../testing/api.md#settings)).

## Checking It Works

After either way, against the site's address:

- [ ] `/` shows the home page, with the four services.
- [ ] Reloading a job's page, `/jobs/<id>`, shows the job, not the web server's 404.
- [ ] `/api/v1/health` returns `{"status":"ok"}` through the site.
- [ ] The footer shows the API's versions, not "unavailable". If it says "unavailable" while `/` works, check `API_UPSTREAM`.
- [ ] A cSNP job, such as the form's example, runs to **Succeeded**.
- [ ] An ID mapping job, such as the form's example, runs to **Succeeded**, with six mappings.
- [ ] The page has no **Mock data** banner.

## Changing Things Later

- **A new Node or nginx version:** a pull request that changes the pinned digest in `frontend/Dockerfile`. Dependabot doesn't update it.
- **The API moves to another container name or network:** restart `panther-web` with the new `API_UPSTREAM` and network. No rebuild needed.
- **The site moves under a path:** rebuild with `--build-arg BASE_PATH=/<path>/`, and serve it there, as above.
