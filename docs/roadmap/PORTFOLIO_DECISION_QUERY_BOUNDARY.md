# Stage 34.2.20 — Portfolio Decision Query Boundary

This boundary exposes authoritative Portfolio Decision lifecycle/read metadata.

Every read preserves tenant, portfolio, project, revision, actor and authorization context, plus lifecycle and append-only audit revision metadata. Cross-domain references are opaque identifiers and are never recalculated by the API.

The repository is tenant/portfolio scoped and deterministic. Empty queries return an empty tuple; not-found behavior is therefore explicit and non-exceptional for collection reads. Transaction and idempotency behavior remains owned by the application layer and authoritative persistence implementation.