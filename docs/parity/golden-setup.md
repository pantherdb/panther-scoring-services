# Golden Setup

How to run each service's reference and regenerate its golden files. Only `csnp` has one so far. The goldens themselves are in `engine/tests/golden/<service>/`, each folder with a README giving every file's source and sha256. Why each input is in the set is in [inputs.md](inputs.md).

## `csnp`

The reference is the legacy pipeline at `pantherdb/cSNP_analysis` `cebb5ab`: `parse_blastp.pl` (step 2) and `PANTHER_PSEP1.01.pl` (step 3). Step 1 is BLAST+ itself.

| Piece | Version |
| ----- | ------- |
| The scripts | `cebb5ab`, each pinned by sha256 in the root `Dockerfile` |
| Perl | 5.40.1, Debian trixie's `perl` package `5.40.1-6+deb13u1` |
| BLAST+ | 2.17.0, the engine image's ([tech-stack.md](../design/tech-stack.md#pinning-tool-versions)) |
| `sort` | GNU coreutils, in the C locale (`LC_ALL=C`), for step 2's ranking |
| PAML library | `PAML_RST.tar.gz`, production's build, sha256 in the legacy behaviour spec §7.1 |
| BLAST database and species tree | The PSEP 1.01 release's, sha256 in spec §7.1 |

### The Reference Image

`csnp-reference` is a test-only stage of the root `Dockerfile`, built from the `engine` stage: the engine and BLAST+, plus Debian's `perl` package and the three legacy scripts in `/opt/csnp-reference/`. The runtime `api` image never contains either; like every image from the Python base, it has only Debian's Essential `perl-base`. CI and compose never build it.

`pantherdb/cSNP_analysis` is private, so the image can't clone it. The scripts come from your checkout instead, as a named build context. From the repository root, with `cSNP_analysis` at `../panther-workspace/legacy/cSNP_analysis`:

```sh
scripts="$(mktemp -d)"
git -C ../panther-workspace/legacy/cSNP_analysis archive cebb5ab \
  run_blastp.pl parse_blastp.pl PANTHER_PSEP1.01.pl | tar -x -C "$scripts"
docker buildx build --load --build-context csnp-reference-scripts="$scripts" \
  --target csnp-reference -t panther-csnp-reference .
```

- **`git archive` only reads the checkout,** so `panther-workspace` stays untouched, whatever branch it's on.
- **Each script is checked against its pinned sha256.** A script that differs fails the build, and `sha256sum` names it: `PANTHER_PSEP1.01.pl: FAILED`.
- **Building `engine` or `api` never needs the context.**

### Running It

The image runs the engine's `panther-engine csnp parity` commands, with your working copy mounted over the engine and your data folder read-only, as compose does for the `engine` service:

```sh
docker run --rm -v "$PWD/engine:/work/engine" -v "$PWD/.data:/data:ro" \
  -e PANTHER_DATA_DIR=/data -e PYTHONDONTWRITEBYTECODE=1 --user "$(id -u):$(id -g)" \
  panther-csnp-reference panther-engine csnp parity reference tests/golden/csnp/generated
```

