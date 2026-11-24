# treegrafter Golden Files

The files the `treegrafter` tests compare against, and the inputs that produce them. Every file here is stored byte for byte (`-text` in `.gitattributes`).

## `example/`: The Site's Example

| File | What it is | sha256 |
| ---- | ---------- | ------ |
| `apoe.fasta` | Human APOE, the sequence search form's example, under `>sequence`: a copy of hmmscore's `example/apoe.fasta`, which says where it's from | `e1a6ca45e9377ec39a7cd19c4edc99649d5f73b98078d666cfd58ae291b68dd3` |

Each service's tests read their own copy, so a change to one service's example never changes the other's tests.

## The Cases

`cases.json` lists each case and why it's there, and `inputs/<case>.txt` is the engine's sequence, as the API sends it: no header, no whitespace, upper case, and no final line feed. Why each case is in the set is also in [inputs.md](../../../../docs/parity/inputs.md#treegrafter). `cases.json`'s sha256 is `e7cf3fd4f712770cc2edb82db81a2279088c4c328751bce57fbb1d6df6245aba`.

| File | Made from | sha256 |
| ---- | --------- | ------ |
| `apoe.txt` | `example/apoe.fasta`, normalised as the API does: the header and line breaks removed. The same as hmmscore's `apoe.txt` | `eddd8b84fbb094df0b4067ca1d0b9b137ddaee4f8b3a548fcff5152e92a4dd4b` |
| `hbb.txt` | Human HBB, `https://rest.uniprot.org/uniprotkb/P68871.fasta` (sha256 `a976e8ef07b298781398d4a66d52ddf13b796e991baa7e4e499732ecc6689107` on 2026-11-24), normalised | `9ebf320eb707d71644444fe5006ed58af56a0bf0ec9568eb6a3a65e0e8191465` |
| `hba.txt` | Human HBA, `https://rest.uniprot.org/uniprotkb/P69905.fasta` (sha256 `aecc3cb75f840f242f6b4489d501384d0c50cf0d61a8dab5a1dab81a80aa4bae` on 2026-11-24), normalised | `14725a10598943a7aa719eed7d24c7fee599192a6c63c75b051ee6f156341242` |
| `pthr11034.txt` | Human NDRG1, a leaf of PTHR11034's tree, `https://rest.uniprot.org/uniprotkb/Q92597.fasta` (sha256 `3adb3dfd65056d7b0a7f6d3b89e596b94ea623fe96aa61bb858f13923899e236` on 2026-11-24), normalised | `e60fb3a5a1c9eb9cd1346cd7a533c0e72c427662cbc56d6bf46659a7639d058c` |
| `apoe-hbb.txt` | `apoe.txt`, then `hbb.txt` | `92b75ae2846412b6fd3c70c8c57e8c73be2f241283dba941cbe5078942f79f28` |
| `apoe-peptide60.txt` | `apoe.txt`'s residues 91 to 150 | `1a2ad7cca51de067fc14342663467a462de43ffd8cebcb635e94e9467bfa7984` |
| `random300.txt` | 300 residues drawn from the 20 standard amino acids by Python's `random.Random(20261124).choices("ACDEFGHIKLMNPQRSTVWY", k=300)` | `832660b384001b98a53f526dde4cc51ac63d36d3688d1e52084f54803a944b3e` |
| `apoe-stop.txt` | `apoe.txt` and a final `*`. The same as hmmscore's | `b64a04acd0982ec17f0f01ff62473bfa5661bb38fac5410c494264ce75f3d643` |
| `apoe-dot.txt` | `apoe.txt` with a `.` after residues 80, 160 and 240. The same as hmmscore's | `f0badc8ce30618d1012d270197e282394e79900363b70ef852db700b8fdc734a` |
| `apoe-underscore.txt` | `apoe.txt` with a `_` after residues 80, 160 and 240. The same as hmmscore's | `2596905a7905a695625c314d2f5bbf428a318169994de5d976b8d2f0c2a4cae4` |
| `apoe-star.txt` | `apoe.txt` with a `*` after residues 80, 160 and 240. The same as hmmscore's | `86a194dff090e9f696d3025a81fc7dd7af3e1c91c3f6f8bbf966af282460f17e` |
| `apoe-uncommon.txt` | `apoe.txt` with `B`, `J`, `O`, `U`, `X` and `Z` in place of residues 50, 100, 150, 200, 250 and 300. The same as hmmscore's | `bc05a1b391135bb9d561ec820158d61998319d305e0e2d1be488a19e19931560` |

## `parity/`: The Goldens

What EBI's command line answered, for `tests/test_treegrafter_parity.py` and `panther-engine treegrafter parity check`. The reference is EBI's `treegrafter` at the commit `engine/pyproject.toml` pins, in the engine image, with HMMER 3.4 and EPA-ng 0.3.8: `hmmsearch` with `treegrafter.sh`'s flags, then `treegrafter run -e 0.00000001 --print-go` ([golden-setup.md](../../../../docs/parity/golden-setup.md#treegrafter)). Each case's `result.tsv` is that command's output, the header and a row, or the header alone for no hit.

- **`parity/fixture/`:** made on the committed fixture, `../../fixtures/treegrafter/`, with release 2026-08-28, on `linux/amd64`, on 2026-11-24, by `panther-engine treegrafter parity reference`. The engine matched every case on both `linux/amd64` and `linux/arm64`, so there's no `fixture-arm64/` copy.

| Case | `result.tsv`'s sha256 |
| ---- | --------------------- |
| `apoe` | `ce64b1ec82ed9ad421f09ccfb6d319befed18311e8d5893d4d50d6d48eda8b42` |
| `hbb` | `a875a77c496cd4e9bde569353704db5b5954ba38a5fde4bdc54eee5af3d07618` |
| `hba` | `38281d7cf3cf3c404611612eb67a7aafefdbe55e51a5771ff78543d814420f83` |
| `pthr11034` | `7d862469559556f226b0dced6c4cdd978e7597eb8c49a2ca1d40e27afc2ad894` |
| `apoe-hbb` | `7d5f701800d123f33ef36f4070033f238a4a251f13e4288100020514f8d917a8` |
| `apoe-peptide60` | `e51dec7a593a60b31c0fea9c2f82bf97e3739e1e4c67b6f909839c251a62986e` |
| `random300` | `e51dec7a593a60b31c0fea9c2f82bf97e3739e1e4c67b6f909839c251a62986e` |
| `apoe-stop` | `dfa768bb5c6eb802139a79192ac6a37ba8a110941752fe9568b41f9f5377b552` |
| `apoe-dot` | `3173b726b4ed9e7a932dbd051dbe3a7948294f4ef94534fd8b0c987c710fcdc9` |
| `apoe-underscore` | `3173b726b4ed9e7a932dbd051dbe3a7948294f4ef94534fd8b0c987c710fcdc9` |
| `apoe-star` | `3173b726b4ed9e7a932dbd051dbe3a7948294f4ef94534fd8b0c987c710fcdc9` |
| `apoe-uncommon` | `eaa924d8d198c4e4b5a6f198524920e7f4340f5405cf75656577dee13e286f5b` |
