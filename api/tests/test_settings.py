import pytest
from pydantic import ValidationError

from panther_api.settings import Settings


def test_defaults() -> None:
    settings = Settings()

    assert settings.job_workers == 2
    assert settings.job_expiry_seconds == 24 * 60 * 60


def test_environment_overrides_the_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PANTHER_API_JOB_WORKERS", "5")
    monkeypatch.setenv("PANTHER_API_JOB_EXPIRY_SECONDS", "3600")

    settings = Settings()

    assert settings.job_workers == 5
    assert settings.job_expiry_seconds == 3600


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("PANTHER_API_JOB_WORKERS", "0"),
        ("PANTHER_API_JOB_WORKERS", "two"),
        ("PANTHER_API_JOB_EXPIRY_SECONDS", "0"),
        ("PANTHER_API_JOB_EXPIRY_SECONDS", "1 day"),
    ],
)
def test_invalid_values_are_rejected(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        Settings()
