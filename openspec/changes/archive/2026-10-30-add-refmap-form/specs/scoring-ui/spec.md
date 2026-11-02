# Spec Delta

## ADDED Requirements

### Requirement: refmap form

The UI SHALL offer a refmap form at `/refmap`, linked from the home page. It MUST have a box for protein IDs, a box for an organism code that starts empty, and a count of the IDs that will be sent. An action MUST fill both boxes with an example: human UniProt accessions and `HUMAN`.

#### Scenario: Open the form from the home page

- **WHEN** the user opens `/` and follows the link to protein ID mapping
- **THEN** the UI shows `/refmap`, with an empty IDs box, an empty organism box, and no IDs counted

#### Scenario: Use the example

- **WHEN** the user chooses to use an example on `/refmap`
- **THEN** the IDs box holds `P04217`, `P01023`, `P02649`, `P04637`, `P38398` and `P00533`, one per line, the organism is `HUMAN`, and the form says 6 IDs will be sent

### Requirement: refmap IDs split by line, first column

The UI SHALL read each line of the IDs box up to its first tab, and split what's before the tab at every run of whitespace and commas, dropping empty pieces. The IDs MUST be sent as typed, in order, repeats included: not trimmed further, case-changed or de-duplicated. The form MUST say on how many lines something after a tab was left out.

#### Scenario: One per line, and lists on a line

- **WHEN** the IDs box holds `"P04217\r\nP01023, P02649  P04637\n\n"`
- **THEN** the request's `ids` is `["P04217", "P01023", "P02649", "P04637"]`

#### Scenario: Kept as typed

- **WHEN** the IDs box holds `"P04217 p04217 P04217 P04217-2"`
- **THEN** the request's `ids` is `["P04217", "p04217", "P04217", "P04217-2"]`

#### Scenario: A second column

- **WHEN** the IDs box holds `"P04217\t1.5\nP01023\t0.2"`
- **THEN** the request's `ids` is `["P04217", "P01023"]`, and the form says the first column was read on 2 lines

### Requirement: refmap IDs loaded from a text file

The refmap form SHALL let the user load a text file into the IDs box, read in the browser and never uploaded, replacing the box's text. The loaded text MUST be split, counted and checked as typed text is. A file larger than 10 MB, or one that can't be read, MUST NOT change the box, and the IDs field MUST say why in fixed text.

#### Scenario: A file of IDs

- **WHEN** the user loads a text file holding `"P04217\nP01023\tA1BG"`
- **THEN** the IDs box holds that text, the form says 2 IDs will be sent, and nothing is sent until the user submits

#### Scenario: A file too large

- **WHEN** the user loads a file of more than 10 MB
- **THEN** the IDs field says the file is larger than 10 MB, and the box keeps its text

### Requirement: refmap form checks the input before sending

Before sending, the refmap form SHALL check the input against `scoring-input`'s refmap rules: the organism, trimmed, and the IDs as split. Each broken rule MUST be shown on its field, and no request MUST be sent while any is broken. An ID that breaks the rules MUST be named by its place in the list, its line and as typed, at most ten, then a count. The form MUST NOT reject an input the rules accept.

#### Scenario: Empty form

- **WHEN** the user submits the form with both boxes empty
- **THEN** the IDs and organism fields each show an error, and no request is sent

#### Scenario: Too many IDs

- **WHEN** the user submits 100,001 IDs
- **THEN** the IDs field says at most 100,000 can be sent, and no request is sent

#### Scenario: IDs that aren't IDs

- **WHEN** the user submits the IDs `"P04217\nP0é4217\nP04217 <65 characters>"`
- **THEN** the IDs field names ID 2 on line 2, `P0é4217`, and ID 4 on line 3, the start of the long one, and no request is sent

#### Scenario: Not an organism code

- **WHEN** the user submits the organism `human`, `HOMOSAPIENS` or `../x`
- **THEN** the organism field shows an error that doesn't quote it, and no request is sent

#### Scenario: A valid input is sent

- **WHEN** the user submits 100,000 IDs of up to 64 printable ASCII characters, in any case, and the organism ` HUMAN `
- **THEN** no field shows an error, and the request is sent with those IDs and `HUMAN`

### Requirement: refmap server field errors shown on their fields

When the API answers a refmap request with a 422 validation problem, the form SHALL show each error's `msg` on the field its `loc` names, and keep the user's input. An error about one ID MUST name it by its place, its line and the ID as sent, taken from the form's own copy. An error whose `loc` names no field of the form MUST be shown with the form. The UI MUST NOT open a job page.

