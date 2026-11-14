import pytest
from pydantic import ValidationError

from panther_api.settings import Settings


def test_defaults() -> None:
    settings = Settings()

    assert settings.job_workers == 2
    assert settings.job_expiry_seconds == 24 * 60 * 60
    assert settings.max_queued_jobs == 50
    assert settings.results_budget_mib == 256
    assert settings.max_body_bytes == 16 * 1024 * 1024
    assert settings.cors_origins == ()
    assert settings.log_level == "INFO"
    # hmmscore's (openspec add-hmmscore-job, design.md, decision 5).
    assert settings.hmmscore_max_residues == 10_000
    assert settings.hmmscore_time_limit_seconds == 720
    assert settings.hmmscore_max_running == 1
    assert settings.hmmscore_cpu == 0


@pytest.mark.parametrize(
    ("value", "level"), [("debug", "DEBUG"), ("Warning", "WARNING"), (" ERROR ", "ERROR")]
)
def test_the_log_level_is_read_in_any_case(
    monkeypatch: pytest.MonkeyPatch, value: str, level: str
) -> None:
    monkeypatch.setenv("PANTHER_API_LOG_LEVEL", value)

    assert Settings().log_level == level


@pytest.mark.parametrize(
    ("value", "origins"),
    [
        ("", ()),
        ("  ", ()),
        ("https://pantherdb.github.io", ("https://pantherdb.github.io",)),
        (
            " https://pantherdb.github.io , http://localhost:4173,",
            ("https://pantherdb.github.io", "http://localhost:4173"),
        ),
    ],
)
def test_cors_origins_are_a_comma_separated_list(
    monkeypatch: pytest.MonkeyPatch, value: str, origins: tuple[str, ...]
) -> None:
    monkeypatch.setenv("PANTHER_API_CORS_ORIGINS", value)

    assert Settings().cors_origins == origins


def test_environment_overrides_the_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PANTHER_API_JOB_WORKERS", "5")
    monkeypatch.setenv("PANTHER_API_JOB_EXPIRY_SECONDS", "3600")
    monkeypatch.setenv("PANTHER_API_MAX_QUEUED_JOBS", "0")
    monkeypatch.setenv("PANTHER_API_MAX_BODY_BYTES", "1024")
    monkeypatch.setenv("PANTHER_API_RESULTS_BUDGET_MIB", "1")

    settings = Settings()

    assert settings.job_workers == 5
    assert settings.job_expiry_seconds == 3600
    assert settings.max_queued_jobs == 0
    assert settings.max_body_bytes == 1024
    assert settings.results_budget_mib == 1


@pytest.mark.parametrize(
    ("name", "value", "field"),
    [
        ("PANTHER_API_HMMSCORE_MAX_RESIDUES", "5000", "hmmscore_max_residues"),
        ("PANTHER_API_HMMSCORE_MAX_RESIDUES", "1", "hmmscore_max_residues"),
        ("PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS", "3600", "hmmscore_time_limit_seconds"),
        ("PANTHER_API_HMMSCORE_MAX_RUNNING", "2", "hmmscore_max_running"),
        ("PANTHER_API_HMMSCORE_CPU", "4", "hmmscore_cpu"),
    ],
)
def test_each_hmmscore_setting_is_read_from_its_variable(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str, field: str
) -> None:
    monkeypatch.setenv(name, value)

    assert getattr(Settings(), field) == int(value)


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
        ("PANTHER_API_RESULTS_BUDGET_MIB", "0"),
        ("PANTHER_API_RESULTS_BUDGET_MIB", "-1"),
        ("PANTHER_API_RESULTS_BUDGET_MIB", "256MiB"),
        # hmmscore's residue limit is at most the product owner's 10,000.
        ("PANTHER_API_HMMSCORE_MAX_RESIDUES", "0"),
        ("PANTHER_API_HMMSCORE_MAX_RESIDUES", "10001"),
        ("PANTHER_API_HMMSCORE_MAX_RESIDUES", "10k"),
        ("PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS", "0"),
        ("PANTHER_API_HMMSCORE_TIME_LIMIT_SECONDS", "12 minutes"),
        ("PANTHER_API_HMMSCORE_MAX_RUNNING", "0"),
        ("PANTHER_API_HMMSCORE_MAX_RUNNING", "one"),
        ("PANTHER_API_HMMSCORE_CPU", "-1"),
        ("PANTHER_API_HMMSCORE_CPU", "all"),
        ("PANTHER_API_LOG_LEVEL", "LOUD"),
        ("PANTHER_API_LOG_LEVEL", "CRITICAL"),
        ("PANTHER_API_LOG_LEVEL", ""),
        # CORS takes origins: no wildcard, no path, no trailing slash, no bare host.
        ("PANTHER_API_CORS_ORIGINS", "*"),
        ("PANTHER_API_CORS_ORIGINS", "https://*.github.io"),
        ("PANTHER_API_CORS_ORIGINS", "https://pantherdb.github.io/panther-scoring-services/"),
        ("PANTHER_API_CORS_ORIGINS", "https://pantherdb.github.io/"),
        ("PANTHER_API_CORS_ORIGINS", "pantherdb.github.io"),
        ("PANTHER_API_CORS_ORIGINS", "https://pantherdb.github.io,ftp://example.org"),
    ],
)
def test_invalid_values_are_rejected(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        Settings()
