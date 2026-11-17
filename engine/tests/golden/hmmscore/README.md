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

## `parity/`: The Goldens

What the legacy service answered, for `tests/test_hmmscore_parity.py` and `panther-engine hmmscore parity check`. The reference is `pantherScoring`'s `scoreAlignXml.cgi` and `pantherScore.pl` at `89ea0ae`, with HMMER 3.1b2, in the `hmmscore-reference` image on `linux/amd64` ([golden-setup.md](../../../../docs/parity/golden-setup.md#hmmscore)). Why each case is in the set is in [inputs.md](../../../../docs/parity/inputs.md#hmmscore).

### The Inputs

`cases.json` lists each case, why it's there, and, for `apoe-lower` alone, the text the CGI is posted where it isn't the engine's. `inputs/<case>.txt` is the engine's sequence, as the API sends it: no header, no whitespace, upper case, and no final line feed. `cases.json`'s sha256 is `c9c6218f3e0c8f93fb0669e7018c9107d172da40483d235cf0cc3f8fb7721836`.

| File | Made from | sha256 |
| ---- | --------- | ------ |
| `apoe.txt` | `example/apoe.fasta`, normalised as the API does: the header and line breaks removed | `eddd8b84fbb094df0b4067ca1d0b9b137ddaee4f8b3a548fcff5152e92a4dd4b` |
| `test.txt` | The release's `test.fasta`, `https://data.pantherdb.org/ftp/hmm_scoring/19.0/pantherScore2.2/test.fasta`, sha256 `097bbf0c629a0b7aaa00c73c5368d11b9a5ba689412f4051ab5b353e03db2499`, normalised | `1c880ed01f85104af5a52c07c52142980e39bb3e440ec6e75452e581bb96ec30` |
| `tie-pthr35774.txt` | The consensus of the sample's `books/PTHR35774/hmmer.hmm`, by 3.4's `hmmemit -c` | `d4b0f9ccb1c23d984d3ca2b15d03b7b03cc1f55c7ea5ac7df2c1ec099c41c949` |
| `pir-pthr34093.txt` | The consensus of `binHmm`'s `PTHR34093..pir`, which no model file holds, by 3.4's `hmmemit -c`. Its `X`s are the model's masked positions | `dc0ef51c99c3ac1ed4c71cb7c8f224b540ee7547b5fcc92c689e04f086d0d7f2` |
| `no-hit.txt` | 20 `W`s, which no model of the sample reports | `2b3721ae4cd54b1457c9a497a01ec1ecebf791308184faaffb57f9daa9a2c3b7` |
| `over-cutoff.txt` | APOE's residues 189 to 208, whose only row is over 1e-3 | `086cfce033761c5f115f7375fb354c666898a1dc595acf1d2a36875bd869c407` |
| `best-over-cutoff.txt` | Residues 148 to 159 of the consensus of the sample's `PTHR24068.SF460.pir`, by 3.4's `hmmemit -c` of `binHmm.txt` (below) | `d9c5b45b4774fcc9326bfb6ef760366190d19ca40eb8de5673dd23284262fdd6` |
| `apoe-lower.txt` | The same as `apoe.txt`: the engine gets it upper-cased. `cases.json` has the lower-case text the CGI is posted | `eddd8b84fbb094df0b4067ca1d0b9b137ddaee4f8b3a548fcff5152e92a4dd4b` |
| `apoe-stop.txt` | `apoe.txt` and a final `*` | `b64a04acd0982ec17f0f01ff62473bfa5661bb38fac5410c494264ce75f3d643` |
| `apoe-uncommon.txt` | `apoe.txt` with `B`, `J`, `O`, `U`, `X` and `Z` in place of residues 50, 100, 150, 200, 250 and 300 | `bc05a1b391135bb9d561ec820158d61998319d305e0e2d1be488a19e19931560` |
| `apoe-dot.txt` | `apoe.txt` with a `.` after residues 80, 160 and 240 | `f0badc8ce30618d1012d270197e282394e79900363b70ef852db700b8fdc734a` |
| `apoe-underscore.txt` | `apoe.txt` with a `_` after residues 80, 160 and 240 | `2596905a7905a695625c314d2f5bbf428a318169994de5d976b8d2f0c2a4cae4` |
| `apoe-tilde.txt` | `apoe.txt` with a `~` after residues 80, 160 and 240 | `e219d39c20e6d352491ddc46217e6694613dfd0c8c453847874bf4cb10acb752` |
| `apoe-star.txt` | `apoe.txt` with a `*` after residues 80, 160 and 240 | `86a194dff090e9f696d3025a81fc7dd7af3e1c91c3f6f8bbf966af282460f17e` |
| `titin-10000.txt` | The first 10,000 residues of titin, from `https://rest.uniprot.org/uniprotkb/Q8WZ42.fasta`, sha256 `2bb79b409b2540249a432bd638215e5a789e69116eaf1ea0d15e48304e5c80f2`, as the survey pinned it | `5c43b2a872a58e20797027d2812e9d3999eca547a9af8a3166684d83997c6e12` |

