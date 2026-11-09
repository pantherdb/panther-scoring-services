# 03: Protein ID Mapping Form

Checks the protein ID mapping form: choosing the organism, filling the IDs, loading a file, the checks it makes before sending, and the results page with mock data; then, against the real API, that the example maps to the legacy service's answers. The first four test cases use mock data; the last uses the real API. About 20 minutes.

## Before You Start

You need Node `^22.22.2` or `>=24.15.0`, and for TC 3.5, Docker (with compose) and the refmap data in `.data/` at the repository root (523 MB, fetched once; see `docs/testing/api.md`). Ports 8000 and 5173 must be free. For TC 3.2, make a text file named `ids.txt` with three lines: `P04217`, a tab and `1.5`; `P01023`, a tab and `0.2`; and `P02649` on its own. A spreadsheet saved as tab-separated text, with the IDs in the first column and the numbers in the second, gives the same file.

For TC 3.1 to TC 3.4, start the website with mock data:

```sh
cd frontend
npm ci
npm run dev
```

Then open `http://localhost:5173` in a browser.

**With mock data, the organism list has only six organisms,** real ones, such as Endocarpon pusillum (ENDPU); the real list has 1,533. **The example's mappings in TC 3.4 are the legacy service's answers;** any other ID's mapping is mock data, made up to show the results page: `PTHR00000` is not a real PANTHER family, and which IDs map was decided by their letters, not by any data. Every page says so in a dark **Mock data** banner at the top.

## TC 3.1 Open the Form, Choose an Organism and Use the Example

- [ ] The home page has a **Protein ID mapping** section, below **Coding SNP impact scoring**, with a **Map protein IDs** button, and not marked **Coming soon**. In the header, the **ID mapping** tab isn't marked coming soon either; **HMM scoring** and **TreeGrafter** are.
- [ ] Click **Map protein IDs**. The address changes to `/refmap`, and the page is headed **Protein ID mapping**.
- [ ] The **Protein IDs** box and the **Organism** selector are empty, and under the IDs box it says **No IDs yet.**
- [ ] Click the organism selector. It lists the organisms by name, each with its code in brackets, such as **Endocarpon pusillum (ENDPU)**, sorted by name.
- [ ] Type `pusill`. Only **Endocarpon pusillum (ENDPU)** and **Micromonas pusilla (MICPC)** are left. Clear it and type `eco57`: only **Escherichia coli O157:H7 (ECO57)** is left. Choose it.
- [ ] Click **Use an example**. The IDs box fills with six IDs, one per line: `U1G4Q5`, `U1GCA1`, `U1HRR6`, `U1GLV9`, `U1GJ40`, `U1HQ27`. The organism is **Endocarpon pusillum (ENDPU)**. Under the box it says **6 IDs will be sent.**
- [ ] Add `P04217, p04217` on a new line. The count says **8 IDs will be sent.**: a comma separates IDs, and lower case is a different ID.
- [ ] Using only the keyboard, Tab to the organism selector, type `araneus`, press the down arrow and Enter. The organism is **Araneus ventricosus (ARAVE)**.

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

- [ ] Reload `/refmap`, and click **Map IDs**. Both fields turn red, each with a message under it; the organism's asks for an organism from the list. The address stays `/refmap`.
- [ ] Choose an organism. Its message goes; the IDs box's stays.
- [ ] Click **Use an example**. Add two lines to the IDs: `P0é4217`, then `Q9Y6K9`, a space and 70 `A`s on one line. Click **Map IDs**. The IDs box names ID 7 (`P0é4217`, line 7) and ID 9 (the start of the `A`s, cut short with `…`, line 8), and says each ID must be 1 to 64 printable ASCII characters.
- [ ] Remove the two lines. Click **Map IDs**: no message shows, and a job page opens.
- [ ] No message shows a port number, a file path or a command.

**Pass / Fail:**
**Notes:**

## TC 3.4 Map the Example (Mock Data)

- [ ] Open `http://localhost:5173/refmap`, click **Use an example**, then **Map IDs**. The button shows a spinner for a moment.
- [ ] The address changes to `/jobs/` followed by a long id, and the page is headed **Protein ID mapping**.
- [ ] The status shows **Queued**, then **Running**, then **Succeeded**, without a reload.
- [ ] The page says **Mapped against Endocarpon pusillum (ENDPU).** and **6 IDs: 5 have a PANTHER ID, 1 has none.**
- [ ] A **Mappings** table has six rows numbered 1 to 6, in the order of the example, with columns **#**, **ID** and **PANTHER ID**: `U1G4Q5` `PTHR11360:SF130`, `U1GCA1` `PTHR21058:SF0`, `U1HRR6` `PTHR42765:SF2`, `U1GLV9` `PTHR28011`, `U1GJ40` `PTHR13401`, and `U1HQ27` **No PANTHER ID**.
- [ ] There are no page buttons under the table: six rows fit one page.
- [ ] Click **Download the mappings (TSV)**. The browser saves `panther-id-mapping-` followed by the job's id and `.tsv`. Open it in a text editor: the first line is `id` and `panther_id` with a tab between, then the six IDs in order, each with its PANTHER ID after a tab, and nothing after `U1HQ27`'s tab.
- [ ] **Versions used** lists the API, the engine and the four tools, matching the footer, and only this job's data: **refmap data** `PANTHER 19`, not cSNP's `PANTHER 9`.
- [ ] Go back to `/refmap`, load a file of more than 100 IDs (for example, `ids.txt`'s lines copied 50 times), choose **Endocarpon pusillum (ENDPU)**, and click **Map IDs**. The results show 100 rows, "Rows 1 to 100 of", and page buttons. Click page 2: the rows go on from 101.
- [ ] On a phone, or with the browser window narrowed to phone width, the form and the results don't scroll sideways, the organism selector's list opens under it without the page jumping, and the page buttons fit.

**Pass / Fail:**
**Notes:**

## Against the Real API

Stop the mock website with Ctrl+C. If `.data/refmap/19/` isn't there yet, fetch the refmap data, from `engine/`, with `uv run panther-engine refmap data fetch --data-dir ../.data`. Then, from the repository root, start the API:

```sh
docker compose up --build api
```

Leave it running. It's ready when `http://localhost:8000/api/v1/health` shows `{"status":"ok"}`. In a second terminal, start the website against it:

```sh
cd frontend
npm run dev:api
```

## TC 3.5 Map the Example (Real API)

- [ ] Open `http://localhost:5173/refmap`. There is no **Mock data** banner at the top of the page.
- [ ] Click the organism selector, and type `coli`. It offers many Escherichia coli strains, more than the six organisms of the mock list. Type `ENDPU` instead: it offers **Endocarpon pusillum (ENDPU)**.
- [ ] Click **Use an example**, then **Map IDs**. A job page opens, and its status reaches **Succeeded** within a few seconds.
- [ ] The page says **Mapped against Endocarpon pusillum (ENDPU).** and **6 IDs: 5 have a PANTHER ID, 1 has none.**, and the table shows the same six mappings as in TC 3.4, `U1HQ27` with **No PANTHER ID**.
- [ ] **Versions used** lists the API and the engine, as the footer does.
- [ ] No message shows an error code, port number, file path or command.

**Pass / Fail:**
**Notes:**

## When You're Done

Stop the website with Ctrl+C, then stop the API with Ctrl+C and remove it with `docker compose down` from the repository root.
