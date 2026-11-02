"""The limit on a request body's size, applied before anything reads the body into memory.

The input limits in the request models are Pydantic checks, which run only after Starlette has
read the whole body and decoded its JSON. This middleware runs first: it refuses a body whose
`Content-Length` is over the limit without reading it, and otherwise reads the body itself,
counting, and refuses it as soon as the count passes the limit. A body within the limit is handed
on to the app unchanged.
"""

from http import HTTPStatus

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from panther_api.problems import Problem, problem_response
from panther_api.settings import MAX_BODY_BYTES, Settings


def body_too_large_detail(limit: int) -> str:
    """The 413's detail: fixed text and the limit, never anything from the request."""
    return f"The request body is larger than the API accepts, {limit:,} bytes."


def _declared_length(scope: Scope) -> int | None:
    """The `Content-Length`, or None when there isn't one or it isn't a number."""
    headers: list[tuple[bytes, bytes]] = scope["headers"]
    for name, value in headers:
        if name == b"content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


class BodyLimit:
    """Answer `413` for a request whose body is over `PANTHER_API_MAX_BODY_BYTES`.

    The limit is read from the settings the lifespan stores in `app.state.settings`, so it's read
    once, at startup, like every other setting.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        # The default only where the lifespan hasn't run, as for a test client used without `with`.
        settings: Settings | None = getattr(scope["app"].state, "settings", None)
        limit = MAX_BODY_BYTES if settings is None else settings.max_body_bytes

        declared = _declared_length(scope)
        if declared is not None and declared > limit:
            await self._refuse(limit, scope, receive, send)
            return

        # Read the body here, so no more than the limit is ever held.
        messages: list[Message] = []
        received = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                # The client went away before sending it all: there's no one to answer.
                return
            messages.append(message)
            received += len(message.get("body", b""))
            if received > limit:
                await self._refuse(limit, scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        async def replay() -> Message:
            # The body as it came, then whatever the server sends next, such as a disconnect.
            if messages:
                return messages.pop(0)
            return await receive()

        await self.app(scope, replay, send)

    @staticmethod
    async def _refuse(limit: int, scope: Scope, receive: Receive, send: Send) -> None:
        status = HTTPStatus.CONTENT_TOO_LARGE
        problem = Problem(title=status.phrase, status=status, detail=body_too_large_detail(limit))
        await problem_response(problem)(scope, receive, send)
