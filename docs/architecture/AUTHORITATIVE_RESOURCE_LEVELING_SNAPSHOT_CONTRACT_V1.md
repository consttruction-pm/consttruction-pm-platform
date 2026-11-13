# Authoritative Resource-Leveling Snapshot Contract — Proposal v1

Status: **Design proposal; not yet an accepted product contract**

Date: 2026-10-18

Related tracking: issues #1462 and #1468; design gate #1447; reconciliation parent #680.

## 1. Problem statement

The current `ScheduleInputSnapshot` validates its canonical payload hash and binds the tenant, project, project revision, snapshot ID, and calculation identity. The schedule evaluator accepts an optional `SchedulerLevelingInput` and fails closed when resource leveling is requested without one. The P6 resource-leveling read adapter can map versioned resource read DTOs to the scheduler boundary.

The inspected production query path does not supply that input. Wiring a live resource read into the query provider would be unsafe unless the resource records are proven to belong to the exact same immutable schedule input revision.

## 2. Proposed contract choice

**Proposal:** use a separately persisted, immutable companion record for resource-leveling input, bound to the exact schedule snapshot. This keeps the current canonical schedule payload contract stable while making the additional calculation input explicit. This is a proposal for review, not a claim that this persistence model already exists.

The companion record must include at least:

- contract/schema version;
- `snapshot_id` and `snapshot_hash`;
- `tenant_id`, `project_id`, and `project_revision`;
- deterministic canonical payload for the fully mapped `SchedulerLevelingInput`;
- SHA-256 of that canonical payload;
- stable input/composition identity and timezone-aware creation timestamp.

The canonical payload must include every value that can affect leveling results: resource capacities/calendar slices, resource demand by activity and period, and all scheduler-leveling options/priority semantics that are not already covered by the schedule snapshot. Preserve exact decimal values; do not round through binary floating point.

## 3. Composition and persistence boundary

A single application-level snapshot composer should:

1. Read authoritative activity, relationship, calendar, resource assignment, period-value, and resource-calendar data for one tenant/project/revision.
2. Reject any cross-scope, cross-revision, missing-link, unsupported-contract-version, or inconsistent source state.
3. Materialize the authoritative schedule input and the typed resource-leveling input from that same read boundary.
4. Persist the schedule snapshot and companion leveling record atomically where the backing store supports a shared transaction. If atomic multi-record persistence is unavailable, use a durable publication protocol so neither record can be treated as ready until both are committed and mutually verified.
5. Return a published snapshot identity only after both records can be freshly read and validated.

Do not silently infer absent ActivityMaster fields, invent resource calendars, or fill unsupported scheduling semantics with defaults. Any missing data required by the requested mode must fail closed with a stable error code.

## 4. Query-time rules

The production query provider should load only the immutable companion by the already selected snapshot identity, then verify:

- exact snapshot ID and snapshot hash match;
- tenant, project, and project revision match;
- payload hash and schema version are valid;
- referenced activity IDs and assignment-period links are consistent;
- the input contains all required scheduler fields and no invalid negative capacity/demand values.

Only after validation should it pass the typed input to `evaluate_schedule_snapshot(..., leveling_input=...)`. The query calculation must not read mutable resource repositories to assemble or patch the input during evaluation.

If a companion is absent, stale, mismatched, or invalid, fail closed. Do not fall back to a live read, an empty resource set, or a plain-scheduling result when leveling was requested.

## 5. Acceptance tests required before implementation is considered complete

1. Persist real ActivityMaster and resource assignment/period/calendar fixtures, compose both inputs, commit, and construct a new provider instance.
2. Fresh-read and execute a resource-leveling schedule; assert the expected schedule result and final capacity checks.
3. Preserve non-default Decimal demand and capacity values through write, canonicalization, persistence, fresh-read, adapter mapping, and calculation.
4. Reject a companion with a changed payload but unchanged hash.
5. Reject snapshot ID/hash mismatch, tenant mismatch, project mismatch, project-revision mismatch, and activity/assignment/period link mismatch.
6. Prove a missing companion fails closed and does not query mutable resource repositories at calculation time.
7. Prove a failed second write cannot expose a published snapshot with only one of its two inputs.
8. Exercise both forward and backward leveling plus relevant schedule constraints; final capacity and constraint validation must remain enabled.
9. Run focused tests and full CI on the exact PR head; record exact SHA and run links.

## 6. Existing gaps that this proposal does not claim to solve

- The inspected `ActivityMaster` contract does not currently expose every scheduling field potentially required to compose a complete authoritative schedule input. Field-level reconciliation is a prerequisite; do not add guessed fields.
- The production composition test currently constructs `AuthoritativeScheduleInput` directly, so it does not prove the persisted ActivityMaster-to-snapshot path.
- The current main branch has recorded failures in shared-batch resource capacity validation and backward-leveling `START_NO_LATER_THAN` constraint handling. These are separate correctness defects and must not be hidden by weakening validation.
- This proposal is documentation only. It does not represent a code implementation, runtime test, or CI result.

## 7. Review decision requested

Reviewers should confirm or reject the companion-record proposal against the existing persistence and transaction boundaries before code changes begin. If the project instead chooses to extend `ScheduleInputSnapshot` itself, update this contract and its acceptance tests before wiring production calculation.
