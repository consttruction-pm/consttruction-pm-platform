# P0 — Shared Scheduling Core Performance & Adaptive Execution Feasibility

**Priority:** P0 — highest CUBI Engineering priority  
**Tracking:** [Issue #1992](https://github.com/consttruction-pm/consttruction-pm-platform/issues/1992)  
**Assessment date:** 2026-11-16  
**Repository:** `consttruction-pm/consttruction-pm-platform`  
**Reviewed baseline:** `main` at `9d496a219dd39250ff220052d62111b6cdcb958c`  
**Assessment type:** repository source review, architecture feasibility and official Version 26 HTML Help review  
**Implementation status:** No production-code changes made by this assessment  
**Performance benchmark status:** Not measured in this assessment; runtime checkout was unavailable in the assessment environment. A reproducible benchmark phase is mandatory before claiming performance gains.

---

## 1. Priority and product decision

This is a **P0 workstream** and the highest-priority Engineering activity. Scheduling Core optimization must be planned and executed before other Engineering enhancements that modify, extend, or depend on Scheduling, Calendars, Activity dates, Relationships, Float, Resource Loading or Resource Leveling.

The purpose is not to reduce calculation scope or simplify the product. The purpose is to make the existing authoritative calculation engine faster and capable of using available hardware, while preserving every currently supported capability and all applicable P6 Professional Version 26 semantics.

Unrelated workstreams may continue only where they do not change, destabilize or introduce dependencies into the Scheduling Core P0 work.

### Governing architecture direction

1. Keep one canonical, versioned CUBI Calculation Engine. Do not fork calculation logic into separate cloud, desktop, mobile or worker implementations.
2. Run multiple isolated execution instances of that same engine when useful. Worker count is a runtime deployment parameter, not a reason to copy or branch the engine source.
3. Make process-level concurrency for independent immutable schedule jobs the first parallel-execution target.
4. Evaluate intra-project parallelism separately and only for operations whose dependencies and deterministic result equivalence are proven.
5. Adapt worker capacity to resources actually available to the process/container/host, including CPU quotas, affinity and RAM. Do not equate the host's advertised logical CPU count with the capacity available to CUBI.
6. Do not commit to fixed mappings such as “four vCPU means three workers” or “32 vCPU means 28 workers.” Derive those limits from measured per-job CPU and memory use, other service reservations and load.
7. Support Cloud, Local Server and Desktop execution through environment-specific supervisors/adapters around the same Engine.
8. Preserve approved offline calculation semantics for Desktop and Mobile. A runtime/packaging feasibility gate is required; do not assume a cloud ProcessPool can be reused unchanged on a mobile device.

## 2. Non-negotiable calculation and parity boundary

The normative desktop parity source for applicable scheduling behavior is **Oracle Primavera P6 Professional Version 26 English HTML Help**. Do not replace it with P6 EPPM, Primavera Cloud, a previous P6 release, or a simplified generic CPM interpretation.

Official Version 26 HTML entry points reviewed:

- [P6 Professional Version 26 Help table of contents](https://docs.oracle.com/cd/G48902_01/client_help/en_US/toc.htm)
- [P6 Professional Version 26 User Guide table of contents](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/toc.htm)
- [P6 Professional Version 26 Web User Guide](https://docs.oracle.com/en/industries/construction-engineering/primavera-p6-professional/26/pro-user/index.html)
- [Schedule a project](https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedule_a_project.htm)
- [Scheduling Projects](https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedulingprojects.htm)
- [Schedule Options dialog box](https://docs.oracle.com/cd/G48902_01/client_help/en_US/schedule_options_dialog_box.htm)
- [Choose a calendar for relationship lag](https://docs.oracle.com/cd/G48902_01/client_help/en_US/choose_a_calendar_for_relationship_lag.htm)
- [Leveling resources](https://docs.oracle.com/cd/G48902_01/English/User_Guides/p6_pro_user/leveling_resources.htm)
- [Analyze the schedule using multiple critical float paths](https://docs.oracle.com/cd/G48902_01/client_help/en_US/analyzing_the_schedule_using_multiple_critical_float_paths.htm)

Also use the repository's existing source index: `docs/workspace/reference/oracle-p6-reference-index.md`.

### Version 26 behaviors that optimization must not weaken

The characterization and regression suite must retain, where represented by the current Engine:

- Forward and Backward Pass and their relationship-feasibility checks;
- Early Start, Early Finish, Late Start and Late Finish;
- Total Float, Free Float, negative Float and criticality thresholds;
- Longest Path and Multiple Critical/Float Paths, including path number and order;
- FS, SS, FF and SF relationships, signed Lag/Lead and start-to-start calculation options;
- project, activity, resource and relationship-lag calendars, including mixed calendars and working-time boundaries;
- Data Date, actual and remaining work, progress, retained logic, progress override and out-of-sequence behavior;
- activity constraints, mandatory dates, upper/lower bounds and expected finish behavior;
- WBS Summary and Level of Effort treatment;
- resource assignments, time-phased demands, leveling priorities, selected/all resources, cross-project resource settings, over-allocation rules and preservation of scheduled early/late dates;
- post-leveling recalculation of costs and all resulting diagnostics/error conditions;
- deterministic behavior for identical immutable inputs, irrespective of input collection order or worker scheduling order.

The P6 Version 26 Help specifically documents that resource leveling is generally performed during the Forward Pass and that a Backward Pass recalculates late dates when the option to preserve scheduled early and late dates is cleared. It also documents resource-driven critical paths after leveling. These behaviors make naive parallel movement of competing resource assignments unsafe.

The Version 26 Help also distinguishes multiple critical float paths from the rule used to flag critical activities: Float Paths are calculated after scheduling, and activities flagged critical under the selected criticality rule can remain critical even when they are not members of a calculated path. That distinction must survive every optimization.

Scheduling multiple projects is not permission to merge their settings: the official Schedule a Project Help describes project-specific Data Date handling for multiple open projects. Snapshot and project identity boundaries must remain explicit.

## 3. Repository evidence reviewed

The following is a static source review of `main` at the baseline SHA above. Function and module references are authoritative; line numbers can move in later commits.

| Area | Current evidence | Feasibility conclusion |
|---|---|---|
| Shared calculation boundary | `src/construction_pm/schedule_evaluator.py::evaluate_schedule_snapshot` evaluates a materialized immutable input snapshot and does not read repositories during the core calculation. | Strong foundation for isolated/retryable worker execution. |
| Schedule Query | `ScheduleQueryApplicationService.execute` calls the provider synchronously; `AuthoritativeScheduleQueryProvider.execute` loads/binds snapshot facts and calls `evaluate_schedule_snapshot` in the request path. | Heavy Schedule Query work is currently synchronous at this boundary. |
| Date-based CPM | Shared Engine implements forward/backward passes, relationship/constraint checks, floats and critical/float-path projections. | Preserve and characterize before optimizing. |
| Time-Aware CPM | Separate Time-Aware forward/backward/float path exists in `time_forward_pass.py` and `time_schedule.py`. | Must be benchmarked and parity-tested independently; do not assume date/time algorithms are interchangeable. |
| Resource Leveling | `resource_leveling.py` rebuilds and scans time-phased demands during forward leveling; `leveling_scheduler.py` re-runs authoritative CPM at several stages and validates backward candidates through CPM. | Highest likely algorithmic cost for resource-heavy schedules. |
| Multi-project batch | `authoritative_schedule_batch.py::execute_authoritative_schedule_batch` can form one shared graph when external relationships/resource leveling require it; its ordinary independent-project path iterates projects sequentially. | Existing batch boundary is not a distributed worker pool. Cross-project edges/shared resources require coordinated execution. |
| Durable queue readiness | `P6_PRODUCTION_READINESS_CONTRACT.md` validates a durable job-queue configuration and readiness probe. Repository search did not find a Schedule-specific durable queue/worker integration. | Queue configuration alone is not proof that Schedule jobs are enqueued or executed by workers. |
| Duplicate calculation suppression | The authoritative query path evaluates snapshots; no Schedule-specific single-flight/dedup path was identified in this review. | Safe dedup is feasible but not currently evidenced. |
| Runtime observability | Bounded in-process metrics export and structured request/job events exist, but the production readiness contract explicitly says there is no distributed tracing exporter. | Extend metrics/correlation for Scheduling Jobs; do not claim distributed tracing is implemented. |
| Test foundations | Scheduling parity, Time-Aware, resource-leveling, scheduler orchestration, immutable snapshot and PostgreSQL snapshot-concurrency tests exist. | Useful characterization foundation; test coverage does not equal large-scale performance proof. |

### Relevant source files

- `src/construction_pm/scheduling/forward_pass.py`
- `src/construction_pm/scheduling/time_forward_pass.py`
- `src/construction_pm/scheduling/time_schedule.py`
- `src/construction_pm/scheduling/schedule.py`
- `src/construction_pm/scheduling/resource_leveling.py`
- `src/construction_pm/scheduling/leveling_scheduler.py`
- `src/construction_pm/scheduling/authoritative_schedule_batch.py`
- `src/construction_pm/schedule_evaluator.py`
- `src/construction_pm/backend_p0/schedule_query.py`
- `src/construction_pm/backend_p0/authoritative_schedule_query.py`
- `docs/engineering/P6_PRODUCTION_READINESS_CONTRACT.md`
- `docs/architecture/SCHEDULING_P6_PARITY_CERTIFICATION_PACK.md`
- `docs/architecture/TIME_AWARE_BACKWARD_PASS_AND_FLOAT.md`
- `docs/architecture/RESOURCE_LEVELING_REGRESSION_CONFORMANCE_2026-10-21.md`

### Existing test locations identified

- `tests/scheduling/test_schedule_parity.py`
- `tests/scheduling/test_time_forward_pass.py`
- `tests/scheduling/test_time_schedule.py`
- `tests/scheduling/test_resource_leveling.py`
- `tests/scheduling/test_leveling_scheduler.py`
- `tests/test_schedule_evaluator.py`
- `tests/test_authoritative_schedule_query.py`
- `tests/test_schedule_input_snapshot_repository.py`
- `tests/integration/test_postgres_p6_schedule_snapshot_concurrency.py`

Important qualification: the PostgreSQL schedule-snapshot concurrency test exercises concurrent idempotent snapshot upserts. It is not evidence that concurrent CPM calculations or Resource Leveling jobs run in parallel.

## 4. Performance findings and recommended disposition

### P0-F1 — Topological ready-list ordering

**Locations:** `forward_pass.py::_topological_order`; corresponding ready-list logic in `time_forward_pass.py::time_forward_pass`.

The current Kahn-style traversal maintains a sorted Python list, removes its first element with `pop(0)`, and re-sorts when newly-ready activities are inserted. On wide DAG frontiers this adds repeated shifting and sorting overhead.

**Feasibility:** Feasible with low semantic risk.

**Candidate:** Replace the ready list with a min-heap (`heapq`) keyed by the exact existing activity-id ordering. Sort outgoing successors identically before decrementing indegrees. Preserve duplicate-edge counting, cycle detection and exact deterministic order.

**Proof required:** For generated and real graphs, compare the entire topological order, then the complete canonical Schedule result against the unchanged implementation. Include wide, deep, disconnected, duplicate-edge and cyclic cases. A heap is not accepted if tie-breaking changes.

**Status 2026-11-16 — implemented and verified.** `topological_order.py` is now the single ordering primitive for both paths; the previous list algorithm is retained verbatim as the differential oracle in `tests/scheduling/test_topological_order.py`. Measured: wide 100k 3,640 → 3,040 ms, fan 25k 5,945 → 3,011 ms, DAG unchanged; every canonical output hash identical.

### P0-F2 — Time-Aware Free Float search

**Location:** `time_schedule.py::calculate_time_floats`.

The current implementation probes delay values one unit at a time, up to the 10,000 boundary, for each outgoing relationship. Every probe rebuilds candidate start/finish times and evaluates the relationship using calendar-aware lag arithmetic. The date-based path already contains `schedule.py::_max_holding_delay`, which uses exponential/binary search and preserves a 10,000 sentinel boundary.

**Feasibility:** Feasible only after a formal monotonicity proof and exhaustive differential testing.

**Candidate:** A Time-Aware equivalent of bounded exponential/binary search may reduce probes substantially. Do not copy the date-based helper blindly. Prove monotonicity across WORKING_HOUR/WORKING_DAY activity duration, supported Lag units, signed Lag, FS/SS/FF/SF, 24-hour and selected lag calendars, activity-calendar differences, breaks, holidays, DST/time-zone transitions and the exact legacy sentinel behavior.

**Proof required:** Exhaustive small-domain comparisons plus seeded randomized cases across all relationship/calendar combinations, and boundary cases around 0, 1, 9,999 and 10,000. If monotonicity cannot be proven for a supported combination, retain the existing exact algorithm for that combination.

**Status 2026-11-16 — implemented and verified.** `_free_float_limit` uses an 8-step linear prefix then exponential/binary search; `_legacy_free_float_limit` preserves the original scan as the oracle. Boundaries 0/1/9998/9999/10000/20000 and the no-boundary sentinel are covered by tests; the monotonicity argument is documented and exercised over holidays, breaks and signed lags. Measured: DAG 100k 165.3 → 68.2 s (2.42x); slack-heavy cases 993.9 → 54.0 ms and 7,756.9 → 208.1 ms (18.4x / 37.3x); every hash identical.

### P0-F3 — Forward Resource Leveling demand rebuild and repeated scans

**Location:** `resource_leveling.py::propose_forward_leveling_within_float`.

The loop rebuilds shifted demand rows for all included activities, identifies overloaded resource-period pairs, repeatedly sums demand rows for each pair, then scans activities and recomputes their shifted demands to find eligible candidates. It also finds the selected activity again from a list.

**Feasibility:** Feasible with conditions; likely high payoff for resource-heavy projects.

**Candidate:** Maintain deterministic per-activity shifted-demand views and an indexed Resource/Period demand ledger. When one activity shifts, update only its old/new period rows and re-evaluate only affected resource-period keys. Cache resolver-derived shifts where the calendar/version identity is unchanged. Maintain a direct activity-id lookup.

**Critical Decimal/determinism caution:** Do not assume subtracting an old Decimal aggregate and adding a new one is always bit-for-bit equivalent to rebuilding a sum under the active Decimal context. Preserve the current canonical summation order or use an exactly equivalent representation. Candidate enumeration and sorting must keep the current priority tuple, descending demand tie-break and activity-id fallback exactly.

**Proof required:** Every proposed shift, the ordered shift list, final per-period demand, overload report and complete final Schedule must match the current path. Include activities consuming multiple resources, overlapping periods, missing capacities, selected-resource subsets, external project priority, over-allocation percentages, mixed calendars and exact priority ties.

**Status 2026-11-16 — implemented and verified for the forward within-float proposal.** A per-activity shifted-demand cache plus a `(resource, period)` ledger rebuilt in canonical activity order replaces the repeated date arithmetic and per-period scans. The sorted candidate tuple, descending-demand tie-break and activity-id fallback are unchanged, and Decimal sums are rebuilt (not incrementally mutated). Measured: 100 activities 9,421 → 1,072 ms (8.8x), 250 activities 161,183 → 18,473 ms (8.7x); the complete ordered shift list hash is identical, including golden hashes captured before the change. The remaining superlinear growth is the one-accepted-shift-per-iteration decision schedule, not the ledger.

### P0-F4 — Repeated full CPM in Resource Leveling orchestration

**Location:** `leveling_scheduler.py::schedule_with_resource_leveling`.

The current orchestration runs an initial CPM, an intermediate CPM after forward shifts, a final CPM, and—when backward leveling is enabled—may run a full CPM plus final resource-load validation for each backward candidate considered.

This preserves correctness but can scale poorly as candidate count and network size grow.

**Feasibility:** Incremental reuse is feasible only after dependency analysis; replacing authoritative CPM validation with an approximate check is not acceptable.

**Candidate order:**
1. Count and time every schedule call and every backward candidate validation.
2. Identify repeated pure work that is identical for the same immutable activity graph, constraints, options, calendar manifest and calculation identity.
3. Explore memoization of immutable graph/calendar-derived structures and safe CPM intermediate products.
4. Evaluate incremental propagation only if invalidation of successors, predecessors, constraints, early/late dates, Float Paths, global project-finish effects and resource demands is completely defined.
5. Keep final ordinary CPM schedule and final aggregate resource-load validation as authoritative acceptance gates.

**Unsafe shortcut:** Do not accept backward candidates based only on local date arithmetic or independent resource groups when relationships, project-finish boundaries or resource demands can interact.

### P0-F5 — Synchronous Schedule Query and absent proven Schedule Worker path

**Locations:** `schedule_query.py::ScheduleQueryApplicationService.execute`; `authoritative_schedule_query.py::AuthoritativeScheduleQueryProvider.execute`; `schedule_evaluator.py::evaluate_schedule_snapshot`.

The application service authorizes and then synchronously calls its provider. The authoritative provider obtains the immutable snapshot/context/resource facts and calls the evaluator before returning. The evaluator itself is a clean, repository-independent calculation seam once all immutable inputs have been assembled.

The production readiness contract supports a configured durable job queue component, but this review found no Schedule-specific durable job enqueue/claim/lease/worker/result lifecycle. Do not report queue readiness as Scheduling worker implementation.

**Feasibility:** High for independent project jobs, provided a durable job contract and result lifecycle are added.

**Candidate design:** Keep request authentication/authorization, snapshot resolution and required input binding at the application boundary. Persist an immutable job envelope with all calculation inputs/identities, enqueue it, and let a worker invoke the same evaluator. Return a job/run identity and let clients poll/subscribe to status and retrieve the result. For compatibility, small jobs may use a measured inline fast path; do not block the UI request on unbounded large scheduling work.

### P0-F6 — Same-snapshot single-flight and result cache

**Evidence:** No Schedule-specific single-flight path was identified in the inspected authoritative execution route.

**Feasibility:** High with strict identity and authorization gates.

A dedup/cache key must include, at minimum:

- tenant and project identity;
- project revision and immutable Snapshot ID/hash;
- calculation identity and identity schema version;
- canonical Schedule Options and schedule mode;
- Engine semantic/version identity;
- project/activity/resource/relationship-lag calendar manifest and versions;
- resource facts/capacity/demand hash;
- cost/rate input identity when recalculation is requested;
- cross-project batch identity and external relationship/resource facts where applicable.

A project ID alone is never a safe cache key. Re-check each requesting user's authorization and tenant scope before returning a result, even if a calculation is shared. In-flight deduplication must have cancellation/reference-count semantics so one user's cancellation does not cancel work still needed by another user. Cache invalidation must be identity-based, not time-only.

### P0-F7 — Benchmark and scale proof missing

No benchmark evidence was found in the reviewed commit for 5k/25k/50k/100k activity scheduling or 20/100/1000 simultaneous heavy scheduling calculations. The existing CI status demonstrates that defined CI jobs passed; it does not demonstrate performance under large graph or high-concurrency workloads.

**Feasibility:** Required and achievable as an isolated benchmark harness and repeatable fixture suite.

No absolute run-time, user-capacity or cost-per-project claim is approved until it is measured on named hardware/configuration.

## 5. Adaptive execution architecture recommendation

### 5.1 Single Engine, multiple execution instances

Keep one Engine package/build and a versioned calculation identity. Workers are independent processes/containers executing that same artifact against immutable input envelopes. They do not own a different scheduler, calendar engine or Resource Leveling algorithm.

Recommended logical components:

- **Calculation Engine:** pure authoritative scheduling/evaluation logic; no UI, session, database connection or mutable global runtime state.
- **Execution Manager:** accepts job requests, applies queue policy, assigns capacity and manages lifecycle.
- **Durable Job Queue:** persists job identity, payload reference, priority, attempt, lease, cancellation and terminal state.
- **Worker Supervisor/Pool:** starts, drains and replaces worker processes; enforces per-worker CPU/RAM limits and bounded concurrency.
- **Resource Monitor:** reports effective CPU quota/affinity, memory available, current RSS, queue depth, active jobs, database pool pressure and host health.
- **Result Store:** persists immutable result and full calculation identity/content hash, not an unversioned mutable “latest result” alone.

### 5.2 Scale between independent projects — first implementation target

This is the highest-confidence parallelization route.

Each independent job uses one complete immutable schedule input snapshot. A worker loads/binds the required typed inputs, invokes the canonical evaluator, validates the returned run identity and writes the immutable result.

Jobs with shared cross-project relationships, common resource-leveling constraints or an explicitly shared batch graph must be routed as one coordinated batch job unless the existing semantics prove that they can be safely separated. Never split a coupled batch just to fill more worker slots.

For Python CPU-bound execution, process-based workers are the initial candidate because ordinary CPython threads do not provide general parallel Python-bytecode execution under the GIL. Benchmark serialization, process startup, memory copies and calendar materialization before choosing process granularity. A process per activity is not recommended.

### 5.3 Scale inside one project — second, separate research track

Potentially safe candidates:

- Compute activity-independent calendar/materialization/index data once.
- Evaluate activities in the same topological frontier only after every predecessor result for that frontier is fixed.
- Run independent read-only projections over an immutable completed schedule result in parallel.
- Parallelize per-resource demand materialization or candidate scoring only if final candidate choice and reduction order remain identical.

Restrictions:

- Activities with dependency edges cannot be evaluated before predecessor outputs are available.
- Disconnected graph components may still interact through project finish, float basis, global constraints, resource leveling or cross-project resources. Do not call them fully independent until each global dependency is accounted for.
- Resource Leveling is a deterministic global decision process. Parallel demand construction is a more realistic first target than parallel acceptance of activity moves.
- A shared resource period is a synchronization boundary. Candidate moves must not be accepted concurrently if they can consume the same capacity or change each other's CPM dates.
- If a native/compiled kernel is eventually introduced, it must be one canonical Engine implementation or a verified implementation artifact from the same source; it must not become a second independent business-rule engine.

**Recommendation:** do not make intra-project parallel scheduling a prerequisite for the first multi-worker cloud release. Prove and implement safe job-level concurrency first.

### 5.4 Adaptive resource budgeting

Determine the effective CPU capacity available to the process, not merely the machine's advertised CPU count:

- CPU affinity/cpuset;
- container CPU quota and throttling;
- VM/container limits;
- Windows processor/job-object constraints where relevant;
- reserved capacity for API, database, system services and foreground desktop interaction.

Memory must be an explicit concurrency constraint. Use measured peak RSS by schedule-size/feature class and a safety reserve. A worker slot is available only when both CPU and memory budgets permit it.

The manager should adapt based on:

- queue depth and oldest wait;
- active job count and job-size class;
- CPU usage/throttling and process affinity;
- free/committed RAM and measured per-job RSS;
- database connection/latency pressure;
- interactive versus background job priority;
- per-tenant fairness and quotas.

Use bounded scale-up, graceful scale-down and worker draining. Do not kill active jobs during ordinary scale-down. Jobs need leases/heartbeats, idempotent result publication, safe retry and stale-worker fencing.

Do not encode 4/8/16/32 as a hard cap. They are benchmark points. The architecture should allow 1, 4, 8, 16, 32, 64 and larger worker counts across nodes when provisioned capacity supports them; runtime concurrency is determined by measured resource limits.

### 5.5 Cloud, Local Server and Desktop

| Environment | Recommended execution shape | Main feasibility / gate |
|---|---|---|
| Cloud | Durable queue + stateless process/container Workers + shared result store + autoscaling supervisor. | High feasibility for independent jobs. Requires real queue/worker integration, metrics, worker leases, result persistence and deployment sizing. |
| Local Server | Same Engine and queue contracts, with a local supervisor and configurable worker cap; multiple nodes can be added later. | High feasibility. Start single-node; define node registration and distributed locking before multi-node support. |
| Windows Desktop | Bundled local Engine runtime/service with process workers, local persistence and bounded resource policy; no internet dependency for approved offline scheduling. | Feasible with packaging/lifecycle work. Confirm the actual installer/runtime can ship and supervise the same Python Engine securely and reliably. |
| Mobile offline | Execute the approved portable Shared Core semantics locally; no independent Mobile scheduler. | Not yet proven by this assessment. The backend Engine is Python while mobile is a TypeScript client; a supported portable runtime/FFI/WASM/embedded-runtime path and parity gate must be confirmed before claiming full offline parity. Do not silently implement an alternate JS scheduler. |

The existing client foundation documents that Web/Desktop/Mobile consume shared versioned contracts and must not redefine scheduling semantics. That is the correct product rule. It does not, by itself, prove the packaged offline execution runtime for each platform.

## 6. Benchmark and verification plan

### 6.1 Fixture sizes and graph shapes

Build seeded synthetic project fixtures outside production data and outside user projects:

- 1,000 activities — smoke/perf sanity;
- 5,000 activities — medium;
- 25,000 activities — heavy baseline;
- 50,000 activities — very heavy;
- 100,000 activities — stress, only if available RAM/CPU safely permits.

Use multiple graph shapes, not only a linear chain:

- long/deep chains;
- wide frontiers with thousands of ready activities;
- branching/merging DAGs;
- disconnected components;
- high fan-in/fan-out;
- mixed FS/SS/FF/SF and positive/negative Lag;
- custom/mixed calendars, holidays and working intervals;
- constraints, Data Date and progressed activities;
- resource demand overlap and multi-resource activities;
- cross-project relationships/shared resource cases.

Include 5k/10k/25k resource assignments and several calendar counts only when the fixture semantics are fully specified.

### 6.2 Execution matrix

Test the same immutable fixture at worker counts 1, 4, 8, 16 and 32 on a machine/container that can actually supply those CPU and RAM resources. Test 64+ only on an appropriately provisioned environment.

Run separate workload mixes:

1. Same exact snapshot/options requested by many users — expected one in-flight calculation only after single-flight is implemented and proven.
2. Distinct independent project snapshots — expected distinct calculations concurrently.
3. Revisions/options that differ — must never be incorrectly deduplicated.
4. Coupled multi-project graphs/resource scopes — must remain coordinated.
5. Mixed small interactive and large background jobs — test queue fairness and responsiveness.

### 6.3 Measurements

Record, per case:

- exact Engine commit/version and calculation identity;
- hardware model, physical/logical CPU, effective CPU quota/cpuset and RAM limit;
- operating system, Python version, dependency lock and process start method;
- fixture seed, activity/relationship/calendar/resource counts and options;
- wall-clock time, CPU time, peak RSS and memory per worker;
- queue wait, service time, throughput and p50/p95/p99;
- DB pool usage/latency, retry count, failures, cancellation and worker restarts;
- output canonical hash and field-by-field equality result;
- speedup and efficiency against the one-worker baseline.

Do not infer speedup from CPU count alone. Include cold-start and warm-worker cases separately. Isolate database and network effects from pure CPU benchmark runs.

### 6.4 Correctness gates

For every optimized or parallel execution path:

- Compare the complete result structure field-by-field to the unchanged baseline implementation.
- Compare activity identities, dates/times, duration, early/late dates, every Float value, critical status, Float Path/Order, project finish, diagnostics, resource shifts, final demand/capacity, costs and calculation identities.
- Test input-order permutations and repeated runs.
- Ensure the same immutable input produces the same canonical output for 1/4/8/16/32 workers.
- Preserve Decimal semantics, calendar resolution and deterministic tie-breaking.
- Prove tenant/project authorization and result isolation before cache reuse.
- Test retry, worker crash, lease expiry, duplicate delivery, cancellation, stale worker fencing and result publication.
- Keep all final authoritative CPM relationship/constraint checks and final aggregate resource capacity checks.

A benchmark is a **correctness failure** if it is faster but produces even one unapproved output difference.

## 7. Recommended implementation sequence after feasibility review

1. **P0-A — Characterization and baseline:** identify/extend fixtures; capture current full-output hashes and timings; document known runtime gaps. No semantic change.
2. **P0-B — Low-risk algorithmic improvements:** deterministic heap-based ready queue; direct lookup/indexes; other local data-structure improvements only after differential testing.
3. **P0-C — Time-Aware Free Float optimization:** only after monotonicity proof and boundary/property tests.
4. **P0-D — Resource Leveling optimization:** build canonical indexed demand ledger; validate every intermediate ordered decision and final load.
5. **P0-E — CPM reuse:** remove identical pure work where identity is exact; explore incremental propagation only behind full equivalence evidence.
6. **P0-F — Independent-job execution:** durable Schedule Job lifecycle, process workers, bounded queue, safe single-flight and immutable results.
7. **P0-G — Adaptive supervisor:** hardware/quota/RAM detection, global resource budget, graceful autoscaling and tenant fairness.
8. **P0-H — Intra-project parallelism:** evaluate topological-frontier and independent read-only calculations only after the job-level pool is stable.
9. **P0-I — Desktop/Mobile offline packaging:** prove execution of the same authoritative Engine artifact and exact cross-runtime parity.

Each phase is a separate reviewable implementation slice with focused tests, full affected suite and final integrated CI. No performance number is a release claim until its evidence is attached to the exact tested commit.

## 8. Baseline and assessment limitations

### Repository/CI evidence

The reviewed `main` commit was `9d496a219dd39250ff220052d62111b6cdcb958c`.

At the time of review, GitHub Actions check-runs on that exact SHA showed **8/8 successful checks**:

- Python test matrix: 3.11, 3.12 and 3.13;
- Client typechecks: web, desktop, mobile and client-sync;
- PostgreSQL sync integration.

The Vercel preview status was separately reported as rate-limited ("Deployment rate limited — retry in 24 hours"). That is an external preview/deployment limitation and is not a Scheduling test result.

### What this assessment did not prove

- No local pytest suite was executed in this assessment environment.
- No 1k/5k/25k/50k/100k performance benchmark was run.
- No 20/100/1000 concurrent Schedule computation test was run.
- No deployed Cloud or Local Server worker pool was provisioned or exercised.
- No runtime test proved Windows Desktop or Mobile offline packaging of the Python Engine.
- No formal independent Oracle certification is claimed.

The assessment environment could inspect GitHub repository files and CI metadata but could not resolve GitHub from its local shell for a fresh repository checkout. Therefore, all performance findings are static code-derived hypotheses until reproduced by the benchmark phase. Do not copy the rough timing figures from earlier conversational estimates into project performance claims.

## 9. Feasibility verdict

| Capability | Verdict | Reason / condition |
|---|---|---|
| Deterministic min-heap topological queue | **Feasible** | Preserves current lexical ready-order if implemented/tested exactly. |
| Time-Aware Free Float bounded binary search | **Feasible with Conditions** | Must prove monotonicity for all supported units, calendars, lags, relationships and sentinel boundaries. |
| Incremental Resource/Period demand ledger | **Feasible with Conditions** | Decimal summation order, candidate ordering and every affected period must remain exactly equivalent. |
| Reduce repeated CPM work | **Feasible with Conditions / High Risk** | Safe cache of identical pure products is promising; incremental CPM and backward candidate shortcuts can invalidate global dates/floats/constraints. |
| Durable queue and process Worker Pool for independent snapshots | **Feasible** | Immutable evaluator boundary exists; Schedule Query is currently synchronous and needs a complete job/result lifecycle. |
| Same-snapshot single-flight/cache | **Feasible with Conditions** | Requires full calculation identity and independent authorization on every read. |
| Adaptive CPU/RAM-aware worker count | **Feasible** | Must use effective quota/affinity and measured memory/job, with a shared concurrency budget. |
| Scale-out to 32/64/hundreds of workers | **Feasible with Conditions** | Architecture can support it; real capacity depends on queue, DB, memory, network, deployment and tested workload. No fixed capacity claim yet. |
| Intra-project CPM parallelism | **Feasible with Conditions** | Topological frontier/barrier model is possible; dependency and global project-finish semantics must remain intact and process overhead must be measured. |
| Parallel Resource Leveling decisions | **High Risk** | Shared resource capacity and deterministic greedy priority sequence couple candidate moves. Parallelize preparation/scoring before decision acceptance, not the decision itself without proof. |
| Desktop offline execution of same Engine | **Feasible with Conditions** | Bundle/supervise same Engine runtime and bound resources; validate installer and local lifecycle. |
| Mobile offline execution of same Engine | **High Risk / unresolved runtime gate** | Portable authoritative Engine execution/runtime is not proven in current repository evidence; must not create an independent mobile calculation engine. |

### Final recommendation

Proceed with **one canonical Engine plus adaptive process-based Workers for independent immutable schedule jobs** as the first scaling architecture. Start with measured baseline and behavior-preserving hot-spot improvements. Keep intra-project parallelism as a later, separately verified capability. Treat Resource Leveling candidate selection as a deterministic global operation unless a narrower parallel partition is mathematically proven.

This P0 initiative is an optimization and execution-capacity uplift, not a reduction of P6 Version 26 behavior. No scheduling option, calculation, calendar, relationship, validation or user-visible capability may be removed or weakened to obtain a faster benchmark.

## 10. P0-A to P0-D execution record (2026-11-16)

Reference commit `e02850361300c494477148bd5e426d2516534ad5`; optimized commit
`d764c81d6de834390f335971f9069c5a64b8228b` on `p0/scheduling-core-optimization`.
Full evidence, per-run JSON and caveats:
`docs/workspace/evidence/p0-scheduling-core-2026-11-16/`.

### 10.1 What was implemented

- **P0-A:** seeded, version-stable fixture generator and canonical result
  serialisation/hashing (`scheduling/benchmark_fixtures.py`) plus
  `scripts/scheduling_core_benchmark.py`. Six shapes (`chain`, `wide`, `dag`,
  `fan`, `mixed`, `slack`), real wall/CPU/peak-RSS capture, error records
  instead of estimates.
- **P0-B:** `scheduling/topological_order.py`, one deterministic min-heap
  ordering used by the date and time forward passes. Lexicographic ready
  order, duplicate-edge counting, unknown-reference `KeyError` and cycle
  behaviour are preserved exactly.
- **P0-C:** Time-Aware Free Float boundary located with an 8-delay linear
  prefix followed by exponential/binary search. The 10,000-step legacy scan
  remains in the module as the differential oracle. The 0 and 9,999 sentinels
  are preserved bit-for-bit.
- **P0-D:** forward within-float leveling now keeps a cached shifted-demand
  index per (activity, shift) and rebuilds a `(resource, period)` ledger in
  canonical activity order each iteration. Candidate tuples and Decimal sums
  are unchanged.

### 10.2 Measured results (median wall ms, same-session pairs)

| Path | Case | Reference | Optimized | Change |
|---|---|---|---|---|
| Date CPM | DAG 100k | 15,441.7 | 15,505.4 | 1.00x |
| Date CPM | wide 100k | 3,640.4 | 3,040.0 | 1.20x |
| Date CPM | fan 25k | 5,944.7 | 3,011.3 | 1.97x |
| Time CPM + Float | DAG 100k | 165,300.2 | 68,235.6 | 2.42x |
| Time CPM + Float | DAG 25k | 41,009.1 | 17,103.8 | 2.40x |
| Float stress | slack 80 | 7,756.9 | 208.1 | 37.3x |
| Leveling | 100 | 9,421.2 | 1,071.7 | 8.8x |
| Leveling | 250 | 161,182.7 | 18,472.7 | 8.7x |

Every canonical output hash matches the reference. The full Python suite passed
with the new differential suites included: 4,446 passed / 204 skipped at the
code commit `d764c81d`, and 4,449 passed / 204 skipped once the golden leveling
hash assertions were added in the accompanying evidence commit.

### 10.3 Not measured and why

- Python 3.11/3.13: only 3.10 and 3.12 exist in the execution environment;
  the matrix must be produced by CI.
- 16/32/64+ workers and concurrency: the host has 4 CPUs and no such workers
  exist at this commit. P0-F/P0-G are not implemented, so no worker or queue
  number is claimed.
- Leveling 1k/5k/25k/50k/100k: the reference proposal pass at 250 activities
  already costs 161 s and a 1,000-activity attempt did not complete inside a
  300 s budget. The optimized pass at 500 activities costs 158 s. These sizes
  are NOT MEASURABLE on this host until the decision schedule itself changes.
- Constraints, Data Date, progressed activities, cross-project/shared-resource
  and cost fixtures: not yet modelled in the generator, so not benchmarked.
- PostgreSQL-backed scheduling, queue wait, throughput, p50/p95/p99 across
  workers: outside this slice.

### 10.4 Honest measurement caveat

The shared host is not frequency-stable: an identical time-path case measured
1.7x slower in a later session with the same hash and the same input counts.
All comparisons above are back-to-back, same-session pairs of medians, and
absolute times are not a capacity claim.

### 10.5 Next slice

P0-E must first count the CPM passes inside
`leveling_scheduler.schedule_with_resource_leveling` and only then remove
provably identical work; final CPM and final resource-load validation stay
authoritative. P0-F (durable job lifecycle with leases, retries, cancellation,
result persistence and authorization-checked single-flight) and P0-G (adaptive
supervision from real quota/RAM) remain unimplemented and unmeasured.

## 11. P0-E execution record (2026-11-16)

Status: implemented and verified. Reference for this slice is `79200d26`, the
merge of P0-A..P0-D.

### 11.1 What was counted first

`leveling_scheduler.schedule_with_resource_leveling` executes a sequence of CPM
passes: an initial pass on the caller's constraints, an intermediate pass on the
forward-leveling constraints, one trial pass per backward candidate, and a
closing pass on the final constraints. Every pass calls the same
`construction_pm.scheduling.schedule.schedule` with the same activities,
relationships, calendars, options, lag resolvers, batch finish, activity
resolvers and calculation context. Only the ordered `ActivityConstraint` tuple
differs.

Measured before the change:

| Scenario | CPM passes |
|---|---|
| Two linked activities, one accepted backward move | 5 |
| Forward-only orchestration, 20 / 50 / 100 activities | 3 / 3 / 3 |
| No forward and no backward shift | 3 |

Three of those passes were exact duplicates: the intermediate pass repeats the
initial pass when forward leveling proposed no positive shift; the closing pass
repeats the intermediate pass when no backward shift was accepted or backward
leveling is disabled; the closing pass repeats the last accepted candidate
trial when that candidate produced the final constraint set.

### 11.2 What was changed

The identical passes are replaced by the already computed `ScheduleResult`.
Because `schedule()` is a pure function of its arguments and the constraint
tuple is compared exactly, reuse cannot change an output. The final
`_validate_final_resource_load` still runs on the returned result, so the final
resource-capacity validation and the final CPM result remain authoritative. No
calculation, option, calendar rule, relationship rule, float value or leveling
decision changed, and the single authoritative CUBI engine is still the only
implementation.

### 11.3 Measured result

Forward-only orchestration fixture, 3 runs after 1 warm-up, same host:

| Activities | CPM passes | Wall time before | Wall time after | Gain | Single CPM pass |
|---|---|---|---|---|---|
| 20 | 3 -> 2 | 24.541 ms | 22.989 ms | 6.3% | 1.863 ms |
| 50 | 3 -> 2 | 293.177 ms | 284.480 ms | 3.0% | 9.315 ms |
| 100 | 3 -> 2 | 2,172.426 ms | 2,147.145 ms | 1.2% | 33.400 ms |

Every canonical output hash is identical (`d23faac4…`, `a43f0cd7…`,
`a3da54e1…`). The gain is bounded by the removed pass: the dominant remaining
cost is the one-shift-per-iteration forward decision schedule, which is
quadratic in activity count and outside P0-E.

The two-activity backward-acceptance scenario drops from 5 to 3 passes with an
identical result; the count, the fresh-CPM equality and the continued final
validation are asserted in `tests/scheduling/test_leveling_cpm_reuse.py`.

### 11.4 Not measured

- Backward-acceptance orchestration at 50+ activities: the fixtures that force
  many accepted backward moves also hit the one-shift-per-iteration cost and did
  not converge without a capacity profile tailored to proposal order, so no
  number is claimed.
- Python 3.11/3.13 and PostgreSQL: CI only.
- Worker counts, queue pressure and throughput: P0-F/P0-G are not implemented.

Evidence: `docs/workspace/evidence/p0e-scheduling-cpm-reuse-2026-11-16/`.

### 11.5 Next slice

P0-F: durable Scheduling Job lifecycle (stable identity, leases, retries,
cancellation, result persistence, failure recovery, and single-flight dedup that
still enforces per-user authorization), with the same Engine and version
identity for every execution surface.

## 12. P0-F execution record (2026-11-16)

Status: implemented and verified. Reference for this slice is `9591d000`, the
merge of P0-E.

### 12.1 Why this slice came next

§4 P0-F5/P0-F6 recorded a synchronous Schedule Query path with no durable
Schedule Worker: nothing survived a process restart, two concurrent submissions
for the same snapshot could both calculate, and the canonical result hash was
not bound to the engine version that produced it. Those are availability and
correctness-of-identity defects, not performance defects, so they were fixed
before any worker parallelism (P0-G/P0-H) could rely on them.

### 12.2 What was built

Two layers around the unchanged authoritative engine. Neither layer calculates;
the caller still runs `construction_pm.scheduling` exactly once and persists the
canonical hash.

| Requirement | Implementation |
|---|---|
| Identity | `job_id = sha256(tenant, project, dedup scope, request fingerprint, generation)`; `engine_version` and `calculation_identity` persisted on the job |
| Leases | Owner + token + expiry; only the token holder renews, checkpoints, completes or fails; expiry is taken over only after an explicit check |
| Retries | Retryable failure or expired lease requeues until `max_attempts`, then FAILED with the last error |
| Cancellation | QUEUED cancels immediately; LEASED records the request and terminates at the next checkpoint, renewal, completion attempt or expiry, never publishing a result |
| Result persistence | One immutable result per job; identical replay tolerated, different result rejected |
| Failure recovery | `recover_expired()` requeues, fails or cancels abandoned leases |
| Single-flight | Partial unique index on the active state per authorization-scoped request key, so at most one QUEUED/LEASED job exists |
| Authorization | The dedup key includes an authorization-derived scope and `can_view` is re-checked before returning a job or a result, so dedup never merges two users' runs |

State machine: `QUEUED -> LEASED -> SUCCEEDED | FAILED | CANCELLED`, with
`LEASED -> QUEUED` on a retryable failure or an expired lease. Every durable
write is a revision compare-and-set, so a stale worker cannot overwrite a newer
state.

### 12.3 Measured result on PostgreSQL 14.24

Local single-node cluster, autocommit connections, schema created from
`infra/scheduling_job_schema.sql`; each cycle is submit → claim → complete.

| Metric | Value |
|---|---|
| Cycles | 200 |
| Median cycle | 0.506 ms |
| p95 cycle | 0.715 ms |
| Max cycle | 2.534 ms |
| Schema init | 0.834 ms |

Concurrent single-flight: 16 threads, one connection each, all submitting the
same authorization-scoped request at a shared barrier.

| Metric | Value |
|---|---|
| Unique job ids | 1 |
| Jobs created | 1 |
| Errors | 0 |
| Wall time | 31.002 ms |

The guarantee is the partial unique index, not application timing: the losing
threads hit the index, re-read and return the winner's job.

### 12.4 Correctness evidence

- `tests/scheduling/test_scheduling_job_lifecycle.py` — 16 tests on the
  in-memory reference repository: single-flight, authorization scoping,
  claim/renew/stale token, completion and result immutability, engine identity
  mismatch, retryable vs terminal failure, cooperative cancellation, expiry
  recovery (requeue/fail/cancel), a new generation after a terminal job, 8
  concurrent submissions, and persistence of the real engine's canonical hash
  for a 50-activity fixture.
- `tests/test_scheduling_job_postgres.py` — 6 PostgreSQL tests: round trip and
  result persistence, the partial unique index across two real connections, a
  lost compare-and-set, takeover of an expired lease by another worker, result
  immutability, and 6 concurrent submitting threads. Run locally against 14.24
  and in the `postgres` CI job.
- No scheduling calculation, leveling decision, option, calendar rule,
  relationship rule or float value was modified. The lifecycle never produces a
  schedule; it only stores the engine's canonical hash and payload.

### 12.5 Not measured

- Multi-host or high-availability PostgreSQL: only a local single node exists.
- End-to-end HTTP admission and client polling: no HTTP surface was added, so
  none is claimed.
- Worker counts, queue waiting time and throughput: P0-G/P0-H are not
  implemented.

Evidence: `docs/workspace/evidence/p0f-scheduling-jobs-2026-11-16/`.

### 12.6 Next slice

P0-G: adaptive resource management — one global worker budget derived from
effective CPU affinity and cgroup quota, memory headroom and real queue
pressure, with the same engine and version identity on every execution surface.

## 13. P0-G execution record (2026-11-16)

Status: implemented and verified. Tested commit `d2fc916e`, based on `3b56a4c2`
(P0-F merge).

### 13.1 What was built

One derived worker budget and one execution loop; neither contains calculation
logic, and neither has a Cloud/Desktop/Mobile/Worker variant.

| Requirement | Implementation |
|---|---|
| Effective CPU capacity | CPU affinity plus cgroup v2 `cpu.max` or cgroup v1 `cpu.cfs_quota_us`, whichever is smaller |
| Memory capacity | `MemAvailable` from `/proc/meminfo` capped by the cgroup memory limit |
| One global budget | A process-wide `BoundedSemaphore` permit set; every calculation holds one permit for its whole duration, so all executors in a process share the same ceiling |
| Adaptive processing | `AdaptiveWorkerController` raises the dispatch target by one per observation while a backlog exists and lowers it after consecutive empty observations; it is clamped to the hard budget |
| Same engine identity | The executor optionally pins `(engine_version, calculation_identity)` and fails the job before calculating when the record differs; every surface calls the same engine and the same lifecycle |
| Durable execution | P0-F leases are renewed by a heartbeat while the calculation runs; completion persists the engine's canonical hash; retryable failures requeue, terminal failures are recorded, cancellation never publishes a result |

A worker is one OS process with one permit, because the authoritative
calculation is CPU-bound Python and holds the GIL. The adaptive controller
therefore changes how many processes are kept busy, not how many threads run
Python bytecode at once. This is a deployment property, not a calculation rule.

### 13.2 Measured result on this host

Host: 4 logical CPUs, no cgroup quota, 5.93 GiB available memory. Derived
budget: 4 workers, CPU-limited.

32 jobs on one immutable 200-activity fixture, real worker processes over
PostgreSQL 14.24:

| Workers | Wall (ms) | Throughput (jobs/s) | Speed-up | CPU cores | p50 latency (ms) | p95 | p99 |
|---|---|---|---|---|---|---|---|
| 1 | 1,090.1 | 29.36 | 1.00x | 0.94 | 601.0 | 1,031.6 | 1,097.7 |
| 2 | 557.4 | 57.41 | 1.96x | 1.85 | 316.4 | 518.7 | 552.6 |
| 4 | 316.4 | 101.15 | 3.45x | 3.32 | 189.4 | 294.4 | 311.2 |

Queue wait, not calculation time, is what parallelism removes: p50 queue wait
569.2 → 284.7 → 156.9 ms while p50 calculation time stays 31.3 → 31.6 → 32.4 ms.

All runs produced exactly one canonical hash,
`2719a62c5717fbd11a022e107f53b97660097d14ad607be571e29740e6b8eacf`, equal to the
single-process reference; all 32 jobs succeeded and persisted a result, and the
queue was empty after each drain.

8 workers forced onto 4 CPUs produced 96.34 jobs/s, 4.8% slower than 4 workers,
which confirms the derived cap is a capacity bound rather than an arbitrary
limit.

### 13.3 Not measured

- 16 and 32 workers: the host supplies 4 effective cores, so the benchmark
  refuses them and records the refusal. No extrapolated number is claimed.
- Multi-host PostgreSQL and real Cloud/Desktop/Mobile deployment surfaces: only
  a local single-node cluster exists.
- Thread-pool scaling inside one process: excluded by the GIL and not claimed.
- Memory pressure: the policy has a memory cap and a 512 MiB per-job estimate,
  but no out-of-memory run was performed.
- HTTP admission and client polling: no HTTP surface was added.

Evidence: `docs/workspace/evidence/p0g-adaptive-workers-2026-11-16/`.

### 13.4 Next slice

P0-H: intra-project parallelism. Unlike P0-G, this touches calculation
semantics, so it remains gated on exact canonical equality for every split and
on retaining the final CPM and final resource-capacity validation.

## 14. P0-H execution record (2026-11-16)

Status: implemented and verified; production default unchanged. Tested commit
`af8b38c0`, based on `3ed3892c` (P0-G merge).

### 14.1 What was parallelized and why only this

Profiling the time-aware engine at 20,000 activities showed the per-activity
float calculation dominates: forward pass 0.73 s, backward pass 2.50 s, floats
10.13 s (about 76% of the 13.4 s total). Each activity's float is already a pure
function of the frozen early/late schedules, its outgoing relationships,
calendars and lag calendar, so evaluating activities in different processes
cannot change a value.

`calculate_time_floats` now accepts an execution-only `workers` parameter:
sorted ids are split into contiguous chunks, evaluated by the same pure
function in forked children, and merged in id order. `time_schedule` exposes it
as `float_workers`. The parameter changes neither inputs nor formula, and the
default is 1, so no existing caller changes behaviour.

Deliberately left sequential:

- the date CPM forward/backward passes and the resource-leveling decision loop,
  whose steps depend on the previous accepted result;
- thread-based execution, which cannot help CPU-bound Python under the GIL;
- any automatic use inside a threaded server process, because forking a process
  that holds database/logging locks is unsafe. The parallel path falls back to
  the same sequential loop when `threading.active_count() > 1` or when the
  platform has no `fork`.

### 14.2 Measured result

Same fixture and seed, 2 runs after 1 warm-up, canonical hash compared:

| Activities | Float workers | Wall median (ms) | Speed-up | Parent CPU (ms) |
|---|---|---|---|---|
| 5,000 | 1 | 3,350.0 | 1.00x | 3,349.6 |
| 5,000 | 2 | 2,155.5 | 1.55x | 903.0 |
| 5,000 | 4 | 1,482.7 | 2.26x | 837.9 |
| 20,000 | 1 | 13,462.5 | 1.00x | 13,461.0 |
| 20,000 | 2 | 8,516.5 | 1.58x | 3,420.1 |
| 20,000 | 4 | 5,923.9 | 2.27x | 3,375.5 |

The ceiling is the still-sequential forward and backward passes: about 24% of
the 20,000-activity run, so `1 / (0.24 + 0.76/4) ≈ 2.4x` is the best four
workers can do; 2.27x was measured. Canonical output hashes are identical at
every worker count (`3d2f1f8d…` at 5,000 and `d6fb2475…` at 20,000), and the
parity tests compare every field of every float record.

### 14.3 What this means for adoption

The capability is real and exact, but it is not switched on by default. A
server that already runs calculation threads cannot safely fork during a
calculation, and P0-G's executor runs calculations in threads. Using this path
therefore requires a dedicated single-threaded worker bootstrap that passes
`float_workers` explicitly. Until such a bootstrap exists, the measured gain is
available but unexercised in production, and the sequential path remains the
authoritative default. This is recorded rather than presented as a production
speed-up.

### 14.4 Not measured

- Time constraints, exception calendars and working-day durations in the
  parallel path: the parity fixtures cover FS/SS/FF/SF, positive and negative
  lags, and working-hour/day values, but not every V26 calendar variant.
- 16 and 32 float workers: the host supplies 4 effective cores.
- Memory sum across children: only the maximum child RSS is available from
  `RUSAGE_CHILDREN`.
- Any gain in the date path, leveling path or multi-project batch: those were
  not parallelized in this slice.

Evidence: `docs/workspace/evidence/p0h-intra-project-floats-2026-11-16/`.

### 14.5 Next slice

P0-I: offline runtime boundary. The remote engine, calendar and snapshot
dependencies of the offline runtime need an explicit boundary with no network
calls, and the offline result must remain the same canonical output.

## 15. P0-I execution record (2026-11-16)

Measured on merged main `ffc946ca` (P0-I merged as `648cef68`; reference main
before the branch was `a7735bb7`). No second calculation engine exists: the
offline runtime calls `evaluate_schedule_snapshot`, the same boundary used
online.

### 15.1 Boundary definition

| Requirement | Implementation |
|---|---|
| Self-contained artifact | `OfflineScheduleBundle` (`construction-pm/offline-schedule-bundle/v1`): canonical snapshot payload + SHA-256, calculation context, snapshot creation metadata, and the version-pinned calendar definitions |
| Calendar dependency | Calendar definitions are exported from `CalendarResolverRegistry.entries()` including exception layers and base references; the bundle carries only the closure of calendars the snapshot resolves |
| Snapshot dependency | The runtime rebuilds `ScheduleInputSnapshot` from the payload and re-validates its hash; a tampered payload fails with `OFFLINE_SNAPSHOT_HASH_MISMATCH` |
| Engine dependency | No repository, transport, URL, credential or engine discovery is accepted. The runtime evaluates in the same process with the same engine code |
| No network | `deny_network_access()` replaces `socket.connect`, `connect_ex`, `create_connection` and `getaddrinfo` with raising stubs for the duration of `execute()` |
| Fail closed | Missing calendars, missing base calendars, hash mismatches, identity mismatches and unsupported bundle schemas raise stable `OFFLINE_*` codes; nothing is coerced |
| Preserved semantics | The offline path runs date-based or time-aware CPM through the existing evaluator, including final CPM validation. Resource leveling and resource-dependent placement need application-bound capacity inputs that a bundle does not carry yet and are rejected with `OFFLINE_LEVELING_INPUT_REQUIRED` instead of being simplified |

### 15.2 Measured parity

`scripts/scheduling_offline_parity.py` evaluates the snapshot online, binds the
bundle, then executes the bundle in a fresh subprocess whose socket layer is
disabled *before* any `construction_pm` import. 3 runs per size, 4 logical CPUs:

| Activities | Relationships | Online median | Offline median (process + parse + calculate) | Bundle bytes | Canonical run identity |
|---|---|---|---|---|---|
| 1,000 | 1,923 | 241.1 ms | 272.7 ms | 853,285 | `0c811c700798…` identical |
| 5,000 | 9,575 | 1,237.2 ms | 1,337.6 ms | 4,247,877 | `901b101d3500…` identical |

A probe subprocess attempting `socket.create_connection` returned
`OFFLINE_NETWORK_ACCESS_DENIED:create_connection`, so the guard is active in the
measured environment rather than merely unused.

### 15.3 Exact resolver hoist exposed by the boundary

Building bundles made an existing hot path visible:
`resolve_relationship_lag_resolvers` rebuilt the snapshot-wide activity calendar
map once per relationship, although that map is relationship-independent. It is
now resolved once and passed into `resolve_relationship_lag_calendar` (new
optional `calendars` keyword). `registry.resolve` is pure for a pinned
reference, so the resolver objects are unchanged.

Old implementation re-run against the same snapshots, 3 runs:

| Activities | Old median | New median | Speed-up | Canonical run identity |
|---|---|---|---|---|
| 200 | 252.0 ms | 49.3 ms | 5.11x | identical `7ba4b8a7…` |
| 1,000 | 5,247.5 ms | 243.2 ms | 21.58x | identical `0c811c70…` |

This removes repeated resolution only. No CPM pass, float, constraint,
calendar rule, validation or leveling decision changed or was reordered.

### 15.4 Verification

- `tests/scheduling/test_offline_schedule_runtime.py` (12 tests): date and
  time-aware round-trip identity, exception layers and base inheritance,
  deterministic bundles, missing calendar/base rejection, tampered payload and
  bundle hashes, unsupported schema, network guard denial and restoration,
  guard active during `execute`, explicit leveling rejection.
- `tests/scheduling/test_calendar_resolution.py`: precomputed calendars yield
  the same resolver object as per-call resolution.
- Full matrix: Python 3.11 / 3.12 / 3.13, PostgreSQL 14.24 integration.

### 15.5 Not measured

- Windows Desktop installer and runtime supervision; mobile FFI/WASM/embedded
  runtime packaging. Mobile offline parity is still gated on a proven portable
  runtime for the same engine and is not claimed here.
- Time-aware bundles beyond unit parity, multi-project bundles, leveling
  bundles, and compatibility with older bundle schemas.
- Peak RSS of the offline process and bundle parse time at very large sizes.

### 15.6 Phase status

P0-A through P0-I are implemented and measured. P0-I closes the scheduled
sequence: there is no further phase in the canonical P0 plan. Any follow-up
should be a new, explicitly scoped change (for example leveling inputs in the
bundle, or a proven mobile runtime) rather than an extension of this record.

Evidence: `docs/workspace/evidence/p0i-offline-runtime-2026-11-16/`.

## 16. P0-J execution record (2026-11-17)

P0-J is the continuation registered as [Issue #2020](https://github.com/consttruction-pm/consttruction-pm-platform/issues/2020) and linked to #1992. It starts from merged main after #1998/#1999/#2000 and does not re-implement P0-A … P0-I. Phases 1–2 (profiling, leveling, closed forms) were merged as `92a62afd` (PR #2021); phases 3–5 (parallel float, job path, stress) were merged as `b6b3cb71` (PR #2022) and measured on `87fc5c4a`. Nothing below removes a capability, option, validation, calendar rule, relationship type, float/critical-path rule, leveling decision or calculation output.

### 16.1 Measured profiling (phase 1)

Profiling used `scripts/p0j_profile.py` (phase wrappers plus cProfile) on the real pre-change commit `ee9753e6`, with per-size benchmarks to confirm the shares. cProfile inflates absolute time ~2–3×; only shares are used from it.

| Path | Dominant cost before P0-J | Share |
| --- | --- | --- |
| Date CPM | `_max_holding_delay` probe search for Free Float | ~70 % |
| Time-aware CPM | `_free_float_limit` prefix + exponential/binary probe | ~76 % |
| Forward leveling | full ledger rebuild + rescan per overloaded period per accepted 1-day shift | 18.6 s at 250, ~158 s at 500 activities |
| Backward leveling | same rebuild shape and cumulative replay | 45.7 s at 100, >600 s at 250 |

The qualitative finding matters more than the percentage: every hot spot was repeated *recomputation* of something already determined (a limit, a demand ledger), not an intrinsically expensive P6 calculation. That is why closed forms and incremental ledgers could remove the cost without touching a single decision rule.

### 16.2 Resource Leveling first (phase 2)

Both passes now keep a per-`(resource, period)` member map, exact `Fraction` totals, a maintained over-allocation set, a version-stamped lazy min-heap of candidates, per-activity demand caches and an O(1) contiguous working-day series. Candidate ordering, priority keys, protected activities, shift bounds and every recorded shift are unchanged. The previous rebuild algorithms are kept as an executable oracle in `tests/scheduling/test_leveling_incremental_equivalence.py` (183 tests, 80 randomized seeds per direction, four calendars including holidays, multiple resolvers, signed/absent priorities, multi-resource demands, over-allocation percentages, beyond-float bounds, two golden decision sequences).

| Case | Reference `ee9753e6` | Current | Speedup | Shifts | Canonical hash |
| --- | --- | --- | --- | --- | --- |
| forward 100 | 1,074.2 ms | 14 ms | 75× | 84 | identical |
| forward 250 | 18,317.6 ms | 48 ms | 380× | 226 | identical |
| forward 500 | 156,983.4 ms | 83 ms | 1,888× | 476 | identical |
| forward 25,000 | – | 5,329 ms | – | – | `7c142e0b…` |
| forward 50,000 | – | 11,068 ms | – | – | `fc188c3e…` |
| backward 100 | 45,672.6 ms | 17 ms | 2,669× | 864 cumulative | identical `53429109…` |
| backward 250 | not finished in 600 s | 53 ms | ≥ 11,400× (lower bound) | – | – |
| backward 25,000 | – | 7,690 ms | – | – | `7509be0b…` |

Orchestration (CPM + forward + backward + validation) at 20/50/100 activities is 10/52/197 ms with the same hashes as the P0-E evidence, so CPM reuse is preserved.

### 16.3 Verified closed forms (phase 2, CPM)

`_holding_delay_boundary` derives the holding-delay limit from working-day index arithmetic; `_float_limit_interval_bound` does the same for working time. Both fall back to the original probe path whenever any calendar, unit or lag combination is outside the proven case (different lag calendar, non-working units). Accuracy is established by differential tests against a reconstruction of the probe predicate: `tests/scheduling/test_free_float_closed_form.py` (12 seeds × 300 random cases × all relationship types, lags −4..5, plus a full-schedule equality check with the closed form disabled) and `tests/scheduling/test_time_float_search.py` (shape × float-day equality with the interval bound disabled, signed lags, WORKING_DAY fallback).

| Shape | Activities | Before | After | Speedup | Hash equal |
| --- | --- | --- | --- | --- | --- |
| date dag | 25,000 | 3,765.3 ms | 1,725.5 ms | 2.18× | yes |
| date dag | 100,000 | 15,725.3 ms | 7,401.6 ms | 2.12× | yes |
| time dag | 25,000 | 17,043.9 ms | 8,153.0 ms | 2.09× | yes |
| time dag | 100,000 | 69,038.8 ms | 33,641.9 ms | 2.05× | yes |

The 50,000/100,000 reference numbers were produced in a worktree at `ee9753e6` with the same fixture (`dag`, seed 20261116, `float_days=0`), 1 warm-up and 3 repeats. The older P0 baseline file at 100,000 is not used for this ratio because it ran `float_days=2`, a different fixture condition.

The time-aware path also fixes a real crash: `calculate_time_hours` raised `finish must not precede start` for negative total float because the magnitude was computed in the wrong direction before negation. Signed results are now covered for every relationship type and lag.

### 16.4 Safe parallel float in the real worker path (phase 3)

`FloatExecutionPolicy(workers, admission, allow_spawn)` now crosses the authoritative boundary: `evaluate_schedule_snapshot(..., float_execution=...)` forwards it through `_evaluate_materialized` into `time_schedule(float_policy=...)`, and `AuthoritativeScheduleQueryProvider` and `OfflineSchedulingRuntime` accept it. The offline runtime defaults to one slot per effective core; the job executor defaults to sequential.

Safety rules, all enforced in code and tested:

* `fork` only when `threading.active_count() == 1` and there is no parent process (a forked child must never inherit another thread's locks).
* `spawn` only with explicit `allow_spawn` and only if the immutable float context pickles.
* One `_FLOAT_POOL_GUARD` per process, so a nested pool is refused rather than multiplied.
* Extra slots come from `GlobalExecutionBudget.admit_extra`, which grants only what the process-wide permit set can actually give, non-blocking by default to avoid holder-waits-on-holder deadlock; extra slots are accounted separately from job permits.
* Deterministic merge by activity id in canonical order; any failure (`OSError`, `RuntimeError`, budget exhaustion, one chunk) falls back to the exact sequential loop.

Measured with `scripts/p0j_float_parallel.py` (2 warm-ups, 7 repeats; spawn 5), whole time-aware schedule:

| Activities | Context | 1 slot | 2 | 4 | Speedup at 4 | Canonical hash |
| --- | --- | --- | --- | --- | --- | --- |
| 500 | main (`fork`) | 183.7 ms | 146.2 ms | 125.6 ms | 1.46× | equal |
| 2,000 | main (`fork`) | 736.0 ms | 579.1 ms | 504.1 ms | 1.46× | equal |
| 5,000 | main (`fork`) | 1,864.9 ms | 1,447.6 ms | 1,229.1 ms | 1.52× | equal |
| 25,000 | main (`fork`) | 9,485.3 ms | 7,512.8 ms | 6,262.4 ms | 1.51× | equal |
| 25,000 | thread, default | 9,490.5 ms | – | 9,464.0 ms | sequential by design | equal |
| 25,000 | thread, `allow_spawn` | 9,436.8 ms | 10,170.6 ms | 10,311.5 ms | 0.92× | equal |

The float pass alone is ~3.3× faster with fork (4.60 s → 1.30 s at 25,000); the whole schedule gains 1.5× because forward and backward passes stay serial (they are relationship-dependent and are not parallelised without a proof). In the threaded executor, the only safe method is `spawn`, and the float context pickles to 11.6 MB at 25,000 activities: ~25 µs per activity of transfer against ~169 µs of parallelisable work, i.e. a measured loss, so `allow_spawn` is `False` and the executor stays exactly sequential with `pool_slots_used = 1`. The architecture solves the safety problem rather than disabling the feature: the same policy is profitable in the offline/CLI runtime, and opting into spawn is one field for hosts with cheaper transfer.

### 16.5 Real Scheduling Job path (phase 4)

The float policy completed the query provider path, which had no way to express execution policy without bypassing the authoritative boundary. `tests/scheduling/test_scheduling_job_authoritative_path.py` exercises the real `SchedulingJobService` + `SchedulingJobExecutor` + `AuthoritativeScheduleQueryProvider` over a SQLite snapshot repository: three jobs on the same snapshot produce the same `output_hash`, a resubmission after completion deduplicates, tenant/project isolation rejects cross-scope reads (`SchedulingJobError`), and a job whose `calculation_identity` does not match the engine is `FAILED` with no result row. Duplicate/single-flight, concurrent same-snapshot, retry/lease expiry, crash recovery, cancellation and no-partial-result behaviour remain covered by the P0-F/P0-G suites and were not weakened.

Performance of the budgeted executor was re-confirmed by phase 5 rather than re-measured in isolation: the stress matrix below runs the production executor in every worker process.

### 16.6 Reproducible stress (phase 5)

Pure engine (1,000 → 100,000 activities, date/time/leveling, wide/fan/dag) is recorded in the evidence directory with 2 warm-ups and 3–7 repeats; 50,000/100,000 results are in §16.3. The queue/DB/worker path is measured separately by `scripts/p0j_job_stress.py`, because mixing API latency with engine time would make both unreadable.

Method: fixed 200-activity fixture, real PostgreSQL 14.24, one production `SchedulingJobExecutor` per OS process with one budget permit, 32 request-scoped client connections, 10% of users cancelling and resubmitting, status polling at 20 Hz, per cell one warm-up plus three measured repeats.

| Users | Workers | Wall median (spread) | Jobs/s | Queue p50 / p95 | Status p50 | Submit p99 | CPU cores | PG conns |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 100 | 1 | 2.652 s (1.7 %) | 41.5 | 1,258 / 2,354 ms | 0.13 ms | 14.6 ms | 0.62 | 34 |
| 100 | 2 | 1.361 s (1.1 %) | 80.8 | 623 / 1,154 ms | 0.11 ms | 14.9 ms | 1.22 | 35 |
| 100 | 4 | 0.798 s (2.5 %) | 137.9 | 329 / 524 ms | 0.16 ms | 30.9 ms | 2.38 | 38 |
| 500 | 1 | 9.535 s (3.0 %) | 57.7 | 6,365 / 11,686 ms | 8.84 ms | 199.8 ms | 0.84 | 35 |
| 500 | 2 | 6.793 s (0.7 %) | 81.0 | 2,983 / 5,315 ms | 5.86 ms | 228.9 ms | 1.20 | 36 |
| 500 | 4 | 4.088 s (2.0 %) | 134.6 | 1,635 / 2,563 ms | 6.59 ms | 178.3 ms | 2.04 | 38 |
| 1,000 | 1 | 19.137 s (2.6 %) | 57.5 | 12,502 / 22,884 ms | 38.37 ms | 596.7 ms | 0.84 | 35 |
| 1,000 | 2 | 13.138 s (0.3 %) | 83.7 | 5,811 / 10,520 ms | 12.15 ms | 518.5 ms | 1.23 | 36 |
| 1,000 | 4 | 8.467 s (2.3 %) | 129.9 | 2,973 / 4,975 ms | 15.62 ms | 438.5 ms | 1.95 | 38 |

Oversubscription on the same host (100 users): 8 processes 0.620 s / 177.4
jobs/s / 3.23 cores / 26 connections; 16 processes 0.632 s / 173.9 / 4.04 / 33;
32 processes 0.763 s / 144.1 / 4.58 / 49; 64 processes 1.118 s / 98.4 / 5.30 /
82, with a 50.5 % spread across its three runs. The median of three repeats is
used everywhere; the warm-up run is stored but excluded.

The scripted cancels are exact (every `cancel_requested` reached terminal `CANCELLED`), every case persisted one canonical hash equal to the in-process engine result, and no case left a pending job, a failed job, a partial result, or a worker that exited non-zero. Scaling is real but bounded by the client path: 1→4 workers gives 3.32× at 100 users, 2.33× at 500 and 2.26× at 1,000, while CPU use never exceeds 2.38 of 4 cores and submit p99 grows to 597 ms at 1,000 users. Oversubscription confirms the limit instead of assuming it: 8/16 processes reach 177.4/173.9 jobs/s, 32 drops to 144.1 and 64 to 98.4, with 82 PostgreSQL connections and 5.30 cores of CPU time at 64. The harness therefore refuses `workers > effective_cores` unless a run is explicitly labelled simulated.

### 16.7 Invariants held

| Invariant | Status |
| --- | --- |
| Exactly one authoritative calculation engine | Yes: all paths call `evaluate_schedule_snapshot`; no per-surface engine was added |
| Identical canonical hash for 1 vs N workers | Yes: float 1/2/4 slots, 3 runs per case, and every job-stress repeat |
| No relationship-dependent phase parallelised | Yes: only per-activity floats; forward/backward passes and leveling decisions stay serial |
| Final CPM validation retained | Yes: unchanged and exercised by every benchmark and job |
| Final resource-capacity validation retained | Yes: unchanged; leveling equivalence tests include over-allocation and capacity checks |
| Worker count from real capacity | Yes: `detect_effective_capacity` + `GlobalExecutionBudget`; 8–64 recorded only as simulated |
| No capability/validation removed for speed | Yes: the only algorithm changes are exact closed forms and incremental ledgers with oracles |

### 16.8 Verification

* Full suite on `87fc5c4a`: 4,873 passed, 131 skipped; post-merge on `b6b3cb71`: 4,889 passed, 131 skipped (Python 3.12, local PostgreSQL 14.24).
* New tests: `tests/scheduling/test_time_float_execution_policy.py` (11) and `tests/scheduling/test_scheduling_job_authoritative_path.py` (3), plus the existing differential suites (`test_free_float_closed_form.py`, `test_time_float_search.py`, `test_leveling_incremental_equivalence.py`).
* Required CI: GitHub Actions Python 3.11/3.12/3.13, PostgreSQL integration and the four typechecks. Vercel deployments are infrastructure-only for this change (no Web/UI change).

### 16.9 Limits and phase status

* 4 effective CPUs; no multi-host, multi-node or >4-worker capacity is claimed. 8/16/32/64 results are simulated-quota behaviour on this host.
* The job-stress fixture is deliberately small and constant; engine scaling is §16.3, not the queue table.
* The stress harness does not kill workers mid-job; crash recovery and lease expiry are covered by the lifecycle suites, not by this matrix.
* Time-aware peak RSS is 9–10% higher than the reference at 50,000/100,000 activities, a measured trade for the closed-form interval candidates.
* Desktop packaging, mobile runtime, leveling bundles and HTTP admission remain out of scope, as recorded in §15.5.

P0-A … P0-J are implemented and measured. No further phase is implied by this record; any follow-up (leveling inputs in the offline bundle, multi-host PostgreSQL, a different worker topology) requires a new, explicitly scoped decision.

Evidence: `docs/workspace/evidence/p0j-scheduling-optimization-2026-11-17/`.
