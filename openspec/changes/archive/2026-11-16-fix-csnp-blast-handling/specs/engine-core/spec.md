# Spec Delta

## ADDED Requirements

### Requirement: Tools run without usage reports

The engine SHALL start every external tool with BLAST+'s usage reporting turned off (`BLAST_USAGE_REPORT=false`), whatever the caller's environment says, so that no tool run contacts NCBI. The images that hold the tools SHALL set the same variable, so a tool run by hand in an image doesn't report either.

#### Scenario: A caller asks for reports

- **WHEN** the engine runs a tool while its own environment has `BLAST_USAGE_REPORT=true`
- **THEN** the tool's environment has `BLAST_USAGE_REPORT=false`, and the rest of the caller's environment reaches it unchanged

#### Scenario: In the images

- **WHEN** a shell in the engine image or the API image prints `BLAST_USAGE_REPORT`
- **THEN** it prints `false`

#### Scenario: NCBI unreachable

- **WHEN** the engine runs `blastp -version` in the engine image, with NCBI's host name pointed at an address that drops traffic
- **THEN** it finishes in under 2 seconds
