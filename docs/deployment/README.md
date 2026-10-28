# Deployment

How the service gets deployed, and a record of each deployment.

## What Goes Here

| File | Contents |
| ---- | -------- |
| `runbook-<topic>.md` | Steps that repeat, such as `runbook-deploy.md`, `runbook-rollback.md` or `runbook-new-panther-release.md`. Not dated: keep them current |
| `YYYY-MM-DD-<environment>.md` | A record of one deployment, for example `2026-12-01-staging.md` |

## What a Deployment Record Includes

- Environment, date, and who deployed.
- Versions: image tags, PANTHER library version, BLAST+ version.
- What changed since the last deployment.
- Any manual steps, and anything that went wrong.
- How to roll back.

**Never put secrets here**: no passwords, tokens or private hostnames. Say where a secret is stored, not what it is.