`tie-pthr35774`'s and `pir-pthr34093`'s consensus sequences were made in the engine image, on `linux/amd64`, with the sample in `/data`:

```sh
hmmemit -c /data/hmmscore/19/books/PTHR35774/hmmer.hmm
hmmconvert /data/hmmscore/19/globals/binHmm.h3m > binHmm.txt && hmmfetch --index binHmm.txt
hmmfetch binHmm.txt PTHR34093..pir | hmmemit -c -
```

`no-hit` and `over-cutoff` were picked with `hmmscan --domtblout` on the sample: `over-cutoff` from a search of APOE's windows of 8 to 76 residues, in the arm64 engine image. Their tables were then recorded in the amd64 one, at `--cpu 0`. `no-hit`'s has no row. `over-cutoff`'s has one, PTHR18976's SF2 model at 11.7 bits and E-value 0.0035, 3.5 times the cutoff:

```text
PTHR18976.SF2.pir    -            290 sequence             -             20    0.0035   11.7   0.0   1   1   7.6e-06    0.0035   11.7   0.0   175   190     1    16     1    20 0.88 -
```

`best-over-cutoff` (`HMMSCORE-5`) came from a search of the sample, in the arm64 engine image: windows of 12, 16, 20, 25, 30 and 40 residues, at every 7th residue, of the consensus of each of the sample's 456 models (`hmmemit -c binHmm.txt`), of APOE and of `test.fasta`, 110,991 queries in one `hmmscan`. One had its best model, by score, over 1e-3 beside a lower-scoring model under it: these 12 residues. 3.4 on amd64 and 3.1b2 on its own presses give the same first two rows, so `getBestHit` takes SF508 at 13.8 bits, whose 0.0012 fails the cutoff, and SF502's 0.0009 doesn't count:

```text
PTHR24068.SF502.pir  -            188 sequence             -             12    0.0009   13.7   0.7   1   1   4.4e-05    0.0009   13.7   0.7   177   187     1    11     1    12 0.91 -
PTHR24068.SF508.pir  -            148 sequence             -             12    0.0012   13.8   0.4   1   1   5.8e-05    0.0012   13.8   0.4   137   147     1    11     1    12 0.91 -
```

On the full library, every E-value is about 316 times the sample's, so there it's no hit with no model under the cutoff.

### `sample/`: The Reference on the Data Sample

`panther-engine hmmscore parity reference` on the data sample, `hmmscore-sample-1`, run on 2026-11-16 under Docker's emulated `linux/amd64` on an Apple Silicon Mac. 3.1b2 read its own presses of the sample's models. For each case:

| File | What it is |
| ---- | ---------- |
| `cgi.xml` | The CGI's standard output, posted `sequence=<text>`, without its first two lines, `Content-type:text/html` and a blank one |
| `best.tsv` | `pantherScore.pl -D B -n`'s output for the same query: every tied best ID, a line each, in Perl's hash order. Empty for no hit |
| `hmmsearch/<ID>.out` | `hmmsearch` of the model file at each ID in `best.tsv` against the query, as the CGI ran it. `:` is a `.` in the file's name, as Windows can't hold `:` |

- **`tie-pthr35774`'s `best.tsv` lists both IDs,** and its `cgi.xml` shows `PTHR35774`, the CGI's first line in that run's hash order. The port reports `PTHR35774:SF1` (divergence 13).
- **`no-hit`, `over-cutoff`, `best-over-cutoff` and `titin-10000` have no hit,** so their `cgi.xml` is `<scores>` and `</scores>` alone, and they have no report. None of titin's families is in the sample.
- **The reports aren't reproducible byte for byte:** each ends with the run's CPU time. Only the lines between "Domain annotation for each sequence" and "Internal pipeline statistics summary:" are compared.
- **arm64:** HMMER 3.4 gave every case's result on arm64 too, so there's no `sample-arm64/`. A case whose arm64 result differs would get the port's result there as `sample-arm64/<case>.json`, listed here with what differs.

Each file's sha256, from `parity/`, for `sha256sum --check`:

