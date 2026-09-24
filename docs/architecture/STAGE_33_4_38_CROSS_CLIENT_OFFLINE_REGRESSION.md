# Stage 33.4.38 — Cross-Client Offline Regression Pack

Date: 2026-09-24

This backend regression pack verifies that Web, Desktop and Mobile can consume
the same typed time-scheduling API payload and that offline mutation persistence
preserves ProjectContext, expected revision and mutation identity.

The tests intentionally do not execute or reimplement scheduling formulas.
Authoritative calculation remains in the Shared Scheduling Core.

Coverage:
- identical API DTO produced for all three client integration paths;
- InMemory and SQLite queue round-trip;
- tenant/company/project context preservation;
- expected revision preservation;
- retry attempt metadata does not alter idempotency identity.

Runtime CI execution remains unverified.
