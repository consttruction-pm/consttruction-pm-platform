# Backend Idempotency Revision Fingerprint Hardening

Date: 2026-09-24

The idempotency fingerprint for Resource and ResourceAssignment mutations includes the optional `expected_revision` precondition. Reusing the same idempotency key with a different optimistic-locking precondition is therefore treated as a different mutation instead of replaying the prior result.

No Scheduling/P6 or Progress/EVM semantics are changed.

Regression coverage: `tests/resources/test_idempotency_revision_fingerprint.py`.
