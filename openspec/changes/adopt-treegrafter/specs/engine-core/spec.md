# Spec Delta

## MODIFIED Requirements

### Requirement: A search tool doesn't outlive the process that started it

On Linux, a search tool the engine runs (`hmmscan`, `hmmsearch`, `blastp` or `epa-ng`) SHALL be killed when the process that started it dies, however it dies, so that no search runs on without its time limit beside the work that replaces it. The engine's other tools, such as its version checks, run as before.

#### Scenario: The parent is killed

- **WHEN** a process on Linux runs a search tool through the engine's tool runner, and the process is killed with `SIGKILL`
- **THEN** the tool is killed shortly after

#### Scenario: The parent finishes normally

- **WHEN** a process runs a search tool through the engine's tool runner, and the tool ends before the process does
- **THEN** the tool's exit status and output reach the caller as before
