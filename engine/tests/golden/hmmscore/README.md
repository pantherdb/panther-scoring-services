# hmmscore Golden Files

The files the `hmmscore` tests compare against, and the inputs that produce them. Every file here is stored byte for byte (`-text` in `.gitattributes`).

## `example/`: The HMM Scoring Form's Example

The legacy site's example input for HMM scoring, human APOE.

| File | What it is | sha256 |
| ---- | ---------- | ------ |
| `apoe.fasta` | The HMM scoring help page's sequence (`tips_exampleHmmScoreInput_content.jsp`), its ten lines as written, under `>sequence`. That's the name `scoreAlignXml.cgi` gives a sequence pasted without a header (93 to 95). The page ends its lines in CRLF; this file in LF | `e1a6ca45e9377ec39a7cd19c4edc99649d5f73b98078d666cfd58ae291b68dd3` |

Its 317 residues are those of cSNP's `example/apoe.fasta`, from the cSNP help page. Each service's tests read their own copy, so a change to one service's example never changes the other's tests.

## `sample-hmmscan/`: The Example Against the Data Sample

`hmmscan --domtblout` for `example/apoe.fasta` against the hmmscore data sample (`hmmscore-sample-1`), in the engine image, without the table's `#` lines. Those lines hold the command, the paths and the date. `tests/test_hmmscore_sample_data.py` runs `hmmscan` again on each `engine-image` leg, and checks that its table is the committed one for that architecture. The tables guard the sample and HMMER, as cSNP's step-1 BLAST golden does; they aren't parity.

| File | Made on | sha256 |
| ---- | ------- | ------ |
| `amd64/apoe.domtblout` | `linux/amd64` | `51839c84371be515464d3627b7c72a1e8be96b1e49af8be17a0fa316a92714c9` |
| `arm64/apoe.domtblout` | `linux/arm64` | `51839c84371be515464d3627b7c72a1e8be96b1e49af8be17a0fa316a92714c9` |

**Why there are two.** HMMER 3.4 computes a few numbers differently on amd64 and arm64, from the same pressed files: on the full library, some scores differ in the last digit, and a domain near a cutoff can move ([the survey doc](../../../../docs/parity/hmmscore-library-survey.md#hmmscan-on-arm64)). For `hmmscore-sample-1`, the example's two tables happen to be the same, 11 lines. Each is still its own file, so a new sample or HMMER can make them differ without a test failing on one leg.

Its best hit is `PTHR18976.SF2.pir` at 439.0 bits, as on the full library. The E-values are smaller than the full library's, since `hmmscan` multiplies each P-value by the number of models searched: 456 in the sample, 144,361 in the library.

## Regenerating

`example/apoe.fasta` doesn't change.

Regenerate both `sample-hmmscan/` tables when the sample or HMMER changes, with the new sample in `.data/`. From the repository root, for each architecture, in an engine image built for it:

```sh
docker run --rm --platform linux/amd64 -v "$PWD/.data:/data:ro" \
  -v "$PWD/engine/tests/golden/hmmscore/example:/example:ro" <engine image for amd64> \
  sh -c 'hmmscan --domtblout /tmp/apoe.domtblout /data/hmmscore/19/globals/binHmm /example/apoe.fasta > /dev/null && grep -v "^#" /tmp/apoe.domtblout' \
  > engine/tests/golden/hmmscore/sample-hmmscan/amd64/apoe.domtblout
```

For arm64, `--platform linux/arm64`, an engine image built for arm64, and `arm64/` in the output's path. An Apple Silicon Mac runs both: Docker's emulated amd64 gives real amd64's numbers. Then update the sha256s above.
