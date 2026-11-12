# Design

## Context

The website needs an organism's whole classification file as its reference list (proposal.md). The engine already pins those files (`refmap/19/panther_classification/<code>`, checked by sha256 against the release) and reads them for jobs (`read_classification`). Nothing in `docs/design/` changes.

## Decisions

### 1. The shape is `RefmapResult`

The body is the result of a `refmap` job that sent every ID in the file, so a client that reads one reads the other, and the schema reuses the model. A mapping per line, not per distinct ID, so the file is rebuilt exactly; the website's `parseIdFamId` reads lines as before. **Rejected:** the file as `text/plain` (the website asked for JSON, and the shape is the API's own); a map from ID to PANTHER ID (loses order and repeats).

### 2. Read as a job reads, without changing the engine

`classification_json` reads the file with the engine's `classification_file`, `ENCODING` and `panther_id_of`, and splits lines and fields as `read_classification` does. `read_classification` keeps only wanted IDs and the last line of each, so it can't serve here; a shared engine reader is left for the engine developer to decide.

### 3. A 404 for a code not listed, checked before the path

The code is a path segment, so an unlisted one is a missing resource, not invalid input. It must match the species code pattern and be in `ORGANISM_CODES` before `classification_file` is called, so `..`, an encoded `/` or another file can't be named. The schema still carries the pattern and length.

### 4. Built per request, off the event loop, as bytes

The file is read and serialised with `pydantic_core.to_json` from plain dicts, not models (the review of #64 measured models at about six times the cost), in `run_in_threadpool`. Nothing is kept, in the API or by a cache header: ABSGL's 14,825 mappings take about 35 ms, and the response is freed once sent. **Rejected:** the organism list's hour-long `Cache-Control`, so no copy outlives the request. A missing file raises the engine's `MissingDataError`, which the API's handler turns into the generic 500.
