# Document OCR Adapter Boundary

This stage defines a provider-neutral OCR extraction boundary for project documents.

- Requests are tenant/project/document/revision scoped.
- The opaque storage reference identifies the source document without coupling core code to a storage provider.
- OCR results carry the source revision and provider identity.
- OCR engines and credentials remain outside Shared Core and the persistence layer.
- The reference adapter exists only for deterministic tests and local contract verification.
- OCR output can be passed to the document search indexing boundary as a separate application step.
