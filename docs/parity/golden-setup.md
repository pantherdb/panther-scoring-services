# Golden Setup

How to run each service's reference and regenerate its golden files: `csnp`, `refmap` and `hmmscore` so far. The goldens themselves are in `engine/tests/golden/<service>/`, each folder with a README giving every file's source and sha256. Why each input is in the set is in [inputs.md](inputs.md).

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

## `refmap`

The reference is `map_panther.pl` at `pantherdb/RefProteomeMapper` `4fc6a09`. It's the same file on `master` (`649c85f`), in `panther-workspace`, and on `data.pantherdb.org` ([refmap-legacy-behaviour.md](refmap-legacy-behaviour.md)).

| Piece | Version |
| ----- | ------- |
| The script | `4fc6a09`, pinned by sha256 in the root `Dockerfile` |
| Perl | 5.40.1, Debian trixie's `perl` package `5.40.1-6+deb13u1`, as for `csnp` |
| The data | The PANTHER 19 release of 2024-06-20, pinned by `engine/src/panther_engine/refmap/data.json` ([engine.md](../testing/engine.md#the-refmap-data)) |

### The refmap Reference Image

`refmap-reference` is a test-only stage of the root `Dockerfile`, built from the `engine` stage: the engine, plus Debian's `perl` package and `map_panther.pl` in `/opt/refmap-reference/`. The runtime `api` image has neither. CI and compose never build it. From the repository root:

```sh
docker buildx build --load --target refmap-reference -t panther-refmap-reference .
```

- **The repository is public, so no checkout is needed.** A stage of its own, `refmap-reference-script`, downloads the script from GitHub at the full commit, so curl stays out of the image. The build needs the network.
- **The script is checked against its pinned sha256.** A script that differs fails the build, and `sha256sum` names it: `map_panther.pl: FAILED`.
- **There's no self-check,** unlike `csnp-reference`: no output of `map_panther.pl` was ever published to check against. The full run compares the Perl with the port on every line instead.
- **Building `engine` or `api` never downloads the script.**

### Regenerating the refmap Goldens

The cases are in `engine/tests/golden/refmap/cases.json`; why each is there is in [inputs.md](inputs.md#refmap). The image runs them with your working copy mounted over the engine and your data folder read-only, from the repository root:

```sh
docker run --rm -v "$PWD/engine:/work/engine" -v "$PWD/.data:/data:ro" \
  -e PANTHER_DATA_DIR=/data -e PYTHONDONTWRITEBYTECODE=1 --user "$(id -u):$(id -g)" \
  panther-refmap-reference panther-engine refmap parity reference
```

- **It writes `out/<case>.out`,** the script's standard output for each case, byte for byte, in about 2 s. It's sent to a file rather than captured as text, which would turn each carriage return into a line feed. A second run gives the same bytes.
- **The outputs go to a temporary folder first,** and into `out/` only once every case has run. If one case fails, `out/` is left as it was.
- **The data folder needs the refmap data.** It stops before running anything if a published organism's file is missing: the Perl reads a missing file as an empty one, and would answer `NOHIT` for every ID (`REFMAP-9`).
- **Update the checksums** in the golden folder's README, and commit `out/` with them. CI checks the port against it without Perl (`tests/test_refmap_golden.py`).

### The refmap Full Run

M1's acceptance for refmap's engine: every ID of every organism in the release, through both the Perl and the port. From the repository root, with the refmap data in `.data/`:

```sh
docker run --rm -v "$PWD/engine:/work/engine" -v "$PWD/.data:/data:ro" \
  -e PANTHER_DATA_DIR=/data -e PYTHONDONTWRITEBYTECODE=1 \
  panther-refmap-reference panther-engine refmap parity full
```

- **For each organism, one at a time,** it writes a list of every ID in the organism's file, in file order, then extras from a generator seeded with `port-refmap:<code>`: up to 20 of its IDs repeated, 20 lower-cased, 20 with `-2`, 20 with `.1`, and 20 from the next organism's file. The same data and seed give the same lists. `--seed` changes the seed.
- **It runs `map_panther.pl` on the list,** maps the same IDs with `map_ids()`, and compares each line's first two fields.
- **It prints each organism's IDs and differences** as it goes, the first 20 differences of each, and a total. It exits with status 1 if any line differs.
- **`--organism CODE`** runs only that organism; repeat it for more. Its extras still come from the next organism in the list, so a rerun of one organism checks the IDs the full run did, and that organism's file must be in the data folder too.
- **It writes nothing** outside the container's `/tmp`, so it needs no `--user`. On 2026-11-06 it took 81 s on an Apple Silicon Mac. The result is in [inputs.md](inputs.md#the-refmap-full-run).

## `hmmscore`

The reference is `pantherdb/pantherScoring` at `89ea0ae`: `scoreAlignXml.cgi`, what the website called, and the `pantherScore.pl` it runs ([hmmscore-legacy-behaviour.md](hmmscore-legacy-behaviour.md)), with production's HMMER, 3.1b2.

| Piece | Version |
| ----- | ------- |
| The scripts | `scoreAlignXml.cgi`, `pantherScore.pl` and `lib/` at `89ea0ae`, each pinned by sha256 in the root `Dockerfile` |
| Perl | 5.40.1, Debian trixie's `perl` package, as for `csnp`, with `libyaml-libyaml-perl` for YAML::XS, which the CGI reads its `config.yaml` with |
| HMMER | 3.1b2, Bioconda's `quay.io/biocontainers/hmmer:3.1b2--3` at digest `sha256:e7b1a7a131b7acd6546a6a77cfffc3007fc80f74f7b40b5c660fe29fda122158`, the survey's: `hmmscan`, `hmmsearch`, `hmmpress` and `hmmconvert`, in `/opt/hmmer-3.1b2/bin` |
| The data | The data sample `hmmscore-sample-1` for `sample/`; the full library, pinned by `engine/src/panther_engine/hmmscore/data.json`, for `full/` ([engine.md](../testing/engine.md#the-hmmscore-data-sample)) |

### The hmmscore Reference Image

`hmmscore-reference` is a test-only stage of the root `Dockerfile`, built from the `engine` stage: the engine and HMMER 3.4, plus Debian's `perl` and YAML::XS, HMMER 3.1b2's four tools, and the scripts in `/opt/hmmscore-reference/`. The runtime `api` image has none of them. CI and compose never build it. It's **amd64 only**: 3.1b2 has no arm64 build with vector code, and the Bioconda image is amd64's alone. An Apple Silicon Mac builds and runs it under Docker's emulated amd64.

`pantherdb/pantherScoring` is private, so the scripts come from your checkout, as a named build context, as for `csnp`. From the repository root, with `pantherScoring` at `../panther-workspace/legacy/pantherScoring`:

```sh
scripts="$(mktemp -d)"
git -C ../panther-workspace/legacy/pantherScoring archive 89ea0ae \
  scoreAlignXml.cgi pantherScore.pl lib | tar -x -C "$scripts"
docker buildx build --platform linux/amd64 --load \
  --build-context hmmscore-reference-scripts="$scripts" \
  --target hmmscore-reference -t panther-hmmscore-reference .
```

- **Each file is checked against its pinned sha256,** and the folder must hold those twelve files and no other. A file that differs fails the build, and `sha256sum` names it: `pantherScore.pl: FAILED`.
- **The stage checks that each HMMER tool runs** on the engine's Debian, and reports 3.1b2. If a later Bioconda image didn't, the fallback is building 3.1b2 from the survey's source tarball ([the survey](hmmscore-library-survey.md#hmmer-31b2-against-34)).
- **Building any other stage on arm64 never pulls the 3.1b2 image,** and building this one for arm64 fails, saying it's amd64 only.

### Regenerating the hmmscore Goldens

The cases are in `engine/tests/golden/hmmscore/parity/cases.json`; why each is there is in [inputs.md](inputs.md#hmmscore). The image runs them with your working copy mounted over the engine and your data folder read-only, from the repository root:

```sh
docker run --rm --platform linux/amd64 -v "$PWD/engine:/work/engine" -v "$PWD/.data:/data:ro" \
  -e PANTHER_DATA_DIR=/data -e PYTHONDONTWRITEBYTECODE=1 --user "$(id -u):$(id -g)" \
  panther-hmmscore-reference panther-engine hmmscore parity reference
```

- **The self-check comes first:** `pantherScore.pl` on the example must give one line, `PTHR18976:SF2` at 439.0 bits, as the survey and `sample-hmmscan/amd64/apoe.domtblout` say. It catches an image that reads the library wrongly. Nothing is written unless it passes.
- **For each case, one at a time,** in a fresh folder holding the CGI's `config.yaml` and links to the scripts, which the CGI finds by relative path:
  1. the CGI, run with `REQUEST_METHOD=POST` and posted `sequence=<text>` on standard input. Its output, without the `Content-type` header, is `cgi.xml`;
  2. `pantherScore.pl -l <library> -D B -n -i <query> -o best.tsv -H /opt/hmmer-3.1b2/bin`, the CGI's command with `-n` for the names. `best.tsv` lists every tied best ID, where the CGI shows only the first;
  3. `hmmsearch` of the model file at each ID in `best.tsv`, as the CGI runs it, into `hmmsearch/`.

  One at a time, because `pantherScore.pl` writes `hmmscan`'s table to a fixed `/tmp/temp.domtblout` (`HMMSCORE-7`). Each case's outputs replace its folder in `sample/` only once it has run; a case that fails leaves its goldens as they were.
- **`--goldens sample`, the default,** has 3.1b2 read its own presses of the sample's models, as in the survey's task 10.1: `hmmconvert` turns `binHmm.h3m` back to text, `hmmpress` presses it, and `names.tab` and `books/` are linked beside it, since `FamLibBuilder::exists` needs both folders. The sample's own pressed files are 3.4's.
- **`--case NAME`** runs one case; repeat it for more. **`--data-dir`** overrides `PANTHER_DATA_DIR`.
- **It takes about 30 s** for the fifteen cases on an Apple Silicon Mac. The reports end with the run's CPU time, so a second run gives the same `best.tsv` and the same alignments, but not the same bytes. A tie's `best.tsv` and `cgi.xml` can list its IDs in another order.
- **Then check the port against them,** in the engine image, natively on each architecture, and in the reference image for amd64:

  ```sh
  docker compose run --rm -T engine panther-engine hmmscore parity check
  ```

  It prints each case's time, every difference, and how many cases match, and exits with status 1 if any differs. CI runs the same comparison in `tests/test_hmmscore_parity.py`, on both `engine-image` legs. Where a case's arm64 result differs from the amd64 golden, save the port's arm64 result as `sample-arm64/<case>.json` with `parity.write_result`, and list what differs in the golden folder's README.
- **Update the sha256s** in the golden folder's README, and commit `sample/` with them.

### The hmmscore Staging Run

M1's acceptance for hmmscore's engine: the same cases on the full library, into `full/`, on an amd64 machine with the full library verified (`panther-engine hmmscore data verify`, [engine.md](../testing/engine.md#the-hmmscore-full-library)) and the reference image. With the library's data folder at `/full-data`:

```sh
docker run --rm -v "$PWD/engine:/work/engine" -v /full-data:/data:ro \
  -e PANTHER_DATA_DIR=/data -e PYTHONDONTWRITEBYTECODE=1 --user "$(id -u):$(id -g)" \
  panther-hmmscore-reference sh -c '
    panther-engine hmmscore parity reference --goldens full &&
    panther-engine hmmscore parity check --goldens full'
```

- **3.1b2 reads the library's shipped pressed files** for `full`, as production's did; nothing is pressed.
- **The time limit:** in fresh processes, time `titin-10000` and the example with `panther-engine hmmscore score --usage --cpu 0` ([engine.md](../testing/engine.md#scoring-from-the-command-line)), for #68 and the survey's timing section.
- **Record the machine, the date and the result** in [inputs.md](inputs.md#the-hmmscore-staging-run), and commit `full/` with its sha256s in the golden folder's README.

### The hmmscore Staging Run Under Apptainer

On a cluster without Docker, such as CARC's Endeavour, where the survey fetched and measured the full library, the same image runs through Apptainer. Below, `<scratch>` is a folder on the cluster's scratch file system, and `<data>` is the data folder holding `hmmscore/19/`.

1. **On a machine with Docker,** build the image as in [The hmmscore Reference Image](#the-hmmscore-reference-image). Then save its amd64 image, and copy it over:

   ```sh
   docker save --platform linux/amd64 -o hmmscore-reference.tar panther-hmmscore-reference
   rsync -z --progress hmmscore-reference.tar <cluster>:<scratch>/
   ```

2. **On the cluster, on a compute node** (`salloc`), clone the branch, and convert the image. Keep Apptainer's cache and temporary files on scratch, not in your home folder:

   ```sh
   cd <scratch>
   git clone --branch <branch> https://github.com/pantherdb/panther-scoring-services.git
   export APPTAINER_CACHEDIR="$PWD/apptainer-cache" APPTAINER_TMPDIR="$PWD/apptainer-tmp"
   mkdir -p "$APPTAINER_CACHEDIR" "$APPTAINER_TMPDIR"
   module load apptainer    # if apptainer isn't on PATH
   apptainer build hmmscore-reference.sif docker-archive://hmmscore-reference.tar
   ```

3. **Run it all as one job,** with `sbatch` from `<scratch>`. It writes `full/` into the clone:

   ```bash
   #!/bin/bash
   #SBATCH --account=<account>
   #SBATCH --partition=<partition>
   #SBATCH --nodes=1
   #SBATCH --exclusive
   #SBATCH --mem=0
   #SBATCH --time=06:00:00
   #SBATCH --output=hmmscore-staging-%j.log
   set -euo pipefail
   data=<data>

   run() {
     apptainer exec --cleanenv \
       --bind "$PWD/panther-scoring-services/engine:/work/engine" --bind "$data:/data:ro" \
       --env PANTHER_DATA_DIR=/data --env PYTHONDONTWRITEBYTECODE=1 \
       --pwd /work/engine hmmscore-reference.sif "$@"
   }

   hostname; lscpu | grep -E '^(Model name|CPU\(s\)):'; free -g | sed -n 2p; date -u
   run panther-engine hmmscore data verify
   run panther-engine hmmscore parity reference --goldens full
   run panther-engine hmmscore parity check --goldens full || echo "parity check exited with status $?"
   for query in tests/golden/hmmscore/example/apoe.fasta tests/golden/hmmscore/parity/inputs/titin-10000.txt; do
     for attempt in 1 2; do
       echo "== $query, run $attempt"
       run panther-engine hmmscore score --usage --cpu 0 "$query" > /dev/null
     done
   done
   ```

   - **The whole node:**
     - The timings shouldn't share CPUs.
     - `pantherScore.pl` passes `hmmscan` no `--cpu`, so 3.1b2 starts a thread for each core, and each thread adds memory.
     - To compare with the survey's timings, run on its node type, an AMD EPYC 7513 (`--nodelist`).
   - **`data verify` comes first,** and the job stops if the library fails it. It took about 96 minutes on Endeavour's BeeGFS. The whole job took about 3 hours on 2026-11-17, on `b11-19`, the survey's node.
   - **Apptainer runs as you,** so `--user` isn't needed. It doesn't use the image's working directory, hence `--pwd`. `--cleanenv` keeps the cluster's environment, such as its Python variables, out of the container.
   - **Each `score` is a fresh process.** Its `--usage` lines go to the log, on standard error. The first of each pair may read the pressed files cold.

4. **Bring `full/` and the log back** to your checkout, then record and commit them as above:

   ```sh
   rsync -a <cluster>:<scratch>/panther-scoring-services/engine/tests/golden/hmmscore/parity/full/ \
     engine/tests/golden/hmmscore/parity/full/
   ```
