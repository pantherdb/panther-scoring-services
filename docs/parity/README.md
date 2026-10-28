# Parity

**Parity** means the new Python engine gives the same answers as the legacy Perl for the same input.

This port is a rewrite, not a redesign. The Perl (`PANTHER_PSEP1.01.pl` and the scripts around it) is what pantherdb.org runs today, and it's the method the PANTHER-PSEP paper describes. If the Python returns a different family, preservation age or prediction for the same variant, users get different results without being told. Parity is how we show the port didn't change the science.

Parity is the acceptance test for **milestone M1** (the faithful port). It does not apply to **M2** (adding HMMER or RAxML). M2 is meant to change answers, so it's validated against known pathogenic and benign variants instead.

## How It Works

1. **Choose a fixed set of inputs:** protein sequences plus substitutions. Cover normal cases and edge cases, such as:
   - a position outside the protein
   - a wrong wild-type amino acid
   - a substitution with a `2` in its position (the `tr/%2B/ /` bug)
2. **Make the golden files.** Run the inputs through the Perl pipeline and save the outputs as reference answers.
3. **Compare.** Run the same inputs through the Python engine. Every mismatch is either a porting bug, or a deliberate change that has been approved.
4. **Log every deliberate change** in `divergences.md`.

## What Goes Here

| File | Contents |
| ---- | -------- |
| `golden-setup.md` | How to run the Perl and regenerate the golden files: the container, Perl and BLAST+ versions, and the PANTHER library version |
| `inputs.md` | Each test input, and why it's in the set |
| `divergences.md` | The divergence log (format below) |

The golden files themselves are test fixtures, so they live with the engine's tests in `backend/`. This folder explains them.

## Divergence Log Format

```markdown
| # | What differs | Perl output | Python output | Why | Approved by | Date |
| - | ------------ | ----------- | ------------- | --- | ----------- | ---- |
| 1 | Form values containing "2" | `A12P` read as `A1 P` | `A12P` | Bug: `tr/%2B/ /` in the site's snpScore.cgi | | |
```

A row without an approver is a proposal, not a divergence. Until someone signs it off, the Python must match the Perl.
