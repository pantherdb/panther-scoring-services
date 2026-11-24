# treegrafter Scoring Fixtures

What the tools wrote for three proteins grafted against the treegrafter fixture (`../treegrafter/`), for the scoring tests that run fake tools. Each is from EBI's command line at the pinned commit, as `treegrafter.sh search` runs it: `hmmsearch -Z 65000000 -E 0.001 --domE 0.00000001 --incdomE 0.00000001 --notextw` against the fixture's `famhmm/binHmm`, with the query named `query`, then `treegrafter run -e 0.00000001 --print-go --keep`, whose EPA-ng output was kept. They were made in the engine image, with HMMER 3.4 and EPA-ng 0.3.8, on arm64, on 2026-11-24.

| File | What it is |
| ---- | ---------- |
| `apoe.hmmsearch.out` | `hmmsearch`'s report for APOE, the site's example (`../../golden/hmmscore/example/apoe.fasta`): PTHR18976 only |
| `apoe.jplace` | EPA-ng's placement of APOE on PTHR18976's tree: one placement, below `AN163` |
| `hbb.hmmsearch.out` | `hmmsearch`'s report for human HBB, UniProt P68871: PTHR11442 only |
| `hbb.jplace` | EPA-ng's placements of HBB on PTHR11442's tree: five, below `AN248` |
| `ndrg1.hmmsearch.out` | `hmmsearch`'s report for human NDRG1, UniProt Q92597: PTHR11034 only, a family that can't be placed |

The tests cut these reports into others by family section, from a `Query:` line to its `//`, such as one with two families, or edit one value, such as an E-value over the 1e-8 cutoff.
