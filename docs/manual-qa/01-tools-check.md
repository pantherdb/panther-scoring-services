# 01: Scoring Tools Check

Checks that the website, the API, the engine and the scoring tools work together, using the "Check the scoring tools" button on the home page. It starts a small job that reports each tool's version; no scoring is done. About 10 minutes.

## Before You Start

You need Docker (with compose) and Node `^22.22.2` or `>=24.15.0`. Ports 8000 and 5173 must be free.

1. From the repository root, start the API with the real tools:

   ```sh
   docker compose up --build api
   ```

   Leave it running. It's ready when `http://localhost:8000/api/v1/health` shows `{"status":"ok"}`.
2. In a second terminal, start the website against that API:

   ```sh
   cd frontend
   npm ci
   npm run dev:api
   ```

3. Open `http://localhost:5173` in a browser.

The versions below are the ones pinned in the API image today. If the image changes, expect what the footer shows instead.

## TC 1.1 The Home Page

- [ ] The header reads **PANTHER Scoring**.
- [ ] The footer lists **API**, **Engine**, `blastp` 2.17.0, `hmmscan` 3.4, `hmmsearch` 3.4 and `epa-ng` 0.3.8.
- [ ] Below the page's main text, a **Scoring tools** section has a plain (not coloured) **Check the scoring tools** button.

**Pass / Fail:**
**Notes:**

## TC 1.2 Run the Check

- [ ] Click **Check the scoring tools**. The button shows a spinner for a moment and can't be clicked again.
- [ ] The address changes to `/jobs/` followed by a long id, and the page is headed **Scoring tools check**.
- [ ] The status shows **Queued** or **Running**, with "This page updates by itself" and a spinner.
- [ ] Without reloading, the status changes to **Succeeded** within a few seconds. The first check after the API starts can take a second or two longer.
- [ ] The page shows "Ran for" and a time in seconds.
- [ ] A **Tools** table lists `blastp`, `hmmscan`, `hmmsearch` and `epa-ng`, in that order, each with a version.
- [ ] **Versions used** lists the API, the engine and the same four tools, matching the footer.

**Pass / Fail:**
**Notes:**

## TC 1.3 The Result Has Its Own Address

- [ ] Reload the page. It shows the same job, still **Succeeded**, with the same table.
- [ ] Copy the address into a new tab. It shows the same job.
- [ ] Click **Check the scoring tools** again from the home page. The new job has a different id.

**Pass / Fail:**
**Notes:**

## TC 1.4 A Job That Doesn't Exist

- [ ] Open `http://localhost:5173/jobs/not-a-job`. The page is headed **Job not found**, and says the job may have expired.
- [ ] Change one character of a real job's id in the address bar and open it. It also shows **Job not found**.
- [ ] Neither page shows a port number, a file path, an error code or a command.
- [ ] **Back to home** returns to the home page.

**Pass / Fail:**
**Notes:**

## TC 1.5 The API Is Down

- [ ] Stop the API: press Ctrl+C in its terminal.
- [ ] Reload a job's page. It's headed **Job unavailable**, says the scoring service can't be reached, and has a **Try again** button. It shows no status and no table.
- [ ] Go to the home page and click **Check the scoring tools**. A message says the scoring service can't be reached; the address stays on the home page.
- [ ] Neither message shows a port number, a file path, an error code or a command.
- [ ] Start the API again (`docker compose up api`), wait until it's ready, then click **Try again** on the job's page. It now says **Job not found**: the API keeps jobs in memory, so they're lost when it restarts.
- [ ] Click **Check the scoring tools** on the home page again. The check runs and succeeds.

**Pass / Fail:**
**Notes:**

## When You're Done

Stop the website with Ctrl+C, then stop the API with Ctrl+C and remove it with `docker compose down` from the repository root.
