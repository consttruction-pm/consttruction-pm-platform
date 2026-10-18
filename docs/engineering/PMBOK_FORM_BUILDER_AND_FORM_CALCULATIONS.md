# CUBI PMBOK-Aligned Form Builder and Form-Calculation Contract

**Document ID:** CUBI-FORM-CALC-001  
**Status:** Mandatory engineering specification; implementation coverage remains open until mapped to source code and tests  
**نسخه فارسی همراه:** [قرارداد فارسی فرم‌ساز و محاسبات فرم](PMBOK_FORM_BUILDER_AND_FORM_CALCULATIONS_FA.md)  
**Initial issue date:** 2026-10-18  
**Reference baseline reviewed:** PMBOK® Guide — Eighth Edition (published November 2025; PMI's product page identifies an errata sheet for the second printing last updated April 2026), plus relevant current PMI practice guides and standards  
**Applies to:** CUBI website Form Builder, reusable form templates, form instances/submissions, calculated fields, form-specific rules, approvals, form-driven reports, exports and AI-assisted form creation.

## 1. Purpose and binding rule

This document defines the calculation, validation, data, workflow, user-interface and verification contract for the CUBI website's form-building area. It is not just a list of form names: it specifies how templates are modelled, how fields are typed, how user-selected calculations are defined and evaluated, how approval and audit state are retained, and how form data connects to project scope and the shared calculation services.

**Mandatory rule:** before creating, changing, reviewing or debugging the Form Builder, any calculated form field, a form template, a formula editor, a form workflow, a form-derived KPI/report, or an AI form-generation action, the contributor must read this contract and the relevant official source pages in Section 31. Cite the applicable section IDs and test IDs in the PR.

No contributor may:
- invent a formula and describe it as required by PMBOK;
- treat every suggested artifact as mandatory on every project;
- copy protected publication content as an implementation shortcut;
- add an independent schedule, calendar, resource, cost or EVM calculation inside the form UI;
- bypass typed validation, approval permissions or audit history; or
- report full compatibility before formula examples, field mappings, actual UI controls and tests have been independently verified.

## 2. What the latest PMBOK baseline means for CUBI

The official PMI PMBOK Guide page identifies the Eighth Edition, dated November 2025, with an errata sheet for the second printing last updated April 2026. PMI describes this edition as retaining a principles/performance-domain foundation, clarifying guidance and reintroducing process guidance in a non-prescriptive, adaptable form. It identifies six core principles and seven performance domains.

For CUBI, this means:
1. PMBOK is a **tailoring and artifact-design profile**, not a universal schema that every project must complete identically.
2. CUBI may offer ready-to-use templates and workflows associated with project management practices, but each project/organization can enable, tailor, rename, localize or deactivate items subject to governance and contractual needs.
3. A blank field, formula or form is not a substitute for project judgment, a technical approval or a contract requirement.
4. Form calculations that support a management decision must show their inputs, formula version, units, scale, assumptions and data freshness.
5. The PMBOK-aligned form layer must not change the separate CUBI scheduling/reference-calculation contract. Schedule dates, CPM, calendars, resource leveling and the canonical EVM values must come from their shared domain engines.

The six principles described by PMI are represented for design coverage as: holistic view; focus on value; embed quality; lead accountably; integrate sustainability; and build empowered teams. The seven performance domains named on the official PMBOK page are Governance, Scope, Schedule, Finance, Stakeholders, Resources and Risk. CUBI uses these as coverage tags and navigation groupings, not as a claim that every project must create seven specific documents.

PMI's 2026 Standard for Artificial Intelligence in Portfolio, Program and Project Management is a separate and newer source for AI-assisted forms. It describes eight guiding principles, five performance domains, human-in-the-loop review, ethical/legal guardrails, lifecycle guidance and tailoring. These become AI form-authoring governance requirements, not a substitute for validation or human approval.

## 3. Authority, source attribution and formula labels

### 3.1 Source precedence

1. Current official PMI publication/page for the selected edition and its official errata.
2. Applicable current PMI practice guide/standard for the specific technique (for example, scheduling, WBS, earned value, risk, estimating, requirements/business analysis or AI).
3. This CUBI contract and explicitly approved CUBI-specific policies.
4. Existing implementation and tests, to be inspected as evidence rather than blindly assumed correct.
5. Generic industry convention or developer intuition.

A specific formula appearing in a common technique is not automatically a mandatory PMBOK formula. The formula registry must say which category it belongs to.

### 3.2 Required formula authority classes

Every calculated field must carry one of these classifications in its metadata and audit view:

- **PMI-DOCUMENTED:** explicitly supported by the cited current official publication/page; the source rule is recorded.
- **CUBI-APPROVED TECHNIQUE:** a standard calculation method made available as a user-selected option; not falsely presented as a formula required by PMBOK.
- **PROJECT-CONFIGURED:** formula, scale, weights, units, tax/retention terms or threshold configured and approved by the project/organization.
- **REFERENCE-ENGINE:** value sourced from the shared CUBI scheduling, calendar, resource/cost, progress or EVM engine. The form must not recalculate it.
- **AI-PROPOSED:** draft formula or logic generated by AI; unusable in a published form until type-checked, tested and approved by an authorized human.
- **OPEN / PARITY-TEST REQUIRED:** current official sources or deployed reference behavior have not yet settled an edge case. It cannot be advertised as compatible until resolved.

### 3.3 Copyright and source handling

Create original CUBI form layouts and data models based on management concepts; do not copy large portions of copyrighted standards, proprietary template packs or paid publication content. Internal engineering records must retain links, edition, rule summary and verification state. User-facing CUBI labels should remain brand-neutral and explain the workflow in CUBI wording.

## 4. Main architecture and boundaries

Use the following separation:

- **Form Definition Core:** form schema, field metadata, repeatable sections, conditions, validation rules, formula references and definition versioning.
- **Shared Formula Core:** safe parsing, AST/type checking, units, dependency extraction, cycle detection and deterministic formula evaluation.
- **Domain Calculation Services:** canonical schedule/calendar/resource/cost/progress/EVM services; form formulas may read approved results but may not duplicate these engines.
- **Application/Workflow Layer:** template selection, submission creation, transaction boundary, authorization, transition checks, approval routing, recalculation orchestration and audit records.
- **Repository/Persistence:** stores immutable template versions, submissions, typed values, formula metadata, approval events, attachments and source snapshots.
- **API/DTO Layer:** validates contract, project/tenant scope and typed input, then returns canonical results; it must not implement business formulas.
- **Website UI:** form designer, preview, response entry, validation messages, calculation output, approval, history, print/export. UI is not an independent calculation engine.
- **Reporting/Export:** consumes canonical stored values and provenance; it does not reconstruct calculations from displayed strings.
- **AI Form Assistant:** proposes definitions and formulas, then calls the authoritative validator/evaluator through permission-scoped tools.

A form template that contains formulas must still function if rendered in a different supported language or layout. Website, desktop and future mobile must use the same definition version and calculation authority.

## 5. Form/template and submission data model

### 5.1 Immutable form template version

Each published template version must have:
- tenant and project/methodology scope (or explicitly global scope where authorized);
- stable template ID and immutable version number;
- stable field IDs that are not translated display labels;
- title/help/option translation keys and default locale;
- schema hash and contract version;
- status (draft, review, published, deprecated/retired);
- author, reviewer, publisher, timestamps and change reason;
- calculation/formula semantic version;
- fields, validation rules, conditions, formulas and explicit dependencies;
- workflow/approval definition version;
- output/report layout versions;
- permission policy, retention policy and attachment requirements;
- references to official/organizational sources where applicable and a formula-authority classification.

Publishing a changed formula or field structure creates a new immutable template version. Historical instances must remain readable using the schema/version that created them. Do not silently rewrite historical responses to the newest schema.

### 5.2 Form instance/submission

Each form instance stores:
- tenant ID, project ID and project revision/snapshot;
- template ID, immutable template version and schema hash;
- instance ID, form revision and idempotency key where needed;
- submission owner/author, created/updated dates and timezone context;
- status, approval state, responsible person, reviewers and final approver;
- field values in typed internal form rather than only formatted strings;
- calculated values and formula engine/semantic version;
- calculation inputs/snapshot hashes and affected-field dependency metadata;
- referenced activity/WBS/resource/contract/submittal/RFI/change/risk/issue IDs;
- attachments, evidence hashes, signatures/acknowledgement metadata and file version;
- comments, rejection reasons, workflow events and before/after audit history;
- locale used for entry/rendering, without using locale as a calculation input;
- stale/not-calculated/errors/warnings flags.

All writes must check authorization, tenant/project scope and optimistic revision. A stale client cannot overwrite a newer approved value silently.

## 6. Supported field types and exact meaning

The v1 inspection/quality/safety template contract currently defines only Boolean, Select, Text and Number inputs. That is useful as an initial template feature, but it is not enough to meet the full form-building scope. Expand by a new schema version; do not silently change the existing v1 JSON contract.

| Field type | Stored value | Required validation/behavior |
|---|---|---|
| Text | Unicode string | Length, allowed characters/pattern, sensitive-data marking, normalization policy. |
| Long text/rich text | Structured/sanitized content | Safe markup policy, length, multilingual text, no untrusted executable HTML. |
| Boolean | true/false or null | Null is different from false until a default/answer is supplied. |
| Single choice | Stable option ID | Options have stable IDs and separate translated labels; reject unknown/retired IDs unless an approved historical case. |
| Multi-choice | Set/list of option IDs | Reject duplicates; deterministic storage order; min/max selections. |
| Integer | Exact integer | Reject Boolean-as-integer; min/max and integer precision. |
| Decimal/Number | Exact decimal | Unit, precision, rounding boundary, min/max, null and denominator rules. Never use floating-point for financial values. |
| Percent | Canonical decimal ratio or explicitly typed percentage | Store one canonical form, e.g. 0.25 means 25%; display percentage separately; validate expected range but do not silently clamp values. |
| Currency/Money | Decimal amount + ISO currency identity | Never add different currencies without explicit approved conversion; native amount and converted amount remain distinguishable. |
| Quantity | Decimal + unit-of-measure ID | Unit identity and conversion are explicit; no assumed factor of 1. |
| Duration | Typed duration + unit + calendar/time context when working time is meant | Calendar-aware calculations use the shared calendar service; elapsed time and working time are different concepts. |
| Date | Date-only value | No accidental timezone shift from a date-only field. |
| Date/time | Timezone-aware timestamp | Persist a normalized instant plus applicable zone/context; presentation timezone does not change elapsed results. |
| Person/team/organization | Stable entity ID | Validate project/tenant membership and permissions at submit/approve time. |
| Project entity reference | Stable project/activity/WBS/resource/contract/etc. ID | Validate referenced entity still exists, belongs to allowed scope and has the required revision/status. |
| File/evidence | Attachment ID, hash, media type and metadata | Malware scanning, access control, immutable or versioned evidence, no silent replacement of approved attachments. |
| Signature/acknowledgement | Typed actor, action, timestamp and integrity reference | A checkbox alone cannot be represented as a legally valid signature unless configured workflow/contract authorizes that meaning. |
| Repeating section/table | Ordered child records with stable row IDs | Row-level formulas and aggregate dependencies; deterministic row order; add/remove operations recalculate dependents. |
| Formula/calculated field | Computed typed value | Read-only by default; no direct user overwrite of derived result; formula version/result status preserved. |
| Read-only external/engine field | Canonical source reference + copied snapshot value if needed | Identify source service, source revision/time and stale conditions; never shadow-calculate. |

### 6.1 Stable identifiers and translations

Field IDs, option IDs, formula IDs, unit IDs and workflow-state IDs remain stable across locales. Translated text is a display layer. Do not use a translated label as the formula dependency key, database key or external-reference key.

## 7. Form validation contract

Validation is performed at definition publication, entry/update, calculation, submission, approval and export boundaries as appropriate.

Supported validation classes must include:
- required when visible/applicable;
- data type and schema version;
- minimum/maximum, allowed values, text pattern and length;
- uniqueness within the proper project/template/form scope;
- conditional visibility, conditional requirement and conditional editability;
- cross-field conditions and chronology rules;
- foreign/entity reference existence and scope;
- unit/currency compatibility;
- formula result type and declared output unit;
- attachment count/type/size/evidence requirements;
- workflow transition and approval-role constraints;
- project revision/stale value checks;
- date/time zone and calendar context;
- numeric precision and explicit rounding;
- permission/access/segregation-of-duties checks.

A field that is hidden by a condition should be treated according to a declared policy (ignored, cleared or retained but excluded); the engine must never infer the behavior. Every template must state the policy because it affects completion percentage, validation and audit.

Errors must be machine-readable (stable error code, field ID, source formula/condition and context) and rendered in accessible localized text. Do not swallow validation errors or convert them into a successful submission.

## 8. Formula and conditional-rule language

### 8.1 Safe formulas only

Formula text is parsed into a typed expression tree. Arbitrary Python/JavaScript/SQL, reflection, filesystem/network operations, dynamic imports, eval/Function, custom unsafe code, and hidden calls to external services are prohibited. A published formula must identify its dependencies, result type/unit, semantics version and authority classification.

The current canonical Shared Formula Core documents these known function IDs: IF, SUM, MIN, MAX, ABS, ROUND, COALESCE, NOT, AND and OR. The formula compatibility registry also records selected verified source-dialect aliases. These are the current documented support boundary, not a promise that every function from Excel, a schedule product or another formula language is implemented.

Any additional function (including date/calendar functions, risk functions, currency conversion, lookup, regular expression or statistical distribution function) needs its own specification, type signature, unit/null/error behavior, source evidence and tests before being offered in the UI.

### 8.2 Expression characteristics

Every formula definition includes:
- formula ID/version and source expression;
- output field ID, declared type and unit;
- source dialect (canonical or explicitly supported import dialect);
- field/formula dependency IDs;
- decimal precision/rounding rule;
- null and divide-by-zero behavior;
- allowed numeric range where meaningful;
- authority class/source references;
- deterministic engine version;
- validation examples and expected outputs;
- author/reviewer and immutable audit record.

### 8.3 Conditions are not approvals

Conditions may control field visibility, requiredness, enabled state, validation, notification routing or proposed workflow destination. They must not bypass role authorization or automatically approve a form solely because a calculated score crossed a threshold. If organization policy explicitly allows rule-based approval, model it as a workflow policy with named authority, version, trace and override process—not as a hidden formula side effect.

## 9. Numeric precision, nulls, errors, and units

### 9.1 Arithmetic and precision

- Use Decimal/exact decimal arithmetic for monetary amounts, cost, quantities, percentages and weighted metrics where applicable.
- Keep canonical internal values separate from formatted values.
- Store unit/currency identity alongside values.
- Apply ROUND only at declared output boundaries; do not round every intermediate calculation.
- Round-trip input/output without locale-dependent numeric conversion errors.
- Reject NaN, Infinity, malformed decimal inputs and incompatible units.

### 9.2 Null and zero

A blank numeric answer, a known zero, “not applicable”, “not yet measured”, “withheld” and “not calculated” are not the same. Preserve null reason/status when relevant. Sum, average, score and percent formulas must have explicit missing-value policies. A zero denominator must yield an explicit not-calculable status or a documented conditional result; it cannot silently become zero or 100%.

The existing Shared Formula Core documents that its rollup SUM/MIN/MAX ignores null children and returns null when no value is present. Form-specific aggregate definitions must either use this existing behavior or document and test an explicitly different behavior.

### 9.3 Units

The existing unit-semantics document specifies compatible units for addition/subtraction and compositional dimensions for multiplication/division/powers; symbolic units do not perform actual currency or physical-unit conversions. Therefore:
- quantity conversions use an explicit approved unit-conversion service;
- currency conversions use an explicit dated rate/source and audit event;
- working-duration/date formulas use the authoritative calendar/duration service;
- EVM and schedule fields use the canonical engine output and declared units;
- no form formula may infer a conversion merely from the field label.

## 10. Formula dependencies and recalculation lifecycle

On a change to an input or referenced entity:
1. Authenticate and validate scope/revision.
2. Store the typed working value in a transaction or calculation context without prematurely publishing partial results.
3. Evaluate changed field constraints.
4. Discover the transitive closure of formulas depending on the changed field/formulas.
5. Reject dependency cycles with a trace of formula/field IDs.
6. Recalculate only affected formula fields in deterministic topological order; deterministic tie order is required.
7. Feed each valid output into downstream formulas.
8. Validate result type, unit, allowed range and field-specific invariants.
9. If any required formula fails, return a typed calculation failure; do not expose a partially updated formula set as fully valid.
10. Persist calculation outputs/provenance atomically with the form revision where applicable.
11. Mark other results stale if their source project/activity/WBS/calendar/cost/EVM snapshot changed.
12. Record audit/result hash and return the authoritative calculation status.

A formula depending on an external project field remains a dependency even when that field is not itself a formula node. Formula evaluation order and results must be reproducible for identical definitions, values, revision/context and engine version.

## 11. Canonical calculation context and project integration

Every form calculation must say whether its values come from:
- local user-entered form data;
- a formula over form values;
- a project/entity field snapshot;
- a canonical domain-calculation result;
- an external approved integration;
- a user-configured technique;
- an AI-proposed value awaiting review.

The calculation context should include tenant/project/revision, form/template versions, locale presentation context, unit/currency context, source entity IDs/revisions, data date or relevant period when a time-sensitive value is shown, formula semantic version, engine version and calculation timestamp.

If a form reads scheduled dates, duration, float, progress, assignment units, capacity, budget at completion, PV/EV/AC or other canonical scheduling/EVM output, read it through the approved API/result snapshot. **Never implement an alternate CPM/EVM/capacity formula in the form layer.** The dedicated CUBI scheduling/calc contract and its canonical services remain the source for those concepts.

## 12. Form-builder template lifecycle

The website form designer must support:
- create new template, clone existing template, import a supported schema, and select a blank/template starter;
- add/remove/reorder fields and sections with stable IDs;
- repeatable detail tables and attachments;
- labels, localized help, examples, units and display formats;
- default values, requiredness, conditional visibility/editability and dependency rules;
- formula editor with type/result-unit/dependency preview and validation;
- option lists with stable values and translated labels;
- field-level and cross-form/entity validation;
- preview for desktop/mobile widths, RTL/LTR, all enabled languages and print/export output;
- draft/review/publish/deprecate/rollback template-version flow;
- comparison/diff of template and formula versions;
- sample calculations with fixed inputs and expected outputs;
- access/approval matrix and signature/evidence configuration;
- change impact list for fields that affect formulas, reports, APIs and existing form instances;
- audit history, copy/export/import, and template usage inventory.

Publishing a template must fail if it contains unsupported formula syntax, invalid field/type references, dependency cycles, missing translations required by the project's language policy, broken options, undeclared unit conversions, unsafe conditions, invalid approval paths, or missing regression fixtures for a changed formula.

## 13. Core form field examples and semantics

Use these as canonical examples for the implementation registry:
- project charter: project purpose, value/benefit hypothesis, measurable outcome, sponsor, authority, key assumptions/constraints and approval state;
- requirements: requirement ID, source, business rationale, priority, owner, acceptance criterion, verification method, trace to deliverable/test, change history and status;
- change request: request ID, origin, description/reason, impacted scope/WBS/activity/contract, cost/schedule/resource/risk/quality/safety/sustainability impact, alternatives, recommendation, decision, approver, baseline/revision and implementation verification;
- risk/opportunity: cause-event-effect, category, probability scale, impact dimensions, risk owner, response, trigger, residual risk, response cost, review date and status;
- issue/action/decision: item ID/type, description, priority/impact/urgency, owner, due date, dependencies, decision/options, action link, state, closure/evidence and audit;
- cost estimate: estimate basis/method, WBS/control account, quantities, rate/currency, low/most-likely/high, assumptions, estimate date, confidence range if applicable, exclusions, contingency/management reserve separation and reviewer;
- inspection/quality/safety: location/work package, requirement/spec reference, criteria, observation/result, evidence, defect/nonconformance class, severity, responsible party, corrective/preventive action, due date, reinspection and closure approval;
- procurement evaluation: vendor, mandatory gate results, weighted criteria, scores/evidence, risk/clarification, normalized score, approval and conflict-of-interest statement;
- payment/quantity: contract/BOQ item, approved quantity, prior certified quantity, current measured quantity, cumulative quantity, contract rate, retention/advance/tax/adjustment rules, supporting evidence and approval;
- acceptance/handover/closeout: deliverable, acceptance criteria, evidence, exception/defect list, approval/waiver, owner, transfer date, warranty/maintenance handover, residual risks and closure decision.

These fields are original CUBI data-design examples, not a claim that PMBOK mandates a single form layout. Projects must tailor fields and workflows to their contracts, organization, development/delivery approach and risk.

## 14. Form catalog and domain coverage

The form catalog must cover, at minimum, the following logical artifacts. They may appear as separate templates, a configurable bundle or a reusable record type; they must not be forced onto every project.

| Form family | Required field groups | Typical calculations/derived fields | Authority classification |
|---|---|---|---|
| Project Charter / Value Case | goal, need, outcomes, sponsor, stakeholders, assumptions, constraints, authority, decision | value metric baseline/target/gap where configured; completeness/approval readiness | PMI-guided structure; project-configured measures |
| Assumptions/Constraints/Dependencies | ID, statement, category, owner, due/review date, status, impact if false, related entity | age/due status, affected item counts | CUBI workflow |
| Requirement / Traceability | ID, source, rationale, priority, acceptance criterion, verification, target WBS/deliverable, status | coverage = accepted/tested requirements ÷ applicable requirements under a selected definition; orphan/incomplete trace count | PMI-guided; defined calculation policy |
| WBS / Work Package / Deliverable Acceptance | WBS ID, control account, deliverable, package owner, acceptance criteria, weight, status, evidence | weighted progress and accepted-quantity totals under selected policy | WBS practice guidance + CUBI policy |
| Schedule Review / Milestone Status | milestone/activity references, actual/forecast dates, variance explanation, action | schedule/float/forecast values from shared scheduling service only | REFERENCE-ENGINE |
| Cost Estimate / Budget | estimate method, quantities, rate, currency, range, assumptions, approvals, baseline reference | line amount, totals, estimate range and variance under explicit method | PMI estimating guide + configured policy |
| EVM/Progress Status | baseline, period, PV, EV, AC, BAC, ETC, EAC, metrics and explanation | canonical EVM outputs from shared domain service | REFERENCE-ENGINE |
| Risk / Opportunity Register | cause-event-effect, probability/impact scales, owner, response, triggers, residual and status | qualitative score, EMV and portfolio totals only as selected | PMI risk guide + project-configured scales |
| Issue / Action / Decision Log | type, impact, urgency, owner, due date, options, decision, closure | age/overdue working time, status/priority counts; no hidden auto-approval | PMI-guided record design + CUBI policy |
| Change Request / Change Log | reason, scope/dates/cost/resources/risk/quality impacts, alternatives, decision | deltas and revised forecast from canonical services; direct cost line calculations from approved values | PMI-guided governance + CUBI workflow |
| Stakeholder / Engagement | stakeholder, role, interests, power/influence if configured, concern, response, owner, review | configured score/coverage; no universal mandatory score formula | PMI-guided + project-configured |
| Communication / Meeting / Action | audience, message, channel, date, decisions, actions, owners and due dates | completion, overdue and action counts | CUBI workflow |
| Procurement / Bid Evaluation | mandatory gate, criteria, weights, score, evidence, evaluator, conflict and decision | weighted score only under approved model; eligibility gates precede score | PMI procurement domain + project policy |
| Quality Inspection / NCR / CAPA | spec, inspected quantity, criteria, finding, severity, correction, cause, due date, reinspection | pass/defect rates, optional configurable failure-mode score | quality practice + optional technique |
| RFI / Submittal / Site Instruction | contract/spec/drawing link, query/submittal, responsible party, response/due dates, revision, decision, schedule/cost impact | overdue worktime, approved cost deltas and schedule impacts from domain services | Construction-specific CUBI extension |
| Daily Report / Safety Observation / Field Assurance | date/shift/location, crew/equipment/weather, quantities, incidents/observations, evidence, reviewer | sums by shift/period; measurable progress with accepted quantities | Construction-specific CUBI extension |
| Quantity Measurement / Payment Application | BOQ, quantity, rate, period, prior quantity/value, current value, approved adjustments, retention/tax/advance and approval | gross, cumulative, deductions, net due and reconciliation | Contract-configured CUBI extension |
| Lessons Learned / Acceptance / Handover / Closeout | lesson, cause, impact, recommendation, owner, evidence, deliverable acceptance, residual items | action closure and evidence completeness | PMI-guided + project policy |
| Form Template / Approval Audit | version, author, approver, criteria, formula/test versions, decision history | completeness/readiness counts, audit coverage | CUBI governance |

This table is a minimum catalogue. Every actual website template and form control must be inventoried in Section 29 before claiming completeness.

## 15. Canonical general formulas for form fields

These formulas are available as explicit techniques, not automatically applied to every field named “progress,” “risk,” “priority” or “score.” Each instance must declare its method, inputs, units, rounding and missing-value behavior.

### 15.1 Ratio percentage

For an applicable numerator N and denominator D:

Percent = 100 × N / D.

Preconditions: N and D have compatible units and D > 0. When D = 0, the result is not calculable unless a separately approved business rule defines the case. Do not auto-return 0 or 100. Preserve unrounded ratio internally; display rounding is separate.

Example: 42 accepted items of 60 applicable items: 100 × 42 / 60 = 70%.

### 15.2 Weighted average/weighted completion

For values x(i) and non-negative weights w(i):

Weighted Value = Σ(w(i) × x(i)) / Σw(i).

Conditions: all x(i) must use a compatible scale; the weight source and denominator population must be declared; zero total weight is not calculable; null child policy must be named. Percentages must be represented consistently (all ratios or all percentage points). If a child weight is BAC, quantity, criticality or a manually assigned value, record that choice in formula metadata.

Example: weights 60 and 40, progress values 80% and 50%: (60×0.80 + 40×0.50) / 100 = 68%.

### 15.3 Change magnitude/percent change

Delta = New Approved Value − Baseline Value.

Percent Change = 100 × Delta / Baseline Value if Baseline Value ≠ 0.

This is a comparison metric, not a project schedule re-calculation. For zero baseline, return not-applicable/undefined with reason. Do not treat a negative value as positive by taking ABS unless the selected metric expressly calls for magnitude.

### 15.4 Complete-field ratio

Required-field completion ratio = number of visible/applicable required fields that pass validation ÷ total visible/applicable required fields × 100.

Hidden/not-applicable fields are excluded only under the template's explicit condition policy. Approval fields must not be counted as completed before the required authorized approval event exists. A high completeness percentage cannot bypass blocking validation.

## 16. Risk and opportunity form calculations

### 16.1 Qualitative probability-impact score

If the project configures ordinal scales with probability rating P and impact rating I:

Qualitative Score = P × I.

This is a selected scoring convention, not a universal numerical formula mandated by PMBOK. The template must specify:
- probability scale and all labels/definitions;
- impact dimensions (for example cost, schedule, scope, safety, quality, environment, reputation) and the rule for combining them;
- whether the overall impact score uses maximum, weighted average, or a project-selected dimension;
- heat-map thresholds and response priority mapping;
- how missing ratings and “not applicable” are handled;
- how opportunities (positive uncertainty) differ from threats.

Ordinal scores are ranking aids, not monetary expectations. A product of 4×5 is not a 20-unit monetary loss.

### 16.2 Expected Monetary Value (EMV)

When probability is a calibrated number p from 0 to 1 and the impact is a monetary amount with explicit currency:

EMV = p × Monetary Impact.

Use positive impact magnitude and a separate signed convention or type (Threat/Opportunity) to prevent double-negation. Example: p = 0.25 and cost impact = 100,000 USD gives threat expected-cost magnitude = 25,000 USD; the project's threat/opportunity sign policy determines whether the signed portfolio term is −25,000 or +25,000. Record response cost separately; a net expected value may be calculated only when the model explicitly includes it.

For a list of risks, ΣEMV is valid only as the selected expected-value aggregate and must warn that dependencies, correlated risks, mutually exclusive scenarios and double counting can make simple addition inappropriate. A probability-impact score cannot be substituted for EMV.

### 16.3 Risk response and residual risk

- Inherent score and residual score are distinct snapshots before/after response.
- Response effectiveness is only quantified if the selected model defines its denominator and meaning (for example, reduction in expected monetary impact or change of configured ordinal score).
- Risk owner, response action, due date, trigger, response cost, residual risk, approval and review date remain required governance fields as configured.
- “Risk closed” requires an explicit authorized status transition and evidence/reason; a low score alone does not close it.

Required tests: probability boundary 0 and 1, monetary zero/negative entry validation, missing dimensions, threat/opportunity sign, currency mismatch, response cost excluded/included by selected model, residual re-evaluation and duplicate/dependent risk aggregation.

**Sources:** current PMI Risk Management in Portfolios, Programs, and Projects: A Practice Guide (First Edition, current guide surfaced in the PMI standards catalog; updated content announced in 2024). Use the official guide's risk concepts; treat the precise scoring scales and formulas here as project-selected CUBI techniques, not universal PMI-mandated numbers.

## 17. Estimation forms and uncertainty calculations

Estimate templates must record method, units, quantity basis, source evidence, assumptions, exclusions, base date, estimator/reviewer and applicable project/WBS/activity scope.

### 17.1 Three-point estimating options

Where the user selects a three-point technique with Optimistic O, Most Likely M and Pessimistic P values of the same measure/unit:

- PERT weighted estimate = (O + 4M + P) / 6.
- PERT standard-deviation estimate = (P − O) / 6, under the selected PERT assumptions.
- PERT variance = ((P − O) / 6)².
- Triangular mean, when explicitly selected = (O + M + P) / 3.

These are optional estimating techniques described in project-estimating practice, not formulas required for every PMBOK project. Validate O ≤ M ≤ P, consistent units/calendar basis and selected technique. Zero spread produces zero range under the formula; invalid ordering fails validation. Store O/M/P and formula version rather than only the result.

Example: O=20 days, M=30 days, P=50 days. PERT estimate = (20 + 120 + 50) / 6 = 31.666666… days; PERT standard deviation = 30/6 = 5 days. Display rounding is a separate declared boundary. The calendar service determines the interpretation of the duration result; the form must not directly add a decimal number of days to a date.

### 17.2 Estimate lineage and revision

An updated estimate must record whether it replaces or supplements the earlier estimate, the affected WBS/control accounts, changed assumptions, reason, and approval. Comparing estimates must use identical units/currency/base-date definitions or an explicit conversion. A calculation cannot make a previously approved baseline change without the designated baseline/change workflow.

### 17.3 Parametric and analogous methods

Do not assume one parametric factor works across all projects. A parametric form must identify the measured driver, quantity/rate definition, calibration dataset/source, rate effective date, scale, applicability and residual error. An analogous estimate must identify the comparison estimate and adjustment assumptions. The formula definition belongs to the selected method/configuration; it must not be hidden in an unversioned label.

**Source:** PMI Practice Standard for Project Estimating — Second Edition. The exact selected model, data assumptions and estimate units must be preserved.

## 18. Procurement and option-evaluation scores

A weighted evaluation form may compute a score when the organization has approved the criteria, relative weights, rating definitions and eligibility gates.

If rating r(i) and normalized weight w(i) are set:

Total Score = Σ(w(i) × r(i)), where Σw(i) = 1.

Equivalent form with weights in percentage points:

Total Score = Σ(WeightPercent(i) × Score(i)) / 100.

A normalized supplier score across a rating range [Smin, Smax] may use (Score − Smin)/(Smax − Smin) only if the project explicitly selects that normalization and Smax > Smin.

Required controls:
- weights must be non-negative and sum to the required total within the chosen tolerance;
- missing scores must be blocked or treated according to an explicit approved policy, never silently treated as zero;
- mandatory disqualification/qualification gates are evaluated separately from weighted scoring;
- tie-breaking, rounding and sensitivity to weight changes are disclosed;
- each score is supported by evaluator/evidence and conflicts of interest are captured;
- a top score is not an automatic award/approval. Procurement authority and contract rules remain separate.

Example: criteria weights 35%, 25%, 25%, 15%, ratings 4, 3, 5, 4. Total = 0.35×4 + 0.25×3 + 0.25×5 + 0.15×4 = 4.00 on a 1–5 scale.

## 19. Quantity progress and weighted physical progress forms

Construction progress forms may use measured/accepted quantities and weighted work-package progress, but the selected method must be project-approved and distinct from schedule percent complete or EVM Performance % Complete.

- Quantity progress = Accepted Actual Quantity / Approved Total Quantity × 100, if total quantity > 0.
- Remaining Quantity = Approved Total Quantity − Accepted Actual Quantity, if this quantity model is selected.
- Quantity Variance = Accepted Actual Quantity − Planned/Target Quantity at the selected data cut-off.
- Weighted physical progress = Σ(Approved Weight(i) × Physical Progress(i)) / ΣApproved Weights(i), where weights are from the named approved method (for example agreed quantity/value weights or work-package weights).
- Cumulative actual quantity = the source ledger's accepted quantity through the selected cut-off; never blindly sum duplicate daily entries.
- If actual quantity exceeds the baseline quantity, expose the overrun; do not silently clamp to 100%. Whether progress can exceed 100% is an explicit contract/project policy.
- Measurement unit conversions must use an approved conversion path and retain the original measurement unit/evidence.
- A work item rejected at inspection or not yet accepted must be included/excluded according to an explicit measurement rule; do not treat “installed”, “measured”, “inspected” and “accepted for payment” as equivalent states.

Schedule % Complete, activity Physical/Duration/Units %, earned progress quantity and EVM Performance % Complete are four separate concepts. The form may show more than one, but must not use a single field or formula for all of them.

## 20. Cost, change-impact and payment-form calculations

### 20.1 Cost line

For approved quantity Q and unit rate R in compatible units/currency:

Line Amount = Q × R.

Store Q, its UOM, R, its price UOM/currency and the resulting amount. Tax, escalation, indirect cost, contingency, currency conversion and overhead are separate components; include them only via an explicitly selected contract/estimate method. Formula precision/rounding is specified at line-level and rollup-level boundaries.

### 20.2 Change-request financial impact

Change Delta = Proposed/Approved New Value − Current Approved Value, with the two values defined under the same scope, date basis, currency and inclusions.

Total Change Cost Impact = Sum of line-level approved cost deltas + explicitly selected indirect/tax/escalation/other adjustment components.

Do not simply add schedule duration changes to compute schedule cost impact: any change affecting activity scope/duration/relationships/resources must be passed through the authoritative schedule and cost services, using a separate scenario/snapshot before approval. Report direct cost, indirect/overhead, risk/contingency, taxes, currency-conversion effects and forecast/EVM changes as named components. Whether values are included in the contract price or reserve is a project rule.

A change impact score across cost, time, scope, resources, risk, quality, safety and sustainability must be a configured weighted/threshold model, not an undocumented sum across dimensions with incompatible units.

### 20.3 Payment application/certificate

The site can offer the following configurable pattern for construction payment forms. It is a **CUBI construction extension governed by the contract**, not a universal PMBOK formula or legal/tax rule.

- Current Gross Measured Value = Σ(Approved Current-Period Quantity(i) × Applicable Contract Rate(i)).
- Cumulative Gross Value = source-ledger cumulative value through the certificate cut-off; where built from periods, validate it equals prior cumulative gross plus the current period's gross, adjusted by explicitly approved corrections.
- Retention Withheld = contract-defined retention function applied to eligible value; the contract may have caps, release stages, exemptions or differing rates.
- Advance Recovery = contract-defined recovery amount/function.
- Tax Amount = contract-defined taxable base × applicable tax rate, only where applicable and supported by the project's legal/contract settings.
- Other Adjustment = Σ explicitly signed/typed approved additions and deductions.
- Net Current Due = Current Gross Measured Value + Approved Additions + Applicable Tax − Retention Withheld − Advance Recovery − Other Deductions.
- Cumulative Net Certified is calculated from the approved certificate ledger; it must not double-count previous certificates.
- Balance to Contract = Applicable Contract Value − Cumulative Certified Value, if these values use the same currency/scope and contract-change version.

Example only: current measured value USD 5,000; eligible retention rate 5% = USD 250; approved advance recovery USD 500; approved deduction USD 100; approved tax on the full USD 5,000 taxable base at 10% = USD 500. Net Current Due = 5,000 + 500 − 250 − 500 − 100 = USD 4,650. If the tax base or contract treatment differs, the configured calculation must change accordingly.

The form must keep quantity approval, contractual rate, tax, retention, advance recovery, correction, prior certificate, evidence, reviewer and payment authorization distinct. A computed Net Due value does not itself approve payment or prove legal entitlement.

## 21. Quality, inspection, NCR/CAPA and checklist calculations

Simple rates are allowed if the denominator and population are explicit:
- Inspection Pass Rate = Passed Inspection Items / Applicable Inspected Items × 100.
- Nonconformance Rate = Rejected/Nonconforming Items / Applicable Inspected Items × 100.
- Closure Rate = Closed Eligible Corrective Actions / Total Eligible Corrective Actions × 100.

Require denominator > 0; otherwise return not-calculable. Record the cut-off, count definitions, cancelled/void items treatment, reinspection version and evidence source. For repeat inspections, do not count the same defect twice unless the selected metric measures inspection attempts rather than unique defects.

A failure-mode risk score such as Severity × Occurrence × Detection may be offered as a separately identified FMEA technique only where the quality organization selects and defines its scales. It is not asserted as a PMBOK-required formula. The scale definitions, multiplication convention, threshold, missing values and change history must be configured and reviewed.

A required quality/safety checklist item cannot be marked satisfied based only on a formula if it requires inspection evidence, qualified reviewer, signature or objective acceptance. Calculated scores support, but do not replace, technical acceptance and safety authority.

## 22. Stakeholder, communications, issue, decision and action forms

These record types share an item/log architecture but must remain distinct in meaning and state:

- **Stakeholder record:** identity, relationship to project, expectations/concerns, role, contact/privacy constraints, engagement owner and agreed engagement action.
- **Communication record:** audience, purpose, approved message, channel, planned/sent dates, response/decision and confidentiality.
- **Issue:** current problem/condition, impact, urgency, owner, due date, containment/response, dependency, escalation and resolution evidence.
- **Decision log:** question/decision, options considered, criteria, decision authority, date, rationale, impacts and follow-up.
- **Action item:** concrete work to complete, owner, due date/calendar policy, status, acceptance evidence and links to the issue/meeting/decision that created it.

Issue score = Impact Rating × Urgency Rating may be offered as a configurable ordinal prioritization policy. It is not a mandatory universal PMI formula. Working days overdue = shared-calendar working-time difference from due date to evaluation date only when the selected date policy calls for working-time; elapsed days use a different measure. Closed items remain auditable; closure status does not delete the underlying problem or all prior approvals.

## 23. Change governance, approval and workflow formulas

Define a workflow state machine per template/version, for example Draft → Submitted → In Review → Returned for Correction / Approved / Rejected → Implemented → Verified → Closed. This is a configurable example, not a universal PMI-mandated flow.

Every transition must define:
- permitted source and target states;
- actor/role/permission and segregation-of-duties constraint;
- required fields/evidence/signatures at that point;
- whether formulas must be freshly recalculated;
- whether the transition locks the form revision or baseline;
- notification/audit event;
- rollback/void/correction semantics;
- links to downstream actions (create WBS/activity/issue/RFI/contract change) and idempotency key.

Completion/readiness indicators can be calculated, but the final Approve/Reject action must be an authorized action with actor, timestamp, decision, rationale and audit trail. A formula result cannot impersonate a human signature. If automatic workflow transitions are explicitly configured, log the rule/version that caused them and preserve a human override/exception path.

## 24. Multilingual, RTL/LTR, Jalali/Gregorian and accessibility contract

All form definitions, option lists, instructions, validation messages, approval actions and calculation error descriptions must support the project's enabled languages. Stable IDs do not change with labels. Use language-specific translated labels and display formats.

- RTL or LTR layout changes presentation only, never the field IDs, formula order or numeric values.
- Displaying a date in Jalali or Gregorian format does not change the stored date or project event ordering.
- Decimal comma, grouping symbol, localized digits and currency placement are input/output formatting; parse only under an explicit locale and convert to canonical numeric values once.
- Date-only fields remain date-only; timestamps retain timezone-aware instants and a declared presentation timezone.
- Accessible names, tooltips, keyboard navigation, focus behavior, error summary and readable text are required for every control, including formula editor, validation icon, attachment action, approval buttons and export.
- For numeric forms, print/export must show units and context so the same amount is not mistaken for a different currency/unit after translation.

Required invariant test: enter one form in Persian RTL and another equivalent in an LTR language, then verify identical canonical data, calculation results, dependency order, approval policy and export values.

## 25. Security, evidence, privacy and audit

- Scope every template, instance, formula, attachment, approval and calculation by tenant and allowed project/revision context.
- Apply least privilege: design/edit template, publish, fill form, submit, review, approve, sign, export and administer formula compatibility are distinct capabilities.
- Prevent self-approval when the organization policy requires separation between proposer, reviewer and approver.
- Store append-only workflow events and immutable formula/template versions. Corrections produce a new event/version rather than erasing important decision evidence.
- Attachments are permission-bound evidence. Replacing an attachment after approval must create a new version and trigger re-review when policy demands it.
- Sensitive personal/contract/financial data needs access, redaction, retention and export policies.
- Exports and AI context must respect exactly the same authorization as the originating form.
- Formula output logs should record formula ID/version, input snapshot hash, engine version, value status and errors, while avoiding leakage of sensitive field values into general logs.

## 26. AI-assisted form creation under the 2026 AI standard

The AI assistant may propose:
- a form schema, sections and fields;
- field types and validation rules;
- a form/field-to-project-domain mapping;
- formula expression drafts and sample test cases;
- workflow/approval suggestions;
- translations, help text and a tailored template bundle;
- a list of missing fields or conflicting rules detected in an existing template.

But it must not publish a template, apply a destructive schema migration, approve a change/payment/inspection, execute an untested formula or silently change a project baseline without the specific authorized user action.

Required AI controls:
1. The AI output is an explicitly marked draft.
2. Each generated formula is passed through the same safe parser, type checker, dependency/cycle checks, unit checks, validators and test harness as a human-authored formula.
3. Each formula suggestion records the intended formula-authority class and source/assumption; it never claims PMBOK mandates a formula unless the official source actually does.
4. Human review compares formula inputs/outputs with examples and approves/publishes the immutable version.
5. The assistant can read/write only within user-granted tool permissions and project scope.
6. Approval and signature actions remain role/permission bound; AI cannot simulate a person’s signature or decision.
7. Source text, project confidential data, intellectual property and generated output are governed by access, retention and audit policies.
8. The standard AI workflow supports human review, correction/override, escalation and post-publication monitoring.

These provisions reflect PMI's June 2026 Standard for Artificial Intelligence in Portfolio, Program and Project Management at a high level: human-in-the-loop review, ethical/legal guardrails, lifecycle thinking and tailoring. They do not claim to reproduce its full paid content.

## 27. User-facing website menu, controls and icon registry

Every control that creates, edits, validates, calculates, approves, exports or reports a form must be inventoried. The action must map to a field/template/domain/API/formula ID and corresponding tests.

At minimum inventory these website surfaces where present:
- Form Builder landing/list/search/filter/clone/create/import;
- template designer and version status;
- field palette for each supported field type;
- section/group/repeating-table controls;
- field property drawer (ID, title, description, type, units, default, requiredness, validation, visibility, editability);
- formula editor, formula validation, dependency preview, test-input/sample-output panel;
- conditional logic/validation-rule builder;
- reference picker for project/activity/WBS/resource/contract/risk/issue;
- options/choice editor;
- localization/RTL preview and accessibility controls;
- form instance preview, save draft, submit, cancel, return for correction, approve, reject, sign/acknowledge;
- attachment/evidence management;
- template publish/deprecate/rollback/compare versions;
- audit history and revision comparison;
- report/print/PDF/Excel/CSV export;
- AI draft-generate/validate/revise/apply tools;
- mobile-responsive layout and keyboard shortcuts.

For each actual control record: stable action ID; screen/menu path; icon asset and accessible label; field/setting affected; domain API; formula IDs and dependencies; validation/error behavior; permissions; audit event; test IDs; owner; reviewer; and exact verified SHA. A screenshot alone does not prove the mapping. Absence from the registry is an audit gap, not evidence that the control has no effect.

## 28. Calculation and validation examples to make testable

These expected calculations become golden tests after their formula-authority class and rounding policy are assigned:

| ID | Inputs | Expected result | Key guard |
|---|---|---|---|
| FORM-RATIO-01 | N=42, D=60 | 70% | D must be positive |
| FORM-WEIGHT-01 | Weight 60 at 80%, weight 40 at 50% | 68% weighted result | Sum weights=100; values normalized consistently |
| FORM-RISK-01 | p=0.25, threat impact magnitude USD 100,000 | EMV magnitude USD 25,000; signed value follows declared threat convention | p in [0,1]; currency identity |
| FORM-PERT-01 | O=20, M=30, P=50 days | PERT expected duration 31.666666… days; standard deviation 5 days | O≤M≤P; rounding separated |
| FORM-TRI-01 | O=20, M=30, P=50 | Triangular mean 33.333333… in the same unit | Only if triangular mode selected |
| FORM-BID-01 | Weights 35/25/25/15%; scores 4/3/5/4 | 4.00 on 1–5 scale | Weight sum and mandatory gates |
| FORM-QUANTITY-01 | Accepted 42 m³, baseline 60 m³ | 70% measured progress; remaining 18 m³ | UOM and acceptance state |
| FORM-COST-01 | Quantity 125 m, rate USD 80/m | USD 10,000 line value | Same UOM and currency |
| FORM-CHANGE-01 | New approved value 1,200, baseline 1,000 | Delta +200; percent +20% | Same scope/basis; baseline≠0 |
| FORM-QUALITY-01 | 92 pass, 8 fail, 100 applicable inspections | Pass rate 92%; nonconformance rate 8% | Unique-vs-repeat inspection population declared |
| FORM-PAY-01 | Gross 5,000; tax 500; retention 250; advance recovery 500; deductions 100 | Net due 4,650 | Only when the explicit example tax/contract basis applies |
| FORM-OVERDUE-01 | Due date before evaluation date | Result from selected elapsed/working-time policy | Selected calendar/version and timezone |
| FORM-EVM-01 | Form points to approved shared EVM snapshot | Exactly the canonical engine EV/PV/AC/CPI/etc. values | No local shadow formula |

No golden test is considered complete until the result type, unit, precision, formula authority, missing-value handling and relevant output/audit status are also asserted.

## 29. Existing CUBI implementation baseline and gap mapping

A source tree check on 2026-10-18 found these relevant existing components in main:

- Field assurance templates: src/construction_pm/field_assurance_templates.py; shared/contracts/field-assurance-template.v1.schema.json; tests/test_field_assurance_templates.py and tests/integration/test_field_assurance_templates_postgres_live.py.
- The existing field-assurance template types are Inspection, Quality and Safety. The current v1 item input types are Boolean, Select, Text and Number. Its schema requires tenant/project/project revision, template ID/version, type/title key and ordered items.
- Formula engine: src/construction_pm/p6_formula_engine.py, formula authority/definition APIs and repositories, formula dependency graph, recalculation, rollups, unit semantics, compatibility registry and their tests. These are the current base to integrate with, not to duplicate.
- Existing formula types include Null, Boolean, Number, Text, Date and DateTime. The current canonical function registry documents IF, SUM, MIN, MAX, ABS, ROUND, COALESCE, NOT, AND and OR.
- docs/architecture/P6_FORMULA_DEFINITION_PERSISTENCE_API_V1.md makes the persistence/API boundary store Shared Core metadata; it does not parse/evaluate expressions. Formula definition identity includes tenant/project/formula/version with project revision scope and audit.
- docs/architecture/P6_FORMULA_DEPENDENCY_DAG_V1.md specifies deterministic dependency planning, transitive dependency detection and cycle rejection.
- docs/architecture/P6_FORMULA_RECALCULATION_V1.md specifies deterministic recalculation of affected formulas in topological order; failures must not return an authoritative partial result.
- docs/architecture/P6_FORMULA_ROLLUPS_V1.md records null/unit rules for SUM/MIN/MAX and identifies full subject-area rollup behavior as a separate conformance task.
- docs/architecture/P6_FORMULA_UNIT_SEMANTICS_V1.md explicitly states symbolic units do not perform actual currency/physical conversions and do not introduce calendar/date arithmetic.

This baseline is not proof of complete Form Builder capability. Gaps to resolve include extending form schema beyond four field types; integrating form instances/submissions and approval workflows; exposing explicit field/formula source and unit metadata; connecting template data to the shared formula engine; adding formula/validation/conditional UI; linking form values to approved project entities; and mapping every actual website control to its domain action and tests. A new schema/API contract must be versioned instead of silently altering field-assurance-template.v1.

## 30. Required test matrix and merge gate

Each new/changed form feature must have a documented minimum test matrix.

### Schema/template
- valid/invalid schema; duplicate ID/order/options; unsupported field/function/version;
- immutable version and deterministic serialization;
- tenant/project/revision mismatch; stale update and concurrent write;
- clone/import/export/publish/deprecate/rollback;
- existing form instances remain readable with their original template schema.

### Formula/type/unit
- every supported operator/function and argument signature;
- decimal accuracy, rounding boundary and locale input parsing;
- compatible/incompatible units and currency; no implicit conversion;
- null versus zero, empty SUM, zero denominator, negative/large values and unsupported result type;
- cycle trace, missing field dependency and transitive recalculation;
- deterministic repeat calculation and no partial authoritative output on error;
- formula function compatibility aliases by explicit source dialect/version.

### Form behavior/workflow
- hidden conditional required field under each configured hidden-value policy;
- required field, invalid value, correct error field/code/accessibility text;
- submit/return/approve/reject/close state transitions and unauthorized role;
- approval actor separation, evidence replacement after approval, attachment scope;
- formula version changes and older form submission replay;
- AI-proposed formula rejected until approved, permission-scoped output and audit.

### Domain formulas
- all golden rows in Section 28;
- ordinal risk score vs monetary EMV distinction; threat/opportunity sign;
- estimate technique changes PERT/Triangular output as selected;
- score weight sum, missing score and eligibility gate;
- quantity overrun (>100%), accepted/rejected quantities, duplicate period measurement;
- payment values, prior certificates, approved revisions, retention cap, tax base, advance recovery, zero amounts, currency/rounding;
- EVM fields match the canonical shared engine exactly, including baseline/Data Date and null/division semantics;
- due/overdue dates around weekend/holiday/shift/financial-period boundary according to selected date policy.

### UI, locale and output
- website form controls/actions map to action registry;
- keyboard/assistive technology, validation summary, focus management;
- RTL/LTR and all supported languages with identical canonical outputs;
- responsive form, repeated rows and large attachments;
- preview, print/PDF/Excel/CSV consistency and no secondary formulas in export code.

### Completion requirements
1. Applicable contract section IDs, authoritative source and formula authority are recorded in the PR.
2. Focused formula and schema tests pass.
3. Full required CI passes on the exact final SHA.
4. Database/PostgreSQL and DTO round-trip tests pass where affected.
5. Independent reviewer validates the formulas and actual control mapping.
6. OPEN items have named owner, evidence and target decision; they are not marked complete just to close a checklist.
7. Existing calculation validators and safe-formula restrictions remain active.
8. No product-completion or weighted-project-progress credit is awarded for documentation alone.

## 31. Official source register

Current source pages checked for this contract:

### PMBOK and general form tailoring
- [PMBOK® Guide — Eighth Edition, PMI official publication page](https://www.pmi.org/standards/pmbok) — page states publication November 2025, 408 pages, errata for the second printing last updated April 2026, six principles and seven performance domains.
- [PMI Standards and Publications catalog](https://www.pmi.org/standards) — current list of standards and practice guides; includes PMBOK 8, AI standard, earned value, estimating, scheduling, WBS, risk and business-analysis guides.
- [Project Management — Getting Back to Basics, PMI](https://www.pmi.org/learning/library/project-management-getting-back-basics-9313) — original PMI article describes tailoring templates/forms/logs to a practical methodology and examples such as charter, stakeholder list, requirements, schedule, risk register, action items, meeting minutes, status report, change request, acceptance and closeout. It also cautions against bureaucratic overuse.
- [Risks, issues, and changes: forms and logs, PMI](https://www.pmi.org/learning/library/risks-issues-changes-forms-logs-1078) — describes distinction between an individual form and a log of multiple records and the importance of linking items to their forms.

### AI-assisted form governance
- [The Standard for Artificial Intelligence in Portfolio, Program and Project Management, PMI official publication page](https://www.pmi.org/standards/artificial-intelligence) — June 2026, human-in-the-loop, 8 guiding principles, 5 performance domains and ethical/legal controls.
- [PMI press release: global AI standard published 9 June 2026](https://www.pmi.org/about/press-media/2026/pmi-publishes-worlds-first-global-standard-for-ai-in-project-work).

### Risk, business analysis and estimation
- [Risk Management in Portfolios, Programs, and Projects: A Practice Guide — PMI](https://www.pmi.org/standards/risk-management-in-portfolios) — current practice-guide listing for risk; the PMI catalog notes updated content in 2024.
- [Business Analysis for Practitioners: A Practice Guide — Second Edition](https://www.pmi.org/standards/business-analysis-second-edition) — published January 2024.
- [The PMI Guide to Business Analysis](https://www.pmi.org/shop/p-/book/the-pmi-guide-to-business-analysis/00101605701).
- [Practice Standard for Project Estimating — Second Edition](https://www.pmi.org/shop/p-/book/practice-standard-for-project-estimating---second-edition/00101618601) — estimating models for plan-driven and adaptive life cycles.

### Related canonical calculation/technical services
- [Practice Standard for Scheduling — Third Edition](https://www.pmi.org/shop/p-/book/practice-standard-for-scheduling---third-edition/00101612701) — supporting reference for the schedule domain; CUBI must still use the separate canonical scheduling engine.
- [Practice Standard for Work Breakdown Structures — Third Edition](https://www.pmi.org/shop/p-/book/practice-standard-for-work-breakdown-structures---third-edition/00101616801) — WBS is a cross-discipline foundation for schedule, budget, risk and performance reporting.
- [The Standard for Earned Value Management — PMI](https://www.pmi.org/shop/p-/book/the-standard-for-earned-value-management/00101618501) — EVM as integration of scope, schedule, resources, performance and forecasts.
- [CUBI shared formula engine source](../../src/construction_pm/p6_formula_engine.py).
- [CUBI formula dependency graph contract](../architecture/P6_FORMULA_DEPENDENCY_DAG_V1.md).
- [CUBI formula recalculation contract](../architecture/P6_FORMULA_RECALCULATION_V1.md).
- [CUBI formula unit semantics](../architecture/P6_FORMULA_UNIT_SEMANTICS_V1.md).
- [CUBI field-assurance template schema](../../shared/contracts/field-assurance-template.v1.schema.json).

## 32. OPEN items and adoption ledger

The form calculation layer is not complete until these have a named owner, source evidence, test ID, reviewer and status:
- exact form/field list and workflows enabled for each CUBI subscription/project type;
- complete actual website Form Builder UI/control/icon inventory;
- all field types and schema migrations beyond field-assurance-template.v1;
- formula functions/operators and date/calendar/unit integration not yet supported by Shared Formula Core;
- source-backed defaults and every selectable risk/estimate/quality/procurement scoring model;
- detailed saved estimate/measurement/payment rules at the contract/country/project level;
- approval/security/segregation-of-duties rules for every form family;
- old form instance compatibility when formulas, options, translations or template version change;
- actual implementation/test mapping for every domain form in Section 14;
- parity or source-check fixtures for every formula labelled PMI-DOCUMENTED.

Permitted states: NOT REVIEWED; SOURCE REVIEWED; SPECIFIED; IMPLEMENTED—UNVERIFIED; TESTED; INDEPENDENTLY REVIEWED; OPEN/AMBIGUOUS; NOT IMPLEMENTED; NOT APPLICABLE WITH REASON. Never translate “source reviewed” into “implemented”, or “implemented” into “tested”.

## 33. Definition of Done

This contract is adopted only when:
1. It is merged into the authoritative main branch.
2. Repository agent instructions and the development rules require it before form/field/calculation changes.
3. Form Builder templates, formula editor, validation and workflow actions are mapped to this contract.
4. Every form family and calculation technique has schema definitions, field IDs, authority class, expected formula, input/output units and test cases.
5. PMBOK-guided templates are tailored/project-configured and are not misrepresented as universally mandatory.
6. Every schedule/EVM value uses the canonical calculation service.
7. All required tests and full CI pass on the exact final SHA, with independent review.
8. The unresolved coverage ledger is accurate; all remaining OPEN items are visible and owned.

Until these gates pass, this document is the mandatory target contract and gap register—not a claim that the current site has already implemented every feature or is fully PMBOK-conformant.
