# Document Search Adapter Boundary

This stage defines the application boundary for indexing and querying document text without coupling the backend to a specific search engine.

## Rules

- Search entries are scoped by tenant and project.
- Every entry carries document revision and SHA-256 content identity.
- An older revision can never overwrite a newer indexed revision.
- Removal requires the current revision.
- Empty queries return no results.
- Search-engine-specific behavior remains behind the DocumentSearchAdapter protocol.
- OCR extraction is not performed by this boundary; an OCR provider can produce text for a later index operation.

The included in-memory adapter is a deterministic contract/reference implementation for tests and local verification, not a production search engine.
