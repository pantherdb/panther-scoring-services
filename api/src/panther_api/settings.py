"""The API's settings, read from environment variables prefixed `PANTHER_API_`.

The lifespan reads them once, when the app starts, so an invalid value stops the API before it
takes a request. There is no `.env` file. docs/testing/api.md lists the variables.
"""

import re
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

MAX_BODY_BYTES = 16 * 1024 * 1024
"""The default limit on a request body. It fits the largest valid request: a `refmap` job of
100,000 IDs of 64 characters is about 13 MB of JSON when every `"` or `\\` is escaped."""

MAX_QUEUED_JOBS = 50
"""The default cap on jobs waiting for a worker. Why 50: openspec harden-api-for-hosting,
design.md, decision 3."""

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]
"""The log levels a setting may name. Not CRITICAL: the API logs nothing at that level, so it
would silence the log (openspec add-api-logging, design.md, decision 6)."""

ORIGIN = re.compile(r"https?://[^/\s*?#@]+")
"""A browser origin: a scheme and a host, with any port, and no path, wildcard or trailing `/`."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PANTHER_API_")

    job_workers: int = Field(default=2, ge=1, description="Worker processes that run jobs")
    job_expiry_seconds: int = Field(
        default=24 * 60 * 60, ge=1, description="How long a finished job is kept"
    )
    max_queued_jobs: int = Field(
        default=MAX_QUEUED_JOBS,
        ge=0,
        description="Jobs that may wait for a worker; one more is refused with a 503",
    )
    max_body_bytes: int = Field(
        default=MAX_BODY_BYTES,
        ge=1,
        description="The largest request body accepted, in bytes; a larger one is a 413",
    )
    log_level: LogLevel = Field(
        default="INFO",
        description="The lowest level logged: DEBUG, INFO, WARNING or ERROR, in any case",
    )
    # NoDecode: the variable is a comma-separated list, not JSON.
    cors_origins: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(),
        description=(
            "Browser origins allowed to call the API from another site, comma-separated, such as "
            "https://pantherdb.github.io; empty allows none, and adds no CORS headers"
        ),
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def _upper_case_level(cls, value: object) -> object:
        """Accept a level in any case, such as `debug`."""
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Split the comma-separated list, and refuse anything that isn't an exact origin."""
        if not isinstance(value, str):
            return value
        origins = tuple(origin.strip() for origin in value.split(",") if origin.strip())
        for origin in origins:
            if not ORIGIN.fullmatch(origin):
                # The value is configuration, not request data, so it may be named.
                raise ValueError(
                    f"{origin!r} isn't an origin: give the scheme and host only, such as "
                    "https://pantherdb.github.io, with no path, no trailing / and no *"
                )
        return origins
