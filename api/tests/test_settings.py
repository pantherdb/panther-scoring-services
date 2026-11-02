import pytest
from pydantic import ValidationError

from panther_api.settings import Settings


def test_defaults() -> None:
    settings = Settings()

    assert settings.job_workers == 2
    assert settings.job_expiry_seconds == 24 * 60 * 60
    assert settings.max_queued_jobs == 50
    assert settings.max_body_bytes == 16 * 1024 * 1024


def test_environment_overrides_the_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PANTHER_API_JOB_WORKERS", "5")
    monkeypatch.setenv("PANTHER_API_JOB_EXPIRY_SECONDS", "3600")
    monkeypatch.setenv("PANTHER_API_MAX_QUEUED_JOBS", "0")
    monkeypatch.setenv("PANTHER_API_MAX_BODY_BYTES", "1024")

    settings = Settings()

    assert settings.job_workers == 5
    assert settings.job_expiry_seconds == 3600
    assert settings.max_queued_jobs == 0
    assert settings.max_body_bytes == 1024


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("PANTHER_API_JOB_WORKERS", "0"),
        ("PANTHER_API_JOB_WORKERS", "two"),
        ("PANTHER_API_JOB_EXPIRY_SECONDS", "0"),
        ("PANTHER_API_JOB_EXPIRY_SECONDS", "1 day"),
        ("PANTHER_API_MAX_QUEUED_JOBS", "-1"),
        ("PANTHER_API_MAX_QUEUED_JOBS", "many"),
        ("PANTHER_API_MAX_BODY_BYTES", "0"),
        ("PANTHER_API_MAX_BODY_BYTES", "16MB"),
    ],
)
def test_invalid_values_are_rejected(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        Settings()
