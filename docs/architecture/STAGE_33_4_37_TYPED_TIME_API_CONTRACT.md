# Stage 33.4.37 — Typed Time-Aware API Contract Regression

Date: 2026-09-24

Backend-owned completion of the typed API boundary for the existing Shared Core time-scheduling contract.

## Scope

- versioned API payload 1.0;
- calculation context with explicit schedule mode and project start;
- typed activity duration values and units;
- FS/SS/FF/SF relationships with signed lag/lead;
- datetime constraint DTOs using the six established Shared Core constraint types;
- canonical transport strings are preserved; no client-side scheduling formula is introduced.

The API layer validates and serializes. Scheduling semantics remain authoritative in the Shared Scheduling Core.

Web, Desktop and Mobile consume the same DTO shape. Existing date-based APIs are not changed by this substage.

Runtime CI execution remains unverified.
