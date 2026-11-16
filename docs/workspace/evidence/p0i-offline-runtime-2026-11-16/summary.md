# P0-I offline runtime boundary — measured evidence

Date: 2026-11-16. Measured on merged main `ffc946ca` (P0-I code merged as `648cef68`; reference main before the branch was `a7735bb7`).
Engine: the single authoritative Shared Scheduling Core; no second scheduler
exists for offline execution.

## What was proven

1. An offline bundle (`construction-pm/offline-schedule-bundle/v1`) can be
   built from an immutable snapshot, its exact version-pinned calendar
   definitions (including base references and exception layers) and the
   deterministic calculation context, and serialized to one JSON artifact.
2. Executing that artifact in a fresh process produces the identical canonical
   `calculation_run_identity` as the online evaluator on the same snapshot.
3. The whole offline import + calculation path is network-free: the subprocess
   disables `socket.connect`, `connect_ex`, `create_connection` and
   `getaddrinfo` before importing any `construction_pm` module. A probe run
   confirms the guard is active (`OFFLINE_NETWORK_ACCESS_DENIED:create_connection`).
4. The runtime accepts no repository, transport, URL or credential, so there is
   no remote engine, calendar or snapshot dependency to reach.

## Parity measurements (`offline-parity.json`, 3 runs per size)

| Activities | Relationships | Online median | Offline median (separate process) | Bundle bytes | Run identity |
|---|---|---|---|---|---|
| 1,000 | 1,923 | 241.1 ms | 272.7 ms | 853,285 | `0c811c700798…` (equal) |
| 5,000 | 9,575 | 1,237.2 ms | 1,337.6 ms | 4,247,877 | `901b101d3500…` (equal) |

The offline median includes process start, bundle parse, snapshot
materialization and calculation; it is not a claim that offline is faster.

Network guard probe: `{"denied": "OFFLINE_NETWORK_ACCESS_DENIED:create_connection", "ok": true}`.

## Resolver hoist discovered by the boundary measurement

Building the bundle exposed an existing O(edges × activities) recomputation in
`resolve_relationship_lag_resolvers`: the snapshot-wide activity calendar map
was rebuilt once per relationship even though it does not depend on the
relationship. The map is now resolved once and passed in. Resolution values are
unchanged (`registry.resolve` is pure for a pinned reference), and the map is
only used to select the predecessor/successor calendar references.

`resolver-hoist-equivalence.json` compares the old and new implementations on
the same snapshots:

| Activities | Old median | New median | Speed-up | Canonical run identity |
|---|---|---|---|---|
| 200 | 252.0 ms | 49.3 ms | 5.11x | identical `7ba4b8a7…` |
| 1,000 | 5,247.5 ms | 243.2 ms | 21.58x | identical `0c811c70…` |

This is an exact-equivalence reduction of repeated *resolution* work only; it
does not remove or reorder any CPM step, validation, option, calendar rule,
relationship rule, float or leveling decision.

## Explicit boundary limits

- Resource leveling and resource-dependent placement need application-bound
  capacity inputs that are not part of a bundle yet. A snapshot that requests
  them is rejected with `OFFLINE_LEVELING_INPUT_REQUIRED` instead of being
  silently simplified. Online behavior is unchanged.
- The network guard is process-local and synchronous; it is intended for the
  dedicated offline calculation process, not for patching a live server.
- Mobile offline execution still requires a proven portable runtime for the
  Python engine; this slice does not claim mobile packaging parity.

## Not measured

Windows Desktop installer/supervision, mobile runtime/FFI/WASM packaging,
time-aware bundles beyond the unit parity tests, multi-project batches,
leveling bundles, and cross-version (older bundle schema) behaviour.

Files: `offline-parity.json`, `resolver-hoist-equivalence.json`,
`environment.json`. Unit coverage: `tests/scheduling/test_offline_schedule_runtime.py`
(12 tests) and the precomputed-calendar equivalence test in
`tests/scheduling/test_calendar_resolution.py`.
