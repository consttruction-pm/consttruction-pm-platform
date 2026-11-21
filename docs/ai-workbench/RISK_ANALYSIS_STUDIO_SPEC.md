# Risk Analysis Studio — Specification

Status: **PARTIAL**. The risk register (`risk_api.py`, `risk_application.py`,
`workspace-risks.ts`) is real and can be reused. Quantitative methods have no
validated analysis service; they must not run in the browser or fabricate
distributions.

## Six tabs

1. **Risk Overview** — counts by severity/status/category, top risks, exposure
   coverage, stale or unowned risks.
2. **Risk Register** — the fields in #2090 (id, title, category, cause, event,
   effect, affected WBS/activity, probability, schedule/cost/quality/safety
   impact, inherent/current/residual rating, owner, response, trigger, due date,
   status, evidence, revision). Filters by all scoped dimensions.
3. **Risk Matrix** — 3×3, 5×5 and configurable probability/impact matrix;
   heatmap and distribution; clicking a cell filters the register.
4. **Quantitative Analysis** — EMV, three-point/PERT, Monte Carlo, sensitivity
   and tornado, P50/P80/P90. Each method requires validated inputs, records
   assumptions and seed, and states its limitations. Without inputs it returns
   `INSUFFICIENT_DATA` or `CALCULATION_BLOCKED`.
5. **Response Planning** — avoid/mitigate/transfer/accept/exploit/enhance/share
   where applicable; action, owner, due date, budget, expected impact, residual
   risk and reassessment.
6. **History & Decisions** — revisions, rating changes, evidence and decisions.

## Links to schedule

A risk may reference a WBS node, activity, milestone or resource only when the
identifier exists in the authoritative project read. Navigation Risk↔Gantt must
use the same scope and highlight the object. No inferred links.

## Permissions

Read: project read. Write: project risk write. Quantitative run and response
approval use separate permissions; a viewer sees the register and matrix but no
write or run control.

## Help

EPPM risk topics are the primary source where they exist; CUBI-only quantitative
methods must be labelled CUBI Extension with the method reference recorded in
`ENGINEERING_AI_WORKBENCH_HELP_MATRIX.md`. Exact URLs remain
`HELP_REFERENCE_PENDING` until opened and recorded.

## Acceptance

Register create/edit/filter/rating works; matrix filters the register; links
resolve to real activities; responses and residuals persist; quantitative
results appear only from a validated service with recorded inputs.
