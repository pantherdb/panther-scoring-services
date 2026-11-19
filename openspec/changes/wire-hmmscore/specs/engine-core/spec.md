# Spec Delta

## ADDED Requirements

### Requirement: A tool doesn't outlive the process that started it

On Linux, an external tool the engine runs SHALL be stopped when the process that started it dies, however it dies, so that no tool runs on without its time limit, beside the work that replaces it. The mechanism is the engine's: a signal the kernel sends the tool when its parent dies, or a session per tool that the caller can stop.

#### Scenario: The parent is killed

- **WHEN** a process runs a long-running tool through the engine's tool runner, and the process is killed with `SIGKILL`
- **THEN** the tool is no longer running shortly after, or, where the engine runs each tool in a session of its own, once the caller has stopped that process's sessions as the engine provides

#### Scenario: The parent finishes normally

- **WHEN** a process runs a tool through the engine's tool runner, and the tool ends before the process does
- **THEN** the tool's exit status and output reach the caller as before
