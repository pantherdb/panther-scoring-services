# Parity

**Parity** means the new Python engine gives the same answers as each service's reference for the same input.

| Service | Reference |
| ------- | --------- |
| `hmmscore` | Legacy Perl `pantherScore.pl` |
| `refmap` | Legacy Perl `map_panther.pl` |
| `csnp` | Legacy Perl `snpScore.cgi` pipeline (`PANTHER_PSEP1.01.pl` and the scripts around it), on the frozen cSNP data |
| `treegrafter` | EBI's Python `treegrafter` at the commit we pin. We adopt it rather than port the legacy Perl 1.01; leaving the Perl is [divergence 1](divergences.md) |

Each port is a rewrite, not a redesign. The Perl is what pantherdb.org runs today. If the Python returns a different family, score, mapping or prediction for the same input, users get different results without being told. Parity is how we show the port didn't change the science.

Parity is the acceptance test for **milestone M1** of each service. It does not apply to **cSNP's M2** (HMMER or tree grafting for PSEP). M2 is meant to change answers, so it's validated against known pathogenic and benign variants instead.

## How It Works

1. **Choose a fixed set of inputs for each service.** Cover normal cases and edge cases. For example, for `csnp`:
   - a position outside the protein
   - a wrong wild-type amino acid
   - a start-loss variant such as `M1V` (`MAP-4`)
   - a batch that spans two families, in both orders (`SCORE-7`)
2. **Make the golden files.** Run the inputs through the service's reference and save the outputs as reference answers.
3. **Compare.** Run the same inputs through the Python engine. Every mismatch is either a porting bug, or a deliberate change that has been approved.
4. **Log every deliberate change** in `divergences.md`.

## What Goes Here

| File | Contents |
| ---- | -------- |
| [golden-setup.md](golden-setup.md) | How to run each reference and regenerate the golden files: the container, the Perl and tool versions (BLAST+, HMMER3, EPA-ng), the pinned `treegrafter` commit, and the PANTHER data versions |
| [inputs.md](inputs.md) | Each test input, by service, and why it's in the set |
| [divergences.md](divergences.md) | The divergence log (format below) |
| [csnp-library-survey.md](csnp-library-survey.md) | The survey of the cSNP PAML_RST library: what each check found across all 8,607 families, how the Perl's readings differ from the strict readers', and the families chosen for the cSNP data sample |
| [refmap-legacy-behaviour.md](refmap-legacy-behaviour.md) | What the legacy `refmap` service does, as its code runs it: the lookup, what the website called and how it used the answers, the data, the quirks (`REFMAP-1`, …) with their parity calls, and the proposed golden inputs |

The golden files themselves are test fixtures, so they live with the engine's tests in `engine/`. This folder explains them.

**Store the golden files and the parity inputs byte for byte.** Their folder, `engine/tests/golden/<service>/`, has a `-text` rule in `.gitattributes`. The repo's default turns CRLF into LF when a file is committed, on every OS. Some `csnp` cases carry a carriage return on purpose: `e10`'s input line ends in CRLF, and `MAP-5` keeps the trailing `\r` in the output substitution.

### Where to start for `csnp`

The legacy repository already has the reference material. Paths are relative to `panther-workspace/legacy/cSNP_analysis/`:

- `.specs/2026-10-28-legacy-behavior-spec.md`:
  - §6: the quirk catalog. Each quirk has a parity call: **Match**, **Decide** or **N/A**.
  - §7: pinned checksums for the PAML library, BLAST DB, species file and sample; commands to regenerate the outputs; and the expected outputs for the 35-SNP sample, the order-dependence run, the edge cases and the CGI.
- `docs/2026-10-28-parity-review.md`: the defects and the keep-or-fix decisions, which are logged here as proposed divergences.

**Matching those goldens byte for byte reproduces known defects.** Until a proposed row is approved, the Python matches the legacy output, defects included. [golden-setup.md](golden-setup.md) and [inputs.md](inputs.md) start from spec §7 rather than redo it.

### Where to start for `refmap`

[refmap-legacy-behaviour.md](refmap-legacy-behaviour.md). The legacy code is two short Perl scripts in `panther-workspace/legacy/RefProteomeMapper/`, with no spec of its own, so that doc is the reference for its quirk IDs.

## Divergence Log Format

```markdown
| # | Service | What differs | Reference output | Python output | Why | Approved by | Date |
| - | ------- | ------------ | ---------------- | ------------- | --- | ----------- | ---- |
| n | `csnp` | Form values containing "2" | `A12P` read as `A1 P` | `A12P` | Bug: `tr/%2B/ /` in the site's snpScore.cgi | | |
```

A row without an approver is a proposal, not a divergence. Until someone signs it off, the Python must match the reference.
