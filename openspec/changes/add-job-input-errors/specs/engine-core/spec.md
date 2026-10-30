# Spec Delta

## ADDED Requirements

### Requirement: Input errors

The engine SHALL report input that a service can't process as a whole by raising its input error, with a message written for the person who submitted the input. The message MUST NOT contain file paths, tool output or internal identifiers. An input error MUST keep its type and message when it is passed from a worker process to the process that started the work.

#### Scenario: Raised in a worker process

- **WHEN** a function run in a separate process raises an input error with the message "Unknown organism."
- **THEN** the process that started it receives an input error with the message "Unknown organism."

#### Scenario: Copied between processes

- **WHEN** an input error is pickled and unpickled
- **THEN** the copy is an input error with the same message
