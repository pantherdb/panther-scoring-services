# Spec Delta

## ADDED Requirements

### Requirement: hmmscore form

The UI SHALL offer an HMM scoring form at `/hmmscore`, linked from the home page and from the HMM scoring tab. It MUST have one box for a protein sequence, as plain residues or FASTA with one header line, and an action that fills it with the legacy help page's example, human APOE, with no header.

#### Scenario: Open the form from the home page (hmmscore)

- **WHEN** the user opens `/` and follows the link to HMM scoring
- **THEN** the UI shows `/hmmscore`, with an empty sequence box

#### Scenario: Use the example (hmmscore)

- **WHEN** the user chooses to use an example on `/hmmscore`
- **THEN** the sequence box holds the 317 residues of human APOE that start `MKVLWAALLVTFLAGCQAKV`, in lines of 35 as the help page shows them

### Requirement: hmmscore form checks the input before sending

Before sending, the HMM scoring form SHALL check the sequence against `scoring-input`'s hmmscore rules, with the most residues the API's setting allows, 10,000; the API checks the server's own limit. A broken rule MUST be shown on the sequence field, without quoting the sequence, and no request MUST be sent. The form MUST NOT reject a sequence the rules accept.

#### Scenario: Empty hmmscore form

- **WHEN** the user submits the HMM scoring form with no sequence, or with only a FASTA header
- **THEN** the sequence field shows an error, and no request is sent

#### Scenario: Two sequences in the hmmscore form

- **WHEN** the user submits `">one\nMKV\n>two\nMKV"`
- **THEN** the sequence field says to submit one protein, and no request is sent

#### Scenario: Past the most residues in the hmmscore form

- **WHEN** the user submits a sequence of 10,001 residues
- **THEN** the sequence field says it's longer than 10,000 residues, and no request is sent

#### Scenario: A character hmmscan doesn't read, in the hmmscore form

- **WHEN** the user submits `MKV1L`, `MKV-L` or `MKV*L`
- **THEN** the sequence field says which characters a sequence may hold, without quoting it, and no request is sent

#### Scenario: A valid sequence is sent for hmmscore

- **WHEN** the user submits `">sp|P02649|APOE_HUMAN\nmkvl waal\n"`
- **THEN** no error is shown, and the request is sent with `service` `hmmscore` and the sequence as typed, which the API normalises

### Requirement: hmmscore server field errors shown on the sequence

When the API answers an HMM scoring request with 422, the form SHALL show each error whose `loc` names `sequence` on the sequence field, with the API's message, and any other error with the form. Editing the sequence MUST clear its server error.

#### Scenario: Past the server's residue limit

- **WHEN** the user submits a sequence of 5,001 residues and the API answers 422 with an error on `["body", "hmmscore", "input", "sequence"]` that names the server's limit of 5,000 residues
- **THEN** the sequence field shows that message, and the sequence is unchanged

#### Scenario: An hmmscore error on no field

- **WHEN** the API answers 422 with an error whose `loc` is `["body", "hmmscore", "input", "opType"]`
- **THEN** the form shows that error's message with the form

### Requirement: HMM scoring not yet available

When the API answers an HMM scoring request with 501, the form SHALL say that HMM scoring isn't available yet, in fixed text, keep the sequence, and stay at `/hmmscore`. When the API can't be reached, it MUST say so, as the other forms do; when it answers with any other error, it MUST say the job couldn't be started. No message MUST show a status code or build details, and the form MUST stay usable.

#### Scenario: The API answers 501 (hmmscore)

- **WHEN** the user submits a valid sequence and the API answers 501
- **THEN** the form says HMM scoring isn't available yet, the sequence is unchanged, the UI stays at `/hmmscore`, and the form can be submitted again

#### Scenario: The API answers 500 (hmmscore)

- **WHEN** the user submits a valid sequence and the API answers 500 with problem details
- **THEN** the form says the job couldn't be started, with no status code or build details

#### Scenario: The network fails (hmmscore)

- **WHEN** the user submits a valid sequence and the request fails with a network error
- **THEN** the form says the scoring service can't be reached, and keeps the sequence

### Requirement: Submitting an hmmscore request opens its job

When the API accepts an HMM scoring request with 202, the UI SHALL open `/jobs/{id}` for the new job. While the request is in flight, the submit action MUST be disabled.

