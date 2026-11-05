# Spec Delta

## ADDED Requirements

### Requirement: One line for each finished job

When a job finishes, the API SHALL log one line with the job's id, its service, the size of its input, its status, the error's HTTP status if it failed, how long it waited for a worker and how long it ran, in seconds. The line MUST be `INFO` for a job that succeeded or failed on its input, and `ERROR` otherwise.

#### Scenario: A job that succeeds

- **WHEN** a `csnp` job for `HUMAN` with a sequence of 347 residues and 3 substitutions runs and succeeds
- **THEN** the log has one `INFO` line with the job's id, `csnp`, `HUMAN`, 347 residues, 3 substitutions, `succeeded`, its wait and its run time

#### Scenario: A job that fails on its input

- **WHEN** a job fails because the engine can't process its input
- **THEN** the log has one `INFO` line with the job's id, `failed`, `422`, its wait and its run time, and neither the engine's message nor a traceback

#### Scenario: A job that fails unexpectedly

- **WHEN** a job's work raises an unexpected exception
- **THEN** the log has one `ERROR` line with the job's id, `failed`, `500`, its wait and its run time

#### Scenario: A worker dies

- **WHEN** the worker process running a job dies
- **THEN** the log has one `ERROR` line with the job's id, `failed` and `500`, and says the worker stopped

### Requirement: The size of a job's input

A job's lines SHALL give the size of its input: for `csnp`, the species code, the sequence's length in residues and the number of substitutions; for `refmap`, the organism code and the number of IDs. They MUST NOT contain the submitted sequence, substitutions or IDs.

#### Scenario: A cSNP job's size

- **WHEN** a `csnp` job for `HUMAN` with a sequence of 347 residues and 3 substitutions finishes
- **THEN** its line has `HUMAN`, 347 residues and 3 substitutions, and neither the sequence nor any substitution

### Requirement: A job's submission is logged at DEBUG

When the API accepts a job, it SHALL log one `DEBUG` line with the job's id, its service and the size of its input, once the job has started. A request that creates no job MUST NOT log a submission line, and a failure while writing the line MUST NOT stop the job from running.

#### Scenario: Submitted at DEBUG

- **WHEN** the log level is `DEBUG` and a client submits a valid job
- **THEN** the log has one `DEBUG` line with the job's id, its service and the size of its input, before the job's finish line

#### Scenario: Not at INFO

- **WHEN** the log level is `INFO` and a client submits a valid job that succeeds
- **THEN** the job's only line is its finish line

#### Scenario: A request that creates no job

- **WHEN** the log level is `DEBUG` and a client submits a request that gets a `422`, a `501` or a `503`
- **THEN** no submission line is logged

### Requirement: An unexpected error's traceback is logged once in ten minutes

For a job that fails unexpectedly, the API SHALL log the exception's traceback with the finish line the first time that error is seen in ten minutes. An error is the same when its type and the place it was raised are, whatever its message. A repeat within ten minutes MUST log the finish line without the traceback, naming the job whose line has it and how many times the error was seen since.

#### Scenario: The same error twice

- **WHEN** two jobs fail one after the other with the same exception type, raised from the same place
- **THEN** the first job's line has the traceback, and the second job's line has none and names the first job

#### Scenario: A message that varies

- **WHEN** two jobs fail one after the other from the same place with the same exception type, and messages that differ, such as a time limit that scales with the input
- **THEN** the second job's line has no traceback and names the first job

#### Scenario: A different error

- **WHEN** a job fails with an error, and the next job fails with the same type and message raised from another place
- **THEN** both jobs' lines have their traceback

#### Scenario: After ten minutes

- **WHEN** a job fails with an error first seen more than ten minutes before
- **THEN** its line has the traceback again, and later repeats name this job

### Requirement: A refused submission is logged

When the API refuses a valid job request because the queue is full, it SHALL log a `WARNING` line with the service, the number of jobs running and waiting, and the cap, at most once a minute. A refusal in the minute after a line MUST be counted, and the next line MUST give the number of refusals since the previous line.

#### Scenario: Queue full

- **WHEN** `PANTHER_API_MAX_QUEUED_JOBS` jobs are waiting and a client submits a valid job
- **THEN** the client gets a `503`, and the log has one `WARNING` line naming the service and the cap

#### Scenario: A client retrying against a full queue

- **WHEN** the queue is full, and a client submits three valid jobs within a minute, then another a minute after the first
- **THEN** the first and the last get a `WARNING` line, and the last line says three jobs were refused since the first line