```text
ed6a9ed9ba7007f06be69cc8ee5adeac5ae57311c9644558d354b86635178b74  sample/apoe-dot/best.tsv
be9ea6e841df5989e1747da01c3e970f37f0a8ac719ec87d581bbd0368162083  sample/apoe-dot/cgi.xml
bf2a841eeab97627b39e20b85549fb7e3065c0b8a5c4ad17fbdb06863dc8eee9  sample/apoe-dot/hmmsearch/PTHR18976.SF2.out
7c7bf39100c6af1c104f5653f804d69c1526c6cd16645692b46e494331113bc8  sample/apoe-lower/best.tsv
cf3cd3ccb390d735e96e463102ebaa8495d88355e9f35462131a3ec7f58ec4b9  sample/apoe-lower/cgi.xml
29cd572a7bad658a76b4a1963cf1a24046f9441deb497ec5b3122227e05ca64d  sample/apoe-lower/hmmsearch/PTHR18976.SF2.out
ed6a9ed9ba7007f06be69cc8ee5adeac5ae57311c9644558d354b86635178b74  sample/apoe-star/best.tsv
f02c36a01e6cdcd8f781a2fa82f7f20b79cee8168563a9dab8c5947019285204  sample/apoe-star/cgi.xml
5ead533b649cb38e770f78d964de8ce57d516237f70a66c798f2fea5a194a548  sample/apoe-star/hmmsearch/PTHR18976.SF2.out
d73de263d11e8f7c80d6997ff7b5ddbdcecc161ad5870ecb84225739c4c88555  sample/apoe-stop/best.tsv
a37f323f90193ade4e0d4114fd0ae2d3d3bb073beeb210aa930512f909849f8c  sample/apoe-stop/cgi.xml
b3f8d07a2607a0cd3d4053a96afe0df1a00356ba20e553a7f10c8f9046f076b4  sample/apoe-stop/hmmsearch/PTHR18976.SF2.out
ed6a9ed9ba7007f06be69cc8ee5adeac5ae57311c9644558d354b86635178b74  sample/apoe-tilde/best.tsv
7223eded7bfe0a3d9383145c2939571b5727d3d6c07b25d3e4e2f65317837f93  sample/apoe-tilde/cgi.xml
d7939c08bfa5aeef7371b8b0e703ddf3c7723038aa16f5f80e460f64ed55d914  sample/apoe-tilde/hmmsearch/PTHR18976.SF2.out
c7c654ae2b68cb9201a1df7310b3186e14260fc56e2bb21b264e6e0f19e7e0f0  sample/apoe-uncommon/best.tsv
103fa3b5222af0f61bda4bd5809ab3705200b735066450256251512c1a465526  sample/apoe-uncommon/cgi.xml
c300b9c5885404b67ae7c71f2c023b48abb5ebfb8bb14aa950d96ae9ff24aa38  sample/apoe-uncommon/hmmsearch/PTHR18976.SF2.out
ed6a9ed9ba7007f06be69cc8ee5adeac5ae57311c9644558d354b86635178b74  sample/apoe-underscore/best.tsv
be9ea6e841df5989e1747da01c3e970f37f0a8ac719ec87d581bbd0368162083  sample/apoe-underscore/cgi.xml
a3598f1a8b760fb9b7a7be9f1f15da735ba4d9cc14763c09cc40b6a0b2d52fd1  sample/apoe-underscore/hmmsearch/PTHR18976.SF2.out
7c7bf39100c6af1c104f5653f804d69c1526c6cd16645692b46e494331113bc8  sample/apoe/best.tsv
cf3cd3ccb390d735e96e463102ebaa8495d88355e9f35462131a3ec7f58ec4b9  sample/apoe/cgi.xml
ba412e4605fc8c0736270a9e277c706d59f66261e6f7fc8450f3870a0c4c5313  sample/apoe/hmmsearch/PTHR18976.SF2.out
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  sample/best-over-cutoff/best.tsv
515ffdaa3c1ae8903eba8758b3e41cfbfd58f21436d8c088813db281f70b4c87  sample/best-over-cutoff/cgi.xml
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  sample/no-hit/best.tsv
515ffdaa3c1ae8903eba8758b3e41cfbfd58f21436d8c088813db281f70b4c87  sample/no-hit/cgi.xml
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  sample/over-cutoff/best.tsv
515ffdaa3c1ae8903eba8758b3e41cfbfd58f21436d8c088813db281f70b4c87  sample/over-cutoff/cgi.xml
a6d71b67939134f8e7176f59ed108e792522b1b6f39b504e980ec109d33e7956  sample/pir-pthr34093/best.tsv
ed50321604b88ebb4c2a8dadeacc9ce8d73d256bcdcfff1fb9084421c81d5f55  sample/pir-pthr34093/cgi.xml
1d0f5267a665ac6140e7e451ef1f79ca53aa9ac0b7b7c8381c7413f7c1203e35  sample/pir-pthr34093/hmmsearch/PTHR34093.out
a8881e4f8f407b498e11bfb90d25ab273de05c8387f60b8a3d13e94836d30d3e  sample/test/best.tsv
a99f7056229493109d8e602c22f8564920d2e9c25eee3471fb90891240df5718  sample/test/cgi.xml
aba9f1514d783a76756c86eb82452f79c6e1c79926c777551c1a993b8cecdf1c  sample/test/hmmsearch/PTHR10489.SF627.out
2a6e5c3e246d01a438bdb33e9d9273130946051b87fd045d24f7a60a9e02bc7f  sample/tie-pthr35774/best.tsv
1a65ddb7cfca65724123fa263ed720a642e43ae9b5ac2f97a21afe7e074c1e2d  sample/tie-pthr35774/cgi.xml
ac6267d4905a56bf075fed2b1198642c13cc406f05f4bdbfc7bf7e197469b8dc  sample/tie-pthr35774/hmmsearch/PTHR35774.SF1.out
230a62a3acb5e295b0b0cbc7fdf13fcb63481eeec45b30d5571028b57043b6f7  sample/tie-pthr35774/hmmsearch/PTHR35774.out
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  sample/titin-10000/best.tsv
515ffdaa3c1ae8903eba8758b3e41cfbfd58f21436d8c088813db281f70b4c87  sample/titin-10000/cgi.xml
```

