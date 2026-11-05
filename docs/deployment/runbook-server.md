# Runbook: Images on Our Server

How to get the site and the API onto the server as Docker images, and serve the site beside the API at one address, so its calls to `/api/v1` need no CORS. The site's way is an alternative to [GitHub Pages](runbook-pages.md), using the same build. The images are `frontend/Dockerfile` and the root `Dockerfile`; the change that added the site's image and publishing is `add-frontend-image`.

HTTPS, the hostname and which ports are open are the server's front end, as [hosting.md](../design/hosting.md) says; this runbook covers what runs behind it.

## Getting the Images

Each image comes one of two ways. Both give the same image.

| | Pulled from GitHub's container registry | Built on the server |
| --- | --- | --- |
| The server needs | Docker | Docker and a checkout of this repository |
| What it runs | The image CI built and checked | A build of the same commit |
| How long it takes | Seconds: a download | Minutes for the site; longer for the API |

**Published by CI.** After a merge to `main` that changes what's in an image, and once that image's checks pass, CI pushes it:

| Image | Published when these change |
| ----- | --------------------------- |
| `ghcr.io/pantherdb/panther-web` | `frontend/` |
| `ghcr.io/pantherdb/panther-api` | `api/`, the engine's source, `pyproject.toml` or tools, the root `Dockerfile` or `.dockerignore` |

- **Tags:** `main`, the latest, and the commit's full SHA, which never moves and is what rolling back uses. A commit's SHA is on its page on GitHub, or from `git log`.
- **`linux/amd64` only.** A machine on `arm64` builds the image itself.
- **Kept until someone deletes them,** on the package's page on GitHub. Storage is free for a public image.
- **Pull requests never publish.** They only build and check.

**Once, after the first publish:** an organization owner makes each package public (the package's page → Package settings → Change visibility). Until then, pulling needs a GitHub login with `read:packages`.

## The Site: Two Ways

| | A: the `web` container | B: the built files |
| --- | --- | --- |
| What runs | nginx in a container, on port 8080, serving the site and forwarding `/api/` to the API | Nothing new: the server's web server serves a folder |
| The server's web server | Forwards the site's address to the container | Serves the folder, and forwards `/api/` to the API itself |
| Updating | Like the API: pull or build the image, restart the container | Copy the files into a new folder, swap it in |

Pick one. The server keeps working as it does today until someone switches. Every build fails if it contains the API mocking library or the mock data banner.

## Build Settings

The defaults suit a site at the root of its address, with the API at `/api/` on the same address. The published image uses them. If that isn't so, build on the server with `--build-arg`.

| Build argument | Default | What it sets |
| -------------- | ------- | ------------ |
| `BASE_PATH` | `/` | The path the site is served under, such as `/scoring/` |
| `VITE_API_BASE_URL` | empty: the relative `/api/v1` | The API's URL, without `/api/v1`, if the API is at another address |

More on both in [frontend.md, Build Settings](../testing/frontend.md#build-settings).

## A: The `web` Container

### Get the image

Pull it:

```bash
docker pull ghcr.io/pantherdb/panther-web:main
```

Or build it, from the repository's root, on the commit to deploy:

```bash
git pull
docker build -t panther-web frontend
```

### Start it

On the same Docker network as the API container, telling it the API container's name. `<image>` is `ghcr.io/pantherdb/panther-web:main` if pulled, `panther-web` if built:

```bash
docker run -d --name panther-web --restart unless-stopped \
  --network <the API's network> \
  -e API_UPSTREAM=http://<the API container's name>:8000 \
  -p <host port>:8080 <image>
```

- **Start the API first.** nginx looks up `API_UPSTREAM` when it starts, and stops if the name doesn't exist yet.
- **`API_UPSTREAM`** is `http://api:8000` unless set: the API's service name in `compose.yaml`.
- **The server's front end** then forwards the site's address to `<host port>`. Which port, and whether it's open only to the front end, is the server's choice.
- **With compose,** `docker compose up -d --build web` builds and starts the API and the site together, the site on port 8080. The API then needs the data mount the `api` service names.

### Update it

```bash
docker pull ghcr.io/pantherdb/panther-web:main    # or: git pull, then the docker build above
docker rm -f panther-web
docker run ...                                     # the same command as above
```

**To roll back,** remove the container and run the same command with an earlier commit's tag, `ghcr.io/pantherdb/panther-web:<commit SHA>`. If you build on the server, `docker tag panther-web panther-web:previous` before each build, and roll back to that.

## B: The Built Files

### Get them

Write them to a new folder next to the one the web server serves. From the pulled image:

```bash
docker pull ghcr.io/pantherdb/panther-web:main
docker create --name panther-web-files ghcr.io/pantherdb/panther-web:main
docker cp panther-web-files:/srv/site <web root>.new
docker rm panther-web-files
```

Or built, from the repository's root, on the commit to deploy:

```bash
git pull
docker build --target site --output type=local,dest=<web root>.new frontend
```

Either way, the folder holds `index.html`, `404.html` and `assets/`.

### Swap them in

```bash
mv <web root> <web root>.previous
mv <web root>.new <web root>
```

**To roll back,** swap the folders back. Remove `<web root>.previous` before the next update.

### What the web server needs

The same as the `web` image's nginx config, `frontend/nginx/default.conf.template`:

- **Deep links:** a path that isn't a file gets `index.html`, such as nginx's `try_files $uri $uri/ /index.html;`. Without it, reloading `/jobs/<id>` gives a 404.
- **`/api/` forwarded to the API,** with a body limit a little over the API's 16 MiB.
- **Caching:** files under `/assets/` can be cached for a year; `index.html` should be revalidated (`Cache-Control: no-cache`), so a new build shows at once.

## The API Image

Pulling replaces `docker build --target api` on the server. Nothing else about running the API changes:

```bash
docker pull ghcr.io/pantherdb/panther-api:main
```

Then remove the API's container and start it again with `ghcr.io/pantherdb/panther-api:main` as its image, and the same settings as before: the data mount, `PANTHER_DATA_DIR` and `PANTHER_API_JOB_WORKERS` ([hosting.md](../design/hosting.md#what-the-server-provides)). Keep the container's name, so `API_UPSTREAM` still finds it. **To roll back,** start it with an earlier commit's tag.

The API image appears on the registry after the first merge that changes it; until then, build it on the server as before.

## Checking It Works

After any of these, against the site's address:

- [ ] `/` shows the home page, with the four services.
- [ ] Reloading a job's page, `/jobs/<id>`, shows the job, not the web server's 404.
- [ ] `/api/v1/health` returns `{"status":"ok"}` through the site.
- [ ] The footer shows the API's versions, not "unavailable".
- [ ] A cSNP job, such as the form's example, runs to **Succeeded**.
- [ ] The page has no **Mock data** banner.

## Changing Things Later

- **A new Node or nginx version:** a pull request that changes the pinned digest in `frontend/Dockerfile`. Dependabot doesn't update it.
- **The API moves to another container name or network:** restart `panther-web` with the new `API_UPSTREAM` and network. No rebuild needed.
- **The site moves under a path:** build on the server with `--build-arg BASE_PATH=/<path>/`, and serve it there. The published image is for `/` only.
- **Old images:** delete versions on the package's page. Keep the one running, and one or two before it to roll back to.
