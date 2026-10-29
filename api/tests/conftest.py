from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from panther_engine.core.tools import ToolReport

from panther_api.main import create_app

# Every tool found, in the engine's order, at made-up paths that no response may contain.
FAKE_REPORTS = (
    ToolReport("blastp", Path("/opt/fake-tools/bin/blastp"), "2.17.0"),
    ToolReport("hmmscan", Path("/opt/fake-tools/bin/hmmscan"), "3.4"),
    ToolReport("hmmsearch", Path("/opt/fake-tools/bin/hmmsearch"), "3.4"),
    ToolReport("epa-ng", Path("/opt/fake-tools/bin/epa-ng"), "0.3.8"),
)


@pytest.fixture(autouse=True)
def fake_tools(monkeypatch: pytest.MonkeyPatch) -> tuple[ToolReport, ...]:
    """Stand in for the engine's tool report, so no test runs or needs the real tools.

    A test that needs another report patches `panther_api.versions.report_tools` again, before
    it builds its app.
    """
    monkeypatch.setattr("panther_api.versions.report_tools", lambda: list(FAKE_REPORTS))
    return FAKE_REPORTS


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as client:
        yield client
