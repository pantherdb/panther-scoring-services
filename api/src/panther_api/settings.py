"""The API's settings, read from environment variables prefixed `PANTHER_API_`.

The lifespan reads them once, when the app starts, so an invalid value stops the API before it
takes a request. There is no `.env` file. docs/testing/api.md lists the variables.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

MAX_BODY_BYTES = 16 * 1024 * 1024
"""The default limit on a request body. It fits the largest valid request: a `refmap` job of
100,000 IDs of 64 characters is about 13 MB of JSON when every `"` or `\\` is escaped."""

MAX_QUEUED_JOBS = 50
"""The default cap on jobs waiting for a worker. Why 50: openspec harden-api-for-hosting,
design.md, decision 3."""


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
