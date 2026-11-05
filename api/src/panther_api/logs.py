"""The API's log: one format for its own records and Uvicorn's, on standard error.

`configure_logging()` runs first in the lifespan, once the settings are read, so the level comes
from `PANTHER_API_LOG_LEVEL`. Uvicorn has configured its own loggers by then; this takes them
over. Its first lines, before the lifespan, keep Uvicorn's format. Why it's done this way:
openspec add-api-logging, design.md, decisions 1 to 3.

Never log a value a user submitted, such as a sequence, a substitution or an ID: log its size.
"""

import logging
import re
import sys
import time
from typing import override

from panther_api.settings import LogLevel

UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")

# Requests left out of the access log below DEBUG. Matched at the end of the path, so they still
# match if the API is served under a path prefix.
_HEALTH = re.compile(r"/api/v1/health")
_JOBS = re.compile(r"/api/v1/jobs")
_JOB = re.compile(r"/api/v1/jobs/[^/]+")
_PATH_END = re.compile(r"(/api/v1/.*)$")


class _Formatter(logging.Formatter):
    """`2026-11-04T17:02:13.415Z INFO panther_api.jobs.runner: message`, in UTC."""

    converter = time.gmtime
    default_time_format = "%Y-%m-%dT%H:%M:%S"
    default_msec_format = "%s.%03dZ"

    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s: %(message)s")


class _Handler(logging.Handler):
    """Writes to whatever `sys.stderr` is when a record arrives, not when the handler was made,
    so it never holds a stream that a test's output capture has since closed."""

    def __init__(self, level: int) -> None:
        super().__init__(level)
        self.setFormatter(_Formatter())

    @override
    def emit(self, record: logging.LogRecord) -> None:
        try:
            stream = sys.stderr
            stream.write(self.format(record) + "\n")
            stream.flush()
        except Exception:
            self.handleError(record)


class RoutineRequestFilter(logging.Filter):
    """Drops Uvicorn's access record for a health check, a job poll answered with a 2xx, and a
    job submission answered with 202, whose job gets a line of its own.

    It keeps any record it doesn't recognise, so a change in Uvicorn's record logs too much,
    not too little.
    """

    @override
    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if not (isinstance(args, tuple) and len(args) == 5):
            return True
        _client, method, full_path, _http_version, status = args
        if not (isinstance(method, str) and isinstance(full_path, str) and isinstance(status, int)):
            return True
        match = _PATH_END.search(full_path.split("?", 1)[0])
        if match is None:
            return True
        path = match.group(1)
        if method == "GET" and _HEALTH.fullmatch(path):
            return False
        if method == "GET" and _JOB.fullmatch(path) and 200 <= status < 300:
            return False
        return not (method == "POST" and _JOBS.fullmatch(path) and status == 202)


def configure_logging(level: LogLevel) -> None:
    """Send every record at `level` and above, the API's and Uvicorn's, to standard error in one
    format. Below DEBUG, leave routine requests out of the access log.

    Safe to call again, as every test's app start does: it replaces the handler and filter it
    added before, and leaves other handlers on the root, such as pytest's, alone.
    """
    numeric = logging.getLevelNamesMapping()[level]

    root = logging.getLogger()
    for handler in [handler for handler in root.handlers if isinstance(handler, _Handler)]:
        root.removeHandler(handler)
    root.addHandler(_Handler(numeric))
    root.setLevel(numeric)

    for name in UVICORN_LOGGERS:
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
        logger.propagate = True
        logger.setLevel(numeric)

    access = logging.getLogger("uvicorn.access")
    for old in [old for old in access.filters if isinstance(old, RoutineRequestFilter)]:
        access.removeFilter(old)
    if numeric > logging.DEBUG:
        access.addFilter(RoutineRequestFilter())
