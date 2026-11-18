# 04: HMM Scoring Form

Checks the HMM scoring form: its notice that HMM scoring isn't available yet, the example, the checks it makes before sending, and the results page with mock data; then, against the real API, that a sequence is answered as not available yet and kept. The first three test cases use mock data; the last uses the real API. About 15 minutes.

## Before You Start

You need Node `^22.22.2` or `>=24.15.0`, and for TC 4.4, Docker (with compose). Ports 8000 and 5173 must be free.

For TC 4.1 to TC 4.3, start the website with mock data:

```sh
cd frontend
npm ci
npm run dev
```

Then open `http://localhost:5173` in a browser.

**With mock data, every sequence gets the same made-up hit,** `PTHR00000:SF1`, named **MOCK FAMILY**, and an alignment whose first line says it's mock data. `PTHR00000` is not a real PANTHER family, so its link leads to a pantherdb.org page for a family that doesn't exist. Every page says so in a dark **Mock data** banner at the top.

## TC 4.1 Open the Form and Use the Example

- [ ] The home page has an **HMM scoring** section, marked **Coming soon**, with a **Score a protein sequence** button. In the header, the **HMM scoring** tab is marked **Soon**.
- [ ] Click **Score a protein sequence**. The address changes to `/hmmscore`, the page is headed **HMM scoring**, and the **HMM scoring** tab is underlined as the current page.
- [ ] Above the **Protein sequence** box, a note says HMM scoring isn't available on this site yet, so a sequence submitted now won't be scored.
- [ ] The box is empty, and the **Score sequence** button can be clicked.
- [ ] Click **Use an example**. The box fills with human APOE: ten lines, the first `MKVLWAALLVTFLAGCQAKVEQAVETEPEPELRQQ`, each 35 letters long but the last, `NH`, and no `>` header line.
- [ ] Go home, and click the **HMM scoring** tab in the header. The form opens again, empty.

**Pass / Fail:**
**Notes:**

## TC 4.2 Mistakes Show Before Sending

- [ ] Click **Score sequence** with the box empty. The box turns red, and the message under it says the sequence has no residues. The address stays `/hmmscore`.
- [ ] Type `>my protein` on one line and `*` on the next, and click **Score sequence**. The message still says there are no residues: a `*` alone isn't a protein.
- [ ] Replace the text with `MKV1L`, and click **Score sequence**. The message says which characters a sequence may hold: the letters A to Z, and `.`, `_`, `~` and `*`. It doesn't repeat `MKV1L`. Try `MKV-L` and `MKVÄL`: the same message.
- [ ] Replace the text with `>one`, `MKV`, `>two`, `MKV`, each on its own line. The message says to submit one protein.
- [ ] Type a letter in the box. The red and the message go.
- [ ] Replace the text with `mkvbjouxz*`, and click **Score sequence**. No message shows, and a job page opens: lower case, the uncommon letters and a final `*` are accepted.
- [ ] No message shows a port number, a file path or a command.

**Pass / Fail:**
**Notes:**

## TC 4.3 Score the Example (Mock Data)

- [ ] Open `http://localhost:5173/hmmscore`, click **Use an example**, then **Score sequence**. The button shows a spinner for a moment.
- [ ] The address changes to `/jobs/` followed by a long id, the page is headed **HMM scoring**, and the **HMM scoring** tab is marked as current.
- [ ] The status shows **Queued**, then **Running**, then **Succeeded**, without a reload.
- [ ] The page shows **PANTHER ID** `PTHR00000:SF1`, **Name** **MOCK FAMILY**, **E-value** `7e-131` and **Bit score** `439.0`, written exactly so.
- [ ] Click `PTHR00000:SF1`. pantherdb.org's family page opens in a new tab, its address ending `clsAccession=PTHR00000%3ASF1`; this page stays open in the first tab. A screen reader names the link as opening in a new tab.
- [ ] Under **Alignment**, the alignment shows in a fixed-width font, its first line saying it's mock data, with its columns lined up and no line wrapped.
- [ ] Press Tab until the alignment's box is outlined, then press the right arrow a few times. The alignment scrolls sideways within its box.
- [ ] **Versions used** lists the API, the engine and the four tools, matching the footer.
- [ ] Click **New HMM scoring search**. The form opens, empty, without the note about an earlier job.
- [ ] Press the browser's Back button, and click **Edit and resubmit**. The form opens with a note that it was filled in from your earlier job, and the box holds the example as it was.
- [ ] On a phone, or with the browser window narrowed to phone width, the form and the results page don't scroll sideways; only the alignment's box does, when you swipe it.

**Pass / Fail:**
**Notes:**

## Against the Real API

Stop the mock website with Ctrl+C. From the repository root, start the API:

```sh
docker compose up --build api
```

Leave it running. It's ready when `http://localhost:8000/api/v1/health` shows `{"status":"ok"}`. HMM scoring needs no data yet. In a second terminal, start the website against it:

```sh
cd frontend
npm run dev:api
```

## TC 4.4 HMM Scoring Isn't Available Yet (Real API)

- [ ] Open `http://localhost:5173/hmmscore`. There is no **Mock data** banner at the top of the page, and the note above the box says HMM scoring isn't available on this site yet.
- [ ] Click **Use an example**, then **Score sequence**. A message under the box says HMM scoring isn't available yet, and no job was started. The address stays `/hmmscore`.
- [ ] The box still holds the example, and **Score sequence** can be clicked again, with the same message.
- [ ] Replace the text with `MKV1L`, and click **Score sequence**. The form's own message about the characters shows, as in TC 4.2.
- [ ] No message shows an error code, such as 501, a port number, a file path or a command.

**Pass / Fail:**
**Notes:**

## When You're Done

Stop the website with Ctrl+C, then stop the API with Ctrl+C and remove it with `docker compose down` from the repository root.
