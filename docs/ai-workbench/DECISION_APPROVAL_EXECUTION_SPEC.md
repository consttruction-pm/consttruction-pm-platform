# Decision & Approval Execution — Specification

Status: **PARTIAL**. Enterprise approvals are wired. There is no Engineering
proposal store bound to a scenario revision, no exact-version approval and no
execution contract with reauthorization, atomic apply, audit and fresh read.

## Proposal inbox

Columns: proposal id, project, requester, type, base revision, scenario, impact,
risk, status, created, due date. Filters by project/status/type/requester/due
window. A proposal always points to one immutable scenario run and one base
revision.

## Proposal detail

1. **Summary** — objective, assumptions, constraints, evidence, limitations.
2. **Before / After** — exact changes with old/new values, selected-change
   granularity, and links to the affected Gantt/grid records.
3. **Validation & Impact** — schedule/cost/resource/risk deltas, conflicts,
   stale-source checks and permission result.
4. **Decision** — approve exact proposal, reject with reason, request changes,
   choose another scenario, select individual changes, defer/delegate where
   policy permits.

## Decision binding

- Approval binds to `proposal_id + proposal_version + base_revision`.
- Approving one scenario never approves later edits or a future version.
- Partial selection is recorded as its own change set.

## Execution sequence

1. Re-authorize the actor.
2. Re-read the source revision and compare with the proposal base.
3. Re-run validation and conflict detection.
4. Apply only the approved change set through the canonical project service,
   atomically where supported.
5. Append an audit record with actor, time, reason, execution identity and
   rollback/compensation availability.
6. Fresh-read the project and compare with the proposal.
7. Show the execution result; enable **Open in Engineering**.

If the revision changed: stop, do not auto-merge, require re-planning. If
execution fails: expose `PARTIAL_FAILURE`; never hide a partial write. Rollback
only through a real service capability.

## Required contracts

| Contract | State |
|---|---|
| proposal entity + immutable versions | absent |
| scenario-run reference | absent |
| approval decision store for Engineering | absent |
| execution + audit + read-back | absent |
| Enterprise approvals | present, different scope |

## Acceptance

No material change executes without an explicit approval of the exact proposal
version, a successful reauthorization/revision check, an audit record and a
verified fresh read.
