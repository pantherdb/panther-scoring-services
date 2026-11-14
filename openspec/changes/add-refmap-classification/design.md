# Design

## Context

The website needs an organism's whole classification file as its reference list (proposal.md). The engine already pins those files (`refmap/19/panther_classification/<code>`, checked by sha256 against the release) and reads them for jobs (`read_classification`). The first version built each response per request; the engine developer's review of #73 found that holds up to about 106 MB per request with nothing limiting how many run at once, imports engine internals, and copies the engine's line parsing. This design answers those points. Nothing in `docs/design/` changes.

## Decisions

### 1. The shape is `RefmapResult`, one mapping per line

The body has the fields of a `refmap` job's result, so a client that reads one reads the other, and the schema reuses the model, whose description now covers both. A mapping per line, not per distinct ID, so the file is rebuilt exactly; the website's `parseIdFamId` reads lines as before. That differs from a job for a repeated ID: a job gives the last line's value each time, as `map_panther.pl`'s hash did, and this gives each line's. The published files repeat no ID, so today the two agree. **Rejected:** the file as `text/plain` (the website asked for JSON, and the shape is the API's own); a map from ID to PANTHER ID (loses order and repeats).

### 2. One reader in the engine, exported

`classification_lines(path)` yields each line's ID and value with `map_panther.pl`'s rules (lines end at `\n`, the value is the text after the first tab up to the next, Latin-1), reading a line at a time. `read_classification` keeps the wanted IDs' last values from it; `classification_mappings(code)` yields every line as an `IdMapping`, after checking the code and the file. So a change to how a line is read, such as `REFMAP-3`'s `\r`, reaches jobs and the endpoint together. The API imports only what `panther_engine.refmap.__all__` exports: `classification_json_file`, `check_classification_json` and, in tests, `classification_mappings` (api/CLAUDE.md, "The Engine").

### 3. A 404 for a code not listed, checked before the path

The code is a path segment, so an unlisted one is a missing resource, not invalid input. It must be in `ORGANISM_CODES` before `classification_json_file` is called, so `..`, an encoded `/` or another file can't be named; membership in the engine's set is the only check, so there's one source of truth for the codes. The schema still carries the pattern and length, and documents the 404's problem; the operation is marked `NO_VALIDATION_PROBLEM`, so no impossible 422 is listed.

### 4. Built ahead of time, sent from disk

The data changes only with a new release, so each organism's response is built once, by `panther-engine refmap data build-json`, as gzipped JSON at `refmap/19/classification_json/<code>.json.gz`: 1,533 files, 176 MB, about a minute (ARAVE 1.5 MB, ENDPU 66 KB). The build streams a batch of 10,000 mappings at a time into gzip, writes beside the target and moves it into place, with no name or time in the gzip header, so the same file gives the same bytes. It isn't part of `fetch`: the data folder is read-only to the API, and the team builds it where the data is, such as the HPC system, and copies the folder.

The route sends the file a piece at a time (64 KiB): as it is, with `Content-Encoding: gzip` and its length, when `Accept-Encoding` accepts gzip; decompressed as it's sent otherwise, such as to the website's Java client. Nothing is built or kept in memory, and the CPU per request is a file read or a decompression. That's a property of the design, not a requirement, since no test can show the absence of a copy; the spec requires what a client can see: the built file's bytes, the encoding and the headers (review of #73). **Rejected:** building per request with a cap on how many run at once (the review's fallback: the peak per request stays about 106 MB); building the JSON in the API at startup (the data folder is read-only, and it would hold every response in memory or need a writable folder).

### 5. No cache headers

Nothing tells a client it may keep a copy: no `Cache-Control`, no `ETag` or `Last-Modified` (the response is streamed, not a `FileResponse`, which would add both). The team's decision: the website fetches it once per analysis and doesn't send conditional requests. `Vary: Accept-Encoding` is sent, since the body depends on it.

### 6. A missing file is logged, not raised

Without the file, or without `PANTHER_DATA_DIR`, the route answers the generic 500 itself and logs the cause at most once in ten minutes, as a job's unexpected error is (`_RecentErrors`), so a client calling repeatedly against a server without the files can't flood the log. At startup, once the refmap data is in place, `check_classification_json` logs how many files are missing; without the refmap data, its line would only repeat refmap's.
