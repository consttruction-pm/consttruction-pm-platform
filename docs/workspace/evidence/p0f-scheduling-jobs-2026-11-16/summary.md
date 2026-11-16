# P0-F evidence — durable Scheduling Job lifecycle

Date: 2026-11-16
Reference: `9591d000` (main after P0-E)

## What was built

A lifecycle boundary around the single authoritative CUBI engine, in two
layers:

- `src/construction_pm/scheduling_job_lifecycle.py` — all rules: job identity,
  leases, retries, cancellation, result persistence, failure recovery and
  authorization-scoped single-flight de-duplication. It never calculates; the
  caller runs `construction_pm.scheduling` and persists the canonical hash.
- `src/construction_pm/postgres_scheduling_job_lifecycle.py` — the durable
  adapter. Every write is a revision compare-and-set, and a partial unique index
  enforces at most one QUEUED/LEASED job per authorization-scoped request key.
- `infra/scheduling_job_schema.sql` — portable baseline schema.

State machine: `QUEUED -> LEASED -> SUCCEEDED | FAILED | CANCELLED`, with
`LEASED -> QUEUED` on a retryable failure or an expired lease.

| Requirement | Implementation |
|---|---|
| Identity | Deterministic `job_id = sha256(tenant, project, dedup scope, request fingerprint, generation)`; `engine_version` and scheduling `calculation_identity` are stored on the job |
| Leases | Owner + token + expiry; only the token holder may renew, checkpoint, complete or fail; an expired lease is taken over only after an explicit expiry check |
| Retries | Retryable failure or lease expiry requeues until `max_attempts`, then FAILED with the last error |
| Cancellation | QUEUED cancels immediately; LEASED records the request and terminates at the next checkpoint, renewal, completion attempt or lease expiry, never publishing a result |
| Result persistence | One immutable result per job (engine identity, canonical output hash, payload); an identical replay is tolerated, a different one is rejected |
| Failure recovery | `recover_expired()` requeues, fails or cancels abandoned leases |
| Single-flight + authorization | The key includes an authorization-derived scope; `can_view` is re-checked before any job or result is returned, so two callers in different scopes never share or observe one another's run |

## Measured on PostgreSQL 14.24

Local cluster, `autocommit` connections over the Unix socket, schema created by
`initialize()`; the 200-cycle loop does submit → claim → complete per cycle.

| Metric | Value |
|---|---|
| Cycles | 200 |
| Median cycle | 0.506 ms |
| p95 cycle | 0.715 ms |
| Max cycle | 2.534 ms |
| Schema init | 0.834 ms |

Concurrent single-flight: 16 threads, each with its own connection, all calling
`submit` for the same authorization-scoped request at the same barrier.

| Metric | Value |
|---|---|
| Unique job ids | 1 |
| Jobs created | 1 |
| Errors | 0 |
| Wall time | 31.002 ms |

The partial unique index, not application timing, is what guarantees the single
active job; the 16 threads contend on the index and the losers re-read and
return the winner.

## Verification

- `tests/scheduling/test_scheduling_job_lifecycle.py` — 16 tests over the
  in-memory reference repository: single-flight, authorization scoping, claim /
  renew / stale token, completion and result immutability, engine identity
  mismatch, retryable and terminal failure, cooperative cancellation, expiry
  recovery (requeue, fail, cancel), new generation after a terminal job, 8
  concurrent submissions, and persistence of the real engine's canonical hash
  for a 50-activity fixture.
- `tests/test_scheduling_job_postgres.py` — 6 PostgreSQL tests including the
  partial unique index under a real second connection, a lost compare-and-set,
  takeover of an expired lease by another worker, and 6 concurrent submitting
  threads on separate connections. These ran locally against PostgreSQL 14.24
  and run in the `postgres` CI job.

## Not measured

- Multi-host or high-availability PostgreSQL: only a local single node exists.
- End-to-end HTTP admission and client polling: no HTTP surface was added in
  this slice, so none is claimed.
- Worker counts, queue waiting time and throughput: P0-G is not implemented.
