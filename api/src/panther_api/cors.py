"""CORS for a frontend on another origin, such as the GitHub Pages site (deploy-frontend-to-pages).

`PANTHER_API_CORS_ORIGINS` lists the origins allowed. Empty, the default, adds no CORS at all:
requests pass straight through, and no response gets a CORS header. Set, requests go through
Starlette's `CORSMiddleware`, with exactly those origins, the methods and header the API uses,
and the response headers a client reads: `Location` and `Retry-After`. No wildcard, no credentials.
"""

from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from panther_api.settings import Settings

ALLOWED_METHODS = ("GET", "POST")
ALLOWED_HEADERS = ("Content-Type",)
EXPOSED_HEADERS = ("Location", "Retry-After")


class Cors:
    """Starlette's `CORSMiddleware` for the origins in the settings, or nothing when there are none.

    The settings are read in the lifespan and kept in `app.state.settings`, after the middleware
    stack is built, so the origins are read on each request, as `limits.BodyLimit` reads its limit,
    and the `CORSMiddleware` for them is built once.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._origins: tuple[str, ...] = ()
        self._cors: CORSMiddleware | None = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        settings: Settings | None = getattr(scope["app"].state, "settings", None)
        origins = () if settings is None else settings.cors_origins
        if not origins:
            await self.app(scope, receive, send)
            return
        if self._cors is None or origins != self._origins:
            self._origins = origins
            self._cors = CORSMiddleware(
                self.app,
                allow_origins=origins,
                allow_methods=ALLOWED_METHODS,
                allow_headers=ALLOWED_HEADERS,
                expose_headers=EXPOSED_HEADERS,
                allow_credentials=False,
            )
        await self._cors(scope, receive, send)
