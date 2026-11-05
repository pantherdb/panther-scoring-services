# Proposal

**Area:** api. Everything changed is in `api/` and its docs. No engine, frontend or schema changes.

## Why

The API is about to run on the team's server ([hosting.md](../../../docs/design/hosting.md), #34), where "the API's logs" are how anyone sees what it's doing. Today the API never sets up logging:

- Its `INFO` lines are lost: Uvicorn configures only its own loggers, so `panther_api`'s messages fall to Python's last-resort handler, which prints `WARNING` and above. A job that fails on its input (`jobs/runner.py`) is never seen.
- Nothing records a job being submitted, how long it waited, or how long it ran. There's no way to tell who is using a service, or whether jobs are slow.
- Lines carry no timestamp, and the API's lines and Uvicorn's have different formats.
- The access log has one line for every poll: the frontend polls a job every second, so a five-minute cSNP job writes 300 lines that say nothing.

## What Changes

- **One log format,** set up when the API starts: a UTC timestamp, the level, the logger and the message, on standard error, for the API's own loggers and Uvicorn's alike.
- **`PANTHER_API_LOG_LEVEL`,** `INFO` by default; `DEBUG`, `INFO`, `WARNING` or `ERROR`. An invalid value stops the API from starting, as for the other settings.
- **One line for each job,** when it finishes: its service, the size of its input, its status, how long it waited and how long it ran. `INFO`, or `ERROR` for an unexpected failure. The submission gets a line of its own only at `DEBUG`.
- **An unexpected error's traceback once in ten minutes.** When every job fails the same way, such as while the data is missing, the first job's line has the traceback, and the repeats name that job instead of repeating 30 lines each.
- **A `WARNING` when the queue is full** and a submission gets a `503`, since that means the server needs more workers or is being flooded.
- **Quieter access log:** at `INFO` and above, a successful `GET /api/v1/jobs/{id}` poll, `GET /api/v1/health`, and a `POST /api/v1/jobs` answered with `202` aren't logged; the job's own line covers the last. Every other request is, including a poll that gets a `404` and a submission that gets a `422`. At `DEBUG`, every request is logged.
- **No user data in the log.** A job's line gives sizes and codes, such as a sequence's length, how many substitutions and the species code, never the sequence, a substitution or an ID.
- **Docs:** the setting in `docs/testing/api.md`, what the log shows and how to read it, and `api/CLAUDE.md`'s rule about user data.

Not in this change:

- **JSON logs, a log file or a log shipper.** Plain lines on standard error suit `docker logs`. If the server gets a log collector, a JSON format can be added then.
- **Request ids** tying an access line to a job. An accepted submission has no access line at `INFO`, and at `DEBUG` the submission line follows it.
- **The client's address behind a proxy.** The access log shows the address the API sees, the proxy's unless the proxy's forwarded headers are trusted. That's part of the server setup (#34).
- **Logging in the worker processes.** The engine doesn't log, and an exception in a worker reaches the API's log with its traceback already.

## Parity

None. Logging doesn't change any service's output, and needs no divergence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `api-service`: new requirements for the log format and level setting, the quieter access log, and keeping user data out of the log.
- `scoring-jobs`: new requirements for a job's finish line and its input's size, the submission line at `DEBUG`, a repeated error's traceback once in ten minutes, and the refused-submission line.

"Configuration from the environment" isn't modified: `harden-api-for-hosting`, not yet archived, modifies it. The level setting is part of the new log requirement instead.

## Impact

- **Code:** a new `api/src/panther_api/logs.py`; `settings.py` (the level), `main.py` (set up in the lifespan), `jobs/runner.py` (the job lines and the queue-full line), and a size summary for each service's input model in `jobs/`.
- **Tests:** new tests for the format, the level, the access filter, the job lines and the absence of user data.
- **No contract change:** `openapi.json` and the frontend's types are unchanged.

## Open Questions

- **Does the server have a log collector,** or a rule on how long logs are kept? Needs team verification with the engine developer, who runs the server. Docker's default `json-file` driver keeps everything unless the container sets a size limit.
