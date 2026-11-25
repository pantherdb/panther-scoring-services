# treegrafter's Full-Library Set

Thirty proteins grafted on PANTHER 19's full TreeGrafter library, with release 2026-08-28, by EBI's command line and by the engine: the second set of `adopt-treegrafter`'s full-library run (task 7.6). The goldens' own cases (`../cases.json`) ran on the full library too, into `../parity/full-arm64/`. Why the set is what it is, and the run, are in [inputs.md](../../../../../docs/parity/inputs.md#the-treegrafter-full-library-run); what the library holds is in [the survey](../../../../../docs/parity/treegrafter-library-survey.md).

It's for checks by hand, on a machine with the full library: CI doesn't run it. From the repository root:

```sh
docker compose run --rm -T engine panther-engine treegrafter parity check \
  --golden tests/golden/treegrafter/library --goldens full
```

## The Inputs

`cases.json` lists each protein and why it's there, and `inputs/<case>.txt` is its sequence, as the API sends it: no header, no whitespace, upper case, and no final line feed. `cases.json`'s sha256 is `c8760912df0dca4faee9e8651fbc2e449ccde8fad21d6c6ed5a27e71da65baa0`.

| File | Made from | sha256 |
| ---- | --------- | ------ |
| `cftr.txt` | UniProt P13569, `https://rest.uniprot.org/uniprotkb/P13569.fasta` (sha256 `0574a2437b33ae9ac901e8c0bf86c568685bf677361987127fccd9574f515826` on 2026-11-24), normalised | `a86f7dbeb9c5f48401a1a452b440d782c35067d2da152180a09ce26f76d11639` |
| `dync1h1.txt` | UniProt Q14204, `https://rest.uniprot.org/uniprotkb/Q14204.fasta` (sha256 `39c4c48c73e21f0207c64336bbb1cf9c8844a105d897038b4162e418a0c89c80` on 2026-11-24), normalised | `779fba7bce6f20a5aa9862d8c265611124ba073815cebea645c7d2110c48c964` |
| `titin-10000.txt` | UniProt Q8WZ42, `https://rest.uniprot.org/uniprotkb/Q8WZ42.fasta` (sha256 `2bb79b409b2540249a432bd638215e5a789e69116eaf1ea0d15e48304e5c80f2` on 2026-11-24), normalised, its first 10,000 residues: the same as hmmscore's `titin-10000.txt` | `5c43b2a872a58e20797027d2812e9d3999eca547a9af8a3166684d83997c6e12` |
| `or1a1.txt` | UniProt Q9P1Q5, `https://rest.uniprot.org/uniprotkb/Q9P1Q5.fasta` (sha256 `307c44ddd864669825448e47927c35d7bc2ddb7ef8121ee8fbb4fefdf0558b95` on 2026-11-24), normalised | `9a79439422ed78475973cb19efbcbc91c658bca304554fc0d817b7860d8d41eb` |
| `mapk1.txt` | UniProt P28482, `https://rest.uniprot.org/uniprotkb/P28482.fasta` (sha256 `cccd58c08068f43c3bdd1027d24cf25d57c64c1135325575e85001f05e9a2691` on 2026-11-24), normalised | `1670aefbe2d9baf3412d23252180a37554c5647a0ad5cb1fbd06bb18417aee49` |
| `h3-1.txt` | UniProt P68431, `https://rest.uniprot.org/uniprotkb/P68431.fasta` (sha256 `6ec96cb85297e358031acd26b7e722a66e629d7fdcacc8478a5f0ec17ea96397` on 2026-11-24), normalised | `1fb6acc65c96cc143b2f8a65b5a89da2d19b99d5e8bfbd8d5d81d4ad38ce4e72` |
| `actb.txt` | UniProt P60709, `https://rest.uniprot.org/uniprotkb/P60709.fasta` (sha256 `50469aa3087cbb3679ce4167ab78ce1352cc07bd7fa6533e77ed9601dedcaa08` on 2026-11-24), normalised | `d498c40159d7c993d9e7e36afbe2f4921d5e81e6ab08d5388cbab47cc0234a92` |
| `calm1.txt` | UniProt P0DP23, `https://rest.uniprot.org/uniprotkb/P0DP23.fasta` (sha256 `b718184bb435725b2836c29604d1b3553b8788f15f4bd07d7cc507531c0302e4` on 2026-11-24), normalised | `4a9f2f38a0afe61f9cd35d05788764536c1b394551a521687d0e537ad2760ff5` |
| `tp53.txt` | UniProt P04637, `https://rest.uniprot.org/uniprotkb/P04637.fasta` (sha256 `59aace7211b64e5918ef6547fc48d6419a134fa91f158415d598d3416882f063` on 2026-11-24), normalised | `e3ca60f18e3b6e98986ad6749215ee3b7a3abc09c191675213d1f243c035c9a3` |
| `brca1.txt` | UniProt P38398, `https://rest.uniprot.org/uniprotkb/P38398.fasta` (sha256 `76e29e4e2e1310c227ed32ce2eb030a273eea456592015f9d4080f1d86750b82` on 2026-11-24), normalised | `80d7199c8d1550a5ba8387043481c1acf0f070df410b47c2bc1375584b59bdf1` |
| `egfr.txt` | UniProt P00533, `https://rest.uniprot.org/uniprotkb/P00533.fasta` (sha256 `684e2da1f3ef05d0ce90d0aefe9125c6f7e9cdcfeac27ae72ed35243b64a73e8` on 2026-11-24), normalised | `dbb4583267ad40a7dfd854ee3c44ce4be38e137d0570e3eb76cf1854a74e7246` |
| `ins.txt` | UniProt P01308, `https://rest.uniprot.org/uniprotkb/P01308.fasta` (sha256 `ec55929cdb69371f89213f4b08a19808c115fc8225ed92b09dd93d15571b5584` on 2026-11-24), normalised | `99603f8fb1e9872e2d24ee1e9f85108c2bddea6b148a0f1099e16ba2715c8263` |
| `gapdh.txt` | UniProt P04406, `https://rest.uniprot.org/uniprotkb/P04406.fasta` (sha256 `da9a1e46f172a3e08735dc21e6ce9be5772e745a896fad5e2f155d34faad79e0` on 2026-11-24), normalised | `4b2c2bd32a59c45cd89bf42b340c41f03a8517f2fd427d837cfa76b63742ffee` |
| `rho.txt` | UniProt P08100, `https://rest.uniprot.org/uniprotkb/P08100.fasta` (sha256 `ef2cd3ad4e04b50f432050fcb71f7fdb51d2b004821b15ca712f25b3ec25925f` on 2026-11-24), normalised | `b59611b13c3509dcbb28613b8c35f400f97e67788dcf416dce0511a576c347c1` |
| `ubb.txt` | UniProt P0CG47, `https://rest.uniprot.org/uniprotkb/P0CG47.fasta` (sha256 `c1991fb05ea412c54246f18cd0b08c6cfb92c744c3e83c6d70a899b7430009d0` on 2026-11-24), normalised | `b99a5e678bdfbf9b6c2a1b574ba987085d3ab3f118ef307320ae5e15c6634065` |
| `kras.txt` | UniProt P01116, `https://rest.uniprot.org/uniprotkb/P01116.fasta` (sha256 `be58c42a464baafed08805898078839b0b47b559cec93fdb3cd7f8d95ab95ea6` on 2026-11-24), normalised | `1d5a9ab11f64cb886d8ffa08a153c412b2d190fcf70e5690cd4b4c7efcdee53a` |
| `lyz.txt` | UniProt P61626, `https://rest.uniprot.org/uniprotkb/P61626.fasta` (sha256 `adc9e9ace03759071d823dcb5986f0897d0d174a83f211e8d9b3ed2a36812007` on 2026-11-24), normalised | `7d0e4fd9fdc4406e6179855d1e2bf7e9aa182416262a70dafca656fcada3f2f7` |
| `groel.txt` | UniProt P0A6F5, `https://rest.uniprot.org/uniprotkb/P0A6F5.fasta` (sha256 `9128f2dfe8fa0b868466295100b686f03cd9542185de44708b0f4367ce1ff7bf` on 2026-11-24), normalised | `40544c6fee0f15b6fe78d6ab7e5e27d8080224fe28dc0d6ca6f2e9a790dd24d4` |
| `reca.txt` | UniProt P0A7G6, `https://rest.uniprot.org/uniprotkb/P0A7G6.fasta` (sha256 `d50de46435332af12eb002e6184691e8fe1365d0e58ec0541388ca84938cbe0c` on 2026-11-24), normalised | `7b173d7a1bebe89504c2f4afcc71cba2b37385acbc6b869f7c6071bf2de262d4` |
| `sars2-spike.txt` | UniProt P0DTC2, `https://rest.uniprot.org/uniprotkb/P0DTC2.fasta` (sha256 `399308ca13674141add24eb388b1b4fc3a84330350075c18be0b4261166f8086` on 2026-11-24), normalised | `794d56c4e53ad15197d12fcee6c8231e888d2fc60728f4ef875561b80af2639d` |
| `cdc28.txt` | UniProt P00546, `https://rest.uniprot.org/uniprotkb/P00546.fasta` (sha256 `7c29fcb3c1c6dd1fd88d8a6e9290ba61ce7eab1685da73190ff773e63798c6f0` on 2026-11-24), normalised | `97f8f345398bf5cec8d8e3a6d255f43a1e5b896747e2417fad92a8c46bd95079` |
| `rbcl.txt` | UniProt P00875, `https://rest.uniprot.org/uniprotkb/P00875.fasta` (sha256 `612b450ea331fd38f6c51bbd16308775a58472ee1f944c1ebe25fe9bf8422388` on 2026-11-24), normalised | `0b9be6228e3b08c115b028cbe19132d932d25d3b53b81b5423f019a96272df0b` |
| `notch.txt` | UniProt P07207, `https://rest.uniprot.org/uniprotkb/P07207.fasta` (sha256 `4cbbebe4a409a36e4bef456c76b2b5dd987ebd3e18298729687d3ab6c06ad112` on 2026-11-24), normalised | `c02e6a1696ffa0114fd7da0b6c5af0a26b90e6520c919054a9f1d7a1bf48f566` |
| `bacteriorhodopsin.txt` | UniProt P02945, `https://rest.uniprot.org/uniprotkb/P02945.fasta` (sha256 `3c9b9576fcbc7c199c2aae5905a5d9d99df5621408b947bed4c14cbea10c800e` on 2026-11-24), normalised | `78c26b0b585d83693169b264daabcc735decfefc8ad7c922e03be7fbf0a74c1a` |
| `flc.txt` | UniProt Q9S7Q7, `https://rest.uniprot.org/uniprotkb/Q9S7Q7.fasta` (sha256 `4366d540c8ea060fe71bd3b1cd5baff95070ce122520006305f060c94f9bcf55` on 2026-11-24), normalised | `76221041358da89c18a60e9b8197b528e23423b701b512a79c9a4fc4170d3f13` |
| `laci.txt` | UniProt P03023, `https://rest.uniprot.org/uniprotkb/P03023.fasta` (sha256 `30f9fa453ec0e0e66b37b74b999ae491fc8d5a8f3b2e6d3b5001606e48f5032d` on 2026-11-24), normalised | `ac83dff630587d7c8852f0cac03bffbc646ad7447791bf7c6b00506c18567cd6` |
| `slc15a5.txt` | UniProt A6NIM6, `https://rest.uniprot.org/uniprotkb/A6NIM6.fasta` (sha256 `0e165a7d9760d91b0742e7dfda0c310ead2aca38ac300dd781d9ab881cceb523` on 2026-11-24), normalised | `46220c711236fc704e6a312b3f04f07f7ae5902a9cd79eab2400378e6a85f403` |
| `ap3b1.txt` | UniProt O00203, `https://rest.uniprot.org/uniprotkb/O00203.fasta` (sha256 `45fb2e7c6ab589acbdebf5cd842ff562c07993f8e1bb4416da020bc55a74ac4b` on 2026-11-24), normalised | `ab556826f13ad9b3a8626fb8d0b271972b7b819c13f9af33220d016bb22cf8d7` |
| `cox6b1.txt` | UniProt P14854, `https://rest.uniprot.org/uniprotkb/P14854.fasta` (sha256 `8fa73d3eae2fe7f4df30a78c7ca8ab698267dedb0f5add2c8ee0c15d69eeaa6e` on 2026-11-24), normalised | `5fc250cef72681e7da7bf7b7726f2cc2c6ba56be463807649b0e4877aacc8d74` |
| `mocs2.txt` | UniProt O96007, `https://rest.uniprot.org/uniprotkb/O96007.fasta` (sha256 `439afac6e073bb919a06fb3d159cc99ec03cae92f29d7109a58f06a07f297522` on 2026-11-24), normalised | `fd432372639308e73694d81ca5e5c350b61d6c0492e4c3353744ac0f64c3b777` |

## `parity/full-arm64/`

EBI's `--print-go` output for each protein, by `panther-engine treegrafter parity reference --goldens full`, on 2026-11-24, in the engine image on `linux/arm64`, an M1 Pro's Docker Desktop. The engine matched all 30. There's no amd64 run yet: on amd64, `parity reference` writes `parity/full/`.

| Case | Hit | `result.tsv`'s sha256 |
| ---- | --- | --------------------- |
| `cftr` | `PTHR24223:SF19` at `AN168` | `bff370fdea098db4efc13c6117fb1af6eeb7091486ebd7793ff874b7de62ddb2` |
| `dync1h1` | `PTHR46532:SF13` at `AN38` | `aa105ece5cc6a52f25f18341cef4b34bce614c64ef5ab87304737a030f4876ae` |
| `titin-10000` | `PTHR47633:SF4` at `AN92` | `bb4855c284bb7bc76f96d27d728204a68ecc8a6087472c7859025732549002b3` |
| `or1a1` | `PTHR48001:SF50` at `AN1842` | `1a2fde31180b70e50b5a47ecb1a6a737f0bb84d246072dd9b41f45271d929df7` |
| `mapk1` | `PTHR24055:SF584` at `AN2190` | `4cd4f7c72c81b9ce18e85526f5a4d89c22adb1c425aa6db7b08330aa9c0bb00e` |
| `h3-1` | `PTHR11426:SF242` at `AN1140` | `1323c6133e7ae9c0038e101008cb75bf9c306319963ab119e968afeb9e730e68` |
| `actb` | `PTHR11937:SF575` at `AN1128` | `2a63d9a8337a8ddc6c6cdbc2fd29b924d9762dbdcdd33e9f162ce1f7c3dbc24b` |
| `calm1` | `PTHR23048:SF0` at `AN316` | `36f69f6b451e894d6726c0d82710ce8371f03d10ad3019b2d7c036e62a8f98c5` |
| `tp53` | `PTHR11447:SF6` at `AN14` | `6efd78ad2131a29788c576d467e4fa54e44e6890e56f778f6c5c07d8b59442a9` |
| `brca1` | `PTHR13763:SF0` at `AN23` | `f62b53f9311af126a17861a0f2b83a5a0ef9fcf90cea1d8d3e5fce3b54c9fefd` |
| `egfr` | `PTHR24416:SF91` at `AN462` | `1ab1e729ac79b948a777c14e388f3016ff80db228bede97f4e96ea15a7a838f0` |
| `ins` | `PTHR11454:SF9` at `AN15` | `b961483bc0c77e083ff3d700ee542c51a4524f9baaf5fbfd339cc7f1a2709861` |
| `gapdh` | `PTHR10836:SF111` at `AN71` | `0827e6e3791ed072d62e601719bac43cd045c26325662296ea7beb56d361bb9b` |
| `rho` | `PTHR24240:SF15` at `AN702` | `953d8b2d1618137a4a265309a6b43cd730e62f173b7da8478a51dffef41f2d74` |
| `ubb` | `PTHR10666:SF437` at `AN682` | `50ea8af06eb17de84d3bcd16d2bf4b7fc293c3a5a82e17be658aaf56d8d65e48` |
| `kras` | `PTHR24070:SF388` at `AN1448` | `eab834777cfea3e413ff8d35e163d2c078f9beec9a158e50348cb887880969d0` |
| `lyz` | `PTHR11407:SF28` at `AN222` | `1024385d2ff8871db0e8beb3367c24b5aef5b2f92573b5e0e613e518bbbc8b41` |
| `groel` | `PTHR45633:SF3` at `AN1022` | `001b92ae2402905d237e22bebaac4d8b19e20e4822bfa86d233c1886d53b08ee` |
| `reca` | `PTHR45900:SF1` at `AN355` | `d5727fef084b5414fc6844035ea4ba8adf487ce2e18f2f577c1c977681ed5bf7` |
| `sars2-spike` | no hit | `e51dec7a593a60b31c0fea9c2f82bf97e3739e1e4c67b6f909839c251a62986e` |
| `cdc28` | `PTHR24056:SF254` at `AN947` | `2557729bcbf33bf5a20085d12f79d9974984d8c93f61edcf1d7ec04314700acc` |
| `rbcl` | `PTHR42704:SF16` at `AN101` | `a5e0492580c7d592f721fe60b341b9c90f16f9a952968b53fc4b7e4a35c8f568` |
| `notch` | `PTHR24049:SF22` at `AN254` | `0c5e1bea06bac5e9ac6d69b750728f17106f308b4801644e993a88e545df7baa` |
| `bacteriorhodopsin` | `PTHR28286:SF2` at `AN54` | `045397acfe5d1c93327b2605da5aa3bdd7bd5303640c1e521d389755407516ab` |
| `flc` | `PTHR48019:SF238` at `AN1028` | `799027fe58870943c8b57f0ead505edcebfe5083442934670c15da0927a8f40a` |
| `laci` | `PTHR30146:SF153` at `AN198` | `35a62b2050f789ef0c72e63d0832c82c292690210aa7fbcdb711f9b23580e120` |
| `slc15a5` | `PTHR11654:SF91` at `AN98` | `bba360c137b1854e7ba41e9d6cbc94846a1b65129dadc9000ff955551a95bbb5` |
| `ap3b1` | `PTHR11134`, the family alone | `a7221f81971e4423905a63361dc39d9f095edeb58418e2377b37552391b63b50` |
| `cox6b1` | `PTHR11387`, the family alone | `33e10d83d9d75485c2c823bcca58289cacc5ed566cf42bc56243b018257c6c6d` |
| `mocs2` | `PTHR23404`, the family alone | `b2f239feebb95b1f4a950e37f677928ffaef386ae3673b788fef3142384e1063` |
