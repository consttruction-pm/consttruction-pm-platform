# P0-E evidence — exact CPM-pass reuse in the resource-leveling orchestrator

Date: 2026-11-16
Reference: `79200d26f78b6c128273694aaa3cb25d9a8dbcab` (main after P0-A..P0-D)
Optimized: the P0-E working tree

Both sides ran the identical fixture and CLI code. The reference side used a
detached worktree at `79200d26` with only
`src/construction_pm/scheduling/benchmark_fixtures.py` and
`scripts/scheduling_core_benchmark.py` copied in, so the scheduling engine
itself was untouched. Every pair below is a contemporaneous measurement on the
same host.

## What changed

`schedule_with_resource_leveling` performs a sequence of CPM passes that differ
only in their ordered constraint tuple; every other argument is the same local
variable. Three of those passes were provably identical duplicates:

1. the intermediate pass repeats the initial pass when forward leveling
   proposed no positive shift (`forward_leveling_constraints` drops zero-day
   shifts, so the merged constraint tuple is the base tuple);
2. the closing pass repeats the intermediate pass when no backward shift was
   accepted, or when backward leveling is disabled by
   `preserve_scheduled_early_and_late_dates`;
3. the closing pass repeats the last *accepted* candidate trial when that
   candidate's constraint set is exactly the final set.

Each duplicate is replaced by reuse of the already computed `ScheduleResult`.
The final `_validate_final_resource_load` still runs on whatever result is
returned, so final CPM validity and final resource-capacity validation are not
weakened. No schedule option, calendar rule, relationship rule, float value or
leveling decision changed.

## Measured pass counts

The forward-only orchestration fixture has no relationships, every activity
starts on the project start day, and each holds 4 units of one resource for two
working days against a daily capacity of 8. The project finish is
`max(20, 2n + 10)` working days after the early finish, so every activity has
enough float and the orchestrator resolves without an overload error.

| Activities | Forward shifts | Backward shifts | CPM passes (reference) | CPM passes (optimized) | Canonical hash |
|---|---|---|---|---|---|
| 20 | 18 | 0 | 3 | 2 | `d23faac45ef0…` (both) |
| 50 | 48 | 0 | 3 | 2 | `a43f0cd7a8b2…` (both) |
| 100 | 98 | 0 | 3 | 2 | `a3da54e11ce8…` (both) |

## Measured wall time

Median of 3 runs after 1 warm-up, in ms. `single CPM` is one authoritative CPM
pass on the same fixture, measured separately, which bounds what one removed
pass can be worth.

| Activities | Reference | Optimized | Gain | Single CPM pass |
|---|---|---|---|---|
| 20 | 24.541 | 22.989 | 6.3% | 1.863 |
| 50 | 293.177 | 284.480 | 3.0% | 9.315 |
| 100 | 2,172.426 | 2,147.145 | 1.2% | 33.400 |

Peak RSS: 48–53 MB, unchanged within noise. The gain is bounded by the removed
pass: the remaining orchestration time is the forward leveling decision
schedule, which is quadratic in the number of activities (the one-shift-per-
iteration schedule described in the P0-D evidence), so the relative benefit
shrinks as the fixture grows.

## Backward-acceptance scenario

A two-activity SS case where one backward move is accepted performs **5** passes
on the reference engine and **3** on the optimized engine, with identical
published result. The count is asserted in
`tests/scheduling/test_leveling_cpm_reuse.py`, which also pins:

- the returned result equals a fresh `schedule()` call with the derived final
  constraint set (dates, finish, total and free float);
- the closing pass is not repeated;
- an orchestration with no shift at all performs a single CPM pass;
- `_validate_final_resource_load` still receives the returned result.

## Not measured

- Backward-acceptance orchestration at scale: the fixtures that force many
  accepted backward moves also expose the one-shift-per-iteration cost and did
  not converge at 50+ activities without a capacity profile tailored to the
  proposal order. No such number is claimed.
- Python 3.11 / 3.13 and PostgreSQL concurrency: CI only.
- Worker counts and queue metrics: not implemented (P0-F/P0-G).
