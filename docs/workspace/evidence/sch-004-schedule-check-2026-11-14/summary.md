# SCH-004 Schedule Check and diagnostics — 2026-11-14

- **Tested code:** `8948bff4` (`feat(schedule): expose authoritative schedule check conditions`, PR #1970).
- **Requirement:** the Schedule Check surface must evaluate the documented schedule conditions against the authoritative calculation result, report a fixed rule catalogue with severities and counts, and let the user drill through from a finding to the affected activity — without recomputing CPM, float or constraints in the browser.

## Audit before the change

- `src/construction_pm/scheduling/diagnostics.py` already defined `ScheduleDiagnosticCode`, `INFEASIBILITY_MATRIX` and `ScheduleInfeasibilityError`, and the CPM result carried negative-float and infeasibility diagnostics.
- `backend_p0/authoritative_schedule_query.py` exposed the diagnostics in the FACT and EXPLANATION responses, but there was **no rule catalogue**, **no counts**, and **no UI**. `apps/web/src/schedule-cycle.ts` rendered the run-results table only, so a user could not see open ends, constraints or negative lags as a checkable list.
- The rule set itself existed only implicitly: open ends were derivable from relationship endpoints, constraints from the stored composer input, and negative lag from relationship lags. No single contract described the six conditions or their severities.

## Change

- **Core (`src/construction_pm/scheduling/schedule_checks.py`, new):** introduces `ScheduleCheckRuleId` with exactly six rules — `NEGATIVE_FLOAT`, `OPEN_START`, `OPEN_FINISH`, `ACTIVITY_CONSTRAINT`, `MANDATORY_CONSTRAINT`, `NEGATIVE_LAG` — and the fixed severity catalogue (`WARNING`, `WARNING`, `WARNING`, `INFO`, `WARNING`, `INFO`). `evaluate_schedule_checks(source, *, date_result=None, time_result=None)` derives predecessor/successor presence from the source relationships, excludes `WBS Summary` and `Level of Effort` from open-end checks, classifies non-mandatory constraints as `ACTIVITY_CONSTRAINT` and `MANDATORY_START`/`MANDATORY_FINISH` as `MANDATORY_CONSTRAINT`, reports negative lags and negative total float, and sorts findings deterministically by catalogue order then identity. `ScheduleCheckFinding` is a frozen dataclass with `to_payload()`.
- **Payload (`build_schedule_check_payload`):** `p6-schedule-check.v1` (`kind: "schedule_check"`) with `scope`, `snapshot_id`, `snapshot_hash`, `calculation_run_identity`, `counts` (`total`/`ERROR`/`WARNING`/`INFO`), a `rules` array that includes zero-count rules, and the ordered `findings`.
- **Evaluator (`src/construction_pm/schedule_evaluator.py`):** `ScheduleEvaluationResult` gains `schedule_check_findings`, populated from the date or time calculation result, so the check is a projection of the same authoritative run.
- **Query (`src/construction_pm/backend_p0/authoritative_schedule_query.py`):** `_schedule_check_payload` binds the tenant/project/revision scope and the snapshot identity, and the block is added to the date and time FACT and EXPLANATION responses. The FILTER response is unchanged.
- **Web (`apps/web/src/schedule-cycle.ts`):** typed `ScheduleCheck` parsing validates contract/kind, scope, counts, severities, non-negative integer counts and string details; absent or older blocks return `null` while malformed blocks throw. `renderScheduleCheck` renders the counts, one row per rule (including zero counts), the findings list and a focus button per finding. `renderScheduleRunResult` appends the section after the results table, and `mountRunPanel` wires `data-check-focus` to the matching grid row (`click()` + `scrollIntoView`). English and Persian labels cover the title, counts, rule/severity columns, findings and the six rule names.
- **E2E (`apps/web/e2e/preview-e2e.mjs`):** after the constrained run it waits for `[data-schedule-check]`, reads the six rule rows and asserts `total` equals the sum of counts and that `A140` appears as an `ACTIVITY_CONSTRAINT` finding. After the constraint is deleted and the schedule rerun, it asserts the six rules are present, the total still equals the sum, `NEGATIVE_LAG` is `0`, `OPEN_START` names `A100`, `OPEN_FINISH` names `A210`, no constraint findings remain, then clicks `[data-check-focus="A100"]` and waits for that grid row to become `aria-selected="true"`.

## Browser proof

Recorded check `schedule check lists conditions, counts and drills through to an activity` at `8948bff4`:

1. The run-results panel renders a `data-schedule-check` section bound to the published snapshot.
2. Final rerun after deleting the constraint: six rules with severities `NEGATIVE_FLOAT 0 / OPEN_START 1 / OPEN_FINISH 2 / ACTIVITY_CONSTRAINT 0 / MANDATORY_CONSTRAINT 0 / NEGATIVE_LAG 0`, total `3`.
3. The open-start finding names `A100` and the open-finish findings include `A210`; `A170` is the other open finish.
4. Clicking the `A100` focus button selects the matching activity grid row and scrolls it into view.
5. Screenshot `07i-schedule-check.png` was captured. The schedule panels are clipped/hidden in the P6 shell preview (the same limitation recorded for SCH-001/SCH-002 screenshots), so the DOM assertions in `evidence.json` are the authoritative proof.

Full run at `8948bff4`: 101/101 checks, 55 screenshots, zero uncaught exceptions and zero API 5xx.

## Unit and server coverage at the same code

- `tests/scheduling/test_schedule_checks.py` (new, 6 tests) — WBS Summary/Level of Effort exclusion, mandatory vs non-mandatory classification, negative lag and negative float, time-aware negative float, zero-count rules and count consistency in the payload, stable empty input.
- `tests/test_authoritative_schedule_query.py` — the negative-float FACT and EXPLANATION now assert the `p6-schedule-check.v1` block, expected counts and per-rule counts, and the finding order for the affected activity.
- `apps/web/src/schedule-cycle.test.ts` (3 tests) — valid document parsing with scope `P-1@4`, absent block returns `null` and invalid severity throws, and markup with counts, zero-count rules, findings and the `A100` focus button plus constraint evidence.
- Python `4329 passed, 204 skipped`; Web `1165 tsx` + `15 node --test`; `tsc` and esbuild clean.

## Evidence in this bundle

- `evidence.json` — full suite result at `git_head` `8948bff4dec014dcab18fcdc859b4e15ffeaf3b7`, 101 checks, 55 screenshots, with the `schedule_check` block (six rules, total 3, `A100` open start, `A210` open finish, zero constraint findings after delete, `A100` drill-through).
- `07i-schedule-check.png` — captured run with the schedule check section (panel clipping noted above).

## Limits

- **Bounded rule set.** The catalogue covers the six conditions the authoritative core can evaluate today. The external Version 26 rule catalogue and any additional checks require a licensed V26 schedule export and are `BLOCKED_EXTERNAL`.
- **No separate docked Schedule Check window.** The check renders inside the Schedule window's run-results panel rather than as its own docked window/tab; the data and drill-through are the same.
- Negative float remains a `WARNING` in the check layer, while genuine infeasibility still raises `ScheduleInfeasibilityError` in the calculation core; the check never suppresses that error.
