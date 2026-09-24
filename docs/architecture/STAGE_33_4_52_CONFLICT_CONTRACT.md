# Stage 33.4.52 — Conflict Resolution Contract

## Purpose

Make synchronization conflicts semantically identical across Web, Desktop and Mobile while allowing each client to present them in its own UI.

## Required semantics

A conflict preserves:

- stable error_code
- expected_revision
- optional actual_revision
- available_actions
- opaque details

The reference stale-revision actions are:

- discard
- refresh_and_retry
- defer

These are action semantics, not UI labels. Clients may localize or render them differently.

## Client boundary

Clients present the conflict and available actions. They do not silently alter the expected revision, merge business values, or recalculate Scheduling/P6, Calendar, Progress/EVM, Resource/Cost or financial semantics.

## Resolution authority

A refresh/retry operation obtains authoritative current project state from the Application/API layer. Any business merge or recalculation remains server/Shared Core controlled.

## Scope

This stage establishes the shared conflict contract and presentation model. Automatic business merges, durable conflict history and end-to-end conflict UX remain subsequent stages.