#### Scenario: The API accepts the request (hmmscore)

- **WHEN** the user submits a valid sequence and the API answers 202 with an `hmmscore` job
- **THEN** the UI shows `/jobs/{id}` for that job, headed as HMM scoring

#### Scenario: While submitting the sequence

- **WHEN** the user has submitted a valid sequence and the API hasn't answered yet
- **THEN** the submit action is disabled

### Requirement: hmmscore results on the job page

When an `hmmscore` job has succeeded with a hit, the job page SHALL show the hit's PANTHER ID, linking to its page on pantherdb.org, its name, its E-value and its bit score, each exactly as the API gives it, and the alignment. With a `null` hit, it MUST say there were no hits to PANTHER for the sequence. The job's versions MUST be shown with it.

#### Scenario: A job with a hit

- **WHEN** the user opens the page of a succeeded `hmmscore` job whose hit is `PTHR00000:SF1`, named "MOCK FAMILY", with E-value `7e-131` and score `439.0`
- **THEN** the page shows `PTHR00000:SF1`, "MOCK FAMILY", `7e-131` and `439.0`, the alignment, and the job's API, engine and tool versions

#### Scenario: A job with no hit

- **WHEN** the user opens the page of a succeeded `hmmscore` job whose `hit` is `null`
- **THEN** the page says there were no hits to PANTHER for the sequence, and shows no alignment

#### Scenario: A running hmmscore job

- **WHEN** the user opens the page of a running `hmmscore` job
- **THEN** the page shows no hit and no alignment

### Requirement: hmmscore alignment as text

The job page SHALL show an `hmmscore` hit's alignment as monospaced text, exactly as the API gives it, with its line breaks and spaces kept and no line wrapped. A long line MUST scroll within the alignment's own box, so the page doesn't scroll sideways at mobile widths.

#### Scenario: Columns kept

- **WHEN** a hit's alignment has lines whose residues line up in columns
- **THEN** the page shows them lined up, each line unwrapped

#### Scenario: A long alignment on a phone

- **WHEN** the user opens the page of an `hmmscore` job whose alignment has lines of 200 characters, at mobile width
- **THEN** the alignment scrolls sideways within its box, and the page does not

## MODIFIED Requirements

### Requirement: Services that aren't available yet

Every service the API can't score yet SHALL be marked "coming soon", in its tab and on the home page: today HMM scoring and TreeGrafter. HMM scoring's tab MUST still open its form. TreeGrafter MUST open a page that says what the service will do, that it's coming soon, and links home.

#### Scenario: The marks

- **WHEN** the user opens any page
- **THEN** the HMM scoring and TreeGrafter tabs say they're coming soon, and cSNP scoring and ID mapping don't

#### Scenario: A service without a form

- **WHEN** the user follows the TreeGrafter tab
- **THEN** a page says TreeGrafter is coming soon, says what it will do, and links home

#### Scenario: HMM scoring's form while coming soon

- **WHEN** the user follows the HMM scoring tab
- **THEN** the HMM scoring form is shown, and HMM scoring is marked as current

### Requirement: The home page shows every service

The home page SHALL show the four services, in the tabs' order, each with what it does and the same "coming soon" mark. A service with a form MUST link to it.

#### Scenario: The four services

- **WHEN** the user opens `/`
- **THEN** the page shows cSNP scoring, ID mapping, HMM scoring and TreeGrafter, with links to the cSNP, refmap and HMM scoring forms, and the last two marked coming soon

### Requirement: The next step from a job's page

A job's page SHALL offer the next step, whatever the job's status: for a `csnp` job, a link to an empty cSNP form; for a `refmap` job, a link to an empty refmap form; for an `hmmscore` job, a link to an empty HMM scoring form; for the tools check, a link home.

#### Scenario: A cSNP job

- **WHEN** the user opens the page of a `csnp` job and follows "New cSNP search"
- **THEN** the cSNP form is shown, empty

#### Scenario: An hmmscore job's next step

- **WHEN** the user opens the page of an `hmmscore` job and follows its link to a new HMM scoring search
- **THEN** the HMM scoring form is shown, empty

#### Scenario: The tools check

- **WHEN** the user opens the page of a tools job
- **THEN** the page links home