#### Scenario: The API rejects the organism

- **WHEN** the API answers 422 with an error whose `loc` is `["body", "refmap", "input", "organism"]`
- **THEN** the organism field shows that error's `msg`, both boxes are unchanged, and the UI stays at `/refmap`

#### Scenario: The API rejects one ID

- **WHEN** the user submits the IDs `"P04217\np04217, P01023"` and the API answers 422 with an error whose `loc` is `["body", "refmap", "input", "ids", 2]`
- **THEN** the IDs field shows that error's `msg`, saying it's about ID 3, `P01023`, on line 2

#### Scenario: An error on no field

- **WHEN** the API answers 422 with an error whose `loc` is `["body", "refmap", "input", "fileContents"]`
- **THEN** the form shows that error's `msg` with the form

### Requirement: refmap mapping not yet available

When the API answers a refmap request with 501, the form SHALL say that protein ID mapping isn't available yet, in fixed text, keep the user's input, and stay at `/refmap`. When the API can't be reached, it MUST say so, as the cSNP form does; when it answers with any other error, it MUST say the job couldn't be started. Neither message MUST show a status code or build details, and the form MUST stay usable.

#### Scenario: The API answers 501

- **WHEN** the user submits a valid input and the API answers 501
- **THEN** the form says protein ID mapping isn't available yet, both boxes are unchanged, the UI stays at `/refmap`, and the form can be submitted again

#### Scenario: The API answers 500

- **WHEN** the user submits a valid input and the API answers 500 with problem details
- **THEN** the form says the job couldn't be started, with no status code or build details

#### Scenario: The network fails

- **WHEN** the user submits a valid input and the request fails with a network error
- **THEN** the form says the scoring service can't be reached, and keeps the input

### Requirement: Submitting a refmap request opens its job

When the API accepts a refmap request with 202, the UI SHALL open `/jobs/{id}` for the new job. While the request is in flight, the submit action MUST be disabled.

#### Scenario: The API accepts the request

- **WHEN** the user submits a valid input and the API answers 202 with a `refmap` job
- **THEN** the UI shows `/jobs/{id}` for that job, headed as protein ID mapping

#### Scenario: While submitting

- **WHEN** the user has submitted a valid input and the API hasn't answered yet
- **THEN** the submit action is disabled

### Requirement: refmap results on the job page

When a `refmap` job has succeeded, the job page SHALL say how many IDs it has, how many have a PANTHER ID and how many have none, and show a table with one row per mapping, in the order given: its place counted from 1, the ID, and the PANTHER ID exactly as the API gives it, or "No PANTHER ID" for `null`. The job's versions MUST be shown with it.

#### Scenario: A mapped job

- **WHEN** the user opens the page of a succeeded `refmap` job whose mappings are `P04217` to `PTHR00000:SF4`, `P38398` to `null`, and `P04217` to `PTHR00000:SF4`
- **THEN** the page says 3 IDs, 2 with a PANTHER ID and 1 with none, shows the three rows in that order, and shows the job's API, engine and tool versions

#### Scenario: Still running

- **WHEN** the user opens the page of a running `refmap` job
- **THEN** the page shows no mappings table

### Requirement: refmap results a page at a time

The refmap results table SHALL show at most 100 rows at once, with controls to move between pages and a note of which rows are shown, so that a job of 100,000 mappings stays responsive. The page MUST NOT scroll sideways at mobile widths.

#### Scenario: Moving between pages

- **WHEN** a succeeded `refmap` job has 250 mappings and the user goes to page 3
- **THEN** the table shows rows 201 to 250

#### Scenario: The largest job

- **WHEN** a succeeded `refmap` job has 100,000 mappings and the user goes to the last page
- **THEN** the table shows rows 99,901 to 100,000, and the page does not scroll sideways

### Requirement: refmap mappings download

The refmap results SHALL offer every mapping as a tab-separated file, built in the browser: a header line `id` and `panther_id`, then one line per mapping in the order given, with an empty `panther_id` for `null`. The file MUST be named after the job.

#### Scenario: Downloading

- **WHEN** the user downloads the mappings of a job whose mappings are `P04217` to `PTHR00000:SF4` and `P38398` to `null`
- **THEN** the file is `panther-id-mapping-<job id>.tsv` and holds `"id\tpanther_id\nP04217\tPTHR00000:SF4\nP38398\t\n"`

#### Scenario: Every page

- **WHEN** a job has 150 mappings and the table shows its first page
- **THEN** the downloaded file has a line for each of the 150
