# 02: cSNP Form

Checks the coding SNP scoring form: filling it, the checks it makes before sending, and the results page, first with mock data, then with real scores from the API. The first three test cases use mock data; the last three use the real API and the cSNP data sample, and TC 2.6 what happens when the form can't load its species list. About 20 minutes.

## Before You Start

You need Node `^22.22.2` or `>=24.15.0`, and for TC 2.4 to TC 2.6, Docker (with compose), `curl`, and the cSNP data sample in `.data/` at the repository root (157 MB, fetched once; see "The Data Sample" in `docs/testing/api.md`). Ports 8000 and 5173 must be free.

For TC 2.1 to TC 2.3, start the website with mock data:

```sh
cd frontend
npm ci
npm run dev
```

Then open `http://localhost:5173` in a browser.

**The results in TC 2.3 are mock data,** made up to show the results page: family `PTHR00000` is not a real PANTHER family, and the ages, predictions and pDel values were not computed. Don't compare them with the legacy site. Every page says so in a dark **Mock data** banner at the top.

## TC 2.1 Open the Form and Choose a Species

- [ ] The home page's **Coding SNP impact scoring** section has a **Score coding SNPs** button.
- [ ] Click it. The address changes to `/csnp`, and the page is headed **Coding SNP impact scoring**.
- [ ] The **Protein sequence** and **Substitutions** boxes are empty, and **Species** reads `Homo sapiens (HUMAN)`.
- [ ] Click **Use an example**. The sequence box fills with ten lines of residues starting `MKVLWAALLV`, the substitutions box with `L46P`, `C130R`, `R163C` and `R176C`, one per line, and the species is `Homo sapiens (HUMAN)`.

Next, the species list. With mock data it has only 8 species; against the real API (TC 2.4), it has 85.

- [ ] Click **Species**. A list opens under it, each species written as its name and its code in brackets, such as `Mus musculus (MOUSE)`, in alphabetical order of name.
- [ ] Select the text in the box, and type `muscul`. The list narrows to `Mus musculus (MOUSE)`. Click it: the box reads `Mus musculus (MOUSE)`.
- [ ] Select the text again and type `plaf7` in lower case. The list narrows to `Plasmodium falciparum (PLAF7)`: a code finds its species too.
- [ ] Type `xyz` instead. The list says no species matches. Click outside the box: it goes back to the species chosen before.
- [ ] With the keyboard only: press Tab from the substitutions box to reach **Species**, type `rattus`, press the down arrow, then Enter. The box reads `Rattus norvegicus (RAT)`.
- [ ] Click **Use an example**. The species is `Homo sapiens (HUMAN)` again.
- [ ] On a phone, or at phone width, scroll down to **Species** and tap it. The list opens next to the box, and the page doesn't jump back to the top.

**Pass / Fail:**
**Notes:**

## TC 2.2 Mistakes Show Before Sending

