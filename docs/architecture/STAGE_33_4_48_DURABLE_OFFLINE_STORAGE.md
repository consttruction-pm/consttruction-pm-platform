# Stage 33.4.48 — Durable Offline Storage

## Purpose

Persist approved offline mutations across application restart without embedding business calculations in the storage layer.

## Contract

The storage boundary exposes:

- append
- pending
- acknowledge

The stored mutation preserves tenant/project identity, expected revision, mutation identity, idempotency key, operation and opaque payload.

## Portability

A framework-neutral storage protocol is authoritative. A portable JSON-file adapter is supplied as the initial reference implementation for Desktop/local environments and tests. Platform-specific databases may later implement the same protocol.

## Atomicity

The JSON adapter writes to a temporary file and replaces the target file after serialization, reducing the risk of partial writes.

## Authority

Storage never recalculates Scheduling/P6, Calendar, Progress/EVM, Resource/Cost or financial semantics.

## Remaining synchronization work

Retry policy, network transport, server acknowledgement, conflict handling, and end-to-end synchronization remain subsequent stages.
