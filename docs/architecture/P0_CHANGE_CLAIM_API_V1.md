# P0 Change / Claim API v1

The versioned `p0-change-claim.v1` transport boundary exposes the existing Change/Variation/Notice/Claim application service.

It does not add scheduling, entitlement, pricing, EVM, resource/cost, or financial semantics.

- `create` requires project write permission, tenant/project scope, actor identity match, timezone-aware timestamp, expected revision, and an idempotency key.
- `get` requires project read permission and the same tenant/project scope.
- The API serializes the existing typed resource and evidence references without changing the persistence model.
- The internal `ChangeClaim` model retains its existing `1.0` persistence contract; `p0-change-claim.v1` is the transport contract.
