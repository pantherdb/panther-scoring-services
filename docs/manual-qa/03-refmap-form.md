# 03: Protein ID Mapping Form

Checks the protein ID mapping form: filling it, loading a file, the checks it makes before sending, and the results page with mock data; then, against the real API, that it says mapping isn't available yet. The first four test cases use mock data; the last uses the real API. About 15 minutes.

## Before You Start

You need Node `^22.22.2` or `>=24.15.0`, and for TC 3.5, Docker (with compose). Ports 8000 and 5173 must be free. For TC 3.2, make a text file named `ids.txt` with three lines: `P04217`, a tab and `1.5`; `P01023`, a tab and `0.2`; and `P02649` on its own. A spreadsheet saved as tab-separated text, with the IDs in the first column and the numbers in the second, gives the same file.

For TC 3.1 to TC 3.4, start the website with mock data:

```sh
cd frontend
npm ci
npm run dev
```

Then open `http://localhost:5173` in a browser.

**The mappings in TC 3.4 are mock data,** made up to show the results page: `PTHR00000` is not a real PANTHER family, and which IDs map was decided by their letters, not by any data. Don't compare them with the legacy site. Every page says so in a dark **Mock data** banner at the top.

## TC 3.1 Open the Form and Use the Example

- [ ] The home page has a **Protein ID mapping** section, below **Coding SNP impact scoring**, with a **Map protein IDs** button.
- [ ] Click it. The address changes to `/refmap`, and the page is headed **Protein ID mapping**.
- [ ] The **Protein IDs** and **Organism** boxes are empty, and under the IDs box it says **No IDs yet.**
- [ ] Click **Use an example**. The IDs box fills with six IDs, one per line: `P04217`, `P01023`, `P02649`, `P04637`, `P38398`, `P00533`. The organism is `HUMAN`. Under the box it says **6 IDs will be sent.**
- [ ] Add `P04217, p04217` on a new line. The count says **8 IDs will be sent.**: a comma separates IDs, and lower case is a different ID.

**Pass / Fail:**
**Notes:**

## TC 3.2 Load IDs From a File

- [ ] Reload `/refmap`, and type `ZZZ` in the IDs box.
- [ ] Click **Load IDs from a text file**, and choose `ids.txt`. The box now holds the file's three lines, and `ZZZ` is gone.
- [ ] Under the box it says **3 IDs will be sent.**, and that only the first column was read on 2 lines.
- [ ] Choose `ids.txt` again. The box still holds its three lines.
- [ ] Choose a file larger than 10 MB, if you have one (a video, for example). The IDs box says the file is larger than 10 MB and wasn't read, and still holds the three lines.

**Pass / Fail:**
**Notes:**

## TC 3.3 Mistakes Show Before Sending

- [ ] Reload `/refmap`, and click **Map IDs**. Both boxes turn red, each with a message under it. The address stays `/refmap`.
- [ ] Type `H` in the organism box. Its message goes; the IDs box's stays.
- [ ] Click **Use an example**, change the organism to `human`, and click **Map IDs**. The organism box asks for 1 to 5 upper-case letters or digits, and doesn't repeat `human`.
- [ ] Change the organism back to `HUMAN`. Add two lines to the IDs: `P0é4217`, then `Q9Y6K9`, a space and 70 `A`s on one line. Click **Map IDs**. The IDs box names ID 7 (`P0é4217`, line 7) and ID 9 (the start of the `A`s, cut short with `…`, line 8), and says each ID must be 1 to 64 printable ASCII characters.
- [ ] Remove the two lines. Click **Map IDs**: no message shows, and a job page opens.
- [ ] No message shows a port number, a file path or a command.

**Pass / Fail:**
**Notes:**

## TC 3.4 Map the Example (Mock Data)

- [ ] Open `http://localhost:5173/refmap`, click **Use an example**, then **Map IDs**. The button shows a spinner for a moment.
- [ ] The address changes to `/jobs/` followed by a long id, and the page is headed **Protein ID mapping**.
- [ ] The status shows **Queued**, then **Running**, then **Succeeded**, without a reload.
- [ ] The page says **6 IDs: 5 have a PANTHER ID, 1 has none.**
- [ ] A **Mappings** table has six rows numbered 1 to 6, in the order of the example, with columns **#**, **ID** and **PANTHER ID**. `P38398`'s PANTHER ID reads **No PANTHER ID**; the others read `PTHR00000:SF` and a digit.
- [ ] There are no page buttons under the table: six rows fit one page.
- [ ] Click **Download the mappings (TSV)**. The browser saves `panther-id-mapping-` followed by the job's id and `.tsv`. Open it in a text editor: the first line is `id` and `panther_id` with a tab between, then the six IDs in order, each with its PANTHER ID after a tab, and nothing after `P38398`'s tab.
- [ ] **Versions used** lists the API, the engine, the four tools and **csnp data** `PANTHER 9`, matching the footer.
- [ ] Go back to `/refmap`, load a file of more than 100 IDs (for example, `ids.txt`'s lines copied 50 times), type `HUMAN`, and click **Map IDs**. The results show 100 rows, "Rows 1 to 100 of", and page buttons. Click page 2: the rows go on from 101.
- [ ] On a phone, or with the browser window narrowed to phone width, the form and the results don't scroll sideways, and the page buttons fit.

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

## TC 3.5 Mapping Isn't Available Yet

The API checks a protein ID mapping request, then refuses it until the engine can map IDs.

- [ ] Open `http://localhost:5173/refmap`. There is no **Mock data** banner at the top of the page.
- [ ] Click **Use an example**, then **Map IDs**. A message says protein ID mapping isn't available yet, and that your input is kept. The address stays `/refmap`, and both boxes still hold the example.
- [ ] The message shows no error code, port number, file path or command.
- [ ] Click **Map IDs** again. The same message shows: the form still works.

**Pass / Fail:**
**Notes:**

## When You're Done

Stop the website with Ctrl+C, then stop the API with Ctrl+C and remove it with `docker compose down` from the repository root.
