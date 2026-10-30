# Spec Delta

## MODIFIED Requirements

### Requirement: A failing job reveals nothing internal

When a job's work raises an error other than an input error, the job SHALL end with status `failed` and an `error` in problem-details form, with a generic `detail`. The job MUST NOT contain the error's message, a traceback, file paths or configuration values. Other jobs MUST be unaffected.

#### Scenario: The work raises

- **WHEN** a job's work raises an error whose message contains a file path
- **THEN** the job ends with status `failed`, a `null` `result` and a problem-details `error` with status 500, and the job contains neither the message nor the path

## ADDED Requirements

### Requirement: Input errors reach the user

When a job's work reports that its input can't be processed, by raising the engine's input error, the job SHALL end with status `failed`, a `null` `result`, and a problem-details `error` with status 422 whose `detail` is the input error's message. The job MUST NOT contain a traceback. Other jobs MUST be unaffected.

#### Scenario: Unprocessable input

- **WHEN** a job's work raises an input error with the message "The input can't be scored."
- **THEN** the job ends with status `failed`, a `null` `result`, and an `error` with status 422 and the `detail` "The input can't be scored."

#### Scenario: Other jobs keep running

- **WHEN** one job's work raises an input error while another job runs
- **THEN** the other job still ends with status `succeeded`
