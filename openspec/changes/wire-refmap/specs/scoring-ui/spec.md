# Spec Delta

## ADDED Requirements

### Requirement: refmap organism list unavailable

While the organism list loads, the refmap form SHALL say so in the organism field. If the list can't be loaded, the form MUST stay usable: it MUST offer a box for an organism code instead, keeping the organism chosen so far, say in fixed text that the list couldn't be loaded, with no status code or build details, and offer to load the list again. When the list then loads, the form MUST offer the selector, keeping the organism if it is in the list.

#### Scenario: Loading the organisms

- **WHEN** the user opens `/refmap` and the organism list hasn't loaded yet
- **THEN** the organism field says the organisms are loading, and the IDs box can be filled

#### Scenario: The organism list fails to load

- **WHEN** the user opens `/refmap` and the API answers the organism list with an error
- **THEN** the organism field is an empty box, the form says the organism list couldn't be loaded, shows no status code or build details, and offers to try again

#### Scenario: Submitting without the organism list

- **WHEN** the organism list couldn't be loaded, and the user types the organism `ENDPU` and submits valid IDs
- **THEN** the request is sent with the organism `ENDPU`

#### Scenario: Trying the organism list again

- **WHEN** the organism list couldn't be loaded, the user typed `ENDPU`, and chooses to try again, and the list now loads
- **THEN** the organism field is the selector, showing "Endocarpon pusillum (ENDPU)"

### Requirement: refmap submit failures

When the API can't be reached, the refmap form SHALL say so, as the cSNP form does; when it answers with any other error than a 422 validation problem, it MUST say the job couldn't be started. Neither message MUST show a status code or build details. The form MUST keep the user's input, stay at `/refmap`, and stay usable.

#### Scenario: The API answers 500 (refmap)

- **WHEN** the user submits a valid input and the API answers 500 with problem details
- **THEN** the form says the job couldn't be started, with no status code or build details, and both fields are unchanged

#### Scenario: The network fails (refmap)

- **WHEN** the user submits a valid input and the request fails with a network error
- **THEN** the form says the scoring service can't be reached, and keeps the input

## MODIFIED Requirements

### Requirement: refmap form

The UI SHALL offer a refmap form at `/refmap`, linked from the home page. It MUST have a box for protein IDs, an organism selector that starts empty, and a count of the IDs that will be sent. The selector MUST offer the organisms the API lists for refmap, each shown by its name and its code, such as "Endocarpon pusillum (ENDPU)", and none it doesn't list. Typing part of a name or of a code MUST narrow the options to the organisms that match, in any letter case. The selector MUST have a label, MUST be usable with the keyboard alone, and MUST stay responsive with every organism listed. Whatever the selector shows, the request MUST send the organism's code. An action MUST fill both fields with an example from the mapping data's own test list: six `ENDPU` IDs and the organism `ENDPU`.

#### Scenario: Open the form from the home page (refmap)

- **WHEN** the user opens `/` and follows the link to protein ID mapping
- **THEN** the UI shows `/refmap`, with an empty IDs box, no organism chosen, and no IDs counted

#### Scenario: Use the example (refmap)

- **WHEN** the user chooses to use an example on `/refmap`
- **THEN** the IDs box holds `U1G4Q5`, `U1GCA1`, `U1HRR6`, `U1GLV9`, `U1GJ40` and `U1HQ27`, one per line, the organism is "Endocarpon pusillum (ENDPU)", and the form says 6 IDs will be sent

#### Scenario: The organisms the API lists

- **WHEN** the user opens the organism selector
- **THEN** it offers each organism the API lists, by name and code, and no other

#### Scenario: Search an organism by name

- **WHEN** the user types `pusill` in the organism selector and chooses "Endocarpon pusillum (ENDPU)"
- **THEN** the organism is "Endocarpon pusillum (ENDPU)"

#### Scenario: Search an organism by code

- **WHEN** the user types `eco57` in the organism selector
- **THEN** the selector offers the organism whose code is `ECO57`, and no organism whose name or code doesn't contain `eco57`

#### Scenario: The organism's code is sent

- **WHEN** the user chooses "Endocarpon pusillum (ENDPU)" and submits valid IDs
- **THEN** the request's `organism` is `ENDPU`

### Requirement: refmap form checks the input before sending

Before sending, the refmap form SHALL check the input against `scoring-input`'s refmap rules: the organism and the IDs as split. Once the organism list has loaded, the organism MUST be one of its codes; before then, or when the list couldn't be loaded, the form checks the trimmed organism's shape only, and the API checks the rest. Each broken rule MUST be shown on its field, and no request MUST be sent while any is broken. An ID that breaks the rules MUST be named by its place in the list, its line and as typed, at most ten, then a count. The form MUST NOT reject an input the rules accept.

