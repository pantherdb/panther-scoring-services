# Divergences

Every deliberate difference between the Python engine and a service's reference. The format and rules are in [README.md](README.md). A row without an approver is a proposal: until it's signed off, the Python must match the reference.

| # | Service | What differs | Reference output | Python output | Why | Approved by | Date |
| - | ------- | ------------ | ---------------- | ------------- | --- | ----------- | ---- |
| 1 | `treegrafter` | The whole implementation: we adopt EBI's Python `treegrafter` instead of porting the legacy Perl 1.01 | Perl 1.01: HMMER, then RAxML 8.2.4 placement; 3-column output (query, family, annotation string) | EBI `treegrafter`: `hmmsearch`, then EPA-ng placement; TSV of up to 15 columns (subfamily, scores, coordinates, graft node, optional GO) | EBI maintains it for InterPro, it targets current PANTHER releases (the Perl hardcodes PANTHER 12), and it's Apache-2.0. Its output becomes the parity reference. Decided by the team on 2026-10-28 | | |
