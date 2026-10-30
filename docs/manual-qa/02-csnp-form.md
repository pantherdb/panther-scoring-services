# 02: cSNP Form

Checks the coding SNP scoring form: filling it, the checks it makes before sending, the results page, and what it says while the real API can't score cSNP yet. The first three test cases use mock data, because the API doesn't score cSNP yet; the last two use the real API. About 15 minutes.

## Before You Start

You need Node `^22.22.2` or `>=24.15.0`, and for TC 2.4 and TC 2.5, Docker (with compose) and `curl`. Ports 8000 and 5173 must be free.

For TC 2.1 to TC 2.3, start the website with mock data:

```sh
cd frontend
npm ci
npm run dev
```

Then open `http://localhost:5173` in a browser.

**The results in TC 2.3 are mock data,** made up to show the results page: family `PTHR00000` is not a real PANTHER family, and the ages, predictions and pDel values were not computed. Don't compare them with the legacy site. Every page says so in a dark **Mock data** banner at the top.

## TC 2.1 Open the Form

- [ ] The home page's **Coding SNP impact scoring** section has a **Score coding SNPs** button.
- [ ] Click it. The address changes to `/csnp`, and the page is headed **Coding SNP impact scoring**.
- [ ] The **Protein sequence** and **Substitutions** boxes are empty, and **Species** reads `HUMAN`.
- [ ] Click **Use an example**. The sequence box fills with ten lines of residues starting `MKVLWAALLV`, the substitutions box with `L46P`, `C130R`, `R163C` and `R176C`, one per line, and the species is `HUMAN`.

**Pass / Fail:**
**Notes:**

## TC 2.2 Mistakes Show Before Sending

- [ ] Reload `/csnp`, clear **Species**, and click **Score substitutions**. All three boxes turn red, each with a message under it. The address stays `/csnp`.
- [ ] Type one letter in the sequence box. Its message goes; the other two stay.
- [ ] Click **Use an example**. Every message goes.
- [ ] Add a second FASTA sequence: put `>one` on a new first line and `>two` above the last line. Click **Score substitutions**. The sequence box says it holds more than one sequence.
- [ ] Click **Use an example** again, change **Species** to `human`, and submit. The species box asks for upper-case letters or digits.
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
- [ ] **Versions used** lists the API, the engine and the four tools, matching the footer.
- [ ] A dark banner at the very top says **Mock data**, and that nothing on the page comes from the scoring service. Scroll to the end of the page: the banner is still at the top of the window.
- [ ] On a phone, or with the browser window narrowed to phone width, the page doesn't scroll sideways, every column is visible, and the banner's text wraps without being cut off.

**Pass / Fail:**
**Notes:**

## Against the Real API

Stop the mock website with Ctrl+C. From the repository root, start the API:

```sh
docker compose up --build api
```

Leave it running. It's ready when `http://localhost:8000/api/v1/health` shows `{"status":"ok"}`. In a second terminal, start the website against it:

```sh
cd frontend
npm run dev:api
```

## TC 2.4 cSNP Scoring Isn't Available Yet

- [ ] Open `http://localhost:5173/csnp`. There is no **Mock data** banner at the top of the page.
- [ ] Click **Use an example**, then **Score substitutions**.
- [ ] A message says cSNP scoring isn't available yet, and that your input is kept.
- [ ] The address stays `/csnp`, and the sequence, the four substitutions and `HUMAN` are all still there.
- [ ] The message shows no error code (such as 501), port number, file path or command.
- [ ] Click **Score substitutions** again. The same message shows; nothing else changes.

**Pass / Fail:**
**Notes:**

## TC 2.5 The API Checks the Input Too

The form checks the same rules as the API, so a request the API would reject isn't sent from the form. This test case sends one directly. The end-to-end tests check that the form shows such an error on its field.

- [ ] In a third terminal, send a request with an invalid species and no substitutions (the second command in `docs/testing/api.md`, "The cSNP Job: Validated, Not Scored Yet"):

  ```sh
  curl -si localhost:8000/api/v1/jobs -H 'Content-Type: application/json' \
    -d '{"service": "csnp", "input": {"sequence": "MKVLWAALLV", "substitutions": [], "species": "human; id"}}'
  ```

- [ ] The answer is `422`, with one error whose `loc` ends in `"substitutions"` and one whose `loc` ends in `"species"`.
- [ ] The answer doesn't contain `human; id`.
- [ ] Back in the browser, the form at `/csnp` still works: TC 2.4's message shows for the example.

**Pass / Fail:**
**Notes:**

## When You're Done

Stop the website with Ctrl+C, then stop the API with Ctrl+C and remove it with `docker compose down` from the repository root.