### `full/`: The Reference on the Full Library

The staging run: `panther-engine hmmscore parity reference --goldens full` on PANTHER 19's full library, after `data verify`, on 2026-11-17. It ran on `b11-19`, an AMD EPYC 7513 node of CARC's Endeavour cluster, in the `hmmscore-reference` image through Apptainer, with the engine at `3b92fe6` ([inputs.md](../../../../docs/parity/inputs.md#the-hmmscore-staging-run)). 3.1b2 read the library's shipped pressed files, as production's did. The files are as in `sample/`.

- **Each case has the sample's hit, at the same score.** The E-values are about 316 times the sample's, since the library has 144,361 models to the sample's 456.
- **`tie-pthr35774` ties here too,** at 89.5 bits and 7.3e-25, and its `cgi.xml` again shows `PTHR35774`.
- **`titin-10000` has a hit here:** `PTHR11100:SF29`, titin, at 19443.0 bits and an E-value of 0. Its `hmmsearch` report aligns six domains to the model's 35,040 positions.
- **`no-hit`, `over-cutoff` and `best-over-cutoff` have no hit,** as on the sample.

Each file's sha256, from `parity/`, for `sha256sum --check`:

```text
b90bbf5f0ff651c330eb63033738054cd983b41cc3f9cea8db09a2ccf514c378  full/apoe-dot/best.tsv
f3d642e456f81bd4ed517f2a66d565527a9e17d61b0d1f1f7b38aea1a53800f7  full/apoe-dot/cgi.xml
c82061a70c29f978e123fd719b3adb0d96aa61f2df8d5cee5d3187e25f70d4f8  full/apoe-dot/hmmsearch/PTHR18976.SF2.out
8a4e0a9c1bb4770757593bb5a20494b4c98b525daa7f7d788dadd8b07caef351  full/apoe-lower/best.tsv
c9304487d38d25b6f4232b9d96ad793db09d5ee650a9b6e386abaaa036b4779e  full/apoe-lower/cgi.xml
43267bc360aea7dce8e237af5f45c0f24cf57759a115c207d1af5abc524048ae  full/apoe-lower/hmmsearch/PTHR18976.SF2.out
b90bbf5f0ff651c330eb63033738054cd983b41cc3f9cea8db09a2ccf514c378  full/apoe-star/best.tsv
0d5afa29e47113ec11122f61a298bd2a9a88ef8393bfc0003a1704501404d353  full/apoe-star/cgi.xml
6680fd43a875e181d3a60977f7a020f18f5e2e3c0b5bbfbaa68f7701f0eb04ba  full/apoe-star/hmmsearch/PTHR18976.SF2.out
8f3db22821214674931a151f09d3cf24e3db3d04afaf859dfc8a1bae3ca61719  full/apoe-stop/best.tsv
81dc5d7d3c62c524e9d2381127b3ab22a46d55ad1f0dbbd8a5f4f0bd1da9a89f  full/apoe-stop/cgi.xml
0f0294d5089650238e97194ab3d6d73920093979dc2cb1e9431d4f727750b4fd  full/apoe-stop/hmmsearch/PTHR18976.SF2.out
b90bbf5f0ff651c330eb63033738054cd983b41cc3f9cea8db09a2ccf514c378  full/apoe-tilde/best.tsv
261e88f54c9a165888e639a32adb105b294e6feebf7230a851eec0677b889317  full/apoe-tilde/cgi.xml
5db5adb9405b4d07b97d0a42bd50770d9586c999218427fabee85d2f16e77862  full/apoe-tilde/hmmsearch/PTHR18976.SF2.out
640da13e5595302f33b46956852836c8955b0e1421381c61af4fd39483c08ad0  full/apoe-uncommon/best.tsv
544f60e3362b6e4815cd8b5800a75aa7e4b95e8932371981a7a23dbc4e5cd6df  full/apoe-uncommon/cgi.xml
a39faa7fc45beb315f2b644065dfddd502fab02afcc4258f1f6106832ee509d8  full/apoe-uncommon/hmmsearch/PTHR18976.SF2.out
b90bbf5f0ff651c330eb63033738054cd983b41cc3f9cea8db09a2ccf514c378  full/apoe-underscore/best.tsv
f3d642e456f81bd4ed517f2a66d565527a9e17d61b0d1f1f7b38aea1a53800f7  full/apoe-underscore/cgi.xml
e88a1d2cbef61a2e2b7b0eeb673c177bb1f42dc827a8b49a1a519d31c121112f  full/apoe-underscore/hmmsearch/PTHR18976.SF2.out
8a4e0a9c1bb4770757593bb5a20494b4c98b525daa7f7d788dadd8b07caef351  full/apoe/best.tsv
c9304487d38d25b6f4232b9d96ad793db09d5ee650a9b6e386abaaa036b4779e  full/apoe/cgi.xml
254325ac1ef564a3b49f81baaf6edb9b34d2800d12d1e60aed4bab011f9c0d1b  full/apoe/hmmsearch/PTHR18976.SF2.out
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  full/best-over-cutoff/best.tsv
515ffdaa3c1ae8903eba8758b3e41cfbfd58f21436d8c088813db281f70b4c87  full/best-over-cutoff/cgi.xml
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  full/no-hit/best.tsv
515ffdaa3c1ae8903eba8758b3e41cfbfd58f21436d8c088813db281f70b4c87  full/no-hit/cgi.xml
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  full/over-cutoff/best.tsv
515ffdaa3c1ae8903eba8758b3e41cfbfd58f21436d8c088813db281f70b4c87  full/over-cutoff/cgi.xml
6f7da9790efd8db148dd3fdad326468852c8f14a8642dd112cb27d99d4b1675f  full/pir-pthr34093/best.tsv
5eba64f02c964d79a8f2f835d3bde4b2fcaf72520d1118dc967f15c562a4220e  full/pir-pthr34093/cgi.xml
79c109548975cff4d46dc093394081b73bc4c3f4f4bd299ae70bedf3bf94c401  full/pir-pthr34093/hmmsearch/PTHR34093.out
cee6a8ae7dc51e50cbcf6b508a153c91b8f93ffeae28b53456fbcbee8e0687a0  full/test/best.tsv
77bb7b078f5b9a24a2de649cbcefc6b7e125e7d522fdb58dc2f378b7b3c35241  full/test/cgi.xml
13b0c7c77ca7eb287f3cfa76f96c5f8f01a70ce94e460ec9e02222efe6b540a8  full/test/hmmsearch/PTHR10489.SF627.out
b094e1eb9812089ab5f119d54255e5d4714b03013e7f3da3f7e7756516d60356  full/tie-pthr35774/best.tsv
a5a99b7446269d90f5822967f30c4e970babc31707f80b9b7aa23769a9beda38  full/tie-pthr35774/cgi.xml
17fffd9352046914647d7cb1ae8e1870090ae9b84134e262ff5725defdbc9ea3  full/tie-pthr35774/hmmsearch/PTHR35774.SF1.out
0eaec26c97d9c5c374793ca6524f8e957261e1a3c83526a3b512bc3ed7c78462  full/tie-pthr35774/hmmsearch/PTHR35774.out
dbf34b323681686dee5f90b4ce5d4e2dca7b42e7e426ab2189dd59ff8eda0bfa  full/titin-10000/best.tsv
28d9f3d7b318a400cbf913c5caf298d8057fd99252322719ba0a51551d692838  full/titin-10000/cgi.xml
91b1669d42f44f63b0b371f827c39b21037e5b25219ebf89d41b18c61a2448fa  full/titin-10000/hmmsearch/PTHR11100.SF29.out
```

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
