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
- PostgreSQL persistence stores provider-neutral indexed text and document identity; it does not implement a search-engine SDK or OCR engine.
- Production search engines may implement the same adapter contract without becoming authoritative for document lifecycle or project-control calculations.

## Implementations

- InMemoryDocumentSearchAdapter is the deterministic contract/reference implementation for local verification.
- PostgresDocumentSearchAdapter provides production persistence and tenant/project/revision isolation; PostgreSQL LIKE matching is a reference query path, not a claim of full-text search-engine behavior.

## Runtime verification

The PostgreSQL integration suite verifies indexing, newer-revision replacement, stale-revision rejection, tenant/project scoping, current-revision removal, and empty post-removal results.

No P6, scheduling, Progress/EVM, Resource/Cost, or financial formulas are introduced.
