# refmap Golden Files

The reference outputs the `refmap` port must match, and the inputs that produced them. The reference is RefProteomeMapper's `map_panther.pl` at `4fc6a09`, run in the `refmap-reference` image against the pinned PANTHER 19 release (`src/panther_engine/refmap/data.json`). How they are made, and why each case is in the set, is in [docs/parity/](../../../../docs/parity/README.md): `golden-setup.md` and `inputs.md`.

Every file here is stored byte for byte (`-text` in `.gitattributes`). `cases/crlf.classification` and `cases/list-endings.list` carry carriage returns on purpose, and `cases/non-ascii-id.list` a Latin-1 byte.

| Path | What it holds |
| ---- | ------------- |
| `cases.json` | Each case: its name, what it shows, its ID list, and either an organism, whose classification file is in the data folder, or a made-up classification file here. A case the port refuses names the error it raises and its row in `docs/parity/divergences.md` |
| `release/` | The data server's test lists, unchanged |
| `cases/` | The hand-made ID lists and the made-up classification files |
| `out/` | `map_panther.pl`'s standard output for each case, byte for byte |

The port's mapping for each ID must equal the first two fields of its line in `out/`, with `NOHIT` for none. For a refused case, the port must raise the named error instead, and `out/` keeps the reference's answer as a record.

## `release/`: The Data Server's Test Lists

Downloaded unchanged on 2026-11-06 from `https://data.pantherdb.org/ftp/generic_mapping/`. The same bytes are in `archive/2024-06-20/`, beside the pinned release.

| File | What it is | sha256 |
| ---- | ---------- | ------ |
| `release/test_geneList` | The README's test list: 450 ENDPU IDs, one per line | `c8cc106c29eaa36dc8adbd922892f9b49c818b0ba06a56b6dc2366926f19f898` |
| `release/test_geneList_values` | All 9,228 ENDPU IDs, each with a value in a second column, for the enrichment test | `03eeed52065a039dcb915c4fde789a65a354dfa2357ca939249152f2fd6fc841` |

## `cases/`: Written by Hand

Written for `port-refmap` on 2026-11-06. `cases/missing.classification` is never created: the `missing-file` case is about its absence.

