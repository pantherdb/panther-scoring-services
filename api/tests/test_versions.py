from importlib.metadata import version
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from panther_engine.core.tools import TOOLS, ToolReport

from panther_api.main import create_app
from panther_api.versions import read_versions

# The directory in conftest's fake report paths. No response may contain it.
FAKE_TOOLS_DIR = "fake-tools"


def use_reports(monkeypatch: pytest.MonkeyPatch, *reports: ToolReport) -> None:
    monkeypatch.setattr("panther_api.versions.report_tools", lambda: list(reports))


def test_fake_report_matches_the_engine(fake_tools: tuple[ToolReport, ...]) -> None:
    assert [report.name for report in fake_tools] == [tool.name for tool in TOOLS]
    assert all(report.path and FAKE_TOOLS_DIR in report.path.parts for report in fake_tools)


def test_read_versions_gives_the_package_versions() -> None:
    versions = read_versions()

    assert versions.api == version("panther-api")
    assert versions.engine == version("panther-engine")


def test_read_versions_keeps_the_engine_order() -> None:
    names = [tool.name for tool in read_versions().tools]

    assert names == ["blastp", "hmmscan", "hmmsearch", "epa-ng"]


def test_missing_and_unreadable_tools_are_null(monkeypatch: pytest.MonkeyPatch) -> None:
    use_reports(
        monkeypatch,
        ToolReport("blastp", None, None),
        ToolReport("hmmscan", Path("/opt/tools/bin/hmmscan"), None),
    )

    tools = {tool.name: tool.version for tool in read_versions().tools}

    assert tools == {"blastp": None, "hmmscan": None}


def test_read_versions_leaves_out_the_paths() -> None:
    assert FAKE_TOOLS_DIR not in read_versions().model_dump_json()


def test_versions_lists_every_tool(client: TestClient) -> None:
    response = client.get("/api/v1/versions")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "api": version("panther-api"),
        "engine": version("panther-engine"),
        "tools": [
            {"name": "blastp", "version": "2.17.0"},
            {"name": "hmmscan", "version": "3.4"},
            {"name": "hmmsearch", "version": "3.4"},
            {"name": "epa-ng", "version": "0.3.8"},
        ],
    }


def test_a_missing_tool_is_listed_as_null(
    monkeypatch: pytest.MonkeyPatch, fake_tools: tuple[ToolReport, ...]
) -> None:
    present = [report for report in fake_tools if report.name != "epa-ng"]
    use_reports(monkeypatch, *present, ToolReport("epa-ng", None, None))

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/versions")

    assert response.status_code == 200
    assert response.json()["tools"] == [
        {"name": "blastp", "version": "2.17.0"},
        {"name": "hmmscan", "version": "3.4"},
        {"name": "hmmsearch", "version": "3.4"},
        {"name": "epa-ng", "version": None},
    ]


def test_versions_response_has_no_paths(client: TestClient) -> None:
    assert FAKE_TOOLS_DIR not in client.get("/api/v1/versions").text


def test_versions_are_read_once_at_startup(
    monkeypatch: pytest.MonkeyPatch, fake_tools: tuple[ToolReport, ...]
) -> None:
    calls = 0

    def counting_report() -> list[ToolReport]:
        nonlocal calls
        calls += 1
        return list(fake_tools)

    monkeypatch.setattr("panther_api.versions.report_tools", counting_report)

    with TestClient(create_app()) as client:
        assert calls == 1
        bodies = [client.get("/api/v1/versions").json() for _ in range(3)]

    assert calls == 1
    assert bodies[0] == bodies[1] == bodies[2]


def test_a_failing_tool_report_leaves_health_and_versions_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failing_report() -> list[ToolReport]:
        raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

    monkeypatch.setattr("panther_api.versions.report_tools", failing_report)

    with TestClient(create_app()) as client:
        health = client.get("/api/v1/health")
        tools = client.get("/api/v1/versions").json()["tools"]

    assert health.status_code == 200
    assert tools == [{"name": tool.name, "version": None} for tool in TOOLS]
