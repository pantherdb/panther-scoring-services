"""Every error as RFC 9457 problem details (`application/problem+json`)."""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pydantic.json_schema import models_json_schema
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_MEDIA_TYPE = "application/problem+json"
VALIDATION_DETAIL = "Request validation failed"
UNEXPECTED_DETAIL = "The server hit an unexpected error and could not complete the request."


class Problem(BaseModel):
    """An RFC 9457 problem details body."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str


class FieldError(BaseModel):
    """One field that failed validation. The submitted value is never included."""

    loc: list[str | int]
    msg: str
    type: str


class ValidationProblem(Problem):
    """A 422 problem that lists the fields that failed validation."""

    errors: list[FieldError]


# Declared on the /api/v1 router, so every route documents its errors. Because a `default`
# response is declared, FastAPI doesn't add its own HTTPValidationError 422.
PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    "default": {"model": Problem, "description": "Error, as problem details"},
    500: {"model": Problem, "description": "Unexpected error"},
}

_SCHEMA_REF = "#/components/schemas/{model}"


def document_problems(schema: dict[str, Any]) -> dict[str, Any]:
    """Finish the generated OpenAPI schema so it matches what the handlers return.

    Every operation that takes input documents a 422 with `ValidationProblem`, and every error
    response's body is listed under `application/problem+json`. Changes `schema` in place.
    """
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    _, definitions = models_json_schema(
        [(ValidationProblem, "validation")], ref_template=_SCHEMA_REF
    )
    components.update(definitions["$defs"])
    validation_response = {
        "description": "Request validation failed",
        "content": {
            PROBLEM_MEDIA_TYPE: {
                "schema": {"$ref": _SCHEMA_REF.format(model=ValidationProblem.__name__)}
            }
        },
    }

    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            responses = operation.setdefault("responses", {})
            if "parameters" in operation or "requestBody" in operation:
                responses["422"] = validation_response
            for status, response in responses.items():
                content = response.get("content", {})
                if (status == "default" or status[0] in "45") and "application/json" in content:
                    content[PROBLEM_MEDIA_TYPE] = content.pop("application/json")

    return schema


def add_problem_handlers(app: FastAPI) -> None:
    """Make every error the app returns a problem-details response."""
    # Starlette's class, not FastAPI's subclass: Starlette's router raises its own
    # for unknown paths (404) and wrong methods (405).
    app.exception_handler(StarletteHTTPException)(_http_error)
    app.exception_handler(RequestValidationError)(_validation_error)
    app.exception_handler(Exception)(_unexpected_error)


def _title(status: int) -> str:
    """The reason phrase, which RFC 9457 uses as the title for `about:blank`."""
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Error"


def _respond(problem: Problem, headers: Mapping[str, str] | None = None) -> JSONResponse:
    return JSONResponse(
        problem.model_dump(),
        status_code=problem.status,
        headers=headers,
        media_type=PROBLEM_MEDIA_TYPE,
    )


async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    title = _title(exc.status_code)
    # Starlette types `detail` as str, but FastAPI's HTTPException accepts any value.
    raw_detail = cast(object, exc.detail)
    detail = raw_detail if isinstance(raw_detail, str) else title
    problem = Problem(title=title, status=exc.status_code, detail=detail)
    # Keeps headers such as Allow on a 405.
    return _respond(problem, exc.headers)


VALUE_ERROR_PREFIX = "Value error, "


def _message(error: Mapping[str, Any]) -> str:
    """Pydantic's message, except where it quotes the submitted value or adds a prefix."""
    # A tagged union's message quotes the tag it was given, such as an unknown `service`.
    if error["type"] == "union_tag_invalid":
        ctx = error.get("ctx", {})
        return (
            f"Input tag found using {ctx.get('discriminator')} does not match any of the "
            f"expected tags: {ctx.get('expected_tags')}"
        )
    message = str(error["msg"])
    # A validator's ValueError reads "Value error, <message>"; users read only the message,
    # which our validators write for them.
    if error["type"] == "value_error":
        return message.removeprefix(VALUE_ERROR_PREFIX)
    return message


async def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic's errors also carry `input`, `ctx` and `url`; only these three are returned,
    # so a submitted value is never echoed back.
    errors = [
        FieldError(loc=list(error["loc"]), msg=_message(error), type=str(error["type"]))
        for error in exc.errors()
    ]
    status = HTTPStatus.UNPROCESSABLE_CONTENT
    problem = ValidationProblem(
        title=status.phrase, status=status, detail=VALIDATION_DETAIL, errors=errors
    )
    return _respond(problem)


async def _unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
    # Nothing about the exception goes in the response. Starlette re-raises it after this
    # handler, so the server logs it with its traceback.
    status = HTTPStatus.INTERNAL_SERVER_ERROR
    return _respond(Problem(title=status.phrase, status=status, detail=UNEXPECTED_DETAIL))
