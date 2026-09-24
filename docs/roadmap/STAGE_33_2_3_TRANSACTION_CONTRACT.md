# Stage 33.2.3 — Transaction Contract

- Clarified that the outermost transaction owner controls BEGIN/COMMIT/ROLLBACK.
- Nested repository transaction contexts participate in the same transaction and do not commit independently.
- Added regression coverage for nested success and nested failure rollback.
- Existing resource/assignment optimistic locking and persistence semantics remain unchanged.
