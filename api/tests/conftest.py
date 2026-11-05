import logging
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from job_helpers import report_fake_tools
from markers import fail_if_missing, skip_if_missing
from panther_engine.core.tools import ToolReport

from panther_api.logs import UVICORN_LOGGERS
from panther_api.main import create_app


def pytest_runtest_setup(item: pytest.Item) -> None:
    skip_if_missing(item)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_call(item: pytest.Item) -> None:
    fail_if_missing(item)


# Every tool found, in the engine's order, at made-up paths that no response may contain.
FAKE_REPORTS = (
    ToolReport("blastp", Path("/opt/fake-tools/bin/blastp"), "2.17.0"),
    ToolReport("hmmscan", Path("/opt/fake-tools/bin/hmmscan"), "3.4"),
    ToolReport("hmmsearch", Path("/opt/fake-tools/bin/hmmsearch"), "3.4"),
    ToolReport("epa-ng", Path("/opt/fake-tools/bin/epa-ng"), "0.3.8"),
)


@pytest.fixture(autouse=True)
def default_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start every test from the settings' defaults, whatever the shell exports, such as
    `PANTHER_API_LOG_LEVEL=WARNING`. A test that needs a setting sets it after this runs."""
    for name in [name for name in os.environ if name.startswith("PANTHER_API_")]:
        monkeypatch.delenv(name)


@pytest.fixture(autouse=True)
def fake_tools(monkeypatch: pytest.MonkeyPatch) -> tuple[ToolReport, ...]:
    """Stand in for the engine's tool report, so no test runs or needs the real tools.

    It replaces the report where the app reads the versions and where the `tools` job calls it
    in this process. Worker processes don't see a monkeypatch, so it also replaces the function
    the job runner submits to them with one that returns the same versions (job_helpers.py).

    A test that needs another report patches `panther_api.versions.report_tools` again, before
    it builds its app; one that needs other work in the workers patches
    `panther_api.jobs.runner.run_job` with another function from job_helpers.py.
    """
    monkeypatch.setattr("panther_api.versions.report_tools", lambda: list(FAKE_REPORTS))
    monkeypatch.setattr("panther_api.jobs.tools.report_tools", lambda: list(FAKE_REPORTS))
    monkeypatch.setattr("panther_api.jobs.runner.run_job", report_fake_tools)
    return FAKE_REPORTS


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    """Undo what the app's start did to the logging setup (panther_api.logs), so a test's log
    level or handler doesn't carry over to the next test."""
    root = logging.getLogger()
    uvicorn = [logging.getLogger(name) for name in UVICORN_LOGGERS]
    saved_root = (list(root.handlers), root.level)
    saved = [
        (list(logger.handlers), list(logger.filters), logger.level, logger.propagate)
        for logger in uvicorn
    ]
    yield
    # Only the handlers the app added go: pytest adds and removes its own around each phase.
    for handler in list(root.handlers):
        if handler not in saved_root[0] and type(handler).__module__ == "panther_api.logs":
            root.removeHandler(handler)
    root.setLevel(saved_root[1])
    for logger, (handlers, filters, level, propagate) in zip(uvicorn, saved, strict=True):
        logger.handlers[:] = handlers
        logger.filters[:] = filters
        logger.setLevel(level)
        logger.propagate = propagate


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as client:
        yield client