| File | What it is | sha256 |
| ---- | ---------- | ------ |
| `cases/repeats.list` | The IDs of `repeats` | `3a6e92f31ba3a69d843568e04ea28cf6586d5c288ddf91b1a8585a886ebfe96e` |
| `cases/case-and-suffixes.list` | The IDs of `case-and-suffixes` | `b744a5688e20ce0550d73bb3def45f9ef3192c8f4c8cd70346bdc0b144bee56d` |
| `cases/first-unmapped.list` | The IDs of `first-unmapped` | `423685144a36f280b8ceeedeae00e5f312f72baec1735561c67bd1e41f4a9ace` |
| `cases/other-organism.list` | The IDs of `other-organism` | `c52c94e5674d0ae2ea5cb46951f241e22a6f4f786fb5b601aca90f94f282ee0f` |
| `cases/punctuation.list` | The IDs of `punctuation` | `fc2b407a4d0a5d1ba269abe9f568cb3b92434727b2ba6b271cfd3ffb477e41f9` |
| `cases/list-endings.list` | The IDs of `list-endings` | `a857362a97922d31c116334a306539244d8a8147879b326b6165ce801aec7d61` |
| `cases/repeated-id.list` | The IDs of `repeated-id` | `8e8c404fefd43bca8f0e9487a8391b905570c9a08e665e46871d4f380414ba53` |
| `cases/repeated-id.classification` | The made-up classification file of `repeated-id` | `1b55306da94220f8fb16e22f9b28ee78f5772d61bb802310a81ffff80b857f86` |
| `cases/crlf.list` | The IDs of `crlf` | `46ba2c66718bada7bfcbbd9ffa2cc1933232f227ee5e1b4229554346bc5964d1` |
| `cases/crlf.classification` | The made-up classification file of `crlf` | `69bf1a65e086a0243ee3e9037304672a1192784a111afb8e481dc5709a03500e` |
| `cases/no-second-field.list` | The IDs of `no-second-field` | `420079b13b4cc0ec19317d7f291dccbdda77bd485ed76befc86e2b5adb81d5c4` |
| `cases/no-second-field.classification` | The made-up classification file of `no-second-field` | `89520648a5073be3525cd1342623e56dce283127fbd72f0e8a7d8a33cb434c1c` |
| `cases/empty-second-field.list` | The IDs of `empty-second-field` | `8e8c404fefd43bca8f0e9487a8391b905570c9a08e665e46871d4f380414ba53` |
| `cases/empty-second-field.classification` | The made-up classification file of `empty-second-field` | `e1fa9694d5c4929d9469a8e112c073b03970be526d0001787a8093d0dced6b3a` |
| `cases/third-field.list` | The IDs of `third-field` | `8e8c404fefd43bca8f0e9487a8391b905570c9a08e665e46871d4f380414ba53` |
| `cases/third-field.classification` | The made-up classification file of `third-field` | `f2f72d582383f05d1aee408164222dfb107832e3b726a46117f123184997936c` |
| `cases/stored-nohit.list` | The IDs of `stored-nohit` | `420079b13b4cc0ec19317d7f291dccbdda77bd485ed76befc86e2b5adb81d5c4` |
| `cases/stored-nohit.classification` | The made-up classification file of `stored-nohit` | `0bf0d35be9376a0f5ddce3ecdc4169ae6ffa636520d7bd23764048474ce875be` |
| `cases/no-final-line-feed.list` | The IDs of `no-final-line-feed` | `8e8c404fefd43bca8f0e9487a8391b905570c9a08e665e46871d4f380414ba53` |
| `cases/no-final-line-feed.classification` | The made-up classification file of `no-final-line-feed` | `3ae9f63a0a1cf8ea5550208a3998be3c158a1047d4accb720c5e4e56b7a93ca4` |
| `cases/empty-line.list` | The IDs of `empty-line` | `93f2dd6ada5d1ff84c897fef9a9ef83ac761cc04d861685554e88c9c65b699ff` |
| `cases/space-in-id.list` | The IDs of `space-in-id` | `11c7f318536c1800bcb475cfd729a0d50e431155e84cc2277191723cfd380bf3` |
| `cases/id-too-long.list` | The IDs of `id-too-long` | `8e6706777c7045979d473d09e5605d14d5345e7075aecd05fe7f659874a9f873` |
| `cases/non-ascii-id.list` | The IDs of `non-ascii-id` | `a4b19b5ca95f5c68c6d6f66626ba7477413e75735f16e50ccdd8d2c00dc3dffa` |
| `cases/unknown-organism.list` | The IDs of `unknown-organism` | `a92fc5dea9132d4c3d32b401905920ca19c63762470f0d1f866e2a69c44c99e3` |
| `cases/missing-file.list` | The IDs of `missing-file` | `c8a1eb658c3ee2385c5357cf0ed8d6fc7a6e22477e6d5a1bbc17e46b0ad3c915` |

## `out/`: The Reference's Output

Written by `panther-engine refmap parity reference` in the `refmap-reference` image, with Perl 5.40.1, on 2026-11-06. Running it again gives the same bytes.

