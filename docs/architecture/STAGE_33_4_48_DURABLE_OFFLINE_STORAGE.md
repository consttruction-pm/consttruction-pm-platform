# SQLite Offline Mutation Queue Transaction Ownership Fix

**Parent:** #1680 — durable local project database and outbox.
**Issue:** #1685.

The SQLite queue may be constructed over a connection that is already inside a caller-owned transaction. Schema initialization must not commit that transaction. The constructor now records transaction ownership before creating the queue table and commits only when no outer transaction existed.

This preserves the host's ability to place local domain writes and the outbox append under one `SQLiteTransactionManager.transaction()` boundary. A rollback must undo both the domain write and the queued mutation. Queue construction itself must not commit unrelated caller work.

This is a storage-ownership fix only. It does not change mutation identity, payload, retry, idempotency, sync ordering or calculation semantics.
