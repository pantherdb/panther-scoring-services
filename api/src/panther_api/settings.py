"""The API's settings, read from environment variables prefixed `PANTHER_API_`.

The lifespan reads them once, when the app starts, so an invalid value stops the API before it
takes a request. There is no `.env` file. docs/testing/api.md lists the variables.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PANTHER_API_")

    job_workers: int = Field(default=2, ge=1, description="Worker processes that run jobs")
    job_expiry_seconds: int = Field(
        default=24 * 60 * 60, ge=1, description="How long a finished job is kept"
    )
