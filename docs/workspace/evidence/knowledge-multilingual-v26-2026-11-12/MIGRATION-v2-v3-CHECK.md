# Schema v2 → v3 identity migration on the real corpus copy

Date: 2026-11-12
Scope: local verification, SQLite copy of the measured evidence database.

The evidence database `cubi-knowledge-v26.sqlite3` (sha256 `ac3eee96…`, schema
version 2) was copied to `/tmp`, opened once through `SqliteKnowledgeStore`
(which migrates to schema version 3), and measured read-only afterwards.

| Check | Before | After |
| --- | --- | --- |
| Schema version | 2 | 3 |
| Cards | 1030 | 1030 |
| Topics | 1539 | 1539 |
| Translation records | 9 | 9 |
| Audit records | 513 | 513 |
| Orphan translations (no card) | — | 0 |
| Card ids in stable form | 0 of 1030 | 1030 of 1030 |
| Card ids in legacy form | 1030 of 1030 | 0 |

Further checks:

- Card content is unchanged: the sorted `(title, card_type, content_hash,
  publication_status)` multiset is identical before and after migration.
- Every migrated card id equals `card_id_for(source_id, topic_key)`
  (1030 of 1030). The 509 merged duplicate topics own no card, which is
  exactly the number of recorded `topic_merged` audits, so those ids are
  absent by design rather than lost.
- The four immutability triggers were recreated after the identity update:
  `knowledge_audit_no_update`, `knowledge_audit_no_delete`,
  `knowledge_card_event_no_update`, `knowledge_card_event_no_delete`.
- The production evidence database itself was **not** modified; it is still
  schema version 2 and is only ever opened read-only by
  `tools/knowledge_inventory.py`.

This is SQLite evidence. The PostgreSQL store has not been migrated or tested
in this environment (**BLOCKED_EXTERNAL**: no server, no driver).
