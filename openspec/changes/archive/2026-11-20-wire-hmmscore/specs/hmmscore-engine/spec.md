# Spec Delta

## MODIFIED Requirements

### Requirement: The time limit

Given a time limit in seconds, the engine SHALL apply it to the whole search, `hmmscan` and `hmmsearch` together. Past it, the engine SHALL stop the running tool, and raise its hmmscore timeout error, which `panther_engine.hmmscore` exports. The timeout error MUST NOT be the input error, nor a subclass of it, since a search can run past its limit on a busy server whatever its input. It MUST keep its type when passed from a worker process to the process that started the work. With no time limit, scoring isn't limited.

#### Scenario: Too long

- **WHEN** a protein is scored with a time limit shorter than `hmmscan` takes
- **THEN** scoring raises the timeout error, not the input error, no tool is left running, and the search's folder is removed

#### Scenario: Past the limit in a worker process

- **WHEN** a protein is scored in a worker process with a time limit shorter than `hmmscan` takes
- **THEN** the process that started the work receives the timeout error