| File | Case | sha256 |
| ---- | ---- | ------ |
| `out/test_geneList.out` | `test_geneList` | `8c2acd874802e620a6448dd3ac0aa28e4a3fcc67c26b5d91db0f097c401e7cf9` |
| `out/test_geneList_values.out` | `test_geneList_values` | `0b6cb74010a692240e68311e92860eda74472833d0fbd7e283b024b82e936ac4` |
| `out/repeats.out` | `repeats` | `722b6ee1bed23c1b0e1805556c73247b2c2e8f2e94765f0f794ad9c742dffd37` |
| `out/case-and-suffixes.out` | `case-and-suffixes` | `8178c99da594f51011a70ef87cd87d2bf551b89ab3fa3406b410e91443e42f6d` |
| `out/first-unmapped.out` | `first-unmapped` | `ddf20713c40497573e93ee0b166a4127e28577cc1f0c868397d6b755aa20fab3` |
| `out/other-organism.out` | `other-organism` | `540e85eb29e40cbf59e9eeb7b82ac2cd26180ecffcb3b658a7117d46783a71c3` |
| `out/punctuation.out` | `punctuation` | `e5fc2cfd9741b18877464582b73f5a901b134de8b2fcde118121dd38851d9f2f` |
| `out/list-endings.out` | `list-endings` | `e368535a3092f9bb21e4f8c87d5c24f4e8bdb43f7a8207383bf03e55913d4498` |
| `out/repeated-id.out` | `repeated-id` | `f31353c69a7fcb3bb9b96064b71acca4313bd4b3c939bf94e4096f792447f50d` |
| `out/crlf.out` | `crlf` | `1b7440f6e1c630269ea774990e9fa3767f2a2039aab9243a472dc5b5f9949b16` |
| `out/no-second-field.out` | `no-second-field` | `88e55d65409978854617b4cf2cd7235d7d95a8edf6c06954aacde2d544624085` |
| `out/empty-second-field.out` | `empty-second-field` | `f95d86a5b8c74c795f0b761085145619226cd90efcdbaec02de041162d82a082` |
| `out/third-field.out` | `third-field` | `d93150f16a6eb97bd21259dba352038c0d4dec1281576c33f27696cb4847581b` |
| `out/stored-nohit.out` | `stored-nohit` | `a0de22f73d2a708821ce65c1438a4219c2ac1b23c4506c50e5d496a3e389e04e` |
| `out/no-final-line-feed.out` | `no-final-line-feed` | `34a7f1482aa07dc72c718602619261e136ee3d0dec5f45dd25a05076b10175c5` |
| `out/empty-line.out` | `empty-line`: refused by the port, divergence 10 | `22b03fc56a7ed448ba5e9d40c9ae3a8a2a9666916f8b34a644739de61d592183` |
| `out/space-in-id.out` | `space-in-id`: refused by the port, divergence 10 | `3bc850cf0b432efb46291d915c53942d1529cab415c04f230f1cb961f252575e` |
| `out/id-too-long.out` | `id-too-long`: refused by the port, divergence 10 | `178be001c382326833a24b2aef5ed300533faad62d8eb808a53d482e149ab1e2` |
| `out/non-ascii-id.out` | `non-ascii-id`: refused by the port, divergence 10 | `9f7739ad473ad31985438001d2ae9762ab5327a60230270b5e5fe5139780d3b7` |
| `out/unknown-organism.out` | `unknown-organism`: refused by the port, divergence 9 | `0c5d7be678a51ca8b63fc39086c4d53d11822589c5cffb990a3e6cea1a4ad9b0` |
| `out/missing-file.out` | `missing-file`: refused by the port, divergence 9 | `d40b386186a8ea17d67e88d8c7671cd5d63cb52d780362afe99a17c23fb4a88c` |

## Regenerating

From the repository root, with the refmap data fetched into `.data/`, after building the image ([golden-setup.md](../../../../docs/parity/golden-setup.md#refmap)):

```sh
docker run --rm -v "$PWD/engine:/work/engine" -v "$PWD/.data:/data:ro" \
  -e PANTHER_DATA_DIR=/data -e PYTHONDONTWRITEBYTECODE=1 --user "$(id -u):$(id -g)" \
  panther-refmap-reference panther-engine refmap parity reference
(cd engine && uv run panther-engine refmap parity check --data-dir ../.data)
```

Then update the checksums here, and commit `out/` with them.
