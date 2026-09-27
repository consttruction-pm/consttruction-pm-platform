# Document Approval Lifecycle Boundary

The document persistence boundary now exposes an explicit lifecycle transition operation.

Allowed transitions:
- draft -> submitted
- submitted -> approved
- submitted -> rejected
- rejected -> submitted
- approved -> superseded

Every transition:
- requires the expected current revision;
- records the acting user and timestamp in append-only audit history;
- increments the document revision;
- changes status only, preserving the persisted document payload;
- rejects invalid transitions without mutation.

Approval policy/role authorization remains an application-layer concern. OCR, search indexing and storage-provider behavior remain separate adapters.