#### Scenario: Empty form (refmap)

- **WHEN** the user submits the form with no IDs and no organism
- **THEN** the IDs and organism fields each show an error, and no request is sent

#### Scenario: Too many IDs

- **WHEN** the user submits 100,001 IDs
- **THEN** the IDs field says at most 100,000 can be sent, and no request is sent

#### Scenario: IDs that aren't IDs

- **WHEN** the user submits the IDs `"P04217\nP0é4217\nP04217 <65 characters>"`
- **THEN** the IDs field names ID 2 on line 2, `P0é4217`, and ID 4 on line 3, the start of the long one, and no request is sent

#### Scenario: Not an organism code

- **WHEN** the organism list couldn't be loaded, and the user submits the organism `endpu`, `ENDOCARPON` or `../x`
- **THEN** the organism field shows an error that doesn't quote it, and no request is sent

#### Scenario: An organism not in the list

- **WHEN** the organism list couldn't be loaded, the user types the organism `HUMAN`, the list then loads, and the user submits
- **THEN** the organism field shows an error asking for an organism from the list, and no request is sent

#### Scenario: A valid input is sent (refmap)

- **WHEN** the user submits 100,000 IDs of up to 64 printable ASCII characters, in any case, and the organism "Endocarpon pusillum (ENDPU)"
- **THEN** no field shows an error, and the request is sent with those IDs and `ENDPU`

#### Scenario: A typed organism is trimmed

- **WHEN** the organism list couldn't be loaded, and the user submits valid IDs and the organism ` ENDPU `
- **THEN** the request is sent with `ENDPU`

### Requirement: refmap results on the job page

When a `refmap` job has succeeded, the job page SHALL say which organism the IDs were mapped against, by its name and code when the organism list has loaded and by its code otherwise, how many IDs it has, how many have a PANTHER ID and how many have none, and show a table with one row per mapping, in the order given: its place counted from 1, the ID, and the PANTHER ID exactly as the API gives it, or "No PANTHER ID" for `null`. The job's versions MUST be shown with it.

#### Scenario: A mapped job

- **WHEN** the user opens the page of a succeeded `refmap` job for `ENDPU` whose mappings are `U1G4Q5` to `PTHR11360:SF130`, `U1HQ27` to `null`, and `U1G4Q5` to `PTHR11360:SF130`
- **THEN** the page says the IDs were mapped against "Endocarpon pusillum (ENDPU)", says 3 IDs, 2 with a PANTHER ID and 1 with none, shows the three rows in that order, and shows the job's API, engine and tool versions, and its refmap data as PANTHER 19

#### Scenario: The organism without the list

- **WHEN** the user opens the page of a succeeded `refmap` job for `ENDPU` and the organism list can't be loaded
- **THEN** the page says the IDs were mapped against `ENDPU`, and shows the mappings

#### Scenario: Still running

- **WHEN** the user opens the page of a running `refmap` job
- **THEN** the page shows no mappings table

### Requirement: Services that aren't available yet

Every service the API can't score yet SHALL be marked "coming soon", in its tab and on the home page: today HMM scoring and TreeGrafter. HMM scoring and TreeGrafter MUST each open a page that says what the service will do, that it's coming soon, and links home.

#### Scenario: The marks

- **WHEN** the user opens any page
- **THEN** the HMM scoring and TreeGrafter tabs say they're coming soon, and cSNP scoring and ID mapping don't

#### Scenario: A service without a form

- **WHEN** the user follows the HMM scoring tab
- **THEN** a page says HMM scoring is coming soon, says what it will do, and links home

### Requirement: The home page shows every service

The home page SHALL show the four services, in the tabs' order, each with what it does and the same "coming soon" mark. A service with a form MUST link to it.

#### Scenario: The four services

- **WHEN** the user opens `/`
- **THEN** the page shows cSNP scoring, ID mapping, HMM scoring and TreeGrafter, with links to the cSNP and refmap forms, and the last two marked coming soon

## REMOVED Requirements

### Requirement: refmap mapping not yet available

**Reason**: The API maps IDs, so it no longer answers a valid `refmap` request with `501`, and the form has no "not available yet" message to show.

**Migration**: The unreachable and other-error messages move to "refmap submit failures". An unexpected `501` gets the "couldn't be started" message, as any other error does.
