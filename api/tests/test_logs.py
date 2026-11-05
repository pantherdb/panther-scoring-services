"""The log's format and level, and the requests left out of the access log (openspec change
add-api-logging; api-service: One log format, Log level from the environment, Routine requests
are left out of the request log, No user data in the log)."""

import logging
import re

import pytest
from serving import serve

from panther_api.logs import RoutineRequestFilter, configure_logging

TOOLS_JOB: dict[str, object] = {"service": "tools", "input": {}}
LINE = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z (DEBUG|INFO|WARNING|ERROR) \S+: .*")
UNKNOWN_JOB = "/api/v1/jobs/00000000-0000-4000-8000-000000000000"


def lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if LINE.fullmatch(line)]


def request_lines(text: str, request: str) -> list[str]:
    """The access lines for a request such as `GET /api/v1/health`."""
    return [line for line in lines(text) if " uvicorn.access: " in line and f'"{request} ' in line]


# The format.


def test_a_record_is_one_line_with_a_utc_timestamp_level_and_logger(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("INFO")

    logging.getLogger("panther_api.example").info("a message %s", 42)

    err = capsys.readouterr().err
    assert re.search(
        r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z INFO panther_api\.example: a message 42$",
        err,
        re.MULTILINE,
    ), err


def test_a_request_has_the_same_format(capsys: pytest.CaptureFixture[str]) -> None:
    with serve() as server:
        assert server.request("GET", "/api/v1/versions")[0] == 200

    [line] = request_lines(capsys.readouterr().err, "GET /api/v1/versions")
    assert " INFO uvicorn.access: " in line
    assert line.endswith('"GET /api/v1/versions HTTP/1.1" 200')


def test_starting_twice_leaves_one_handler() -> None:
    root = logging.getLogger()
    configure_logging("INFO")
    count = len(root.handlers)

    configure_logging("DEBUG")

    assert len(root.handlers) == count
    assert len(logging.getLogger("uvicorn.access").filters) == 0
    configure_logging("INFO")
    assert len(logging.getLogger("uvicorn.access").filters) == 1


# The level.


def test_info_is_the_default_and_debug_is_left_out(capsys: pytest.CaptureFixture[str]) -> None:
    with serve():
        logging.getLogger("panther_api.example").debug("not shown")
        logging.getLogger("panther_api.example").info("shown")

    err = capsys.readouterr().err
    assert "not shown" not in err
    assert "INFO panther_api.example: shown" in err


def test_a_higher_level_leaves_out_info_and_requests(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PANTHER_API_LOG_LEVEL", "warning")

    with serve() as server:
        assert server.request("GET", "/api/v1/versions")[0] == 200
        logging.getLogger("panther_api.example").info("not shown")
        logging.getLogger("panther_api.example").warning("shown")

    err = capsys.readouterr().err
    assert request_lines(err, "GET /api/v1/versions") == []
    assert "not shown" not in err
    assert "WARNING panther_api.example: shown" in err


# Routine requests.


def test_a_successful_poll_and_an_accepted_job_write_no_request_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with serve() as server:
        job = server.run_job(TOOLS_JOB)

    err = capsys.readouterr().err
    assert job["status"] == "succeeded"
    assert request_lines(err, f"GET /api/v1/jobs/{job['id']}") == []
    assert request_lines(err, "POST /api/v1/jobs") == []


def test_a_poll_for_an_unknown_job_writes_a_request_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with serve() as server:
        assert server.request("GET", UNKNOWN_JOB)[0] == 404

    [line] = request_lines(capsys.readouterr().err, f"GET {UNKNOWN_JOB}")
    assert line.endswith(" 404")


def test_a_health_check_writes_no_request_line(capsys: pytest.CaptureFixture[str]) -> None:
    with serve() as server:
        assert server.request("GET", "/api/v1/health")[0] == 200
        assert server.request("GET", "/api/v1/versions")[0] == 200

    err = capsys.readouterr().err
    assert request_lines(err, "GET /api/v1/health") == []
    assert len(request_lines(err, "GET /api/v1/versions")) == 1


def test_a_refused_submission_writes_a_request_line(capsys: pytest.CaptureFixture[str]) -> None:
    with serve() as server:
        assert (
            server.request("POST", "/api/v1/jobs", {"service": "tools", "input": {"x": 1}})[0]
            == 422
        )

    [line] = request_lines(capsys.readouterr().err, "POST /api/v1/jobs")
    assert line.endswith(" 422")


def test_every_request_is_logged_at_debug(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("PANTHER_API_LOG_LEVEL", "DEBUG")

    with serve() as server:
        job = server.run_job(TOOLS_JOB)
        assert server.request("GET", "/api/v1/health")[0] == 200

    err = capsys.readouterr().err
    assert len(request_lines(err, "POST /api/v1/jobs")) == 1
    assert len(request_lines(err, f"GET /api/v1/jobs/{job['id']}")) >= 1
    assert len(request_lines(err, "GET /api/v1/health")) == 1


@pytest.mark.parametrize(
    ("method", "path", "status", "kept"),
    [
        ("GET", "/api/v1/health", 200, False),
        ("GET", "/api/v1/health?x=1", 200, False),
        ("GET", "/panther/api/v1/health", 200, False),
        ("GET", "/api/v1/jobs/abc", 200, False),
        ("GET", "/api/v1/jobs/abc", 404, True),
        ("POST", "/api/v1/jobs", 202, False),
        ("POST", "/api/v1/jobs", 503, True),
        ("GET", "/api/v1/versions", 200, True),
        ("GET", "/api/v1/jobs/abc/more", 200, True),
    ],
)
def test_the_filter(method: str, path: str, status: int, kept: bool) -> None:
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5000", method, path, "1.1", status),
        None,
    )

    assert RoutineRequestFilter().filter(record) is kept


@pytest.mark.parametrize("args", [(), ("only one",), ("a", "GET", "/api/v1/health", "1.1", "200")])
def test_the_filter_keeps_a_record_it_doesnt_recognise(args: tuple[object, ...]) -> None:
    record = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, "message", args, None)

    assert RoutineRequestFilter().filter(record) is True


# No user data.


def test_a_rejected_value_is_not_logged(capsys: pytest.CaptureFixture[str]) -> None:
    value = "XYZZY-PLUGH-LOGGED"
    with serve() as server:
        status, _ = server.request(
            "POST",
            "/api/v1/jobs",
            {
                "service": "csnp",
                "input": {"sequence": value, "substitutions": [value], "species": value},
            },
        )

    err = capsys.readouterr().err
    assert status == 422
    assert request_lines(err, "POST /api/v1/jobs")
    assert value not in err
