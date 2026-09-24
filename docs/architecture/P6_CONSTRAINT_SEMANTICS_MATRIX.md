# P6 Constraint Semantics Matrix — Stage 33.4.21

Date: 2026-09-24

This matrix defines the Shared Scheduling Core contract for the currently implemented activity-date constraints. It is a compatibility baseline for P6-style scheduling behavior; it is not a claim of formal Oracle certification.

| Constraint | Forward Pass | Backward Pass | Relationship interaction | Validation |
|---|---|---|---|---|
| Start No Earlier Than | Raises earliest start | Does not move late dates | Reduces float; early schedule must remain feasible with FS/SS/FF/SF and lag/lead | Early Start >= target |
| Start No Later Than | Does not move an already-earlier start; rejects if exceeded | Lowers latest start | Relationship-driven late dates may make schedule infeasible | Start <= target |
| Finish No Earlier Than | Moves start so finish reaches target | Does not move late dates | Reduces float; early schedule must remain feasible with all relationship types | Early Finish >= target |
| Finish No Later Than | Rejects finish beyond target | Lowers latest start | Relationship-driven dates may make schedule infeasible | Finish <= target |
| Mandatory Start | Forces exact start unless predecessor logic makes it impossible | Forces exact start unless successor/project finish logic makes it impossible | Exact relationship feasibility is required | Start == target |
| Mandatory Finish | Forces exact finish unless predecessor logic makes it impossible | Forces exact finish unless successor/project finish logic makes it impossible | Exact relationship feasibility is required | Finish == target |

## Calendar semantics

Constraint dates are normalized through WorkingTimeResolver. Non-working target dates therefore resolve to the applicable working boundary rather than introducing a second calendar implementation.

## Combined constraints

Before either CPM pass, validate_constraint_set() checks contradictory start lower/upper windows, contradictory finish lower/upper windows, conflicting mandatory start dates, conflicting mandatory finish dates, mandatory start/finish versus activity duration, and cross start/finish windows.

After scheduling, constraint windows are validated against the actual scheduled dates.

## Relationship semantics

The authoritative relationship types remain FS, SS, FF, and SF. Lag is working-day based. Positive lag creates separation; negative lag is lead. Forward and backward passes must use the same relationship semantics.

## Backward-pass rule

A backward schedule is valid when late-date constraints applicable to the backward pass are satisfied, latest dates do not exceed project finish, every relationship remains feasible, and activity duration remains unchanged. P6 Start/Finish No Earlier Than constraints are early-date constraints and therefore are not required to hold against late dates; they can reduce total float and can produce negative total float. Mandatory constraints apply to both early and late dates.

## Pending P6 parity work

Still pending before claiming full P6 parity: comprehensive constraint-option comparison against documented P6 behavior; richer time-of-day/calendar semantics; exact schedule-option parity; formal parity test pack and certification evidence.

This matrix is a Shared Core specification and must not be reimplemented independently by Web, Desktop, or Mobile clients.


## Stage 33.4.25 P6 semantic correction

2026-09-24: Oracle P6 documentation confirms that Start On or After and Finish On or After affect early dates, while Start On or Before and Finish On or Before affect late dates. Mandatory Start/Finish constrain both early and late dates. The Shared Core now follows this scope instead of propagating lower-bound constraints through the late network. P6 also permits negative total float; negative float is reportable and critical under the default zero threshold rather than being rejected as an invalid schedule. citeturn1search1turn2search3turn2search2