- **`--user "$(id -u):$(id -g)"`** makes you the owner of the files it writes, as for `sample fetch` ([engine.md](../testing/engine.md#the-csnp-data-sample)).
- **The data folder needs the cSNP data sample,** or the full data. Fetch the sample first.
- **Each Perl run gets a fresh working folder,** with a link to the data folder's species tree: `PANTHER_PSEP1.01.pl` opens it by relative path (`RUN-1`), and `parse_blastp.pl` writes `./<species>` (`MAP-2`).

### The Self-Check

`parity reference` always starts with the self-check, and runs nothing else unless it passes. The spec's own inputs must give the spec's goldens, byte for byte:

- **§7.3:** steps 2 and 3 on `release/HUMAN` and `release/sample.input`, with species `HUMAN`, give `spec/sample.out`;
- **§7.5:** step 2 on `release/HUMAN` and `spec/edge-cases.input`, with species `NA`, then step 3, give `spec/edge-cases.out`.

It catches a Perl that reads the scripts differently from production's. When it passes, it saves both step-2 outputs as `generated/sample.snpparse` and `generated/edge-cases.snpparse`. It takes about 40 s.

### Regenerating the Goldens

Regenerate when the sample, the generator or the defaults change. From the repository root:

```sh
(cd engine && rm -rf tests/golden/csnp/generated/step2 tests/golden/csnp/generated/step3 \
  && uv run panther-engine csnp parity cases tests/golden/csnp/generated --data-dir ../.data)
docker run --rm -v "$PWD/engine:/work/engine" -v "$PWD/.data:/data:ro" \
  -e PANTHER_DATA_DIR=/data -e PYTHONDONTWRITEBYTECODE=1 --user "$(id -u):$(id -g)" \
  panther-csnp-reference panther-engine csnp parity reference tests/golden/csnp/generated
(cd engine && uv run panther-engine csnp parity check tests/golden/csnp/generated --data-dir ../.data)
```

1. **`parity cases`** writes the cases: for each family, step-3 cases grouped by gene, and the step-2 runs. The seed is `port-csnp`, with 5 genes and 8 positions per family; `--seed`, `--genes` and `--positions` change them. The same data and seed give the same files. It takes about 8 s for the sample.
2. **`parity reference`** runs them through the Perl, one process per family, and writes each output beside its input. About 5 minutes for the sample, most of it reading `PTHR11695`'s 136 MB `.paml` once per gene.
3. **`parity check`** runs the port on every case and the self-check's inputs, and compares. It lists every case that differs, by family and SNP id, and the kinds of node the walks stopped at. It exits with status 1 if any case differs.

Then commit `engine/tests/golden/csnp/generated/`. CI checks the port against it without Perl (`tests/test_csnp_golden.py`).

### The Step-1 Golden

`blast/` holds the BLAST+ 2.17.0 output for the three sample proteins and the form's example against the sample's database, with the query named `P0001` as the service names it. It doesn't come from the legacy: the legacy BLAST+ version is unknown. It guards against a later BLAST+ picking a different best hit. Regenerate it in the engine image, from the repository root:

```sh
docker compose run --rm -T engine python -c '
from pathlib import Path
from panther_engine.csnp import blast
from panther_engine.csnp.parity import write
golden = Path("tests/golden/csnp")
for fasta in ("release/sample.fasta", "example/apoe.fasta"):
    for block in (golden / fasta).read_text().split(">")[1:]:
        name, _, sequence = block.partition("\n")
        lines = blast.search("".join(sequence.split()), Path("/data/csnp/9"))
        write(golden / f"blast/{name.strip()}.csv", "".join(lines))
'
```

### The Form's Example

`example/` holds the scoring form's example, human APOE with four substitutions, and the Perl's output for it: steps 2 and 3 on its step-1 golden, `blast/APOE.csv`. Why it's in the set is in [inputs.md](inputs.md#the-forms-example). Regenerate the output in the reference image, after the step-1 golden, from the repository root:

```sh
docker run --rm -v "$PWD/engine:/work/engine" -v "$PWD/.data:/data:ro" \
  -e PANTHER_DATA_DIR=/data -e PYTHONDONTWRITEBYTECODE=1 --user "$(id -u):$(id -g)" \
  panther-csnp-reference python -c '
from pathlib import Path
from panther_engine.csnp import parity
golden, data = Path("tests/golden/csnp"), Path("/data/csnp/9")
reference = parity.Reference.find()
differences = parity.self_check(reference, golden, data, None)
if differences:
    raise SystemExit("\n".join(differences))
example = golden / "example"
blast, snps = parity.read(golden / "blast/APOE.csv"), parity.read(example / "apoe.input")
snpparse = reference.step2(blast, snps, "HUMAN")
parity.write(example / "apoe.snpparse", snpparse)
parity.write(example / "apoe.out", reference.step3(snpparse, data))
'
```

- **The self-check runs first,** as in `parity reference`: if the image doesn't reproduce spec §7.3 and §7.5, it writes nothing. It takes about a minute in all.
- **It's a command, not a `parity` subcommand:** the example is one fixed input, and `parity reference` also serves the staging run, which mustn't write into the committed goldens (`add-apoe-to-csnp-sample`, design decision 4).

### The Staging Run on the Full Library

M1's acceptance is the same three commands on the full data ([engine.md](../testing/engine.md#using-the-full-library)), into a folder of their own rather than the committed goldens:

```sh
panther-engine csnp parity cases /parity/full --data-dir /full-data
panther-engine csnp parity reference /parity/full --data-dir /full-data --golden /work/engine/tests/golden/csnp
panther-engine csnp parity check /parity/full --data-dir /full-data --golden /work/engine/tests/golden/csnp
```

- **The cases** are generated from every family in the library: 8,607 families, about 360,000 cases with the defaults. The generator reads each `.paml` once.
- **The Perl** reads each family's `.paml` once per gene: about 3 hours for the defaults, on 17 GB of `.paml`. `--family` limits a run to some families, for a rerun.
- **The report** of `parity check` goes in `docs/parity/`, as a dated record of the run.
