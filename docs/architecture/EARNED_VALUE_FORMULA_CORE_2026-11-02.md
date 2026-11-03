# Earned Value Formula Core — Reconciliation Record

Date: 2026-11-02
Paths: `src/construction_pm/scheduling/earned_value.py`, `src/construction_pm/resources/evm_bridge.py`
Tests: `tests/scheduling/test_earned_value.py`, `tests/resources/test_evm_bridge.py`
Status: arithmetic implemented and tested; source-value selection and Version 26 parity remain open.

## Implemented identities

- CV = EV - AC and SV = EV - PV.
- CPI = EV / AC and SPI = EV / PV, using Decimal arithmetic.
- ETC estimators are selected explicitly: Remaining Cost, PF = 1, PF = 1 / CPI, PF = 1 / (CPI * SPI), or a user-defined PF.
- EAC = AC + ETC and VAC = BAC - EAC.
- Results expose a canonical string/`None` snapshot for reproducible evidence.

## Explicit edge rules

- AC = 0 leaves CPI undefined (`None`); PV = 0 leaves SPI undefined. Undefined indices are never replaced with 0 or 1.
- A performance-factor estimator that needs an undefined or zero index fails closed (`EARNED_VALUE_COST_INDEX_UNAVAILABLE`, `EARNED_VALUE_SCHEDULE_INDEX_UNAVAILABLE`, `EARNED_VALUE_COST_INDEX_ZERO`, `EARNED_VALUE_SCHEDULE_INDEX_ZERO`).
- A performance-factor estimator rejects EV > BAC instead of emitting a negative ETC (`EARNED_VALUE_REMAINING_BUDGET_NEGATIVE`).
- Missing BAC, missing Remaining Cost, an unsupported estimator, a non-positive user PF and any non-finite or negative input fail closed.
- VAC is `None` without BAC; CV and SV remain defined.
- CPI-based ETC divides the remaining budget by CPI directly, so an exact quotient is not distorted by a rounded reciprocal.

## Still open

- Resolving EV, PV, AC and BAC from a selected baseline, Data Date, WBS percent-complete/EV technique and cost rollup is not part of this module and is not claimed.
- Currency conversion, financial-period boundaries, WBS technique overrides, manual future-period buckets and resource-curve methods remain unqualified.
- The existing native EV field inventory is typed read evidence only; it is not a calculation proof.
- No full Version 26 EVM parity claim is made.
