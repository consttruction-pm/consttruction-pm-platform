# ENT-13 — Commercial formula register

These are explicit CUBI policy formula specifications for the commercial read model. They are not asserted to be exact Unifier formulas until the relevant current-release Help topic and configured business process are crosswalked. Currency and rounding are configuration-bound and must be tested independently.

| Formula ID | Expression | Variables / sign convention | Unit | Rounding |
|---|---|---|---|---|
| ENT13-F01 | revised_contract_value = original_contract_value + sum(approved_change_values) | Only approved/effective changes; pending changes excluded | Contract currency | Currency minor unit, half-up |
| ENT13-F02 | pending_change_exposure = sum(pending_change_estimates) | Pending changes shown separately; never added to approved commitment | Contract currency | Currency minor unit, half-up |
| ENT13-F03 | remaining_sov = sum(sov_line_revised_amount - sov_line_certified_to_date) | Certified-to-date is cumulative and cannot exceed policy limits without exception | Contract currency | Currency minor unit, half-up |
| ENT13-F04 | current_net_certified = current_gross_work - retention - advance_recovery - deductions + tax | Each component is non-negative and separately evidenced; sign convention explicit | Contract currency | Currency minor unit, half-up |
| ENT13-F05 | certified_not_paid = certified_to_date - paid_to_date | Must not be negative; reconcile against finance/ERP | Contract currency | Currency minor unit, half-up |
| ENT13-F06 | retention_outstanding = retention_withheld_to_date - retention_released_to_date | Release is an approved commercial event | Contract currency | Currency minor unit, half-up |
| ENT13-F07 | forecast_final_contract_value = revised_contract_value + forecast_unapproved_scope | Forecast-only projection; not an approved commitment or liability | Contract currency | Currency minor unit, half-up |

## Ownership and verification

- Enterprise owns these commercial projection definitions and their provenance.
- Approved project cost/EVM, schedule and resource effects are delegated to Engineering; payment disbursement and accounting reconciliation are delegated to the designated finance/ERP owner.
- Currency conversion requires a named rate provider, rate date, source currency and target currency.
- Each formula requires independent expected-value examples, zero/negative/over-limit cases, duplicate event/revision tests and reconciliation tests before implementation-ready status.