- [ ] Reload `/csnp`, and click **Score substitutions**. The sequence and substitutions boxes turn red, each with a message under it; **Species** doesn't, since it still has a species. The address stays `/csnp`.
- [ ] Type one letter in the sequence box. Its message goes; the other stays.
- [ ] Click **Use an example**. Every message goes.
- [ ] Add a second FASTA sequence: put `>one` on a new first line and `>two` above the last line. Click **Score substitutions**. The sequence box says it holds more than one sequence.
- [ ] Click **Use an example** again, add a substitution of 33 characters (for example `L` followed by 32 `1`s), and submit. The substitutions box says substitution 5 is longer than 32 characters.
- [ ] Click **Use an example** again, add `XYZ` and `G12|` on two new lines, and submit. The substitutions box names substitution 5 (`XYZ`) and substitution 6 (`G12|`), and asks for the form `L46P`.
- [ ] Change `XYZ` to `l46p` (lower case) and remove the `G12|` line. Submit: the form is accepted, because lower case is fine, and a job page opens.
- [ ] Go back to `/csnp`, click **Use an example**, and replace the substitutions with `L46P, C130R,R163C` on one line. Submit: the form is accepted, with no message on the substitutions box, and a job page opens, because commas separate substitutions too. (The mock results always show the example's four rows, whatever was sent.)
- [ ] Go back to `/csnp`, click **Use an example**, and replace the substitutions with `L46P;C130R`. Submit: the substitutions box names substitution 1 (`L46P;C130R`), because a semicolon doesn't separate substitutions.
- [ ] Apart from the malformed substitutions, no message repeats what you typed, and none shows a port number, a file path or a command.

**Pass / Fail:**
**Notes:**

## TC 2.3 Score the Example (Mock Data)

- [ ] Open `http://localhost:5173/csnp`, click **Use an example**, then **Score substitutions**. The button shows a spinner for a moment.
- [ ] The address changes to `/jobs/` followed by a long id, and the page is headed **Coding SNP impact scoring**.
- [ ] The status shows **Queued**, then **Running**, then **Succeeded**, without a reload.
- [ ] The page shows **PANTHER family** `PTHR00000`.
- [ ] A **Scores** table has four rows, in the order you typed: `L46P`, `C130R`, `R163C`, `R176C`, with columns **Substitution**, **Age (Mya)**, **Prediction or message** and **pDel**.
- [ ] The `R176C` row reads "Not scored: Invalid substitution", with its age and pDel empty.
- [ ] **Versions used** lists the API, the engine, the four tools and **csnp data** `PANTHER 9`, matching the footer.
- [ ] A dark banner at the very top says **Mock data**, and that nothing on the page comes from the scoring service. Scroll to the end of the page: the banner is still at the top of the window.
- [ ] On a phone, or with the browser window narrowed to phone width, the page doesn't scroll sideways, every column is visible, and the banner's text wraps without being cut off.

**Pass / Fail:**
**Notes:**

## Against the Real API

Stop the mock website with Ctrl+C. If `.data/csnp/9/` isn't there yet, fetch the data sample, from `engine/`, with `uv run panther-engine csnp sample fetch --data-dir ../.data`. Then, from the repository root, start the API:

```sh
docker compose up --build api
```

Leave it running. It's ready when `http://localhost:8000/api/v1/health` shows `{"status":"ok"}`. In a second terminal, start the website against it:

```sh
cd frontend
npm run dev:api
```

## TC 2.4 Score a Protein With the Real API

The data sample holds 16 PANTHER families. This test case uses a protein of one of them, P26439, from the PSEP release's sample, so its scores are real and known.

- [ ] Open `http://localhost:5173/csnp`. There is no **Mock data** banner at the top of the page.
- [ ] Paste the second line of `engine/tests/golden/csnp/release/sample.fasta` (one line of residues starting `MGWSCLVTGA`) into **Protein sequence**. Type `A10E G15D S213G M1V` in **Substitutions**, and leave **Species** as `Homo sapiens (HUMAN)`. Click **Species** first: the list has 85 species, among them `Canis familiaris (CANFA)`.
- [ ] Click **Score substitutions**. A job page opens, and within about 10 seconds the status shows **Succeeded**, without a reload.
- [ ] The page shows **PANTHER family** `PTHR10366`.
- [ ] The **Scores** table has four rows, in this order: `A10E`, `220`, "possibly damaging", `0.50`; `G15D`, `4200`, "probably damaging", `0.95`; `S213G`, `91`, "probably benign", `0.19`; `M1V`, an empty age, "Not scored: Invalid substitution", an empty pDel.
- [ ] **Versions used** lists the API, the engine, the four tools and **csnp data** `PANTHER 9`, matching the footer.
- [ ] Reload the page. It shows the same job and scores.
- [ ] Go back to `/csnp`, click **Use an example**, then **Score substitutions**. The example is human APOE, whose family the sample holds too: the job succeeds with **PANTHER family** `PTHR18976`, and the **Scores** table has four rows, in this order: `L46P`, `91`, "probably benign", `0.19`; `C130R`, `6`, "probably benign", `0.02`; `R163C`, `220`, "possibly damaging", `0.50`; `R176C`, `220`, "possibly damaging", `0.50`.
- [ ] Go back to `/csnp`, type `1234567890` as the sequence, `A10E` as the substitution, and submit. The job page says the job failed, and that the sequence can't be read as a protein sequence. It shows no scores.
- [ ] No page shows an error code, port number, file path or command.

**Pass / Fail:**
**Notes:**

## TC 2.5 The API Checks the Input Too

The form checks the same rules as the API, so a request the API would reject isn't sent from the form. This test case sends one directly. The end-to-end tests check that the form shows such an error on its field.

- [ ] In a third terminal, send a request with an invalid species and no substitutions (the command in `docs/testing/api.md`, "Requests That Are Refused"):

  ```sh
  curl -si localhost:8000/api/v1/jobs -H 'Content-Type: application/json' \
    -d '{"service": "csnp", "input": {"sequence": "MKVLWAALLV", "substitutions": [], "species": "human; id"}}'
  ```

- [ ] The answer is `422`, with one error whose `loc` ends in `"substitutions"` and one whose `loc` ends in `"species"`.
- [ ] The answer doesn't contain `human; id`.
- [ ] Send it again with `"species": "ZZZZZ"`, the shape of a species code but not a species in the cSNP data. The answer is `422`, with an error whose `loc` ends in `"species"`, and it doesn't contain `ZZZZZ`.
- [ ] Back in the browser, the form at `/csnp` still works: the example still opens a job page.

**Pass / Fail:**
**Notes:**

## TC 2.6 The Species List Can't Be Loaded

The form must still work when the API can't send the species list. Leave the website running with `npm run dev:api`.

- [ ] In the API's terminal, stop it with Ctrl+C.
- [ ] Open a new private (incognito) window, so the browser has no copy of the list, and go to `http://localhost:5173/csnp`. **Species** is a plain box holding `HUMAN`. Under its label, a note says the list of species couldn't be loaded and to type a PANTHER species code, and a **Load the list of species again** button is below the box. Nothing shows an error code, port number, file path or command.
- [ ] Clear the box and click **Score substitutions** with the other boxes filled (use the example). The species box asks for a species code.
- [ ] Type `human`, and submit. The species box asks for upper-case letters or digits.
- [ ] Type `MOUSE`. Start the API again with `docker compose up api` from the repository root, and wait until `http://localhost:8000/api/v1/health` shows `{"status":"ok"}`.
- [ ] Click **Load the list of species again**. **Species** becomes the list again, reading `Mus musculus (MOUSE)`.

**Pass / Fail:**
**Notes:**

## When You're Done

Stop the website with Ctrl+C, then stop the API with Ctrl+C and remove it with `docker compose down` from the repository root.
